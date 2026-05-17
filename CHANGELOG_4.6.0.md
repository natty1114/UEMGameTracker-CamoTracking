# BO3 Tracker 4.6.0

## Per-Map Detail Pages
- Added clickable per-map detail pages from Career Profile map lists.
  - Added a top-level `MAP DETAILS` button on Career Profile that opens a dedicated archived map selection page.
  - The map selection page now scans the full archive so it can show every map played, not only the capped Career Profile top-map summaries.
  - The map selection page supports search, sorting by matches, highest round, time played, recently played, or map name, and paginates results at 24 maps per page.
  - Map selection cards show Steam Workshop preview images through the same cached workshop image helper used by the live dashboard when a workshop link is available.
  - Personal Bests, Most Played Maps, and Top Maps by Highest Match XP rows now open an in-app map profile.
  - Map profiles show matches, highest round, average round, best XP, average XP, KPM/XPM, best weapons, recent matches, and recent round history.
  - `api_data.py` now exposes `get_map_detail()` to aggregate Player 1 archived match history for a selected map.
  - Restored the Career rank card workshop image container expected by the dashboard media setting, preventing the Career Profile from appearing to stop at the header.
  - Tightened Career Profile header media sizing so the dossier cards and clickable map rows are visible sooner.

## Career Weapon Profiles
- Added clickable per-weapon profile details from the Weapon Usage table.
  - Weapon rows now open an in-page profile card with total kills, headshots, headshot percentage, corrected damage, PaP uses, best match, recent match rows, and Chart.js graphs for kills over time and kills by map.
  - `api_data.py` now exposes `get_weapon_detail()` to scan archived match history for a selected Player 1 weapon.
  - Fixed weapon row click handling for names containing apostrophes or punctuation, such as `Rang's Suoper Ray`.
  - Fixed weapon profile lookups for archived weapon names with stray whitespace, such as `Mystifier `, so the detail card matches the same kills shown in the Weapon Usage table.

## Live Weapon Status
- Added enchantment-tier display for live weapon statuses.
  - Live weapon status now prefers each weapon's `enchant` value and maps it to Unpacked, Common, Rare, Epic, Legendary, Mythic, Exotic, Divine, Eternal, Cosmic, Celestial, or Ultimate Enchantment.
  - Replaced the old `STD` fallback label with `Unpacked Weapon`.
  - Live weapon processing now prefers merged `weapon_data` before falling back to `top5`, so per-weapon enchantment fields are retained more reliably.

## AAT Tracking
- Added AAT display for live and archived weapon detail views.
  - Live weapon rows now show the current AAT from `currentAAT`, `current_aat`, or `aat` under the enchantment badge.
  - Weapon detail profiles now include AAT uses, top AAT, AAT breakdown, and an AAT column in recent match rows.
  - Added reusable AAT icon loading via `aat icons/<raw_aat_key>.png` or `.webp`, with text fallback when an icon is missing.
  - Added the first AAT icon asset: `aat icons/zm_aat_ricochet.png`, shown for `zm_aat_ricochet` with `Ricochet` hover text.
  - `runner.py` now includes the `aat icons` folder in release builds.

## Match History
- Added sidebar filters for archived match logs.
  - Match history can now be searched by map, player, or game ID.
  - Added map, date range, dynamic match XP range, and sort controls for newest, oldest, map name, highest round, highest XP, and lowest XP.
  - Archived match rows now show recorded XP earned for the match when available.
  - Filtered results paginate correctly and show a visible match count summary.
  - Cached archive metadata to keep the auto-refreshing sidebar responsive.

## Map Detail Performance & Pagination
- Added pre-built index (`map_index_cache.json`) of map→files to avoid scanning all archived matches.
- Map selection page reads entirely from the index; no longer re-scans archives on every visit.
- Both map selection and map detail pages cache data in memory after first load.
- Added pagination (25 matches per page) to map detail with a "Load More" button.
- Added REFRESH button on map selection page to force-rebuild the index.
- Added MAP SELECTION button on map detail header to return to the hub.
- Fixed game_id lookup in map detail rows — index stores filename-derived game_id so `get_history_report` finds the right file.
- Fixed `loadHistory` to show "ARCHIVED MATCH NOT" when a match isn't found (was leaving stale data).

## Persistent Map Detail Summary
- Added `config/map_detail_summary.json` — pre-computed per-map aggregates stored in the config folder for user backup.
- Map detail pages load from this file instead of re-opening every archived match file.
- Only maps whose entry count changed since the last index build are recomputed.
- REFRESH clears both the index and the detail summary for a full clean rebuild.

## Updater Preservation
- Added `favorites.json` to `PRESERVED_PATHS` so user favorites survive updates.
- Added `aat icons` and `chart.js` to `MANAGED_PATHS` so they're backed up and installed during updates.

## Live Dashboard Weapons
- Live weapon table now prefers `top5` over `weapon_data` so all 5 top weapons appear instead of only 2. (fix)

## Version
- Updated app metadata to `4.6.0`.
- Updated Windows executable metadata to `4.6.0.0`.
