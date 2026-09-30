# 框架入口、保护链与调用图定位信号

只读取与目标项目相关的章节。信号用于发现候选位置，不构成安全结论；必须继续核对装配、匹配条件、实际实现、分支和返回路径。

## Java / Spring

- 入口：`@Controller`、`@RestController`、`@RequestMapping`、各 HTTP mapping、`RouterFunction`、WebFlux handler、GraphQL mapping、WebSocket handler、gRPC service、Spring Data REST、Actuator。
- 装配：`@SpringBootApplication`、`@ComponentScan`、`@Import`、auto-configuration、条件注解、Servlet/Filter registration、模块 POM 和组合根。
- 保护链：`SecurityFilterChain`、`requestMatchers`、`permitAll`、`authenticated`、`OncePerRequestFilter`、`FilterRegistrationBean`、`HandlerInterceptor`、`WebMvcConfigurer`、`WebFilter`、`@Aspect`、`@Around`、`@Before`、`@PreAuthorize`、`@PostAuthorize`、`@Secured`、方法安全开关。
- 调用图：Controller/Handler 到 Service 接口与注入实现、`@Qualifier`/`@Primary`/条件 Bean、事务代理、自调用、事件发布、`@Async`、消息生产消费、缓存注解、Mapper/Assembler、`@ControllerAdvice` 和响应序列化。
- 数据权限：Spring Data 派生查询、`@Query`、Specification、QueryDSL、MyBatis mapper/XML、JPA EntityManager、租户拦截器、软删除或行级过滤器。
- 常见陷阱：多条 filter chain 的 order；白名单方法范围过宽；AOP 自调用或非代理对象；接口/实现注解差异；注入实现与静态命中不同；异常/fallback 继续返回；缓存键丢失主体；异步调用丢失上下文；只从请求 DTO 读取 user/tenant；`findById` 后没有归属校验；Entity 直接绑定和返回。

## Node.js / TypeScript

- 入口：Express/Fastify router、NestJS controller、Next.js route handler/API routes、Nuxt/Nitro server routes、GraphQL resolver、Socket.IO/WebSocket handler。
- 装配：router mount、module imports、global prefix、file-system routing、serverless/export 配置、反向代理和 edge middleware。
- 保护链：middleware、route-group middleware、Nest guard/interceptor/pipe/decorator、Passport strategy、Next middleware、GraphQL context/auth directives。
- 调用图：Controller/handler 到 provider/service、依赖注入 token、middleware/guard/interceptor/exception filter、Promise 分支、事件/队列、ORM、cache、serializer 和 response mapper。
- 数据权限：ORM `where` 条件、repository/service 查询、Supabase RLS、Firebase rules、Prisma/Drizzle hooks、数据库 client 包装。
- 常见陷阱：只在页面做登录判断；middleware matcher 漏掉 API；客户端可改 metadata/role；service key 暴露；`any`、`Record<string, any>` 或对象 spread 导致 mass assignment；RLS 关闭或策略恒真。

## Python

- 入口：FastAPI/APIRouter、Flask blueprint/view、Django URL/view/viewset/router、GraphQL resolver、ASGI/WebSocket handler。
- 装配：router/blueprint include、Django urls、app factory、middleware 列表、依赖注入与 settings。
- 保护链：FastAPI dependencies、decorators、Django middleware/permissions/authentication classes、Flask before_request、ASGI middleware。
- 调用图：view/router 到 dependency/service/manager、同步与 async 分支、signals/tasks、serializer、ORM、cache、exception handler 和 response model。
- 数据权限：ORM queryset/filter、manager、permission object checks、tenant scope、serializer create/update。
- 常见陷阱：全局依赖没有应用到子 router；只配置 authentication class 未配置 permission；queryset 未按 request.user/tenant 限制；`dict`/`Any`/任意 Pydantic extra 字段。

## Go

- 入口：`net/http` handler、ServeMux、Gin/Echo/Fiber/Chi routes、gRPC service registration。
- 装配：route group、subrouter mount、server startup、middleware wrapping order。
- 保护链：middleware 链、group middleware、context principal、interceptor、policy helper。
- 调用图：handler 到 interface 的实际实现、context 传递、goroutine/channel、defer/recover、repository、cache、编码器和错误包装。
- 数据权限：SQL/ORM predicate、repository 参数、事务内二次读取、tenant session variable。
- 常见陷阱：特定 group 未包认证；middleware 顺序错误；只解析 JWT 不验证；查询只带资源 ID；`map[string]any` 更新模型。

## .NET

- 入口：MVC/API Controller、Minimal API `Map*`、SignalR hub、gRPC service、GraphQL resolver。
- 装配：endpoint mapping、assembly/application parts、middleware pipeline、route groups。
- 保护链：`UseAuthentication`、`UseAuthorization` 顺序、`RequireAuthorization`、`AllowAnonymous`、filters、attributes、policies、resource authorization handler。
- 调用图：endpoint/controller 到 DI 实现、handler/service、middleware/filter、async/Task、event/message、EF/repository、cache、mapper 和 exception handler。
- 数据权限：EF LINQ predicate、global query filter、repository/service、tenant provider。
- 常见陷阱：只注册服务未启用 middleware；Minimal API 漏掉 route-group policy；`AllowAnonymous` 继承/覆盖；按 ID 直接 `FindAsync`；DTO 与 Entity 自动映射过宽。

## 前端、网关与协议证据

- 前端调用只用于发现和核对，不代表后端边界安全。搜索 fetch/Axios/client SDK、GraphQL operation、WebSocket URL、下载链接和动态路径拼接。
- 网关/代理重点核对路由重写、strip prefix、method match、公开域名、内部域名、鉴权插件、白名单和多个入口是否汇合到同一后端。
- OpenAPI、GraphQL schema 和 protobuf 是契约证据，不是装配与授权证据；必须与实现及部署入口对照。

## 跨框架调用图追踪原则

- 先用引用、类型和依赖注入配置定位候选实现，再用组合根、注册条件和调用点确认实际实现；文本同名不等于真实调用边。
- 同时从入口向下追踪输入和副作用，从响应、凭据、数据访问、文件、网络和状态变更 sink 反向追踪来源；两向结果必须汇合。
- 把条件分支、异常、fallback、重试、缓存、异步和返回映射作为调用图节点，不把它们压缩成“Service 已处理”。
- 无法静态解析的反射、插件、运行时脚本、生成代码或外部实现保留为有边界的 `未确认`，不得跳过其下游安全目标。
