# Contributing to PB DevKit

感谢你对 PB DevKit 的关注！本指南将帮助你更好地参与项目贡献。

## 项目版本

| 版本 | 技术栈 | 状态 |
|------|--------|------|
| **pb-devkit-2.x** (推荐) | Rust + Tauri + Angular | 活跃开发 |
| pb-devkit-1.x | Python | 维护中 (不再活跃) |

---

## 开发环境设置

### 2.x 版本 (Rust)

```bash
# 克隆仓库
git clone https://github.com/sugitter/pb-devkit.git
cd pb-devkit

# 安装 Rust (如未安装)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 开发 CLI
cd pb-devkit-2.x/pb-devkit-cli
cargo build

# 开发 Desktop GUI
cd pb-devkit-desktop
npm install
npm run tauri dev

# 运行测试
cargo test --workspace
```

### 1.x 版本 (Python - 遗留)

```bash
# 克隆仓库
git clone https://github.com/sugitter/pb-devkit.git
cd pb-devkit

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e .
pip install pytest ruff mypy

# 运行测试
python -m pytest tests/ -v
```

---

## 开发规范

### 2.x (Rust)

- 使用 `cargo clippy` 进行代码检查
- 遵循 Rust 官方代码风格
- 使用 `cargo fmt` 格式化代码
- 新功能必须包含单元测试

```bash
# 代码检查
cargo clippy --workspace

# 格式化
cargo fmt --all

# 测试
cargo test --workspace
```

### 1.x (Python - 遗留)

- 使用 `ruff` 进行代码检查: `ruff check src/`
- 遵循 PEP 8，行长限制 100 字符
- 使用 Type Hints 增强代码可读性

---

## 提交规范

使用英文提交信息，格式: `type(scope): description`

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `refactor` | 代码重构 |
| `perf` | 性能优化 |
| `test` | 测试相关 |

```bash
# 示例
git commit -m "feat(cli): add progress bar for batch export"
git commit -m "docs: update v2.1 roadmap"
git commit -m "perf(search): implement parallel search with rayon"
```

---

## 项目结构

```
pb-devkit/
├── pb-devkit-2.x/              # Rust 版本 (推荐)
│   ├── pb-devkit-core/         # 核心解析库
│   │   └── src/
│   │       ├── pbl.rs          # PBL 解析
│   │       ├── pe.rs           # PE 分析
│   │       ├── dw.rs           # DataWindow 分析
│   │       ├── decompile.rs    # 反编译
│   │       └── project.rs      # 项目检测
│   ├── pb-devkit-cli/          # CLI 工具 (20 命令)
│   └── pb-devkit-desktop/      # Tauri + Angular GUI
│       └── src/app/
│           ├── components/     # 10 个 UI 组件
│           └── services/       # 后端服务
├── pb-devkit-1.x/              # Python 版本 (遗留)
│   ├── src/pb_devkit/
│   │   ├── commands/           # CLI 命令
│   │   └── parsers/            # 解析器
│   └── tests/
├── docs/                       # 文档
│   ├── SKILL.md               # Agent Skill
│   ├── AGENT_SKILL.md         # 项目级 Skill
│   └── ...
└── ...
```

---

## 常见任务

### 添加新 CLI 命令 (2.x)

1. 在 `pb-devkit-cli/src/commands/` 创建 `newcmd.rs`
2. 实现命令结构体和 `run()` 方法
3. 在 `main.rs` 注册命令

### 添加新 UI 组件 (2.x)

1. 在 `pb-devkit-desktop/src/app/components/` 创建组件
2. 使用 Angular 17+ 独立组件语法
3. 在 `app.component.ts` 注册面板

---

## 问题反馈

- Bug 报告: [GitHub Issues](https://github.com/sugitter/pb-devkit/issues)
- 功能建议: [GitHub Discussions](https://github.com/sugitter/pb-devkit/discussions)
- 文档纠错: 直接提交 PR

---

*感谢你的贡献！*