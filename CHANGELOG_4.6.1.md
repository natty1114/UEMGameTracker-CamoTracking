# BO3 Tracker 4.6.1

## UI
- AAT icon now displayed inline next to enchantment name (row layout) instead of below it.
- AAT icon size increased from 34px to 42px.
- Enchantment label font size increased from 0.78em to 0.82em.
- Background removed from AAT icon images (`zm_aat_blast_furnace.png`, `zm_aat_dead_wire.png`, `zm_aat_fire_works.png`, `zm_aat_ricochet.png`, `zm_aat_thunder_wall.png`) using edge-connected flood fill to preserve icon details.
- Added a clearly labeled, unobtrusive animated Donate button in the sidebar linking to the UEM Map Testing PayPal donation page.
- Expanded Spanish, German, French, Italian, Portuguese, Russian, Japanese, Korean, and Chinese translations for Weapon Usage headings, weapon detail headings, Graph Overlay settings, and Map Details / Map Detail sections, including dynamically rendered map stats and table labels.
- Added search/filter controls to the dev tool Map Weapons editor so weapons can be found by display name, console name, category, Pack-a-Punch name, map name, or workshop ID, with optional all-map searching.

## Fixes
- Fixed calendar picker icon not visible on archived match filter date inputs in dark theme.
- Fixed workshop link button in map detail tab not navigating to the correct Steam Workshop page when the game data only has a numeric workshop ID instead of a full URL.
- Fixed career profile rank card no longer displaying the workshop map image as a background behind the card content.
- Fixed map detail hero workshop images being overly zoomed/cropped by changing `background-size` from `cover` to `contain`.
- Cleaned up weapon categories across the map weapon config, including Return to Bus Depot and other maps where weapons were incorrectly left in `Other` or assigned to the wrong weapon type.
- Improved automatic weapon categorization for additional COD weapon IDs, Wonder Weapons, melee weapons, and Star Wars weapons, while preserving explicit SMG/Sniper-style variant categories.

## Version
- Updated app metadata to `4.6.1`.
- Updated Windows executable metadata to `4.6.1.0`.
