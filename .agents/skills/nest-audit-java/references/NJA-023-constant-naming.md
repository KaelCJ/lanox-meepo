# NJA-023 Java 常量与枚举值未使用驼峰命名

## 元数据

- 状态：Ready
- 类型：Code Smell
- 质量属性：可维护性、可靠性
- 默认级别：普通
- 标签：java、constant、naming、api、interface、enum、generated-source
- 适用范围：目标项目明确启用“枚举值和公开常量使用 UpperCamelCase、其他常量使用 lowerCamelCase”规则时，人工维护或当前授权可修改的 Java 枚举值与常量；包括声明、限定引用、脚手架模板和生成真源

## 为什么是问题

全大写下划线命名把 Java 标识符、环境变量和 wire 字段混在同一视觉层级。目标项目规则对枚举值与常量使用同一套驼峰约定时，枚举值和公开常量使用 UpperCamelCase，非公开常量使用 lowerCamelCase。命名不一致会降低代码检索和审查的信噪比；改名若遗漏限定引用、反射、生成真源或枚举序列化契约，还会造成编译失败或运行时契约漂移。

## 触发调查

以下形状只在目标项目已启用上述命名规则时触发调查：

- `public static final` 或 `final static` 字段含下划线、连续全大写片段或首字母小写；
- `private`、`protected`、包可见 `static final` 字段或接口隐式常量首字母大写、含下划线或全大写；
- 枚举值含下划线、连续全大写片段或首字母小写；
- 接口中声明 `INSTANCE`、`DEFAULT_*` 等隐式公开字段；
- 常量改名只修改声明，未搜索限定引用、静态 import、反射/序列化配置、脚手架模板和生成真源；
- 扫描器把普通 `final` 实例字段、局部变量、方法参数或环境变量字符串列为常量或枚举值。

这些信号只启动调查；不能仅凭文本匹配直接判定问题。

## 判定所需证据

1. 读取完整声明和拥有它的类型，确认它是枚举值、`static final`、`final static` 或接口/注解隐式常量，而不是普通实例字段、局部变量或参数；
2. 从目标项目规则确认命名类别和适用范围，再核对枚举值、`public` 常量、其他可见性常量、下划线和连续全大写片段；
3. 搜索全部生产引用、静态 import、反射、SpEL、配置绑定、序列化、脚手架模板和生成器，确认改名影响及所有权；
4. 核对字符串值、JSON/wire 字段、环境变量、错误码、文件路径、`Enum.name()`/`valueOf()` 和持久化契约，确认本规则只改变 Java 标识符；
5. 检查 Maven 模块依赖、外部发布 API、Nest 正式只读源码和生成代码边界；不能修改的外部或生成所有权不得被误报为人工修复目标；
6. 对公开常量评估源码兼容性。若存在仓外调用方或已发布二进制契约，需提供兼容策略或把问题标为未验证，不静默增加别名。

## 不应报告

- 普通 `final` 实例字段、局部变量、方法参数、lambda 变量和 JavaScript `const`；
- 环境变量、HTTP header、JSON/wire 字段、错误码或文件路径字符串本身；
- 代码生成器、正式 Nest 仓库、外部 SDK 或已发布只读源码拥有的常量，除非当前授权包含其真源或人工适配层；
- 已有外部契约明确要求保留的公开常量或枚举标识符，且当前任务没有兼容迁移授权；
- 目标项目没有启用本细则所述驼峰规则；此时不能用本规则替代其实际命名规范；
- 枚举值已经使用 UpperCamelCase，而其独立 wire 值、数据库值或展示值按外部契约保留原貌；
- 只在历史文档、原始稿、审计报告或 `.logs` 证据中出现的旧名称。

## 不合规与合规示例

目标项目已启用上述驼峰规则时，不合规：枚举值、公开常量和包可见常量均使用全大写下划线。

```java
public enum ReviewStatus {
    PENDING_REVIEW("pending_review");

    private final String value;
}

public static final String DEFAULT_BASE_URL = "https://example.test";
static final String PROCESS_EVENTS_PATH = "process/events.jsonl";

client.setBaseUrl(DEFAULT_BASE_URL);
```

同一前提下，合规：Java 标识符改为对应驼峰形式，独立字符串值保持不变。

```java
public enum ReviewStatus {
    PendingReview("pending_review");

    private final String value;
}

public static final String DefaultBaseUrl = "https://example.test";
static final String processEventsPath = "process/events.jsonl";

client.setBaseUrl(DefaultBaseUrl);
```

不应报告：枚举标识符已经使用 UpperCamelCase，其 wire 值和环境变量字符串保持协议原貌。

```java
enum Status {
    PendingReview("pending_review")
}
String model = System.getenv("OPENAI_MODEL");
```

## 最小修复

目标项目已启用上述规则时，在当前授权范围内把违规枚举值和常量改为项目要求的形式，并同步同一 Java 符号的生产引用、静态 import、反射注册、脚手架模板和生成真源。保留独立字符串值、外部字段名、错误码、路径和运行行为；删除旧名称后重新做大小写敏感全仓扫描。若 `Enum.name()`、`valueOf()`、JSON、数据库、公开 API、反射或生成所有权无法确认，停止结构性改名并报告证据缺口。

## 报告要求

报告必须给出目标项目启用的命名 Rule、实际级别、准确文件和行号、符号类别与可见性、当前名称、建议名称、全部已确认消费者，以及是否涉及生成或外部契约。说明修改只影响 Java 标识符、哪些字符串或 wire 契约被排除；枚举值还要说明 `name()`、`valueOf()`、序列化和持久化是否被消费。缺少项目 Rule 证据时不判定命中；若没有完成全仓引用、反射、生成真源或源码兼容核对，明确标为未验证。不要把日志历史、环境变量或普通 `final` 字段作为命中。
