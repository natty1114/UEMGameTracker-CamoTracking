# BO3 Tracker Dev Log

## 2026-05-03

### Read-only inventory

Time: not recorded originally.

- Confirmed the project is a Python desktop app using `pywebview`.
- Identified `bo3tracker.py` as the main app entry point.
- Identified `runner.py` as the PyInstaller packaging script.
- Identified helper modules: `challenge_system.py`, `match_xp.py`, and `xpm_grapher.py`.
- Identified app data files, asset folders, and release/build folders.
- Confirmed `git` is not available on PATH in this environment.
- Confirmed `rg` could not be used due to Windows access permissions.

### Safety baseline

Time: not recorded originally.

- Added `PROJECT_INVENTORY.md` as a living map of the project.
- Added this `DEV_LOG.md` for decisions, changes, and smoke-test results.
- Added a smoke-test runner that avoids importing or launching the app.
- Created `manual_review_not_active_app/`.
- Moved inactive review candidates into `manual_review_not_active_app/`:
  - `bo3tracker - Copy.py`
  - `xpm_grapher - Copy.py`
  - `xptracker.py`
  - `xptrackerV2.py`
  - `workshop_puller.py`
- Left all release build folders in the main folder by user request.

### Decisions

- User requested that decisions be confirmed before being made.
- User approved creating inventory/dev-log/smoke-test files.
- User requested files/folders unrelated to `runner.py` or the active `bo3tracker.py` app be placed in a separate folder for manual review.
- User clarified that release builds should stay in the main folder.

### Smoke tests

Time: not recorded originally.

- `python .\run_smoke_tests.py` could not run because `python` is not on PATH.
- `py .\run_smoke_tests.py` could not run because the Windows launcher found no installed Python.
- Smoke tests passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-03 XP debugger

Time: not recorded originally.

### Request

- User reported some round XP graph bars show zero XP after a rank gain on the previous round.
- User asked for a debugger that detects XP earned each round, including level and game ID, exposed as a Settings toggle that opens a separate window.

### Changes

- Added non-breaking debug snapshots to `MatchXPTracker`.
- Added an XP Round Debug Window toggled from the Settings tab.
- The debug window shows time, game ID, player, round, prestige, level, raw XP, tick XP, derived round XP, total match XP, and rank changes.
- Added smoke-test coverage for the new debug API surface.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Match XP rollover fix

Time: not recorded originally.

### Request

- User provided prototype logs showing correct XP across a same-prestige level change:
  - P20 L355 `6,208,790 / 6,778,400`
  - P20 L356 `786,350 / 6,797,800`
  - Expected gain: `1,355,960`

### Changes

- Updated `match_xp.py` to read `Total XP in Current Stage` from `xp_requirements.csv` instead of `Global Cumulative XP`.
- Added same-prestige level rollover math so Master Prestige level changes can add remaining previous-level XP plus current-level XP.
- Preserved the existing total match XP API and debug snapshot API.
- Added smoke-test coverage for the exact P20 L355 -> L356 example.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 XP debugger display update

Time: not recorded originally.

### Request

- User asked to show rollover math in the debugger.
- User asked to include map name.
- User asked to rename the raw XP value to something clearer, like current level progress.

### Changes

- Added rollover debug details to `MatchXPTracker` snapshots:
  - remaining previous-level XP
  - skipped-level XP, if any
  - current level progress
- Added Map and XP Math columns to the XP debugger window.
- Renamed the debugger's `Raw XP` column to `Level XP`.
- Updated the Settings helper text for the debugger.
- Added smoke-test checks for the rollover debug details.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Graph sizing update

Time: not recorded originally.

### Request

- User asked for the XPM graph and Round XP graph to fit the dark background area in the live player card view.

### Changes

- Removed the fixed `550px` graph wrapper width used by both chart renderers.
- Added responsive chart sizing based on the available panel width.
- Kept horizontal scrolling available when the number of round labels needs more width than the panel can provide.
- Updated shared graph CSS so both XPM and Round XP charts use the full container width.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Theme graph styling update

Time: not recorded originally.

### Request

- User asked for the graph sizing/layout changes to be reflected in the theme CSS files where applicable, while keeping each theme visually consistent.

### Changes

- Updated `themes/115_Origins.css` to match the responsive graph sizing behavior from `style.css`.
- Added theme-specific graph surface styling to:
  - `themes/Golden Divinium.css`
  - `themes/matrix.css`
  - `themes/RedHex.css`
  - `themes/retro.css`
  - `themes/trench.css`
  - `themes/void.css`
- Each theme now keeps full-width graph containers and themed backgrounds/borders for XPM and Round XP views.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Theme-aware chart colors

