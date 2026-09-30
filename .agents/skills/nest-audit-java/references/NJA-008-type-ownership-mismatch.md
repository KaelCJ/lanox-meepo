# NJA-008 Java 类型与分层所有权错位

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性
- 默认级别：普通
- 标签：ownership、nested-type、responsibility、package、layering
- 适用范围：嵌套类型、执行类内部模型、分层 package，以及拥有独立状态、算法、协议或生命周期的实现

## 为什么是问题

把请求、响应、结果或独立组件嵌套在 Service、Controller、Runtime、Repository 等执行类中，会把产生者或消费者误当成语义所有者。其他消费者被迫依赖执行类命名空间，独立职责也容易继续堆入门面。

把 Web 入口、用例编排、领域行为、基础设施实现和 DTO 平铺在单 module 根包也会抹掉项目已经采用的依赖方向。单 JAR 只说明部署边界相同，不能证明这些类型属于同一逻辑层。

## 触发调查

- 其他顶级类型引用 `Outer.Request`、`Service.Result` 或相似嵌套契约；
- 嵌套类型拥有独立状态、算法、协议解析、IO 或生命周期；
- 外层只产生或消费该类型，并不构成真实父子聚合；
- Controller、应用 Service、外部进程或 I/O Connection 和 DTO 位于同一根包，当前项目已有 presentation、application、infrastructure 和契约 DTO 样板；
- 仅凭目录名称或通用架构记忆声明层级顺序，没有读取当前 POM 和生产依赖；
- 为提取类型又顺带增加 public、Bean、接口、Factory 或兼容别名。

## 判定所需证据

1. 搜索全部消费者、构造者、序列化和框架引用；
2. 判断外层是否为真实语义所有者，而非执行入口；
3. 核对 package/module 边界和最小必要可见性；
4. 读取当前项目已有 Controller、Service、DTO、基础设施样板和 Maven POM，画出实际依赖方向，不把目录排列当成依赖证据；
5. 比较提取为真实所有者顶级类型或迁入既有逻辑层 package 后的依赖与认知成本；
6. 保证迁移不擅自拆 Maven module、不创建空层、不引入额外抽象或改变外部契约。

## 不应报告

- 小型子对象表达真实聚合或父子层级；
- DTO 忠实映射外部 JSON 或协议嵌套结构；
- 临时状态只服务单一算法且不会脱离外层消费；
- 结构由生成器拥有，人工拆分会破坏生成契约。
- 当前项目没有采用分层 package，单用途模块根包中的类型职责一致且没有跨层依赖；
- 分包需要新增未授权 Maven module、反转现有依赖或制造空 domain、接口和转发层。

## 示例

不合规：多个模块通过 `Runtime.ExecutionResult` 交换结果，而 Runtime 只是执行者，Result 已成为独立契约。

不合规：单 JAR 中的 Controller、用例 Service、外部子进程 Connection 和请求响应 DTO 全部位于模块根包，尽管当前项目已经有 presentation、application、infrastructure 和 DTO 分包样板。

合规：把结果移到真实归属 package 的顶级类型，以消费者所需的最小可见性暴露；不额外创建接口或 Registry。

合规：保持一个 Maven module，只把 Web 入口、应用编排、外部连接实现和 DTO 移入项目既有逻辑层 package；没有领域行为时不创建空 domain。

## 最小修复

仅迁移真实所有权错位的类型或职责到项目既有逻辑层 package，同步必要消费者并保持行为与序列化契约；不要按行数机械拆分，也不要把 package 整理扩大成 Maven 模块重构。

## 报告要求

列出外层或当前 package 职责、真实消费者、现有分层样板、POM 依赖方向、建议所有者、可见性和已检查的不拆分反例。
