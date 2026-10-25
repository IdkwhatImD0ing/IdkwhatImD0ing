# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`, public). It opens on **the map of 日月神教, the Sun Moon Divine Sect**: the same map you get by pressing M on his site https://art3m1s.me, the floating xianxia sect (日月神教 is the sect of Jin Yong's *The Smiling, Proud Wanderer*). Bill's name and a gold Enter key sit on top; the legend beside the painted scroll is the page's table of contents. Below it Bill speaks plainly, in the first person. The sect is the setting. Bill is the only speaker.

The page sentence: **"Bill Zhang builds voice-first LLM agents at Pinterest and has won 36 of 59 hackathons."** Everything on the page serves it. Top to bottom (about 2,400 px at 1280 wide; about 3,000 when the Shipped journal lands, which Bill approved on 2026-10-24):

| # | Element | Job (the visitor's question) | Rank |
|--:|:--|:--|:--|
| 1 | **The map screen** (the MAP block: 13 linked pictures cut from one panel). Header band: 日月神教 SUN MOON DIVINE SECT, the carved seal beside "Bill Zhang" (the biggest text on the page), "builds voice-first LLM agents at Pinterest", and the gold ENTER ART3M1S.ME key, over the site's gate and moon. Under it the site's painted map on its scroll, the dotted route and the eleven stop seals, and a legend: each row is a stop (number, Chinese name, English name) plus a README section and one plain fact, and links to that section. A red ink ring draws itself once around the gate, "You are here". A foot line: "Click a place to jump to it", "On art3m1s.me, press M for this map" | Who is this, what does he do, where do I click, what is on this page? | Star |
| 2 | Intro, 2 sentences, fact first (`#about`) | What has he done? | Quiet |
| 3 | **Shipped**: 4 project cards (HACKLOG), the sword row (36 gold of 59, `#hackathons`), a short caption | What has he built that won? Is he good? | Support |
| 4 | **Work**: 6 roles, one line each; 2 education lines (`#school`); 1 tools sentence (`#tools`) | Where has he worked? | Quiet |
| 5 | **Now**: 3 real repos with a link, a date and one LLM sentence (NOW); one `<sub>` "How it works" line | What is he working on this week? | Quiet |
| 6 | **Play**: one closed `<details>` with Minesweeper (破阵) and one line of how-to, the gong, the star register, the terminal card line, the back shelf (.plan, archive, the 3D token) and one of Bill's old commit messages | Is there anything fun here? | Quiet |
| 7 | Footer line (email and LinkedIn, `#contact`) and the carved seal, centred | How do I reach him, now that I've read it? | Quiet |

The legend's rows and where they land: 11 望月台 Contact (`#contact`), 10 洞府 Now (`#now`), 09 护宗大阵 Play (`#play`), 08 玉简阁 Résumé (the PDF on the site), 07 碑林 Tools (`#tools`), 06 藏经阁 School (`#school`), 05 任务殿 Work (`#work`), 04 论剑台 Hackathons (`#hackathons`), 03 炼器峰 Shipped (`#shipped`), 02 心镜台 About (`#about`), 01 山门 You are here (art3m1s.me). Never remove one of those anchors without changing `art_map.STOPS`. The tiles link to `#user-content-<id>`, the id GitHub really writes for `<a id="<id>">`: on the profile page (github.com/IdkwhatImD0ing) a plain `#now` changes the address but does not scroll, because only repo pages run GitHub's script that maps it (checked live on 2026-10-24: the `#user-content-` form jumped 9 of 9 on the profile page at 1280 and 390 wide; on the repo page it jumped only about half the time, where plain `#tools` jumped 6 of 6). The profile page is where the map is the first screen, so it wins. Any new in-page link on this page uses the `#user-content-` form.

The page is partly hand-written and partly written by scripts: the **steward** (an LLM call, `update_currently_building.py`) writes the Now lines twice a week from Bill's real public commits, GitHub Actions run the game and keep the page alive, and **visitors** play Minesweeper by opening issues and get on the register by starring the repo. There is no build/lint/test setup: stdlib Python scripts in `scripts/` that CI and issue events run, plus a few local-only generators.

