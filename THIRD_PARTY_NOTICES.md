# Third-party and binary asset register

This register records the evidence needed before a bundled binary is advertised or redistributed. It is **not** a license grant. The root [MIT License](LICENSE) does not automatically apply to any asset listed here.

Machine-readable records and SHA-256 values are kept in [`docs/third-party-assets.json`](docs/third-party-assets.json). The current release remains blocked because the required ownership and redistribution evidence has not been recorded for any listed binary.

## Current status

Reviewed: **2026-10-07**  
Release status: **BLOCKED — historical binaries and other private assets remain in Git**

The two SessionStart JARs have been removed from the current working tree and the configured Codex hook now calls a Python script. Their hashes remain here and in the machine-readable register to identify the copies still present in Git history. Supplied Java source shows the intended SessionStart output, but existing build outputs have different hashes and no ownership or redistribution license was established. Removing a current file is not permission to redistribute its historical blob; do not publish a full clone or release archive containing these files.

| Historical asset | Former role | SHA-256 | Runtime | Status |
|---|---|---|---|---|
| `.workspace-assistant/foundation/host-hooks/claude/claude-session-start.jar` | Optional Claude Code SessionStart hook | `22d2786d97bb1546e7f02c9d81b21c8ccfb69b8ea5a0031e56dcab632bb5e0f9` | Java 21 | Removed from current tree; historical authorization pending |
| `.workspace-assistant/foundation/host-hooks/codex/codex-session-start.jar` | Codex SessionStart hook formerly referenced by `.codex/hooks.json` | `50927212e894b3cc2ffd9667888c090a584be635a709a2362abd6a2c087475f2` | Java 21 | Removed from current tree; historical authorization pending |

The observed manifests identify these files as `nest-component-workspace` version `1.0.0`, built with JDK 21. This observation is provenance metadata, not proof of ownership or permission to redistribute.

## Evidence required to clear an asset

For each row, maintainers must record all of the following in the machine-readable register or in a review record referenced by it:

1. The copyright owner or author.
2. The authoritative source repository or build source.
3. The exact upstream version or commit used to produce the file.
4. The SPDX license identifier and any required NOTICE text.
5. Written permission or a license clause that permits redistribution in this repository and in release archives.
6. A reproducible build reference or SBOM when the asset contains bundled dependencies.
7. Supported runtime versions, platforms, and the data read or written by the binary.
8. The verified SHA-256 for the exact artifact being released.

Do not commit confidential agreements, credentials, private customer data, or internal session dumps as evidence. Store sensitive authorization records in an appropriate private system and record only a stable reference, decision, and reviewer in the public register.

## Review procedure

1. Compare the artifact with the authoritative source or build output.
2. Verify the license and redistribution scope with the owner or legal record.
3. Review the binary's runtime behavior and documented dependencies.
4. Only if a binary will be reintroduced, update its row from `pending` to `cleared`, record the evidence and verify the exact SHA-256. Otherwise keep the historical record pending until its public-history exposure is separately resolved.
5. Run the public validation and a clean-install smoke test before publishing.

The work-item ID generator now uses Python UUID4; its previously tracked UUID19 JAR has also been removed from the current tree. The two SessionStart handlers now have a Python implementation in `tools/session_start.py`; the Codex hook invokes it, while no Claude project hook configuration is currently installed. Python protocol tests do not prove that a new Claude Code/Codex session loaded the hook. All three former JARs remain in Git history; a future-tree deletion does not erase historical copies, and any history cleanup requires separate approval. The offline Quickstart does not copy hooks or JARs, but cloning the repository still fetches historical objects.
