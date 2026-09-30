# AGENTS.md

## 项目定位

这是 `lanox-meepo`：面向 Claude Code 与 Codex 的可复用人机协作工作流工具包。项目通过 Skills、Rules、Commands、参考资料和验证脚本，把需求、执行、审计、工作项和 Session 管理整理为可复制的协作流程。

## 入口与职责

- `AGENTS.md`：本项目跨任务稳定的 Agent 工作规则；它是共享正文的唯一所有者。
- `CLAUDE.md`：只能是 `@AGENTS.md` 的纯导入包装，不得复制或追加正文。
- `README.md`：面向 GitHub 用户的项目说明、安装方式、能力介绍和公开边界；不要把 Agent 内部规则写入 README。
- `.agents/skills/`：Skills 正文、参考资料、模板和验证脚本。
- `.claude/commands/`：Claude Code 的命令入口；命令应与对应 Skill 的职责保持一致。
- `.codex/`：Codex 宿主的规则与 Hook 配置。
- `.workspace-assistant/10-工作项/`：工作项索引和工作项事实记录；动态进展写入工作项，不写入本入口。

## 工作原则

1. 先理解用户目标和当前仓库事实，再选择最小适用的 Skill；不要因为看到相似关键词就扩大范围。
2. 入口规则、Skill 正文、工作项记录和用户 README 各自拥有自己的事实边界，不互相复制或替代。
3. 修改规则或流程时优先复用现有 Skill、模板和验证脚本；不要为同一职责新增平行机制。
4. 不把计划、局部检查或推测写成已完成事实；报告验证命令和结果，并明确未覆盖范围。
5. 保护用户已有修改；不擅自提交、推送、发布、删除历史或改写其他会话资产。
6. 不将密钥、个人数据、客户代码、真实会话转储或来源不明的二进制加入公开仓库。
7. 这是开源项目，增长应依靠真实可复现的用户价值；不得买星、刷星、互刷、机器人批量互动或伪造指标。

## 常用验证

在仓库根目录执行：

```bash
python -m compileall -q .agents/skills
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --root .
python .agents/skills/nest-work-item/scripts/work_item_index.py --root .workspace-assistant/10-工作项 validate
```

入口校验通过只说明 `AGENTS.md` / `CLAUDE.md` 的机械关系正确，不代表宿主一定已加载或执行全部规则。

## 修改边界

- 修改共享入口正文时只修改 `AGENTS.md`，并保持 `CLAUDE.md` 内容严格为 `@AGENTS.md`。
- 修改工作项时遵循 `.agents/skills/nest-work-item/SKILL.md` 及其方法文件，不在根入口追加过程流水。
- 修改 Skill、Rule 或 Command 时先读取其对应的 `SKILL.md` 或命令说明，再进行最小范围变更。
- 涉及公开发布时，先检查许可证、第三方资产、缓存、敏感信息和二进制再执行 Git 操作。
