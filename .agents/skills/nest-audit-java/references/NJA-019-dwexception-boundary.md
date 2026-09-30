# NJA-019 主动异常未统一为 `DwException`

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可靠性、可维护性
- 默认级别：重大
- 标签：DwException、exception-boundary、error-conversion、cause、structured-metadata、async
- 适用范围：目标项目启用 `DwException` 统一异常约束后，生产 Java 中主动抛出、包装、转换或异步传播业务/基础设施失败的代码；不要求把外部契约、生成代码或 `Error` 机械改成 `DwException`

## 为什么是问题

在目标项目自有边界主动抛出 `IllegalStateException`、`IllegalArgumentException`、裸 `RuntimeException`、`UncheckedIOException` 或主动 `IOException`，会让同一应用出现多套错误载体。统一 Advice、SSE/异步完成信号、日志与调用方可能只能识别 `DwException` 的 code、消息和 cause，导致错误码丢失、底层原因被覆盖、响应映射不一致或恢复逻辑按实现细节分叉。过度自定义的运行时异常还会增加无真实消费者的类型层级。

## 触发调查

- `throw new IllegalStateException(...)`、`throw new IllegalArgumentException(...)`、`throw new RuntimeException(...)`、`throw new UncheckedIOException(...)` 或主动 `throw new IOException(...)` 出现在目标项目自有 Service、Controller、Repository、client、Agent、候选组件或异步/流式边界；
- `orElseThrow`、`CompletableFuture.failedFuture`、`completeExceptionally`、lambda/stream 适配器或回调中主动构造上述异常；
- catch 外部异常后重新抛出非 `DwException`，或者只保留 message 而丢失 cause、错误码、协议元数据；
- 新增只改变类型名称的 `RuntimeException` 子类，调用方没有按其独立字段或类型恢复。

## 判定所需证据

1. 定位异常构造/传播位置，区分主动创建、外部异常 catch 类型和异常变量原样转发；
2. 沿真实调用链核对统一 Advice、Controller/SSE、异步 future、重试/回退、日志和资源清理如何识别异常类型、code、message、cause 与 suppressed；
3. 确认该位置是否属于目标项目自有边界，是否有接口、SPI、框架回调、外部协议或生成器强制的具体异常契约；
4. 若异常携带 HTTP status、响应体、headers、requestId、耗时等元数据，核对是否存在真实消费者按这些字段恢复，及改为 `DwException` 后元数据如何保留；
5. 对照最小转换方案，确认 `DwException` 构造语义正确：普通消息使用 `new DwException().buildCodeMsg(message)`，带原因保留 cause，稳定业务错误使用现有 code，不把展示消息误作 code。

## 不应报告

- `Error`、`ThreadDeath`、`VirtualMachineError` 等致命错误；清理或异步隔离边界应保持其原样传播，不伪装成业务失败；
- 外部库、JDK、框架回调、SPI/覆写签名或公开客户端契约明确要求具体受检/运行时异常，且目标项目不能改变其契约；进入项目自有边界后仍应调查是否需要转换；
- 代码生成器拥有的源码、正式 Nest 只读仓库或当前授权范围外的制品；
- 仅 `catch (IOException)`、`catch (IllegalArgumentException)` 等为了读取、分类或记录外部异常的 catch 类型，本身不构成主动传播违规；
- 已是 `DwException` 或有真实消费者按结构化元数据恢复的最小 `DwException` 子类；不能以“类名不是 DwException”单独判定。

## 不合规与合规示例

不合规：

```java
try {
    client.send(request);
} catch (IOException ex) {
    throw new RuntimeException("send failed");
}
```

这里丢失了原始 cause，统一错误处理无法稳定取得 code 或诊断上下文。

合规：

```java
try {
    client.send(request);
} catch (IOException ex) {
    throw new DwException(ex).buildCodeMsg("send failed");
}
```

合规例外：若确有消费者按 HTTP status、body、headers、requestId 等结构化字段恢复，可以使用 `DwException` 的稳定 code 与 `codeFormatArgs` 承载这些字段，并由消费者按该 code 解码；只有外部契约确实要求独立异常类型时，才保留最小的 `DwException` 子类。

## 最小修复

在目标项目真实自有边界把主动错误转换为 `DwException`，保留 cause、稳定 code、消息和结构化元数据；删除没有独立消费者的自定义 `RuntimeException` 类型与专用 catch。普通消息调用 `buildCodeMsg`，不要把消息传给只接受 code 的构造器。保留外部契约、`Error`、中断恢复、资源清理和异步完成时序；不借迁移扩大重构、改变响应协议或删除必要元数据。

## 报告要求

报告准确位置、主动传播路径、当前异常载体、真实消费者及其依赖的可观察字段、规则默认与实际级别、外部契约/生成代码/结构化元数据排除证据，以及最小修复方向。若只能证明存在非 `DwException` 类型而无法证明是目标项目自有边界主动传播，列为未验证，不判定命中。源码扫描可证明形状覆盖，编译可证明类型契约，均不能单独证明统一 Advice、SSE 或端到端行为已保持。
