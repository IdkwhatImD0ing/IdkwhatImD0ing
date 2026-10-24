# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`, public), designed as a visit to **日月神教, the Sun Moon Divine Sect**: the same floating xianxia sect as his site https://art3m1s.me (日月神教 is the sect of Jin Yong's *The Smiling, Proud Wanderer*). The page follows the site's own flight order, one section per place, each introduced by a banner image that links to the next ("fly on"):

山门 Mountain Gate (hero, talisman keys) → 心镜台 Heart-Mirror Terrace (identity card) → 炼器峰 Artifact Forge Peak (projects) → 论剑台 Sword-Discussion Arena (hackathon record) → 任务殿 Mission Hall (experience + the steward's board) → 藏经阁 Scripture Pavilion (education, relics) → 碑林 Stele Forest (skills) → 护宗大阵 Grand Sect-Protecting Formation (the minesweeper + the timetable) → 洞府 Cave Abode (personal) → 望月台 Moon-Gazing Terrace (register, contact, footer).

Bill is the 教主, the Sect Leader. The page is partly hand-written and partly written by the sect itself: the **steward** (执事, an LLM, `update_currently_building.py`) reposts the mission board twice a week, the **elders** (GitHub Actions workflows) keep the bell-and-drum timetable, and **visitors** write to it by petition (issues) and by starring the repo (they become 外门弟子, outer disciples). It must still read as a great engineer profile a recruiter can scan in 20 seconds: who Bill is, what he builds, wins, projects, skills, links. There is no build/lint/test setup: stdlib Python scripts in `scripts/` that CI and issue events run, plus a few local-only generators.

The sect's previous life was a machine called `tianni` (ART3M1S OS): the Heaven Defying Bead cracked open and there was a sect inside it the whole time; the old soul in the bead took the job of steward; the DO NOT PRESS button became a sealed gong. That page is preserved in `archive/whitebox-os/`.

## Fiction rules (apply to ALL user-visible text)

- **In fiction, always.** Dry, deadpan wit about real work is the house voice ("the elders are not judging. they are timing."). The old sysadmin jokes became sect jokes.
- **The English name is always "Sun Moon Divine Sect".** The site used an older English name until its rename on 2026-10-23; that old last word never appears outside `archive/` (check: a case-insensitive whole-word search for it in tracked files outside `archive/` finds nothing; "cultivation" is fine).
- **No emoji, anywhere.**
- **Every Chinese term is glossed in English nearby** (same line, the same alt text, or the banner directly above). Chinese only appears where nothing after it on that line has to align.
- **Facts about Bill are never invented.** Sources: this README's existing facts, the site's data (the PortfolioV5 repo's `client/src/lib/portfolio-data/**`, read-only), and art3m1s.me. If the data has a gap, the page gives an in-fiction excuse; it never makes something up.
- **Never fake command output or data.** Everything a block shows comes from real files, git, or the GitHub API.
- **Width:** every line inside a `<pre>` or a code fence is at most 72 display columns, counting a CJK character as 2 (`readme_blocks.display_cols`). The copy-paste `curl` line is the one exception. Phones show ~34 columns and scroll sideways, so put the meaning first on each line.
- **Both themes are designed:** dark (gold on ink) and light (ink on aged paper), via `<picture>` with `prefers-color-scheme`. Phones always get the dark drawings ("on a phone you always fly at night").

## Design system (`scripts/ink.py`)

Every SVG is drawn through `ink.py`; never hand-write colours or fonts into an SVG.

| Token | Dark | Light | Means |
|:--|:--|:--|:--|
| ground | #0E0C14 | #F4ECDC | panel ground (the site's ink and paper) |
| raised / track / line | #1B1826 / #2A2433 / #4D402C | #EBE0C8 / #DDD0B4 / #C4AE86 | tablets and keys / unlit cells / hairlines |
| text / muted | #F5ECDC / #A89F91 | #1F1A17 / #6B5F50 | body / labels |
| gold | #E9C77E | #7A5518 | lit, won, active |
| ember | #C98A4B | #A0742C | meters, glow (never small text in light) |
| jade | #8FE3C8 | #2C6E5A | "you can act here", qi |
| seal | #B8412D | #A8321F | seal fills only |
| danger | #F0A089 | #A8321F | the formation's backlash and qi deviation, nothing else |

- **Type is drawn as glyph outlines, never `<text>`**: `scripts/ink_glyphs/<face>.json` (cut locally by `generate_glyphs.py` from SIL OFL fonts, licences committed next to them). Faces: Ma Shan Zheng (brush, Chinese display >= 16px), Noto Serif SC (small Chinese), Instrument Serif (display), Geist 400/500 (body), Geist Mono (data). A character missing from its table raises, and the renderer keeps the old files. Adding new Chinese copy to an SVG means re-running `generate_glyphs.py` first.
- **Motion:** the SVG with all animation removed is the finished picture; animation only adds motion. Every animated SVG carries `@media (prefers-reduced-motion: reduce){*{animation:none!important}}`. Light SVGs contain no `@keyframes` at all.
- **Markup:** `<source>` order is phone (`(max-width: 600px)`, always the dark file) → light → `<img>`. Never combine a width query with `prefers-color-scheme` in one `media` (GitHub's `themed-picture` rewrites the colour-scheme part). The hero adds reduced-motion stills; GitHub's sanitizer keeps those sources (checked 2026-10-24). Wrap every non-link image in a bare `<picture>` (GitHub auto-links a bare `<img>`). Inline-image rows must be <= 279px wide to survive a 360px phone (README column: 279px at 360, 309px at 390, ~831px at 1280, 846px at 1440). No markdown tables, shields, GitHub alerts, footnotes or third-party image services on the page.
- **Ornaments** reuse the site's own path data (cloud corners, brush strokes, the ink ring, the worn seal, the sun-and-moon logo).

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it. Marker names are the old ones on purpose (invisible to readers; renaming one means changing the script and README together).

| Marker block / asset | Owner | Trigger |
|:--|:--|:--|
| `HACKLOG` (+ `assets/forge/<slug>{,-light,-phone}.svg`) | `scripts/render_hacklog.py`, drawing in `art_forge.py` (data: `var/log/hackathons.log` + `var/lib/ships.json`) | `profile-summary.yaml` |
| `FSCK` (+ `assets/formation/panel-<seq>*.svg`) | `scripts/artemis_ops.py`, drawing in `art_formation.py` (state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `CRONTAB` (timetable + the steward's ledger) | `scripts/render_crontab.py` (workflow YAMLs + `git log -E --grep "^(artemis-build\|steward) [0-9]+:"`) | `profile-summary.yaml` |
| `PASSWD` (the disciple register) | `scripts/render_passwd.py` (stargazers) | `profile-summary.yaml` + `watch` events |
| `BOOT_ONELINER` (footer line) | `scripts/artemis_ops.py` gong easter egg (pool: `scripts/data/oneliners.txt`) | 1 in 10 gong strikes, silently |
| `BUILD_PLATE` + `assets/status.json` | `scripts/update_currently_building.py` (the steward: missions, note, cultivation) | `profile-summary.yaml` |
| `assets/mirror/card*.svg`, `assets/hall/board*.svg` | `scripts/render_card.py` (status.json, `data/fsck/`, git log, GitHub API) | `profile-summary.yaml` + `moon-watch.yaml` |
| `bill.ansi` (the terminal talisman) | `scripts/generate_ansi_card.py` | both scheduled workflows |
| `assets/gate/*.webp` (hero) | `scripts/generate_gate.py` from captured frames | by hand (local, Pillow) |
| `assets/keys/`, `assets/banners/`, `assets/seal/` | `scripts/generate_chrome.py` | by hand |
| `assets/arena/record*.svg` | `scripts/generate_arena.py` | by hand, when the record changes |
| `assets/formation/tiles/**`, `gong*.svg`, `relay*.svg` | `scripts/generate_tiles.py` (= `artemis_ops.py tiles`) | by hand, after design changes |
| `assets/relics/heimuling.stl` (黑木令, the Black Wood Token) | `scripts/generate_token_stl.py` | by hand |
| `scripts/ink_glyphs/*.json` | `scripts/generate_glyphs.py` | by hand, when copy adds characters |

`CRONTAB`, `PASSWD`, `BOOT_ONELINER` and `BUILD_PLATE` live inside HTML `<pre>` blocks and their content is HTML-escaped. `CRONTAB`/`PASSWD` start right after the bold heading and end right before `</pre>`; the footer `<pre>` holds `BOOT_ONELINER` and `BUILD_PLATE` back to back. `status.json` keeps its old schema: `processes` are the posted missions (`command` = mission name, `flags` = tags, `cpu` = qi devoted), `motd` is the steward's note, `obsession` is what the Sect Leader is in closed-door cultivation on. `render_card.py` imports `FALLBACK_MOTD, FALLBACK_OBSESSION, SEED_PROCESSES, clean_obsession, clean_processes, fit_motd, stable_pid` from `update_currently_building.py`; keep those names. `var/lib/ships.json` is hand-maintained and read-only to scripts; if it is missing or malformed `render_hacklog.py` fails closed and keeps the old artifacts. Hand-crafted: the relics (`.plan`, `README.md.bak`, `man/bill.1.md`), the back-shelf `<details>` with the STL fence (GitHub renders it as a 3D viewer), the raw-source hex comment, and all the section text.

Steward commit subjects: a real rewrite is `steward N: reposted the missions around X, kept the good ones` (the ledger and the board grep for `^(artemis-build|steward) N:`); the LLM down is `steward: the ink ran dry, kept the old missions (run N)`; the canned fallback is `steward: the ink ran dry, posted the standing missions (run N)`.

## The formation game (破阵, break the formation; issue-ops)

Visitors play minesweeper against the 护宗大阵 by opening issues. Titles (prefixes are case-sensitive, the cell letter is not):

| Title | Does | Legacy alias (still works) |
|:--|:--|:--|
| `sect\|zhen\|C4` | read one node | `artemis\|fsck\|C4` |
| `sect\|zhen\|relay` | re-lay a spent formation | `artemis\|fsck\|reformat` |
| `sect\|gong` | strike the sealed gong (勿敲 DO NOT STRIKE) | `artemis\|button` |
| `sudo make me a sandwich` | the kitchen hall declines | - |

`artemis-ops.yaml` routes them: eyes-reaction ack → `python scripts/artemis_ops.py process --title ... --actor ... --issue N` (stdout = the in-character reply; exit code always 0) → commit README + `data/fsck/` + `assets/formation/` → comment + close. A drain step answers up to 8 other queued petitions. Titles are passed via env vars only (injection guard) and matched against a strict regex; anything else with a `sect|` or `artemis|` prefix gets "the sect does not know the art ...". Replies never @-mention anyone. Stats keep logging the old op names (`fsck C4`, `reformat`, `button`); the view maps them for display (`step C4`, `re-lay`, `gong`). The engine never depends on the art: if `art_formation`/`ink` fail to import, the visitor still gets a reply and the board is simply not redrawn.

**Never change** `DEFAULT_SALT`, the HMAC message `board:{n}:first:{cell}`, `place_mines`, `MINE_COUNT`, the state/stats JSON keys or the `data/fsck/` paths: any of them silently corrupts the live board. The status panel's file name carries a `seq` counter from `stats.json` (`panel-<seq>.svg`, bumped on every op; the previous set is kept, older ones are pruned), because GitHub's `/raw/` redirect drops query strings and the raw CDN caches a path for five minutes. The board needs a viewport of at least ~350px. Full assertion suite: `python scripts/artemis_ops.py self-test` (must pass before any commit that touches the engine, the art modules or the one-liner pool).

## Running things locally

Always from the repo root (scripts resolve `README.md` and state relative to CWD):

```powershell
python scripts/artemis_ops.py self-test           # game engine + formation art test suite
python scripts/artemis_ops.py render              # FSCK block + panel SVGs from current state
python scripts/render_hacklog.py                  # HACKLOG forge artifacts (--offline, --dry-run)
python scripts/render_crontab.py                  # CRONTAB timetable + the steward's ledger
python scripts/render_passwd.py                   # PASSWD register; without GITHUB_TOKEN it warns and exits 0
python scripts/update_currently_building.py --fallback-only --status .preview/status.json  # BUILD_PLATE without touching the real status.json
python scripts/render_card.py --dry-run           # identity card + mission board (--offline, --omen NAME, --out-dir DIR)
python scripts/generate_ansi_card.py              # bill.ansi
```

Local-only generators (`generate_glyphs.py` needs fontTools; `generate_gate.py` needs Pillow; `generate_chrome.py`, `generate_arena.py`, `generate_tiles.py`, `generate_token_stl.py` are stdlib) never run in CI. Everything CI runs is stdlib-only.

Hero re-capture (the gate): Playwright at 1280x720 on https://art3m1s.me, wait ~12 s, hide every page element but the WebGL canvas (`body *{visibility:hidden!important} canvas{visibility:visible!important}`), then scroll from 0 to ~900 in eased steps taking a screenshot each (~80 frames) and hold ~20 frames at the gate. `generate_gate.py` crops to 2:1, composites the title overlay, loops, and encodes the five WebPs (hero <= 6 MB, still <= 400 KB, light <= 600 KB, phone <= 3 MB, phone still <= 250 KB). Never run Blender for this.

Env vars: `OPENAI_API_KEY`/`OPENAI_MODEL`/`REQUIRE_OPENAI` (the steward), `GITHUB_TOKEN` (rate limits, star dates, contributions), `GITHUB_SHA`/`GITHUB_RUN_NUMBER` (build plate and commit subjects), `FSCK_SALT` (seals the formation). Preview the README the way GitHub renders it: `gh api -X POST markdown -f mode=gfm -F text=@README.md`, wrapped in github-markdown-css. Never print secrets.

## Architecture constraints

- **Concurrency:** every workflow that writes to `main` (`artemis-ops.yaml`, `profile-summary.yaml`, `moon-watch.yaml`) shares the `profile-readme-writes` concurrency group (no cancel) and runs `git pull --rebase --autostash origin main` before committing. Preserve both in any new workflow.
- **Never blank a block:** scripts only replace marker content (or write SVGs) after a successful, validated, non-empty render; on API failure they warn and exit 0. A bad API day must not damage the README. If the LLM call fails, the previous `status.json` (with its original dates) is kept.
- **Missing markers are a no-op:** renderers warn and exit 0 if their markers are absent, so script and README changes can land independently.
- **Scheduled-workflow decay:** GitHub disables cron workflows after 60 days without repo activity. The Mon/Thu steward run (`17 15 * * 1,4`; the build plate changes every run) and the Saturday moon watch (`41 14 * * 6`) are the de facto keepalive. Don't thin the cadence.
- **Game integrity:** trap positions are never persisted; they are HMAC-derived from the optional `FSCK_SALT` secret (unset → the public fallback salt, and the panel admits "honor system"). Rotating the secret mid-board re-lays the formation by design. State stores only read nodes with their earned digits.
- **The register needs auth:** the stargazers endpoint 401s unauthenticated; `GITHUB_TOKEN` is always set in CI. Without it `render_passwd.py` leaves the block alone.
- **The 35/58 record:** the lifetime totals (35 won of 58 entered) are `WON`/`ENTERED` in `scripts/ink.py`. Hand-written copies to update with them: the README (identity-card alt, arena record alt and the arena sentence), `man/bill.1.md` (`--hackathon`), the `var/log/hackathons.log` header, and `.plan`'s win rate; then re-run `generate_arena.py`. `hackathons.log` holds only verified greatest hits; Bill appends one line per event (plus a `var/lib/ships.json` record).
- **No third-party widgets:** metrics, skylines, snakes, pin cards, shields and typing SVGs were retired long ago. Anything new is drawn locally through `ink.py`.
- **Fragile externals fail soft:** OpenAI, the Hackathon Playbook RSS feed and the GitHub API all degrade to the last good data.
- `scripts/update_playbook_posts.py` is library-only (imported by `update_currently_building.py`); its own `main()` targets markers that no longer exist.

## Archive policy

Nothing is deleted. Retired files move to `archive/` (with `git mv` where they were tracked), and verbatim snapshots are taken from git history. `archive/` is a museum: kept verbatim, exempt from the fiction rules, never written by scripts, and nothing in it runs (GitHub only runs workflows in `.github/workflows/`). `archive/whitebox-os/` is the machine called tianni as found on 2026-10-24 at commit `a864764`: its README (links to petitions unwrapped, workflow links pinned to that commit), drawings, scripts, old CLAUDE.md, relics and the `terminal-hero.yaml` workflow. `archive/README.md` is the index.
