# Devlog - V.3.5

## 2026-05-11

### Apps Script Submission Endpoint
Moved public submission builds away from shipping Google service-account credentials. `sheet_db.py` now checks `config/uem_config.json` for `submission_endpoint_url`; when present, it posts report payloads to the Apps Script web app with a shared secret and stable per-install client ID. If no endpoint URL is configured, the old `gspread` service-account path remains as a local/admin fallback.

Added `apps_script_submission_endpoint.gs` for the Google Sheet side. The script validates the shared secret, rejects missing/invalid Steam Workshop links, uses a honeypot field, applies a per-client cooldown and per-Steam-ID duplicate cooldown, appends copyable data to `Submissions`, writes audit data to `Submission Metadata`, and stores recent rate-limit state in a hidden `Submission Rate Limits` tab.

Configured the current local app with the deployed Apps Script endpoint and secret. A direct endpoint test returned `{"ok":true}` and created a `Codex Test Submission` row, confirming the deployment accepted the payload. The normal local Python HTTPS path on this machine still reports a certificate-chain verification error, so insecure verification was only used for the manual endpoint test and was not made the app default.

### Map App Packaging
Added `build_map_compat.py` and `UEMMapCompatibility.spec` inside the map compatibility folder. The build script creates a local `release/` folder with `UEMMapCompatibility.exe`, runtime assets, config, and a `scripts/` source snapshot. It skips `google_credentials.json` and service-account JSON files by default so public packages do not include reusable Google credentials.

Updated `app.py` so packaged builds resolve runtime paths from the exe folder, change into that folder on startup, and open Help/Settings as additional pywebview windows in the same process. This avoids the old packaged behavior where `sys.executable help_page.py` would point back at the frozen exe instead of Python.

## 2026-05-11

### Theme Audio Toggle
Added a `theme_audio_enabled` setting to `config/uem_config.json` so users can turn off theme background audio without losing their theme selection.

The config defaults to `true` (audio on). The value is passed into the HTML template as a JS constant `THEME_AUDIO_ENABLED` and checked before any `audio.play()` call in `applyTheme` and `tryStartDeadopsAudio`. The settings page has a new "Theme Audio" section with a checkbox and save button, wired through `SettingsApi.save_theme_audio_setting()`.

Also cleaned up the hardcoded `name === 'DeadOps Arcade'` checks. `applyTheme` now looks for `theme.audio` on the theme object, `fitDeadopsMediaToEmptySpace` uses `THEMES[currentTheme]?.audio`, and each theme in `themes.json` can declare an `audio` block. Dead Ops Arcade has been updated with `audio.file: "deadops.mp3"` and `audio.name: "Dead Ops Arcade Theme"`.

# Devlog - V.3.3

## 2026-05-11

### Submission Sheet Copy Workflow
The `Submissions` worksheet needs to be easy to copy into the main compatibility sheet. Earlier metadata columns (`Timestamp`, `Submitted By`, `Report Type`, and `Barebones UEM Version`) were kept to the right of the normal sheet columns, but selecting and copying a full row could still carry those extra fields into the main sheet.

Changed the layout so `Submissions` now contains only the main tracker columns `A:L`. Submission metadata is written to a separate `Submission Metadata` tab instead, with enough identifying context (`Timestamp`, `Map`, `Steam Link`, `Submitted By`, `Report Type`, and `Barebones UEM Version`) to audit reports without polluting the copyable row.

### Google Sheets Append Range
Adding blank spacer columns between the main row and metadata exposed a Google Sheets append behavior: `append_row()` detected the right-side metadata block as the active table and shifted submitted values into later columns. The writer now passes an explicit `table_range` for the `A:L` submission table, so new reports append into the intended columns.

### Dropdown Status Values
Submission reports now write status values into status columns, not version strings. A full support report writes `Yes` into `Full`; a broken report writes `No`; barebones reports write `Yes`, `Yes/Bugs`, or `No` plus the selected barebones version into the Barebones column. The actual full UEM version remains in `UEM Version (Full)`.

The writer also copies dropdown validation from the main tracker sheet into new submission status cells when the source sheet is available. This keeps submitted rows visually and behaviorally close to the existing Google Sheets dropdown chips.

### Full Status Dropdown Repair
Found one remaining path where `Works` and `WorksBugs` reports still assigned `full_val = uem_version`, which put values like `Public-V1.3.1 (build-005)` into the `Full` dropdown column. Updated the mapping so `Works` writes `Yes` and `WorksBugs` writes `YES/BUGS (see notes)`.

The live `Submissions` sheet was also scanned for existing `Full` cells containing version strings. The affected row was repaired so column `D` now contains a valid dropdown status again.

