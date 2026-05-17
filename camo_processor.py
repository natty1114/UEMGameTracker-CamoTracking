"""Camo Matrix data processing for BO3 Tracker."""

import os

from app_paths import get_base_path
from asset_helpers import get_camo_image_src
from file_utils import load_json
from game_data import CAMO_DB_FILE, CAMO_NAMES


CAMO_ICON_CACHE = None


def process_camo_data(user_json_path, starred_list=None):
    global CAMO_ICON_CACHE

    master_path = os.path.join(get_base_path(), CAMO_DB_FILE)
    if not os.path.exists(master_path):
        return {"error": "Database file 'custom_camos.json' not found."}

    master_list = load_json(master_path)
    if not master_list:
        return {"error": "Database loaded but contains 0 weapons."}

    user_progress = {}
    username = "GUEST"

    if user_json_path and os.path.exists(user_json_path):
        user_data = load_json(user_json_path)
        username = user_data.get("username", "Unknown")
        user_progress = user_data.get("progress", {})

    starred_set = set(str(item) for item in (starred_list or []))

    if CAMO_ICON_CACHE is None:
        CAMO_ICON_CACHE = []
        for i in range(len(CAMO_NAMES)):
            img_data = get_camo_image_src(i + 1)
            CAMO_ICON_CACHE.append(img_data)

    grouped_data = {}

    for weapon in master_list:
        map_name = weapon.get("map", "Unknown Sector")
        if not map_name:
            map_name = "Unknown Sector"

        if map_name not in grouped_data:
            grouped_data[map_name] = {"weapons": [], "total_levels": 0, "current_levels": 0}

        w_id = str(weapon.get("id"))
        val = user_progress.get(w_id, user_progress.get(int(w_id), 0))

        max_val = 20
        current_val = int(val)

        grouped_data[map_name]["total_levels"] += max_val
        grouped_data[map_name]["current_levels"] += current_val

        camo_name = CAMO_NAMES[current_val] if current_val < len(CAMO_NAMES) else "Unknown Camo"

        weapon_entry = {
            "id": w_id,
            "name": str(weapon.get("name", "Unknown") or "Unknown"),
            "type": str(weapon.get("type", "Weapon") or "Weapon"),
            "packed": str(weapon.get("packedName", "")),
            "gametype": str(weapon.get("GameType", "")),
            "camo_name": camo_name,
            "camo_val": current_val,
            "is_starred": w_id in starred_set,
        }
        grouped_data[map_name]["weapons"].append(weapon_entry)

    for map_key in grouped_data:
        grouped_data[map_key]["weapons"].sort(key=lambda x: (x["type"], x["name"]))

    return {
        "username": username,
        "camo_icons": CAMO_ICON_CACHE,
        "camo_names": CAMO_NAMES,
        "maps": grouped_data,
        "weapon_count": len(master_list),
    }
