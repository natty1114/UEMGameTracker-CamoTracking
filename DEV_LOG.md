# BO3 Tracker Dev Log

## 2026-05-15 Version 4.4.0 — Launch readiness and global weapon backfill

### Request

User asked to make sure the app is ready to launch and bump the version number by 0.1.

### Changes

1. Bumped release metadata from `4.3.0` to `4.4.0` in `app_version.json`.
2. Bumped `app_metadata.py` fallback `DEFAULT_VERSION` to `4.4.0`.
3. Updated Windows executable metadata files to `4.4.0.0`:
   - `version_info_bo3tracker.txt`
   - `version_info_updater.txt`
4. Added `CHANGELOG_4.4.0.md` covering the global weapon tracking changes.
5. Updated `runner.py` to package `CHANGELOG_4.4.0.md` with release builds.
6. Verified smoke tests pass with the bundled Python runtime.

## 2026-05-14 Map weapons two-way sync infrastructure

### Request

User wanted two-way sync for map_weapons.json between all running tracker clients without FTP credentials in the runtime app. Sync must be automatic for all users during gameplay, not just manual via the dev tool.

### Changes

1. **Created `site/public_html/tracker/map_weapons_sync.php`** — Stateless file-based sync endpoint:
   - GET returns the current `map_weapons.json`.
   - POST merges incoming data on top of existing data (never deletes, only adds/reconciles).
   - Weapons deduplicated by `console_name` within each map entry — no duplicate entries.
   - No DB dependency, self-contained with `json_response()` pattern and `LOCK_EX` file writes.

2. **Created `sync_map_weapons.py`** — Client sync module:
   - `fetch()`: GET from remote with ETag caching, TLS fallback, 24h rate limit.
   - `push()`: POST local data to server.

3. **Extended `MapWeaponsManager`** with `sync_from_remote()` and `push_to_remote()`:
   - `sync_from_remote()` fetches remote data and merges new maps/weapons into local.
   - `push_to_remote()` sends the full local data to the server.

4. **Added `map_weapons_sync_url` to `app_version.json`** (reads `app_metadata.MAP_WEAPONS_SYNC_URL`).

5. **Hooked into bo3tracker.py**:
   - `schedule_map_weapons_startup_sync()`: **Two-way startup sync** — pulls remote data first, then pushes local discoveries. Every user shares their discoveries on every launch.
   - `schedule_map_weapons_push()`: **Auto-push during gameplay** — after `discover_from_game()` saves new weapons, pushes them to the server so all users benefit. Rate-limited to once per 5 minutes.
   - Separate thread locks (`map_weapons_sync_lock` / `map_weapons_push_lock`) so pull and push don't block each other.

6. **Added Sync/Upload buttons to dev tool** Map Weapons tab (manual override).

7. **Added `sync_map_weapons.py` to runner.py** release source list.

### Verification

- Python compile checks passed for all touched modules.
- All smoke tests pass (including new runner source file check for `sync_map_weapons.py`).

## 2026-05-11 Map compatibility packaging

### Request

- User wanted the BO3 Tracker MAP COMPAT button to open the separate local map compatibility app without breaking camo tracker functionality.
- User asked for any map-app packaging scripts to stay inside `local map compatiblityu`.
- User also asked about avoiding bundled Google credentials and moved submissions toward an Apps Script endpoint.

### Changes

- Updated `bo3tracker.py` so `launch_map_compat_window()` uses `get_base_path()` and prefers `local map compatiblityu/UEMMapCompatibility.exe` when present, falling back to `app.py` for development.
- Added `local map compatiblityu/build_map_compat.py` and `local map compatiblityu/UEMMapCompatibility.spec`.
- Updated `runner.py` to call the local map compatibility builder and include the generated map app folder in `Release_Build`.
- Updated the map compatibility app so Help and Settings open as pywebview windows in the same process, avoiding frozen-exe relaunch problems.
- Added `apps_script_submission_endpoint.gs` and endpoint config support in `sheet_db.py`.
- Configured the map app to use the deployed Apps Script endpoint and secret supplied by the user.
- The map compatibility build script skips Google service-account credential JSON files by default.

### Verification

- `python -m py_compile` passed for the edited tracker, runner, and map app modules.
- `python "local map compatiblityu\\build_map_compat.py"` built `UEMMapCompatibility.exe`.
- `python runner.py` completed and created `BO3Tracker-3.8.zip` with `Release_Build\\local map compatiblityu\\UEMMapCompatibility.exe`.
- Confirmed the generated release did not include `google_credentials.json`.
- Apps Script endpoint direct test returned `{"ok":true}` and created a test submission row.
- Local Python HTTPS verification on this machine still reports a certificate-chain error for Google endpoints; insecure verification was used only for the one manual endpoint test, not as the app default.

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

## 2026-05-05

### Prepared Release 2.8 build folder

- Rebuilt `Release_Build` from the current 2.8 source using `runner.py`.
- Confirmed the copied files in `Release_Build/scripts` match the root source files.
- Confirmed local runtime files such as `config.json`, `global_stats_state.json`, and graph/challenge progress files are not included in the clean release folder.
- Added runner safety checks so server/private files are rejected if they ever appear in the release output.

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

- Created `themes/neon_pulse.css` â€” a cyberpunk-inspired theme with cyan/magenta neon gradients, pulsing card glow, scanline overlay, and animated background.
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

## 2026-05-05 Version 2.8 anonymous global stats opt-in

Time: 17:31:05 +01:00 Europe/London.

### Request

- User asked to add a version 2.8 manual opt-in popup for the global anonymous stats database.
- User asked for a Settings toggle to opt in/out.
- User wanted no personally identifiable information collected.
- User wanted duplicate protection when changing the EXE so the same archived games are not uploaded multiple times.
- User asked to make sure passwords are not visible to end users or copied into the build/GitHub scripts.

### Changes

- Added `global_stats_client.py` as the app-side uploader for anonymous archived match summaries.
- Added a versioned 2.8 privacy modal shown once until the user accepts or declines.
- Added a Settings card with an opt-in/out toggle and manual `SYNC NOW` button.
- Added background sync scheduling on opt-in, app startup, and archive save, with local rate limiting.
- Added `global_stats_state.json` as the local upload state file beside the app/config, so EXE changes do not reset uploaded-match memory.
- Kept backend dedupe by anonymous `game_id_hash` as a second protection layer against duplicate game uploads.
- Added `global_stats_client.py` to the release source-script copy list in `runner.py`.
- Added `.gitignore` entries for local config, upload state, and server-side Namecheap secrets.
- Confirmed `namecheap/backend/config.php` is not part of the runner build asset/source lists.

### Privacy and security notes

- The uploader does not send Steam IDs, Windows usernames, local file paths, raw archive JSON, profile files, or database credentials.
- The desktop app contains the public submit URL and ingest token required by the endpoint; this token is not a database password and should be treated as abuse friction rather than a true secret.
- The Namecheap database password remains only in `namecheap/backend/config.php`, which is excluded from `.gitignore` and not copied by `runner.py`.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-05 Global stats profile dedupe hardening

Time: 17:51:49 +01:00 Europe/London.

### Request

- User reported global career Player Points and GobbleGums could still double during testing.
- User asked to update the dev log and smoke tests after the fix.

### Changes

- Added a stable anonymous `profile_hash` to the app-side and test uploader payloads.
- Changed the profile hash from career-value-based to archive-anchor-based so career growth does not create new profile rows.
- Updated `submit_stats.php` to upsert `contributor_profiles` by `profile_hash` as well as contributor hash.
- Added `migration_add_profile_hash.sql` and `cleanup_profile_duplicates.sql` for server-side migration/cleanup support.
- Added smoke-test coverage for:
  - version 2.8 global stats opt-in UI/API contract,
  - upload dedupe fields (`game_id_hash`, `profile_hash`, upload state),
  - runner not referencing server secrets,
  - `.gitignore` excluding local state and Namecheap server config.

### Notes

- Existing inflated `contributor_profiles` rows should be cleaned once on the server, usually with `TRUNCATE TABLE contributor_profiles;`, then data can be resent with the updated uploader.
- The app still does not send database credentials or raw archive/profile files.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-05 Global stats manual sync cooldown

Time: 17:57:00 +01:00 Europe/London.

### Request

- User asked whether repeatedly pressing `SYNC NOW` could spam the database.
- User asked to add protection against manual sync hammering.

### Changes

- Added `MANUAL_SYNC_INTERVAL_SECONDS = 2 * 60` to the app-side global stats client.
- Updated `sync_history()` so manual/forced sync still respects a 2-minute local cooldown.
- Kept background sync on the longer 15-minute cooldown.
- Added clearer stored sync messages for local cooldown, no-history, no-new-match, and successful sync outcomes.
- Updated smoke-test coverage to check the manual cooldown constant is present.

### Notes

- Backend rate limiting still remains in place as the second line of defense.
- Match/profile dedupe still prevents repeated sync attempts from inflating uploaded stats.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-05

### Restored global stats upload flow

- Reverted the experimental contributor-token/register flow and restored `submit_stats.php` authentication to the configured `GLOBAL_STATS_INGEST_TOKEN`.
- Removed the runtime `GLOBAL_STATS_INGEST_TOKEN` / `config.json` dependency from the app uploader so packaged sync works as it did before.
- Removed the temporary token migration/register backend files that caused uploads to fail when the live database did not have the new token table.
- Made backend rate limiting skip cleanly if the optional `ingest_rate_limits` table has not been installed yet.
- Kept the 2-minute manual sync cooldown, 15-minute background cooldown, game-id dedupe, and profile max-value handling.

### Smoke tests

- Passed using Codex bundled Python:
  - `C:\Users\Nat\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .\run_smoke_tests.py`

## 2026-05-05 Optional GitHub updater packaging

Time: 22:54:08 +01:00 Europe/London.

### Request

- User asked to prepare update 2.9 packaging so future releases include an updater.
- User wanted updates to stay optional, with a small sidebar notification near Settings.
- User asked to run smoke tests and append the dev log.

### Changes

- Bumped the app and global stats client version constants to 2.9.
- Added a GitHub Releases update check against `natty1114/UEMGameTracker-CamoTracking`.
- Added an optional sidebar update notice and Settings update status/check control.
- Added `updater.py`, a separate updater program that downloads the selected release zip, waits for BO3 Tracker to close, replaces release-managed files, preserves user/runtime JSON and cache files, and restarts the app.
- Updated `runner.py` to build and package `BO3Updater.exe` alongside `BO3Tracker.exe`, and to copy `updater.py` into release scripts.
- Added smoke-test coverage for updater packaging and optional update UI/API contracts.

### Notes

