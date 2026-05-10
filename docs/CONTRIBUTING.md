# Contributing to PB DevKit

感谢你对 PB DevKit 的关注！本指南将帮助你更好地参与项目贡献。

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-repo/pb-devkit.git
cd pb-devkit

# 创建虚拟环境 (可选)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e .
pip install pytest ruff mypy
```

## 开发规范

### 代码风格
- 使用 `ruff` 进行代码检查: `ruff check src/`
- 遵循 PEP 8，行长限制 100 字符
- 使用 Type Hints 增强代码可读性

### 提交规范
- 使用英文提交信息
- 提交信息格式: `type(scope): description`
- 类型: `feat`, `fix`, `docs`, `refactor`, `test`

```bash
# 示例
git commit -m "feat(dw): add SQL extraction for nested queries"
```

### 测试要求
- 新功能必须包含测试用例
- 运行测试: `python -m pytest tests/ -v`
- 确保 68 个测试全部通过后再提交

## 项目结构

```
pb-devkit/
├── src/pb_devkit/       # 核心代码
│   ├── commands/        # CLI 命令
│   ├── parsers/         # 解析器模块
│   └── *.py             # 核心引擎
├── tests/               # 测试用例
├── docs/                # 文档
└── vscode-extension/    # VS Code 插件
```

## 常见任务

### 添加新命令
1. 在 `src/pb_devkit/commands/` 创建 `newcmd.py`
2. 实现 `register()` 和 `run()` 函数
3. 在 `cli.py` 注册命令

### 添加解析器
1. 在 `src/pb_devkit/parsers/` 创建解析器类
2. 继承基类并实现必要接口
3. 在 `__init__.py` 导出

## 问题反馈

- Bug 报告: GitHub Issues
- 功能建议: GitHub Discussions
- 文档纠错: 直接提交 PR

---

*感谢你的贡献！*