# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Bill Zhang's GitHub profile README (`IdkwhatImD0ing/IdkwhatImD0ing`, public). It opens on **the map of 日月神教, the Sun Moon Divine Sect**: the same map you get by pressing M on his site https://art3m1s.me, the floating xianxia sect (日月神教 is the sect of Jin Yong's *The Smiling, Proud Wanderer*). Bill's name and a gold Enter key sit on top; the legend beside the painted scroll is the page's table of contents. Below it Bill speaks plainly, in the first person, and Shipped is a page of the sect's journal: prints of his winning builds' objects from the site's forge, each with one of his real commit messages. Then the record plate (36 / 59 over the swords, with one line Bill said in an interview), Work and Now in plain text, a two-fold menu (the full record of 36 wins, and Play), and the carved seal. The sect is the setting. Bill is the only speaker.

The page sentence: **"Bill Zhang builds voice-first LLM agents at Pinterest and has won 36 of 59 hackathons."** Everything on the page serves it. Top to bottom (2,996 px at 1280 wide with both folds closed since the record plate landed; Bill approved "about 3,000" on 2026-10-24, and 3,000 is the cap):

| # | Element | Job (the visitor's question) | Rank |
|--:|:--|:--|:--|
| 1 | **The map screen** (the MAP block: 13 linked pictures cut from one panel). Header band: 日月神教 SUN MOON DIVINE SECT, the carved seal beside "Bill Zhang" (the biggest text on the page), "builds voice-first LLM agents at Pinterest", and the gold ENTER ART3M1S.ME key, over the site's gate and moon. Under it the site's painted map on its scroll, the dotted route and the eleven stop seals, and a legend: each row is a stop (number, Chinese name, English name) plus a README section and one plain fact, and links to that section. A red ink ring draws itself once around the gate, "You are here". A foot line: "Click a place to jump to it", "On art3m1s.me, press M for this map" | Who is this, what does he do, where do I click, what is on this page? | Star |
| 2 | Intro, 2 sentences, fact first (`#about`) | What has he done? | Quiet |
| 3 | **Shipped**, a page of the sect's journal (like Black Myth: Wukong's 影神图): the title card 炼器峰 Shipped (stop 03); the star build's **spread** (HACKLOG; DispatchAI): a print of its object from the site's forge (令旗, the Command Flag) with a photo of the real app tipped in, then the prize line, the name, its one-liner, three facts, one sentence from our own write-up and Bill's real commit message from that weekend with its time and hash; then three smaller **pages** (TalkTuahBank, AdaptEd, SlugLoop), each a print, the prize, the name, the one-liner and a real commit. | What has he built that won? | Star of screen 2 (the spread); the pages support it |
| 4 | **The record plate** (`#hackathons`, stop 04 of the map, `assets/arena/record*.svg`): 论剑台 and SWORD-DISCUSSION ARENA · STOP 04 OF 11 as on the title cards, **36** big in gold over "/ 59" and HACKATHONS WON, Bill's interview line "Just cause you lost at a hackathon doesn't mean it's a bad project." (ME, IN AN INTERVIEW, SEP 2026), and the rack of 59 swords, 36 gilded. Then a short caption (college, LA Hacks 2026 judge, Playbook, YouTube, Devpost) | Is he good? | Star of screen 3 |
| 5 | **Work**: 6 roles, one line each; 2 education lines (`#school`); 1 tools sentence (`#tools`) | Where has he worked? | Quiet |
| 6 | **Now**: 3 real repos with a link, a date and one LLM sentence (NOW); one `<sub>` "How it works" line | What is he working on this week? | Quiet |
| 7 | **The menu**: two closed folds that share `name="menu"`, so opening one closes the other. "Full record: the 36 hackathons I've won" (`#record`): every win by year, newest first, one plain line each (project · event · prize). "Play: Minesweeper, but you play it by opening issues" (`#play`): the board (破阵) and one line of how-to, the gong, the star register, the terminal card line, the back shelf (.plan, archive, the 3D token) and one of Bill's old commit messages | Which 36? Is there anything fun here? | Quiet |
| 8 | Footer line (email and LinkedIn, `#contact`) and the carved seal, centred | How do I reach him, now that I've read it? | Quiet |

The legend's rows and where they land: 11 望月台 Contact (`#contact`), 10 洞府 Now (`#now`), 09 护宗大阵 Play (`#play`), 08 玉简阁 Résumé (the PDF on the site), 07 碑林 Tools (`#tools`), 06 藏经阁 School (`#school`), 05 任务殿 Work (`#work`), 04 论剑台 Hackathons (`#hackathons`), 03 炼器峰 Shipped (`#shipped`), 02 心镜台 About (`#about`), 01 山门 You are here (art3m1s.me). Never remove one of those anchors without changing `art_map.STOPS`. The tiles link to `#user-content-<id>`, the id GitHub really writes for `<a id="<id>">`: on the profile page (github.com/IdkwhatImD0ing) a plain `#now` changes the address but does not scroll, because only repo pages run GitHub's script that maps it (checked live on 2026-10-24: the `#user-content-` form jumped 9 of 9 on the profile page at 1280 and 390 wide; on the repo page it jumped only about half the time, where plain `#tools` jumped 6 of 6). The profile page is where the map is the first screen, so it wins. Any new in-page link on this page uses the `#user-content-` form.