### Recent Version Lists
The submission form no longer exposes every historical version found in the cache. Full and barebones version dropdowns are filtered to the current version family, with the current version selected by default. This reduces accidental old-version reports while preserving the ability to choose the immediately relevant recent build.

### Live Sheet Repair
After the append-range issue was found, the shifted test submission row was moved back from the later columns into `A:L`, the extra right-side metadata area was cleared from `Submissions`, and the metadata headers were moved to the new `Submission Metadata` tab.

### Help Page
Updated `help_page.py` with a new submission workflow section and a Google Sheets workflow section. The help now explains that `Submissions` is copy-safe and that tracking data lives in `Submission Metadata`.

### Config Folder Cleanup
Moved runtime settings, favorites, and Google service-account credential JSON files into a new `config/` folder. `app.py` now resolves `uem_config.json` and `favorites.json` from that folder and creates it automatically when saving. `sheet_db.py` now reads Google credentials from `config/google_credentials.json`.

### Theme File Split
Moved the large `THEMES` dictionary out of `app.py` and into `themesmap/themes.json`, beside the theme-specific Dead Ops media assets. `app.py` now loads themes from that JSON file on startup and keeps a minimal built-in default fallback so the app can still open if the theme file is missing or invalid.

### Settings Window
Added a cog button to the main app header and wired it through the pywebview API to open a separate `settings_page.py` script. The first version of the settings window is informational: it shows current mod versions, config and credential paths, image cache usage/limits, Steam request backoff settings, and the Google Sheets tab names used by submissions.

Added editable Steam image cache controls to the settings page. Users can now turn local Workshop thumbnail caching on or off and set the cache quota with a slider from 0 MB to 1024 MB. The values are saved into `config/uem_config.json` as `image_cache_enabled` and `image_cache_limit_mb`; the main app applies them when it starts its image worker.

### Dead Ops Arcade Theme Media
Replaced the Dead Ops Arcade YouTube embed with local theme assets from `themesmap/`. The first local-asset attempt embedded `Deadops.gif` and `deadops.mp3` as data URIs, but the GIF made the generated HTML too large for WebView2's `NavigateToString`. The app now starts a tiny localhost static asset server for `themesmap/`, keeping the HTML small while still loading the local GIF and MP3 reliably. The gif displays as a wide media strip underneath the map grid, while the mp3 loops through a hidden audio element. The media block is shown only when the active theme key is `DeadOps Arcade`; switching away pauses and resets the audio.

After testing, the media block was changed to measure the empty space left below the rendered map cards and above pagination. The GIF fits into that gap when there is room and hides when the gap is too small, avoiding footer overlap while still using the lower empty area. To improve quality in the wide shallow bar, the media now uses two GIF layers: a blurred cover backdrop fills the whole width, while the main GIF is centered with its aspect ratio preserved.

Also added close handling for the background image worker. When the main window closes, pending image work is cleared and later callbacks skip `evaluate_js`, preventing disposed WebView2 errors from image updates that finish after shutdown.

### Steam Image Rate-Limit Protection
The original image worker kept appending uncached page images to a single queue. If a user paged quickly through many results, the app could build a large backlog of old Steam Workshop image lookups even though those pages were no longer visible.

Changed `SteamImageFetcher.queue_batch()` so cached images still notify the UI immediately, but uncached downloads replace the pending queue with the latest visible batch. The pending queue is capped, in-progress downloads are deduplicated, and failed image lookups are temporarily cooled down. HTTP 429 responses now pause new Steam image requests for a backoff period before retrying later.

Measured the current compressed thumbnail cache against the Workshop IDs in `uem_cache.json`. The full set is estimated to need roughly 158 MB by average cached image size, so the local `steam_images` quota was increased from 50 MB to 200 MB to allow near-complete caching with some headroom.

# Devlog - V.3.2

## 2026-05-11

### SyntaxWarning Fix
Python 3.12+ emitted a `SyntaxWarning` for an invalid `\d` escape inside the JavaScript auto-fill regex. Escaped it as `\\d` so the JavaScript engine receives the intended digit class at runtime.

### Barebones Version Split
The submission form originally had a single UEM version dropdown. The database tracks both full and barebones versions, so the form now collects both independently. The barebones list is extracted from the `Barebones (V 1.1.22 Unless Stated)` field in the JSON cache.

### Current Version Marking
Version dropdowns mark the current release so submitters can quickly pick the expected version. Current versions are kept as constants because they change with each UEM release.

### Select Text Clipping
Long version strings were clipped in the filter bar. The select width constraints were loosened so controls can wrap cleanly in the header.

### Steam Workshop Scraper
Auto-fill originally worked only for maps already present in the local database. `steam_scraper.py` fetches Steam Workshop page details and lets new or unknown maps still populate name and author fields where Steam exposes them.
