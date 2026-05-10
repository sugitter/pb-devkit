"""pb dw command - DataWindow analyzer: SQL extraction, table schema reverse-engineering.

Parse PowerBuilder DataWindow objects (.srd source files or .ps decompiled files)
and extract:
  - Embedded SQL SELECT statements
  - Table names and column definitions
  - Retrieve arguments (parameters)
  - DataWindow style (tabular/freeform/grid/crosstab/label/graph/ole/etc.)
  - DataWindow → Window/UO reference mapping

Output modes:
  - Default: Pretty-print per-DW summary
  - --sql:   Print raw SQL only (pipe-friendly)
  - --tables: Print table → column schema (DDL-like)
  - --json:  Machine-readable JSON
  - --html:  Standalone HTML report

Usage:
    python pb.py dw <src_dir>                    # Analyze all .srd in dir
    python pb.py dw <src_dir> --sql              # Extract SQL only
    python pb.py dw <src_dir> --tables           # Schema per table
    python pb.py dw <src_dir/d_order.srd>        # Single file
    python pb.py dw <src_dir> --filter d_order%  # Wildcard filter
    python pb.py dw <src_dir> --html -o dw.html  # HTML report
    python pb.py dw <src_dir> --json             # JSON output
"""
import argparse
import sys
import re
import json
import fnmatch
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Optional, List, Dict, Any


