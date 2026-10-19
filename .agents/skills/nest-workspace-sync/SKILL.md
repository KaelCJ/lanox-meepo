---
name: nest-workspace-sync
description: 在用户明确要求同步、一键同步或按已确认计划同步时，把当前来源的公共 Nest Workspace 资产按白名单备份、写入、校验到一个目标绝对目录，并按条件登记目标本地工作项。目标理解、版本审计和同步建议由 nest-audit-workspace 负责；普通审计、业务文件修改、Git 提交或发布不使用本 Skill。
---

# Workspace 同步

## 授权与输入

只在 Human 已明确要求同步、一键同步或按已确认计划同步时写目标。只有审计、检查版本或给建议时，不执行本 Skill 的写入流程。

目标必须是 Human 明确给出的既有绝对目录，且不能是文件系统根、来源自身或来源上下级、符号链接、junction 或其他 reparse point。

同步授权不包含业务代码、项目专属入口、Git add、commit、push、发布或外部操作。

## 唯一受管范围

- `.workspace-assistant/foundation/`：整体镜像；
- `.agents/skills/`：来源目录下所有 `nest-*` Skill，当前 18 项（含 Skill 内的脚本、引用和 Agent 配置）：
  - `nest-audit-entry`
  - `nest-audit-java`
  - `nest-audit-security-api`
  - `nest-audit-skill-body`
  - `nest-audit-text`
  - `nest-audit-workspace`
  - `nest-git-commit`
  - `nest-insights`
  - `nest-rule-entry`
  - `nest-rule-frontend`
  - `nest-rule-java`
  - `nest-rule-skill-description`
  - `nest-session-archive`
  - `nest-session-resume`
  - `nest-work-item`
  - `nest-work-report`
  - `nest-work-todo`
  - `nest-workspace-sync`
- `.claude/commands/`：来源目录下所有 `nest-*` Claude 命令入口，当前 16 项：
  - `nest-audit-entry.md`
  - `nest-audit-java.md`
  - `nest-audit-security-api.md`
  - `nest-audit-text.md`
  - `nest-audit-workspace.md`
  - `nest-git-commit.md`
  - `nest-insights.md`
  - `nest-rule-entry.md`
  - `nest-rule-frontend.md`
  - `nest-rule-java.md`
  - `nest-session-archive.md`
  - `nest-session-resume.md`
  - `nest-work-item.md`
  - `nest-work-report.md`
  - `nest-work-todo.md`
  - `nest-workspace-sync.md`
- `.codex/rules/nest-git.rules`：同步该规则文件；
- `.codex/hooks.json`：只同步命令为 `java -jar .workspace-assistant/foundation/host-hooks/codex/codex-session-start.jar` 的 `hooks.SessionStart` Hook。

这两项 Skill 没有同名 Claude 命令入口：`nest-audit-skill-body`、`nest-rule-skill-description`；**仍必须同步 Skill 本身**。以上清单记录当前来源实际项，未来新增的 `nest-*` 也自动进入脚本的全量范围，不得因清单尚未更新而只复制其中一部分。必须使用下方脚本执行，禁止手工挑选若干 Skill 后报告“同步完成”。

目标根 `AGENTS.md`、`CLAUDE.md`、README、工作项、业务代码、非 `nest-*` 资产和其他 Hook 不属于公共同步对象。

## 预检

写入前执行：

```text
python -X utf8 "<当前来源绝对路径>\.agents\skills\nest-workspace-sync\scripts\sync_workspace.py" --check --target "<目标目录绝对路径>"
```

核对 `skillInventory.source` 和 `sourceCount`：当前来源应列出上述 18 项；逐项看 `target`、`missing` 和 `extra`，不得只看状态或只数已同步的两个 Skill。清单与当前来源不一致时以实际来源为准，如实说明新增或移除项，不得裁剪脚本的全量范围。