- Updates are not forced. The app checks quietly and only launches the updater when the user clicks `UPDATE NOW`.
- Existing users will need to install 2.9 manually once so `BO3Updater.exe` is present for later automatic updates.
- Future GitHub releases should upload a zip asset containing the contents of `Release_Build` and mark the newest release as latest.

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py updater.py runner.py global_stats_client.py run_smoke_tests.py`
  - `python run_smoke_tests.py`

### Release build

- Passed:
  - `python runner.py`
- Confirmed `Release_Build` includes:
  - `BO3Tracker.exe`
  - `BO3Updater.exe`
  - release assets and copied scripts
- Created upload package:
  - `BO3Tracker-2.9.zip`

## 2026-05-05 Versioned release zip packaging

Time: 22:58:58 +01:00 Europe/London.

### Request

- User asked whether `runner.py` can package the build and zip it using the correct version number.

### Changes

- Updated `runner.py` to read `APP_VERSION` from `bo3tracker.py`.
- Added automatic release zip creation after the release folder is assembled and safety-checked.
- The zip is named from the app version, for example `BO3Tracker-2.9.zip`.
- The zip contents are rooted at the release files themselves, so `BO3Tracker.exe` and `BO3Updater.exe` appear at the top level after extraction.
- Added smoke-test coverage for the versioned zip packaging contract.

### Smoke tests

- Passed using local Python:
  - `python -m py_compile runner.py run_smoke_tests.py`
  - `python run_smoke_tests.py`
  - `python runner.py`

## 2026-05-05 App version label

Time: 23:05:54 +01:00 Europe/London.

### Request

- User asked to show the version number somewhere in the app.

### Changes

- Added a small persistent version label at the bottom of the sidebar.
- Kept the existing Settings App Updates version display.
- Added smoke-test coverage for both visible version surfaces.

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py run_smoke_tests.py`
  - `python run_smoke_tests.py`

## 2026-05-05 Darkwood theme

Time: 23:10:27 +01:00 Europe/London.

### Request

- User provided a screenshot of a dark brown and gold app style and asked to implement it with a name.

### Changes

- Added a new selectable theme named `Darkwood`.
- Created `themes/Darkwood.css` with a dark walnut/brown background, gold headings, amber controls, grid texture, and framed configuration cards.
- Added matching Darkwood graph colors.
- Added matching Darkwood live overlay colors.
- Made `Darkwood` always available in the theme selector instead of challenge-locked.
- Added smoke-test coverage for the new theme contract.

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py run_smoke_tests.py`
  - `python run_smoke_tests.py`

## 2026-05-05 Version 3.0 release prep

Time: 23:12:25 +01:00 Europe/London.

### Request

- User asked to package the latest version numbering and Darkwood theme changes as the next version.

### Changes

- Bumped the app version from 2.9 to 3.0.
- Bumped the global stats client app version to 3.0.
- Updated updater user-agent metadata to 3.0.
- Kept the runner versioned zip flow so the next package is generated as `BO3Tracker-3.0.zip`.
- Made the updater-missing message version-neutral for users who still need one manual install.

### Notes

- This makes the Darkwood theme release the next GitHub version.
- Recommended GitHub release metadata:
  - Tag: `V3.0`
  - Title: `BO3 Tracker V 3.0`
  - Asset: `BO3Tracker-3.0.zip`

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py global_stats_client.py updater.py run_smoke_tests.py runner.py`
  - `python run_smoke_tests.py`

## 2026-05-05 Update rollback support

Time: 23:37:18 +01:00 Europe/London.

### Request

- User asked for a rollback feature so the app can return to the previous version after an update.

### Changes

- Bumped the app, updater, and global stats client version metadata to 3.1 for the rollback release.
- Updated `BO3Updater` to create a backup of release-managed app files before installing an update.
- Added update backup metadata in `rollback_info.json`.
- Kept user/runtime files preserved and outside rollback backups.
- Added rollback mode to `BO3Updater`.
- Added a Settings -> App Updates `ROLLBACK LAST UPDATE` button.
- Added app API support for launching rollback through the updater.
- Added smoke-test coverage for backup/rollback contracts.

### Notes

- Rollback restores the most recent `Backups/app_update_*` snapshot.
- Rollback still uses the separate updater executable, because the main app cannot safely replace its own running executable.
- Recommended GitHub release metadata:
  - Tag: `V3.1`
  - Title: `BO3 Tracker V 3.1`
  - Asset: `BO3Tracker-3.1.zip`

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py global_stats_client.py updater.py run_smoke_tests.py runner.py`
  - `python run_smoke_tests.py`

### Follow-up polish

- Applied BO3 Tracker default dark/cyan styling to the updater window.
- Styled updater panels, title text, status text, and action buttons to match the main app's default theme.
- Added smoke-test coverage for updater UI styling markers.

## 2026-05-06 Updater self-replacement fix

Time: not recorded.

### Request

- User reported the updater styling did not appear and rollback did not seem to create backups.
- User suspected antivirus may have blocked the updater initially, then allowed the app afterward.

### Findings

- The updater styling and rollback code existed in source and the release scripts.
- The installed `BO3Updater.exe` could remain old because updates preserved `BO3Updater.exe` to avoid overwriting the running updater process.
- If an older updater installed a newer release, it could update `BO3Tracker.exe` but leave the old updater in place, so backup/rollback and updater styling would not appear.

### Changes

- Bumped release metadata to 3.2.
- Changed the app to launch `BO3Updater.exe` from `%TEMP%`.
- During updates, the app extracts the updater executable from the target release zip first, so stale installed updater copies do not keep running forever.
- Removed `BO3Updater.exe` from the updater preserve list so the release-managed updater exe can be replaced safely.
- Added `BO3Updater.exe` to the updater managed files list so it is backed up, installed, and restored.
- Kept rollback using the same temporary-launch approach so rollback can restore the updater executable too.
- Added smoke-test coverage for the temporary updater launch path.

### Notes

- This should fix future in-app updates replacing `BO3Updater.exe`, even if the currently installed updater is stale.
- Users whose antivirus blocked the updater before may not have an update backup from that failed/blocked attempt.
- Recommended GitHub release metadata:
  - Tag: `V3.2`
  - Title: `BO3 Tracker V 3.2`
  - Asset: `BO3Tracker-3.2.zip`

### Smoke tests

- Passed using local Python:
  - `python -m py_compile bo3tracker.py global_stats_client.py updater.py run_smoke_tests.py runner.py`
  - `python run_smoke_tests.py`

## 2026-05-06 Version 3.3 theme and changelog update

Time: not recorded.

### Request

- User asked for richer theme backgrounds across multiple themes.
- User asked for theme images to load reliably in the pywebview app.
- User asked for a changelog section that pulls current version changes from GitHub.
- User bumped version metadata to 3.3 and asked whether it would break the app.

### Changes

- Bumped app metadata to `APP_VERSION = "3.3"` in `bo3tracker.py`.
- Bumped global stats client metadata to `APP_VERSION = "3.3"` in `global_stats_client.py`.
- Bumped `GLOBAL_STATS_PROMPT_VERSION` to `3.3`.
- Updated smoke-test expectations to the 3.3 app version.
- Fixed theme asset URL handling so injected theme CSS can load local image assets reliably in WebView2.
- Kept small startup/default assets embedded as data URIs while avoiding the previous large-startup-HTML crash pattern.
- Added or wired themed background assets for:
  - default tactical
  - Cherry Blossom
  - Darkwood
  - Golden Divinium
  - Matrix
  - Neon Pulse
  - RedHex
  - Retro
  - Trench
  - Void
- Added Cherry Blossom graph colors so chart lines, points, and bars match the theme.
- Fixed Cherry Blossom live feed/status text readability.
- Tuned RedHex, Retro, Trench, and Void image sizing so backgrounds fill the visible app panel without unwanted gaps.
- Added a `LATEST CHANGELOG` card to Help & FAQ.
- Added `TrackerAPI.get_latest_changelog()` to fetch the latest GitHub release title/body from the existing releases API.
- Added frontend changelog rendering with a refresh button and graceful failure text.
- Fixed the changelog JavaScript newline escaping bug that caused the app to freeze at `CONNECTING...` and made buttons stop responding.
- Updated the global stats opt-in modal text to use `GLOBAL_STATS_PROMPT_VERSION` instead of a hardcoded old version string.

### New assets

- `default_tactical_background.jpg`
- `default_tactical_background.png`
- `themes/cherry_blossom_anime_flowers.png`
- `themes/darkwood_wooden_board_background.jpg`
- `themes/darkwood_wooden_board_background.png`
- `themes/golden_divinium_background.jpg`
- `themes/golden_divinium_background.png`
- `themes/matrix_cracked_code_background.jpg`
- `themes/matrix_cracked_code_background.png`
- `themes/neon_pulse_city_background.jpg`
- `themes/neon_pulse_city_background.png`
- `themes/redhex_tactical_background.jpg`
- `themes/redhex_tactical_background.png`
- `themes/retro_retrowave_background.jpg`
- `themes/retro_retrowave_background.png`
- `themes/trench_bunker_background.jpg`
- `themes/trench_bunker_background.png`
- `themes/void_event_horizon_background.jpg`
- `themes/void_event_horizon_background.png`

### Notes

- GitHub currently reports latest published release `3.2`; the new Help & FAQ changelog panel will show the latest published release until a `3.3` GitHub release is published.
- Recommended GitHub release metadata:
  - Tag: `V3.3`
  - Title: `BO3 Tracker V 3.3`
  - Asset: `BO3Tracker-3.3.zip`

### Smoke tests

- Passed using local Python:
  - `python -W error::SyntaxWarning -m py_compile bo3tracker.py`
  - `python run_smoke_tests.py`
- The generated main app script was also checked with:
  - `node --check tmp_app_script.js`

## 2026-05-06 Theme CSS cascade fix

### Problem

Custom themes (e.g., Pacific Paradise) were being overridden by `style.css` rules because of CSS source order. In `bo3tracker.py`, the `#theme-injector` style tag appeared BEFORE the main `style.css` content, causing `style.css` rules with equal specificity to win.

### Fix

Swapped the order in `get_main_app_html()` so that:
1. Main `style.css` content is injected first
2. `#theme-injector` (theme CSS) is injected second
3. Hard-coded UI styles remain last (as "Firewall 2" protection)

This ensures theme CSS appears later in source order and correctly overrides `style.css` defaults.

### Files changed

- `bo3tracker.py`: Moved `<style id="theme-injector">` to appear after the main CSS block (lines ~1243-1249)

### Smoke tests

- All 130+ smoke tests passed after the change.
- No regressions detected; default theme behavior unchanged.

## 2026-05-06 Move default CSS from bo3tracker.py to style.css

### Problem

Several default UI styles (toggle switches, challenge system, player card selector, privacy modal, update notice, app-version-label) were hard-coded in `bo3tracker.py` inside a `<style>` block labeled "Firewall 2". This made `style.css` incomplete and harder to maintain.

### Fix

Moved all default UI CSS rules from `bo3tracker.py` to `style.css`:
1. Toggle switch styles (`.switch`, `.slider`, etc.)
2. Challenge system UI (`.chal-grid`, `.chal-card`, `.chal-btn`, `.theme-header`)
3. Player card selector (`.card-selector-img`, `.card-display-header`)
4. Privacy modal (`.privacy-modal-backdrop`, `.privacy-modal`, etc.)
5. Update notice (`.update-notice`, `.update-status`)
6. `.perk-item` override
7. `.app-version-label`

Kept only theme-specific CSS in `bo3tracker.py`:
- `body.theme-void` and related `@keyframes gradientBG`
- `body.theme-pacific-paradise` and related `@keyframes`

### Files changed

- `style.css`: Added ~60 lines of default UI styles
- `bo3tracker.py`: Removed ~60 lines of default CSS, kept only theme-specific rules

### Smoke tests

- All 130+ smoke tests passed after the move.
- No regressions detected; default UI renders correctly.

## 2026-05-06 Remove dead theme CSS from bo3tracker.py

### Problem

`bo3tracker.py` contained hard-coded CSS rules for `body.theme-void` and `body.theme-pacific-paradise` (plus `@keyframes` for `gradientBG`, `tropicalDrift`, `sunGlare`, `breezeSweep`). These are **dead code** — no JavaScript ever applies `theme-void` or `theme-pacific-paradise` classes to the `<body>`. The actual theme files (`void.css`, `Pacific Paradise.css`) already define these styles directly on `body`.

