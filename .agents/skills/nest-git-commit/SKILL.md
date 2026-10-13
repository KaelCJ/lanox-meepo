---
name: nest-git-commit
description: "仅当用户显式调用 $nest-git-commit、点名 nest-git-commit、指定 .agents/skills/nest-git-commit/SKILL.md 或明确要求执行本 Skill 时使用：代做全量暂存，按主题粗分批次创建本地提交并简要报告。不用于推送、Pull Request、分支删除、reset、rebase 或其他历史改写。"
---

# Nest Git 提交

代替用户在 IDEA 中逐个 Git Add：全量暂存当前仓库的可提交改动，大致按主题分批完成本地提交。用户不需要预先暂存。

## 流程

1. 显式调用即授权本地 Add 和提交，不重复询问。用户要求只预览时，只查看改动，不暂存或提交。
2. 在仓库根目录查看 `git status`。有未解决冲突或正在进行 merge、cherry-pick、rebase 时停止。
3. 执行 `git add -A`，再用 `git diff --cached --name-status` 看全部暂存路径。没有暂存差异就报告并结束。仅在判断主题或写消息需要时查看具体 diff。
4. 按功能或工作项粗分批次：相关改动即使跨目录也放一起，独立主题分开。边界不清时合并；同一文件及一次重命名的两端只放在同一批，不拆改动块。
5. 多批时，逐批执行 `git commit -m "<message>" -- "<本批路径...>"`；只有一批时执行 `git commit -m "<message>"`。其余已暂存文件留给后续批次。提交过程中若发现文件又被编辑，停止并报告，因为按路径提交会读取工作区版本。
6. 任一提交失败就停止，保留已完成的提交和剩余暂存内容。全部完成后查看 `git status --short` 和 `git log --oneline --decorate -5`，简要报告本次提交的短哈希、消息、每批一句话说明及剩余未提交内容；不输出完整 diff、构建结果或执行过程。

## 提交信息格式

格式固定为：

```text
<type>(<工作项ID>): <中文简述>
```

- `<type>` 只能取下列之一，英文小写：

  | type | 含义 |
  |---|---|
  | `feat` | 新增对使用者可见的能力 |
  | `fix` | 修复缺陷 |
  | `refactor` | 重构，不改变外部行为 |
  | `docs` | 文档、工作项记录、知识沉淀 |
  | `test` | 测试 |
  | `build` | 构建、依赖、发行和平台资产 |
  | `chore` | 杂项维护，例如配置、忽略规则、脚本 |
  | `revert` | 回退已有提交 |

- `<scope>` 只取工作项 ID，例如 `(r1033)`。没有工作项 ID 时省略整个括号，不用模块名、不用 `*`、不留空括号。
- `<中文简述>` 精简即可：不加句号，不重复文件路径或类名，不用「修改了」「更新一下」这类无信息量表述。
- 整行不超过 72 字符。
- 破坏性变更在 subject 的冒号前加 `!`，例如 `feat(r1033)!: 调整工作项索引格式`；或在正文写 `BREAKING CHANGE: <中文说明>`。
- 需要展开时与 subject 空一行写正文，讲清原因与影响面，不复述 diff。每行不超过 72 字符。
- 不写工具署名或生成器标记，例如 `Co-Authored-By`，除非用户明确要求。

示例：

```text
feat(r1033): 新增本地 Agent 应用发现 SPI 与三家桌面端探测
refactor: 统一 Java 包到 com.digiwin.dap.nest.agent 根包
docs(r1033): 记录四种模型端点协议的请求体与结束状态
build: 把 local-discovery 加入 reactor 并引入 anthropic-java 依赖
fix: 修正 SSE 重放缺少终态事件时丢帧
chore: 更新 nest-rule-java Skill
```

## 边界

- 不推送、不创建 PR、不重写历史、不 reset、不 rebase、不删除分支、不绕过 Git 钩子。
- 不为提交修改源码，不额外构建、测试或打包；正常提交钩子照常执行。
