# 逐 API 深审产物规范

## 目录

- [运行目录](#运行目录)
- [隔离规则](#隔离规则)
- [每 API 必需产物](#每-api-必需产物)
- [结论 Schema](#结论-schema)
- [汇总规则](#汇总规则)

## 运行目录

每次审计使用独立的 `<audit-root>/.api-security-audit/<run-id>/`，不得覆盖其他 run：

```text
<run-id>/
├── manifest.json
├── ledger.json
├── macro/
│   ├── api-inventory.csv
│   ├── protection-profiles.md
│   ├── global-findings.md
│   └── domain-index.md
├── shared/
│   ├── domains/
│   ├── flows/<flow-id>/
│   └── variants/<variant-id>/
├── apis/<api-dir>/
│   ├── agent/brief.md
│   ├── agent/result.json
│   ├── contract.md
│   ├── protection-chain.md
│   ├── call-graph.md
│   ├── sequence.mmd
│   ├── data-model.md
│   ├── data-model.mmd
│   ├── findings.md
│   ├── unconfirmed.md
│   ├── review.md
│   └── verdict.json
└── findings/
    ├── prioritized-findings.md
    └── remediation-plan.md
```

`manifest.json` 是 G1 冻结分母；`ledger.json` 记录 run、规则版本、G1-G5 状态、批次、Agent、API 状态和产物校验。`api-dir` 必须含稳定 API ID，目录名不能只依赖可变描述或行号。

## 隔离规则

1. G2 Agent 只读取自己的 `agent/brief.md`、G1 宏观索引、相关源码和本 Skill references；不得读取其他 API 的 `findings.md`、`verdict.json` 或 reviewer 结论。
2. G1 的风险假设可以作为待验证问题，不能作为 G2 的既定漏洞；G2 必须重新确认当前 API 的实际路径、分支、主体、对象和 sink。
3. 可复用的实体/组件/域模型放在 `shared/`，API 目录只记录当前 API 实际触及的字段和关系，避免复制后漂移。
4. G3 横向 Agent 只有在 G2 全部回收后才能读取各 API 结果；横向结论必须列出参与 API ID，不得覆盖任一 API 的原始证据。
5. Agent 异常退出、返回不完整或与 reviewer 冲突时，状态为 `blocked` 或 `needs_review`，不能降级为 `未确认后通过`。

## 每 API 必需产物

- `contract.md`：方法、完整路径、装配条件、所有输入载体和响应序列化；列出客户端可控的主体、目标对象、状态、金额、权限和动态字段。
- `protection-chain.md`：从外部入口到响应的实际链；每个组件要有注册/匹配证据、顺序、身份来源、失败行为和旁路。
- `call-graph.md`：包含实际实现、正常/异常/fallback、缓存、异步、重试、二次查询、事务、响应映射和最终 source/sink；每个关键节点带文件和行号。
- `sequence.mmd`：用 Mermaid `sequenceDiagram`，在无法解析的外部实现处标注 `unconfirmed`，不可画成假定安全的黑盒成功。
- `data-model.md`：用表格写主体、目标对象、owner/tenant、敏感字段、状态转换和数据来源；明确哪些关系已验证、哪些缺失。
- `data-model.mmd`：用 Mermaid `erDiagram` 或简化关系图，只画当前 API 相关实体；不要为了图形完整而猜字段关系。
- `findings.md`：事实、推断、成立前提和用户决定分开；每条 finding 使用唯一 ID，并引用证据位置。
- `unconfirmed.md`：写明缺失事实、影响的安全目标、为什么阻止 `通过` 或严重度判断，以及需要补充的证据。
- `review.md`：G4 reviewer 的独立判断、反证路径、差异和最终处理。

## 结论 Schema

`verdict.json` 至少包含以下字段；状态值只能使用规定枚举：

```json
{
  "api_id": "稳定 API ID",
  "status": "pending|in_progress|complete|blocked|needs_review",
  "local_verdict": "通过|失败|未确认|不适用",
  "global_baseline": "通过|失败|未确认|不适用",
  "release_verdict": "通过|失败|未确认",
  "severity": "严重|高|中|低|无",
  "priority": "P0|P1|P2|P3|无",
  "confidence": "高|中|低",
  "finding_ids": ["F-..."],
  "unconfirmed_fact_ids": ["U-..."],
  "review": {"required": true, "status": "pending|complete|conflict"}
}
```

`local_verdict` 只回答当前 API 自身逻辑是否成立；`global_baseline` 使用同一四态枚举，表示全局日志/CORS/配置/部署问题对当前 API 的实际影响；`release_verdict` 才用于发布门禁。全局问题不能伪装成 API 自身 finding，也不能从 API 目录中删除，只能通过引用关联。

每条 finding 至少包含：`finding_id`、`scope(local|shared|global|deployment)`、`severity`、`priority`、受影响 API ID、入口/参数、保护链、调用图、source/sink 或副作用、影响、成立前提、证据文件/行号、修复方向、置信度和 reviewer 状态。

## 汇总规则

1. 主矩阵从 `manifest.json` 左连接每个 API 的 `verdict.json`，任何缺失结果都显示为 `blocked`，不得丢行。
2. 同一全局 finding 可关联多个 API，但统计时区分“受影响 API 数”与“API 自身失败数”。
3. P0/P1、认证/会话、凭据、支付/充值、管理/审核、文件/OSS、拟判通过的 API 必须有 reviewer；没有 reviewer 的结果不得进入“证据闭环”。
4. 总体发布结论按 `release_verdict`、跨 API finding 和未解决冲突汇总；同时单独报告局部失败、全局基线问题、跨 API 问题和未确认事实。
5. `通过` 必须有端到端证据和反证记录；“未发现问题”、缺少下游代码、内部使用假设、管理员假设或用户未明确确认均不能转为通过。
