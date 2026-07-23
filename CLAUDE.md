# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`), designed as **WHITEBOX/OS — ART3M1S Rev 5080**: the page pretends to be a machine you boot. Every section is a command output; much of the page is written by the machine itself (GitHub Actions + an LLM daemon) and by visitors (issue-ops). There is no build/lint/test setup — only Python scripts in `scripts/` that CI and issue events run.

**Fiction rules (apply to ALL user-visible text):** host `whitebox`, user `bill`, ART3M1S OS. Green phosphor `#00FF41` on `#0D1117`; amber `#FFB000` for warnings. Voice: dry, deadpan sysadmin humor, always in-fiction. **No emoji, anywhere.** Never fake command output — gaps in real data get an in-fiction excuse (e.g. "log rotated"). Fence lines stay ≤72 chars for mobile.

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it:

| Marker block | Owner | Trigger |
|:--|:--|:--|
| `CURRENTLY_BUILDING`, `MOTD`, `BUILD_PLATE` (+ `assets/status.json`) | `scripts/update_currently_building.py` | `profile-summary.yaml` cron |
| `HACKLOG` | `scripts/render_hacklog.py` (data: `var/log/hackathons.log`) | same workflow |
| `CRONTAB` | `scripts/render_crontab.py` (parses the workflow YAMLs) | same workflow |
| `PASSWD` | `scripts/render_passwd.py` (stargazers) | same workflow + `watch` events |
| `FSCK` | `scripts/artemis_ops.py` (game state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `BOOT_ONELINER` | `scripts/artemis_ops.py` button easter egg (pool: `scripts/data/oneliners.txt`) | 1-in-10 button presses, silently |
| `SCREENSAVER` | `scripts/update_screensaver.py` (snake/pacman by ISO week) | `screensaver.yaml` cron |

Machine-generated assets (don't hand-edit): `assets/terminal-hero.gif` (gifos, CI-only — the "boot program of the week" is seeded from the commit SHA, 1-in-8 kernel-panic gag), `assets/neofetch.svg`, `bill.ansi`, `assets/github-metrics.svg` + `assets/github-skyline.svg` (lowlighter/metrics), snake/pacman SVGs (live on the `output` branch, not main). Hand-crafted: `assets/safe-mode.svg` (the light-mode hero — the `<picture>` element serves it to light-mode visitors), fsck tiles, breadcrumb files (`.plan`, `README.md.bak`, `man/bill.1.md`), the STL lander embedded in README.

## The fsck game (issue-ops)

Visitors play minesweeper by opening issues titled `artemis|fsck|C4` (scan), `artemis|fsck|reformat`, `artemis|button`, or `sudo make me a sandwich`. `artemis-ops.yaml` routes them: eyes-reaction ack → `python scripts/artemis_ops.py process --title ... --actor ... --issue N` (stdout = the in-character reply to post) → commit README + `data/fsck/` → comment + close. Titles are passed via env var only (injection guard) and matched against a strict regex; everything else with an `artemis|` prefix gets an in-character "command not found". The engine has a full assertion suite: `python scripts/artemis_ops.py self-test`.

## Running things locally

Always from the repo root (scripts resolve `README.md` and state relative to CWD):

```powershell
python scripts/update_currently_building.py --fallback-only  # all blocks, no OpenAI needed
python scripts/render_hacklog.py                             # HACKLOG from var/log/hackathons.log
python scripts/render_crontab.py                             # CRONTAB from workflow files
python scripts/render_passwd.py                              # PASSWD (GITHUB_TOKEN avoids rate limits)
python scripts/update_screensaver.py                         # SCREENSAVER for current ISO week
python scripts/artemis_ops.py self-test                      # game engine test suite
python scripts/generate_terminal_hero.py --dry-run           # seed/program/stats without gifos
python scripts/generate_neofetch.py                          # needs pillow; falls back gracefully
python scripts/generate_ansi_card.py                         # regenerates bill.ansi
```

Env vars: `OPENAI_API_KEY`/`OPENAI_MODEL`/`REQUIRE_OPENAI` (LLM path), `GITHUB_TOKEN` (rate limits + GraphQL contributions), `GITHUB_SHA`/`GITHUB_RUN_NUMBER` (build stamps + weekly seed). All scripts are stdlib-only except `generate_neofetch.py` (pillow) and `generate_terminal_hero.py` (gifos + ffmpeg, CI-only — use `--dry-run` locally).

## Architecture constraints

- **Concurrency**: every workflow that writes to `main` shares the `profile-readme-writes` concurrency group and runs `git pull --rebase --autostash` before committing. Preserve both in any new workflow.
- **Output branch**: contribution-graph animations are force-pushed to the `output` branch (`screensaver.yaml`) so weekly regens don't pollute `main` history. README references them via `raw.githubusercontent.com/.../output/*.svg`.
- **Never blank a block**: scripts only replace marker content on a successful non-empty render; on API failure they warn and exit 0. Keep that contract — a bad API day must not damage the README.
- **Missing markers are a no-op**: renderers warn+exit 0 if markers are absent, so script and README changes can land independently.
- **Scheduled-workflow decay**: GitHub disables cron workflows after 60 days without repo activity; the twice-weekly bot commits are the de facto keepalive. Don't "clean up" the cron cadence to something rarer.
- **Game integrity**: mine positions are never persisted — they are HMAC-derived from the optional `FSCK_SALT` Actions secret (unset → public fallback salt, and the board renders an in-fiction admission that the map is derivable). Setting/rotating the secret mid-board auto-reformats by design. State stores only revealed cells with their earned adjacency digits.
- **passwd rendering needs auth**: the stargazers `star+json` endpoint 401s unauthenticated; `render_passwd.py` only works with `GITHUB_TOKEN` set (always true in CI). The hackathon log at `var/log/hackathons.log` holds only verified "greatest hits" — Bill appends one line per event; the lifetime 35/58 totals live in `render_hacklog.py`'s rotation-gag line.
- **Fragile externals**: `github-stats-extended.vercel.app` (pin cards — the original github-readme-stats.vercel.app is dead, do not revert to it), `readme-typing-svg.demolab.com`, komarev, shields.io. gifos upstream is dormant-but-working. If a widget dies, prefer replacing it with a locally-generated SVG.
- `scripts/update_playbook_posts.py` is library-only (imported by `update_currently_building.py`); its own `main()` targets markers that no longer exist.
