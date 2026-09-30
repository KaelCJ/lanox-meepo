---
name: nest-rule-java
description: 按需加载当前项目 Java 规则；当本轮包含具体 Java 源码设计决策（即使出现在方案或前端任务中）、创建/修改/生成/重构 Java 源码，或明确的 Java 代码审计结论时使用。仅提及 Java、纯需求/方案/执行/测试文档、工作项、读取解释代码、日志构建、运行验证及非 Java 资源不触发。
---

# Java Rule 加载

## 触发边界

- 本轮输出或变更包含具体 Java 源码设计决策（如类、接口、方法签名或枚举值）、创建/修改/生成/重构 Java 源码，或明确的 Java 代码审计结论时，自动加载本 Skill；即使这些内容夹在方案讨论、前端任务或其他产物中，也要在首次 Java 设计结论或写入前加载。
- 仅处理需求、方案、执行步骤、测试记录、工作项、日志、构建结果、运行验证、代码事实定位或代码解释，且不提出具体 Java 代码结构决策时，不自动加载本 Skill；仅提及 Java、依赖或引用 Java 代码也不构成自动触发。
- 自动触发、用户显式调用 `$nest-rule-java`、已启用的专项 Skill 明确要求项目 Java Rule，三者是独立的加载入口；命中任一入口即按下述协议加载，不以用户显式调用为自动触发的前提。

1. 每个 Agent 在当前有效上下文首次应用 Java Rule 前读取 [唯一规则正文](references/rules.md) 的目录，并按标题边界完整读取核心章节：`代码约束`、`间接层和扩展点必须有当前依据`、`Lombok`、`异常处理`、`Module` 的通用条款（不含 `Module 拆分`、`client Module`）、`Package`、`通用结构`、`Nest 基础设施`、`四层结构`中 `client`/`infrastructure`/`application`/`presentation` 的通用根条款（不含其条件子标题）。先用标题定位，再读取每个选定章节至下一个同级或更高层标题；不要因 Skill 触发而全文读取无关专题。
2. 按当前目标事实追加专题，未命中的专题不读取：
   - 新建或拆分 Maven Module → `Module 拆分`；独立 `client` Module → `Module 拆分`、`client Module`；已有 Module 内增补代码不读取这两节。
   - Feign 或 Dubbo Consumer → `Feign 与 Dubbo Consumer`；Feign 或 Dubbo Provider → `Provider 协议模型`、`rpc`。
   - 出站普通 HTTP Manager → `普通 HTTP`；不要因此读取入站 Controller、SSE 或 HTTP 业务接口专题。
   - 入站普通请求—响应 Controller → `web`、`Web 与 Application DTO`、`HTTP Controller 交互模型`、`HTTP 业务接口`。
   - SSE、文件上传、文件下载或其他流式 Controller → `web`、`Web 与 Application DTO`、`HTTP Controller 交互模型`、`HTTP 业务接口`；若同一任务还含普通接口，再合并读取普通接口专题。
   - MQ/Job → `MQ 消息模型` 或 `Job 任务模型`；Application/Infrastructure Meta 转换 → `converts`。
   - 用户明确设计或改造 Dapper/链路日志 → `Dapper 与链路日志`；静态 HTML、页面 Controller、重定向或资源映射 → `静态 HTML 页面`。
   专题只补充核心，不覆盖核心；需要父级路径定义时一并读取其父级条款。Controller 的交互模型无法由目标响应协议确认时，先核对事实；仍无法确认则停止受影响结论，不凭类名选择专题。
3. 以已读章节名、章节范围和 `rules.md` 当前文件状态（优先 hash）记录加载集合。同一有效上下文且文件未变化时，已完整读取的核心和适用专题直接复用；不要假设宿主一定提供可见的压缩事件。上下文压缩、会话接续、文件变化，或无法确认某组正文仍完整可用时，重新读取核心和当前适用专题。无法确认适用集合、章节边界或正文完整性时，回退为完整读取 `rules.md`；仍缺失、为空、不可读或冲突则停止受影响结论。
4. 在首次 Java 设计、写入或审计结论前应用已加载的适用规则；委派相关工作时要求子 Agent 自行使用本 Skill，不复制规则正文。加载规则不扩大用户授权，也不创建工作项、验证或迁移授权。
