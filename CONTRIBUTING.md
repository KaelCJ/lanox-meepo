# Contributing to Nest

感谢参与。当前项目处于早期阶段，优先欢迎能让安装、理解和验证更容易的改进。

## 提交前

1. 先搜索现有 Issue，避免重复讨论。
2. 对行为变化先创建 Issue，说明场景、目标用户和预期结果。
3. 不提交密钥、个人数据、客户代码、会话转储、缓存或未知来源的二进制。
4. 修改 Skill 或规则时，同时更新对应文档和示例。

## 本地验证

```bash
python -m compileall .agents/skills
python .agents/skills/nest-work-item/scripts/work_item_index.py --help
```

如果修改了入口配对规则，还应运行：

```bash
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --root .
```

## Pull Request

PR 描述请包含：

- 解决的问题和用户场景；
- 变更范围；
- 验证命令及结果；
- 是否需要迁移、文档或兼容性说明。

请保持每个 PR 主题单一、改动可审阅。维护者会优先处理可复现、证据完整且不扩大无关范围的贡献。
