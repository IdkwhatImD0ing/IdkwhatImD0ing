# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`, public). It is a **calling card at the gate of 日月神教, the Sun Moon Divine Sect**, the floating xianxia sect of his site https://art3m1s.me (日月神教 is the sect of Jin Yong's *The Smiling, Proud Wanderer*). One ink-wash picture sets the scene; then Bill speaks plainly, in the first person. The sect is the setting, never the speaker: seasoning, not the meal.

The page sentence: **"Bill Zhang builds voice-first LLM agents at Pinterest and has won 36 of 59 hackathons."** Everything on the page serves it. Top to bottom (about 2,050 px at 1280 wide):

| # | Element | Job (the visitor's question) | Rank |
|--:|:--|:--|:--|
| 1 | Hero: "Bill Zhang" (the biggest text on the page) over "builds voice-first LLM agents · Pinterest"; a small 日月神教 mark, its seal and gloss in the corner | Who is this, and what does he do? | Star |
| 2 | Keys: "Enter art3m1s.me" (the one jade key), Email, LinkedIn, Résumé | Where do I click next? How do I reach him? | Support |
| 3 | Intro, 3 sentences, fact first | What has he done, what does he care about? | Quiet |
| 4 | **Shipped**: 4 project cards (HACKLOG), the sword row (36 gold of 59), a short caption | What has he built that won? Is he good? | Support |
| 5 | **Work**: 6 roles, one line each; 2 education lines; 1 tools sentence | Where has he worked? | Quiet |
| 6 | **Now**: 3 real repos with a link, a date and one LLM sentence (NOW); one `<sub>` "How it works" line | What is he working on this week? | Quiet |
| 7 | **Play**: one closed `<details>` with the formation game, the gong, the disciple register, the terminal line, the relics and the steward's seal (the build plate) | Is there anything fun here? | Quiet |
| 8 | Footer line and the 日月 seal, centred | How do I reach him, now that I've read it? | Quiet |

The page is partly hand-written and partly written by the sect itself: the **steward** (an LLM, `update_currently_building.py`) writes the Now lines twice a week from Bill's real public commits, the **elders** (GitHub Actions) run the game and keep the page alive, and **visitors** play the formation by petition (issues) and join the register by starring the repo. There is no build/lint/test setup: stdlib Python scripts in `scripts/` that CI and issue events run, plus a few local-only generators.

The page's previous lives are in `archive/`: the machine called `tianni` (`archive/whitebox-os/`) and the first, nine-banner sect page (`archive/sun-moon-v1/`).

## The intent standard (every change is checked against this)

Intent means every part has a job you can name, and the jobs are ranked: one star, two or three helpers, a quiet rest. The full standard is the r49 `intent.md` checklist; in short:

- **C1 One purpose.** The page sentence above. "Bill Zhang" is the biggest text on the first screen.
- **C2 Reading order.** Name and line, the jade key, the intro, Shipped (cards, then swords), Work, Now, Play (closed), footer. Nothing ties for first; no decoration is read before the name.
- **C3 Few big shapes.** One primary block (the hero), three secondary (the jade key, the cards, the sword row), everything else an even texture of plain text.
- **C4 Every element has a job** (the table above). No job: cut it. Same job as another element: merge them.
- **C5 Designed quiet.** 56 px between sections, 16 px inside one (ratio 3.5).
- **C6 Never twins.** 6 text sizes at most; headings of different rank never share a size.
- **C7 Colour points.** One accent (jade, on one key). Gold means won. Seal red on 2 seals only.
- **C8 Detail where the eye goes.** Brush lettering, seals and cloud corners only in the hero and the footer.
- **C9 Composed edges.** One left edge. Only the hero and the footer seal are centred.
- **C10 Pull forward.** One filled key; the pinned repos show by the third screen (about 2,400 px).
- **C11 Rhythm.** Who, proof, work, now, then play (folded).
- **C12 One system, one voice.** Two materials (ink pictures, plain GitHub text), 3 drawn faces, one narrator (Bill, first person), no grey code boxes outside the fold.
- **C13 Honest.** Every number and date is real; at most one sentence explains how the page works.
- **C14 The theme is seasoning.** Cover the hero mark, "Enter", "the steward", the footer's last sentence and the seal: who, what, proof and contact must remain.

