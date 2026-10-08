# Nest

> 面向 Claude Code 与 Codex 的可复用人机协作工作流工具包。

Nest 把 Agent 的代码产出约束、需求、执行、审计、工作项和 Session 整理成可复用的协作流程，帮助团队把“会话里的临时约定”变成可检查的项目资产。规则可以指导 Agent 如何实现和验证代码，但不能代替宿主加载验证、测试或人工复核。

[5 分钟 Quickstart](docs/quickstart.md) · [公开范围与发布门禁](docs/public-scope.md) · [第三方资产登记](THIRD_PARTY_NOTICES.md) · [贡献指南](CONTRIBUTING.md)

## 为什么需要 Nest

普通 AI 编程会话往往能完成一次修改，却很难稳定回答：需求是什么、谁确认过、哪些动作真的发生了、审计覆盖了什么、下一个 Session 如何继续。Nest 将这些协作事实放回可检查的工作项、规则和验证入口中。

它不替代人的决定，也不把模型输出当作安全或合规证明；它的目标是让人和 Agent 更容易共同完成工作并留下可复核证据。

## 能做什么

第一阶段聚焦三个工作流：

- **工作项生命周期**：创建、继续、更新和归档带有事实记录的工作项；新编号使用 Python 原生 UUID4，旧编号继续可读。
- **入口与规则治理**：维护 `AGENTS.md` / `CLAUDE.md` 的单一正文和宿主入口关系。
- **审计辅助**：提供 Java、API 安全和文本审计入口，区分证据、未验证范围和人工决定。

仓库中还包含 Session 管理和 Insights 等实验性资产；Java/API 安全审计及组织专属规则也仍需内容或授权复核。它们不在首批离线文本白名单中，不应默认视为所有用户都能直接安装的功能。Workspace Sync 已移除，Workspace 采用审计只提供只读报告和人工适配建议。

## 支持矩阵

| 宿主 | 状态 | 当前建议 |
|---|---|---|
| Claude Code | Alpha | 仅试用离线 Quickstart 的文本白名单；真实宿主端到端加载尚待验证 |
| Codex | Alpha | SessionStart 接线已改为 Python，但未纳入离线白名单，也未经真实宿主验证；旧 JAR 仍在历史中 |
| 其他 Agent 宿主 | 未承诺 | 暂无稳定适配或发布包 |

## 快速开始

### 前置条件

- Git
- Python 3.10+（工作项新编号不需要 Java）
- Claude Code 或 Codex（取决于你要使用的宿主）

### 安装和验证

当前仅提供 [离线 Quickstart](docs/quickstart.md)：从已获准使用的本地源向干净目标复制首批文本白名单资产，并检查实际复制内容。**不要把整仓克隆当作公开安装方式**：历史中仍有三枚已移除的 JAR，当前树也有待隔离的内部工作区记录。最小静态检查为：

```bash
python -m compileall -q .agents/skills tools
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --root . --exclude .claude/worktrees
```

发布候选还需对实际 Git 树运行 `python tools/validate_text_public_tree.py --ref HEAD`；当前树包含内部记录、待审查 Skill 和待授权二进制，**预期被阻止**。该路径预检不能代替内容、许可证或历史检查。

如需手动验证宿主加载，在离线目标项目创建它自己的入口配对后，开启新的 Claude Code 会话调用只读入口审计，例如：

```text
使用 /nest-audit-entry 检查当前项目的 AGENTS.md / CLAUDE.md 配对；只读，不修改文件。
```

工作项新建使用 Python UUID4，不依赖 JAR；[离线 Quickstart](docs/quickstart.md) 提供本地复制和静态验证示例，但真实 Claude Code/Codex 宿主端到端验证仍待完成。两枚 SessionStart JAR 已从当前工作树移除，Codex 接线改用 Python，Claude Code 暂无项目级自动接线；JAR 仍在 Git 历史中且授权未确认，因此不能以整仓克隆作为公开安装路径。

## 目录说明

```text
.agents/skills/   可复用 Skills、参考资料和验证脚本
.claude/commands/ Claude Code 命令入口
.codex/           Codex 规则与 Hook 配置（部分接线待审查）
docs/             面向用户的 Quickstart、公开范围和资产登记
examples/         脱敏、人工构造的使用示例
tools/            公开发布前的标准库验证脚本
.workspace-assistant/  工作区辅助资产（并非全部适合公开发布）
```

## 使用边界

- 这是协作流程工具包，不是自动替代人工决策的系统。
- 审计输出需要由具备上下文的人员复核，不能当作安全或合规保证。
- 不要把密钥、个人数据、客户代码或敏感会话内容提交到公开仓库。
- 未确认来源和再分发许可的二进制、内部工作区数据和组织专属规则，不应作为公开运行依赖；二进制授权状态以 [第三方资产登记](THIRD_PARTY_NOTICES.md) 为准。
- 发布前请阅读 [docs/public-scope.md](docs/public-scope.md)。

## 路线图

- [x] 建立公开范围和离线 5 分钟 Quickstart
- [x] 添加脱敏最小工作流示例
- [ ] 处理历史中的待授权二进制（取得许可或另行批准历史清理），并通过发布门禁
- [ ] 隔离内部工作项、私有 Hook 和组织专属规则
- [ ] 验证可公开获取的安装渠道和实际发布载荷
- [ ] 建立跨平台安装与 CI 验证
- [ ] 发布首个稳定的 `v0.1.0`
- [ ] 根据真实用户反馈稳定工作流契约

## 参与贡献

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。Bug、安全问题和改进建议分别按 [SECURITY.md](SECURITY.md) 与 Issue 指引提交。

## 许可证

本项目根目录文本资产拟采用 [MIT License](LICENSE)。第三方资产、组织专属内容和未确认来源的二进制不自动受该声明覆盖；二进制的审核状态见 [第三方资产登记](THIRD_PARTY_NOTICES.md)，发布前请以 [公开范围说明](docs/public-scope.md) 为准。
