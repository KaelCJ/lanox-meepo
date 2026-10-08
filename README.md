# Nest

> 面向 Claude Code 与 Codex 的可复用人机协作工作流工具包。

Nest 把 Agent 的代码产出约束、需求、执行、审计、工作项和 Session 整理成可复用的协作流程，帮助团队把“会话里的临时约定”变成可检查的项目资产。规则可以指导 Agent 如何实现和验证代码，但不能代替宿主加载验证、测试或人工复核。

[最小工作流示例](examples/minimal-workflow/README.md) · [公开范围说明](docs/public-scope.md) · [历史二进制记录](THIRD_PARTY_NOTICES.md) · [贡献指南](CONTRIBUTING.md)

## 为什么需要 Nest

普通 AI 编程会话往往能完成一次修改，却很难稳定回答：需求是什么、谁确认过、哪些动作真的发生了、审计覆盖了什么、下一个 Session 如何继续。Nest 将这些协作事实放回可检查的工作项、规则和验证入口中。

它不替代人的决定，也不把模型输出当作安全或合规证明；它的目标是让人和 Agent 更容易共同完成工作并留下可复核证据。

## 能做什么

第一阶段聚焦三个工作流：

- **工作项生命周期**：创建、继续、更新和归档带有事实记录的工作项；新编号使用 Python 原生 UUID4，旧编号继续可读。
- **入口与规则治理**：维护 `AGENTS.md` / `CLAUDE.md` 的单一正文和宿主入口关系。
- **审计辅助**：提供 Java、API 安全和文本审计入口，区分证据、未验证范围和人工决定。

仓库中还包含 Session 管理和 Insights 等需要继续验证的资产；Java/API 安全审计及组织专属规则也需要按实际内容核对适用性。Workspace Sync 已移除，Workspace 采用审计只提供只读报告和人工适配建议。

## 支持矩阵

| 宿主 | 状态 | 当前建议 |
|---|---|---|
| Claude Code | Alpha | 仓库已有 Skills 和命令入口；目标项目的真实宿主流程尚待验证 |
| Codex | Alpha | 已有文本规则和 Python SessionStart 接线；真实宿主流程尚待验证 |
| 其他 Agent 宿主 | 未承诺 | 暂无稳定适配或发布包 |

## 当前使用与验证

项目仍在完善工作流本身，不提供自动安装器或已验证的跨项目安装承诺。仓库内的 `.agents/skills/` 与 `.claude/commands/` 是现有入口；[最小示例](examples/minimal-workflow/README.md)展示如何区分需求、约束、已执行动作和未验证范围。

在仓库根目录可运行本地检查：

```bash
python -m compileall -q .agents/skills tools
python -m unittest discover -s tools -p 'test_*.py'
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --root . --exclude .claude/worktrees
```

这些检查只能证明脚本与入口文件的局部性质，不能证明 Claude Code/Codex 在目标项目中加载并遵守规则。真实宿主工作流仍待验证；`AGENTS.md` 是本仓库自身的规则，不应直接复制成其他项目的规则。

## 目录说明

```text
.agents/skills/   可复用 Skills、参考资料和验证脚本
.claude/commands/ Claude Code 命令入口
.codex/           Codex 规则与 Hook 配置（部分接线待审查）
docs/             公开范围说明
examples/         脱敏、人工构造的使用示例
tools/            当前工作流的脚本与局部测试
.workspace-assistant/  工作区辅助资产（并非全部适合公开发布）
```

## 使用边界

- 这是协作流程工具包，不是自动替代人工决策的系统。
- 审计输出需要由具备上下文的人员复核，不能当作安全或合规保证。
- 不要把密钥、个人数据、客户代码或敏感会话内容提交到公开仓库。
- 未确认来源和再分发许可的二进制、内部工作区数据和组织专属规则，不应作为公开运行依赖；历史 JAR 的已知情况见 [历史二进制记录](THIRD_PARTY_NOTICES.md)。
- 发布前请阅读 [docs/public-scope.md](docs/public-scope.md)。

## 路线图

- [x] 建立项目定位与脱敏的最小工作流示例
- [x] 工作项新编号改为 Python UUID4，保留旧编号读取
- [ ] 在真实 Claude Code/Codex 宿主中验证规则、工作项和审计入口
- [ ] 根据真实使用反馈稳定工作流与代码产出约束
- [ ] 在功能验证后决定跨项目安装方式
- [ ] 单独审查已跟踪的内部工作项与 Git 历史中的旧二进制
- [ ] 发布首个稳定的 `v0.1.0`

## 参与贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。Bug、安全问题和改进建议分别按 [SECURITY.md](SECURITY.md) 与 Issue 指引提交。

## 许可证

本项目根目录文本资产拟采用 [MIT License](LICENSE)。第三方资产、组织专属内容和未确认来源的二进制不自动受该声明覆盖；历史 JAR 的情况见 [历史二进制记录](THIRD_PARTY_NOTICES.md)。