The page's previous lives are in `archive/`: the machine called `tianni` (`archive/whitebox-os/`), the first, nine-banner sect page (`archive/sun-moon-v1/`), and the calling card's heroes and keys (`archive/calling-card-v1/`, `archive/calling-card-v2/`).

## The intent standard (every change is checked against this)

Intent means every part has a job you can name, and the jobs are ranked: one star, two or three helpers, a quiet rest. The full standard is the r49 `intent.md` checklist; in short:

- **C1 One purpose.** The page sentence above. "Bill Zhang" is the biggest text on the first screen.
- **C2 Reading order.** Name and line, the gold key, the map's legend, the intro, Shipped (cards, then swords), Work, Now, Play (closed), footer. Nothing ties for first; no decoration is read before the name.
- **C3 Few big shapes.** One primary block (the map screen), two secondary (the cards, the sword row), everything else an even texture of plain text.
- **C4 Every element has a job** (the table above). No job: cut it. Same job as another element: merge them.
- **C5 Designed quiet.** 56 px between sections, 16 px inside one (ratio 3.5).
- **C6 Never twins.** 6 text sizes at most; headings of different rank never share a size.
- **C7 Colour points.** One accent: gold, the site's own. The one filled key (Enter) is gold; on the map, gold labels the places as it does on the site's map; below the map, gold means won. Seal red on 2 seals and the one ink ring only.
- **C8 Detail where the eye goes.** Brush lettering, seals and cloud corners only in the map screen and the footer.
- **C9 Composed edges.** One left edge. The map screen is full width; only the footer seal is centred.
- **C10 Pull forward.** One filled key; the pinned repos show by about the fourth screen (about 2,600 px).
- **C11 Rhythm.** Who, proof, work, now, then play (folded).
- **C12 One system, one voice.** Two materials (ink pictures, plain GitHub text), 3 drawn faces, one narrator (Bill, first person), no grey code boxes outside the fold.
- **C13 Honest.** Every number and date is real; at most one sentence explains how the page works.
- **C14 The theme is seasoning.** Cover the 日月神教 mark, the map's Chinese place names and the seals: who, what, proof and contact must remain (the legend's English titles and facts carry them).

**Counts outside the Play fold** (check them after any change): height at 1280 about 2,400 px (3,000 at most, the journal included); 3 section headings; 2 seals and 1 ink ring; at most 24 images (today 22, 13 of them the one map) and 45 links (today 25); 6 text sizes; 3 drawn faces; 1 accent colour; 0 code boxes; 1 centred block (the footer seal); 1 moving thing (the ring, once). **The 5-second test:** show the first screen for 5 seconds at 1280x800 (dark and light) and on a 385 px phone; a stranger must answer who ("Bill Zhang"), what ("builds voice-first LLM agents at Pinterest") and where to click ("the gold Enter art3m1s.me button"). A new element must name its job and its rank, and take the place of something, not add to the pile.

## Voice: write as Bill (every line a visitor can read)

This covers the README, alt text, text drawn in pictures, bot replies, issue bodies, commit subjects the bots
write, the Now lines, and every file a visitor can open (`.plan`, `bill.ansi`, `archive/README.md`). Bill
writes like a student telling a friend what he built: short plain sentences, first person, real numbers, a bit
excited when something works, honest about what broke. Readers spot machine-written text by devices that come
back on a schedule, so the rules below are about cutting those devices.

Do:
- Say what the thing is in the first few words. Mostly 8 to 15 words a sentence, with a longer one now and then.
- "I" for his work, "we" for team builds. Real numbers, plainly ("36 of the 59 hackathons I've entered").
- Plain words for anything a visitor acts on: click, square, issue, star, mine. Theme words only for names and
  pictures (破阵, 护宗大阵, 勿敲, the seal), each glossed in English.
- Bot replies and errors are just replies and errors: what happened, the score, and what to do next if the
  game is over. One plain line of how-to for the game; players find the rest by playing.
- At most one joke per screen, and only from a real Bill fact. The old-commit-message box in the fold is it.
- Prefer cutting. A line that gives the visitor no fact goes.

Don't (the tells; `voice_tells()` in the steward rejects the ones a script can spot):
- Em dashes, or semicolons and colons used for a dramatic pause. No emoji.
- "X, not Y", "not X but Y", "it's not X, it's Y", "rather than", "not just", "less X, more Y".
- Lists of three abstract things, neat closing lines, deadpan stings ("probably.", "You were told."), wise-
  sounding lore lines, polished self-deprecation.
