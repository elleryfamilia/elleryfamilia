#!/usr/bin/env python3
"""Render the README stat cards as static SVGs.

Fetches profile data with `gh api graphql` and writes light and dark variants
of each card to assets/cards/. Replaces the github-readme-stats.vercel.app
images, whose public instance is regularly paused. Run from the repo root.

Uses whatever token `gh` has. The Actions GITHUB_TOKEN only sees public data,
so private commits/repos are excluded unless a personal token is supplied
(see the CARDS_TOKEN secret in .github/workflows/metrics.yml).
"""
import html
import json
import subprocess
from pathlib import Path

USER = "elleryfamilia"
# repo -> fallback description, used when the repo has none on GitHub
PINS = {
    "zerminal": "A terminal-first development environment for agentic coding",
    "terminal-mcp": "A terminal emulator exposed via MCP for AI assistants",
    "thicc": "A terminal-first editor built for speed, personality, and AI-driven development",
    "loadout": "Composable context for AI coding agents",
}
OUT = Path("assets/cards")
LANG_COUNT = 6

FONT = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'
SIZE = 13
CHAR_W = SIZE * 0.6  # monospace advance width, used for wrapping
PAD = 16

# Same palette as assets/hero-*.svg so the cards read as one system.
THEMES = {
    "light": dict(bg="#f6f8fa", border="#d0d7de", text="#1f2328", muted="#57606a",
                  prompt="#1a7f37", link="#0969da", track="#eaeef2"),
    "dark": dict(bg="#161b22", border="#30363d", text="#c9d1d9", muted="#8b949e",
                 prompt="#3fb950", link="#58a6ff", track="#21262d"),
}

# Octicons (MIT, GitHub), 16px viewBox.
ICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "fork": "M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}

QUERY = """
query($user: String!) {
  user(login: $user) {
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
    }
    pullRequests { totalCount }
    issues { totalCount }
  }
  %s
}
"""
PIN_FRAGMENT = """
  %s: repository(owner: $user, name: "%s") {
    name description stargazerCount forkCount
    primaryLanguage { name color }
  }
"""


def fetch():
    pins = "".join(PIN_FRAGMENT % (f"pin{i}", name) for i, name in enumerate(PINS))
    out = subprocess.run(
        ["gh", "api", "graphql", "-F", f"user={USER}", "-f", f"query={QUERY % pins}"],
        check=True, stdout=subprocess.PIPE, text=True, encoding="utf-8",
    ).stdout  # stderr streams to the job log so API errors stay visible
    data = json.loads(out)["data"]
    if data.get("user") is None:
        raise SystemExit("graphql returned no user; check GH_TOKEN")
    return data


def esc(s):
    return html.escape(s, quote=True)


def fmt(n):
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def wrap(text, max_chars, max_lines):
    words = []
    for w in text.split():  # hard-split words wider than a line (URLs etc.)
        while len(w) > max_chars:
            words.append(w[:max_chars])
            w = w[max_chars:]
        words.append(w)
    lines, cur = [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"
    return lines


def icon(name, x, y, color, size=14):
    s = size / 16
    return (f'<path transform="translate({x} {y}) scale({s:.4f})" fill="{color}" '
            f'fill-rule="evenodd" d="{ICONS[name]}"/>')


def text(x, y, s, color, weight="normal", anchor="start", size=SIZE):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')


def card(width, height, t, body, title):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">',
        f'<title>{esc(title)}</title>',
        f'<g font-family=\'{FONT}\'>',
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="{t["bg"]}" stroke="{t["border"]}"/>',
        *body,
        "</g>",
        "</svg>",
    ]) + "\n"


def prompt_line(t, y, cmd):
    return [text(PAD, y, "$", t["prompt"], "600"),
            text(PAD + CHAR_W * 2, y, cmd, t["text"], "600")]


