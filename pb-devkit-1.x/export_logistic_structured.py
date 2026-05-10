"""Export logistic.exe source code with organized directory structure (v2).

Improved classification:
  src/
    app/            - Application framework (appmaster, uo_application, nvo_*, exe_index)
    windows/        - Window objects (w_*.win)
    userobjects/    - Standard/visual User Objects (uo_*.udo, n_coolmenu)
    menus/          - Menu objects (m_*.udo)
    functions/      - Global functions (uf_* / f_* / *_fun)
    datawindows/    - DataWindow objects (d_* / dw_*)
    structures/     - Structure objects (str_*, rect)
"""
import sys
sys.path.insert(0, 'src')
from pb_devkit.decompiler import decompile_file
from pathlib import Path

EXE_PATH = r'F:\workspace\X6\logistic\logistic\logistic.exe'
OUT_BASE = Path(r'F:\workspace\X6\logistic\logistic\src')


def classify_entry(name: str) -> str | None:
    """Determine subdirectory for an entry based on name and type suffix."""
    if '\\' in name or '/' in name:
        return None  # binary/image path

    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
    base = name.rsplit('.', 1)[0].lower() if '.' in name else name.lower()

    # Known specials
    if base in ('appmaster', 'uo_application'):
        return 'app'
    if name.lower() == 'ob.exe':
        return 'app'  # EXE table of contents

    # Type suffix mapping
    if ext == 'win':
        return 'windows'
    if ext == 'udo':
        if base.startswith('m_') or 'menu' in base:
            return 'menus'
        if base.startswith('nvo_'):
            return 'app'
        return 'userobjects'
    if ext == 'fun':
        return 'functions'
    if ext == 'srd':
        return 'datawindows'
    if ext == 'srs':
        return 'structures'
    if ext == 'srw':
        return 'windows'
    if ext == 'srm':
        return 'menus'
    if ext == 'srf':
        return 'functions'
    if ext == 'sru':
        return 'userobjects'
    if ext == 'srp' or ext == 'srj' or ext == 'src':
        return 'app'
    if ext == 'srq' or ext == 'srx' or ext == 'sre':
        return 'userobjects'
    if ext == 'sra':
        return 'app'
    if ext == 'str':
        return 'structures'

    # Heuristics for objects without clear suffix
    if base.startswith('w_'):
        return 'windows'
    if base.startswith('d_') or base.startswith('dw_'):
        return 'datawindows'
    if base.startswith('nvo_'):
        return 'app'
    if base.startswith('n_'):
        return 'userobjects'
    if base.startswith('m_'):
        return 'menus'
    if base.startswith('s_') or base.startswith('str_'):
        return 'structures'
    if base.startswith('uf_') or base.startswith('f_'):
        return 'functions'
    if base.startswith('uo_'):
        return 'userobjects'
    if 'menu' in base:
        return 'menus'

    return 'app'  # default


def main():
    print(f'[*] Decompiling {EXE_PATH} ...')
    results = decompile_file(EXE_PATH, decompile_all=True)

    # Clear and recreate output
    import shutil
    if OUT_BASE.exists():
        shutil.rmtree(OUT_BASE)

    stats = {'saved': 0, 'failed': 0, 'skipped': 0}
    dir_stats = {}

    for r in results:
        if not r.success:
            print(f'  [ERR] {r.entry_name}: {r.error}')
            stats['failed'] += 1
            continue
        if not r.source or r.source.strip() == '':
            stats['skipped'] += 1
            continue

        sub_dir = classify_entry(r.entry_name)
        if sub_dir is None:
            stats['skipped'] += 1
            continue

        out_dir = OUT_BASE / sub_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        name = r.entry_name
        base = name.rsplit('.', 1)[0] if '.' in name else name

        # Special naming for known files
        if name.lower() == 'ob.exe':
            out_name = '_exe_index.ps'
        else:
            out_name = base + '.ps'

        out_file = out_dir / out_name
        out_file.write_text(r.source, encoding='utf-8')
        print(f'  {r.entry_name} -> {sub_dir}/{out_name}')
        stats['saved'] += 1
        dir_stats[sub_dir] = dir_stats.get(sub_dir, 0) + 1

    print(f'\n[*] Summary: {stats["saved"]} saved, {stats["failed"]} failed, {stats["skipped"]} skipped')
    print(f'[*] Output: {OUT_BASE}')
    print(f'\n[*] Directory breakdown:')
    for d in sorted(dir_stats.keys()):
        print(f'    {d}/: {dir_stats[d]} files')

    # Generate README
    generate_readme(dir_stats, stats)


