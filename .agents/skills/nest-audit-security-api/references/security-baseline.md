# API 安全基线与开源借鉴

## 风险映射

优先映射以下标准，但用真实调用链和业务影响定级：

- OWASP API Security Top 10 2023：API1 BOLA、API2 Broken Authentication、API3 Broken Object Property Level Authorization、API4 Unrestricted Resource Consumption、API5 Broken Function Level Authorization、API6 Sensitive Business Flows、API7 SSRF、API8 Security Misconfiguration、API9 Improper Inventory Management、API10 Unsafe Consumption of APIs。
- OWASP ASVS：认证、会话、访问控制、输入验证、数据保护、API/Web Service 和配置验证要求。
- CWE：CWE-306（关键功能缺少认证）、CWE-862（缺少授权）、CWE-863（授权不正确）、CWE-639（用户可控键导致授权绕过）、CWE-915（动态属性修改失控）。

官方入口：

- https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- https://owasp.org/www-project-application-security-verification-standard/
- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html

## 默认严重度参考

- `严重`：匿名或低权限主体可读取大量敏感数据、执行高影响写操作、跨租户控制资源、直接绕过认证，或取得、签发、刷新、导出其他主体可复用的认证材料并形成账户冒充、接管或横向扩散能力。
- `高`：可稳定造成单对象/单用户越权、管理员功能越权、敏感字段越权读写、非必要读取或返回当前主体的可复用认证材料，或模糊绑定可修改安全关键属性。
- `中`：契约模糊、资产漂移、限制不足或信息泄露，当前证据尚未形成直接高影响利用链。
- `低`：纵深防御或可维护性缺陷，已有有效主控制且实际影响有限。

如果成立前提、部署可达性或数据敏感度不明，降低置信度或标记 `未确认`，不要机械降低严重度。

认证材料出现在对外出参或可调用副作用时先作为最高优先级候选审计，不因字段定义清楚、属于当前主体或接口需要登录而降级。标准登录、刷新或授权交换是否合理，必须在完整保护链和方法调用图上证明协议意图、主体绑定、签发方式、作用域、生命周期和最小披露后再下结论；不能用“认证接口通常返回 Token”直接排除。

## 可借鉴的开源项目

以下项目适合借鉴方法，不应未经核对直接执行其脚本或照搬规则。许可证、版本和仓库内容应在采用时重新核对。

1. **Trail of Bits Skills** — https://github.com/trailofbits/skills
   - 可借鉴：先构建审计上下文、静态分析工具编排、误报复核、variant analysis、SARIF/证据化输出。
   - 与本 Skill 的关系：提供成熟的通用安全审计方法，但不是专门的“逐 API 认证与数据权限矩阵”。
2. **vibesec** — https://github.com/tawgroup/vibesec
   - 可借鉴：先识别技术栈，再加载框架清单；使用确定性 grep/文件证据；重点发现匿名管理 API、RLS、service key 和调试路由。
   - 局限：公开说明主要覆盖 Next.js/Supabase 和常见配置，不足以证明复杂后端的对象级授权。
3. **Z-Audit** — https://github.com/zm2231/z-audit
   - 可借鉴：分阶段审计、认证/IDOR/API/基础设施/数据暴露分栏、结构化严重度报告。
   - 局限：更偏发布前与在线目标的广度扫描；本 Skill 需要更深的源码保护链和 Repository 数据约束证据。
4. **Facebook Research SecPriv Skill** — https://github.com/facebookresearch/secpriv-skill
   - 可借鉴：detector-validator 两阶段工作法，用独立验证减少安全发现误报，并用基准样例评估 Skill。
5. **Semgrep** — https://github.com/semgrep/semgrep 与 https://github.com/semgrep/semgrep-rules
   - 可借鉴：框架/语言分层规则、可定位的 source/sink 模式和可扩展规则包。适合发现候选 API、模糊 DTO 和危险调用；不能单独证明业务数据授权。
6. **CodeQL** — https://github.com/github/codeql
   - 可借鉴：跨函数数据流、污点追踪、查询套件和 SARIF 结果。适合补充输入到危险 sink 的分析；对象所有权仍需业务语义审计。
7. **OpenAPI tooling** — Spectral（https://github.com/stoplightio/spectral）、Schemathesis（https://github.com/schemathesis/schemathesis）与 openapi-diff（https://github.com/OpenAPITools/openapi-diff）
   - 可借鉴：契约 lint、schema 驱动验证和接口漂移检测。只在仓库规则允许动态/API 测试且用户明确授权时运行动态检查。

## 方法取舍

采用“确定性枚举 + 语义调用链审计 + 反证复核”：

- 用搜索、编译期元数据或 SAST 找候选，保证覆盖率；
- 用源码与配置还原真实生效链，判断认证和授权，保证准确性；
- 用第二次反证搜索检查白名单、旁路、同类接口和批量路径，降低漏报；
- 把工具未覆盖、装配不明或业务归属不明明确写成 `未确认`。

不要把扫描器“无发现”等同于安全，也不要为了凑齐报告而制造动态攻击、访问真实用户数据或越过目标授权范围。