### Fix

Removed the entire "Firewall 2" `<style>` block from `bo3tracker.py` since:
1. Theme-specific CSS belongs in `/themes/*.css` files
2. Default UI styles now live in `style.css` (from previous commit)
3. The `#theme-injector` mechanism handles custom theme loading

### Files changed

- `bo3tracker.py`: Removed ~30 lines of dead theme CSS (void, pacific-paradise body rules + keyframes)

### Smoke tests

- All 130+ smoke tests passed after removal.
- No regressions; theme loading via `#theme-injector` works correctly.

## 2026-05-06 Pacific Paradise theme readability & hover fixes

### Problem

1. **Text readability**: Some text in Pacific Paradise theme was hard to read against the light background (e.g., `.sb-date`, `.sb-id`, `.stat-sub`, `p`, `li` had low contrast colors like `#2a2a2a`)
2. **Weird hover box**: Archived match items showed an unwanted "box" effect on hover due to `text-shadow: 0 1px 0 rgba(255,255,255,0.75)` in the hover rule

### Fix

Updated `themes/Pacific Paradise.css`:

1. **Text colors** - Improved contrast:
   - `.stat-big`, `#d_map`, etc.: Changed from `#1a4d2e` to darker `#0d3b1e`
   - `.stat-sub`, `p`, `li`, `.sb-date`, `.sb-id`: Changed from `#2a2a2a` to `#1a3a2a` (darker)
   - `.sb-map`: Set to `#052615` with `font-weight: 900` for better readability
   - `.sb-date`: Set to `#315948` with proper spacing
   - `.sb-id`: Set to `#1a3a2a` with monospace font and word-break

2. **Hover box fix**:
   - Removed `text-shadow` from hover rule (was creating the "box" effect)
   - Reduced hover `background` opacity from `0.32` to `0.25` for subtler effect

### Files changed

- `themes/Pacific Paradise.css`: Updated text colors and hover styling

### Smoke tests

- All 130+ smoke tests passed after the changes.
- Theme renders correctly with improved text readability.

## 2026-05-06 Move inline styles to style.css#

### Problem

Settings & Help pages in `bo3tracker.py` had hardcoded inline styles like `style="color:#fff"` and `style="color:#aaa"` that:
1. Couldn't be overridden by theme CSS (inline styles have highest specificity)
2. Showed up as white/invisible text on light themes (Pacific Paradise)

### Fix

1. **Added default styles to `style.css`** targeting Settings/Help page elements:
   - `#tab-settings .card-title`, `#tab-help .card-title` - card titles
   - `#tab-settings div[style*="font-weight:bold"]` - bold text sections
   - `#tab-settings p`, `#tab-help p` - paragraph text
   - `#tab-help details`, `details summary`, `details p` - troubleshooting sections
   - `#tab-help ul`, `#tab-help li` - feature lists

2. **Removed inline styles from `bo3tracker.py`**:
   - Removed `style="color:#fff; font-weight:bold;"` (replaced with just `font-weight:bold;`)
   - Removed `style="color:#aaa;..."` (replaced with just `font-size:0.8em;...`)
   - Removed `style="color:#777;..."` (replaced with just `font-size:0.75em;...`)
   - Removed `style="color:#ccc;..."` from paragraphs
   - Removed `style="color:var(--highlight);..."` from headings (now handled by CSS)

3. **Updated `Pacific Paradise.css`** to override these new default styles with theme-appropriate colors.

### Files changed

- `style.css`: Added ~80 lines of Settings/Help page default styles
- `bo3tracker.py`: Removed ~40 inline style attributes from Settings/Help HTML
- `themes/Pacific Paradise.css`: Updated to properly style Settings/Help pages

### Smoke tests

- All 130+ smoke tests passed after the changes.
- Inline styles removed; all styling now controlled by CSS files.

## Summary of all changes made (2026-05-06)

### 1. CSS Cascade Fix (bo3tracker.py)
- Swapped order so `style.css` loads BEFORE `#theme-injector`
- Theme CSS now correctly overrides defaults due to source order

### 2. Moved Default CSS from bo3tracker.py to style.css
- Moved ~60 lines: toggle switches, challenge UI, player card selector, privacy modal, update notice, `.perk-item`, `.app-version-label`
- Removed ~60 lines from `bo3tracker.py`, kept only theme-specific rules

### 3. Removed Dead Theme CSS from bo3tracker.py
- Deleted `body.theme-void` and `body.theme-pacific-paradise` CSS rules (never used)
- These were dead code - no JS applies those classes to `<body>`

### 4. Pacific Paradise Theme Readability & Hover Fixes
- Improved text colors for better contrast (`.stat-big`, `.sb-map`, `.sb-date`, `.sb-id`, etc.)
- Fixed "weird box" on hover by removing `text-shadow` from hover rule
- Reduced hover background opacity for subtler effect

### 5. Settings/Help Page Inline Style Removal
- Removed ~40 inline style attributes from `bo3tracker.py` Settings/Help pages
- Added ~80 lines of default styles to `style.css` for Settings/Help pages
- Pacific Paradise CSS updated to properly override defaults with theme colors

### Files Changed
- `bo3tracker.py`: CSS order swap, removed default CSS (~60 lines), removed dead theme CSS (~30 lines), removed inline styles (~40 attributes)
- `style.css`: Added default styles (~80 lines) for Settings/Help pages
- `themes/Pacific Paradise.css`: Updated text colors, hover styling, Settings page overrides

### All Smoke Tests Passed
- After each change, all 130+ smoke tests passed
- No regressions detected in any theme or page

## 2026-05-07 Main script split and runtime config folder

### Problem

`bo3tracker.py` had grown large and the app root was being cluttered by runtime JSON/cache files created while the tracker runs.

### Changes

1. **Moved the main dashboard HTML renderer out of `bo3tracker.py`**
   - Added `ui_main.py`.
   - Moved the large `get_main_app_html()` HTML/JS body into `build_main_app_html(...)`.
   - Kept a small `get_main_app_html()` wrapper in `bo3tracker.py` so existing call sites continue to work.
   - Added `ui_main.py` to `runner.py` release source copy list.

2. **Fixed Unicode display corruption after the HTML split**
   - Restored the graph button icons: `📊 XPM` and `📈 ROUND XP`.
   - Restored challenge/reward/star symbols: `🏆`, `⭐`, `📇`, and `★`.
   - Restored the live modifier warning symbol: `⚠ ACTIVE MODIFIERS`.

3. **Moved setup screen HTML out of `bo3tracker.py`**
   - Added `ui_views.py`.
   - Moved setup page HTML into `build_setup_html(...)`.
   - Kept a small `get_setup_html()` wrapper in `bo3tracker.py`.
   - Added `ui_views.py` to `runner.py` release source copy list.

4. **Added a runtime config folder with compatibility migration**
   - Added `app_paths.py` for shared app paths and runtime-file migration.
   - Runtime files now live under `config/` instead of the app root:
     - `config.json`
     - `best_matches.json`
     - `challenges.json`
     - `unlocked_rewards.json`
     - `damage_history.json`
     - `damage_log.json`
     - `favorites.json`
     - `global_stats_state.json`
     - `match_xp_cache.json`
     - `points_history.json`
     - `xpm_graph_memory.json`
     - `workshop_image_cache/`
   - Migration is conservative: old root files are moved only when the matching `config/` destination does not already exist.
   - Updated runtime writers/readers in `bo3tracker.py`, `challenge_system.py`, `match_xp.py`, `xpm_grapher.py`, and `workshop_images.py`.
   - Added `app_paths.py` to `runner.py` release source copy list.

### Files changed

- `app_paths.py`: New shared path and migration helper.
- `bo3tracker.py`: Smaller UI wrappers and config-folder runtime paths.
- `ui_main.py`: Main dashboard HTML renderer.
- `ui_views.py`: Setup screen HTML renderer.
- `challenge_system.py`: Challenges/unlocks now use `config/`.
- `match_xp.py`: Match XP cache now uses `config/`.
- `xpm_grapher.py`: XPM graph memory now uses `config/`.
- `workshop_images.py`: Workshop image cache now uses `config/`.
- `runner.py`: Release source copy list includes new modules.

### Verification

- `python -m py_compile app_paths.py bo3tracker.py challenge_system.py match_xp.py xpm_grapher.py workshop_images.py ui_main.py ui_views.py runner.py`
- Dashboard HTML smoke test after `ui_main.py` split.
- Setup HTML smoke test after `ui_views.py` split.
- Config migration dry run showed no destination conflicts.
- Existing runtime files were moved into `config/`.
- Direct module checks confirmed XP cache, graph memory, workshop cache, challenges, and unlocks resolve to `config/`.
- Full `bo3tracker` import could not be completed in the bundled Python runtime because `pywebview` is not installed there.

## 2026-05-07 Version 3.4 metadata and changelog

### Problem

Version metadata was split across multiple scripts, which made each release bump easy to miss.

### Changes

- Added `app_version.json` as the single editable version metadata file.
- Added `app_metadata.py` to load:
  - `version`
  - `global_stats_prompt_version`
- Updated `bo3tracker.py` to import `APP_VERSION` and `GLOBAL_STATS_PROMPT_VERSION` from shared metadata.
- Updated `global_stats_client.py` to import `APP_VERSION` from shared metadata.
- Updated the global stats upload `User-Agent` to use the shared app version.
- Updated `runner.py` to read the release zip version from `app_version.json`.
- Updated `runner.py` to include `app_version.json` and `app_metadata.py` in release output/source copies.
- Added `CHANGELOG_3.4.md` with release-ready notes for BO3 Tracker 3.4.

### Version bump

- App version: `3.4`
- Global stats prompt version: `3.4`

### Verification

- Searched for stale hardcoded `APP_VERSION = "3.3"` and `GLOBAL_STATS_PROMPT_VERSION = "3.3"` assignments.
- Confirmed `runner.py` reads `3.4` from `app_version.json`.
- Python compile checks passed for touched modules.

## 2026-05-07 Restore updater script for release builds

### Problem

`updater.py` had been moved into `manual_review_not_active_app/cleanup_2026-05-07/` during directory cleanup, but `runner.py` still requires it to build `BO3Updater.exe`.

### Fix

- Restored `updater.py` to the project root from the manual review folder.
- Updated `updater.py` to import `APP_VERSION` from `app_metadata.py`.
- Updated the updater download `User-Agent` to use the shared app version.
- Added `app_version.json` to updater-managed release files.
- Added `config/` to updater preserved paths so user runtime config/state survives updates in the new folder layout.

### Verification

- Confirmed `runner.py` can find `updater.py`.
- Python compile check passed for `updater.py`.

## 2026-05-07 Fix packaged build level XP requirement lookup

### Problem

The packaged build showed current rank XP as `6,641,590 / 0 XP`, causing the current level progress bar to display `0%`, while the dev folder showed the correct `6,641,590 / 6,914,200 XP`.

### Cause

`match_xp.py` loaded `xp_requirements.csv` from `os.path.dirname(__file__)`. That works in the dev folder, but in a PyInstaller one-file build `__file__` can point inside the temporary bundled runtime instead of the install folder where `xp_requirements.csv` is copied.

### Fix

- Updated `match_xp.py` to load `xp_requirements.csv` from `app_paths.get_base_path()`.
- This makes dev mode and frozen `.exe` mode resolve the CSV from the correct app/install folder.

### Verification

- Confirmed level 362 now resolves to `6,914,200` XP from `xp_requirements.csv`.
- Python compile check passed for `match_xp.py`.
- Rebuilt the 3.4 release with `python runner.py`.
- Fresh `Release_Build` and `BO3Tracker-3.4.zip` were created successfully.

