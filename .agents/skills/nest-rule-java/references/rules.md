# Java Rule

> 本文件是 `$nest-rule-java` 的唯一 Java Rule 真源与章节聚合入口；专题按 Skill 加载，不建立副本。

## 目录

核心章节是所有 Java 设计、产出和审计任务的共同前置；其余章节只在任务事实命中对应专题时加载。读取专题时按本目录的标题边界读取完整章节，不把目录行或单条规则当作替代正文。

- [代码约束](#代码约束)
- [间接层和扩展点必须有当前依据](#间接层和扩展点必须有当前依据)
- [Lombok](#lombok)
- [异常处理](#异常处理)
- [Module](#module)
- [Package](#package)
- [Nest 基础设施](#nest-基础设施)
- [Dapper 与链路日志](#dapper-与链路日志)
- [HTTP Controller 交互模型](#http-controller-交互模型)
- [静态 HTML 页面](#静态-html-页面)
- [HTTP 业务接口](#http-业务接口)

### 按需专题索引

| 任务事实 | 在核心章节之后追加读取 |
|---|---|
| 新建或拆分 Maven Module | `Module` 下的 `Module 拆分` |
| 独立 `client` Module | `Module` 下的 `Module 拆分`、`client Module` |
| Feign 或 Dubbo Consumer | `四层结构` 下的 `Feign 与 Dubbo Consumer` |
| Feign 或 Dubbo Provider | `四层结构` 下 `Provider 协议模型`、`rpc` |
| 出站普通 HTTP Manager | `四层结构` 下的 `普通 HTTP` |
| 入站普通请求—响应 Controller | `四层结构` 下的 `web`、`Web 与 Application DTO`；`HTTP Controller 交互模型`；`HTTP 业务接口` |
| SSE、文件上传、文件下载或其他流式 Controller | `四层结构` 下的 `web`、`Web 与 Application DTO`；`HTTP Controller 交互模型`；`HTTP 业务接口`（流式协议确认条款） |
| 用户明确设计或改造 Dapper/链路日志 | `Dapper 与链路日志` |
| 静态 HTML、页面 Controller、重定向或资源映射 | `静态 HTML 页面` |
| MQ/Job | `四层结构` 下的 `MQ 消息模型` 或 `Job 任务模型` |
| Application/Infrastructure Meta 转换 | `四层结构` 下 `application` 的 `converts` |

## 代码约束

- 禁止声明 JDK `record`。
- 禁止声明或创建嵌套类、内部类、局部类、匿名类、嵌套接口、嵌套枚举和嵌套注解类型；仅静态 Holder 延迟初始化单例，或用户明确要求的具体嵌套结构例外。
- 由代码生成器生成的 Java 源码不得手工修改；需要改变生成结果时，修改对应的生成真源、生成器配置或模板并重新生成。
- 禁止创建 `package-info.java`；只有用户明确要求时才允许创建。
- 枚举值和 `public` 常量使用首字母大写的 UpperCamelCase，其他可见性的常量使用首字母小写的 lowerCamelCase；禁止使用下划线或全大写名称。
- Java Javadoc 使用中文，只补充代码不能直接表达的真实职责、边界或关键行为；不得复述标识符和方法签名，也不得为自解释的样板代码生成无信息注释。
- 不得擅自新增 `${...}` 环境变量占位。
- 新增配置必须有当前真实消费者，不得为未来设想或“可能有用”增加配置项或配置层。
- `${...}` 只改变值的来源，不提供加密或安全性。

## 间接层和扩展点必须有当前依据

- 新增或保留间接层、抽象或扩展点，必须存在当前真实消费者、多个实现、明确替换要求，或者独立算法、事务、I/O、安全、框架、并发、生命周期等真实边界。
- 只有单一生产调用方和单一实现，且只做参数透传或线性转发、没有隐藏独立状态、分支或边界时，直接调用或内联；未来可能复用不是保留依据。

## Lombok

- 只承载数据、配置或请求响应的类型使用 Lombok `@Getter`、`@Setter`，不手写等价访问器。
- 构造器注入使用 `@RequiredArgsConstructor`；存在额外构造逻辑或多个构造入口时除外。
- 只生成当前需要的方法，不使用会额外生成 `equals`、`hashCode`、`toString` 或访问器的组合注解。
- `@SneakyThrows` 只使用无参数形式，使受检异常无需在方法签名中声明并保持原异常向上抛出；禁止任何带参数形式。
- 需要 SLF4J 日志时使用 Lombok `@Slf4j`，不得手工声明等价的 Logger 字段。

## 异常处理

- 异常默认原样向上抛出，禁止使用 `catch`；只有用户明确要求在当前边界处理异常时才允许捕获。
- 代码主动抛出异常时统一使用 `DwException`。

## Module

- 采用四层结构时，`client`、`application`、`infrastructure`、`presentation` 默认分别由独立的 Maven Module 承载；任何合并多个逻辑层、少建或不建其中任一 Module 的方案，都必须先取得人工明确批准，根聚合 POM 不计入这四个业务 Module。
- 每个逻辑层无论是否独立成 Module，都必须使用自己的层 Package，不得平铺到 Module 根 Package。

### Module 拆分

- 新建 Module 命名：`<项目>-<层级>`。
- 已有 Module 命名沿用，不重命名。

### client Module

- `client` 仅为 Package 时，不修改所在 Module 的 parent。
- 独立 `client` Module 使用 Feign 时，parent 为 `com.digiwin.dap.nest:nest-infrastructure-dependencies-parent-openfeign:<当前 Nest 版本>`，并声明 `<relativePath/>`。
- 独立 `client` Module 不使用 Feign 时，parent 为 `com.digiwin.dap.nest:nest-kernel-dependencies-meta:<当前 Nest 版本>`。

## Package

- 从目标源码所在目录向上，读取最近一组项目入口中的 `Java Package 标识`。
- `公司`、`部门`、`项目` 必须由同一组入口完整定义；子目录的完整定义整体覆盖祖先定义，不逐字段继承或拼接。
- 根 Package 为 `com.<公司>.<部门>.<项目>`；本文后续统一写作 `<根 Package>`。
- 层 Package：`<根 Package>.<层级>`。
- 已有根包沿用，不重命名。
- 标识缺失、不完整或同目录双宿主定义冲突时，停止创建 Package，不从源码目录、Module 或类名推断。
- 同一层内需要按业务分类时，先进入稳定职责 Package，再在该职责下拆分业务子 Package，统一使用 `<根 Package>.<层级>.<职责>[.<业务>]`；禁止使用 `<根 Package>.<层级>.<业务>.<职责>`。
- 业务子 Package 只在该职责存在真实类型时创建，不要求同一业务机械镜像到所有职责，也不创建空目录或占位类型。

### 通用结构

#### meta

```text
<所属 Package>.meta
├── constants
├── dto
│   ├── request
│   └── response
└── enums
```

具体规则只声明 Meta 根 Package；其中的 constants、DTO 和 enums 结构统一执行本节。消息、任务或其他具有独立协议角色的模型只在具体规则明确时增加对应子 Package。
只创建当前代码实际使用的子包，不创建空目录或占位类型。
- Meta 下的自有类型、字段和枚举值使用见文知意的精简中文 Javadoc。
- Meta 中的字段不使用 Java 基本类型，统一使用对应包装类型。

##### DTO

- 通用 DTO 放在 `<Meta 根 Package>.dto`，类名使用 `DTO` 后缀。
- 请求 DTO 放在 `<Meta 根 Package>.dto.request`，类名使用 `ReqDTO` 后缀。
- 响应 DTO 放在 `<Meta 根 Package>.dto.response`，类名使用 `RspDTO` 后缀。

### 四层结构

#### client

- `client` 是当前服务对外提供的 API。
- Java 接口放在 `<根 Package>.client.api[.<业务>]`。
- `client` 只能放接口和 meta 类型，不放实现。

##### Provider 协议模型

- Feign 和 Dubbo Provider 的协议模型，Meta 根 Package 为 `<根 Package>.client.meta[.<业务>]`。

#### infrastructure

- 本服务调用外部能力的代码统一归 `<根 Package>.infrastructure.manager`；需要本地分类时，只在 `manager` 下按业务拆分子 Package。

##### Feign 与 Dubbo Consumer

- 本服务使用 Feign 或 Dubbo Consumer 调用外部能力时，使用提供方 API 的类型和命名，不复制或重命名提供方 API。

##### 普通 HTTP

- 调用类由本服务创建，类名以 `Manager` 结尾；Manager 不可实例化且不保存实例状态，调用方法默认使用 `static`，只有用户明确要求时才使用实例或非静态方法。
- Manager 类型和静态方法的划分、命名及请求与响应类型，必须与当前版本的官方 API 逐项、逐字段、逐层级 1:1 对应，不得按当前使用范围删减、合并、改名或增加业务包装。
- 成功状态码以官方文档为准，不能一律把所有 `2xx` 当成功；官方没写就先问用户。
- Meta 根 Package 为 `<根 Package>.infrastructure.manager.meta[.<业务>]`。

#### application

- 承担事务边界的 Application 类放在 `<根 Package>.application.service[.<业务>]`，类名以 `Service` 结尾。
- 不承担事务边界的 Application 类放在 `<根 Package>.application.component[.<业务>]`，类名以 `Component` 结尾。

##### meta

###### Web 与 Application DTO

- 普通 HTTP Controller 调用 Application 所需的请求与响应 DTO、SSE Event DTO，以及 Application 内部用于收拢参数或结果的自有 DTO，Meta 根 Package 为 `<根 Package>.application.meta[.<业务>]`。

###### MQ 消息模型

- MQ 消息模型放在 `<根 Package>.application.meta[.<业务>].message`，使用当前消息契约确认的 `Message`、`Event` 或其他后缀，不改成 DTO，也不直接复用 Web DTO。

###### Job 任务模型

- Job 任务模型放在 `<根 Package>.application.meta[.<业务>].job`，使用当前任务规范确认的模型名称，不改成 DTO，也不把调度参数伪装成 Web 请求。

##### converts

- Application Meta 与 Infrastructure Meta 相互转换的代码放在 `<根 Package>.application.converts`，类名以 `Converter` 结尾。
- 转换通常只读取源 JavaBean 的 getter，并调用目标 JavaBean 的 setter 完成字段映射。

#### presentation

- 当前服务的链路入口放在 `<根 Package>.presentation.server`。

##### web

- 普通 HTTP Controller 放在 `<根 Package>.presentation.server.web[.<业务>]`。
- 请求和响应 DTO 使用 `<根 Package>.application.meta[.<业务>]` 中的类型。

##### rpc

- Feign 和 Dubbo Provider 实现放在 `<根 Package>.presentation.server.rpc[.<业务>]`。
- Provider 实现对应 `<根 Package>.client.api[.<业务>]` 中的 API，协议模型使用 `<根 Package>.client.meta[.<业务>]` 中的类型。

## Nest 基础设施

- 采用 Nest 的项目在设计或实现通用基础能力前，先核对目标模块的实际依赖与 Nest 版本，并按需检索对应版本的 Nest API、源码、现有调用方和测试，核实已有能力的方法语义与适用边界；未主动检索、未找到源码或当前模块尚未声明依赖，不等于 Nest 没有该能力。确认有适用能力时必须复用，不得用 JDK、第三方库或项目内的 Helper、Util、Adapter、包装层重复实现，也不得因局部更快而绕过 Nest。
- JSON 序列化、反序列化和对象转换统一使用 Nest `DwJson`，禁止直接创建或注入 `ObjectMapper`。
- Nest 组件不能拆着用：引入组件就使用它自带的功能，不得在项目中关闭、替换或重新实现其中一部分；不需要该组件时删除组件依赖。

## Dapper 与链路日志

- Dapper 接入必须单独设计；未经用户明确要求，不得自行新增、补齐或改造 Dapper。
- 所有链路日志均由用户主动设计；未经用户明确要求，Agent 不得自行新增、补齐或改造链路日志。

## HTTP Controller 交互模型

- 一个 Controller 只承载一种 HTTP 交互模型；普通请求—响应、SSE、文件下载和其他流式响应分别归类，不因服务同一业务对象而混合。
- SSE 接口只能放在类名以 `SSEController` 结尾的 Controller；该 Controller 不得包含查询、命令、状态、控制等非 SSE 接口。是否属于 SSE 以实际响应协议判断，不能只看是否返回流对象。
- 拆分既有 Controller 时，只调整接口所属类型，不得同时改变 HTTP method、URL、鉴权、请求或事件 DTO、Service 调用契约；Controller 拆分不要求同步拆分 Service。

## 静态 HTML 页面

- 已有可直接访问的 `.html` 页面时，直接使用它；不得为了更短的地址、无后缀、尾斜杠或目录首页，再添加页面 Controller、重定向、转发或额外资源映射。
- 只有组合根需要让 `/` 跳到唯一首页，或者页面确实必须由服务端处理时才允许例外；其他情况必须先取得用户明确同意。同一个页面无论从哪里进入，都必须经过同一鉴权边界。

## HTTP 业务接口

- 普通 HTTP 业务接口默认使用 `POST` 和 JSON `ReqDTO`/`RspDTO`；路径使用明确业务动作，不使用 `GET`、`PUT`、`PATCH`、`DELETE` 或旧动词、旧路径兼容别名。业务标识和筛选条件放入请求 DTO，协议元数据才放入 Header。
- Controller 不得直接暴露 `Map`、`Object`、裸集合、裸字符串、持久化模型、领域模型或外部协议模型；Nest 统一响应只包装一次，`RspDTO` 不重复定义统一响应外壳。
- SSE、文件上传、文件下载和其他确实需要流式处理的接口可以不遵守上述普通接口的 `POST + JSON ReqDTO/RspDTO` 约束；但新增或修改前必须取得用户人工确认，确认具体协议后再实现。
- 普通接口没有业务输入时调用无参 Service 方法；有业务输入时，Controller 只能传入当前接口完整的 `ReqDTO`，不得拆分字段或增加其他参数。
- 用户、租户、权限、语言、traceId 等上下文数据通过 Nest 统一上下文获取，不得作为 Controller 传给 Service 的参数，也不得写入客户端可提交的 `ReqDTO`。
- 需要第二个参数、其他 DTO、跨线程上下文快照或特殊传输签名时，必须先取得用户人工确认；已经确认的 SSE、上传、下载或其他流式接口按确认后的协议设计。
- 普通 HTTP 接口出错时，直接交给 Nest Advice；Controller 和 Service 不得捕获或包装异常，也不得自行拼装失败响应。