def generate_readme(dir_stats, stats):
    total = sum(dir_stats.values())
    lines = [
        '# logistic - 源码目录',
        '',
        f'> 从 logistic.exe 反编译导出，共 {total} 个源码文件（{stats["failed"]} 失败，{stats["skipped"]} 跳过的二进制/图片资源）',
        '',
        '## 目录结构',
        '',
        '```',
        'src/',
    ]
    for d in sorted(dir_stats.keys()):
        lines.append(f'  {d}/          # {dir_stats[d]} 个文件')

    lines.extend([
        '  README.md     # 本文件',
        '```',
        '',
        '## 目录说明',
        '',
        '| 目录 | 文件数 | 说明 |',
        '|------|--------|------|',
        '| app/ | ' + str(dir_stats.get('app', 0)) + ' | 应用框架对象（Application、NVO 非可视对象、EXE 索引） |',
        '| windows/ | ' + str(dir_stats.get('windows', 0)) + ' | 窗口对象（Window） |',
        '| userobjects/ | ' + str(dir_stats.get('userobjects', 0)) + ' | 可视用户对象（User Object） |',
        '| menus/ | ' + str(dir_stats.get('menus', 0)) + ' | 菜单对象（Menu） |',
        '| functions/ | ' + str(dir_stats.get('functions', 0)) + ' | 全局函数（Function） |',
        '| datawindows/ | ' + str(dir_stats.get('datawindows', 0)) + ' | 数据窗口对象（DataWindow） |',
        '| structures/ | ' + str(dir_stats.get('structures', 0)) + ' | 结构体对象（Structure） |',
        '',
        '## 文件说明',
        '',
        '- 文件后缀 `.ps` = PowerScript 源码（反编译生成）',
        '- 原始对象名包含类型后缀（如 `w_login.win`），导出时已去掉后缀',
        '- 本项目使用 **PowerBuilder 10** 开发（pbvm100.dll）',
        '',
        '## 业务模块分析',
        '',
        '### 核心业务窗口',
        '',
        '| 窗口 | 功能 |',
        '|------|------|',
        '| w_login | 用户登录 |',
        '| w_splash | 启动画面 |',
        '| w_appmaster | MDI 主框架 |',
        '| w_logistic_instock | 入库管理 |',
        '| w_logistic_outstock | 出库管理 |',
        '| w_logistic_instock_return | 入库退货 |',
        '| w_logistic_outstock_return | 出库退货 |',
        '| w_logistic_audit | 审核管理 |',
        '| w_logistic_graph | 图表分析 |',
        '| w_orders | 订单管理 |',
        '| w_print | 打印管理 |',
        '',
        '### 系统管理窗口',
        '',
        '| 窗口 | 功能 |',
        '|------|------|',
        '| w_sys_customer | 客户管理 |',
        '| w_sys_products | 商品管理 |',
        '| w_sys_products_category | 商品分类 |',
        '| w_sys_suppliers | 供应商管理 |',
        '| w_sys_pass | 密码管理 |',
        '| w_sys_payment | 支付方式管理 |',
        '| w_users | 用户管理 |',
        '| w_sys_customer_product | 客户-商品关联 |',
        '',
        '### 查询窗口',
        '',
        '| 窗口 | 功能 |',
        '|------|------|',
        '| w_find | 通用查找 |',
        '| w_find_customers | 客户查询 |',
        '| w_find_products | 商品查询 |',
        '| w_find_products_in | 入库商品查询 |',
        '| w_find_suppliers | 供应商查询 |',
        '',
        '### 通用框架组件',
        '',
        '| 对象 | 功能 |',
        '|------|------|',
        '| appmaster | 应用框架（菜单/工具栏/状态栏管理） |',
        '| uo_toolbarutil | 工具栏管理器 |',
        '| uo_printer | 打印组件 |',
        '| uo_query_single | 单条件查询组件 |',
        '| uo_statusbar | 状态栏组件 |',
        '| uo_dwr_progressbar | 进度条组件 |',
        '| n_coolmenu | 风格化菜单 |',
        '',
        '## 依赖运行时',
        '',
        '| 文件 | 说明 |',
        '|------|------|',
        '| pbvm100.dll | PB 10 虚拟机 |',
        '| pbdwe100.dll | PB 10 DataWindow 引擎 |',
        '| pbole100.dll | PB 10 OLE 支持 |',
        '| pbshr100.dll | PB 10 共享库 |',
        '| libjcc.dll | 自定义业务库 |',
        '| libjlog.dll | 日志库 |',
        '| menures.dll | 菜单资源 DLL |',
        '| logistic.ini | 配置文件 |',
        '',
        '## 反编译信息',
        '',
        '- **工具**: pb-devkit (PbdCli 反编译引擎)',
        '- **P-Code 版本**: v100 (PB 10)',
        '- **编码**: GBK → UTF-8 转换',
        '- **导出时间**: 2026-04-15',
        '',
    ])

    OUT_BASE.mkdir(parents=True, exist_ok=True)
    index_path = OUT_BASE / 'README.md'
    index_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'\n[*] Generated {index_path}')


if __name__ == '__main__':
    main()