- `CURRENT`：不写目标，报告受管内容已经一致。
- `NOT_ADOPTED`：目标没有受管资产；`PARTIAL`：有受管资产但缺少来源条目；`DIFFERENT`：有其他内容差异。先列出差异与拟覆盖、删除的受管路径，再按用户同步授权继续。
- 目标受管路径有未提交的本地修改或无法判断所有权的定制时，没有 Human 明确处理决定就停止覆盖或删除并列出路径；普通内容差异不要求额外的发布步骤。
- 检查失败或目标状态在计划后变化：停止并报告。

## 执行

Agent 临时、备份和可丢弃验证产物使用当前来源工作空间根目录下的 `.tmp/<task-id>/`。备份根必须位于该任务自己的子目录，不得直接使用 `.tmp/` 根目录，不得位于目标内部，也不得与目标重叠。

执行：

```text
python -X utf8 "<当前来源绝对路径>\.agents\skills\nest-workspace-sync\scripts\sync_workspace.py" --target "<目标目录绝对路径>" --backup-root "<本次备份根绝对路径>"
```

脚本负责：

- 冻结来源和目标受管文件清单；
- 报告来源、目标 Skill 名称、数量及缺失项；
- 保存同步计划；
- 在覆盖或删除前备份目标受影响资产和完整 `hooks.json`；
- 新增、覆盖和删除白名单资产；
- 结构化合并受管 SessionStart Hook，保留目标其他 Hook；
- 检查来源和目标在执行期间没有并发变化；
- 逐文件 SHA-256 对账；
- 失败时尝试恢复目标并报告真实回滚状态。

`__pycache__`、`.pyc` 和 `.pyo` 不进入受管文件清单、备份或同步结果。

## 同步后复查

再次执行 `--check`。只有返回 `CURRENT`，且 `skillInventory.source` 与 `target` 逐项一致、`missing` 和 `extra` 都为空，才能报告全部来源 Skill 及其他受管公共资产已同步；不能只凭执行命令成功或仅有两项 Skill 到位就报告完成。执行结果中的 `skillInventoryBefore` 和 `skillInventoryAfter` 也须列出实际来源与目标数量及名称。

脚本返回 `synchronized_unrecorded` 时，只能报告“同步已验证、结果证据写入失败”，不能当作完整闭环。

## 目标工作项登记

受管资产对账成功后，先读取目标根实际存在的 `README.md`、`AGENTS.md`、`CLAUDE.md` 和工作项索引，不从来源复制项目事实：

- `current.json`、`archive.json` 与 `index.schema.json` 齐全时，先使用目标 `nest-work-item/scripts/work_item_index.py validate` 校验；用户本次明确要求登记或创建目标工作项时，再调用目标 `$nest-work-item`。
- 用户本次明确要求创建目标工作项，且两份 JSON、旧索引 `README.md` 和既有工作项目录全部不存在时，可使用目标 `work_item_index.py init` 初始化索引，再创建首项。根 `AGENTS.md` 尚未建立不阻止真正全新空间的首项建档；已有入口仍须先读。
- 用户没有要求目标工作项动作，或目标存在部分 JSON、旧索引、既有工作项目录但缺少完整索引时，不初始化、不复制来源工作项、不猜测修复，只报告未登记原因。

登记前使用目标索引脚本以“公共工作空间同步”“Workspace”“公共”“同步”“初始化”等窄词跨两份 JSON 查询并按职责查重。已有等价项时复用且不改写；没有等价项时按目标 `current.json.nextNumber` 和目标规则创建一次同步采用工作项；多个候选无法判断时停止登记。

## 最终报告

报告来源与目标绝对路径、同步前状态、来源与目标的 Skill 名称及数量、同步前缺失/多余的 Skill、实际新增/覆盖/删除、保留内容、备份路径、逐文件对账结果、同步后状态，以及目标工作项的复用、创建或未登记原因。

不得执行 Git add、commit、push、发布或受管范围之外的目标项目动作。

## 级联语义

本 Skill 会作为 `nest-*` 公共资产进入目标。下游空间可以继续作为来源同步到其他空间，但只能声明“与当前来源受管资产一致”；判断与权威空间的实际差异应从 `nest-agent` 空间运行 `$nest-audit-workspace`。
