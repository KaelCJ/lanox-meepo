# Java 审计规则目录

> 本目录是 `nest-audit-java` 通用模式与异常专项模式的内部规则真源。执行审计时完整加载本文件，先按上层 `SKILL.md` 确定模式，再按触发条件读取对应规则族；目标项目启用的 Java Rule 只作为项目附加约束，不能替代本目录或细则正文。

## 使用顺序

读取、模式选择、候选判定和报告格式遵循上层 `SKILL.md`；异常专项模式还须读取[异常专项审计方法](exception-audit.md)。本目录只提供规则导航、默认元数据和未目录化发现的归属边界。逐条细则仍须按触发条件完整读取，不能以目录行或规则 ID 代替证据。

## 通用规则目录

| ruleId | 类型 | 质量属性 | 默认级别 | 主要触发条件 | 细则 |
|---|---|---|---|---|---|
| NJA-001 | Bug | 可靠性 | 重大 | 删除、精简、内联、改签名或替换实现 | [行为变化缺少等价证据](NJA-001-observable-behavior-regression.md) |
| NJA-002 | Code Smell | 可维护性 | 普通 | 新增或扩大 Processor、Helper、Service、Adapter、包装层 | [无价值间接层](NJA-002-unnecessary-indirection.md) |
| NJA-003 | Code Smell | 可维护性 | 普通 | 新增 Interface、Factory、Strategy、Provider、Plugin、配置开关 | [无当前依据的扩展点](NJA-003-speculative-extension-point.md) |
| NJA-004 | Code Smell | 可维护性、可靠性 | 重大 | 同语义基础设施形成多个运行真源，或采用方违反已确认的组件装配契约 | [重复或绕过基础设施能力](NJA-004-duplicate-infrastructure-capability.md) |
| NJA-005 | Code Smell | 可维护性 | 重大 | 改动包含目标外文件、依赖、配置、迁移或兼容设计 | [未授权范围扩张](NJA-005-unauthorized-scope-expansion.md) |
| NJA-006 | Code Smell | 可靠性、可维护性 | 重大 | 用编译、局部检查、Mock 或旧证据宣称行为通过 | [验证证据与结论不匹配](NJA-006-invalid-verification-evidence.md) |
| NJA-007 | Code Smell | 可维护性、可靠性 | 重大 | 修改生成代码或同时保留生成真源和人工产物 | [破坏生成代码所有权](NJA-007-generated-source-ownership.md) |
| NJA-008 | Code Smell | 可维护性 | 普通 | 执行类拥有独立契约，或分层职责被平铺到根 package | [Java 类型与分层所有权错位](NJA-008-type-ownership-mismatch.md) |
| NJA-009 | Bug | 可靠性、安全性 | 重大 | 同步 HTTP 响应泄露底层异常，或状态码、错误信封与日志行为违反已确认契约 | [同步 HTTP 异常被包装为普通响应](NJA-009-synchronous-http-error-envelope.md) |
| NJA-010 | Code Smell | 可维护性、安全性 | 重大 | 客户端可提交服务器拥有的上下文字段，或 Controller 违反目标项目已启用的上下文传递规则 | [Controller 污染业务入参](NJA-010-controller-context-parameter-leak.md) |
| NJA-011 | Code Smell | 可靠性、可维护性 | 普通 | 新增或保留 quota、限流、重试、fallback、兼容或保护分支 | [无当前依据的运行限制或保护分支](NJA-011-speculative-runtime-guard.md) |
| NJA-012 | Code Smell | 可靠性、可维护性 | 重大 | 外部协议实现相对当前版本权威契约存在影响对端或消费者的真实 wire 差异 | [外部 API 契约被拍平或凭调用方猜测](NJA-012-external-api-contract-flattening.md) |
| NJA-013 | Code Smell | 可维护性、可靠性 | 普通 | 新增或修改方法把 `IOException` 等受检异常扩散给没有恢复或协议责任的调用方 | [非必要受检异常扩散](NJA-013-unnecessary-checked-exception-propagation.md) |
| NJA-014 | Code Smell | 可维护性、可靠性 | 普通 | 新增或保留参数空值、不可能状态或瞬时状态预检 | [无真实语义的防御检查](NJA-014-meaningless-defensive-check.md) |
| NJA-015 | Code Smell | 可维护性、可靠性 | 普通 | 目标项目明确要求 `@Slf4j`，但新增或保留等价手写 SLF4J Logger 字段 | [手写日志声明未统一为 `@Slf4j`](NJA-015-manual-logger-declaration.md) |
| NJA-016 | Bug | 可靠性 | 重大 | 资源创建后、所有权交接前仅在部分异常路径清理，或清理异常覆盖原异常 | [资源所有权交接前的异常路径泄漏](NJA-016-resource-handoff-exception-leak.md) |
| NJA-018 | Code Smell | 可维护性、可靠性 | 普通 | Deprecated：不再触发，异常捕获与传播改由本 Skill 的 `NJX-*` 异常专项模式审计 | [已迁移至 Java 异常专项审计](NJA-018-valueless-catch-and-throw.md) |
| NJA-019 | Code Smell | 可靠性、可维护性 | 重大 | 启用 `DwException` 统一异常约束的项目边界主动传播其他异常 | [主动异常未统一为 `DwException`](NJA-019-dwexception-boundary.md) |
| NJA-020 | Code Smell | 可维护性 | 普通 | 新增、修改或批量保留 `package-info.java`，尤其只含包声明和泛化 Javadoc | [无真实包级契约的 `package-info.java`](NJA-020-valueless-package-info.md) |
| NJA-021 | Code Smell | 可维护性、可靠性 | 重大 | SSE 与普通请求—响应映射混合；精确类型后缀仅在目标项目明确启用时检查 | [SSE 与普通请求—响应 Controller 未分离](NJA-021-mixed-sse-and-request-response-controller.md) |
| NJA-022 | Code Smell | 可维护性、可靠性 | 重大 | 目标项目已定义分层与模型所有权，但 DTO、wire 类型、PO/Mapper 或转换器跨越该边界 | [I/O 模型与转换所有权错位](NJA-022-io-model-package-ownership.md) |
| NJA-023 | Code Smell | 可维护性、可靠性 | 普通 | 目标项目已启用按可见性区分的驼峰规则，但枚举值或常量不合规，或改名遗漏消费者与契约边界 | [Java 常量与枚举值未使用驼峰命名](NJA-023-constant-naming.md) |
| NJA-024 | Code Smell | 可维护性、安全性 | 普通 | 页面 Controller、别名或重复资源映射造成路由冲突、鉴权不等价、错误落页或消费者分裂 | [静态 HTML 被无责任 Page Controller 包装](NJA-024-static-html-page-controller.md) |
| NJA-025 | Code Smell | 可维护性 | 重大 | 手写或通过 Lombok、record、Builder 等生成有参构造，且不属于已放行的 Spring Bean 注入或人工授权例外 | [未获放行的有参构造](NJA-025-unauthorized-parameterized-constructor.md) |