Time: not recorded originally.

### Request

- User asked whether XP graph bars and XPM line graph dots can change appearance to match the active theme.

### Changes

- Added a frontend `GRAPH_THEMES` palette map in `bo3tracker.py`.
- XPM line color, fill color, point fill, point border, Round XP bar fill, Round XP bar border, and tooltip highlight now follow the active theme.
- Existing open charts update immediately when a new theme is applied.
- Added smoke-test checks that every known theme has a graph palette.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Settings overlay toggle

Time: not recorded originally.

### Request

- User asked to move the overlay toggle to the Settings page.
- User asked to add timestamps to smoke-test notes in the README.

### Changes

- Moved the Live Overlay toggle card from Help & FAQ to Settings.
- Added timestamped recent passing-run notes to `smoke_tests/README.md`.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 README/dev-log timestamp notes

Time: 01:49:19 +01:00 Europe/London.

### Request

- User asked to add times to the README for when each change was made and to add those notes to the dev log.

### Changes

- Added a timestamped change timeline to `smoke_tests/README.md`.
- Marked older dev-log entries as `time not recorded originally` rather than inventing exact times.
- Added this timestamped dev-log entry for the logging update itself.

## 2026-05-04 ZPM graph and XPM overlay

Time: 01:56:23 +01:00 Europe/London.

### Request

- User asked to add a ZPM graph using the `zpm` value already displayed from `CurrentGame.json`.
- User asked for an option to overlay ZPM on the XPM graph.

### Changes

- Added per-round ZPM storage to `xpm_grapher.py`.
- Added `generate_zpm_data()` for chart-ready ZPM labels/data.
- Added a standalone ZPM graph button and chart in the live XP area.
- Added an `Overlay ZPM` control inside the XPM chart panel.
- The XPM overlay uses a right-side `Zombies/min` axis so XPM and ZPM keep separate scales.
- Extended theme graph palettes with ZPM line/fill colors.
- Added smoke-test checks for the ZPM graph feature.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Graph button text and sizing fix

Time: 02:03:27 +01:00 Europe/London.

### Request

- User reported corrupted text on the ZPM pop-out button.
- User reported the Overlay ZPM button was too small.

### Changes

- Replaced symbol-prefixed graph pop-out labels with plain ASCII labels:
  - `Pop-Out XPM`
  - `Pop-Out Round XP`
  - `Pop-Out ZPM`
- Added stable minimum width/height and no-wrap text styling to shared `.graph-popout-btn` styles.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Runner dev log copy

Time: 02:25:18 +01:00 Europe/London.

### Request

- User asked to update `runner.py` so the dev log is included in the release `scripts` folder.

### Changes

- Added `DEV_LOG.md` to the files copied into `Release_Build/scripts`.
- Renamed runner copy-loop messages from source script to source file to cover both `.py` and `.md`.
- Updated smoke tests to assert `runner.py` includes `DEV_LOG.md`.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Neon Pulse theme

Time: 02:35:00 +01:00 Europe/London.

### Request

- User asked to create a new theme for the app and place it in the `themes/` folder.
- User asked to log this change in the dev log with a date and timestamp.

### Changes

- Created `themes/neon_pulse.css` — a cyberpunk-inspired theme with cyan/magenta neon gradients, pulsing card glow, scanline overlay, and animated background.
- Added `neon_pulse` entry to `GRAPH_THEMES` in `bo3tracker.py` with matching chart colors (cyan XPM line, magenta points/bars/ZPM).
- Theme uses Orbitron font, custom neon cursor, gradient progress bars, and themed graph surface with dual-color grid lines.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Career profile level bar

Time: 02:45:00 +01:00 Europe/London.

### Request

- User asked to add a level progress bar to the career profile page showing current level progress.
- User suggested using `match_xp.py` for level/XP lookups.

### Changes

- Added `get_career_level_info()` API method in `bo3tracker.py` that:
  - Reads live `CurrentGame.json` data, falling back to the most recent `Game_*.json` from history
  - Extracts player 0's prestige, level, and XP
  - Uses `match_xp.xp_tracker_instance.get_xp_required(level)` to look up XP needed for the current level
  - Returns rank text, icons, XP progress percentage, and map name
- Added a new "CURRENT RANK" card at the top of the career tab HTML with:
  - Prestige and level icons
  - Rank text (e.g. "PRESTIGE 20") and subtitle ("Prestige 20 // Level 360")
  - Title and map name
  - Progress bar with "X / Y XP" and percentage display
- Updated `loadCareerData()` JavaScript to call the new API and populate the card elements
- Added smoke test checks for the new API method and HTML elements
- Added `neon_pulse` to the theme graph palette test list

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Career profile tier icons

