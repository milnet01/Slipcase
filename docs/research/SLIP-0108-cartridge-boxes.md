# Cartridge boxes by system and region (SLIP-0108 research)

Gathered 2026-10-21 by one web-research pass in five lanes. The [NA],
[CC3], [VGP], [KC], [MD], [MS], [GG], [HU] and [BD] claims were re-read
at the source the same day. **S** = a source is linked; **U** = no
source found. Sizes are W × H × D in mm, W being the front face's
width. A protector size is the protector's, not the box's; no protector
page says whether its figure is inner or outer. Inch figures are
converted here. Quotes came back through a page-reading tool; check a
load-bearing quote by eye before building on it.

Sources:
[PS] https://www.pacsam.ca/en/retro-game-box-protectors/ ·
[RP] https://retroprotection.com/ (product pages, linked per row) ·
[KC] https://en.wikipedia.org/wiki/Keep_case ·
[VGP] https://en.wikipedia.org/wiki/Video_game_packaging ·
[NA] https://www.nintendoage.net/3rd-party-nes-hang-tab-boxes/ ·
[CC3] https://cartridgecorner.blog/2018/09/20/early-nintendo-entertainment-system-nes-box-art-designs-pt-3-the-gold-silver-experience/ ·
[GV] https://www.videogamegemvault.com/blogs/video-game-gem-vault-blog/piecing-together-the-history-of-nintendo-games-clues-to-use-when-dating-authenticating-nes-box-games-cartridges ·
[MD] https://segaretro.org/Mega_Drive_games ·
[MS] https://segaretro.org/Master_System_games ·
[GG] https://segaretro.org/Game_Gear_games ·
[CCG] https://cartridgecorner.blog/2019/11/13/sega-genesis-box-case-artwork/comment-page-1/ ·
[HU] https://ja.wikipedia.org/wiki/HuCARD ·
[BD] https://bordersdown.net/articles/features/2740950-neo-geo-the-future-is-now ·
[FC] https://note.com/kawag2011/n/nefc29c0e41b3 ·
[AV] https://videogamevariations.com/AtariCompanies/AtariGames/GeneralAtari.htm ·
[AVL] https://videogamevariations.com/AtariLabelList.doc.pdf

Sega Retro blocks plain page fetches; its pages were read in a real
browser.

## What Slipcase has today

`core/case_types.py` holds `NES Cartridge Box`, `SNES Cartridge Box`,
`N64 Cartridge Box`, `Game Boy Box`, `GBA Box` and `Genesis Clamshell`,
all with the `cardboard` texture, and `Universal Cart Case`, offered by
hand on every cartridge platform. The SNES and N64 boxes are portrait,
against the landscape US and PAL boxes in
`docs/research/SLIP-0106-real-cases.md`. The Genesis clamshell is
plastic but uses the cardboard texture. There is no case for Famicom,
Super Famicom, Master System, Game Gear, Atari 2600, PC Engine,
TurboGrafx-16, Neo Geo AES or Virtual Boy.

## The two kinds of box

The user's split holds. **Cardboard cartons** are printed on the outside
of every face. **Plastic cases** (Sega clamshells, keep cases, HuCard
jewel cases) carry a printed paper insert under a clear sleeve or lid.

Which faces of a cardboard carton carry art, beyond front, back and
sides, is sourced only for NES and Atari 2600, and there only as small
print on the end flaps. That the insert of a plastic case covers front,
spine and back and nothing else is sourced for DS and Switch covers
only; for Sega clamshells it is U.

## Nintendo cardboard

| System, region | Construction | Printed faces | W × H × D | Status |
|---|---|---|---|---|
| NES US | reverse straight tuck, locking bottom; flap opens from the back | front, sides (title, series colour), back; codes on flaps | 127 × 180 × 24 protector [PS] | S [NA], [CC3], [GV] |
| NES PAL | U | coloured region triangle on the spine [VGP] | U | U |
| Famicom | paper box; cart in a bag, then from 1985 a plastic tray | U | 112 × 70 × 20, 127 × 87 × 21, 140 × 96 × 21, by era | S [FC] |
| SNES US | cardboard; cart in a plastic container with dust sleeve | front, back; sides, top, bottom U | 178 × 127 × 32 measured | S, see below |
| SNES PAL | US box design | region triangle on the spine | U | S, see below |
| Super Famicom | paper box, clear plastic tray; portrait | U | 105 × 190 × 30 measured | S, see below |
| N64 US | cardboard with cardboard inner tray | U | 181 × 127 × 32 protector [PS] | S, see below |
| N64 PAL | trays and card differ from US, unstated how | region triangle on the spine | U | S, see below |
| N64 JP | portrait | U | 138 × 190 × 30 measured | S, see below |
| GB, GBC, GBA US | cardboard with insert tray | U | 126 × 126 × 23 protector [PS] | S, see below |
| GB, GBC PAL | clear plastic blister tray, then cardboard tray, then a slot moulded into the box | region triangle on the spine | U | S, see below |
| GB, GBC JP | cardboard; plastic cart case inside; small early size, later larger | U | 89 × 102 × 19 measured, size variant U | S, see below |
| GBA JP | smaller, portrait | U | 87 × 137 × 21 by caliper | S, see below |
| Virtual Boy | U | U | fits the GB protector [PS] | U |