## 2026-05-07 Add Clouds theme

### Request

User provided a cloud image and asked for a cloud theme with a matching overlay theme, plus image enhancement if possible.

### Changes

- Enhanced the provided cloud image with the image generation/editing workflow.
- Copied the enhanced image into `themes/clouds_enhanced_background.png`.
- Added `themes/Clouds.css`.
- Added `Clouds` to `ALWAYS_AVAILABLE_THEMES`.
- Added a matching `Clouds` live overlay palette in `OVERLAY_THEMES`.
- Added `Clouds` graph colors in `ui_main.py`.
- Added `Clouds` Settings/Help copy in `ui_main.py`.
- Updated `CHANGELOG_3.4.md`.

### Verification

- Python compile check passed for `bo3tracker.py` and `ui_main.py`.
- Confirmed `Clouds` appears in available themes.
- Confirmed `Clouds` theme CSS loads and inlines the cloud background.
- Confirmed the Cloud overlay palette exists.
- Confirmed Cloud-specific UI copy appears in the rendered dashboard HTML.

## 2026-05-07 Start version 3.5 and extract XP debugger view

### Request

User asked to continue refactoring the main script without rebuilding yet, and to make the Cloud theme plus this refactor part of a 3.5 update.

### Changes

- Updated `app_version.json` to version `3.5`.
- Updated `global_stats_prompt_version` to `3.5`.
- Moved XP debugger HTML from `bo3tracker.py` into `ui_views.py` as `build_xp_debugger_html()`.
- Kept `get_xp_debugger_html()` in `bo3tracker.py` as a wrapper.
- Left XP debugger runtime/window logic in `bo3tracker.py`.
- Added `CHANGELOG_3.5.md`.
- Removed Cloud-theme bullets from `CHANGELOG_3.4.md` so Cloud is tracked under 3.5.
- Added `CHANGELOG_3.5.md` to `runner.py` release source copy list.

### Verification

- Python compile checks passed for touched modules.
- Confirmed app metadata reads version `3.5`.
- Confirmed XP debugger HTML is rendered from `ui_views.py` and includes the `updateXpDebug(...)` JavaScript hook.
- No release rebuild was run, per user request.

## 2026-05-07 Extract unified overlay view

### Request

User asked to move the next safe section from `bo3tracker.py`, check that nothing breaks, and update changelogs.

### Changes

- Moved unified overlay HTML from `bo3tracker.py` into `ui_views.py` as `build_unified_overlay_html(initial_theme_json)`.
- Kept `get_unified_overlay_html()` in `bo3tracker.py` as a wrapper.
- Left overlay runtime behavior in `bo3tracker.py`, including:
  - `overlay_loop()`
  - `toggle_overlays_logic(...)`
  - `push_overlay_theme()`
  - overlay window globals and live update calls
- Updated `CHANGELOG_3.5.md`.

### Verification

- Python compile checks passed for `bo3tracker.py` and `ui_views.py`.
- Confirmed `build_unified_overlay_html(...)` includes `INITIAL_OVERLAY_THEME`, `applyOverlayTheme(...)`, and `updateOverlay(...)`.
- Confirmed `bo3tracker.get_unified_overlay_html()` injects the active Cloud overlay theme JSON.
- No release rebuild was run.

## 2026-05-07 Extract asset helpers

### Request

User asked to move the next recommended helper section out of `bo3tracker.py`.

### Changes

- Added `asset_helpers.py`.
- Moved these helpers out of `bo3tracker.py`:
  - `load_css(...)`
  - `inline_theme_asset_urls(...)`
  - `sanitize_filename(...)`
  - `get_base64_icon(...)`
  - `get_rank_icon_base64(...)`
  - `get_tier_icon_src(...)`
  - `get_prestige_icon_src(...)`
  - `get_level_icon_src(...)`
  - `get_camo_image_src(...)`
  - `get_calling_card_src(...)`
- Removed helper-only imports/constants from `bo3tracker.py`.
- Added `asset_helpers.py` to `runner.py` release source copy list.
- Updated `CHANGELOG_3.5.md`.

### Verification

- Python compile checks passed for `bo3tracker.py`, `asset_helpers.py`, and `runner.py`.
- Confirmed CSS loading still works.
- Confirmed theme asset URL inlining still works for the Cloud background.
- Confirmed perk icon, rank icon, camo image, calling card, and filename sanitizing helpers work from `asset_helpers.py`.
- Confirmed `bo3tracker.py` can still access the imported helpers and Cloud theme content.
- No release rebuild was run.

## 2026-05-07 Extract best-match helpers

### Request

User asked to make the next first move carefully and check that nothing major changed first.

### Changes

- Added `best_matches.py`.
- Moved best-match summary parsing and best-match JSON load/save helpers out of `bo3tracker.py`.
- Kept the app behavior pointed at `config/best_matches.json` through `app_paths.get_runtime_path(...)`.
- Added `best_matches.py` to the `runner.py` release source copy list.
- Updated `CHANGELOG_3.5.md`.

### Verification

- Python compile checks passed for `bo3tracker.py`, `best_matches.py`, and `runner.py`.
- Confirmed best-match summary parsing returns the same expected structure.
- Confirmed best-match loading returns a list and resolves to the config-folder path.
- Confirmed `bo3tracker.py` still imports and exposes the best-match helpers used by the API methods.
- No release rebuild was run.

## 2026-05-07 Extract file I/O, version utilities, and damage memory

### Request

User asked to continue safe refactoring of `bo3tracker.py` as part of version 3.5, extracting self-contained utility functions with no app-state dependencies.

### Changes