**Counts outside the Play fold** (check them after any change): height at 1280 about 2,000 px (2,200 at most); 3 section headings; 2 seals; at most 15 images (today 14) and 45 links (today 17); 6 text sizes; 3 drawn faces; 1 accent colour; 0 code boxes; 2 centred blocks. **The 5-second test:** show the first screen for 5 seconds at 1280x800 (dark and light) and on a 385 px phone; a stranger must answer who ("Bill Zhang"), what ("builds voice-first LLM agents at Pinterest") and where to click ("the green art3m1s.me button"). A new element must name its job and its rank, and take the place of something, not add to the pile.

## Voice and fiction rules (apply to ALL user-visible text)

- **Outside the fold, Bill speaks:** first person, plain, fact first. No jokes in Shipped or Work; one dry line at most elsewhere (the footer's "The gate closes behind you."). The only sect words outside the fold: the hero mark, "Enter" on the jade key, "the steward" in the Now line, the footer's last sentence, and the seal.
- **Inside the Play fold, the sect speaks:** dry, deadpan wit about real work is the house voice there ("the elders are not judging. they are timing.").
- **The English name is always "Sun Moon Divine Sect".** The site used an older English name until its rename on 2026-10-23; that old last word never appears outside `archive/` (check: a case-insensitive whole-word search for it in tracked files outside `archive/` finds nothing; "cultivation" is fine).
- **No emoji, anywhere.** Only en dashes, in date ranges; no em dashes in page copy.
- **Every Chinese term is glossed in English nearby** (same line, the same alt text, or right under it). Chinese only appears where nothing after it on that line has to align.
- **Facts about Bill are never invented.** Sources: this README's existing facts, the site's data (the PortfolioV5 repo's `client/src/lib/portfolio-data/**`, read-only), and art3m1s.me. If the data has a gap, leave it out (or, inside the fold, give an in-fiction excuse); never make something up.
- **Never fake command output or data.** Everything a block shows comes from real files, git, or the GitHub API.
- **Width:** every line inside a `<pre>` or a code fence is at most 72 display columns, counting a CJK character as 2 (`readme_blocks.display_cols`). The copy-paste `curl` line is the one exception. Plain-text lines outside the fold wrap on phones; keep each Work line under about 100 characters so it stays on one line at 1280.
- **Both themes are designed:** dark (gold on ink) and light (ink on aged paper), via `<picture>` with `prefers-color-scheme`. Phones get the dark drawings in both themes, so every phone drawing carries its own ground (a light-theme phone shows it on white). Fixed-size images (the keys) have no phone source, so they follow the theme.

## Design system (`scripts/ink.py`)

Every SVG is drawn through `ink.py`; never hand-write colours or fonts into an SVG.

| Token | Dark | Light | Means |
|:--|:--|:--|:--|
| ground | #0E0C14 | #F4ECDC | panel ground (the site's ink and paper) |
| raised / track / line | #1B1826 / #2A2433 / #4D402C | #EBE0C8 / #DDD0B4 / #C4AE86 | raised panels / unlit swords / hairlines |
| text / muted | #F5ECDC / #A89F91 | #1F1A17 / #6B5F50 | body / labels |
| gold | #E9C77E | #7A5518 | won (and lit) |
| ember | #C98A4B | #A0742C | inside the fold only |
| jade | #8FE3C8 | #2C6E5A | the one main button, nothing else outside the fold |
| seal | #B8412D | #A8321F | seal fills only: 2 seals on the page |
| danger | #F0A089 | #A8321F | the formation's backlash, inside the fold only |

**Type: 3 drawn faces, 6 sizes.** Instrument Serif (display: names and headings), Geist 400/500 (text inside pictures), Ma Shan Zheng (the hero's 日月神教 mark only). Plain text is GitHub's own font. Noto Serif SC and Geist Mono appear only inside the fold (the formation art). Sizes as seen at 1280 wide (the column is about 831 px; a full-width 846 px SVG shows at 98%, the 1200 px hero at 69%):

| Size | Used for |
|--:|:--|
| 64 | "Bill Zhang" in the hero (Instrument Serif 92 in the 1200 px overlay) |
| 30 | Section headings; the "36" and "59" in the sword row |
| 24 | The hero line and mark; card names |
| 16 | All plain text: intro, captions, Work, Now, the fold's summary, footer |
| 14 | Text inside pictures: key labels, card one-liners, "won" and "entered" |
| 12 | Small print: card award lines, the sword caption, the hero gloss, the `<sub>` line |

No new size without removing one.

**Spacing: an 8 px grid.** hair 4 (gutter between cards), tight 8 (gap between keys, baked into each key's right edge), in-section 16 (GitHub's paragraph margin; inner padding of cards), panel 24 (the sword row's side padding), section 56 (16 + the 40 px of empty space at the top of each heading SVG). The Play fold gets its 56 px from an empty `<p>&nbsp;</p>` above it.

**Colour meanings:** jade = "click here" (one key); gold = won (the gilded swords, the "36", the award words on won cards); seal red = the sect's authority (the hero's 神 seal and the footer emblem); everything else is ink, paper, muted and hairline. GitHub's link blue in plain text is fine.

- **Type is drawn as glyph outlines, never `<text>`**: `scripts/ink_glyphs/<face>.json` (cut locally by `generate_glyphs.py` from SIL OFL fonts, licences committed next to them). A character missing from its table raises, and the renderer keeps the old files. Adding new Chinese copy to an SVG means re-running `generate_glyphs.py` first.
- **Motion:** the SVG with all animation removed is the finished picture; motion must mean something (the swords gild in turn because gold means won). Every animated SVG carries `@media (prefers-reduced-motion: reduce){*{animation:none!important}}`. Light SVGs contain no `@keyframes` at all.
- **Markup:** `<source>` order is phone (`(max-width: 600px)`, always the dark file, which carries its own ground) → light → `<img>`. Fixed-size images (the keys) skip the phone source. Never combine a width query with `prefers-color-scheme` in one `media` (GitHub's `themed-picture` rewrites the colour-scheme part). The hero adds reduced-motion stills; GitHub's sanitizer keeps those sources. Wrap every non-link image in a bare `<picture>` (GitHub auto-links a bare `<img>`). Inline-image rows must be <= 279px wide to survive a 360px phone, or break cleanly (the key row breaks into two rows of two). No `<p align="center">` except the hero and the seal. No markdown headings, tables, shields, GitHub alerts, footnotes or third-party image services on the page.
- **Ornaments** (cloud corners, brush strokes, the ink ring, the worn seal, the sun-and-moon logo) reuse the site's own path data, and appear only in the hero, the footer and inside the fold. Every `ink.plate()` outside those passes `corner=0`.

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it. Some marker and file names are old on purpose (invisible to readers; renaming one means changing the script and README together).

| Marker block / asset | Owner | Trigger |
|:--|:--|:--|
| `HACKLOG` (+ `assets/forge/<slug>{,-light,-phone}.svg`, the Shipped cards) | `scripts/render_hacklog.py`, drawing in `art_forge.py` (data: `var/log/hackathons.log` + `var/lib/ships.json`) | `profile-summary.yaml` |
| `NOW` (+ `assets/status.json`) | `scripts/update_currently_building.py` (the steward) | `profile-summary.yaml` (new lines); `moon-watch.yaml` (`--dates-only`) |
| `BUILD_PLATE` (the steward's seal, in the fold) | `scripts/update_currently_building.py` | `profile-summary.yaml`, every run |
| `FSCK` (+ `assets/formation/panel-<seq>*.svg`) | `scripts/artemis_ops.py`, drawing in `art_formation.py` (state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `PASSWD` (the disciple register) | `scripts/render_passwd.py` (stargazers) | `profile-summary.yaml` + `watch` events |
| `BOOT_ONELINER` (the line over the build plate) | `scripts/artemis_ops.py` gong easter egg (pool: `scripts/data/oneliners.txt`) | 1 in 10 gong strikes, silently |
| `bill.ansi` (the terminal talisman) | `scripts/generate_ansi_card.py` (36/59 from `ink.py`, `obsession` from status.json) | both scheduled workflows |
| `assets/gate/*.webp` (hero) + `title*.svg` | `scripts/generate_gate.py` from captured frames | by hand (local, Pillow) |
| `assets/keys/` (site, mail, linkedin, resume), `assets/banners/` (shipped, work, now), `assets/seal/` | `scripts/generate_chrome.py` | by hand |
| `assets/arena/record*.svg` (the sword row) | `scripts/generate_arena.py` | by hand, when the record changes |
| `assets/formation/tiles/**`, `gong*.svg`, `relay*.svg` | `scripts/generate_tiles.py` (= `artemis_ops.py tiles`) | by hand, after design changes |
| `assets/relics/heimuling.stl` (黑木令, the Black Wood Token) | `scripts/generate_token_stl.py` | by hand |
| `scripts/ink_glyphs/*.json` | `scripts/generate_glyphs.py` | by hand, when copy adds characters |

Retired on 2026-10-24 (now in `archive/sun-moon-v1/`): the `CRONTAB` block (timetable and ledger, `render_crontab.py`), the identity card and the mission board (`assets/mirror/`, `assets/hall/`, `render_card.py`), nine banners and four keys.

`PASSWD`, `BOOT_ONELINER` and `BUILD_PLATE` live inside HTML `<pre>` blocks in the fold and their content is HTML-escaped. `PASSWD` starts right after its bold heading and ends right before `</pre>`; the steward's-seal `<pre>` holds `BOOT_ONELINER` and `BUILD_PLATE` back to back. `NOW` is one `<p>` of three lines joined by `<br>`: `<b><a href="https://github.com/OWNER/REPO">REPO</a></b> · Oct 24 · Building ...` (the name is `OWNER/REPO` when the owner is not IdkwhatImD0ing; the date is "Oct 2025" for an older year). The script builds every URL itself from a checked repo name.

`assets/status.json`: `{"obsession": "2-4 words", "missions": [{"repo": "owner/name", "pushed": "YYYY-MM-DD", "line": "one sentence"}], "updated": "...Z"}`. `obsession` is only read by `generate_ansi_card.py`. The steward's honesty rules: candidates are only repos with a PushEvent by Bill in his public events feed (never this repo, and never a personal repo in `SKIP_REPOS`, such as `travel`), topped up from his public repos by last push when fewer than 3; the model may only pick from that list (one repo outside it rejects the whole payload); dates come from the feed, never the model; each line is one plain sentence of at most 64 characters starting with an -ing verb, no jokes, no names, no steward fiction. LLM down or junk: the previous status.json is kept (dates refreshed). No usable previous one, or `--fallback-only`: each line is a recent commit subject (12-64 characters), else the repo description, else "the steward has no notes on this one yet." Fewer than 3 repos in hand: the NOW block is left alone.

`var/lib/ships.json` is hand-maintained and read-only to scripts; if it is missing or malformed `render_hacklog.py` fails closed and keeps the old cards. The cards show the name, the one-liner and one award line (gold award words for a win); stars, forks and the repo address are not drawn (the card itself links to the repo). Hand-crafted: the relics (`.plan`, `README.md.bak`, `man/bill.1.md`), the back-shelf `<details>` with the STL fence (GitHub renders it as a 3D viewer), the raw-source hex comment, and all the section text.

Steward commit subjects: a real rewrite is `steward N: reposted the missions around X, kept the good ones`; the LLM down is `steward: the ink ran dry, kept the old missions (run N)`; the canned fallback is `steward: the ink ran dry, posted the standing missions (run N)`. The moon watch commits `moon-watch: the steward re-read the dates`.

## The formation game (破阵, break the formation; issue-ops)

Visitors play minesweeper against the 护宗大阵 by opening issues. It lives inside the Play fold. Titles (prefixes are case-sensitive, the cell letter is not):

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
python scripts/render_hacklog.py                  # HACKLOG cards (--offline, --dry-run)
python scripts/render_passwd.py                   # PASSWD register; without GITHUB_TOKEN it warns and exits 0
python scripts/update_currently_building.py --fallback-only --readme .preview/README.md --status .preview/status.json  # NOW + BUILD_PLATE without the LLM, on copies
python scripts/update_currently_building.py --dates-only   # what the moon watch runs
python scripts/generate_ansi_card.py              # bill.ansi
```

A local run of the steward on the real README stamps the build plate "run 0 · from local"; run it on `.preview/` copies unless you mean to.

Local-only generators (`generate_glyphs.py` needs fontTools; `generate_gate.py` needs Pillow; `generate_chrome.py`, `generate_arena.py`, `generate_tiles.py`, `generate_token_stl.py` are stdlib) never run in CI. Everything CI runs is stdlib-only.

Hero re-capture (the gate): Playwright at 1280x720 on https://art3m1s.me, wait ~12 s, hide every page element but the WebGL canvas (`body *{visibility:hidden!important} canvas{visibility:visible!important}`), then scroll from 0 to ~900 in eased steps taking a screenshot each (~80 frames) and hold ~20 frames at the gate. Then `python scripts/generate_gate.py titles`, rasterise the three `title*.svg` to PNG with a transparent background (Playwright `omitBackground`), and `python scripts/generate_gate.py encode --frames DIR --overlays DIR`. It crops to 2:1, composites the title overlay, loops, and encodes the five WebPs (hero <= 6 MB, still <= 400 KB, light <= 600 KB, phone <= 3 MB, phone still <= 250 KB). Never run Blender for this.

Env vars: `OPENAI_API_KEY`/`OPENAI_MODEL`/`REQUIRE_OPENAI` (the steward), `GITHUB_TOKEN` (rate limits, star dates, the events feed and commit subjects), `GITHUB_SHA`/`GITHUB_RUN_NUMBER` (build plate and commit subjects), `FSCK_SALT` (seals the formation). Preview the README the way GitHub renders it: `gh api /markdown -f mode=gfm -f context=IdkwhatImD0ing/IdkwhatImD0ing -F text=@README.md`, wrapped in github-markdown-css, dark and light, 1280 and 400 wide. Never print secrets.

## Architecture constraints

- **Concurrency:** every workflow that writes to `main` (`artemis-ops.yaml`, `profile-summary.yaml`, `moon-watch.yaml`) shares the `profile-readme-writes` concurrency group (no cancel) and runs `git pull --rebase --autostash origin main` before committing. Preserve both in any new workflow.
- **Commit pathspecs must exist:** a `file_pattern` entry that matches nothing makes `git add` fail and the commit step break. When a folder is retired, remove it from every `file_pattern` in the same change.
- **Never blank a block:** scripts only replace marker content (or write SVGs) after a successful, validated, non-empty render; on API failure they warn and exit 0. A bad API day must not damage the README. If the LLM call fails, the previous `status.json` is kept.
- **Missing markers are a no-op:** renderers warn and exit 0 if their markers are absent, so script and README changes can land independently.
- **Scheduled-workflow decay:** GitHub disables cron workflows after 60 days without repo activity. The Mon/Thu steward run (`17 15 * * 1,4`) rewrites the build plate every run, so it commits twice a week: that is the keepalive. The Saturday moon watch (`41 14 * * 6`) commits whenever a Now date moved. Don't thin the cadence.
- **Game integrity:** trap positions are never persisted; they are HMAC-derived from the optional `FSCK_SALT` secret (unset → the public fallback salt, and the panel admits "honor system"). Rotating the secret mid-board re-lays the formation by design. State stores only read nodes with their earned digits.
- **The register needs auth:** the stargazers endpoint 401s unauthenticated; `GITHUB_TOKEN` is always set in CI. Without it `render_passwd.py` leaves the block alone.
- **The push feed has no commit messages:** GitHub's events API stopped sending them, so the steward reads subjects from `/repos/{repo}/commits?author=IdkwhatImD0ing`.
- **The 36/59 record:** the lifetime totals (36 won of 59 entered; FullyHacks 2024, Tank, 1st place, counted since 2026-10-24) are `WON`/`ENTERED` in `scripts/ink.py`. Hand-written copies to update with them: the README (the intro's first sentence and the sword row's alt), `man/bill.1.md` (`--hackathon`), the `var/log/hackathons.log` header, and `.plan`'s win rate; then re-run `generate_arena.py` and `generate_ansi_card.py`. `hackathons.log` holds only verified greatest hits; Bill appends one line per event (plus a `var/lib/ships.json` record).
- **No third-party widgets:** metrics, skylines, snakes, pin cards, shields and typing SVGs were retired long ago. Anything new is drawn locally through `ink.py`.
- **Fragile externals fail soft:** OpenAI and the GitHub API degrade to the last good data.
- `scripts/update_playbook_posts.py` is library-only and currently unused (the steward no longer reads the Playbook feed); its own `main()` targets markers that no longer exist.

## Archive policy

Nothing is deleted. Retired files move to `archive/` (with `git mv` where they were tracked), and verbatim snapshots are taken from git history. `archive/` is a museum: kept verbatim, exempt from the fiction rules, never written by scripts, and nothing in it runs (GitHub only runs workflows in `.github/workflows/`). `archive/whitebox-os/` is the machine called tianni as found at commit `a864764`. `archive/sun-moon-v1/` is the first sect page as it was at commit `04bff9e`: the retired drawings and scripts (same relative paths), the README snapshot (petition links unwrapped, every picture it did not take along pinned to that commit), its CLAUDE.md, and the two workflows as they were. `archive/README.md` is the index.
