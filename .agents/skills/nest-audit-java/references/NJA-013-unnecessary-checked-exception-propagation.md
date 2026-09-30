# NJA-013 非必要受检异常扩散

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性、可靠性
- 默认级别：普通
- 标签：checked-exception、IOException、DwException、SneakyThrows、exception-contract
- 适用范围：Java 方法新增或修改受检异常声明、调用链传播和异常文档；不要求把所有 `throws` 字符串机械转换成非受检异常

## 为什么是问题

方法仅为满足底层 JDK/第三方 API 的编译约束而声明 `IOException` 或宽泛受检异常，会把实现细节扩散到没有恢复职责的调用方，迫使上层增加无语义的 `throws`、catch 或包装层。异常类型因此看似是公共契约，实际没有稳定消费者，增加调用跳转和维护成本；更严重时，调用方会为了编译而吞掉、重复包装或错误映射异常。

## 触发调查

- `ProcessBuilder.start`、`Files`、流读写、反射或类似 API 旁边出现只为编译通过的 `throws IOException`/`throws Exception`；
- 私有或内部工具方法把 `IOException` 逐层转交给只有继续抛出、没有按类型恢复的调用方；
- 方法已经在最小边界完成异常转换或使用 `@SneakyThrows`，但仍残留 `throws IOException`、`java.io.IOException` import 或失真的 `@throws` Javadoc；
- 公共入口、脚本实现或适配器对所有底层 I/O 都暴露宽泛 `throws Exception`，却没有稳定异常协议说明。

## 判定所需证据

1. 定位真实调用方、接口/父类覆写关系、反射/SPI 注册和方法的公共可见性；
2. 核对调用方是否按具体受检异常执行重试、回退、资源补偿、业务转换、HTTP Advice 交接或中断恢复；
3. 识别异常是否是外部协议、框架回调、资源生命周期或稳定公共 API 的可观察契约；
4. 对照目标项目的异常规范：在异常产生的最小内部边界转换为项目统一的非受检异常；目标项目明确统一使用 `DwException` 时，确认 cause、堆栈、错误码/消息、日志、Advice、清理和线程中断行为不变；
5. 分别检查 `InterruptedException`，不得把中断传播改成无差别隐藏或吞掉。

## 不应报告

- 接口、SPI、框架/JDK 回调或公开库 API 明确要求该受检异常，且签名受覆写规则约束；
- 调用方依据异常类型进行重试、降级、资源回收、批处理隔离、HTTP/SSE 响应提交后处理或业务错误映射；
- 受检异常是当前外部协议、文件/仓储边界或启动生命周期的一部分，删除声明会破坏真实消费者或契约；
- 仅根据存在 `throws IOException`、任一 `@SneakyThrows` 形态或方法可见性无法确认行为和异常所有权；注解参数本身不构成 NJA-013，违反目标项目明确启用的注解形态规则时另行报告其项目 Rule 来源。

## 示例

不合规：单一生产调用方只继续抛出异常的 `start(List<String>, Path) throws IOException`，其唯一受检异常来源是 `ProcessBuilder.start()`；调用方不按 `IOException` 分支处理。

合规：目标项目内部 `start` 方法捕获 `IOException` 后抛出 `new DwException(cause).buildCodeMsg(message)`；其上层统一 Advice 继续记录详细原因并返回稳定错误语义。

合规：`OutputStream`/Spring `HttpMessageConverter` 回调覆写 `flush() throws IOException`，因为父接口和响应提交生命周期要求显式异常；不能为消除字符串而改签名。

合规：等待进程的 `nextEvent(...) throws InterruptedException` 继续传播中断，或在取消边界恢复 `Thread.currentThread().interrupt()` 后完成进程回收。

## 最小修复

在真实受检异常产生的最小非契约边界按目标项目规范转换为统一非受检异常，移除同一方法的 `throws` 声明、无用 import 和失真 Javadoc；目标项目统一使用 `DwException` 时保留原始 cause，普通消息不得误作错误码。确需隐藏没有稳定消费者的实现细节时，采用目标项目允许的受检异常收口方式；使用 `@SneakyThrows` 时，注解形态不能替代对中断、清理、协议和调用方边界的核对。保留恢复逻辑和 `InterruptedException` 边界，不新增无消费者的异常包装层或宽泛 `Exception`。

## 报告要求

报告准确位置、底层异常来源、真实调用方、是否存在按类型恢复或协议约束、实际级别和最小修复；如果只能证明“有 throws”或使用了 `@SneakyThrows` 而不能证明非必要，列为未验证，不判定命中。注解形态只在目标项目明确启用对应 Rule 时另行报告其来源。修复后应单独说明源码契约扫描、编译或真实端到端证据各自能证明与不能证明的范围。
