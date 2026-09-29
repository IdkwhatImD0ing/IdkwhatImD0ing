# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`), designed as **ART3M1S OS on `tianni`**: the page is one tmux session on a machine you boot. `tianni` (天逆) is named after the Heaven Defying Bead from *Renegade Immortal*: the PC as a cultivator's natal treasure, with an old soul (the LLM daemon) living inside it. The hero boots ART3M1S and shows the attached session; each section below is a tmux window (`0:boot`, `1:ships`, `2:fsck`, `3:etc`) introduced by a status-bar image whose green chip moves one window right; the page ends with `tmux detach`. Much of the page is written by the machine itself (GitHub Actions + an LLM daemon) and by visitors (issue-ops). There is no build/lint/test setup — only stdlib Python scripts in `scripts/` that CI and issue events run.

**Fiction rules (apply to ALL user-visible text):** host `tianni`, user `bill`, ART3M1S OS. The hostname is the `HOST` constant in `scripts/phosphor.py` (with `MACHINE` and `PROMPT`); to rename the machine, change it there, update the hand-written prompts in README.md/.plan/man page/oneliners, and re-run every renderer. Voice: dry, deadpan sysadmin humor, always in-fiction. **No emoji, anywhere.** Never fake command output — gaps in real data get an in-fiction excuse (e.g. "log rotated"). Lines inside `<pre>` screens and code fences stay ≤72 visible chars so they fit the desktop column without scrolling (the one exception is the copy-paste `curl` line); phones show ~34 columns and scroll sideways, so put the meaning first on each line. Each fact appears once on the page (the 35/58 hackathon record lives only in the hero).

## Design system (`scripts/phosphor.py`)

Every SVG is drawn through this module (`import phosphor as ph`); never hand-write colors or fonts into an SVG.

