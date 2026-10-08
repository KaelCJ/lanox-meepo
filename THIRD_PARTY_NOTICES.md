# Historical binary assets

The current tree no longer contains the UUID19 JAR or the two SessionStart JARs, but all three remain in Git history. A normal clone may fetch those objects. This note records the known facts; the repository's [MIT License](LICENSE) does not by itself grant rights to third-party binaries.

| Former asset | SHA-256 | Historical use |
|---|---|---|
| `.workspace-assistant/foundation/host-hooks/claude/claude-session-start.jar` | `22d2786d97bb1546e7f02c9d81b21c8ccfb69b8ea5a0031e56dcab632bb5e0f9` | Optional Claude Code SessionStart hook |
| `.workspace-assistant/foundation/host-hooks/codex/codex-session-start.jar` | `50927212e894b3cc2ffd9667888c090a584be635a709a2362abd6a2c087475f2` | Codex SessionStart hook |

The work-item ID generator and SessionStart handlers now use Python. Supplied Java source describes the intended hook output, but existing build outputs have different hashes from the historical JARs; their exact provenance and redistribution rights have not been established. Before redistributing any historical binary or adding a new one, verify its owner, source, license and exact artifact. Current-tree removal does not rewrite Git history.
