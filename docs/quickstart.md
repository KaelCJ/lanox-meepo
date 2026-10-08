# 5-minute offline Quickstart (pre-release)

This is a local smoke test, **not a public download or release procedure**. Use a source checkout you already have permission to use. Do not clone or distribute the full repository as a text-only installer: its Git history retains three former JARs and tracked private workspace records still require review. This procedure neither runs nor copies the historical JARs or the Python host hooks.

## Prerequisites

- Python 3.10 or newer
- An authorized local source checkout of this project
- A disposable target project directory with no `.agents/` or `.claude/`
- Claude Code for the optional manual host check; the file-level smoke test does not require it

## Copy only the initial text workflow

From the **source checkout's root**, create a disposable target and run the allowlist installer:

```bash
mkdir ../nest-demo-target
python tools/install_text_core.py --target ../nest-demo-target
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Path ..\nest-demo-target
python tools/install_text_core.py --target ..\nest-demo-target
```

The installer copies only the `nest-audit-entry` and `nest-work-item` Skills, the work-item's required text references/script/schema, and their two Claude Code command wrappers. It does not copy the source repository's `AGENTS.md` or `CLAUDE.md`: those rules are specific to **this** project, not your target. It does not copy `.codex/hooks.json`, `.workspace-assistant/`, other Skills, local settings, worktrees or binaries. The installer refuses a target that already has `.agents/` or `.claude/`; it does not merge or overwrite existing customizations.

## Validate the target entry and work-item index

Create your own `AGENTS.md` at the target root with rules for **that** project. For this disposable example, a heading such as `# Demo target` is enough. Create `CLAUDE.md` in the same directory containing exactly `@AGENTS.md` (no other text or UTF-8 BOM). Neither file is supplied by the installer.

From the source checkout, check the **target directory**, not the source tree:

```bash
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --directory ../nest-demo-target
```

A passing result should say `PASS: 1 entry pair(s)`. A missing pair is an error with `--directory`; discovering zero pairs under a root is not proof that the target's rules loaded in either host.

In the disposable target, you may try the installed work-item index without Java:

```bash
python ../nest-demo-target/.agents/skills/nest-work-item/scripts/work_item_index.py --root ../nest-demo-target/.workspace-assistant/10-工作项 init
python ../nest-demo-target/.agents/skills/nest-work-item/scripts/work_item_index.py --root ../nest-demo-target/.workspace-assistant/10-工作项 validate
```

These paths assume the commands are run from the source checkout and the target is a sibling. The initialized target index is disposable test data; never copy this repository's real `.workspace-assistant/10-工作项/` records. The installer itself does not create an index or change business code.

## Optional manual Claude Code check

Open a **new** Claude Code session in the disposable target, then invoke `/nest-audit-entry` to inspect its entry pair (read-only). Optionally ask the installed `nest-work-item` Skill to create a synthetic work item containing only a request and acceptance criteria, without modifying application code. Confirm that the command/Skill is discovered, the target's own rules are used, and the recorded result matches what actually happened. The static tests below cannot establish host discovery or rule execution; a clean Claude Code/Codex end-to-end run is still outstanding.

## Run source checks

From the source checkout's root:

```bash
python -m compileall -q .agents/skills tools
python -m unittest discover -s tools -p 'test_*.py'
python .agents/skills/nest-rule-entry/scripts/validate_entry_pairs.py --root . --exclude .claude/worktrees
python tools/validate_binary_register.py
```

The unit tests create a disposable target, verify the copied file list, reject existing target assets or missing source files, validate a synthetic target entry pair, and exercise the installed UUID4 index. The CI workflow is configured to run these tests on Ubuntu and Windows, but its actual GitHub Actions run has not yet been verified. An inventory pass checks the *current* source tree and records the removed JARs without rehashing absent historical blobs; `python tools/validate_binary_register.py --require-cleared` is intentionally blocked while their history and permission remain unresolved.

## Python SessionStart handlers (not installed here)

For maintainers of this checkout, `tools/session_start.py claude` and `tools/session_start.py codex` read the UTF-8 context at `.workspace-assistant/foundation/host-hooks/session-start-context.md` and emit host-specific JSON. The Codex project configuration invokes the Python handler for `startup|clear|compact`; this repository has no Claude Code project-level SessionStart configuration, so the Claude handler is available but not automatically enabled. The old JARs were removed from the current working tree, not from Git history. `python -m unittest discover -s tools -p 'test_*.py'` exercises both outputs with synthetic context without contacting either host; it does **not** prove either host loads the hook.

## Current limits

This offline copy is not proof of author ownership, redistribution rights, safe Git history, or a usable public installation channel. The source Git tree still tracks private work-item records and unreviewed assets; the former JARs remain in Git history even after their current-tree removal. Do not publish an archive, tag or installer from this checkout until the [public scope policy](public-scope.md) and [binary evidence register](../THIRD_PARTY_NOTICES.md) are satisfied. Existing projects with `.agents/` or `.claude/`, Python host-hook wiring, and real clean-host end-to-end behavior remain outside this first smoke test.