Quotes and sources:

- NES US: "nearly every NES game box is an RST with a locking bottom";
  "the flap of the box, opens from the backside of the box" [NA]. Title
  "printed on the cover and the sides of the box" [CC3]. "Box flaps often
  feature a numeric code" [GV]. Hang tab on games "released from October
  of 1985 until Early September of 1987" [NA].
- Famicom: three hand-measured Lode Runner boxes, given 縦 × 横 × 奥行
  [FC]. Landscape. Pairing each size to a year is inferred from the
  page's order. Koei games came in plastic cases [FC].
- SNES US: "SNES games were packaged in cardboard boxes"; "the box
  measures 7" x 5" x 1.25"" (Chrono Trigger)
  https://scalar.usc.edu/works/chronicles/photos-of-the-chrono-trigger-snes-cartridge-box-and-its-contents.37
- SNES PAL: "Europe (PAL) adopted the North American box design"
  https://myretrogamehub.com/blog/differences-between-super-famicom-and-snes-box-art/
- PAL Nintendo spines "all have a small coloured triangle on their
  spines, but in each territory it is a different colour" [VGP].
- Super Famicom: "縦：19ｃｍ 横：10.5ｃｍ 厚さ：3ｃｍ 実際に測ってみました"
  https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q10125589445 ;
  tray: https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12216481812
- N64 US: "the cardboard box and inner tray"
  https://golisto.com/blog/consoles/the-nintendo-64-deep-dive-every-collector-should-read
- N64 PAL: "The spines, the cardboard quality, and the internal trays
  differ vastly" https://gamegavel.co.uk/n64-collecting-pal-versus-ntsc/
- N64 JP: "縦が約190mm 横が約138mm 奥行(厚み)が約30mm"
  https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12257709902
- GB PAL trays: https://gameverifying.com/wiki/cart-based-systems/gameboy/insert
- GB JP: two box sizes, the later "about 4/5 of the 'standard' Famicom
  box size" https://nintendosegajapan.com/2018/11/11/game-box-protectors-japanese-sizes/ ;
  "８９ｍｍ×１０２ｍｍ×１９ｍｍ"
  https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q12253844982 ;
  cart case in the box https://fumoto36.hatenablog.com/entry/2022/10/30/170510
- GBA JP: 「横幅は137.1㎜」「高さは87.3㎜」「厚さは21.3㎜」
  https://nantoka-game.com/ゲームボーイアドバンスの外箱の大きさやサイズについて/ ;
  the box stands portrait, so the page's 横幅 is read as height. Its
  protector is 90 × 138 × 24
  https://retroprotection.com/product/japanese-game-boy-advance-box-protector/
- GBA: "The Game Boy Advance's cardboard boxes are a little smaller than
  SNES/N64 packaging" [VGP].

Big boxes exist: SNES (Mario Paint, EarthBound) and N64 (Pokémon
Stadium, Star Fox 64) [PS].

## Nintendo plastic

| System | Case | W × H × D | Status |
|---|---|---|---|
| DS NA/JP | black keep case | 122 × 135 × 15 | S [KC] |
| DS EU | clear keep case | 122 × 135 × 20 | S [KC] |
| 3DS | white keep case | 122 × 135 × 12 | S [KC] |
| New 3DS EU | black keep case | 122 × 135 × 14 | S [KC] |
| Switch | clear keep case | 104 × 170 × 10 | S [KC] |
| Switch 2 | red keep case | 104 × 170 × 10 | S [KC] |

