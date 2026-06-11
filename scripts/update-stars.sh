#!/usr/bin/env bash
# Regenerate the "Recently starred" section of README.md from the GitHub API,
# excluding repos owned by the profile owner. Run from the repo root.
set -euo pipefail

USER="elleryfamilia"
LIMIT=6

list=$(gh api "users/$USER/starred?per_page=50" --jq "
  [.[] | select(.owner.login != \"$USER\")][:$LIMIT][] |
  \"- [**\(.full_name)**](\(.html_url)) · ☆ \(
      if .stargazers_count >= 1000
      then \"\(.stargazers_count / 100 | round / 10)k\"
      else \"\(.stargazers_count)\"
      end
    )\(if .description then \" — \(.description)\" else \"\" end)\"
")

python3 - "$list" <<'EOF'
import re, sys
body = sys.argv[1]
readme = open("README.md").read()
new = re.sub(
    r"(<!-- STARS:START -->\n).*?(\n<!-- STARS:END -->)",
    lambda m: m.group(1) + body + m.group(2),
    readme,
    flags=re.S,
)
open("README.md", "w").write(new)
EOF
