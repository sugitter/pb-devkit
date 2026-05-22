"""DataWindow source (.srd) parser."""
import re
from typing import Dict, List, Optional, Any


class DWParser:
    """Parser for DataWindow source files.

    Extracts SQL statements, table names, columns, arguments, and styles.
    """

    def __init__(self, content: str):
        self.content = content
        self.lines = content.splitlines()

    def extract_sql(self) -> Optional[str]:
        """Extract embedded SQL SELECT statement."""
        # Match SQL SELECT in various formats
        patterns = [
            r'select\s+(.+?)\s+from\s+(\w+)',
            r'SELECT\s+(.+?)\s+FROM\s+(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.content, re.IGNORECASE | re.DOTALL)
            if match:
                cols, table = match.groups()
                return f"SELECT {cols} FROM {table}"
        return None

    def extract_table(self) -> Optional[str]:
        """Extract primary table name."""
        sql = self.extract_sql()
        if sql:
            match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_columns(self) -> List[str]:
        """Extract column names from SELECT."""
        sql = self.extract_sql()
        if not sql:
            return []
        match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if match:
            cols = match.group(1).strip()
            if cols == "*":
                return ["*"]
            return [c.strip() for c in cols.split(",")]
        return []

    def extract_arguments(self) -> List[Dict[str, str]]:
        """Extract retrieve arguments."""
        args = []
        # Match: arguments=(("name", type, ...)
        pattern = r'arguments\s*=\s*\(\((.+?)\)'
        match = re.search(pattern, self.content, re.IGNORECASE)
        if match:
            for arg in match.group(1).split("),("):
                parts = arg.replace('"', '').split(",")
                if len(parts) >= 2:
                    args.append({"name": parts[0].strip(), "type": parts[1].strip()})
        return args

    def get_style(self) -> Optional[str]:
        """Extract DataWindow presentation style."""
        styles = ["tabular", "freeform", "grid", "crosstab", "label", "graph", "ole", "rich"]
        content_lower = self.content.lower()
        for style in styles:
            if f'presentation="{style}' in content_lower or f"presentation='{style}" in content_lower:
                return style
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "table": self.extract_table(),
            "columns": self.extract_columns(),
            "sql": self.extract_sql(),
            "arguments": self.extract_arguments(),
            "style": self.get_style(),
        }