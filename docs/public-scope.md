# Public release scope

This file is the maintainer checklist for deciding what may enter the public repository. It is not a license grant for assets whose ownership or redistribution terms are unknown. The binary evidence register is [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) and its machine-readable companion [`docs/third-party-assets.json`](third-party-assets.json).

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

The two SessionStart JARs and the former UUID19 JAR have been removed from the current working tree; their historical copies remain in Git. The machine-readable register keeps the two SessionStart hashes with `present: false` and `status: pending`. This records unresolved provenance without claiming current-tree redistribution permission. The offline text installer copies no hooks or JARs, but a normal clone still downloads historical objects. Do not reintroduce a binary-backed installation path without ownership and redistribution evidence.

The current register deliberately remains `releaseBlocked: true` because the historical assets and private-path review are unresolved. An inventory pass checks current files and register structure; it does not rehash absent historical blobs, clear their rights, or make the repository safe to publish.

## Release gate

Before a file is added to a release, maintainers must be able to answer all of these questions:

1. Who owns or authored it?
2. What license permits redistribution?
3. Does it contain secrets, personal data, internal names, or local paths?
4. Can a clean checkout use it without an unavailable private dependency?
5. Is its behavior and limitation documented for users?

If any answer is unknown, keep the asset out of the public release and record the reason in an issue or release review. For a binary listed in the register, the row must be `cleared`, its SHA-256 must match the artifact, and its source, license, owner, and redistribution evidence must be recorded before a release can include or enable it. The inventory check can pass while the release gate remains blocked. Removing a file from the working tree does not remove it from Git history; history cleanup requires a separate, deliberate operation.

For a proposed **text-only** Git release, `python tools/validate_text_public_tree.py --ref HEAD` fails on known private/runtime paths, review-flagged Skills and common binary extensions in the committed tree. Run it against the index before committing (omit `--ref`); `--list-paths` prints details only in a trusted local environment. The tag CI also runs this path check. It is not a content/secret/license audit and cannot prevent an earlier push or clone from exposing tracked files. Passing it does not authorize publication or replace the binary evidence gate and human review.

## Current review flags

The following paths require explicit ownership or license confirmation before being advertised as public runtime dependencies:

- `.workspace-assistant/foundation/host-hooks/claude/claude-session-start.jar`
- `.workspace-assistant/foundation/host-hooks/codex/codex-session-start.jar`
- `.agents/skills/nest-rule-java/`
- `.agents/skills/nest-audit-java/`
- `.agents/skills/nest-audit-security-api/`
- `.agents/skills/nest-insights/`

This list is a review status, not a claim that the assets are forbidden to publish. Both SessionStart binary rows are now historical (`present: false`) and `pending`; see [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) for the evidence required before any reintroduction. The UUID19 JAR is likewise absent from the current tree but remains in Git history. Do not mark an item as cleared without evidence or claim that the Python migration cleaned historical blobs.