- Created backup of the full project to `I:\camo_tracker_backup_20260507-201600\`.
- Added `file_utils.py` containing shared `load_json()` and `save_json()` file I/O helpers.
- Added `version_utils.py` containing `parse_version_parts()`, `is_version_newer()`, `extract_updater_from_release()`, and `get_updater_launch_path()`.
- Added `damage_memory.py` containing the `DamageMemory` class for 32-bit integer overflow tracking.
- Updated `global_stats_client.py` to import `load_json`/`save_json` from `file_utils.py`, removing duplicated implementations.
- Removed all extracted code from `bo3tracker.py` (~110 lines) and replaced with imports.
- Added all three new files to `runner.py` release source copy list.

### Verification

- Python compile checks passed for all 6 touched modules: `file_utils.py`, `version_utils.py`, `damage_memory.py`, `bo3tracker.py`, `global_stats_client.py`, `runner.py`.
- No release rebuild was run.

## 2026-05-07 Extract stats processor

### Request

User asked to continue safe refactoring of `bo3tracker.py`, extracting `process_stats()` as the next self-contained block.

### Changes

- Created backup of the full project to `I:\camo_tracker_backup_20260507-203041\`.
- Added `stats_processor.py` containing the `process_stats()` multi-player data processor and the `damage_tracker` singleton.
- Removed `process_stats()` (~195 lines) and `damage_tracker = DamageMemory()` from `bo3tracker.py`, replaced with a single import line.
- Added `stats_processor.py` to `runner.py` release source copy list.

### Verification

- Python compile checks passed for `stats_processor.py`, `bo3tracker.py`, and `runner.py`.
- `process_stats()` accesses `damage_tracker`, `xp_tracker_instance`, and `xpm_grapher_instance` by direct import — no circular dependencies.
- No release rebuild was run.

## 2026-05-07 Extract game data constants and overlay themes

### Request

User asked to extract more pure data from `bo3tracker.py` to continue reducing its size as part of version 3.5, with backup first and careful compile verification.

### Changes

- Created backup of the full project to `I:\camo_tracker_backup_20260507-191817\`.
- Added `overlay_themes.py` containing the `OVERLAY_THEMES` colour palette dict.
- Added `game_data.py` containing `PERK_NAMES`, `CAMO_NAMES`, `IGNORE_KEYWORDS`, and 10 app/game path/API constants (`GITHUB_RELEASES_API`, `UPDATER_EXE_NAME`, `CONFIG_FILE`, `DAMAGE_HISTORY_FILE`, `GLOBAL_STATS_STATE_FILE`, `CAMO_DB_FILE`, `CSS_MAIN_FILE`, `CSS_SETUP_FILE`, `THEMES_DIR`, `ALWAYS_AVAILABLE_THEMES`).
- Removed ~120 lines of pure data from `bo3tracker.py` (lines 38–158) and replaced with imports from the two new modules.
- Added both new files to `runner.py` release source copy list.

### Verification

- Python compile checks passed for `game_data.py`, `overlay_themes.py`, `bo3tracker.py`, and `runner.py`.
- Confirmed all originally available names (`OVERLAY_THEMES`, `PERK_NAMES`, `CAMO_NAMES`, `IGNORE_KEYWORDS`, `GITHUB_RELEASES_API`, etc.) are still resolvable by remaining `bo3tracker.py` code via the new imports.
- No release rebuild was run.

## 2026-05-07 Help changelog version import fix

Time: 22:11:20 +01:00 Europe/London.

### Request

User reported a Help & FAQ traceback when the GitHub patch notes panel loaded.

### Cause

`parse_version_parts()` had been moved into `version_utils.py` during the version utility refactor, but `bo3tracker.py` still called it inside `TrackerAPI.get_latest_changelog()` without importing it.

### Fix

- Updated `bo3tracker.py` to import `parse_version_parts` from `version_utils.py`.
- Updated `CHANGELOG_3.5.md` with the Help & FAQ changelog fix.

### Verification

- Python compile checks passed for `bo3tracker.py` and `version_utils.py`.
- Direct `TrackerAPI().get_latest_changelog()` call no longer raises `NameError`.
- The GitHub request can still fail separately on this machine with the Python SSL certificate verification error.
- Rebuilt the 3.5 release with `python runner.py`.
- Fresh `Release_Build` and `BO3Tracker-3.5.zip` were created successfully.
- Verified the release copy of `scripts/bo3tracker.py` includes the `parse_version_parts` import.
- Verified `BO3Tracker-3.5.zip` includes `BO3Tracker.exe`, `BO3Updater.exe`, `scripts/bo3tracker.py`, `scripts/DEV_LOG.md`, and `scripts/CHANGELOG_3.5.md`.

## 2026-05-07 Dog Pack theme

Time: 22:48:03 +01:00 Europe/London.

### Request

User provided three dog photos and asked for a theme that uses them while keeping the dogs visible.

### Changes

- Created `themes/dog_pack_background.jpg`, an edited collage background made from the supplied dog photos.
- Added `themes/Dog Pack.css` with warm sofa/photo styling, translucent panels, readable text, and responsive mobile fallback opacity.
- Added `Dog Pack` to `ALWAYS_AVAILABLE_THEMES`.
- Added `Dog Pack` graph colors in `ui_main.py`.
- Added `Dog Pack` Settings/Help copy in `ui_main.py`.
- Added a matching `Dog Pack` live overlay palette in `overlay_themes.py`.
- Updated `CHANGELOG_3.5.md`.

### Verification

- Python compile checks passed for `game_data.py`, `overlay_themes.py`, `ui_main.py`, `bo3tracker.py`, and `runner.py`.
- Confirmed `Dog Pack` appears in `TrackerAPI().get_available_themes()`.
- Confirmed `TrackerAPI().get_theme_content("Dog Pack")` inlines `dog_pack_background.jpg` as a data image.
- Confirmed the edited dog background asset exists in `themes/`.

## 2026-05-07 Start version 3.6 changelog

Time: 22:52:06 +01:00 Europe/London.

### Request

User asked to track the Dog Pack theme changes in a new 3.6 changelog instead of the 3.5 changelog, and to update the dev log.

### Changes

- Added `CHANGELOG_3.6.md` for the Dog Pack theme release notes.
- Removed Dog Pack release bullets from `CHANGELOG_3.5.md`, leaving 3.5 focused on Clouds, refactors, and the Help & FAQ changelog fix.
- Updated `app_version.json` from `3.5` to `3.6`.
- Updated `global_stats_prompt_version` from `3.5` to `3.6`.
- Added `CHANGELOG_3.6.md` to the `runner.py` release source copy list.

### Verification

- Python compile checks passed for `app_metadata.py`, `game_data.py`, `overlay_themes.py`, `ui_main.py`, `bo3tracker.py`, and `runner.py`.
- Confirmed app metadata reads version `3.6` and global stats prompt version `3.6`.
- Confirmed `Dog Pack` still appears in `TrackerAPI().get_available_themes()`.
- Confirmed `TrackerAPI().get_theme_content("Dog Pack")` still inlines the edited dog background.
- Confirmed Dog Pack Settings copy, graph palette, and overlay palette are still present.

## 2026-05-08 Extract camo processor and restore smoke tests

Time: 23:29:28 +01:00 Europe/London.

### Request

User asked to start with the lowest-risk extraction, update all smoke tests, and make a versioned timestamped backup on `I:\` before editing.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260508-232813\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added `camo_processor.py`.
- Moved Camo Matrix data processing out of `bo3tracker.py`.
- Kept `bo3tracker.process_camo_data(...)` as a compatibility wrapper that passes `app_config["starred"]` into the extracted processor.
- Added `camo_processor.py` to `runner.py` release source copy list.
- Restored active root `run_smoke_tests.py` with current-project checks for syntax, assets, version metadata, camo extraction, theme contracts, and runner packaging.
- Updated `CHANGELOG_3.6.md`.

### Verification

- Python compile checks passed for `bo3tracker.py`, `camo_processor.py`, `runner.py`, and `run_smoke_tests.py`.
- `python run_smoke_tests.py` passed.
- Direct `camo_processor.process_camo_data(None, ["1"])` check returned 341 weapons, map data, and 21 camo icons without an error.

## 2026-05-09 Shi No Numa inspired theme

Time: 02:03:43 +01:00 Europe/London.

### Request

User asked for a Shi No Numa zombies inspired theme with a background image.

### Changes

- Generated an original misty swamp outpost background image.
- Copied the generated image to `themes/shi_no_numa_swamp_background.png`.
- Added `themes/Shi No Numa.css`.
- Added `Shi No Numa` to `ALWAYS_AVAILABLE_THEMES`.
- Added matching graph colors in `ui_main.py`.
- Added matching Settings copy in `ui_main.py`.
- Added a matching live overlay palette in `overlay_themes.py`.
- Updated `CHANGELOG_3.6.md`.
- Updated smoke-test theme contracts for the new theme.

### Verification

- Python compile checks passed for `bo3tracker.py`, `game_data.py`, `overlay_themes.py`, `ui_main.py`, and `run_smoke_tests.py`.
- `python run_smoke_tests.py` passed.
- Confirmed `Shi No Numa` appears in `ALWAYS_AVAILABLE_THEMES`.
- Confirmed the `Shi No Numa` overlay palette exists.
- Confirmed `themes/Shi No Numa.css` references `shi_no_numa_swamp_background.png`.
- Confirmed theme asset inlining converts the background reference to a base64 data image.

## 2026-05-09 Extract player stats backup helper

Time: 03:37:39 +01:00 Europe/London.

### Request

User asked to move the manual UEM stats backup logic next and make a backup first.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-033739\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added `player_stats_backup.py`.
- Moved stats file discovery, `.zip` path normalization, and zip creation out of `bo3tracker.py`.
- Kept the pywebview save dialog and API response formatting in `TrackerAPI.backup_player_stats(...)`.
- Added `player_stats_backup.py` to `runner.py` release source copy list.
- Updated smoke tests to cover the new helper and delegation contract.
- Updated `CHANGELOG_3.6.md`.

### Verification

- Python compile checks passed for `bo3tracker.py`, `player_stats_backup.py`, `runner.py`, and `run_smoke_tests.py`.
- `python run_smoke_tests.py` passed.
- Direct helper check with a temporary fake `players` folder found 2 `stats_zm_*.cgp` files and created a `.zip` containing `stats_zm_0.cgp` and `stats_zm_2.cgp`.

## 2026-05-09 Extract Best Matches workflow helpers

Time: 03:46:08 +01:00 Europe/London.

### Request

User asked to proceed with Best Matches refactor after the health check, and to update the dev log and changelog.

### Backup

- Used existing pre-change backup from this work session: `I:\camo_tracker_backup_v3.6_20260509-034407\`.

### Changes

- Expanded `best_matches.py` with:
  - `sanitize_game_id(...)`
  - `find_archive_data(...)`
  - `add_best_match_from_data(...)`
  - `get_best_matches_with_archive_status(...)`
  - `remove_best_match_by_id(...)`
- Simplified `TrackerAPI.add_current_best_match(...)`, `TrackerAPI.get_best_matches(...)`, and `TrackerAPI.remove_best_match(...)` into thin wrappers.
- Added internal game ID sanitizing in the Best Matches helper layer.
- Updated smoke tests for the Best Matches delegation contract.
- Updated `CHANGELOG_3.6.md`.

### Verification

- Python compile checks passed for all root `.py` files.
- `python run_smoke_tests.py` passed.
- Direct Best Matches helper check with temporary config/history data confirmed sanitized IDs, archive lookup, add, refreshed listing with `exists=True`, match XP summary, and remove behavior.

## 2026-05-09 Best Matches archive ID sanitizer fix

Time: 03:46:08 +01:00 Europe/London.

### Issue

User reported Best Matches could not find an archived match for an ID like `x875789abdd43c25a3_155a_608ecbe3`.

### Cause

The extracted `best_matches.sanitize_game_id(...)` removed `:` characters, while the existing archive writer replaces `:` with `_`. For raw UEM IDs such as `x87:57889abdd43c25a3_155a_608ecbe3`, the helper looked for `Game_x8757889...json` instead of the real `Game_x87_57889...json`.

### Fix

- Updated `best_matches.sanitize_game_id(...)` to match the original archive filename behavior for `:`, `|`, `/`, and `\`.
- Added smoke-test coverage for colon-to-underscore game ID sanitizing.
- Updated `CHANGELOG_3.6.md`.

### Verification

- Python compile checks passed for all root `.py` files.
- `python run_smoke_tests.py` passed.
- Direct lookup against `H:\finished games history` confirmed raw ID `x87:57889abdd43c25a3_155a_608ecbe3` maps to archive filename ID `x87_57889abdd43c25a3_155a_608ecbe3`.
- Confirmed the matching archive loads and summarizes as map `International`, round `6`.

## 2026-05-09 Management tools GUI

Time: 15:24:11 +01:00 Europe/London.

### Request

User asked for a separate GUI management tool, with backup first, and changelog/dev-log notes saying the app now has management tools.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-152411\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added separate `dev_tools/` management tool area.
- Added `dev_tools/admin_gui.py`, a Tkinter GUI with tabs for:
  - Global Stats control JSON
  - Challenge manifest editing
  - Validation and smoke-test checks
- Added `dev_tools/modules/global_stats_control.py`.
- Added `dev_tools/modules/challenge_manifest.py`.
- Added `dev_tools/modules/validation.py`.
- Added `dev_tools/README.md`.
- Added a low-risk live tracker hook that reads `dev_tools/management_outputs/global_stats_control.json` and blocks anonymous global stats sync when management tools set `global_stats_enabled` to `false`.
- Updated smoke tests to include management-tool syntax and contract checks.
- Updated `.gitignore` for local management-tool state.
- Updated `CHANGELOG_3.6.md`.

### Verification

- Python compile checks passed for all root `.py` files and `dev_tools/**/*.py`.
- `python run_smoke_tests.py` passed.
- Direct management-helper behavior check passed for:
  - Saving/loading the Global Stats control JSON.
  - Saving/loading a challenge manifest.
  - Validating a minimal exported challenge manifest.

## 2026-05-09 Management challenge browser

Time: 15:36:39 +01:00 Europe/London.

### Request

User asked whether the management GUI could show the current challenges for each section and make it easier to apply changes so it is clear what needs editing.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-153504\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added `dev_tools/modules/challenge_catalog.py` to read current tracker challenges without launching the tracker.
- Updated `dev_tools/admin_gui.py` with a current-challenge browser grouped by section.
- Added buttons to:
  - Use a selected current challenge as an editor template.
  - Add a copy of a selected current challenge to the remote manifest draft.
  - Compare the editor fields against the selected current challenge.
- Changed challenge category, stat, type, and reward type fields into comboboxes so valid values are easier to apply.
- Updated `dev_tools/README.md`.
- Updated smoke tests for the challenge browser management contract.
- Updated `CHANGELOG_3.6.md`.

### Verification

- `python run_smoke_tests.py` passed.
- In-memory compile check passed for all root `.py` files and `dev_tools/**/*.py`.
- Direct challenge catalog behavior check passed with 70 current challenges loaded from `config/challenges.json`.
- `dev_tools/admin_gui.py` imports successfully without launching the GUI.
- Note: a direct `python -m py_compile` run hit a Windows `__pycache__` access-denied rename, so final syntax verification used in-memory compilation to avoid writing `.pyc` files.

## 2026-05-09 Weekly challenge management

Time: 15:43:32 +01:00 Europe/London.

### Request

User asked if weekly challenges can be set in the management GUI and noted that the Operations page is currently empty.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-154224\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Notes

- `operations` is the bucket for extra non-lifetime challenge rows, such as auto-generated calling-card unlocks or limited-time operation rows.
- It can appear empty when there are no generated/manual `cat: "operations"` challenges in `config/challenges.json`.

### Changes

- Preserved `daily` and `weekly` challenge categories during challenge loading instead of stripping them.
- Added a Weekly filter button to the app Challenges page.
- Added `blank_weekly_challenge(...)` to the management manifest helpers.
- Added a `New Weekly` button to the management GUI.
- Added `weekly` and `daily` options to the category combobox.
- Added category validation in the management validator.
- Updated smoke-test contracts.
- Updated `dev_tools/README.md`.
- Updated `CHANGELOG_3.6.md`.

### Verification

- `python run_smoke_tests.py` passed.
- In-memory compile check passed for all root `.py` files and `dev_tools/**/*.py`.
- Direct weekly challenge helper check passed for template creation and manifest validation.

## 2026-05-09 Bulk challenge hardening tools

Time: 15:49:05 +01:00 Europe/London.

### Request

User needs to make challenges harder across the board.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-154801\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added `dev_tools/modules/challenge_difficulty.py`.
- Added management GUI controls for:
  - Loading current tracker challenges into the manifest draft.
  - Choosing a target multiplier.
  - Choosing categories to scale.
  - Previewing harder target changes.
  - Applying the preview to the manifest draft.
- Updated smoke-test contracts for the hardening helper and GUI controls.
- Updated `dev_tools/README.md`.
- Updated `CHANGELOG_3.6.md`.

### Verification

- `python run_smoke_tests.py` passed.
- In-memory compile check passed for all root `.py` files and `dev_tools/**/*.py`.
- Direct difficulty-helper behavior check passed for category-scoped target scaling and preview output.
- `dev_tools/admin_gui.py` imports successfully without launching the GUI.

## 2026-05-09 Remote management baseline

Time: 16:00:58 +01:00 Europe/London.

### Request

User asked to try the remote management approach so 3.6 clients can receive management changes without another client update.

### Backup

- Created backup at `I:\camo_tracker_backup_v3.6_20260509-155313\`.
- Excluded generated `__pycache__`, `build`, `dist`, and `*.pyc` files from the backup copy.

### Changes

- Added `remote_management_client.py` with:
  - Remote JSON fetch.
  - Cached fallback.
  - Schema normalization.
- Added `remote_management_url` to `app_version.json`.
- Added `REMOTE_MANAGEMENT_URL` to `app_metadata.py`.
- Added `remote_management_cache.json` to managed runtime paths.
- Added remote-management startup refresh/apply in `bo3tracker.py`.
- Added `TrackerAPI.refresh_remote_management_api(...)` for manual refresh/testing from the UI layer later.
- Added remote global-stats shutoff support.
- Added remote challenge manifest apply support in `ChallengeManager.apply_remote_manifest(...)`, preserving progress/completed state by matching challenge ID.
- Added `dev_tools/modules/remote_management_manifest.py`.
- Added `Save Remote Config` in the management GUI to export `dev_tools/management_outputs/remote_management.json`.
- Updated smoke tests.
- Updated `dev_tools/README.md`.
- Updated `CHANGELOG_3.6.md`.

### Verification

- `python run_smoke_tests.py` passed.
- In-memory compile check passed for all root `.py` files and `dev_tools/**/*.py`.
- Direct remote-management client check passed for:
  - Fetching a remote JSON file.
  - Writing the cache.
  - Falling back to the cached copy when the remote URL fails.
- Direct remote-management export check passed for `remote_management.json`.
- Direct remote challenge apply check passed and confirmed progress is preserved for matching challenge IDs.

## 2026-05-09 XP challenge tracking

Time: 20:50:00 +01:00 Europe/London.

### Request

User wanted weekly challenges that track XP earned in a single match, with realistic target ranges for high-XP play.

### Changes

- Added **XP Hunter** weekly challenge template to `WEEKLY_TEMPLATES` with `stat: xp`, `type: single_game`, target range 5,000,000–100,000,000.
- Removed `xp` from `REWARD_POOL` and `ALLOWED_REWARD_TYPES` — XP is a stat only, not a reward type.
- Added `"xp": int(p.get('match_xp_earned', 0))` to all three stats dicts in `challenge_system.py` (`_apply_game_stats`, `apply_live_update`, `reset_all_challenges`).
- Added XP offset subtraction in `_apply_game_stats` and `reset_all_challenges` so mid-game resets don't double-count XP.
- Moved `calculate_match_xp` call **before** `apply_live_update` in `bo3tracker.py` so `match_xp_earned` is populated when challenges update.
- Updated `_apply_stats_to_challenges` to accept an optional `full_stats` parameter. Single-game challenges now use the full match value (not incremental delta) during live tracking, so XP is compared against the correct single-match total.
- Added **Remove** button to the current challenges list in the admin GUI.
- Updated `CHANGELOG_3.7.md`.

### Verification

- Week challenge generation tested: XP Hunter appears with valid targets and XP-free rewards (100 iterations passed).
- End-to-end tests passed for:
  - Live XP tracking via `apply_live_update` (incremental updates during match correctly accumulate).
  - XP offset subtraction in `_apply_game_stats` (net = match XP − offset).
  - XP offset snapshot in `reset_all_challenges`.
  - Force sync via `process_update` (backlogged games accumulate XP correctly).
- All 4 test scenarios passed.

## 2026-05-09

### Diamond theme

- Created `themes/diamond.css` — a diamond/crystal inspired theme with deep navy base, cyan/lavender accents, faceted grid overlays, sparkle animations, and custom diamond cursor. References `diamond_background.jpg`.
- Added `"diamond"` overlay colour palette to `overlay_themes.py` for the overlay stats display.
- Cleaned up 9 redundant `.png` files from `themes/` that had matching `.jpg` counterparts already used by CSS.
-
- ### Remote challenge removal
-
- - Added `"remove": true` support to the challenge manifest system. Challenges flagged with `remove: true` in the remote manifest are deleted from users' local `challenges.json` when the app fetches the next remote management update.
- - `challenge_system.py` `apply_remote_manifest()` now strips removed challenges before merging remaining entries.
- - Added `_save_challenges()` helper to `ChallengeManager` to DRY up file saving.
- - `challenge_manifest.py` — added `remove` to `CHALLENGE_FIELDS`, `blank_challenge()`, and `normalise_challenge()`.
- - `admin_gui.py` — added "Remove from users" checkbox to the manifest challenge editor, populated from the `remove` field on selection. Manifest list now shows `[REMOVE]` prefix for removal entries.
- - `validation.py` — `validate_manifest()` skips strict field checks for removal-only entries (only need an id).
- - `bo3tracker.py` — no changes needed; the existing `apply_remote_management()` call path automatically processes removal entries on next fetch.
-
- ### Verification
-
- - All smoke tests pass (181 tests).
- - All root `.py` files and `dev_tools/**/*.py` pass compile check.
- - 3 functional tests passed:
-   - Manifest with removal + new challenges: old weekly removed, other challenges preserved, new challenges added.
-   - Manifest with only removal entries: all matching challenges removed, empty list saved correctly.
-   - Normal replace without remove flag: progress/completed state preserved as before.

## 2026-05-10 Theme unlock fix

### Problem

Theme unlock requirements were broken. check_theme_unlocks() could never find matching completed challenges for the original themes (void, 115_Origins, RedHex, Golden Divinium, retro, matrix) because _scan_and_create_theme_challenges() overwrote theme_requirements from the original challenge IDs (c_void_1/2/3) to auto-generated IDs (c_auto_th_void_1/2/3). Completing the original lifetime challenges (which say "Unlocks VOID Theme" in their descriptions) did nothing for theme unlocking.

### Fix

Changed _scan_and_create_theme_challenges() to only add new theme_requirements entries for themes not already defined:
if theme_name not in self.theme_requirements

Now:
- Original themes unlock when their lifetime challenges are completed (matching their descriptions)
- New themes (auto-generated from CSS files) still unlock via their kill-based challenges

### Files changed

- challenge_system.py:199 — added if theme_name not in self.theme_requirements guard.

### Verification

- All 181 smoke tests pass.

## 2026-05-10 Help & FAQ and Settings global stats links

### Request

User asked to add info on the global stats board and recent matches to Help & FAQ with site links, and also add the links to the Settings page under the anonymous stats card.

### Changes

- Added a "GLOBAL STATS & RECENT MATCHES" card to the Help & FAQ page with links to:
  - Global Stats Board: `https://uemmaps.com/tracker/tracker.html`
  - Recent Matches: `https://uemmaps.com/tracker/recentmatches.html`
  - Camo Upload: `https://uemmaps.com/`