- Explaining what everyone knows (how Minesweeper numbers work) or how the page works (one sentence at most,
  the `<sub>` under Now).
- Renaming plain things in the theme (petition, node, trap, disciple, elders, scribe, talisman, relic).
- Writing about the page's own history in page copy. `.plan` and one archive link hold it.
- Words: delve, tapestry, testament, pivotal, crucial, showcase, vibrant, seamless, robust, leverage, quietly,
  genuinely, honest, deliberate, load-bearing, journey, elevate, empower, enhance, elements, "matters because",
  "serves as".
- Lowercase as a style, fake typos, forced slang, swearing. Never say hackathons are mostly luck or knock LeetCode.
- Never claim Bill wrote something in his own words when a script or an LLM wrote it.

## Stills, and one ink ring

One thing on the profile moves, once: the map's red ink ring draws itself around the gate ("You are here")
about 1.2 s after the picture loads, takes 1.4 s, and stays drawn. Nothing loops. Bill picked this on
2026-10-24 ("One ink ring"). Everything else is still: no GIF, no animated WebP or PNG, no other SVG
animation. `ink.doc()` refuses `@keyframes` and `<animate>` unless it is called with `motion="once"`; then
`ink.check_once()` allows exactly one CSS animation that says it runs `1` time and holds (`both`), with no
SMIL, no `infinite`, no `alternate`. The ring is a mask over `ink.enso`, so a viewer that ignores CSS
animation shows it fully drawn. Every `<picture>` that shows a moving file also serves a still twin under
`(prefers-reduced-motion: reduce)` (`assets/map/gate-still.svg`, `gate-light-still.svg`,
`gate-phone-still.svg`): an SVG inside `<img>` ignores its own reduced-motion rule, so the twin has to come
from `<picture>`. On a desktop 1280x800 window the gate row is just below the first screen, so many
visitors find the ring already drawn. The old animated heroes are in `archive/calling-card-v1/assets/gate/`.
A new picture is a still, or it does not go on the page.

## Other text rules

- **The English name is always "Sun Moon Divine Sect".** The site used an older English name until its rename on 2026-10-23; that old last word never appears outside `archive/` (check: a case-insensitive whole-word search for it in tracked files outside `archive/` finds nothing; "cultivation" is fine).
- **No emoji, anywhere.** Only en dashes, in date ranges; no em dashes in page copy.
- **Every Chinese term is glossed in English nearby** (same line, the same alt text, or right under it). Chinese only appears where nothing after it on that line has to align.
- **Facts about Bill are never invented.** Sources: this README's existing facts, the site's data (the PortfolioV5 repo's `client/src/lib/portfolio-data/**`, read-only), and art3m1s.me. If the data has a gap, leave it out or say so plainly. Never make something up.
- **Never fake command output or data.** Everything a block shows comes from real files, git, or the GitHub API.
- **Width:** every line inside a `<pre>` or a code fence is at most 72 display columns, counting a CJK character as 2 (`readme_blocks.display_cols`). The copy-paste `curl` line is the one exception. Plain-text lines outside the fold wrap on phones; keep each Work line under about 100 characters so it stays on one line at 1280.
- **Both themes are designed:** dark (gold on ink) and light (ink on aged paper), via `<picture>` with `prefers-color-scheme`. Phones get the dark drawings in both themes, so every phone drawing carries its own ground (a light-theme phone shows it on white). The map's painting, scroll, stop seals and logo are the same by day and night (they are painted or stamped); its panel, words and header picture switch (the light header is an ink-wash print of the same view).
- **Words drawn into pictures go stale by hand.** The map legend's facts live in `scripts/art_map.py` `STOPS` (Contact billzhangsc@gmail.com; Now 3 repos I'm working on; Play Minesweeper on GitHub issues; Résumé PDF; Tools TypeScript and Python; School USC, UC Santa Cruz; Work Pinterest, Scale AI, RingCentral; Shipped 4 builds, 3 of them won; About and You are here have none, since a fact after "About" reads as part of the title). When one of those changes, edit `STOPS` and re-run `python scripts/generate_map.py`.

