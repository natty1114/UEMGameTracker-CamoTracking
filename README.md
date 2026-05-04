# UEMGameTracker-CamoTracking

A community-made external tracker for **Call of Duty: Black Ops III Zombies** and the **UEM mod**.

It provides a live dashboard, match history, camo tracking, XP graphs, ZPM graphs, overlays, challenges, themes, calling cards, and a Best Matches page.

> **Important:** You must accept/enable the API in the UEM mod for `CurrentGame.json` live tracking to work.

## Features

- Live game stats from `CurrentGame.json`
- Match history archive
- Weapon damage tracking beyond the visual damage cap
- Perk display with icons
- Match XP, XPM, Round XP, and ZPM graphs
- Optional ZPM overlay on the XPM graph
- Custom camo tracker for modded maps
- Starred priority weapons
- Career profile with rank, level, XP progress, and lifetime stats
- Challenges and unlockable rewards
- Themes and calling cards
- Theme-aware live overlay
- Optional Steam Workshop map images
- Best Matches page for saving and reopening favorite games

## Requirements

- Windows 10/11
- Call of Duty: Black Ops III
- UEM mod with API access enabled

If running from source:

- Python 3.x
- `pywebview`
- `pyinstaller`

## Setup

1. Download or build `BO3Tracker.exe`.
2. Keep the required asset folders/files beside the `.exe`:

```text
perk icons
rank icons
camoimages
callingcards
themes
style.css
setup.css
custom_camos.json
xp_requirements.csv
```

3. Run `BO3Tracker.exe`.
4. On first launch, select:
   - Your `CurrentGame.json` file
   - A history folder where match JSON files will be saved

## Running From Source

Install dependencies, then run:

```bash
python bo3tracker.py
```

To build a release executable:

```bash
python runner.py
```

## Smoke Tests

The project includes a smoke-test suite for basic validation:

```bash
python run_smoke_tests.py
```

The tests check core Python files, JSON files, required assets, build-script contents, XP rollover behavior, graph support, Best Matches support, and other app contracts.

## Project Notes

This project was built with help from Generative AI.

Some source code may look different from a traditionally structured app, including:

- Large HTML/CSS blocks embedded directly inside Python strings
- A monolithic main application file
- UI state logic written directly inside the generated app HTML

The project is provided as-is as a fun, community-focused tool.

## Troubleshooting

### Stats are not updating

- Make sure the UEM API is accepted/enabled.
- Make sure the tracker points to the correct `CurrentGame.json`.
- Some mods only update the file at certain times, such as round end or pause.

### Icons or images are missing

Make sure these folders/files are beside the executable:

```text
perk icons
rank icons
camoimages
callingcards
themes
style.css
setup.css
custom_camos.json
xp_requirements.csv
```

### Steam Workshop images are not showing

- Make sure the map has a valid Steam Workshop link in the game data.
- Make sure **Show Steam Workshop Images** is enabled in Settings.

### XP looks wrong

Use the XP Round Debugger in Settings to inspect:

- Level XP
- Tick XP
- Round XP
- Match XP
- Rank changes
- Rollover XP math

### Best Match saved the wrong game

The Add Best Match button saves the currently displayed game ID. If you are viewing an archived match, it should save that archived match. If no displayed game ID is available, it falls back to the current live match.

## Credits

Made for the Black Ops III Zombies community.

Special thanks to Sphynx for the UEM mod.

Call of Duty, Black Ops III, and related visual assets belong to Activision/Treyarch.
