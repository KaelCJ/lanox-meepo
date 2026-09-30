# NJA-022 I/O 模型与转换所有权错位

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性、可靠性
- 默认级别：重大
- 标签：dto、io-model、package、presentation、application、infrastructure、http、rpc、po、converter
- 适用范围：目标项目已明确启用 Presentation、Application、Infrastructure 分层及对应模型所有权规则时，其自有 Web DTO、内部参数 DTO、HTTP/RPC 出站协议模型、PO/Mapper 和模型转换代码

## 为什么是问题

目标项目已经定义上述分层与模型所有权时，完整 package 是识别协议方向、依赖所有者和变更影响的主要依据。违反已启用的边界会使调用方无法判断一个字段受 Web、远端协议还是存储契约约束，并把序列化、敏感字段和兼容风险扩散到错误层。没有项目分层依据时，不能从层名或本细则反推唯一架构。

把所有转换机械塞入 Infrastructure 也可能形成反向依赖：Infrastructure 为构造 Application DTO 依赖上层，或者借转换器继续向 Application 暴露 PO。转换位置必须同时满足模型所有权和当前 Maven 依赖方向，不能只满足目录名称。

## 触发调查

- Presentation package 中声明目标项目自有 `*DTO`，或 Controller 直接返回 PO、Mapper 结果和外部 wire 类型；
- Application Service、业务模块根 package 或 Presentation 直接创建 HTTP/RPC 请求、解析响应或持有外部客户端；
- Application 或 Presentation import Infrastructure 的 `*PO`、Mapper、Example、ORM/存储记录；
- HTTP 与 RPC 模型混在无协议区分的 `dto`、`common` 或产品根 package；
- PO/DTO 转换散落在 Controller、Service、Repository 调用点或 DTO 静态工厂，或者转换器位于 Application 却直接绑定 PO；
- Infrastructure converter import Application 或 Presentation，只为构造上层 DTO；
- 被多个消费者使用的请求、结果或参数载体仍嵌套在 Service、Runtime、Controller 或 Client 中；
- MQ Message/Event 或 Job 模型被机械重命名为 DTO。

## 判定所需证据

1. 读取目标项目治理入口，确认已启用的分层、模型所有权和例外；未启用时本规则不适用；
2. 定位真实运行边界，区分 Web 入站、MQ、Job、HTTP 出站、RPC 出站、数据库或文件存储和纯进程内方法调用；
3. 读取目标 Maven POM 和当前生产依赖，确认 Presentation、Application、Infrastructure 的实际依赖方向；
4. 搜索模型的全部构造者、消费者、序列化、Mapper、反射和框架注册，确认其真实所有者及可观察契约；
5. 核对外部或生成模型所有权，不能把不能修改的官方或 Nest 类型误判为目标项目自有 DTO；
6. 对 PO/Mapper 穿透检查是否存在 Infrastructure DTO 与 converter，确认敏感字段、空值、枚举、时间和精度没有在迁移中改变；
7. 对公开嵌套类型检查外层是否为真实父子所有者，还是仅为执行者；
8. 对 MQ/Job 检查其独立 schema、版本、幂等、调度和生命周期规范，不能仅凭“也是 I/O”要求 DTO 后缀。

## 不应报告

- 外部依赖、代码生成器或正式协议拥有的类型保留其官方名称和 package，并只在 Infrastructure 适配器内部使用；
- 一个 Web `ReqDTO` 按项目规则从 Controller 直接传给 Service，没有字段等价的第二个内部 DTO；
- 私有嵌套状态只服务单一算法，或嵌套子对象忠实表达真实父子协议结构；
- 配置、Session/Turn 生命周期所有者、资源句柄、回调、枚举、缓存实体、文件记录或查询投影按其真实角色使用独立名称；
- MQ 与 Job 使用各自已确认的 Message/Event/Job 规范；
- 当前没有真实 HTTP、RPC、MQ 或 Job 消费者，因此没有创建对应空 package；
- 当前 Maven 依赖不允许 Infrastructure 构造 Application DTO，代码先返回 Infrastructure DTO，再在 Application 进行有真实语义的 DTO 映射。
- 目标项目没有启用本细则所述分层或模型所有权规则，当前结构符合其真实架构且没有可证实的依赖倒置、协议泄漏或敏感字段扩散。

## 示例

不合规：Application Service 直接 import `OrderPO` 和 `OrderMapper`，随后在 Service 内逐字段构造 Web `OrderRspDTO`；数据库字段、密码和查询 Example 已越过 Infrastructure。

不合规：一个业务模块在 `application.web` 中直接创建 JSON-RPC wire request 并调用外部进程，同时把官方 response 类型返回给 Controller，违反目标项目已启用的协议模型所有权。

不合规：为了统一 DTO 后缀，把 `PaymentEvent` 和 `SettlementJob` 政名为 DTO，丢失消息版本、幂等与任务生命周期边界。

合规：Infrastructure Repository 使用 PO 和 Mapper，在 `infrastructure.converts` 转为 Infrastructure DTO；Application 只消费 DTO，并在确有 Web 暴露差异时映射为自己的 `RspDTO`。

合规：Web `ReqDTO/RspDTO` 位于 Application meta，Controller 位于 Presentation web；外部 HTTP 与 RPC 的项目自有 DTO 分别位于 Infrastructure 的 `http`、`rpc` meta，官方 wire 类型不离开适配器。

## 最小修复

按目标项目已启用的真实边界，只迁移错位的项目自有模型、适配器和转换器；具体目标 package 以该项目规则为准，不从本细则独立生成架构。同步全部生产消费者并保持 JSON、远端协议、SQL、敏感字段和用户流程不变，不新增空层、兼容别名或字段等价 DTO。

## 报告要求

报告目标项目启用的规则来源、完整 package、模型角色、真实边界、构造者和消费者、POM 依赖方向、外部或生成所有权、具体泄漏或反向依赖、MQ/Job 排除检查，以及保持协议和存储行为的最小迁移方向。缺少项目规则证据时不判定命中；只有静态证据时明确未验证真实序列化、数据库或远端调用。
