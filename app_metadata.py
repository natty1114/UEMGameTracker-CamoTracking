"""App metadata loaded from one editable version file."""

import json
import os
import sys


VERSION_FILE = "app_version.json"
DEFAULT_VERSION = "4.6.1"


def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_metadata():
    path = os.path.join(get_base_path(), VERSION_FILE)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        data = {}

    version = str(data.get("version") or DEFAULT_VERSION).strip()
    prompt_version = str(data.get("global_stats_prompt_version") or version).strip()
    remote_management_url = str(data.get("remote_management_url") or "").strip()
    map_weapons_sync_url = str(data.get("map_weapons_sync_url") or "").strip()
    map_challenges_sync_url = str(data.get("map_challenges_sync_url") or "").strip()
    return {
        "version": version,
        "global_stats_prompt_version": prompt_version,
        "remote_management_url": remote_management_url,
        "map_weapons_sync_url": map_weapons_sync_url,
        "map_challenges_sync_url": map_challenges_sync_url,
    }


APP_METADATA = load_metadata()
APP_VERSION = APP_METADATA["version"]
GLOBAL_STATS_PROMPT_VERSION = APP_METADATA["global_stats_prompt_version"]
REMOTE_MANAGEMENT_URL = APP_METADATA["remote_management_url"]
MAP_WEAPONS_SYNC_URL = APP_METADATA["map_weapons_sync_url"]
MAP_CHALLENGES_SYNC_URL = APP_METADATA["map_challenges_sync_url"]
