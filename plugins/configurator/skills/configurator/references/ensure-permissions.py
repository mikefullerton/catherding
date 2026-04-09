#!/usr/bin/env python3
"""Read allowed-tools from SKILL.md frontmatter, merge Bash() patterns into settings.json."""

import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    skill_file = Path(sys.argv[1])
    settings_file = Path.home() / ".claude" / "settings.json"

    if not skill_file.exists() or not settings_file.exists():
        sys.exit(0)

    # Read SKILL.md, extract frontmatter between --- markers
    content = skill_file.read_text()
    match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        sys.exit(0)

    frontmatter = match.group(1)

    # Find allowed-tools line, extract Bash() patterns
    for line in frontmatter.splitlines():
        if line.startswith("allowed-tools:"):
            patterns = re.findall(r"Bash\([^)]+\)", line)
            break
    else:
        sys.exit(0)

    if not patterns:
        sys.exit(0)

    # Read settings, merge patterns, deduplicate, write back
    settings = json.loads(settings_file.read_text())
    existing = settings.get("permissions", {}).get("allow", [])
    merged = sorted(set(existing + patterns))

    if merged == sorted(existing):
        sys.exit(0)  # No changes needed

    settings.setdefault("permissions", {})["allow"] = merged
    settings_file.write_text(json.dumps(settings, indent=2) + "\n")


if __name__ == "__main__":
    main()