def register(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
    p = sub.add_parser(
        "dw",
        help="DataWindow analyzer: SQL, tables, columns, schema reverse-engineering",
        description=(
            "Parse PowerBuilder DataWindow source files (.srd, .ps) to extract "
            "embedded SQL, table schemas, retrieve arguments and generate reports."
        ),
    )
    p.add_argument(
        "target",
        help="Source directory or single .srd/.ps file",
    )
    p.add_argument(
        "--filter",
        default=None,
        metavar="PATTERN",
        help="Wildcard filter for DW names (e.g. 'd_order*', '*_list')",
    )
    p.add_argument(
        "--sql",
        action="store_true",
        help="Print extracted SQL statements only",
    )
    p.add_argument(
        "--tables",
        action="store_true",
        help="Print table schema (table -> columns) summary",
    )
    p.add_argument(
        "--html",
        action="store_true",
        help="Generate standalone HTML report",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Output file (default: stdout for text, DW_REPORT.html for --html)",
    )
    p.add_argument(
        "--no-refs",
        action="store_true",
        help="Skip scanning for window/UO references to DataWindow objects",
    )
    return p


def run(args):
    """Run DataWindow analysis."""
    target = Path(args.target).resolve()
    if not target.exists():
        print(f"[error] Not found: {target}", file=sys.stderr)
        sys.exit(1)

    # --- Collect files ---
    if target.is_file():
        files = [target]
        src_dir = target.parent
    else:
        files = sorted(target.rglob("*.srd")) + sorted(target.rglob("*.ps"))
        # Deduplicate and filter
        seen = set()
        unique = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique.append(f)
        files = unique
        src_dir = target

    # Apply filter
    if args.filter:
        pat = args.filter.lower()
        files = [f for f in files if fnmatch.fnmatch(f.stem.lower(), pat)]

    if not files:
        print(f"[warn] No DataWindow files found in: {target}", file=sys.stderr)
        sys.exit(0)

    # --- Parse ---
    print(f"Parsing {len(files)} DataWindow file(s)...", file=sys.stderr)
    dws: List[Dict[str, Any]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
            dw_info = _parse_dw_file(f.stem, text, f.suffix.lower())
            dw_info["_file"] = str(f.relative_to(src_dir) if src_dir else f)
            dws.append(dw_info)
        except Exception as e:
            dws.append({
                "name": f.stem,
                "_file": str(f),
                "error": str(e),
                "tables": [], "columns": [], "sql": "",
                "retrieve_args": [], "style": "",
            })

    # --- Scan references ---
    refs: Dict[str, List[str]] = defaultdict(list)
    if not args.no_refs and src_dir.is_dir():
        refs = _scan_dw_references(src_dir)

    # --- Compose table schema ---
    table_schema = _build_table_schema(dws)

    # --- Output ---
    if args.sql:
        _output_sql(dws, args.output)
        return

    if args.tables:
        _output_tables(table_schema, args.output)
        return

    if args.json:
        _output_json(dws, refs, table_schema, args.output)
        return

    if args.html:
        out_path = Path(args.output) if args.output else (src_dir / "DW_REPORT.html")
        html = _render_html(dws, refs, table_schema, src_dir)
        out_path.write_text(html, encoding="utf-8")
        print(f"HTML report: {out_path}", file=sys.stderr)
        return

    # Default: pretty text
    _output_text(dws, refs, table_schema)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

# DataWindow .srd syntax patterns
_DW_STYLE_RE = re.compile(r'\bprocessing\s+(\d+)\b', re.IGNORECASE)
_DW_STYLE_TEXT_RE = re.compile(r'\bstyle\s+type=(\w+)', re.IGNORECASE)
_DW_SQL_RE = re.compile(r'retrieve\s*=\s*"(.*?)"', re.IGNORECASE | re.DOTALL)
_DW_TABLE_RE = re.compile(r'\btable\s+name=(["\w]+)', re.IGNORECASE)
_DW_COL_RE = re.compile(
    r'\bcolumn\s+(?:[a-z_]+=["\w]+\s+)*(?:type=(\w+)\s+)?(?:[a-z_]+=["\w]+\s+)*name=(["\w]+)',
    re.IGNORECASE
)
_DW_COL_TYPE_NAME_RE = re.compile(
    r'\bcolumn\b((?:\s+[a-z_]+=(?:"[^"]*"|\w+))*)',
    re.IGNORECASE
)
_DW_ARGS_RE = re.compile(r'arguments\s*=\s*\(([^)]*)\)', re.IGNORECASE)
_DW_FROM_RE = re.compile(
    r'\bfrom\s+([\w.,\s\[\]`"]+?)(?:\s+where|\s+order\s+by|\s+group\s+by|\s+having|\s*$)',
    re.IGNORECASE
)
_DW_WHERE_RE = re.compile(
    r'\bwhere\s+(.*?)(?:\s+order\s+by|\s+group\s+by|\s+having|\s*$)',
    re.IGNORECASE | re.DOTALL
)
_DW_ORDERBY_RE = re.compile(
    r'\border\s+by\s+(.*?)(?:\s+group\s+by|\s+having|\s*$)',
    re.IGNORECASE | re.DOTALL
)

# .ps decompiled patterns (binary DataWindow attributes format)
_PS_ATTR_RE = re.compile(r'^(\w+)\s+"(.*)"', re.IGNORECASE)

STYLE_MAP = {
    "0": "freeform", "1": "tabular", "2": "label", "3": "n-up",
    "4": "crosstab", "5": "graph", "6": "ole", "7": "richtext",
    "8": "grid", "9": "composite",
    "freeform": "freeform", "tabular": "tabular", "label": "label",
    "grid": "grid", "crosstab": "crosstab", "graph": "graph",
    "ole": "ole", "richtext": "richtext",
}


def _parse_dw_file(name: str, text: str, ext: str) -> Dict[str, Any]:
    """Parse a DataWindow source file (.srd or .ps)."""
    info: Dict[str, Any] = {
        "name": name,
        "tables": [],
        "columns": [],
        "sql": "",
        "sql_tables": [],
        "sql_where": "",
        "sql_orderby": "",
        "retrieve_args": [],
        "style": "",
        "computed_columns": [],
        "error": None,
    }

    # Detect if it looks like a proper .srd source
    is_srd = ("$PBExportHeader" in text or "datawindow(" in text.lower()
               or "table(" in text.lower() or "column(" in text.lower())

    # Also handle .ps (binary decompiled) - these are attribute=value pairs
    is_ps_attr = ext == ".ps" and not is_srd

    if is_ps_attr:
        return _parse_dw_ps_attrs(name, text)

    # ---- Parse .srd format ----

    # Style
    m = _DW_STYLE_TEXT_RE.search(text)
    if m:
        info["style"] = STYLE_MAP.get(m.group(1).lower(), m.group(1))
    else:
        m = _DW_STYLE_RE.search(text)
        if m:
            info["style"] = STYLE_MAP.get(m.group(1), m.group(1))

    # Extract SQL
    m = _DW_SQL_RE.search(text)
    if m:
        raw_sql = m.group(1)
        # Decode PB escape sequences
        sql = _decode_pb_string(raw_sql)
        info["sql"] = sql
        # Parse SQL parts
        fm = _DW_FROM_RE.search(sql)
        if fm:
            for tbl in _split_tables(fm.group(1)):
                if tbl and tbl not in info["sql_tables"]:
                    info["sql_tables"].append(tbl)
        wm = _DW_WHERE_RE.search(sql)
        if wm:
            info["sql_where"] = wm.group(1).strip()
        om = _DW_ORDERBY_RE.search(sql)
        if om:
            info["sql_orderby"] = om.group(1).strip()

    # Extract table() declarations
    for m in _DW_TABLE_RE.finditer(text):
        tbl = m.group(1).strip('"').strip()
        if tbl and tbl not in info["tables"]:
            info["tables"].append(tbl)

    # Merge sql_tables into tables
    for tbl in info["sql_tables"]:
        if tbl not in info["tables"]:
            info["tables"].append(tbl)

    # Extract columns via attribute parsing
    # Match lines like: column type=char(40)  name="col_name" ...
    for m in _DW_COL_TYPE_NAME_RE.finditer(text):
        attr_str = m.group(1)
        # Extract name and type from attribute string
        name_m = re.search(r'\bname=(["\w]+)', attr_str, re.IGNORECASE)
        type_m = re.search(r'\btype=(["\w()]+)', attr_str, re.IGNORECASE)
        dbname_m = re.search(r'\bdbname=(["\w.]+)', attr_str, re.IGNORECASE)
        if name_m:
            col_name = name_m.group(1).strip('"')
            col_type = type_m.group(1).strip('"') if type_m else ""
            db_name = dbname_m.group(1).strip('"') if dbname_m else col_name
            if col_name and col_name not in [c["name"] for c in info["columns"]]:
                info["columns"].append({
                    "name": col_name,
                    "type": col_type,
                    "dbname": db_name,
                })

    # Computed fields
    for m in re.finditer(
            r'\bcompute\s+(?:[a-z_]+=["\w.()]+\s+)*name=(["\w]+)',
            text, re.IGNORECASE):
        col_name = m.group(1).strip('"')
        if col_name:
            info["computed_columns"].append(col_name)

    # Retrieve arguments
    m = _DW_ARGS_RE.search(text)
    if m:
        args_str = m.group(1)
        for arg in re.findall(r'"(\w+)"\s+(\w+)', args_str):
            info["retrieve_args"].append({"name": arg[0], "type": arg[1]})

    return info


def _parse_dw_ps_attrs(name: str, text: str) -> Dict[str, Any]:
    """Parse binary-decompiled .ps DataWindow (attribute=value format)."""
    info: Dict[str, Any] = {
        "name": name,
        "tables": [],
        "columns": [],
        "sql": "",
        "sql_tables": [],
        "sql_where": "",
        "sql_orderby": "",
        "retrieve_args": [],
        "style": "binary",
        "computed_columns": [],
        "error": None,
        "_format": "binary_ps",
    }

    # These files contain something like:
    #   __set_attribute_item("dataobject", "d_xxx")
    #   __get_attribute_item("retrieve", ...)
    # Or raw attribute dumps - try to extract any visible SQL
    sql_candidates = re.findall(
        r'(?:SELECT|select)\s+.+?(?:FROM|from)\s+\w+',
        text, re.DOTALL
    )
    if sql_candidates:
        info["sql"] = sql_candidates[0][:2000]
        fm = _DW_FROM_RE.search(info["sql"])
        if fm:
            for tbl in _split_tables(fm.group(1)):
                if tbl:
                    info["sql_tables"].append(tbl)
                    info["tables"].append(tbl)

    # Try to find table names in any readable text
    for m in re.finditer(r'"(\w{3,30})"', text):
        val = m.group(1)
        if re.match(r'^[a-z][a-z0-9_]{2,}$', val, re.IGNORECASE):
            if val.lower() not in ("true", "false", "null", "and", "or",
                                    "where", "from", "select", "order", "group"):
                # Heuristic: looks like a table name
                pass  # Too noisy; skip

    info["_note"] = "Binary-decompiled .ps file; SQL extraction limited."
    return info


def _decode_pb_string(s: str) -> str:
    """Decode PowerBuilder string escape sequences."""
    return (s.replace("~n", "\n")
             .replace("~r", "\r")
             .replace("~t", "\t")
             .replace('~"', '"')
             .replace("~~", "~"))


def _split_tables(from_clause: str) -> List[str]:
    """Split FROM clause into individual table names."""
    tables = []
    # Handle JOIN syntax: remove JOIN keywords
    from_clause = re.sub(
        r'\b(?:inner|outer|left|right|full|cross)\s+join\b.*?(?=,|\bon\b|\Z)',
        '', from_clause, flags=re.IGNORECASE
    )
    from_clause = re.sub(r'\bjoin\b', ',', from_clause, flags=re.IGNORECASE)
    for part in re.split(r'[,\s]+', from_clause):
        part = part.strip().strip('"').strip('[').strip(']').strip('`')
        # Remove aliases: "table_name alias" or "table_name AS alias"
        part = re.split(r'\s+(?:as\s+)?\w+\s*$', part, flags=re.IGNORECASE)[0]
        part = part.strip()
        if part and re.match(r'^[\w.]+$', part) and len(part) > 1:
            tables.append(part.lower())
    return tables


def _scan_dw_references(src_dir: Path) -> Dict[str, List[str]]:
    """Scan source files for DataWindow control assignments."""
    refs: Dict[str, List[str]] = defaultdict(list)
    patterns = [
        re.compile(r'\.dataobject\s*=\s*["\'](\w+)["\']', re.IGNORECASE),
        re.compile(r'dataobject\s*=\s*["\'](\w+)["\']', re.IGNORECASE),
    ]
    for f in sorted(src_dir.rglob("*")):
        if f.suffix.lower() not in (".srw", ".sru", ".srf", ".ps"):
            continue
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
            for pat in patterns:
                for m in pat.finditer(text):
                    dw_name = m.group(1).lower()
                    src_name = f.stem
                    if src_name not in refs[dw_name]:
                        refs[dw_name].append(src_name)
        except Exception:
            pass
    return dict(refs)


def _build_table_schema(dws: List[Dict]) -> Dict[str, Dict]:
    """Build a table -> {columns, used_by_dws} schema from all DW data."""
    schema: Dict[str, Any] = defaultdict(lambda: {"columns": {}, "dws": []})
    for dw in dws:
        name = dw.get("name", "")
        for tbl in dw.get("tables", []):
            if tbl and tbl != "":
                schema[tbl]["dws"].append(name)
        for col in dw.get("columns", []):
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            db_name = col.get("dbname", col_name)
            if col_name and not col_name.startswith("dw_"):
                for tbl in dw.get("tables", []):
                    if tbl:
                        if db_name not in schema[tbl]["columns"]:
                            schema[tbl]["columns"][db_name] = col_type
    return {k: dict(v) for k, v in schema.items()}


# ---------------------------------------------------------------------------
# Output modes
# ---------------------------------------------------------------------------

def _output_sql(dws: List[Dict], out_path: Optional[str]):
    """Print SQL statements only."""
    lines = []
    for dw in dws:
        sql = dw.get("sql", "")
        if sql:
            lines.append(f"-- [{dw['name']}]")
            lines.append(sql)
            lines.append("")
    text = "\n".join(lines)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
    else:
        print(text)


def _output_tables(schema: Dict, out_path: Optional[str]):
    """Print table schema summary."""
    lines = ["# DataWindow Table Schema", ""]
    for tbl, info in sorted(schema.items()):
        lines.append(f"## {tbl}")
        cols = info.get("columns", {})
        if cols:
            lines.append("")
            lines.append("| 列名 | 类型 |")
            lines.append("|------|------|")
            for col, typ in sorted(cols.items()):
                lines.append(f"| {col} | {typ} |")
        dws = info.get("dws", [])
        if dws:
            lines.append(f"\n使用: {', '.join(dws[:5])}" + (f" (+{len(dws)-5})" if len(dws) > 5 else ""))
        lines.append("")
    text = "\n".join(lines)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
    else:
        print(text)


def _output_json(dws: List[Dict], refs: Dict, schema: Dict, out_path: Optional[str]):
    """Output JSON."""
    data = {
        "datawindows": dws,
        "references": refs,
        "table_schema": schema,
        "generated_at": datetime.now().isoformat(),
    }
    text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
    else:
        print(text)


def _output_text(dws: List[Dict], refs: Dict, schema: Dict):
    """Pretty-print summary."""
    width = 62
    print(f"\n{'='*width}")
    print(f"  DataWindow Analysis Report")
    print(f"{'='*width}")
    print(f"  Total DW: {len(dws)}")
    print(f"  Tables:   {len(schema)}")
    print()

    for dw in dws:
        name = dw.get("name", "?")
        style = dw.get("style", "")
        tables = dw.get("tables", [])
        cols = dw.get("columns", [])
        args = dw.get("retrieve_args", [])
        sql = dw.get("sql", "")
        err = dw.get("error")

        print(f"  ┌─ {name} [{style}]")
        if err:
            print(f"  │  ⚠️  Error: {err}")
        else:
            if tables:
                print(f"  │  Tables:  {', '.join(tables)}")
            if cols:
                col_names = [c.get("name", "") for c in cols[:8]]
                more = f" (+{len(cols)-8})" if len(cols) > 8 else ""
                print(f"  │  Columns: {', '.join(col_names)}{more}")
            if args:
                arg_strs = [f"{a['name']}:{a['type']}" for a in args]
                print(f"  │  Args:    {', '.join(arg_strs)}")
            if sql:
                sql_preview = sql.replace("\n", " ")[:80]
                print(f"  │  SQL:     {sql_preview}...")
            ref_list = refs.get(name.lower(), [])
            if ref_list:
                print(f"  │  Used by: {', '.join(ref_list[:5])}")
        print(f"  └{'─'*50}")
        print()

    # Table schema summary
    if schema:
        print(f"\n{'='*width}")
        print(f"  Database Table Schema")
        print(f"{'='*width}")
        for tbl, info in sorted(schema.items()):
            cols_count = len(info.get("columns", {}))
            dws_count = len(info.get("dws", []))
            print(f"  {tbl:30s}  {cols_count:3d} cols  {dws_count} DW(s)")
        print()


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def _render_html(dws: List[Dict], refs: Dict,
                 schema: Dict, src_dir: Path) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"DataWindow Report — {src_dir.name}"

    # Build rows
    dw_rows = []
    for dw in dws:
        name = dw.get("name", "?")
        style = dw.get("style", "")
        tables = ", ".join(f"<code>{t}</code>" for t in dw.get("tables", []))
        col_count = len(dw.get("columns", []))
        arg_count = len(dw.get("retrieve_args", []))
        ref_list = refs.get(name.lower(), [])
        ref_str = ", ".join(f"<code>{r}</code>" for r in ref_list[:5])
        err = dw.get("error", "")
        sql = dw.get("sql", "")
        sql_preview = (sql[:120].replace("<", "&lt;").replace(">", "&gt;")
                       .replace("\n", " ") + "...") if sql else ""

        detail_id = f"dw_{name}"
        dw_rows.append(f"""
        <tr>
          <td><a href="#" onclick="toggleDetail('{detail_id}');return false;"
                class="dw-name">{name}</a></td>
          <td><span class="badge">{style}</span></td>
          <td>{tables}</td>
          <td>{col_count}</td>
          <td>{arg_count}</td>
          <td>{ref_str}</td>
        </tr>
        <tr id="{detail_id}" style="display:none">
          <td colspan="6" class="detail-cell">
            {'<span class="err">⚠️ ' + err + '</span>' if err else ''}
            {'<div class="sql-block">' + sql_preview + '</div>' if sql_preview else ''}
            {_render_columns_table(dw.get("columns", []))}
            {_render_args_list(dw.get("retrieve_args", []))}
          </td>
        </tr>""")

    # Schema rows
    schema_rows = []
    for tbl, info in sorted(schema.items()):
        cols = info.get("columns", {})
        dw_list = info.get("dws", [])
        col_list = ", ".join(
            f"<code>{c}</code>" + (f"<small>({t})</small>" if t else "")
            for c, t in sorted(cols.items())[:15]
        )
        if len(cols) > 15:
            col_list += f" <em>(+{len(cols)-15} more)</em>"
        dw_str = ", ".join(f"<code>{d}</code>" for d in dw_list[:8])
        if len(dw_list) > 8:
            dw_str += f" <em>(+{len(dw_list)-8})</em>"
        schema_rows.append(f"""
        <tr>
          <td><strong>{tbl}</strong></td>
          <td>{col_list}</td>
          <td>{dw_str}</td>
        </tr>""")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
         background: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ color: #2c3e50; font-size: 1.6em; margin-bottom: 4px; }}
  .subtitle {{ color: #888; font-size: 0.9em; margin-bottom: 24px; }}
  h2 {{ color: #2980b9; font-size: 1.2em; margin: 32px 0 12px; border-left: 4px solid #3498db;
        padding-left: 10px; }}
  .stats {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .stat-card {{ background: white; border-radius: 8px; padding: 16px 24px;
               box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .stat-card .num {{ font-size: 2em; font-weight: bold; color: #2980b9; }}
  .stat-card .label {{ font-size: 0.85em; color: #888; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           border-radius: 8px; overflow: hidden;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; }}
  th {{ background: #2980b9; color: white; padding: 10px 14px; text-align: left;
        font-size: 0.9em; }}
  td {{ padding: 8px 14px; border-bottom: 1px solid #f0f0f0; font-size: 0.9em;
        vertical-align: top; }}
  tr:hover td {{ background: #f8fbff; }}
  .dw-name {{ color: #2980b9; text-decoration: none; font-weight: 500; }}
  .dw-name:hover {{ text-decoration: underline; }}
  .badge {{ background: #ecf0f1; border-radius: 4px; padding: 2px 8px;
            font-size: 0.82em; color: #555; }}
  code {{ background: #ecf0f1; border-radius: 3px; padding: 1px 5px;
          font-size: 0.85em; font-family: monospace; }}
  .detail-cell {{ background: #f8f9fa; padding: 16px 20px !important; }}
  .sql-block {{ font-family: monospace; font-size: 0.85em; background: #2c3e50;
               color: #ecf0f1; padding: 12px; border-radius: 4px; margin: 8px 0;
               white-space: pre-wrap; word-break: break-all; }}
  .err {{ color: #e74c3c; }}
  .col-table {{ width: auto; box-shadow: none; margin: 8px 0; }}
  .col-table th {{ background: #7f8c8d; font-size: 0.82em; padding: 4px 10px; }}
  .col-table td {{ padding: 4px 10px; border-bottom: 1px solid #eee; font-size: 0.82em; }}
  small {{ color: #999; }}
  input[type=text] {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px;
                      width: 280px; font-size: 0.9em; }}
</style>
</head>
<body>
<div class="container">
  <h1>📊 {title}</h1>
  <div class="subtitle">生成时间: {ts}</div>

  <div class="stats">
    <div class="stat-card"><div class="num">{len(dws)}</div><div class="label">DataWindow 对象</div></div>
    <div class="stat-card"><div class="num">{len(schema)}</div><div class="label">数据库表</div></div>
    <div class="stat-card"><div class="num">{sum(len(d.get('columns',[])) for d in dws)}</div><div class="label">列定义</div></div>
    <div class="stat-card"><div class="num">{sum(1 for d in dws if d.get('sql'))}</div><div class="label">含 SQL</div></div>
  </div>

  <input type="text" id="filterInput" placeholder="过滤 DataWindow 名称..." oninput="filterTable()">

  <h2>DataWindow 列表</h2>
  <table id="dwTable">
    <thead>
      <tr>
        <th>名称</th><th>样式</th><th>表</th>
        <th>列数</th><th>参数</th><th>被引用</th>
      </tr>
    </thead>
    <tbody>
      {''.join(dw_rows)}
    </tbody>
  </table>

  <h2>数据库表结构</h2>
  <table>
    <thead>
      <tr><th>表名</th><th>列</th><th>DataWindow</th></tr>
    </thead>
    <tbody>
      {''.join(schema_rows)}
    </tbody>
  </table>
</div>

<script>
function toggleDetail(id) {{
  const el = document.getElementById(id);
  el.style.display = el.style.display === 'none' ? 'table-row' : 'none';
}}
function filterTable() {{
  const val = document.getElementById('filterInput').value.toLowerCase();
  const rows = document.querySelectorAll('#dwTable tbody tr');
  let skip = false;
  rows.forEach(row => {{
    if (row.id && row.id.startsWith('dw_')) {{
      skip = !row.id.toLowerCase().includes(val);
      row.style.display = skip ? 'none' : '';
    }} else {{
      row.style.display = skip ? 'none' : '';
    }}
  }});
}}
</script>
</body>
</html>"""


def _render_columns_table(columns: List[Dict]) -> str:
    if not columns:
        return ""
    rows = "".join(
        f"<tr><td>{c.get('name','')}</td>"
        f"<td>{c.get('type','')}</td>"
        f"<td>{c.get('dbname','')}</td></tr>"
        for c in columns[:30]
    )
    more = f"<tr><td colspan=3><em>... +{len(columns)-30} 列</em></td></tr>" if len(columns) > 30 else ""
    return f"""<table class="col-table">
    <thead><tr><th>列名</th><th>类型</th><th>DB字段</th></tr></thead>
    <tbody>{rows}{more}</tbody>
    </table>"""


def _render_args_list(args: List[Dict]) -> str:
    if not args:
        return ""
    items = " ".join(f"<code>{a['name']}:{a['type']}</code>" for a in args)
    return f"<div><strong>检索参数:</strong> {items}</div>"
