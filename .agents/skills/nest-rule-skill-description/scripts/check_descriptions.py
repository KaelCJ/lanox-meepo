"""Validate SKILL.md frontmatter files against Agent Skills hard constraints.

Usage:
    python check_descriptions.py --root <directory containing skill folders>

Checks each */SKILL.md under --root:
- frontmatter is valid YAML and a mapping
- name: present, kebab-case, <= 64 chars, matches the parent directory name
- description: present, non-empty string, <= 1024 chars

Exit code 1 when any failure exists. Requires PyYAML.
"""

import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is required: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(raw):
    lines = raw.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        raise ValueError("missing opening --- frontmatter delimiter")
    end = next((i for i, l in enumerate(lines) if i > 0 and l.rstrip("\r") == "---"), None)
    if end is None:
        raise ValueError("missing closing --- frontmatter delimiter")
    data = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def check(root):
    failures = 0
    paths = sorted(glob.glob(os.path.join(root, "*", "SKILL.md")))
    if not paths:
        print("no SKILL.md files found under %s" % os.path.abspath(root))
        return 0
    for path in paths:
        skill = os.path.basename(os.path.dirname(path))
        try:
            with open(path, encoding="utf-8") as handle:
                fm = parse_frontmatter(handle.read())
            name = fm.get("name")
            desc = fm.get("description")
            if not isinstance(name, str) or not NAME_RE.match(name):
                raise ValueError("invalid name %r" % (name,))
            if len(name) > 64:
                raise ValueError("name longer than 64 chars")
            if name != skill:
                raise ValueError("name %r does not match directory %r" % (name, skill))
            if not isinstance(desc, str) or not desc.strip():
                raise ValueError("description missing or empty")
            if len(desc) > 1024:
                raise ValueError("description is %d chars (> 1024)" % len(desc))
            print("OK   %-28s desc=%d chars" % (skill, len(desc)))
        except Exception as exc:
            failures += 1
            print("FAIL %-28s %s" % (skill, exc))
    return failures


def main():
    parser = argparse.ArgumentParser(description="Validate SKILL.md frontmatter against Agent Skills hard constraints")
    parser.add_argument("--root", default=".", help="directory containing skill folders")
    args = parser.parse_args()
    failures = check(args.root)
    print("failures:", failures)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