- **Surface**: `#151B23` panels, rx 6 — GitHub's own code-block background, so drawn panes and real `<pre>`/fenced blocks read as one material. Light twin `#F6F8FA`.
- **Type**: GitHub's code font stack; all text via `ph.text`/`ph.runs`, locked to a 0.6em grid with `textLength` so columns align on every OS. Display type is the 5x7 dot matrix (`ph.dot_text`, unlit dots visible).
- **Color means something**: phosphor `#00FF41` = lit/won/active; amber `#FFB000` = warning or "you can act here"; red `#FF5555` = kernel panic only. Everything else is GitHub ink/muted gray. Use the CSS classes from `ph.css` (`fg mu acc acct accd tr gh chip ink warn red`...), never hex.
- **Light mode = "safe mode"**: the same drawing with `mode="light"` (amber accent). Served only through `<picture><source media="(prefers-color-scheme: light)">`, never via prefers-color-scheme inside an SVG (that follows the OS, not the GitHub theme). Safe-mode SVGs have no animation.
- **Motion**: t=0 is the finished frame. Animations only add motion on top of a complete picture; `ph.css` disables all of it under prefers-reduced-motion.
- **Phones**: any row built from inline images must be ≤279px wide to survive a 360px phone (GitHub's README column is 279px at 360, 309px at 390, ~831px at 1280, 846px at 1440). Phone variants are dark-only: they come first in the `<picture>` and compound media queries are not allowed.
- **Markup**: `<source>` order is phone (`(max-width: 600px)`) → light → `<img>`. Never compound media queries. Wrap every non-link image in a bare `<picture>` (GitHub auto-links a bare `<img>` to its raw file). Images that must abut have no whitespace between them and `align="top"`. No GitHub alerts, markdown tables, shields badges, footnotes, or third-party image services — each brings someone else's design system.

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it:

| Marker block / asset | Owner | Trigger |
|:--|:--|:--|
| `assets/hero.svg`, `hero-light.svg`, `hero-phone.svg` | `scripts/render_hero.py` (reads `assets/status.json`, `data/fsck/stats.json`, git log) | `profile-summary.yaml` + `terminal-hero.yaml` |
| `assets/status.json`, `BUILD_PLATE` | `scripts/update_currently_building.py` (LLM → obsession, motd, htop processes) | `profile-summary.yaml` cron |
| `HACKLOG` (+ `assets/ships/`) | `scripts/render_hacklog.py` (data: `var/log/hackathons.log` + `var/lib/ships.json`) | same workflow |
| `CRONTAB` | `scripts/render_crontab.py` (parses the workflow YAMLs + `git log --grep ^artemis-build`) | same workflow |
| `PASSWD` | `scripts/render_passwd.py` (stargazers) | same workflow + `watch` events |
| `FSCK` (+ `assets/fsck/panel-<seq>*.svg`) | `scripts/artemis_ops.py` (game state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `BOOT_ONELINER` | `scripts/artemis_ops.py` button easter egg (pool: `scripts/data/oneliners.txt`) | 1-in-10 button presses, silently |
| `assets/chrome/` (status bars, F-keys) | `scripts/render_chrome.py` | by hand, after design changes |
| `assets/fsck/tiles/{dark,light}/`, button, mkfs key | `python scripts/artemis_ops.py tiles` | by hand, after design changes |
| `bill.ansi` | `scripts/generate_ansi_card.py` (reads `assets/status.json`) | both scheduled workflows |

`CRONTAB`, `PASSWD`, `BOOT_ONELINER` and `BUILD_PLATE` live inside HTML `<pre>` screens and all their content is HTML-escaped. `CRONTAB`/`PASSWD` start at the end of the prompt line and end right before `</pre>`; the footer `<pre>` holds `BOOT_ONELINER` and `BUILD_PLATE` back to back, and `replace_block`'s newlines leave a blank line around the build plate on purpose. `var/lib/ships.json` is hand-maintained and read-only to scripts (repo, payload, fallback stats per ship); if it is missing or malformed `render_hacklog.py` fails closed and keeps the old panes. Hand-crafted: breadcrumb files (`.plan`, `README.md.bak`, `man/bill.1.md`), the `/mnt` details (pkg list + the STL lander, which GitHub renders as a 3D viewer), the raw-source hex comment.

## The fsck game (issue-ops)

Visitors play minesweeper by opening issues titled `artemis|fsck|C4` (scan), `artemis|fsck|reformat`, `artemis|button` (the DO NOT PRESS key), or `sudo make me a sandwich` (the footer's `C-b ? help`). `artemis-ops.yaml` routes them: eyes-reaction ack → `python scripts/artemis_ops.py process --title ... --actor ... --issue N` (stdout = the in-character reply to post) → commit README + `data/fsck/` + `assets/fsck/` → comment + close. Titles are passed via env var only (injection guard) and matched against a strict regex; everything else with an `artemis|` prefix gets an in-character "command not found". The status panel's file name carries a `seq` counter from `stats.json` (`panel-<seq>.svg`, bumped on every op; the previous set is kept, older ones are pruned), because GitHub's `/raw/` redirect drops query strings and the raw CDN caches a path for five minutes. The board needs a viewport of at least ~350px; below that its rows wrap. The engine has a full assertion suite: `python scripts/artemis_ops.py self-test`.

## Running things locally

Always from the repo root (scripts resolve `README.md` and state relative to CWD):

```powershell
python scripts/update_currently_building.py --fallback-only  # status.json + BUILD_PLATE, no OpenAI needed
python scripts/render_hero.py --dry-run                      # seed/program/journal without writing
python scripts/render_hero.py                                # hero.svg, hero-light.svg, hero-phone.svg
python scripts/render_hero.py --program kernel_panic --out-dir .preview/hero/out  # force a boot program
python scripts/render_hacklog.py                             # HACKLOG ship panes
python scripts/render_crontab.py                             # CRONTAB from workflow files + git log
python scripts/render_passwd.py                              # PASSWD; without GITHUB_TOKEN it warns and exits 0
python scripts/artemis_ops.py self-test                      # game engine test suite
python scripts/artemis_ops.py render                         # FSCK block + panel SVGs from current state
python scripts/render_chrome.py                              # static status bars + F-keys
python scripts/generate_ansi_card.py                         # regenerates bill.ansi
```

Env vars: `OPENAI_API_KEY`/`OPENAI_MODEL`/`REQUIRE_OPENAI` (LLM path), `GITHUB_TOKEN` (rate limits, star dates, GraphQL contributions), `GITHUB_SHA`/`GITHUB_RUN_NUMBER` (build stamps + boot seed; without `GITHUB_SHA` the hero seeds from the ISO week). Everything is stdlib-only. To preview the README the way GitHub renders it, POST it to the `/markdown` API (`gh api -X POST markdown -f mode=gfm -F text=@README.md`) and wrap it in github-markdown-css.

## Architecture constraints

- **Concurrency**: every workflow that writes to `main` shares the `profile-readme-writes` concurrency group and runs `git pull --rebase --autostash` before committing. Preserve both in any new workflow.
- **Never blank a block**: scripts only replace marker content (or write SVGs) on a successful non-empty render; on API failure they warn and exit 0. A bad API day must not damage the README. If the LLM call fails, `update_currently_building.py` keeps the previous `status.json` bio (with its original dates) and commits as `artemis: llm offline, ...`; only real rewrites are titled `artemis-build N:`, which is what the CRONTAB receipts and the hero journal grep for.
- **Missing markers are a no-op**: renderers warn+exit 0 if markers are absent, so script and README changes can land independently.
- **Scheduled-workflow decay**: GitHub disables cron workflows after 60 days without repo activity; the twice-weekly `profile-summary` bot commits (the build plate changes every run) plus the weekly boot reroll are the de facto keepalive. Don't "clean up" the cron cadence to something rarer.
- **Game integrity**: mine positions are never persisted — they are HMAC-derived from the optional `FSCK_SALT` Actions secret (unset → public fallback salt, and the panel renders an in-fiction admission that the map is derivable). Setting/rotating the secret mid-board auto-reformats by design. State stores only revealed cells with their earned adjacency digits.
- **passwd rendering needs auth**: the stargazers endpoint 401s unauthenticated; `GITHUB_TOKEN` is always set in CI. `render_passwd.py` renders nothing without `GITHUB_TOKEN` (it warns and leaves the block alone). The hackathon log at `var/log/hackathons.log` holds only verified "greatest hits" — Bill appends one line per event (and a `var/lib/ships.json` record for its repo/payload). The lifetime 35/58 totals are `WON`/`ENTERED` in `render_hero.py` (`generate_ansi_card.py` imports them); hand-written copies to update with them: the hero `alt` text in README.md, `man/bill.1.md` (`--hackathon`), the `hackathons.log` header, and `.plan`'s win rate.
- **No third-party widgets**: the old metrics/skyline/snake/pin-card/shields/typing-SVG widgets were retired for consistency. If something new is needed, draw it locally through `phosphor.py`.
- `scripts/update_playbook_posts.py` is library-only (imported by `update_currently_building.py`); its own `main()` targets markers that no longer exist.
