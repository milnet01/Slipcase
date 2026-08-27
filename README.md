# Slipcase

**Turn a flat game cover into a picture of the box it came in.**

You give Slipcase the front cover of a game. It gives you back an image of
that game's case, turned at an angle, with a spine, edges and a soft shadow —
the kind of picture game libraries show on a shelf.

The result is a PNG with a transparent background, so it drops onto any
backdrop cleanly.

## Who it's for

Anyone tidying up a game collection. Slipcase is built to feed two things in
particular:

- **RetroArch** — its thumbnail system
- **LaunchBox** — its 3D box art style

You don't need either one to use it. The images are ordinary PNG files.

## What it can do

- **Build a 3D case** from a front cover, and optionally a back cover and spine.
- **Invent a spine** when you don't have one, from the platform's own colours
  plus the game title and serial number.
- **Match the real case.** Sizes come from actual measurements, so a Game Boy
  box is the right shape next to a DVD case.
- **Find covers for you.** Fetch artwork from ScreenScraper, TheGamesDB and
  libretro without leaving the app.
- **Do a whole folder at once** with batch mode.
- **Spin the box** and save it as an animation.
- **Split a cover** back out into separate back, spine and front images.

## Case types it knows

DVD Case · CD Jewel Case · NES Cartridge Box · SNES Cartridge Box ·
N64 Cartridge Box · Genesis Clamshell · Game Boy Box · GBA Box · DS Case ·
3DS Case · PSP Case · PS Vita Case · Switch Case · Universal Cart Case

## Getting it running

You'll need **Python 3.12** on Linux.

```bash
pip install -r requirements.txt
python3 main.py
```

That's it — the app opens a window.

To add it to your applications menu, copy `slipcase.desktop` into
`~/.local/share/applications/`. Edit the `Exec` and `Icon` lines first if you
keep the project somewhere other than where it is now.

## Using it

1. **Load a front cover** — or use **Search Online** to fetch one.
2. **Pick the case type** that matches the game.
3. **Adjust the angle** if you want. The default is 30 degrees, which is the
   LaunchBox look; you can go anywhere from 5 to 60.
4. **Export.** For RetroArch, keep the width at or under 512 pixels. For
   LaunchBox, somewhere between 800 and 1200 works well.

## Your settings and logins

Slipcase keeps its settings in `~/.config/slipcase/`. That folder is locked to
your user account only, and the settings file is saved so that only you can
read it.

If you sign in to ScreenScraper, those details are stored there — **not in the
project folder**, so they can't be committed to version control by accident.

## Notes for anyone changing the code

Run the tests before committing:

```bash
python3 -m pytest tests/ -v
```

`STANDARDS.md` is the rulebook — the rendering pipeline, and the security,
speed and memory rules that changes must not break. `CLAUDE.md` is the short
orientation. `ROADMAP.md` is generated from a shared database, so edit it
through the roadmap tooling rather than by hand.

## Licence

MIT — see [LICENSE](LICENSE). You may use, change and share this freely,
including in commercial work, as long as the copyright notice stays with it.