The page is partly hand-written and partly written by scripts: the **steward** (an LLM call, `update_currently_building.py`) writes the Now lines twice a week from Bill's real public commits, GitHub Actions run the game and keep the page alive, and **visitors** play Minesweeper by opening issues and get on the register by starring the repo. There is no build/lint/test setup: stdlib Python scripts in `scripts/` that CI and issue events run, plus a few local-only generators.

The page's previous lives are in `archive/`: the machine called `tianni` (`archive/whitebox-os/`), the first, nine-banner sect page (`archive/sun-moon-v1/`), the calling card's heroes and keys (`archive/calling-card-v1/`, `archive/calling-card-v2/`), the plain project cards and headings (`archive/calling-card-v3/`), and the plain sword row (`archive/calling-card-v4/`).

## The intent standard (every change is checked against this)

Intent means every part has a job you can name, and the jobs are ranked: one star, two or three helpers, a quiet rest. The full standard is the r49 `intent.md` checklist; in short:

- **C1 One purpose.** The page sentence above. "Bill Zhang" is the biggest text on the first screen.
- **C2 Reading order.** Name and line, the gold key, the map's legend, the intro, Shipped (the spread, then the three pages), the record plate (the 36, then the swords, then the quote), Work, Now, the menu (both folds closed), footer. Nothing ties for first; no decoration is read before the name. On the spread the print is seen first, then the name; the prize line sits over the name.
- **C3 Few big shapes.** One primary block (the map screen), two secondary (the journal spread, the record plate), the three journal pages as one quieter band, everything else an even texture of plain text. One star per screen: the map, the spread, the record plate.
- **C4 Every element has a job** (the table above). No job: cut it. Same job as another element: merge them.
- **C5 Designed quiet.** 56 px between sections, 16 px inside one (ratio 3.5).
- **C6 Never twins.** 6 text sizes at most; headings of different rank never share a size.
- **C7 Colour points.** One accent: gold, the site's own. The one filled key (Enter) is gold; on the map, the title cards and the record plate's tag, gold labels the places as it does on the site's map; in the journal and on the record plate, gold means won (the prize words, the 36, the gilded swords). Seal red on 2 seals and the one ink ring only (the journal's prints and the record plate carry no red mark). The prints are paper in the map's brocade mount, the same by day and night (`ink.PRINT_COLORS`).
- **C8 Detail where the eye goes.** Seals only in the map screen and the footer. Cloud corners only on the stars of the first three screens: the map screen, the journal spread and the record plate. Brush lettering in the map screen, the three title cards and the record plate (the place's name), and on the journal's prints (the object's name).
- **C9 Composed edges.** One left edge. The map screen, the journal spread and the record plate are full width, the three pages sit side by side under the spread (828 px, so they still fit a Windows 1280 px window with its scrollbar); only the footer seal is centred.
- **C10 Pull forward.** One filled key; the pinned repos show by about the fourth screen (about 3,000 px).
- **C11 Rhythm.** Who, proof (what he built, then the record), work, now, then the menu (folded): the full record and play.
- **C12 One system, one voice.** Two materials (ink pictures, plain GitHub text), 3 drawn faces, one narrator (Bill, first person), no grey code boxes outside the fold.
- **C13 Honest.** Every number and date is real; at most one sentence explains how the page works.
- **C14 The theme is seasoning.** Cover the 日月神教 mark, the map's Chinese place names and the seals: who, what, proof and contact must remain (the legend's English titles and facts carry them).

**Counts outside the folds** (check them after any change): height at 1280 with both folds closed 2,996 px (3,000 at most, so 4 px are left: a new element must take the place of something; the record plate is 172 px tall, a closed fold costs 37 px); 3 section headings (the title cards) plus the record plate's place line; 2 seals and 1 ink ring; at most 24 images (today 22: 13 for the one map, 3 title cards, the spread and 3 journal pages, the record plate, the seal) and 45 links (today 25); 6 text sizes; 3 drawn faces; 1 accent colour; 0 code boxes; 1 centred block (the footer seal); 1 moving thing (the ring, once). **The 5-second test:** show the first screen for 5 seconds at 1280x800 (dark and light) and on a 385 px phone; a stranger must answer who ("Bill Zhang"), what ("builds voice-first LLM agents at Pinterest") and where to click ("the gold Enter art3m1s.me button"). A new element must name its job and its rank, and take the place of something, not add to the pile.

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
- At most one joke per screen, and only from a real Bill fact. The old-commit-message box in the fold is it. The journal's quotes are not jokes written for the page: each is Bill's real commit message from that build, quoted exactly, typos included ("TRNASFERS WPORKSASDASDASDASDASAD"), with its date, and `render_hacklog.py` refuses any quote that does not match its commit.
- The record plate's quote is Bill's own spoken line, word for word: "Just cause you lost at a hackathon doesn't mean it's a bad project." It comes from his interview answers in `IdkwhatImD0ing/hackathonstarterkit` (`.deslop/voice-profile.md`, Stance 3, approved by Bill on 2026-09-14), and Bill okayed it for the profile on 2026-10-24. It lives in `generate_arena.QUOTE` (drawn with curly apostrophes). Don't add a second line of his to the plate.
- The full record fold's lines are data: projects, events and prizes from the site's `portfolio-data/hackathons.ts`, except the three wins in `var/log/hackathons.log`, which use the log's words (UC Berkeley AI Hackathon, Grand Prize; HackUTD, Overall 1st Place; LA Hacks, Gemini Challenge 1st; Bill picked these on 2026-10-24). No sentence in the fold. The site's other stat tiles ($150k+ in prizes, 17 colleges) are not on the profile: the voice notes in hackathonstarterkit quote the site as "$100K+ in prizes", so the sources disagree, and neither is in `portfolio-data`.
- The journal's sentences come from data, never from a writer: names, prizes and one-liners from the log and `ships.json`, the spread's facts from the site's `portfolio-data`, its one sentence from our own Devpost write-up (as it sits in the DispatchAI README), the quotes from the commits. `ships.json` says where each came from (`words_from`, `rows_from`).
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
- **Words drawn into pictures go stale by hand.** The map legend's facts live in `scripts/art_map.py` `STOPS` (Contact billzhangsc@gmail.com; Now 3 repos I'm working on; Play Minesweeper on GitHub issues; Résumé PDF; Tools TypeScript and Python; School USC, UC Santa Cruz; Work Pinterest, Scale AI, RingCentral; Shipped 4 builds, 3 of them won; About and You are here have none, since a fact after "About" reads as part of the title). When one of those changes, edit `STOPS` and re-run `python scripts/generate_map.py`, then `python scripts/generate_chrome.py` and `python scripts/generate_arena.py` (the title cards and the record plate take their place names and stop numbers from the same `STOPS`). The journal's words live in `var/lib/ships.json` (the spread's rows and sentence, each build's quote) and the forge objects' names in `scripts/data/journal/prints.json`; edit them and re-run `python scripts/render_hacklog.py`. The record plate's words are `ink.WON`/`ENTERED` and `generate_arena.QUOTE`/`QUOTE_FROM`.

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

