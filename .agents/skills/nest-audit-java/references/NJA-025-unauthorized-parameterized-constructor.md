# NJA-025 未获放行的有参构造

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性
- 默认级别：重大
- 标签：constructor、lombok、dependency-injection、coupling、static、javabean
- 适用范围：所有层级和模块的人工维护 Java 源码，包括 Manager、Controller、Application、Meta 与 Infrastructure；不授权修改外部只读源码或生成器所有的产物

## 为什么是问题

有参构造把对象创建与当前字段集合、参数顺序和装配方式绑定，字段变化会扩散到构造声明、工厂和调用方，也容易让本可独立的属性与行为被聚合到同一实例。数据承载对象应通过无参创建和 setter 赋值；不依赖实例状态的行为应使用静态方法。不可变性、`final` 字段、不变量、资源所有权、生命周期、状态机、框架惯例或通常的面向对象设计都不能自行构成本规则的例外。

## 触发调查

- 源码声明了一个或多个参数的构造函数，不论其可见性；
- 使用 `@AllArgsConstructor`，或在非 Spring Bean、非依赖注入用途上使用 `@RequiredArgsConstructor`；
- 使用 `@Builder`、`@SuperBuilder`、`@Value`、`@Data` 或其他可能间接生成有参构造的注解或处理器；
- `record`、枚举、静态工厂、反射入口或方法引用背后存在有参构造；
- 新增未初始化的 `final` 字段，并通过构造函数完成赋值；
- 调用方出现 `new Type(...)`、构造函数方法引用或向有参构造传递当前对象状态。

这些形状只触发调查。注解名称、`final` 字段或 `new` 表达式不能代替对实际生成构造、Spring Bean 身份和授权依据的核实。

## 判定所需证据

1. 完整读取类型及其 Lombok、注解处理器和语言结构，确认源码或生成语义确实提供了至少一个有参构造；
2. 核对目标项目 Java Rule 是否明确放行该具体构造；不得从相邻规则、同类代码、框架习惯或设计理由推导放行；
3. 核对构造函数紧前方是否已有人工授权 Javadoc，并确认该授权早于当前 Agent 改动或由用户明确提供；Agent 在本次任务中新增的 Javadoc 不能作为授权；
4. 对 `@RequiredArgsConstructor`，确认类型实际由 Spring 容器管理，且生成构造只用于注入 Spring Bean 依赖；仅有注解、`final` 字段或依赖形态不能证明放行；
5. 搜索直接创建、工厂、反射、序列化、框架注册和跨模块消费者，确定整改范围与实际级别；调用方数量影响严重度，但不改变禁止条件；
6. 区分人工源码、生成产物和外部只读源码；生成产物命中时定位其模板或生成器，只有所有者处于当前范围内才报告可整改位置。

## 不应报告

- 显式、隐式或 Lombok 生成的无参构造；
- 实际 Spring Bean 使用 `@RequiredArgsConstructor`，且生成参数全部用于 Spring Bean 依赖注入；
- 目标项目 Java Rule 已明确放行的具体构造；
- 构造函数紧前方存在当前任务开始前已有的人工授权 Javadoc，或用户已明确提供该授权；
- 当前修改边界之外的外部只读源码或生成产物；生成器或模板在范围内时，应针对真实所有者报告，不在产物上重复计数。

除上述条件外，不因不可变对象、值对象、`final` 字段、构造期校验、资源或生命周期管理、状态机、序列化要求、框架惯例、私有构造、静态工厂、记录类或调用方较少而排除报告。

## 不合规与合规示例

不合规的数据承载对象：

```java
public final class AgentMeta {
    private final String name;
    private final String version;

    public AgentMeta(String name, String version) {
        this.name = name;
        this.version = version;
    }
}
```

合规的数据承载对象：

```java
@Getter
@Setter
@NoArgsConstructor
public class AgentMeta {
    private String name;
    private String version;
}
```

合规的 Spring Bean 依赖注入：

```java
@Service
@RequiredArgsConstructor
public class OrderApplicationService {
    private final OrderRepository orderRepository;
}
```

同一个 `@RequiredArgsConstructor` 放在普通对象上，或生成参数还承担数据装配、配置绑定和运行状态初始化时，仍然不合规。

## 最小修复

- 数据、Meta、配置和传输对象：删除有参构造及生成它的注解，改为无参创建后通过 setter 赋值；
- 不依赖实例状态的行为：删除实例字段与对象创建，把行为改为静态方法，并把变化值作为方法参数传入；
- 必须保留实例的普通对象：使用无参构造和 setter 完成装配；
- Spring Bean 依赖注入：删除手写有参构造，使用 `@RequiredArgsConstructor` 承载 Spring Bean 依赖；
- 认为确有例外但现有 Java Rule 和人工 Javadoc 均未授权时，停止制造例外并交由人工决定；Agent 不得自行补写授权 Javadoc；
- 生成代码命中时只修改当前授权范围内的模板或生成器，不直接修改产物。

整改不得顺带引入 Builder、Factory、Provider、兼容构造或其他间接有参装配方式，也不得以迁移为由扩大当前授权范围。

## 报告要求

报告准确定位类型、构造函数或生成构造的注解，列出参数用途、直接创建点和真实所有者，并分别给出 Java Rule 放行、既有人工授权 Javadoc、Spring Bean 注册与纯依赖注入的核对结果。说明生成产物与模板边界、建议的无参 setter 或静态化方向，以及未验证的反射和框架消费者。静态扫描只能证明源码形状，不能冒充编译、容器装配或真实运行验证。