- Added the same two links (stats board, recent matches) to the Settings page below the SYNC NOW button in the GLOBAL ANONYMOUS STATS card, separated by a `<br>` for spacing.

### Files changed

- `ui_main.py` — added Help & FAQ card and Settings links
- `style.css` — added `.settings-links` and `.help-content .card a` styles

### Verification

- All 181 smoke tests pass.

## 2026-05-10 Cartoon graffiti theme — camo matrix theming

### Request

User noted the camo matrix page (weapon tables, camo cards, filters, progress bars) had no graffiti-themed styling — it was still using default dark colours.

### Changes

Added a full camo matrix / weapons page theme block to `themes/cartoon_graffiti_theme.css` covering:
- `.camo-card` — comic border, gradient fill, layered box shadow, hover lift with rotation
- `.controls` filter bar — pink accent border/shadow
- `input`/`select` inside controls — Comic Neue font, ink border, focus glow
- `.w-name` — Bangers font, cyan colour, ink text shadow
- `.w-type` — muted comic colour
- `.w-packed` — yellow with ink shadow
- `.camo-tray` / `.camo-option` — ink border, comic shadow, hover scale/rotate with pink glow, active highlight with cyan glow
- `.camo-display` / `.camo-text` — panel with inset shadow, yellow Bangers text with ink shadow
- `.camo-img-box` — ink border with pink shadow
- `.camo-label` — muted comic colour
- `.header-camo` / `h1` — yellow Bangers with ink shadow
- `.user-badge` — pink background, ink border, Bangers font
- `.game-tag` — ink background, comic font
- `table`, `th`, `td` — ink borders, Bangers headings, comic font body
- `.weapon-name-cell` — cyan with ink shadow
- `.weapon-status-pap` / `.weapon-status-std` — pink/bold and muted colours
- `.star-btn` — ink drop shadow
- `.progress-bar` — ink border, **animated multi-colour gradient fill** (`paintRoll` keyframe)

### Files changed

- `themes/cartoon_graffiti_theme.css` — added ~160 lines of camo matrix theming

### Verification

- All 181 smoke tests pass.

## 2026-05-10 Round XP bars not updating on theme switch

### Problem

Switching themes updated the round XP chart's `borderColor` but not `backgroundColor`. The `backgroundColor` was a Chart.js scriptable function that captured `theme.bar` in its closure at chart-creation time. When `applyGraphTheme()` ran, it called `roundXpChartInstance.update('none')` which re-evaluated the function, but the closure still returned the old theme's colour.

### Fix

Changed both `backgroundColor` and `borderColor` functions in `renderRoundXpChart()` (`ui_main.py:1392-1408`) to call `getGraphTheme()` dynamically instead of using the closed-over `theme` variable. Now Chart.js re-evaluates them with the current theme colours on every theme switch.

### Files changed

- `ui_main.py` — `backgroundColor` and `borderColor` functions in `renderRoundXpChart()`

### Verification

- All 181 smoke tests pass.

## 2026-05-10 Clouds theme custom cursors

### Changes

- Added a soft cloud cursor (white cloud with blue outline and sun ray) as the default `body` cursor.
- Added a sparkle/star cursor (gold star with cloud/sun accent) for interactive/hover elements: `button:hover`, `.config-btn:hover`, `.nav-btn:hover`, `.nav-btn.active`, `.nav-btn-small:hover`, `.chal-btn:hover`, `.sb-item:hover`, `.star-btn:hover`, `select:hover`, `input:hover`, `.perk-item:hover`, `.card:hover`, `.chal-card:hover`.

### Files changed

- `themes/Clouds.css` — added custom cursor SVG data URIs

## 2026-05-10 Shi No Numa theme custom cursors

### Changes

- Added a swamp-wood pointer cursor with toxic green glow as the default `body` cursor.
- Added a will-o'-wisp skull face cursor with green glow for interactive/hover elements: `button:hover`, `.config-btn:hover`, `.nav-btn:hover`, `.nav-btn.active`, `.nav-btn-small:hover`, `.chal-btn:hover`, `.sb-item:hover`, `.star-btn:hover`, `select:hover`, `input:hover`, `.card:hover`, `.chal-card:hover`, `.perk-item:hover`.

### Files changed

- `themes/Shi No Numa.css` — added custom cursor SVG data URIs

## 2026-05-10 Darkwood theme custom cursors

### Changes

- Added a dark oak wood pointer cursor (carved wood texture with grain lines and gold stud) as the default `body` cursor.
- Added a carved oak cursor with warm golden highlight for interactive/hover elements: `button:hover`, `.config-btn:hover`, `.nav-btn:hover`, `.nav-btn.active`, `.nav-btn-small:hover`, `.chal-btn:hover`, `.sb-item:hover`, `.star-btn:hover`, `select:hover`, `input:hover`, `.card:hover`, `.chal-card:hover`, `.perk-item:hover`.

