# Public release scope

This is a maintainer checklist for deciding what may enter the public repository, not a license grant for assets whose ownership or redistribution terms are unknown. Historical binary facts are recorded in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

## Public by default

- Root project documentation and governance files owned by this project.
- Plain-text Skills, commands, rules, schemas, and validation scripts whose authorship and redistribution have been confirmed.
- Synthetic examples that contain no real session, customer, production, credential, or personal data.

## Private or blocked until confirmed

- `.workspace-assistant/10-工作项/` runtime records, current work items, session context, caches, and generated reports.
- `.workspace-assistant/foundation/` and `.codex/hooks.json` when they depend on workspace-specific runtime assets.
- Any JAR or other binary whose source, copyright, and redistribution license are not recorded.
- Rules or references containing organization-specific architecture, product names, internal domains, private dependencies, or confidential methods.
- Real Agent/Codex sessions, rollout files, logs, user paths, customer code, and benchmark data that has not been consented and redacted.

## Conditional retention

The two SessionStart JARs and the former UUID19 JAR have been removed from the current tree but remain in Git history. A normal clone can still fetch those objects; this is different from the contents of a current-tree archive. Decide how to handle that history separately, without treating it as proof that a new JAR is safe to redistribute.

## Release gate

Before a file is added to a release, maintainers must be able to answer all of these questions:

1. Who owns or authored it?
2. What license permits redistribution?
3. Does it contain secrets, personal data, internal names, or local paths?
4. Can a clean checkout use it without an unavailable private dependency?
5. Is its behavior and limitation documented for users?

Before sharing a particular set of files, check its actual contents, ownership, license and runtime dependencies. If a binary is included, review the exact artifact and its redistribution rights. Removing a file from the working tree does not remove it from Git history; history cleanup requires a separate, deliberate operation.

The repository currently tracks real work-item records even though `.gitignore` now excludes new ones. Those records require human review before whole-repository publication. No script-based path or binary release gate is claimed to resolve this; focus on verifying the working Skills and host behavior first.

## Current review flags

The following paths require explicit ownership or license confirmation before being advertised as public runtime dependencies:

- `.workspace-assistant/foundation/host-hooks/claude/claude-session-start.jar`
- `.workspace-assistant/foundation/host-hooks/codex/codex-session-start.jar`
- `.agents/skills/nest-rule-java/`
- `.agents/skills/nest-audit-java/`
- `.agents/skills/nest-audit-security-api/`
- `.agents/skills/nest-insights/`

This list is a review status, not a blanket prohibition. The two SessionStart JARs and UUID19 JAR are absent from the current tree but still in Git history; see [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md). Python replacement of the hooks did not remove those historical objects.