## Design system (`scripts/ink.py`)

Every SVG is drawn through `ink.py`; never hand-write colours or fonts into an SVG.

| Token | Dark | Light | Means |
|:--|:--|:--|:--|
| ground | #0E0C14 | #F4ECDC | panel ground (the site's ink and paper) |
| raised / track / line | #1B1826 / #2A2433 / #4D402C | #EBE0C8 / #DDD0B4 / #C4AE86 | raised panels / unlit swords / hairlines |
| text / muted | #F5ECDC / #A89F91 | #1F1A17 / #6B5F50 | body / labels |
| gold | #E9C77E | #7A5518 | the one filled key (Enter art3m1s.me), the map's labels, won (and lit) |
| ember | #C98A4B | #A0742C | inside the fold only |
| jade | #8FE3C8 | #2C6E5A | inside the fold only (the formation's new-board key) |
| seal | #B8412D | #A8321F | the map's one ink ring (the seals' own red is `LOGO_COLORS`) |
| danger | #F0A089 | #A8321F | the formation's backlash, inside the fold only |

**Type: 3 drawn faces, 6 sizes.** Instrument Serif (display: names, headings, the legend's section titles), Geist 400/500 (text inside pictures), Ma Shan Zheng (the map screen's Chinese: the 日月神教 mark and the eleven place names). Plain text is GitHub's own font. Noto Serif SC and Geist Mono appear only inside the fold (the formation art). Sizes as seen at 1280 wide (the column is 846 px, so a full-width 846 px SVG shows at 100%):

| Size | Used for |
|--:|:--|
| 64 | "Bill Zhang" on the map screen |
| 30 | Section headings; the "36" and "59" in the sword row; the legend's three big titles (Work, Hackathons, Shipped) |
| 24 | The name line; card names; the legend's place names and other titles |
| 16 | All plain text: intro, captions, Work, Now, the fold's summary, footer; the 日月神教 mark |
| 14 | Text inside pictures: the Enter key, legend facts, the map's foot line, card one-liners, "won" and "entered" |
| 12 | Small print: the legend's English names and numbers, SUN MOON DIVINE SECT, keycaps, card award lines, the sword caption, the `<sub>` line |

No new size without removing one. Phone drawings (360 px wide, shown at about 86%) set their own sizes: name 46, legend titles 20 to 22, place names 18, the line and the key 16 and 14.

**Spacing: an 8 px grid.** hair 4 (gutter between cards), tight 8 (gap between the keys inside the fold), in-section 16 (GitHub's paragraph margin; inner padding of cards), panel 24 (the sword row's side padding), section 56 (16 + the 40 px of empty space at the top of each heading SVG). The Play fold gets its 56 px from an empty `<p>&nbsp;</p>` above it.

**Colour meanings:** gold = the site's accent: the one filled key (Enter art3m1s.me), the map's labels, and below the map, won (the gilded swords, the "36", the award words on won cards); seal red = the sect's mark (the carved seal beside the name and in the footer) and the ink ring around "You are here"; everything else is ink, paper, muted and hairline. Jade lives inside the fold only. GitHub's link blue in plain text is fine.