### Files changed

- `themes/Darkwood.css` — added custom cursor SVG data URIs

## 2026-05-10 Version 3.8

### Changes

- Bumped `app_version.json` from `3.7` to `3.8`.
- Bumped `app_metadata.py` DEFAULT_VERSION from `3.7` to `3.8`.
- Updated `global_stats_prompt_version` to `3.8`.
- Added `CHANGELOG_3.8.md` to `runner.py` release source copy list.
- **Comprehensive cursor audit:** Checked all 16 remaining themes for custom cursor support — 13 have both default and hover cursors, 4 have body-only cursors (void, trench, diamond, matrix). Documented in CHANGELOG_3.8.md.

## 2026-05-10 DeadOps Arcade theme custom cursors

### Changes

- Added a retro arcade skull pointer cursor with gold/red glow as the default `body` cursor, replacing the previous `crosshair` cursor.
- Added a neon arcade target cursor with crosshair glow for interactive/hover elements: `button:hover`, `.nav-btn:hover`, `.sb-item:hover`, `.config-btn:hover`, `.camo-option:hover`, `.star-btn:hover`, `.header:hover`, `input:hover`, `select:hover`, `.chal-btn:hover`, `.card:hover`, `.chal-card:hover`, `.perk-item:hover`, `.nav-btn.active`, `.nav-btn-small:hover`.

### Files changed

- `themes/DeadOps Arcade.css` — replaced `crosshair` cursors with custom SVG data URI cursors

## 2026-05-11 Version 3.8.1 — updater map compat fix

### Changes

- Bumped `app_version.json` from `3.8` to `3.8.1`.
- Bumped `app_metadata.py` DEFAULT_VERSION from `3.8` to `3.8.1`.
- Updated `global_stats_prompt_version` to `3.8.1`.
- Added `CHANGELOG_3.8.1.md` to `runner.py` release source copy list.
- Fixed updater not pulling the `local map compatiblityu` folder during updates, backups, or rollbacks. Added `"local map compatiblityu"` to `MANAGED_PATHS` in `updater.py`.

### Verification

- Python compile check passed for `updater.py`.
- All smoke tests pass.

## 2026-05-11 Version 3.8.3 — CSV XP lookup fix, UPX disabled, version metadata

### Changes

- Bumped `app_version.json` from `3.8.2` to `3.8.3`.
- Bumped `app_metadata.py` DEFAULT_VERSION from `3.8.2` to `3.8.3`.
- Updated `global_stats_prompt_version` to `3.8.3`.
- Added `CHANGELOG_3.8.3.md` to `runner.py` release source copy list.
- Hopefully fixed the CSV XP lookup issue where levels 1–90 used global cumulative values instead of per-level values.
- **Disabled UPX compression** in all three `.spec` files (`BO3Tracker.spec`, `BO3Updater.spec`, `UEMMapCompatibility.spec`) to reduce AV false-positive detections.
- **Added Windows version metadata** to all three executables:
  - Created `version_info_bo3tracker.txt`, `version_info_updater.txt`, and `local map compatiblityu/version_info_mapcompat.txt` with CompanyName, FileDescription, FileVersion (3.8.3.0), ProductName, LegalCopyright, and OriginalFilename.
  - Wired each `.spec` file's `version=` parameter to its respective version info file.

### Verification

- All smoke tests pass.

## 2026-05-11 Version 3.8.2 — updater progress bar

### Changes

- Bumped `app_version.json` from `3.8.1` to `3.8.2`.
- Bumped `app_metadata.py` DEFAULT_VERSION from `3.8.1` to `3.8.2`.
- Updated `global_stats_prompt_version` to `3.8.2`.
- Added `CHANGELOG_3.8.2.md` to `runner.py` release source copy list.

## 2026-05-12 Version 3.8.4 — live dashboard player names

### User request

- User reported that player names were not showing under each player on the live dashboard.
- User asked whether player `0` was set as `PLAYER 1`, then asked to make that true.
- User asked to add the updates to the changelog and rename versioning to `3.8.4`.

### Changes

- Updated live stats processing to read player display names from `playername` as well as `name`, `player_name`, `username`, and `display_name`.
- Escaped player names before rendering them into dashboard tab HTML.
- Sorted live dashboard players by numeric player id so player `0` appears first.
- Added match XP and XP/min values to the compact live overlay.
- Added current rank, current level, and level-ups gained this game to the compact live overlay.
- Updated the compact overlay to show `Master Prestige` for prestige 20+ players, with Legend/Absolute/Ultimate tier shown separately when available.
- Added Settings toggles to show or hide individual compact overlay sections: perks, top damage, rank/level, and match XP.
- Adjusted compact overlay layout and height calculation so match XP stays visible when rank/tier details are enabled.
- Updated the setup screen CurrentGame.json hint to show the full example path: `YOURDRIVELETTER:\SteamLibrary\steamapps\common\Call of Duty Black Ops III\players\311210\2942053577\CurrentGame.json`.
- Added local rotating weekly challenges in `challenge_system.py` using `weekly_local_...` IDs, deterministic ISO-week rotation, and `active_from` timestamps so old history files do not backfill new weekly objectives.
- Kept remote/devtools challenge manifests separate from local rotation; existing remote weekly challenges and devtools upload flow continue using their current manifest contract.
- Added devtool-compatible remote weekly pools: devtool weekly challenges are published through `weekly_rotation.pool`, the app rotates active challenges with `weekly_remote_...` IDs, and local weeklies remain the fallback when no remote weekly pool exists.
- Updated `dev_tools/modules/challenge_manifest.py` and `dev_tools/modules/remote_management_manifest.py` to preserve the existing manifest shape while adding `weekly_rotation.enabled`, `weekly_rotation.active_count`, and `weekly_rotation.pool`.
- Added `custom_camos_sync.py` to sync `custom_camos.json` from `https://uemmaps.com/custom_camos.json` with a once-per-day startup check, conditional `ETag` / `Last-Modified` headers, JSON validation, and a manual Settings sync button.
- Verified the remote camo sync against a temporary file. Local Python rejected the certificate chain, so added a narrow TLS fallback for this public JSON endpoint; the server provides `Last-Modified` for conditional checks.
- Added `custom_camos_sync.py` to `runner.py` release source copies.
- Added `CHANGELOG_3.8.4.md`.
- Bumped `app_version.json` from `3.8.3` to `3.8.4`.
- Bumped `app_metadata.py` DEFAULT_VERSION from `3.8.3` to `3.8.4`.
- Updated Windows version metadata files from `3.8.3.0` to `3.8.4.0`.
- Added `CHANGELOG_3.8.4.md` to `runner.py` release source copy list.

### Verification

- Python compile checks passed for the touched dashboard, overlay, challenge, and camo sync modules.

## 2026-05-13 Version 3.8.4 — emblem reward support

### User request

- User asked whether emblem support could work the same way as playercards for challenge rewards.
- User asked for emblems to be stored in a separate folder from playercards.
- User asked for the dev tool to include emblems as a reward option.
- User asked whether emblems could also be unlocked through `unlocked_rewards.json` for testing.

### Changes

- Added an `emblems` asset folder with a placeholder so the folder is included before real emblem assets are added.
- Added `get_emblem_src(...)` in `asset_helpers.py`, supporting `.jpg`, `.jpeg`, `.png`, `.webp`, `.mp4`, and `.webm`.
- Added pywebview API methods in `bo3tracker.py` for emblem images, unlocked emblems, active emblem get/set, and manual test unlocks from `config/unlocked_rewards.json`.
- Kept completed challenge reward behavior consistent with playercards: challenges using `reward_type: "emblem"` unlock their `reward_val` when completed.
- Filtered manual `unlocked_rewards.json` emblem entries against actual files in `emblems` so existing theme names do not appear in the emblem selector.
- Added Settings UI for previewing and equipping emblems.
- Added Career Dossier display for the active emblem beside the playercard.
- Added challenge card reward text and completed-state handling for emblem rewards.
- Added `emblem` to dev-tool reward types in `dev_tools/modules/validation.py`.
- Added `discover_emblems(...)` and emblem asset validation for management manifests.
- Added emblem rewards to random weekly generation in `dev_tools/modules/challenge_manifest.py` and wired the dev GUI to pass discovered emblem assets.
- Added `emblems` to `runner.py` release asset packaging, `updater.py` managed paths, and smoke-test runner/package checks.
- Added emblem patch notes to `CHANGELOG_3.8.4.md`.

### Verification

- Python compile checks passed for `asset_helpers.py`, `bo3tracker.py`, `dev_tools/modules/validation.py`, `dev_tools/modules/challenge_manifest.py`, and `dev_tools/admin_gui.py`.
- Full `run_smoke_tests.py` pass confirmed.
- Runner readiness check confirmed all listed source files and required packaged assets exist, including `emblems`.
- `runner.py` is not ready to execute in the currently available Python runtime because `PyInstaller` and `pywebview` are not installed there, and no system `python` or `pyinstaller` command is on PATH.

- Added a `ttk.Progressbar` to the updater GUI that fills during the download, with live KB-downloaded status text.

### Verification

- Python compile check passed for `updater.py`.

## 2026-05-10 Factory theme integration

### Changes

- Fixed `themes/factory.css` background image reference from `gothic_industrial_fortress_under_stormy_skies.png` to `factory.png` (the actual file provided by the user).
- Added `"factory"` entry to `OVERLAY_THEMES` in `overlay_themes.py` (green/rust/amber palette).
- Added `"factory"` entry to `GRAPH_THEMES` in `ui_main.py` for chart colour schemes.
- Added `"factory"` entry to `THEME_SETTINGS_COPY` in `ui_main.py` with industrial-themed UI labels.

### Files changed

- `themes/factory.css` — fixed background image URL
- `overlay_themes.py` — added factory overlay palette
- `ui_main.py` — added factory GRAPH_THEMES and THEME_SETTINGS_COPY entries

## 2026-05-13 Version 4.0.0 — Map weapons discovery and weapon-specific challenges

### Request

User asked to add gun challenges based on what guns are on the map by pulling all console names from `currentgame.json`, including weapons players are holding. User requested a separate file called map weapons, tying the Steam link/ID to the group of weapons, then adding map-based challenges from the dev tool referencing those weapons.

### Changes

- Added `map_weapons.py` with a `MapWeaponsManager` singleton that:
  - Auto-discovers weapons from live game data by scanning all players' `top5`/`weapon_data`.
  - Stores per-map weapon lists keyed by normalized Steam Workshop link.
  - Tracks `console_name`, `display_name`, `first_seen`, `last_seen`, `seen_count`.
  - Links upgraded (PaP) variants to their base weapon via `base_console_name`.
  - Supports manual add/remove/set_map_name.
  - Persists to `config/map_weapons.json`.
- Hooked `map_weapons_manager.discover_from_game(current_data)` into `bo3tracker.py`'s `monitor_game()` loop.
- Updated `game_data.py` with `MAP_WEAPONS_FILE = "map_weapons.json"`.
- Updated `challenge_system.py`:
  - Added `extract_weapon_stats()` helper to extract per-weapon kills/headshots from player data.
  - Injected `_weapons` into stats dict in `apply_live_update()`, `_apply_game_stats_with_time()`, `process_completed_game()`.
  - Added `weapon_console_name` and `weapon_display_name` to `normalize_map_challenge()`.
  - Updated `_challenge_matches_map()` to check weapon filter.
  - Added `_get_weapon_stat_value()` combining base + upgraded variant stats.
  - Updated `_apply_map_stats_to_challenges()` to use weapon-specific stats when `weapon_console_name` is set on a challenge.
