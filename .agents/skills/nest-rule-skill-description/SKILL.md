---
name: nest-rule-skill-description
description: 加载并应用 Agent Skill 的 description 官方写作规范（agentskills.io 硬约束与触发四原则）。任务创建或修改 SKILL.md、撰写、审计或优化任何 Skill 的 description frontmatter 时使用；只阅读或执行已有 Skill 正文、不产出或修改 description 时不触发。
---

# Skill description 规范

适用于本仓库全部 `.agents/skills/*/SKILL.md`（含本 Skill 自身）的 frontmatter description 撰写、修改与审计。规范来源：agentskills.io Specification 与 Optimizing descriptions；DSH 侧由 `dsh-skill-filesystem` 的 `parseSkillFile` 机器执法。

## 硬约束（机器校验，违反即 Skill 静默消失）

- frontmatter 必须是合法 YAML：解析失败、`name` 或 `description` 缺失/为空 → DSH 静默跳过该 Skill，无任何报错。新写的 Skill「不在目录出现」时先查这里。
- `name`：必填，≤64 字符，小写字母/数字/连字符（kebab-case），与所在目录名一致。
- `description`：必填非空字符串，≤1024 字符；原样进入 Skill 目录展示给模型，同时承担「触发路由」与「技能摘要」两个职责。
- 可选字段：规范层有 `license`、`compatibility`（≤500 字符）、`metadata`（字符串键值表）、`allowed-tools`；DSH 扩展 `whenToUse`、`disable-model-invocation`、`user-invocable`。旧字段 `disableModelInvocation` / `modelInvocable` 会导致解析失败，不得使用。

## 写作四原则（官方 Optimizing descriptions）

1. **触发句式**：写给 agent 的行动判断——「当用户要求/显式调用 … 时使用」，不写「本 Skill 是…」的能力宣言。显式调用型 Skill 写全触发形态（$ 调用、点名、SKILL.md 路径、明确要求）并加反隐式触发清单。
2. **意图导向**：写用户会说的话与目标，不写实现机制；机制、参数与内部术语（如「删掉判据」）移入正文。
3. **场景覆盖**：宁全勿漏——列出用户不点名领域词的说法（如「检查入口」「是不是最新」），让近似请求也能命中。
4. **简洁与 near-miss**：几句话到一小段；紧邻但不该触发的场景写入「…不触发/不用于」，特别是同族 Skill 的分工（如整体审计 vs 异常专项、审计 vs 同步）。

## 流程

- **撰写**：按四原则起草 → 对照硬约束自检 → 运行校验脚本，0 失败后交付。
- **修改**：只改 `description` 行，不动 `name` 与正文，除非用户明确要求；不丢失既有「只读/不推送」类边界语义。
- **审计**：逐 Skill 输出三列表格（原文 / 审计结果 / 建议优化），维度 = 硬约束 + 四原则 + near-miss，结论分级为必须改 / 建议轻优化 / 合规保持。
- **校验**：运行 `python <本Skill目录>/scripts/check_descriptions.py --root <skills根目录>`（默认当前目录），要求 0 解析失败、0 超长、name 与目录一致。

## 已知坑

- 未加引号的 description 值内含 ASCII「冒号+空格」（如 `commit: read`）→ YAML 解析失败 → Skill 静默消失；含冒号的 description 整段用双引号包裹。
- description 值中的 ASCII `#` 有 YAML 注释风险；中文标点（：；、（））安全。
- 写入 SKILL.md 后 DSH 文件监听热刷新，下一轮对话生效，无需重启。