## 异常专项规则目录

仅在异常专项模式下选择以下规则；候选扫描、五项证据模型、批量计数和传播链合并方法遵循[异常专项审计方法](exception-audit.md)。

| ruleId | 类型 | 质量属性 | 默认级别 | 主要触发条件 | 细则 |
|---|---|---|---|---|---|
| NJX-001 | Code Smell | 可维护性、可靠性 | 普通 | `catch` 只记录、换壳、改 message/code 或重新抛出，且没有真实处理责任 | [无处理价值的 catch](NJX-001-valueless-catch.md) |
| NJX-002 | Bug | 可靠性 | 重大 | 包装或转换丢失原类型、cause、堆栈、中断、致命错误或消费者分流事实 | [异常事实被改写或因果链丢失](NJX-002-exception-fact-loss.md) |
| NJX-003 | Bug | 可靠性 | 重大 | 技术失败被吞掉并转换为 `null`、空值、默认值、继续处理或成功结果 | [吞异常并制造假结果](NJX-003-swallowed-exception-fake-result.md) |
| NJX-004 | Code Smell | 可靠性、安全性 | 普通 | 同一异常沿传播链重复记录、缺失完整 Throwable，或内部细节直接暴露给用户 | [重复日志或内部细节外泄](NJX-004-duplicate-log-or-detail-leak.md) |
| NJX-005 | Bug | 可靠性、可维护性 | 重大 | 底层包装破坏 Advice、断流、中断、鉴权、重试、任务失败或入口呈现责任 | [入口责任被底层包装破坏](NJX-005-entry-responsibility-damage.md) |

## 全局判定边界

- 规则不是字符串匹配器。类名、方法名、文件数量、调用方数量或单个代码形状只能触发调查，不能单独构成问题。
- 每个问题都必须定位当前消费者、行为或维护影响，并主动检查细则列出的合理化反例。
- 同一位置可以命中多个规则，但报告应合并重复影响，分别保留真实成立的规则 ID，避免把一个根因拆成数量型问题；同时执行两种模式时也遵循这一原则。
- 项目 Rule 的违反另行标注其来源；即使语义相近，也不把 `NJA-*` 与项目规则合并或互相替代。
- 本目录导航当前有效的 `NJA-*` 与 `NJX-*` 规则，并保留明确标记的废止迁移记录。新增、修改、废止及产出与审计规则沉淀读取 [规则维护契约](rule-authoring.md)。
