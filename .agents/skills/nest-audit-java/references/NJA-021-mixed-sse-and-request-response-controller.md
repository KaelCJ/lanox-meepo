# NJA-021 SSE 与普通请求—响应 Controller 未分离

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性、可靠性
- 默认级别：重大
- 标签：spring-mvc、controller、sse、streaming、async、lifecycle、separation
- 适用范围：人工维护的 Java Spring MVC Controller 中新增或修改的 SSE 映射及同类 Controller 边界；精确 `*SSEController` 后缀只在目标项目明确启用该命名规则时检查；不授权批量迁移审计范围外的历史接口，也不授权修改生成代码或外部只读源码

## 为什么是问题

SSE 是长连接、异步、响应可提前提交的交互模型，其完成点、断流、取消、心跳、缓冲、超时、异常和观测生命周期都不同于普通请求—响应接口。同一 Controller 同时承载 SSE 和普通 JSON、HTML、下载或控制接口时，业务资源名称会掩盖传输边界，后续维护者容易把普通统一包装、同步异常处理、超时或同步观测生命周期错误套到 SSE，或者把 SSE 的 Header、写流和断流处理扩散到普通接口。

专用 SSE Controller 让注册边界表达交互模型，使流式生命周期相关的配置、私有辅助方法和审计范围可被准确定位。目标项目进一步要求 `*SSEController` 后缀时，类型名也必须遵守该规则；未启用这一命名约束时，不能只因类名不同而判定问题。缺少交互边界通常不会立即改变 URL，却会提高响应被错误包装、流完成状态失真、断流清理遗漏和修改相互污染的风险。

## 触发调查

- 同一个 `@Controller` 或 `@RestController` 同时存在 `produces = text/event-stream`、`StreamingResponseBody`、`SseEmitter` 或同类 SSE 映射，以及普通请求—响应映射；
- 目标项目明确启用精确后缀规则，但 SSE 映射位于类名不以 `SSEController` 结尾的人工维护类型；
- 普通查询、命令、`interrupt`、`status`、`control` 等接口被放入专用 SSE Controller；
- SSE Header、心跳、事件写出、断流、取消、超时或响应提交后异常 helper 与普通接口共享同一 Controller；
- 拆分方案同时改动 URL、鉴权、既有观测行为、DTO 或 Service，且这些变化没有独立需求依据。

`StreamingResponseBody` 也可能用于下载，类名或返回类型只能触发调查；必须核实媒体类型和实际事件协议后才能判定 SSE。

## 判定所需证据

1. 完整读取 Controller 的类级与方法级映射、`consumes`、`produces`、返回类型、Header 和私有辅助方法，确认端点实际使用 SSE 事件流，而不是下载、普通异步响应或其他流式协议；
2. 列出该类型的全部可达映射，并核实是否同时存在普通请求—响应接口，或专用 SSE 类型是否混入普通命令；
3. 核对 Spring 注册、继承、接口默认方法、生成所有权和框架约束，确认映射的真实所有者及类名是否可由当前项目控制；
4. 读取调用方、鉴权、安全配置、统一包装、异常处理和既有观测实现，确认 Controller 拆分可以保留既有 method、URL、DTO、Header、观测与业务行为；
5. 核对 Service 调用关系，确认问题位于 HTTP 入口分类，不把 Controller 分离机械扩张成 Service 一一拆分或业务重构；
6. 区分当前审计范围与未修改历史代码；证据不足以确认 SSE 协议、生成所有权或拆分等价性时标为未验证，不判定命中。

## 不应报告

- 独立 SSE Controller 内包含多个 SSE 端点，以及只服务这些端点的 Header、心跳、写流、断流和生命周期私有 helper；其类名符合目标项目已启用的命名规则；
- 普通 Controller 只包含请求—响应接口，SSE Controller 只包含 SSE 接口，两者共享同一个业务 Service；
- 使用 `StreamingResponseBody` 实现文件下载或其他已明确的非 SSE 协议，且其 Controller 按真实交互模型组织；
- 框架或代码生成器强制生成类型名和映射所有权，人工扩展层无法在当前授权内等价拆分；
- 外部已发布契约明确强制一个不可拆分的入口类型，且当前实现已记录该约束及流式生命周期边界；
- 审计范围外、当前任务未修改的历史 Controller；本规则不能作为批量迁移授权。

## 不合规与合规示例

不合规：同一 Controller 混合 SSE 与普通中断命令，类型名也没有表达 SSE 边界。

```java
@RestController
@RequestMapping("/api/jobs")
public class JobController {

    @PostMapping(value = "/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseEntity<StreamingResponseBody> events(@RequestBody JobStartReqDTO request) {
        return startEventStream(request);
    }

    @PostMapping("/interrupt")
    public void interrupt(@RequestBody JobInterruptReqDTO request) {
        service.interrupt(request);
    }
}
```

合规：保持路径和 Service 语义不变，只按交互模型拆开入口。示例假设目标项目已启用 `SSEController` 后缀规则。

```java
@RestController
@RequestMapping("/api/jobs")
public class JobSSEController {

    @PostMapping(value = "/events", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public ResponseEntity<StreamingResponseBody> events(@RequestBody JobStartReqDTO request) {
        return startEventStream(request);
    }
}

@RestController
@RequestMapping("/api/jobs")
public class JobController {

    @PostMapping("/interrupt")
    public void interrupt(@RequestBody JobInterruptReqDTO request) {
        service.interrupt(request);
    }
}
```

两个 Controller 可以注入同一个 `JobService`；SSE 专属 helper 留在 `JobSSEController`，不要求为文件数量对 Service 做镜像拆分。

## 最小修复

保持 method、URL、鉴权、既有观测行为、请求与事件 DTO、Header 和 Service 调用语义不变，把 SSE mapping 及其专属媒体类型、Header、心跳、写流、断流、取消、超时和响应提交后异常 helper 移到独立 SSE Controller；目标项目明确启用 `SSEController` 后缀规则时再按该后缀命名。普通查询、命令、状态和控制 mapping 留在普通 Controller。删除拆分后无用的 import、常量和 helper，不新增兼容路径、不复制 Service、不顺带迁移范围外 Controller。

## 报告要求

报告必须给出混合交互模型的 Controller 与准确映射、SSE 判定证据、普通请求—响应映射、流式 helper 或生命周期责任、当前生成与注册所有权，以及错误包装、断流或观测失真的具体风险。命名问题必须同时给出目标项目启用精确后缀规则的证据。最小修复需列出移动后的 SSE Controller 和普通 Controller 所有权，并说明哪些 URL、鉴权、既有观测行为、DTO、Header 与 Service 语义必须保持。若未核实框架注册、生成所有权或调用方兼容，明确标为未验证，不把文件拆分本身写成行为等价证明。