def stats_card(t, d):
    u = d["user"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    cc = u["contributionsCollection"]
    rows = [
        ("star", "Total stars earned", stars),
        ("commit", "Commits this year", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("pr", "Total PRs", u["pullRequests"]["totalCount"]),
        ("issue", "Total issues", u["issues"]["totalCount"]),
    ]
    w, row_h = 440, 24
    y0 = PAD + SIZE + 14
    h = y0 + row_h * len(rows) + 4
    body = prompt_line(t, PAD + SIZE - 2, f"gh stats {USER}")
    for i, (ic, label, val) in enumerate(rows):
        y = y0 + row_h * i + SIZE
        body.append(icon(ic, PAD, y - 12, t["prompt"]))
        body.append(text(PAD + 24, y, label, t["text"]))
        body.append(text(w - PAD, y, fmt(val), t["text"], "600", "end"))
    return card(w, h, t, body, f"{USER}'s GitHub stats")


def langs_card(t, d):
    sizes, colors = {}, {}
    for r in d["user"]["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            sizes[n] = sizes.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or t["muted"]
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:LANG_COUNT]

    w, col_w, row_h = 300, 134, 20
    bar_y = PAD + SIZE + 12
    list_y = bar_y + 8 + 18
    n_rows = (len(top) + 1) // 2
    h = list_y + row_h * n_rows + 4
    body = prompt_line(t, PAD + SIZE - 2, "gh langs")
    bar_w = w - 2 * PAD
    body.append(f'<clipPath id="bar"><rect x="{PAD}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>')
    body.append(f'<rect x="{PAD}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="{t["track"]}"/>')
    x = PAD
    for name, size in top:
        seg = bar_w * size / total
        body.append(f'<rect clip-path="url(#bar)" x="{x:.2f}" y="{bar_y}" width="{seg:.2f}" height="8" fill="{colors[name]}"/>')
        x += seg
    max_chars = int((col_w - 16) / (12 * 0.6))
    for i, (name, size) in enumerate(top):
        cx = PAD + col_w * (i % 2)
        cy = list_y + row_h * (i // 2) + SIZE
        label = f"{name} {100 * size / total:.1f}%"
        if len(label) > max_chars:  # e.g. "Jupyter Notebook 12.3%"
            label = label[: max_chars - 1].rstrip() + "…"
        body.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{colors[name]}"/>')
        body.append(text(cx + 16, cy, label, t["text"], size=12))
    return card(w, h, t, body, f"{USER}'s top languages")


def pin_card(t, repo, fallback):
    w, desc_lines = 400, 2
    max_chars = int((w - 2 * PAD) / CHAR_W)
    desc = repo["description"] or fallback
    lines = wrap(desc, max_chars, desc_lines)
    desc_y = PAD + SIZE + 16
    foot_y = desc_y + 18 * desc_lines + 10 + SIZE  # fixed height so pairs align
    h = foot_y + PAD - 2
    body = [icon("repo", PAD, PAD, t["muted"], 16),
            text(PAD + 24, PAD + SIZE - 1, repo["name"], t["link"], "600", size=14)]
    for i, line in enumerate(lines):
        body.append(text(PAD, desc_y + 18 * i + SIZE - 2, line, t["muted"], size=12))
    x = PAD
    lang = repo.get("primaryLanguage")
    if lang:
        body.append(f'<circle cx="{x + 5}" cy="{foot_y - 4}" r="5" fill="{lang["color"] or t["muted"]}"/>')
        body.append(text(x + 16, foot_y, lang["name"], t["text"], size=12))
        x += 16 + len(lang["name"]) * 12 * 0.6 + 20
    for ic, val in (("star", repo["stargazerCount"]), ("fork", repo["forkCount"])):
        body.append(icon(ic, x, foot_y - 12, t["muted"]))
        label = fmt(val)
        body.append(text(x + 20, foot_y, label, t["text"], size=12))
        x += 20 + len(label) * 12 * 0.6 + 20
    return card(w, h, t, body, f"{USER}/{repo['name']}: {desc}")


def main():
    d = fetch()
    OUT.mkdir(parents=True, exist_ok=True)
    for theme, t in THEMES.items():
        (OUT / f"stats-{theme}.svg").write_text(stats_card(t, d), encoding="utf-8")
        (OUT / f"langs-{theme}.svg").write_text(langs_card(t, d), encoding="utf-8")
        for i, (name, fallback) in enumerate(PINS.items()):
            repo = d[f"pin{i}"]
            if repo is None:
                raise SystemExit(f"repo {USER}/{name} not found")
            (OUT / f"pin-{name}-{theme}.svg").write_text(pin_card(t, repo, fallback), encoding="utf-8")
    print(f"wrote {len(list(OUT.glob('*.svg')))} cards to {OUT}/")


if __name__ == "__main__":
    main()
