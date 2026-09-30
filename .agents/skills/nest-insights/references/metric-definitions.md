# 指标口径

## 精确或高可靠

- JSONL 数量与字节：文件系统盘点。
- Root/Child Thread：SQLite `thread_spawn_edges` 对账结果。
- Turn 完成/中断：按 `turn_id` 配对 `task_started`、`task_complete`、`turn_aborted`。
- Token：每 Turn 最后一个 `last_token_usage` 快照，不累加中间快照。
- 工具：按 `call_id` 去重的 function/custom tool call。
- Patch：只统计观察到的 `patch_apply_end`，不冒充全部文件修改；文件项按每次事件中的路径数累计，同一文件跨多次 Patch 会重复计入。
- Compaction：直接统计 `context_compacted` / `compacted` 事件。

## 观察值或估算

- 活跃时长：已完成 Turn 的 `duration_ms` 之和。
- 文件/语言：仅来自 Patch 元数据中的后缀，Shell 等旁路修改可能不可见；这是事件中的文件项分布，不是唯一文件或仓库语言占比。
- 工具失败：只在结构化结果明确时判定；其余归入 unknown。

## 模型推断

- 目标类别、任务类型、结果语义、满意度、成功因素、摩擦因果和工作流建议。
- 模型推断必须携带匿名 evidence refs 和 0–1 置信度。
- 低于 0.55 或无证据的 Facet 项不得进入报告核心结论。

## 覆盖口径

报告分别展示：扫描 JSONL、SQLite Thread、Root Task、活动延后、已解析 TaskMeta、有效 Task、Facet 成功、Facet 失败、章节成功。不得用其中一个数字替代其他口径。
