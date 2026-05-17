# Changelog

## V.3.4 (2026-05-11)

### Added
- Settings option to toggle theme audio on/off. Audio is enabled by default; turn it off in Settings &gt; Theme Audio. Requires app restart.
- `audio` field added to themes in `themes.json` so themes can declare their own audio files (e.g. Dead Ops Arcade).
- Theme audio state shown in the Settings Project State table.
- JavaScript now checks `THEME_AUDIO_ENABLED` and `theme.audio` before playing audio, instead of hardcoding the DeadOps Arcade name check.

### Fixed
- Theme media no longer tries to play audio when `theme.audio` is missing from the theme definition.

### Changed
- `applyTheme` and `tryStartDeadopsAudio` respect the new `theme_audio_enabled` config value.
- `fitDeadopsMediaToEmptySpace` checks `THEMES[currentTheme]?.audio` instead of a hardcoded theme name.
- `Save Audio Setting` button in the settings window.

## V.3.3 (2026-05-11)

### Added
- Dead Ops Arcade theme now shows the local `themesmap/Deadops.gif` under the map grid with hidden looping `themesmap/deadops.mp3` audio.
- Dead Ops Arcade local media now loads through a tiny localhost asset server instead of oversized embedded data URIs, avoiding WebView2 initialization errors.
- Dead Ops Arcade media now fits into the empty space below the map cards and above pagination instead of overlaying the footer.
- Dead Ops Arcade media quality improved by preserving the main GIF aspect ratio and using a blurred full-width backdrop.
- Image worker callbacks now stop when the app window closes, avoiding disposed WebView2 update errors.
- Cog settings button in the main header, opening a separate settings window.
- New `settings_page.py` script showing current versions, config paths, image cache limits, and Google Sheets tab names.
- Settings controls for Steam image caching, including an on/off toggle and a cache-size slider up to 1024 MB.
- Separate `Submission Metadata` Google Sheets tab for timestamp, map, Steam link, submitter, report type, and barebones version tracking.
- Help page section explaining how to submit reports and copy rows from the `Submissions` tab into the main sheet.

### Fixed
- Steam image loading now drops stale pending downloads when users rapidly paginate, preventing a large backlog of Steam requests.
- Steam image requests now pause and retry later after HTTP 429 rate-limit responses.
- New submissions now append explicitly into the `A:L` main-sheet table range, preventing Google Sheets from placing row data after blank spacer columns.
- Restored the shifted test submission row back into the copyable `A:L` columns.
- Submission rows no longer include metadata fields on the same row, so selecting/copying a whole visible submission row will not bring extra metadata fields into the main sheet.
- Full support reports now write `Yes` or `No` into the `Full` status column instead of writing the selected UEM version there.
- Full support with bugs reports now write `YES/BUGS (see notes)` into the `Full` status column instead of writing the selected UEM version there.
- Repaired existing submission rows where the `Full` dropdown column contained `Public-V1.3.1 (build-005)`.

### Changed
- Theme definitions were moved out of `app.py` into `themesmap/themes.json`.
- Image downloads now favor cached/visible-page images and cap pending uncached Steam downloads.
- Steam image cache limit increased from 50 MB to 200 MB so the app can retain many more Workshop thumbnails locally.
- Steam image cache settings are now read from `config/uem_config.json` instead of being hardcoded only in `image_fetcher.py`.
- Runtime config, favorites, and Google credentials were moved into a new `config/` folder.
- `Submissions` now mirrors the main sheet columns only: `A:L`.
- Submission metadata is written separately to `Submission Metadata` rather than extra columns on `Submissions`.
- Submission report dropdowns now show only recent/current version families.
- Submitted `Full` and `Barebones` cells copy dropdown validation from the main tracker where available, so the status cells match the existing Google Sheets dropdown behavior.

## V.3.2 (2026-05-11)

### Added
- Barebones version dropdown in the submission form, split from full version.
- Current version marking in version dropdowns.
- Steam Workshop auto-fill fallback using `steam_scraper.py` for maps not already in the local database.
- Barebones version metadata support for Google Sheets submissions.

### Fixed
- Invalid regex escape warning in the JavaScript auto-fill code.
- Select text clipping for long version names.

### Changed
- Submission form UEM version field split into `Full UEM Version` and `Barebones UEM Version`.
- `sheet_db.submit_report()` accepts a `bb_version` parameter.