Inserts wrap front, spine and back: a DS cover template is front and
back panels with a spine between
(http://blog.supermediastore.com/article/how-to-print-dvd-video-game-covers);
a Switch cover is "Front cover 128 × 160 mm", "Spine width 10 mm",
"Full wrap 266 × 160 mm" (https://coverstitch.io/dimensions.html).
These are already in `docs/research/SLIP-0106-real-cases.md`.

## Sega

| System, region | Construction | W × H × D | Status |
|---|---|---|---|
| Master System US, PAL | plastic clamshell, clear sleeve over the cover | 128 × 179 × 26 protector [PS] | S [MS] |
| Mark III / Master System JP | cardboard | U | S [MS] |
| Mega Drive, all regions | plastic clamshell | 128 × 179 × 26 protector [PS] | S [MD] |
| Genesis US, Sega, from late 1994 | cardboard | thinner than the clamshell, size U | S [MD] |
| Genesis US, EA | own clamshell for its wider cart | U | S [MD] |
| Game Gear, all regions | cardboard; plastic cart case inside | 113 × 160 × 25 protector [PS] | S [GG] |

Quotes:

- [MS]: "In Japan, games were generally packaged in brown/gold cardboard
  packaging"; "In the west, games were packaged in plastic clamshell
  cases (which would also be used for the Mega Drive)".
- [MD]: Mega Drive games came in "plastic "clamshell" boxes"; "These
  boxes use the same dimensions as Western Master System games" and
  "were used in all regions, including Japan". "Towards the end of 1994
  Sega of America decided to start cutting costs, going back to flimsy
  cardboard boxes. Most third-party publishers, such as EA and Acclaim
  Entertainment, continued to use plastic." EA "adopted similar
  packaging for its games, albeit customised for their bespoke cartridge
  shells".
- [CCG] dates the Sega cardboard boxes to 1995 and names Sonic &
  Knuckles, Comix Zone, Phantasy Star IV and Shining Force II. [KC]: the
  games "were later packaged in pressboard boxes as a cost-cutting
  measure".
- [GG]: "All Game Gear games worldwide were distributed in cardboard
  packaging, though each cartridge was given a plastic container".
  A protector seller lists PAL Game Gear protectors "With Tab"
  (https://www.gameboxprotector.com/collections/sega), which may point to
  plastic PAL cases; that is an inference, so U.
- US cardboard boxes are thinner: "The thinner cardboard games will fit,
  but there will be a little gap"
  (https://stoneagegamer.com/box-protector-for-sega-master-system-genesis-and-32x.html).
- Sega cards: "slightly smaller and much thinner then the standard
  Master System cases" (https://gametrog.com/sega-master-system-information-specs/).

Japanese Mega Drive cases are called smaller by one collector guide, but
[MD] says the clamshell dimensions are shared with the west, and a JP
protector (132 × 180 × 29,
https://www.retrogamecity.com/product-page/sega-mega-drive-japanese-game-box-protectors-pack-of-5-clear-boxes)
is not smaller. Treat JP size as U.

Which faces the clamshell insert covers is U. Golisto calls it "a
printed paper sleeve tucked under the plastic" and notes "sun-faded
spines"
(https://golisto.com/blog/pricing/boxed-vs-loose-mega-drive-games-and-the-clamshell-advantage).
Western clamshells had hang tabs; Japanese ones "did not have hanging
tabs until some of their very late releases"
(https://retromegabit.com/tag/clamshell/).

## Atari, NEC, SNK

| System, region | Construction | Printed faces | W × H × D | Status |
|---|---|---|---|---|
| Atari 2600 | cardboard; book-opening first, then tuck top and bottom flaps | front, back, sides with title; small print on end flaps | 140 × 194 × 23 protector [PS] | S [AV], [AVL] |
| PC Engine HuCard | CD jewel case; card in a soft vinyl sleeve | front via the manual cover; early: sticker on spine and back; later: back jacket and obi | 142 × 125 × 10 jewel case [OD] | S [HU] |
| TurboGrafx-16 TurboChip | plastic case with a holding clip | U | 152 × 178 × 17.5 protector | S, see below |
| Neo Geo AES | cardboard carton (early titles), then plastic clamshell, then snap-lock case | spine card (JP), US stamp on spine | 220 × 165 × 44 measured | S [BD], see below |

[OD] = https://en.wikipedia.org/wiki/Optical_disc_packaging .

Quotes and sources:

- [AV]: "The original games had the book opening type box, but
  afterwards, the boxes were opened at the top flap." [AVL]: "The bottom
  flap also tucks into the box"; "Company info is found on the bottom
  tiny flaps". Cardboard: https://collection.sciencemuseumgroup.org.uk/objects/co8225471/combat-for-the-atari-2600-game-packaging-packaging .
  PAL boxes differ by carrying "5 or 6 languages on the box" [AV]; size U.
- [HU]: 「ケースにはCD用ケースをベースとしたパッケージが使われ、ソフトビニールケースに入ったHuCARD本体が収納される。」;
  early 「背の部分と裏側に商品名が書かれた簡素なシールが貼られた」; later
  「裏ジャケットや帯の付いた物に変更された」.
- TurboChip: US cases have a "holding clip" the Japanese ones lack
  (https://pceworks.wordpress.com/2020/02/29/hucard-basics/); protector
  "6.00 × 0.6875 × 7.000 in"
  (https://retroprotection.com/product/turbografx-box-protector-1-protector/).
  That it is taller than a jewel case is inferred from the protector.
  [PS]'s TurboGrafx figure is not used: its depth matches no game box.
- [BD]: "Cartons. These are cardboard boxes with plastic inserts"; "Clamshells.
  These are fold-over plastic cases"; "all the later games post 1995/96
  come in" snap-lock cases. Size: "I measured a couple and got 220 mm x
  165 mm x 44 mm"
  (https://neogeoforever.com/thread/1419/dimensions-inches-aes-cases);
  orientation of that figure is U. Spine card:
  https://nostos.market/guides/neo-geo-aes-vs-mvs-buyers-guide .
  The AES insert layout is U.

## Not found

Face-by-face print on the top and bottom of any Nintendo carton; the
Sega clamshell insert's extent; PAL NES and SNES construction and size;
Super Famicom opening end; Virtual Boy box construction; JP Game Gear;
original measured sizes for NES, N64, GB, Genesis, Master System and
Atari boxes (protector sizes only).