- **Type is drawn as glyph outlines, never `<text>`**: `scripts/ink_glyphs/<face>.json` (cut locally by `generate_glyphs.py` from SIL OFL fonts, licences committed next to them). A character missing from its table raises, and the renderer keeps the old files. Adding new Chinese copy to an SVG means re-running `generate_glyphs.py` first.
- **Stills only:** no SVG animates (see above). The dark sword row keeps a soft glow on the gold swords; that is a filter, not motion.
- **Markup:** `<source>` order is phone (`(max-width: 600px)`, always the dark file, which carries its own ground) → light → `<img>`. The gate row adds its still twins: phone + reduced motion → phone → reduced motion + light → light → reduced motion → `<img>` (the moving dark file). Never combine a width query with `prefers-color-scheme` in one `media` (GitHub's `themed-picture` rewrites the colour-scheme part); a reduced-motion query may sit with either. When a visitor sets GitHub's theme by hand to light, `themed-picture` turns "reduced motion + light" into always-on, so they get the still ring; that is the safe way to fail. Wrap every non-link image in a bare `<picture>` (GitHub auto-links a bare `<img>`). No `<p align="center">` except the footer seal. No markdown headings, tables, shields, GitHub alerts, footnotes or third-party image services on the page.
- **The map's tiles:** 13 pictures in one `<p>`, each `width="100%" align="top"`, joined by `<br>`, each in its own link except the foot. They are cut from one drawing at whole pixels and carry 3 px of painting past their edges, so they meet with no gap (checked at the 846, 578, 398 and 308 px columns, at 1x, 2x and 3x). A row must stay at least 53 px tall in the 846 px drawing: it shows at 47% in the 398 px column, and a picture shorter than GitHub's 24 px text line leaves a gap under it. Every tile carries its own painting strip as an embedded JPEG (an SVG in `<img>` cannot load other files); keep each file under 1 MB (`generate_map.py` refuses bigger).
- **Ornaments** (cloud corners, brush strokes, the ink ring, the carved seal) reuse the site's own path data, and appear only in the map screen, the footer and inside the fold. Every `ink.plate()` outside those passes `corner=0`.
- **The logo** is the carved seal Bill picked on 2026-10-24 (`ink.LOGO_MASTER`, `LOGO_WEAR`, `logo_markup`): one module is R/16 on a face 41 modules across; `crescent_path` works out its arc flags from the geometry. `variant="light"` cuts the crescent through, so the page shows in it like a real seal print. The 3D token's STL (`generate_token_stl.py`, in the fold) still has the old logo's numbers written in; it changes only when that script is updated and re-run.

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it. Some marker and file names are old on purpose (invisible to readers; renaming one means changing the script and README together).

| Marker block / asset | Owner | Trigger |
|:--|:--|:--|
| `HACKLOG` (+ `assets/forge/<slug>{,-light,-phone}.svg`, the Shipped cards) | `scripts/render_hacklog.py`, drawing in `art_forge.py` (data: `var/log/hackathons.log` + `var/lib/ships.json`) | `profile-summary.yaml` |
| `NOW` (+ `assets/status.json`) | `scripts/update_currently_building.py` (the steward) | `profile-summary.yaml` (new lines); `moon-watch.yaml` (`--dates-only`) |
| `BUILD_PLATE` (an invisible HTML comment under the Now line: `steward run N, from SHA`) | `scripts/update_currently_building.py` | `profile-summary.yaml`, every run |
| `FSCK` (+ `assets/formation/panel-<seq>*.svg`) | `scripts/artemis_ops.py`, drawing in `art_formation.py` (state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `PASSWD` (the disciple register) | `scripts/render_passwd.py` (stargazers) | `profile-summary.yaml` + `watch` events |
| `BOOT_ONELINER` (one of Bill's real old commit messages, in the last box of the fold) | `scripts/artemis_ops.py` gong easter egg (pool: `scripts/data/oneliners.txt`, real commit messages only, quoted exactly) | 1 in 10 gong strikes, silently |
| `bill.ansi` (the terminal card) | `scripts/generate_ansi_card.py` (36/59 from `ink.py`, the Now repos from status.json) | both scheduled workflows |
| `MAP` (the map screen) + `assets/map/<tile>{,-light,-phone}.svg` (`head`, the eleven stops, `foot`; the gate's `-still` twins) | `scripts/generate_map.py`, drawing in `art_map.py` (stdlib), from the strips in `scripts/data/map/` that `generate_map.py cut` makes from PortfolioV5's `public/sect/map/map_full.webp` and `public/sect/poster/landscape.webp` (Pillow). Stop positions: `scripts/data/map/stops.json`, measured on the live map | by hand (local) |
| `assets/banners/` (shipped, work, now), `assets/seal/` (the carved seal) | `scripts/generate_chrome.py` | by hand |
| `assets/arena/record*.svg` (the sword row) | `scripts/generate_arena.py` | by hand, when the record changes |
| `assets/formation/tiles/**`, `gong*.svg`, `relay*.svg` | `scripts/generate_tiles.py` (= `artemis_ops.py tiles`) | by hand, after design changes |
| `assets/relics/heimuling.stl` (黑木令, the Black Wood Token) | `scripts/generate_token_stl.py` | by hand |
| `scripts/ink_glyphs/*.json` | `scripts/generate_glyphs.py` | by hand, when copy adds characters |

Retired on 2026-10-24, third pass (now in `archive/calling-card-v2/`, when the map screen took the top of the page): the still hero (`assets/gate/hero-still.webp`, `hero-light.webp`, `hero-phone-still.webp`, `title*.svg`), its generator `generate_gate.py`, the four keys (`assets/keys/`) and the old `generate_chrome.py` that drew them. Retired on 2026-10-24, second pass (now in `archive/calling-card-v1/`): the animated heroes `hero.webp` and `hero-phone.webp`, the man page `man/bill.1.md` and `README.md.bak`. Retired on 2026-10-24, first pass (now in `archive/sun-moon-v1/`): the `CRONTAB` block (timetable and ledger, `render_crontab.py`), the identity card and the mission board (`assets/mirror/`, `assets/hall/`, `render_card.py`), nine banners and four keys.

`PASSWD` and `BOOT_ONELINER` live inside HTML `<pre>` blocks in the fold and their content is HTML-escaped. `PASSWD` starts right after its bold heading and ends right before `</pre>`; the last `<pre>` of the fold holds `BOOT_ONELINER`. `BUILD_PLATE` sits on its own line under the Now `<sub>` line and holds one HTML comment. `NOW` is one `<p>` of three lines joined by `<br>`: `<b><a href="https://github.com/OWNER/REPO">REPO</a></b> · Oct 24 · Added ...` (the name is `OWNER/REPO` when the owner is not IdkwhatImD0ing; the date is "Oct 2025" for an older year). The script builds every URL itself from a checked repo name.

`assets/status.json`: `{"missions": [{"repo": "owner/name", "pushed": "YYYY-MM-DD", "line": "one sentence"}], "updated": "...Z"}`. The steward's honesty rules: candidates are only repos with a PushEvent by Bill in his public events feed (never this repo, and never a personal repo in `SKIP_REPOS`, such as `travel`), topped up from his public repos by last push when fewer than 3; the model may only pick from that list (one repo outside it rejects the whole payload); dates come from the feed, never the model; each line is one short sentence of at most 64 characters, past tense like a commit message, no jokes, no names, no sect words. Every line passes `voice_tells()` (the Voice section's tells a script can spot); a line that fails is swapped for the repo's plain line: a recent commit subject (12-64 characters, opens with what was done, no tell), else the repo description (no tell), else "Pushed new commits." LLM down or junk: the previous status.json is kept (dates refreshed, lines re-checked). No usable previous one, or `--fallback-only`: the plain lines. `python scripts/update_currently_building.py --self-test` checks the filter offline. Fewer than 3 repos in hand: the NOW block is left alone.

`var/lib/ships.json` is hand-maintained and read-only to scripts; if it is missing or malformed `render_hacklog.py` fails closed and keeps the old cards. The cards show the name, the one-liner and one award line (gold award words for a win); stars, forks and the repo address are not drawn (the card itself links to the repo). Hand-written: `.plan` (a plain changelog of the page), `archive/README.md`, the back-shelf `<details>` with the STL fence (GitHub renders it as a 3D viewer), the small raw-source comment at the top (the MOON GATE word), and all the section text.

Bot commit subjects are plain, like Bill's own: `Update the Now section (steward run N)`, `Update the Now section from commit messages (steward run N)`, `Keep the Now section, no LLM this time (steward run N)`, `Move the Now dates forward (moon watch)`, `Minesweeper move [skip ci]`, `Update the star list`.

## The formation game (破阵, break the formation; issue-ops)

Visitors play minesweeper against the 护宗大阵 by opening issues. It lives inside the Play fold. Titles (prefixes are case-sensitive, the cell letter is not):

| Title | Does | Legacy alias (still works) |
|:--|:--|:--|
| `sect\|zhen\|C4` | open one square | `artemis\|fsck\|C4` |
| `sect\|zhen\|relay` | start a new board once the game is won or lost | `artemis\|fsck\|reformat` |
| `sect\|gong` | strike the sealed gong (勿敲 DO NOT STRIKE) | `artemis\|button` |
| `sudo make me a sandwich` | replies "Okay." (xkcd 149); not linked from the page | - |

`artemis-ops.yaml` routes them: eyes-reaction ack → `python scripts/artemis_ops.py process --title ... --actor ... --issue N` (stdout = the plain reply; exit code always 0) → commit README + `data/fsck/` + `assets/formation/` → comment + close. A drain step answers up to 8 other queued petitions. Titles are passed via env vars only (injection guard) and matched against a strict regex; anything else with a `sect|` or `artemis|` prefix gets "Unknown command ..." and the list of titles that work. Replies never @-mention anyone. Stats keep logging the old op names (`fsck C4`, `reformat`, `button`); the view maps them for display (`open C4`, `reset`, `gong`). The status panel says only what the board does not show (board number, score, mines, stats, the log, winners), in plain words, with no how-to lines. The engine never depends on the art: if `art_formation`/`ink` fail to import, the visitor still gets a reply and the board is simply not redrawn.

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
python scripts/update_currently_building.py --self-test    # the voice filter and line rules, offline
python scripts/generate_ansi_card.py              # bill.ansi
python scripts/generate_map.py                    # the map screen: assets/map/ and the MAP block (stdlib)
python scripts/generate_map.py cut --site ../PortfolioV5/client   # re-cut the painting and header strips (Pillow), then draw
```

A local run of the steward on the real README stamps the build plate "run 0 · from local"; run it on `.preview/` copies unless you mean to.

Local-only generators (`generate_glyphs.py` needs fontTools; `generate_map.py cut` needs Pillow; `generate_map.py`, `generate_chrome.py`, `generate_arena.py`, `generate_tiles.py`, `generate_token_stl.py` are stdlib) never run in CI. Everything CI runs is stdlib-only.

The map screen's pictures come from the site, read-only: the painting is `public/sect/map/map_full.webp` (a painting, so a new scene bake does not change it) and the header band is the site's opening poster, `public/sect/poster/landscape.webp`, which is a capture of the 3D scene. After the scene is re-baked and the site's poster re-made, run `python scripts/generate_map.py cut --site ../PortfolioV5/client` and commit `scripts/data/map/head-*.jpg` and `assets/map/head*.svg`. The poster has pale tile seams in its corners, so `POSTER_BOX` in `generate_map.py` keeps the band inside its clean middle; check a new poster for the same. Never run Blender for this.

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
- **The 36/59 record:** the lifetime totals (36 won of 59 entered; FullyHacks 2024, Tank, 1st place, counted since 2026-10-24) are `WON`/`ENTERED` in `scripts/ink.py`. Hand-written copies to update with them: the README (the intro's first sentence and the sword row's alt) and the `var/log/hackathons.log` header; then re-run `generate_arena.py`, `generate_ansi_card.py` and `generate_map.py` (the legend's Hackathons row). `hackathons.log` holds only verified greatest hits; Bill appends one line per event (plus a `var/lib/ships.json` record).
- **No third-party widgets:** metrics, skylines, snakes, pin cards, shields and typing SVGs were retired long ago. Anything new is drawn locally through `ink.py`.
- **Fragile externals fail soft:** OpenAI and the GitHub API degrade to the last good data.
- `scripts/update_playbook_posts.py` is library-only and currently unused (the steward no longer reads the Playbook feed); its own `main()` targets markers that no longer exist.

## Archive policy

Nothing is deleted. Retired files move to `archive/` (with `git mv` where they were tracked), and verbatim snapshots are taken from git history. `archive/` is a museum: kept verbatim (its old text is not rewritten to the Voice rules; only `archive/README.md` is), never written by scripts, and nothing in it runs (GitHub only runs workflows in `.github/workflows/`). `archive/whitebox-os/` is the machine called tianni as found at commit `a864764`. `archive/sun-moon-v1/` is the first sect page as it was at commit `04bff9e`: the retired drawings and scripts (same relative paths), the README snapshot (petition links unwrapped, every picture it did not take along pinned to that commit), its CLAUDE.md, and the two workflows as they were. `archive/calling-card-v1/` holds what the second 2026-10-24 pass took off the page: the animated heroes, the man page and `README.md.bak`. `archive/calling-card-v2/` holds what the map screen replaced: the still hero and its titles, `generate_gate.py`, the four keys and the `generate_chrome.py` that drew them. `archive/README.md` is the index.
