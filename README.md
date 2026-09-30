# Nest

> 面向 Claude Code 与 Codex 的可复用人机协作工作流工具包。

Nest 把需求、执行、审计、工作项和 Session 整理成可复制的协作流程，帮助团队把“会话里的临时约定”变成可检查、可复用的项目资产。

## 当前状态

项目处于早期公开准备阶段。工作流资产正在持续整理，接口和目录结构可能变化；请先在非关键项目中试用，并通过 Issue 报告不一致之处。

## 能做什么

- **工作项管理**：创建、继续、更新和归档带有事实记录的工作项。
- **代码审计**：提供 Java、API 安全和文本审计入口。
- **工程规则**：为 Java、前端和双宿主入口维护可复用规则。
- **会话管理**：辅助恢复、归档和整理人机协作过程。
- **工作区同步**：把公共协作资产同步到目标目录。

## 快速开始

### 前置条件

- Git
- Python 3.10+
- Claude Code 或 Codex（取决于你要使用的宿主）

### 安装

在目标项目根目录执行：

```bash
git clone https://github.com/KaelCJ/lanox-meepo.git
cp -R lanox-meepo/.agents lanox-meepo/.claude lanox-meepo/.codex .
```

Windows PowerShell 可使用：

```powershell
git clone https://github.com/KaelCJ/lanox-meepo.git
Copy-Item -Recurse lanox-meepo/.agents,lanox-meepo/.claude,lanox-meepo/.codex .
```

然后在 Claude Code 中调用相应入口，例如：

```text
使用 $nest-work-item 创建一个工作项
```

### 验证

检查工作项工具是否可执行：

```bash
python .agents/skills/nest-work-item/scripts/work_item_index.py --help
```

## 目录说明

```text
.agents/skills/   可复用 Skills、参考资料和验证脚本
.claude/commands/ Claude Code 命令入口
.codex/           Codex 规则与 Hook 配置
.workspace-assistant/  宿主辅助资产与工作项数据
```

## 使用边界

- 这是协作流程工具包，不是自动替代人工决策的系统。
- 审计输出需要由具备上下文的人员复核，不能当作安全或合规保证。
- 不要把密钥、个人数据、客户代码或敏感会话内容提交到公开仓库。
- 二进制宿主资产的再分发许可仍需单独确认。

## 路线图

- [ ] 完成一个端到端 Demo 和 90 秒演示
- [ ] 建立跨平台安装与验证脚本
- [ ] 补充贡献指南、Issue 模板和 CI
- [ ] 发布首个稳定的 `v0.1.0`
- [ ] 根据真实用户反馈稳定工作流契约

## 参与贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。Bug、安全问题和改进建议分别按 [SECURITY.md](SECURITY.md) 与 Issue 指引提交。

## 许可证

本项目采用 [MIT License](LICENSE)。第三方资产仍以其各自许可证为准。
