# 数据契约

## 层次

1. Inventory：只记录目录文件数、字节数、时间边界和 SQLite/文件系统对账。
2. TaskMeta：以 Root Task 为单位，包含 canonical Turn、确定性计数、匿名别名和质量标记。
3. Facet Packet：TaskMeta 的最小化脱敏语义输入，不含原始工具输出或系统上下文。
4. Task Facet：目标、任务类型、结果、成功、摩擦、纠正、交互模式、证据引用和置信度。
5. Report Model：聚合事实、章节、覆盖率、匿名任务索引和 manifest。

## 身份与缓存

- Task 匿名别名：`T-` 加 Root Thread ID 的单向摘要前缀。
- Evidence：`T-xxxx/U01`、`T-xxxx/F01` 等匿名引用。
- TaskMeta 缓存键：关联 JSONL 的相对身份、size、mtime_ns、解析器版本。
- Facet 缓存键：Packet 摘要、Facet schema、Prompt 版本和模型选择。报告加载全部仍匹配当前键的成功缓存，每轮只限制新增 Facet 数，不把历史成功 Facet 丢出报告；上一轮已尝试但未形成有效缓存的任务优先重试。
- Chapter 缓存键：聚合摘要、章节名、Prompt 版本和模型选择。

缓存状态只能是 `success`、`failed`、`invalid` 或 `deferred-live`。失败结果不得覆盖最后成功结果。Facet 与分块摘要中的叙事字段有长度上限，防止模型把当前分析过程或 Prompt 复述进任务事实。

## 兼容原则

- 未知事件计数并进入 manifest。
- SQLite 只承担索引、拓扑和对账，不替代 JSONL 语义事实。
- 相同消息的 `event_msg` 与 `response_item` 表示只计一次。
- 子 Agent Thread 的计数和最终摘要折叠回 Root Task，不作为独立用户任务。
