# Changelog

所有重要变更将记录在本文件。

## [Unreleased]

- 建立项目说明、安全策略、贡献指南与公开范围说明，并提供脱敏的最小工作流示例。
- 工作项新编号改用 Python UUID4 并保留旧编号读取能力；从当前树移除原 UUID19 JAR。
- 移除 Workspace Sync，保留只读的 Workspace 采用审计。
- 按可见源码契约用 Python 实现 Claude Code/Codex 的 SessionStart JSON 输出，Codex 接线改用 Python；两枚旧 JAR 从当前树移除，历史与真实宿主验证仍未解决。
- 撤下过早的安装器、二进制校验和 Git 路径检查及其专用测试和接线，优先验证核心工作流。

## [0.1.0] - 待发布

- 首次公开发布（计划中）。
