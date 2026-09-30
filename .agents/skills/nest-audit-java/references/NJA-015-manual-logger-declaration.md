# NJA-015 手写日志声明未统一为 `@Slf4j`

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性、可靠性
- 默认级别：普通
- 标签：lombok、Slf4j、LoggerFactory、logging、boilerplate
- 适用范围：目标项目明确要求 SLF4J 日志声明使用 Lombok `@Slf4j`，且当前 module 已启用 Lombok 的人工维护源码；不要求把生成代码或不同日志门面机械改写为 `@Slf4j`

## 为什么是问题

目标项目已经统一要求 `@Slf4j` 时，手写 `Logger` 字段与 `LoggerFactory.getLogger(...)` 会重复样板并形成第二种声明方式，增加 import、字段和类型名同步维护成本。仅依赖 Lombok 或部分类型恰好使用 `@Slf4j`，不能推出所有手写 logger 都违规；不当批量替换还可能造成日志级别、参数、异常对象或脱敏语义变化。

## 触发调查

- 目标项目已启用 `@Slf4j` 统一规则，且出现 `org.slf4j.Logger`、`org.slf4j.LoggerFactory` import；
- 目标项目已启用该规则，且出现 `LoggerFactory.getLogger(...)` 或 `private static final Logger ...`；
- 同一类型同时出现 `@Slf4j` 与手写 logger 字段；
- 新增或修改的人工维护 Java 类型仍复制日志字段样板。

## 判定所需证据

1. 确认目标项目治理入口明确启用 `@Slf4j` 统一规则，目标 module 使用 Lombok 依赖和注解处理器，且源码是人工维护而非生成产物；
2. 确认字段实际类型为 SLF4J logger，日志调用可由 Lombok 生成的 `log` 字段等价承载；
3. 对照迁移前后级别、模板、参数、异常对象、调用时序、脱敏和静态初始化边界，确认不存在行为变化；
4. 检查类型、父类/接口、反射或外部框架是否要求特定字段名称、日志门面或初始化方式；
5. 确认不是仅因存在 logger 字符串就把 JUL、Commons Logging、生成源码或外部仓库纳入项目整改范围。

## 不应报告

- 代码生成器拥有的源码，且只能通过修改 schema、模板或生成器改变；
- 当前 module 未采用 Lombok，或注解处理器不可用且新增依赖不在授权范围；
- 目标项目没有启用 `@Slf4j` 统一规则，手写 SLF4J logger 符合其当前风格或有独立所有权；
- 使用 JUL、Commons Logging、Log4j API 或其他非 SLF4J 门面；
- 父类、SPI、框架回调、反射、静态初始化或外部 ABI 明确依赖字段名称、可见性或非标准 logger 生命周期；
- 仅发现可以使用 `@Slf4j`，但没有核对当前消费者、依赖和行为等价证据。

## 不合规与合规示例

目标项目已启用 `@Slf4j` 统一规则时，不合规：

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

final class ImportJob {
    private static final Logger log = LoggerFactory.getLogger(ImportJob.class);
}
```

同一前提下，合规：

```java
import lombok.extern.slf4j.Slf4j;

@Slf4j
final class ImportJob {
}
```

合规例外：生成器明确输出 `Logger` 字段，或类型使用 `java.util.logging.Logger` 且项目契约要求该门面；应在审计报告中说明所有权或契约证据。

## 最小修复

目标项目已启用该规则且 module 支持 Lombok 时，在人工维护的 SLF4J 类型上添加 `@Slf4j`，删除 `Logger`、`LoggerFactory` import 与等价字段，保留原有 `log.*` 调用和日志语义。缺少项目规则证据时不提出该迁移；缺少 Lombok classpath 时也不以本规则擅自新增依赖。

## 报告要求

报告准确定位类型和字段，给出目标项目启用规则、module 的 Lombok 依赖、日志门面、生成或人工所有权、行为等价核对范围和实际级别；缺少启用证据时不判定命中。修复后分别说明源码扫描、编译和真实运行证据能证明与不能证明的范围。
