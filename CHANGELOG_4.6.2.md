# BO3 Tracker 4.6.2

## Global Stats Uploads
- Added Pack-a-Punch, enchantment level, repack level, packed weapon name, and AAT details to uploaded weapon summaries.
- Added Workshop ID support to uploaded match summaries so the website can resolve map imagery from match data when the map is not already in the site cache.

## Translations
- Added localized text for the Ultimate Experience Mod Community Tool Discord Presence settings section across all supported languages.
- Added localized text for the Official UEM/T7 Discord Presence settings section, including advanced Discord placeholders, status fallbacks, and the disable-confirmation prompt.
- Added localized GitHub changelog block support so the Help changelog can switch release-note language with the selected app language when the release body includes matching `<!-- changelog:xx -->` sections.
- Added a local DeepL changelog translation helper with per-changelog caching to generate GitHub-ready localized release blocks without re-translating unchanged notes.
- Added a GitHub Actions workflow that can translate a published GitHub release automatically using the `DEEPL_API_KEY` repository secret.

## Website Recent Matches
- Recent matches now returns the latest 50 uploaded matches and displays them 6 per page.
- Added Previous/Next pagination to keep the page easier to browse.
- Added search across map name, raw game ID when available, safe game ID, match ref, mode, round, Workshop ID, weapon names, packed names, and AAT values.
- Recent Matches search now queries the server, so known matches can be found even when they are not on the first loaded page.
- Added optional raw `game_id` and `history_game_id` storage plus a safe short `game_ref` fallback based on `game_id_hash` so users can find matches by the history filename after the updated app has re-uploaded them.
- Added map thumbnails and subtle card backdrops using local cached Workshop images when available.
- Added lazy Workshop image fallback through `fetch_image.php` when a map has a Workshop ID but no local cached image yet.
- Reduced newly fetched Workshop image cache size by compressing images to 640px wide JPGs at quality 72 when PHP GD is available.
- Added `workshop_id` storage migration for match submissions.

## Site Database
- Added `migration_add_weapon_pack_aat.sql` for weapon PaP/AAT metadata.
- Added `migration_add_match_workshop_id.sql` for match-level Workshop image resolution.
- Added `migration_add_match_game_id.sql` for searchable match history game IDs.
- Added `migration_add_match_history_game_id.sql` for searching the visible `Game_...` history filename.

## Version
- Updated app metadata to `4.6.2`.
- Updated Windows executable metadata to `4.6.2.0`.
