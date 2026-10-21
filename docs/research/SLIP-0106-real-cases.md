# Real game cases by system and region (SLIP-0106 research)

Gathered 2026-10-21 by three web-research passes. **S** = a source is
linked; **U** = unverified belief, no source found. Box-protector figures
are inside sizes, so the box is about 1–3 mm smaller. Sizes are
W × H × D in mm, W being the front face's width. The PS1 rows were
re-read at their sources on 2026-10-21.

Main sources:
[OD] https://en.wikipedia.org/wiki/Optical_disc_packaging ·
[KC] https://en.wikipedia.org/wiki/Keep_case ·
[PAL] https://www.psxpaldb.com/case-types/ ·
[KO] https://kotaku.com/two-guys-making-new-sega-cd-jewel-cases-are-in-an-accid-1825364528 ·
[DJ] https://www.thedreamcastjunkyard.co.uk/2016/02/does-it-matter-if-youre-black-or-white.html ·
[PS] https://www.pacsam.ca/en/retro-game-box-protectors/ ·
[SS] https://www.screenscraper.fr/webapi2.php ·
[LB] https://feedback.launchbox-app.com/help/articles/3748363-image-standards-and-requirements

## Jewel and other disc cases

The standard jewel case is 125 × 142 × 10; slim is 5 deep [OD]. The front
booklet is 120 × 120 and shows the front only. The back card "is folded
into a flattened 'U' shape, with the sides being visible along the ends"
[OD], so the back carries a spine strip at both ends. Top and bottom are
bare plastic (U). Which end is the hinge is not stated; the Japanese obi
wraps "around the left side of the case" [OD].

| System, region | W × H × D | Plastic | Status |
|---|---|---|---|
| PS1 NTSC-U, early | long box, about 144 × 207 × 21 | U | S [KO] |
| PS1 NTSC-U, later | 125 × 142 × 10.4 | black tray, clear lid (U) | S https://vgcollect.com/forum/index.php?topic=5238.0 |
| PS1 PAL, 1–2 discs | 130 × 142 × 18 | black tray, PlayStation logo embossed front-left, on the spine, top and bottom | S [PAL], [OD] |
| PS1 PAL, 3+ discs | deeper "multiway" case, depth not found | | S [PAL] |
| PS1 NTSC-J, to about 1997–98 | 18 deep, logo on the side | | S https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q1494966934 |
| PS1 NTSC-J, later | standard 10 deep | | S same page |
| Saturn US, Sega CD US | long box, about 144 × 207 × 21 | | S [KO]; https://www.cgagrading.com/playstation-ps1-video-game-long-box-sega-saturn-cd-acrylic-display-case/ |
| Saturn JP, Sega CD JP | standard jewel | | S [KO] |
| Dreamcast US | 10.2 deep; 24 for multi-disc | clear tray | S [DJ] |
| Dreamcast JP | standard jewel | white tray | S [DJ] |
| Dreamcast PAL | thicker, depth not found | blue tray | S https://segareplay.com/product/pal-style-dreamcast-jewel-case-new/ |
| PC Engine CD JP, PC CD-ROM | standard jewel | | S [KO], [OD] |
| Neo Geo CD | jewel, spine card round the spine | | S https://videogameforums.com/neogeocd/neo-geo-cd-frequently-asked-questions |

## Keep cases and handhelds

One printed sheet wraps back + spine + front under a clear sleeve [KC].
That the opening edge is bare plastic is U.

| System, region | W × H × D | Plastic | Status |
|---|---|---|---|
| DVD keep case (PS2, Wii, Wii U, GameCube NA/PAL, PC) | 135 × 190 × 14 | PS2 black or navy, Wii white, Wii U blue | S [KC] |
| GameCube JP | 107 × 149 × 17 | clear | S [KC] |
| Xbox | 129 × 189 × 13 | green | S https://www.duplication.com/XBOX-LG-3.html |
| Xbox 360 | 133 × 187 × 13 | translucent green | S https://www.duplication.com/X360-GREENTINT.html |
| Blu-ray (PS3, PS4, PS5, Xbox One/Series) | 135 × 171.5 × 13 | PS3 clear, PS4/PS5 blue, Xbox green | S [KC] |
| PSP | 99 × 168 × 14 | clear | S [KC] |
| PS Vita | 105 × 135 × 12 | blue | S [KC] |
| DS NA/JP | 122 × 135 × 15 | black | S [KC] |
| DS EU | 122 × 135 × 20 | clear | S [KC] |
| 3DS | 122 × 135 × 12 | white | S [KC] |
| Switch | 104 × 170 × 10 | clear | S [KC] |
| Switch 2 | 104 × 170 × 10 | red | S [KC] |
| Genesis US, Master System | about 128 × 179 × 26 | black | S [PS] |

## Cartridge boxes

Printed cardboard. Which faces are printed, and with what, is U for every
system.

| System, region | W × H × D | Orientation | Status |
|---|---|---|---|
| NES US | 127 × 180 × 24 | portrait | S [PS] |
| Famicom | 142 × 98 × 22 | landscape | S (search snippet) |
| SNES US/PAL, N64 US/PAL | 181 × 127 × 32 | landscape | S [PS] |
| Super Famicom | 105 × 190 × 30 | portrait | S https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q10125589445 |
| N64 JP | 138 × 190 × 30 | portrait | S https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12257709902 |
| GB, GBC, GBA US/PAL | 126 × 126 × 23 | square | S [PS] |
| GBA JP | 90.5 × 138 × 24 | portrait | S https://retroprotection.com/product/japanese-game-boy-advance-box-protector/ |
| Atari 2600 | 140 × 194 × 23 | portrait | S [PS] |

## What the cover-art services supply

- ScreenScraper: `box-2D` front, `box-2D-back` back, `box-2D-side` one
  spine, `box-texture` (meaning U), `box-scan` [SS]. No top or bottom art.
- LaunchBox: separate Front, Back, Spine (one) and a Box - Full wrap [LB].
- libretro `Named_Boxarts`: in practice front covers only (U).
- Jewel-case back scans often keep both spine strips (U; the user's own
  PAL Ridge Racer Type 4 scan shows both).
