# Changelog

所有重要变更将记录在本文件。

## [Unreleased]

- 建立开源项目说明、安全策略、贡献指南和行为准则。
- 准备第一个可复现 Demo 与自动验证流程。
- 增加公开范围说明、5 分钟 Quickstart、脱敏最小工作流示例和基础 CI 骨架。
- 建立两个 SessionStart JAR 的 SHA-256 登记与授权发布门禁；授权证据仍待补齐，未开放二进制安装路径。
- 工作项新编号改用 Python UUID4 并保留旧编号的读取能力；从当前树移除原 UUID19 JAR。
- 移除 Workspace Sync，保留只读的 Workspace 采用审计。
- 增加离线文本白名单安装、干净目标与路径预检测试，并为 CI 配置 Windows 验证；当前 Git 树仍未通过发布门禁。
- 按可见源码契约用 Python 实现 Claude Code/Codex 的 SessionStart JSON 输出，Codex 接线改用 Python；两枚旧 JAR 从当前树移除，历史与真实宿主验证仍未解决。

## [0.1.0] - 待发布

- 首次公开发布（计划中）。