**Type: 3 drawn faces, 6 sizes.** Instrument Serif (display: names, headings, the legend's section titles, the journal's quotes), Geist 400/500 (text inside pictures), Ma Shan Zheng (the Chinese: the 日月神教 mark, the eleven place names on the map and the title cards, the forge objects' names on the journal's prints). Plain text is GitHub's own font. Noto Serif SC and Geist Mono appear only inside the fold (the formation art). Sizes as seen at 1280 wide (the column is 846 px, so a full-width 846 px SVG shows at 100%):

| Size | Used for |
|--:|:--|
| 64 | The star of each screen, one per screen: "Bill Zhang" on the map screen, the star build's name on the journal spread, the "36" on the record plate |
| 30 | Section headings (the title cards' place name and section name); the "/ 59" on the record plate; the legend's three big titles (Work, Hackathons, Shipped); the object's name upright on the spread's print |
| 24 | The name line; the journal pages' names; the spread's quote and the record plate's quote; the legend's place names and other titles; the objects' names on the pages' prints; the record plate's 论剑台 |
| 16 | All plain text: intro, captions, Work, Now, the folds' summaries and the full record's lines, footer; the 日月神教 mark; the spread's one-liner; the pages' quotes |
| 14 | Text inside pictures: the Enter key, legend facts, the map's foot line, the spread's facts and sentence, the pages' one-liners |
| 12 | Small print: the legend's English names and numbers, SUN MOON DIVINE SECT, keycaps, the title cards' and the record plate's English names and stop numbers, the journal's prize lines, labels, glosses, photo caption and commit lines, HACKATHONS WON and the quote's attribution, the `<sub>` line |

No new size without removing one. Phone drawings (360 px wide, shown at about 86%) set their own sizes: name 46 (and the record plate's 36), legend titles 20 to 22, place names 18 (the plate's 论剑台 22), the line and the key 16 and 14, the phone spread's and record plate's quotes 20, "/ 59" 26, labels 11, the phone title cards' section name 26 and place name 22.

**Spacing: an 8 px grid.** hair 4 (gutter between cards), tight 8 (gap between the keys inside the fold), in-section 16 (GitHub's paragraph margin; inner padding of cards), panel 24 (the sword row's side padding), section 56 (16 + the 40 px of empty space at the top of each heading SVG). The Play fold gets its 56 px from an empty `<p>&nbsp;</p>` above it.

**Colour meanings:** gold = the site's accent: the one filled key (Enter art3m1s.me), the place labels on the map, the title cards and the record plate, and below them, won (the gilded swords, the "36", the prize words of a won build in the journal); seal red = the sect's mark (the carved seal beside the name and in the footer) and the ink ring around "You are here"; everything else is ink, paper, muted and hairline. Jade lives inside the fold only. GitHub's link blue in plain text is fine.

- **Type is drawn as glyph outlines, never `<text>`**: `scripts/ink_glyphs/<face>.json` (cut locally by `generate_glyphs.py` from SIL OFL fonts, licences committed next to them). A character missing from its table raises, and the renderer keeps the old files. Adding new Chinese copy to an SVG means re-running `generate_glyphs.py` first.
- **Stills only:** no SVG animates (see above). The dark record plate keeps a soft glow on the gold swords; that is a filter, not motion.
- **Markup:** `<source>` order is phone (`(max-width: 600px)`, always the dark file, which carries its own ground) → light → `<img>`. The gate row adds its still twins: phone + reduced motion → phone → reduced motion + light → light → reduced motion → `<img>` (the moving dark file). Never combine a width query with `prefers-color-scheme` in one `media` (GitHub's `themed-picture` rewrites the colour-scheme part); a reduced-motion query may sit with either. When a visitor sets GitHub's theme by hand to light, `themed-picture` turns "reduced motion + light" into always-on, so they get the still ring; that is the safe way to fail. Wrap every non-link image in a bare `<picture>` (GitHub auto-links a bare `<img>`). No `<p align="center">` except the footer seal. No markdown headings, tables, shields, GitHub alerts, footnotes or third-party image services on the page.
- **The menu:** the two top-level folds are `<details name="menu">` (GitHub rewrites the name to `user-content-menu` on both, so they still pair up). Opening one closes the other in Chrome 120+, Safari 17.2+ and Firefox 130+; older browsers just leave both open. The back shelf `<details>` inside Play must never get the name, or opening it would close Play around it. Their summaries are plain text ("Full record: ...", "Play: ..."): a drawn plaque per summary would cost about 30 px each, and the page has 4 px left.
- **Alt text holds every drawn word.** Every picture's alt says the words it draws (the tiles' `alt()` in `art_map.py`, `label()` in `generate_arena.py` and `generate_chrome.py`, `spread_alt`/`leaf_alt` in `art_journal.py`, the board's `rail_label`/`row_label` in `art_formation.py`). Where the phone file says a different word, the alt says both ("Click or tap"). A picture with no words (the board's edges) keeps `alt=""`. The record plate's alt is pasted into the README by hand: when `label()` changes, paste it again.
- **The map's tiles:** 13 pictures in one `<p>`, each `width="100%" align="top"`, joined by `<br>`, each in its own link except the foot. They are cut from one drawing at whole pixels and carry 3 px of painting past their edges, so they meet with no gap (checked at the 846, 578, 398 and 308 px columns, at 1x, 2x and 3x). A row must stay at least 53 px tall in the 846 px drawing: it shows at 47% in the 398 px column, and a picture shorter than GitHub's 24 px text line leaves a gap under it. Every tile carries its own painting strip as an embedded JPEG (an SVG in `<img>` cannot load other files); keep each file under 1 MB (`generate_map.py` refuses bigger).
- **Ornaments** (cloud corners, brush strokes, the ink ring, the carved seal) reuse the site's own path data, and appear only in the map screen, the title cards (a dry brush rule), the journal spread (cloud corners and the gold brush stroke under its name), the record plate (cloud corners, top left and bottom right, through `art_journal.sheet`), the footer and inside the fold. The journal's pages have none. Every `ink.plate()` outside those passes `corner=0`.
- **The journal** (`art_journal.py`): the spread is one picture, `width="100%"`, with a phone file that stacks the print over the words; the three pages are pictures `width="276"` (`LEAF_W`), so they sit three across in 828 px and one per row on a phone, where they get the dark page file in both themes (`(max-width: 600px)` points at `<slug>.svg`; no separate phone file). Why 276, not 282: Chrome on Windows keeps 15-17 px of a 1280 px window for its scrollbar (a 1920 px laptop at 150%), so the column there is 829 px, and three 282 px pages wrapped to two plus one (checked live: the column is the window width minus 434 px from 1012 to 1280). At 846 px the pages' row ends 18 px short of the spread; that is the price. Windows from 1012 to 1261 px still wrap them two plus one. A quote is drawn whole or not at all: `whole_quote()` refuses one that would be cut with "..." or lose a character. Every print is a JPEG embedded in its SVG (an SVG in `<img>` cannot load other files). Keep each file under 1 MB (today the spread is about 135 KB).
- **The logo** is the carved seal Bill picked on 2026-10-24 (`ink.LOGO_MASTER`, `LOGO_WEAR`, `logo_markup`): one module is R/16 on a face 41 modules across; `crescent_path` works out its arc flags from the geometry. `variant="light"` cuts the crescent through, so the page shows in it like a real seal print. The 3D token's STL (`generate_token_stl.py`, in the fold) still has the old logo's numbers written in; it changes only when that script is updated and re-run.
- **The record plate** (`generate_arena.py`): one picture, `width="100%"`, 846 x 172, through `art_journal.sheet` (the journal's ground, gold hairline and two cloud corners); left, the place line and the record; right, the quote, drawn whole or not at all; under them the rack, 59 swords 40 px tall. The phone file (360 wide) stacks the place line, the record, the quote and two rows of swords. 172 px is what the 3,000 px cap left; a taller plate needs height from somewhere else.

### The canvas: what a GitHub profile allows (tested 2026-10-24, r52 `canvas.md`)

- **Pictures carry all the styling.** GitHub strips `<style>`, `style=""`, `class`, scripts, iframes, image maps and `data:` URIs in `<img>`. Every look on the page lives inside an SVG drawn through `ink.py`; the page's own HTML is plain text, `<picture>`, links and folds. An SVG in `<img>` cannot load other files, be hovered, or have clickable parts, so fonts are glyph outlines and photos are embedded JPEGs.
- **One link per picture.** A clickable region is its own linked picture (the map's 13 tiles: percent widths, whole-pixel cuts, painting bled 3 px past each edge; no seam at the 846, 578, 398 and 308 px columns at 1x, 2x and 3x).
- **Dark and light are separate files** in `<picture>`. A colour query inside an SVG follows the OS, not GitHub's theme, and never sits in one `media` with a width query.
- **Widths.** The column is 846 px from a 1280 px window up (829 on Windows Chrome at 1280 with its scrollbar), 578 at 1012, 398 at 768, 308 on a 390 px phone. A full-width picture shows at 36% on a phone, so every full-width drawing has a phone file (`(max-width: 600px)`, 360 px wide, the dark file in both themes). Windows from 601 to 1011 px get the desktop files at 47 to 68%, so 12 px words show at 6 to 8 px there; that is a known cost.
- **Sizes.** GitHub cuts a README past 500 KiB (today 88 KB) and its image proxy drops outside files over about 5 MB. This repo keeps every SVG under 1 MB (the biggest today, the spread, is 133 KB).
- **Motion and folds.** `prefers-reduced-motion` works only from `<picture>`, never inside the SVG (hence the ring's still twins). `<details name>` survives the sanitizer, so folds can close each other.
- **Not tested:** Safari, the iPhone and the GitHub mobile app (no WebKit on this PC). Glyph outlines and no `foreignObject` are the safest route for them.

## Who writes what

`README.md` is partly hand-written, partly machine-owned via marker blocks (`scripts/readme_blocks.py:replace_block`). Never hand-edit inside markers; the owning script will overwrite it. Some marker and file names are old on purpose (invisible to readers; renaming one means changing the script and README together).

| Marker block / asset | Owner | Trigger |
|:--|:--|:--|
| `HACKLOG` (+ `assets/journal/<slug>-spread{,-light,-phone}.svg` for the star build and `assets/journal/<slug>{,-light}.svg` for each page: the Shipped journal) | `scripts/render_hacklog.py`, drawing in `art_journal.py` (data: `var/log/hackathons.log` + `var/lib/ships.json`, the prints in `scripts/data/journal/`; every quote checked against its commit, noted in `var/lib/quotes-checked.json`) | `profile-summary.yaml` |
| `scripts/data/journal/` (`cap-<slug>.jpg` the forge captures' crops, `print-<slug>-{spread,leaf}.jpg` the prints, `photo-dispatchai.jpg` the tipped-in photo, `prints.json` the boxes, masks, frames and the objects' names) | `scripts/generate_prints.py` (Pillow + numpy), from captures taken by `scripts/capture_forge.cjs` (Node + playwright-core) of the live forge, and the site's `public/project-posters/` | by hand (local), after a new scene bake |
| `NOW` (+ `assets/status.json`) | `scripts/update_currently_building.py` (the steward) | `profile-summary.yaml` (new lines); `moon-watch.yaml` (`--dates-only`) |
| `BUILD_PLATE` (an invisible HTML comment under the Now line: `steward run N, from SHA`) | `scripts/update_currently_building.py` | `profile-summary.yaml`, every run |
| `FSCK` (+ `assets/formation/panel-<seq>*.svg`) | `scripts/artemis_ops.py`, drawing in `art_formation.py` (state: `data/fsck/`) | `artemis-ops.yaml` on issues |
| `PASSWD` (the disciple register) | `scripts/render_passwd.py` (stargazers) | `profile-summary.yaml` + `watch` events |
| `BOOT_ONELINER` (one of Bill's real old commit messages, in the last box of the fold) | `scripts/artemis_ops.py` gong easter egg (pool: `scripts/data/oneliners.txt`, real commit messages only, quoted exactly) | 1 in 10 gong strikes, silently |
| `bill.ansi` (the terminal card) | `scripts/generate_ansi_card.py` (36/59 from `ink.py`, the Now repos from status.json) | both scheduled workflows |
| `MAP` (the map screen) + `assets/map/<tile>{,-light,-phone}.svg` (`head`, the eleven stops, `foot`; the gate's `-still` twins) | `scripts/generate_map.py`, drawing in `art_map.py` (stdlib), from the strips in `scripts/data/map/` that `generate_map.py cut` makes from PortfolioV5's `public/sect/map/map_full.webp` and `public/sect/poster/landscape.webp` (Pillow). Stop positions: `scripts/data/map/stops.json`, measured on the live map | by hand (local) |
| `assets/banners/` (shipped, work, now: the title cards, from `art_map.STOPS`), `assets/seal/` (the carved seal) | `scripts/generate_chrome.py` | by hand |
| `assets/arena/record*.svg` (the record plate: 36 / 59, the interview line, the sword rack) | `scripts/generate_arena.py` (place names from `art_map.STOPS`, the record from `ink.WON`/`ENTERED`, the quote in `QUOTE`; it warns when the README's alt for the plate is not its `label()`) | by hand, when the record changes |
| The full record fold (`#record`, 36 lines by year) | hand-written from the site's `hackathons.ts` (see Voice) | by hand, when Bill wins one |
| `assets/formation/tiles/**`, `gong*.svg`, `relay*.svg` | `scripts/generate_tiles.py` (= `artemis_ops.py tiles`) | by hand, after design changes |
| `assets/relics/heimuling.stl` (黑木令, the Black Wood Token) | `scripts/generate_token_stl.py` | by hand |
| `scripts/ink_glyphs/*.json` | `scripts/generate_glyphs.py` | by hand, when copy adds characters |

Retired on 2026-10-24, fifth pass (now in `archive/calling-card-v4/`, when the record plate took over the sword row): the plain sword row (`assets/arena/record*.svg` as it was: "36 won 59 entered" over the swords, 136 px) and the `generate_arena.py` that drew it. Retired on 2026-10-24, fourth pass (now in `archive/calling-card-v3/`, when the journal took over Shipped): the four project cards (`assets/forge/`) and `art_forge.py` that drew them, the plain section headings (`assets/banners/` as they were), and the versions of `render_hacklog.py` and `generate_chrome.py` that drew those. Retired on 2026-10-24, third pass (now in `archive/calling-card-v2/`, when the map screen took the top of the page): the still hero (`assets/gate/hero-still.webp`, `hero-light.webp`, `hero-phone-still.webp`, `title*.svg`), its generator `generate_gate.py`, the four keys (`assets/keys/`) and the old `generate_chrome.py` that drew them. Retired on 2026-10-24, second pass (now in `archive/calling-card-v1/`): the animated heroes `hero.webp` and `hero-phone.webp`, the man page `man/bill.1.md` and `README.md.bak`. Retired on 2026-10-24, first pass (now in `archive/sun-moon-v1/`): the `CRONTAB` block (timetable and ledger, `render_crontab.py`), the identity card and the mission board (`assets/mirror/`, `assets/hall/`, `render_card.py`), nine banners and four keys.

`PASSWD` and `BOOT_ONELINER` live inside HTML `<pre>` blocks in the fold and their content is HTML-escaped. `PASSWD` starts right after its bold heading and ends right before `</pre>`; the last `<pre>` of the fold holds `BOOT_ONELINER`. `BUILD_PLATE` sits on its own line under the Now `<sub>` line and holds one HTML comment. `NOW` is one `<p>` of three lines joined by `<br>`: `<b><a href="https://github.com/OWNER/REPO">REPO</a></b> · Oct 24 · Added ...` (the name is `OWNER/REPO` when the owner is not IdkwhatImD0ing; the date is "Oct 2025" for an older year). The script builds every URL itself from a checked repo name.

`assets/status.json`: `{"missions": [{"repo": "owner/name", "pushed": "YYYY-MM-DD", "line": "one sentence"}], "updated": "...Z"}`. The steward's honesty rules: candidates are only repos with a PushEvent by Bill in his public events feed (never this repo, and never a personal repo in `SKIP_REPOS`, such as `travel`), topped up from his public repos by last push when fewer than 3; the model may only pick from that list (one repo outside it rejects the whole payload); dates come from the feed, never the model; each line is one short sentence of at most 64 characters, past tense like a commit message, no jokes, no names, no sect words. Every line passes `voice_tells()` (the Voice section's tells a script can spot); a line that fails is swapped for the repo's plain line: a recent commit subject (12-64 characters, opens with what was done, no tell), else the repo description (no tell), else "Pushed new commits." LLM down or junk: the previous status.json is kept (dates refreshed, lines re-checked). No usable previous one, or `--fallback-only`: the plain lines. `python scripts/update_currently_building.py --self-test` checks the filter offline. Fewer than 3 repos in hand: the NOW block is left alone.

`var/lib/ships.json` is hand-maintained and read-only to scripts; if it is missing or malformed `render_hacklog.py` fails closed and keeps the old journal. Per build: `repo`, `payload` (the one-liner), `lang`/`stars`/`forks` (run log only), `quote` (`text`, the full `sha`, and `when`: the author time with the offset Bill's clock had, e.g. `2024-06-23T05:23:05-07:00`), and on the one star build a `spread` (`rows` of [label, value], `words`, `photo`, plus `rows_from`/`words_from` saying where they came from). The newest four log entries are drawn: the one with a `spread` gets the spread (else the newest win), the rest a page each, newest first. **The quote check:** before drawing, `render_hacklog.py` fetches each quote's commit (`/repos/{repo}/commits/{sha}`); the subject must equal the quote exactly, the author must be IdkwhatImD0ing and the author time the same moment as `when`. One quote that fails, or that was never checked and cannot be checked now, and nothing is drawn (the old files stay). A commit that passed is noted in `var/lib/quotes-checked.json` (a hash names one commit forever), so `--offline` and a day the API is down can still draw it. `python scripts/render_hacklog.py --self-test` checks this offline. A build with no print says "No print yet" on plain paper; a build with no quote has none. Stars, forks and the repo address are not drawn (each picture links to the repo). Hand-written: `.plan` (a plain changelog of the page), `archive/README.md`, the back-shelf `<details>` with the STL fence (GitHub renders it as a 3D viewer), the small raw-source comment at the top (the MOON GATE word), and all the section text.

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
python scripts/render_hacklog.py                  # HACKLOG: the Shipped journal (--offline, --dry-run, --self-test)
python scripts/generate_prints.py                 # the journal's prints from scripts/data/journal/cap-*.jpg (Pillow, numpy)
python scripts/render_passwd.py                   # PASSWD register; without GITHUB_TOKEN it warns and exits 0
python scripts/update_currently_building.py --fallback-only --readme .preview/README.md --status .preview/status.json  # NOW + BUILD_PLATE without the LLM, on copies
python scripts/update_currently_building.py --dates-only   # what the moon watch runs
python scripts/update_currently_building.py --self-test    # the voice filter and line rules, offline
python scripts/generate_ansi_card.py              # bill.ansi
python scripts/generate_map.py                    # the map screen: assets/map/ and the MAP block (stdlib)
python scripts/generate_map.py cut --site ../PortfolioV5/client   # re-cut the painting and header strips (Pillow), then draw
```

A local run of the steward on the real README stamps the build plate "run 0 · from local"; run it on `.preview/` copies unless you mean to.

Local-only generators (`generate_glyphs.py` needs fontTools; `generate_map.py cut` needs Pillow; `generate_prints.py` needs Pillow and numpy; `capture_forge.cjs` needs Node and playwright-core; `generate_map.py`, `generate_chrome.py`, `generate_arena.py`, `generate_tiles.py`, `generate_token_stl.py` are stdlib) never run in CI. Everything CI runs is stdlib-only (`render_hacklog.py` only embeds the JPEGs `generate_prints.py` wrote).

The map screen's pictures come from the site, read-only: the painting is `public/sect/map/map_full.webp` (a painting, so a new scene bake does not change it) and the header band is the site's opening poster, `public/sect/poster/landscape.webp`, which is a capture of the 3D scene. After the scene is re-baked and the site's poster re-made, run `python scripts/generate_map.py cut --site ../PortfolioV5/client` and commit `scripts/data/map/head-*.jpg` and `assets/map/head*.svg`. The poster has pale tile seams in its corners, so `POSTER_BOX` in `generate_map.py` keeps the band inside its clean middle; check a new poster for the same. Never run Blender for this.

The journal's prints are captures of the 3D scene too (the forge, stop 03, taken 2026-10-24 before that night's bake). After a new bake: `node scripts/capture_forge.cjs <empty folder>` (check that the GPU line it prints is the real GPU), pick one frame per object where it faces the camera and set its `capture` and `box` in `scripts/data/journal/prints.json` (and the masks, `poly`/`ell`/`stroke`/`keep`, if the object moved inside the box), then `python scripts/generate_prints.py cut --cap <folder>`, `python scripts/generate_prints.py` and `python scripts/render_hacklog.py`, look at the prints, and commit `scripts/data/journal/cap-*.jpg`, `print-*.jpg` and `assets/journal/*.svg`. The orbit line of the forge ring runs through every object; the print step fills it in from the pixels above and below, which leaves a soft smudge where it crosses (on the flag's pole). The tipped-in photo comes from the site's `public/project-posters/dispatchai.webp` (`generate_prints.py photo --site ../PortfolioV5/client`).

### After the scene bake of 2026-10-24: what to recapture

The site's 3D scene is re-baked on the night of 2026-10-24, after the record plate landed. Two parts of this page are captures of that scene. Re-make them once the bake is live (and the site's poster is re-made), look at them, and commit:

| Part | Files to commit | How |
|:--|:--|:--|
| The map's header band (cut from the site's poster, `public/sect/poster/landscape.webp`) | `scripts/data/map/head-desk.jpg`, `head-desk-light.jpg`, `head-phone.jpg`; `assets/map/head.svg`, `head-light.svg`, `head-phone.svg` | `python scripts/generate_map.py cut --site ../PortfolioV5/client`; check the new poster's corners against `POSTER_BOX` |
| The journal's four prints (the forge, stop 03) | `scripts/data/journal/cap-*.jpg`, `print-*-spread.jpg`, `print-*-leaf.jpg`; `assets/journal/*.svg` (9 files) | `node scripts/capture_forge.cjs <empty folder>` (check the GPU line), update the boxes in `scripts/data/journal/prints.json`, `python scripts/generate_prints.py cut --cap <folder>`, `python scripts/generate_prints.py`, `python scripts/render_hacklog.py` |

Check the flag print's pole afterwards: it has a soft smudge where the forge's orbit line was painted out, which a cleaner frame removes. Nothing else on the page comes from the scene: the map's painting and its other twelve tiles (a painting), the DispatchAI photo (a project poster), the title cards, the record plate, the seal and the board are all drawn, so the bake does not touch them.

**Line endings.** The checkout uses CRLF (`core.autocrlf=true`) and the generators write LF, so after a run `git status` can list files whose content did not change. `git diff --stat` shows the real changes; `git checkout -- <file>` puts back a file that only changed its line endings.

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
- **The 36/59 record:** the lifetime totals (36 won of 59 entered; FullyHacks 2024, Tank, 1st place, counted since 2026-10-24) are `WON`/`ENTERED` in `scripts/ink.py`. Hand-written copies to update with them: the README (the intro's first sentence, the record plate's alt, which `generate_arena.py` prints a warning about, and the full record fold: its summary's "36" and one line for the new win) and the `var/log/hackathons.log` header; then re-run `generate_arena.py`, `generate_ansi_card.py` and `generate_map.py` (the legend's Hackathons row). `hackathons.log` holds only verified greatest hits; Bill appends one line per event (plus a `var/lib/ships.json` record).
- **No third-party widgets:** metrics, skylines, snakes, pin cards, shields and typing SVGs were retired long ago. Anything new is drawn locally through `ink.py`.
- **Fragile externals fail soft:** OpenAI and the GitHub API degrade to the last good data.
- `scripts/update_playbook_posts.py` is library-only and currently unused (the steward no longer reads the Playbook feed); its own `main()` targets markers that no longer exist.

## Archive policy

Nothing is deleted. Retired files move to `archive/` (with `git mv` where they were tracked), and verbatim snapshots are taken from git history. `archive/` is a museum: kept verbatim (its old text is not rewritten to the Voice rules; only `archive/README.md` is), never written by scripts, and nothing in it runs (GitHub only runs workflows in `.github/workflows/`). `archive/whitebox-os/` is the machine called tianni as found at commit `a864764`. `archive/sun-moon-v1/` is the first sect page as it was at commit `04bff9e`: the retired drawings and scripts (same relative paths), the README snapshot (petition links unwrapped, every picture it did not take along pinned to that commit), its CLAUDE.md, and the two workflows as they were. `archive/calling-card-v1/` holds what the second 2026-10-24 pass took off the page: the animated heroes, the man page and `README.md.bak`. `archive/calling-card-v2/` holds what the map screen replaced: the still hero and its titles, `generate_gate.py`, the four keys and the `generate_chrome.py` that drew them. `archive/calling-card-v3/` holds what the journal replaced: the four project cards (`assets/forge/`), the plain section headings, and `art_forge.py`, `render_hacklog.py` and `generate_chrome.py` as they were. `archive/calling-card-v4/` holds what the record plate replaced: the plain sword row and the `generate_arena.py` that drew it. `archive/README.md` is the index.
