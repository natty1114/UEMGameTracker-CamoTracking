"""Game-specific data constants for BO3 Tracker."""

GITHUB_RELEASES_API = "https://api.github.com/repos/natty1114/UEMGameTracker-CamoTracking/releases/latest"
TRACKER_GITHUB_URL = "https://github.com/natty1114/UEMGameTracker-CamoTracking"
UEM_WORKSHOP_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=2942053577"
UPDATER_EXE_NAME = "BO3Updater.exe"
DEFAULT_DISCORD_APPLICATION_ID = "1504865399185870869"
DISCORD_ACTIVITY_NAME = "Ultimate Experience Mod Community Tool"
CONFIG_FILE = "config.json"
DAMAGE_HISTORY_FILE = "damage_history.json"
GLOBAL_STATS_STATE_FILE = "global_stats_state.json"
REMOTE_MANAGEMENT_CACHE_FILE = "remote_management_cache.json"
CAMO_DB_FILE = "custom_camos.json"
MAP_WEAPONS_FILE = "map_weapons.json"
CSS_MAIN_FILE = "style.css"
CSS_SETUP_FILE = "setup.css"
THEMES_DIR = "themes"
ALWAYS_AVAILABLE_THEMES = {"Darkwood", "Cherry Blossom", "Clouds", "Dog Pack", "DeadOps Arcade", "Pacific Paradise", "Shi No Numa"}

PERK_NAMES = {
    "specialty_armorvest": "Juggernog",
    "specialty_quickrevive": "Quick Revive",
    "specialty_fastreload": "Speed Cola",
    "specialty_doubletap2": "Double Tap II",
    "specialty_widowswine": "Widow's Wine",
    "specialty_deadshot": "Deadshot",
    "specialty_electriccherry": "Electric Cherry",
    "specialty_additionalprimaryweapon": "Mule Kick",
    "specialty_staminup": "Staminup",
    "specialty_tracker": "Death Perception",
    "specialty_phdflopper": "PHD Flopper"
}

IGNORE_KEYWORDS = ["null", "specialty_pistoldeath"]

LANGUAGE_OPTIONS = [
    {"code": "en", "label": "English"},
    {"code": "es", "label": "Español"},
    {"code": "fr", "label": "French"},
    {"code": "de", "label": "German"},
    {"code": "it", "label": "Italian"},
    {"code": "pt", "label": "Portuguese"},
    {"code": "pl", "label": "Polish"},
    {"code": "ru", "label": "Russian"},
    {"code": "ja", "label": "Japanese"},
    {"code": "ko", "label": "Korean"},
    {"code": "zh", "label": "Chinese"},
]

CAMO_NAMES = [
    "Gold Camo", "Diamond Camo", "Glacial Frost", "Oil Slick", "Nebula Shroud",
    "Liquid Midnight", "Icy Stellar", "Galaxy Stars", "Blood Camo", "Enchanted Emerald",
    "Orion's Veil", "Stellar Eclipse", "Deep Depth", "Yellow Maelstrom", "Astral Red Storm",
    "Green Aurora", "White Cosmos", "Andromeda Drift", "Acidic Radiance", "Galactic Amethyst",
    "Electralized Diamonds"
]