- Added `dev_tools/admin_gui.py` Map Weapons tab with map list, weapon list (base + PaP grouped), add/remove weapons, camo DB lookup, Steam name fetch, auto-discovery toggle.
- Extended Map Challenges tab with weapon console name/display name fields and auto-populating weapon dropdown.
- Updated `dev_tools/modules/validation.py` with `weapon_kills` and `weapon_headshots` in `ALLOWED_STATS`.
- Added `weapon_kills` and `weapon_headshots` stat templates to `MAP_STAT_TEMPLATES`.
- Bumped version metadata to `4.0.0` across all version files.
- Added `CHANGELOG_4.0.0.md`.

### Verification

- Python compile checks passed for all touched modules.
- CANVAS weapon discovery tested against 3 archived games (5 player-entries, 17 unique weapons across all players).
- Base/upgraded pairs confirmed: LSAT/FSIRT, AUG/AUG-5OM3, M1911/Mustang & Sally, AN-94/Actuated Neutralizer 94000.

## 2026-05-14: PaP matching fixes, runner.py inclusion, weapon challenges for RAINY DEATH, duplicate weapons fix

### Changes

- **`challenge_system.py`**: `_weapon_in_data()` and `_get_weapon_stat_value()` now handle the `_upgraded` suffix (BO2 weapons like Origins Shield), plus reverse matching when challenge filter is already an upgraded name — both base and upgraded kills are summed.
- **`challenge_system.py`**: Fixed `_get_weapon_stat_value()` not tracking any weapon kills — looked up `"weapon_kills"` / `"weapon_headshots"` directly in weapon data entries, but `extract_weapon_stats()` stores values under `"kills"` / `"headshots"`. Now normalises the stat name by stripping the `weapon_` prefix before lookup.
- **`map_weapons.py`**: `get_base_console_name()` now strips both `_upgraded` and `_up` suffixes.
- **`map_weapons.py`**: Removed separate upgraded variant entries entirely — PaP weapons are now stored only as fields on the base entry (`upgraded_console_name`, `upgraded_display_name`). Updated `discover_from_game()` to stop creating separate upgraded entries with `base_console_name`. Updated `get_weapons_with_upgraded()` to build the upgraded list synthetically from the base entry's fields. Removed `add_weapon()` `base_console_name` logic. Removed `get_base_console_name()` helper (unused). Cleaned `map_weapons.json` from 147 entries down to 75 (no duplicate weapon lines).
- **`runner.py`**: Added `map_weapons.py` and `CHANGELOG_4.0.0.md` to release source copy list.
- **`config/map_challenges.json`**: Added 4 weapon-specific challenges for RAINY DEATH (Norinco Type 95 kills/headshots, M600 MK3 kills, CAR-15 Strap kills).

### Verification

- All changed `.py` files pass `py_compile`.
- All 158 smoke tests pass (0 failures).

## 2026-05-14 Version 4.0.1 — map challenge sync and language support

### Changes

- Bumped app metadata from `4.0.0` to `4.0.1`.
- Updated Windows version metadata files to `4.0.1.0` for BO3 Tracker, BO3 Updater, and UEM Map Compatibility.
- Added one-way server-controlled map challenge sync:
  - `sync_map_challenges.py`
  - `map_challenges_sync_url` in `app_version.json`
  - startup pull via `bo3tracker.py`
  - remote GET endpoint at `site/public_html/tracker/map_challenges_sync.php`
  - remote seed file at `site/public_html/tracker/map_challenges.json`
- Map challenges now sync in replace mode from the site while preserving local progress by challenge ID.
- Removed map challenge IDs are archived locally under `removed_challenge_progress` so progress can return if the same ID is re-added later.
- Added Settings language selector with saved `language` config support.
- Added locale packs for German, Spanish, French, Italian, Japanese, Korean, Polish, Portuguese, Russian, and Chinese.
- Added translation loading and application for sidebar navigation, Settings, Customization, Help & FAQ, Live Game, Camo Matrix, Career Profile, Weapon Usage, Best Matches, and Challenges.
- Added placeholder translation support for search inputs.
- Added `locales` to release packaging.
- Added `sync_map_challenges.py` and `CHANGELOG_4.0.1.md` to `runner.py` release source copying.

### Verification

- JSON validation passed for all locale packs in `locales/`.
- Python compile checks passed for touched modules.
- Full `run_smoke_tests.py` pass confirmed.

## 2026-05-15 Version 4.3.0 — Local Chart.js bundling

### Problem

The app loaded Chart.js from `https://cdn.jsdelivr.net/npm/chart.js` at every launch. This meant:
- No graph functionality (XPM, Round XP, ZPM charts) without an internet connection.
- A network request on every app startup.
- Potential for broken graphs if the CDN was down or the user's network blocked it.

### Changes

1. **Downloaded Chart.js v4.5.1** from the CDN and saved it as `chart.js` in the project root.
2. **Updated `ui_main.py`**: Replaced the CDN `<script src="...">` tag with an inline `<script>` block containing the local Chart.js content. The function signature now accepts a `chart_js_content` parameter.
3. **Updated `bo3tracker.py`**: `get_main_app_html()` reads `chart.js` from the app base path and passes its content to `build_main_app_html()`.
4. **Updated `runner.py`**: Added `chart.js` to the release assets copy list.
5. **Updated smoke tests**: Added `chart.js` to the required asset list and runner asset packaging check.
6. **Updated `app_version.json`** and **`app_metadata.py`**: Version bumped from `4.2` to `4.3.0`.
7. **Created `CHANGELOG_4.3.0.md`**.
8. **Created backup** at `I:\camo_tracker_backup_v4.2_20260515-150945\` before making changes.

### Verification

- Python compile checks passed for touched modules (`app_metadata.py`, `bo3tracker.py`, `ui_main.py`, `runner.py`, `run_smoke_tests.py`).
- Full `run_smoke_tests.py` pass confirmed.

## 2026-05-15 Version 4.3.0 — XP requirements CSV in-memory cache

### Changes

1. **Added `_csv_loaded` flag** to `MatchXPTracker` so the 2711-row `xp_requirements.csv` is parsed into memory dicts exactly once per session.
2. **Moved CSV loading out of `__init__`** — now lazy-loaded on the first `get_xp_required()` call instead of at construction time.
3. **`load_csv()`** returns immediately if already loaded, and sets `_csv_loaded = True` after a successful parse.
4. **Failed parses do not set the flag**, so a transient read error can retry on the next lookup.

### Behavior

- Restarting the app re-reads the file from disk, so CSV edits are picked up after restart.
- Within a session the CSV is never re-parsed — all level/XP lookups are constant-time dict reads.
- The `_csv_loaded` guard prevents any code path from double-parsing, even if `load_csv()` were called directly.

### Changed files

- `match_xp.py` — added `_csv_loaded`, lazy-load in `get_xp_required()`, early-return guard in `load_csv()`.

### Verification

- Python compile check passed for `match_xp.py`.
- Full `run_smoke_tests.py` pass confirmed.

## 2026-05-15 Version 4.3.0 — Discord Rich Presence

### Changes

1. **Added `discord_presence.py`** with a minimal Discord local IPC client for optional Rich Presence updates without adding a mandatory third-party dependency.
2. **Added default public Discord Application ID** in `game_data.py`, so public users can enable the tracker Discord card without creating their own Discord Developer Portal application.
3. **Added tracker Discord presence settings** in `ui_main.py`:
   - Main toggle and status text for the tracker card.
   - Advanced Application ID and image asset fields hidden behind a collapsed details control.
   - Clear labels explaining that this is the community tracker Discord card.
4. **Added official UEM/T7 Discord presence settings**:
   - Reads BO3's `players/t7.json` based on the configured `CurrentGame.json` path.
   - Toggles `discord_enabled` in that file.
   - Shows a warning confirmation before disabling the official UEM/T7 Discord card.
   - Notes that BO3/UEM must be restarted after changing the setting.
5. **Enhanced tracker Discord activity content**:
   - Activity title is now `Ultimate Experience Mod Community Tool`.
   - Shows live map and round in the details line.
   - Shows prestige/tier/level, match XP gained, total kills, top weapon usage, and a compact level XP progress bar in the state line.
   - Uses current Steam Workshop map preview art as the large image when a Steam Workshop ID/link is available.
6. **Added Rich Presence buttons**:
   - `Ultimate Experience Mod` button points to `https://steamcommunity.com/sharedfiles/filedetails/?id=2942053577`.
   - `Community Tool` button points to the project repository.

### Changed files

- `discord_presence.py`
- `bo3tracker.py`
- `game_data.py`
- `ui_main.py`
- `style.css`
- `workshop_images.py`
- `runner.py`
- `run_smoke_tests.py`
- `CHANGELOG_4.3.0.md`

### Verification

- Python compile checks passed for touched modules during the Discord Presence work.
- Full `run_smoke_tests.py` pass confirmed after the final Discord Presence updates.

## 2026-05-15 Version 4.3.0 — Backup Restore UX

### Changes

1. **Added UEM stats restore support**:
   - Restores `stats_zm_0.cgp` through `stats_zm_4.cgp` from a selected zip.
   - Uses the configured or setup-selected `CurrentGame.json` path to find the correct BO3 `players` folder.
   - Creates an automatic `uem_stats_before_restore_*.zip` safety backup before replacing existing stat files.
2. **Added tracker config restore support**:
   - Restores files from backup archives that contain the tracked `config/` folder.
   - Skips workshop image cache restore because that cache is regenerated.
   - Creates an automatic `tracker_config_before_restore_*.zip` safety backup before replacing existing config files.
   - Reloads the app view after restore when the restored config includes setup paths.
3. **Integrated restore actions into the UI**:
   - Settings now offers restore buttons beside the existing UEM stats and tracker config backup buttons.
   - First-run setup now includes restore actions for users moving to a fresh install or recovering an existing setup.
   - Both restore flows show confirmation warnings before opening the backup picker.

### Changed files

- `player_stats_backup.py`
- `bo3tracker.py`
- `ui_main.py`
- `ui_views.py`
- `setup.css`
- `run_smoke_tests.py`
- `CHANGELOG_4.3.0.md`

### Verification

- Python compile checks passed for the touched Python modules.

## 2026-05-15 Version 4.3.0 — Weapon Category Chart

### Changes

1. **Added a Kills by Weapon Category donut chart** to the career weapon usage page.
2. **Resolved categories using `map_weapons.json` first**, then falling back to the existing weapon category helper/normalizer when a weapon is not known for the map.
3. **Returned category totals from the weapon usage API** so the chart and table share the same resolved category data.
4. **Reduced category fallback noise** by treating `other` from `map_weapons.json` as inconclusive and adding fallback detection for prefixed custom weapon IDs, Pack-a-Punched suffixes, and melee weapons.
5. **Corrected known fallback classifications**:
   - Added the `Melee` category for real melee/wonder entries such as lightsabers.
   - Corrected `Sumarbrandr` / `t8_zweihander_up` to resolve as `lmg` rather than melee.
   - Verified the local archived weapon split dropped `Other` from over 49% to roughly 0.5% without editing `map_weapons.json`.

### Changed files

- `bo3tracker.py`
- `map_weapons.py`
- `weapon_categories.py`
- `ui_main.py`
- `style.css`
- `CHANGELOG_4.3.0.md`

### Verification

- Python compile checks passed for the touched Python modules.
- Full `run_smoke_tests.py` pass confirmed.