Time: 03:00:00 +01:00 Europe/London.

### Request

- User asked to add the same legend/ultimate/absolute tier icons shown on the dashboard to the career profile level bar.

### Changes

- Updated `get_career_level_info()` in `bo3tracker.py` to return `ult_icon`, `abso_icon`, and `leg_icon` using the existing `get_tier_icon_src()` function.
- Updated the career tab JavaScript to dynamically inject tier icons into `career-prest-box`, matching the live tab's `updatePlayerUI()` pattern:
  - Removes old `.custom-tier-icon` elements on refresh to prevent duplication
  - Inserts leg, abso, ult icons before the prestige icon (visual left-to-right: Ult, Abs, Leg, Prest)
  - Matches icon height to the prestige icon's clientHeight

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-04 Steam Workshop image toggle

Time: 21:24:56 +01:00 Europe/London.

### Request

- User asked for a Settings toggle to disable Steam Workshop images so they do not show on the dashboard.

### Changes

- Added a persisted `workshop_images_enabled` setting, defaulting to enabled.
- Added a "Show Steam Workshop Images" toggle to Settings.
- The toggle hides the live dashboard and career Workshop images immediately when disabled.
- Python API calls now return no Workshop image while the setting is disabled, avoiding background image fetches.
- Added smoke-test coverage for the new Settings/API toggle contract.

## 2026-05-04 Theme-aware overlay

Time: 21:30:33 +01:00 Europe/London.

### Request

- User asked for the live overlay to work with each active theme.

### Changes

- Added `OVERLAY_THEMES` palettes for default, void, 115 Origins, RedHex, Golden Divinium, retro, matrix, trench, and neon pulse.
- Updated the overlay HTML to use CSS variables for background, border, title, damage, divider, fallback, and shadow colors.
- The overlay now applies the active theme when opened, during live overlay updates, and immediately when the app theme changes.
- Switched overlay update data passing to JSON-encoded values to avoid HTML/template escaping issues from perk markup.
- Added smoke-test coverage for the theme-aware overlay contract.

## 2026-05-04 Best matches page

Time: 21:43:01 +01:00 Europe/London.

### Request

- User asked for a Best Match page accessible through the sidepanel.
- User asked for saved best matches to be clickable links that open the game by game ID.
- User asked for an Add Best Match button on the live dashboard where it does not look out of place.

### Changes

- Added `best_matches.json` to store pinned best match records.
- Added a `BEST MATCHES` sidepanel page with clickable saved match rows.
- Added an `ADD BEST MATCH` button into the Current Mission card title area on the live dashboard.
- Added API methods for saving the current live match and returning enriched best match summaries from archived `Game_*.json` files.
- Updated history loading so best match rows can open archived games with the existing game report view.
- Added smoke-test coverage for the best match page/API contract.

## 2026-05-04 Best match target fix

Time: 21:45:27 +01:00 Europe/London.

### Request

- User reported Add Best Match was always saving the live match instead of the currently clicked/viewed map.

### Changes

- Updated the frontend Add Best Match action to pass the currently displayed game ID.
- Updated `add_current_best_match()` to accept a target game ID and resolve archived `Game_*.json` data first.
- Kept live-match fallback behavior for cases where no displayed game ID is available.
- Added smoke-test checks for the displayed-match save path contract.

## 2026-05-04 Best match removal

Time: 21:47:33 +01:00 Europe/London.

### Request

- User asked to remove maps from the Best Matches tab.

### Changes

- Added a REMOVE button on each Best Matches row.
- The remove action stops the row click from opening the match.
- Added `remove_best_match()` API method to update `best_matches.json`.
- Added smoke-test coverage for the remove action/API contract.

## 2026-05-05 Classic mode badge removal

Time: 00:28:51 +01:00 Europe/London.

### Request

- User asked to remove the classic mode icon because it is no longer needed and overlaps the Add Best Match button.

### Changes

- Removed the classic mode icon loader from `bo3tracker.py`.
- Removed the `classic_badge` image from the live dashboard Current Mission card.
- Removed the frontend mode-checking code that toggled the classic badge.
- Added smoke-test coverage to verify the classic badge code is no longer present.

## 2026-05-05 Tracker icons folder removal

Time: 00:31:55 +01:00 Europe/London.

### Request

- User asked to remove remaining references to `trackericons`, confirm the app should still run correctly, and remove the folder.

### Changes

- Removed `trackericons` from `runner.py` packaged assets.
- Removed `trackericons` from smoke-test required asset directories and runner asset checks.
- Removed `trackericons/` from `PROJECT_INVENTORY.md`.
- Deleted the local `trackericons` folder after verifying the resolved path was inside the workspace.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`
