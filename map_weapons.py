"""Map weapon discovery for BO3 Tracker."""
import os
import time

from app_paths import get_runtime_path
from game_data import MAP_WEAPONS_FILE
from file_utils import load_json, save_json
from sync_map_weapons import fetch, push
from weapon_categories import get_weapon_category, normalise_weapon_category


def normalize_steam_link(value):
    text = str(value or "").strip()
    if not text or text == "0":
        return ""
    if "id=" in text:
        text = text.split("id=", 1)[1]
    for sep in ["&", "?", "/", "#"]:
        if sep in text:
            text = text.split(sep, 1)[0]
    return text.strip()


class MapWeaponsManager:
    def __init__(self):
        self.filepath = get_runtime_path(MAP_WEAPONS_FILE)
        self._data = {}
        self._dirty = False
        self._loaded = False
        self._enabled = True

    def load(self):
        data = load_json(self.filepath)
        if isinstance(data, dict):
            self._data = data
        else:
            self._data = {}
        self._loaded = True
        self._dirty = False
        if self._backfill_missing_categories():
            self.save()
        return self._data

    def _backfill_missing_categories(self):
        changed = False
        for entry in self._data.values():
            if not isinstance(entry, dict):
                continue
            for weapon in entry.get("weapons", []):
                if not isinstance(weapon, dict):
                    continue
                if str(weapon.get("category", "")).strip():
                    continue
                console_name = weapon.get("console_name", "")
                display_name = weapon.get("display_name", "")
                weapon["category"] = get_weapon_category(console_name, display_name)
                changed = True
        if changed:
            self._dirty = True
        return changed

    def save(self):
        if not self._dirty:
            return True
        folder = os.path.dirname(self.filepath)
        if folder:
            os.makedirs(folder, exist_ok=True)
        result = save_json(self.filepath, self._data)
        if result:
            self._dirty = False
        return result

    def discover_from_game(self, game_data):
        if not self._enabled:
            return
        if not game_data:
            return
        if not self._loaded:
            self.load()

        game = game_data.get('game') or game_data.get('data', {}).get('game', {})
        players = game_data.get('players') or game_data.get('data', {}).get('players', {})
        map_data = game_data.get('map') or game_data.get('data', {}).get('map', {})
        if not game:
            return

        steam_link = normalize_steam_link(
            game.get("steam_link")
            or game.get("workshop_link")
            or game.get("workshop_url")
            or game.get("workshop_id")
            or game.get("ugc")
        )
        if not steam_link:
            return

        map_name = str(game.get("map_played", game.get("map_name", "Unknown")) or "Unknown")
        now = int(time.time())

        if steam_link not in self._data:
            self._data[steam_link] = {
                "steam_link": steam_link,
                "map_name": map_name,
                "weapons": [],
            }
        elif self._data[steam_link].get("map_name", "") != map_name:
            self._data[steam_link]["map_name"] = map_name

        entry = self._data[steam_link]
        known = {w["console_name"] for w in entry["weapons"]}
        new_weapons = False

        # Primary source: map.loaded_weapons (all weapons on the map)
        loaded = map_data.get("loaded_weapons", {})
        if isinstance(loaded, dict):
            for console_name, w in loaded.items():
                if not isinstance(w, dict):
                    continue
                base_cn = str(w.get("console_name", console_name)).strip()
                base_dn = str(w.get("display_name", "")).strip()
                up_cn = str(w.get("console_name_upgraded", "")).strip()
                up_dn = str(w.get("display_name_upgraded", "")).strip()

                if base_cn and base_cn != "none" and base_cn not in known:
                    weapon_entry = {
                        "console_name": base_cn,
                        "display_name": base_dn or base_cn,
                        "category": get_weapon_category(base_cn, base_dn),
                        "first_seen": now,
                        "last_seen": now,
                        "seen_count": 1,
                        "upgraded_console_name": up_cn if up_cn and up_cn != "none" and up_cn != base_cn else "",
                        "upgraded_display_name": up_dn if up_dn and up_dn != "none" else "",
                    }
                    entry["weapons"].append(weapon_entry)
                    known.add(base_cn)
                    new_weapons = True

            # Fill missing PaP link fields on already-known weapons
            for console_name, w in loaded.items():
                if not isinstance(w, dict):
                    continue
                base_cn = str(w.get("console_name", console_name)).strip()
                up_cn = str(w.get("console_name_upgraded", "")).strip()
                up_dn = str(w.get("display_name_upgraded", "")).strip()
                if not base_cn or base_cn == "none":
                    continue
                for existing in entry["weapons"]:
                    if existing["console_name"] == base_cn and up_cn and up_cn != "none" and not existing.get("upgraded_console_name"):
                        existing["upgraded_console_name"] = up_cn
                        existing["upgraded_display_name"] = up_dn
                        self._dirty = True
                        break

        # Secondary source: player weapon_data (catches anything not in loaded_weapons)
        if players:
            for pid, p in players.items():
                weapons = p.get('top5', p.get('weapon_data', {}))
                if not weapons or not isinstance(weapons, dict):
                    continue
                for console_name, w in weapons.items():
                    if not isinstance(w, dict):
                        continue
                    display = str(w.get('display', 'Unknown'))
                    if display == 'none':
                        continue
                    if console_name not in known:
                        weapon_entry = {
                            "console_name": console_name,
                            "display_name": display,
                            "category": get_weapon_category(console_name, display),
                            "first_seen": now,
                            "last_seen": now,
                            "seen_count": 1,
                        }
                        entry["weapons"].append(weapon_entry)
                        known.add(console_name)
                        new_weapons = True
                    else:
                        for existing in entry["weapons"]:
                            if existing["console_name"] == console_name:
                                existing["last_seen"] = now
                                existing["seen_count"] = existing.get("seen_count", 1) + 1
                                if existing["display_name"] != display:
                                    existing["display_name"] = display
                                category = get_weapon_category(console_name, display)
                                existing_category = str(existing.get("category", "")).strip()
                                if not existing_category:
                                    existing["category"] = category
                                    self._dirty = True
                                break

        if new_weapons:
            self._dirty = True
            self.save()

    def get_weapons(self, steam_link):
        if not self._loaded:
            self.load()
        entry = self._data.get(steam_link, {})
        return entry.get("weapons", [])

    def get_weapons_with_upgraded(self, steam_link):
        weapons = self.get_weapons(steam_link)
        result = []
        for w in weapons:
            entry = dict(w)
            up_cn = entry.get("upgraded_console_name", "")
            if up_cn:
                entry["upgraded"] = [{
                    "console_name": up_cn,
                    "display_name": entry.get("upgraded_display_name", up_cn),
                }]
            result.append(entry)
        return result

    def add_weapon(self, steam_link, console_name, display_name, category=""):
        if not self._loaded:
            self.load()
        if steam_link not in self._data:
            self._data[steam_link] = {
                "steam_link": steam_link,
                "map_name": "",
                "weapons": [],
            }
        entry = self._data[steam_link]
        known = {w["console_name"] for w in entry["weapons"]}
        if console_name in known:
            return False
        now = int(time.time())
        weapon_entry = {
            "console_name": console_name,
            "display_name": display_name,
            "category": normalise_weapon_category(category) if category else get_weapon_category(console_name, display_name),
            "first_seen": now,
            "last_seen": now,
            "seen_count": 1,
        }
        entry["weapons"].append(weapon_entry)
        self._dirty = True
        self.save()
        return True

    def set_weapon_category(self, steam_link, console_name, category):
        if not self._loaded:
            self.load()
        entry = self._data.get(steam_link)
        if not entry:
            return False
        category = normalise_weapon_category(category)
        for weapon in entry.get("weapons", []):
            if weapon.get("console_name") == console_name:
                if weapon.get("category") != category:
                    weapon["category"] = category
                    self._dirty = True
                    self.save()
                return True
        return False

    def get_weapon_category_for(self, steam_link, console_name, display_name=""):
        if not self._loaded:
            self.load()
        entry = self._data.get(normalize_steam_link(steam_link), {})
        console_name = str(console_name or "").strip()
        for weapon in entry.get("weapons", []):
            base_cn = str(weapon.get("console_name", "")).strip()
            up_cn = str(weapon.get("upgraded_console_name", "")).strip()
            if console_name in {base_cn, up_cn, f"{base_cn}_up", f"{base_cn}_upgraded"}:
                category = str(weapon.get("category", "")).strip()
                if category:
                    normalized = normalise_weapon_category(category)
                    if normalized != "other":
                        return normalized
        return get_weapon_category(console_name, display_name)

    def remove_weapon(self, steam_link, console_name):
        if not self._loaded:
            self.load()
        entry = self._data.get(steam_link)
        if not entry:
            return False
        before = len(entry["weapons"])
        entry["weapons"] = [w for w in entry["weapons"] if w["console_name"] != console_name]
        if len(entry["weapons"]) < before:
            self._dirty = True
            self.save()
            return True
        return False

    def set_map_name(self, steam_link, name):
        if not self._loaded:
            self.load()
        if steam_link not in self._data:
            self._data[steam_link] = {
                "steam_link": steam_link,
                "map_name": name,
                "weapons": [],
            }
            self._dirty = True
        elif self._data[steam_link].get("map_name") != name:
            self._data[steam_link]["map_name"] = name
            self._dirty = True
        if self._dirty:
            self.save()

    def get_all_maps(self):
        if not self._loaded:
            self.load()
        return list(self._data.keys())

    def get_map_entry(self, steam_link):
        if not self._loaded:
            self.load()
        return self._data.get(steam_link, {})

    def set_enabled(self, enabled):
        self._enabled = enabled

    @property
    def enabled(self):
        return self._enabled

    def sync_from_remote(self, url, app_config, force=False):
        if not url:
            return {"ok": False, "msg": "Map weapons sync URL is not configured."}
        if not self._loaded:
            self.load()
        result = fetch(url, app_config, force=force)
        if result.get("ok") and result.get("changed") and result.get("data"):
            remote = result["data"]
            merged = False
            for steam_link, entry in remote.items():
                if not isinstance(entry, dict):
                    continue
                if steam_link not in self._data:
                    self._data[steam_link] = entry
                    merged = True
                else:
                    local_entry = self._data[steam_link]
                    if not local_entry.get("map_name") and entry.get("map_name"):
                        local_entry["map_name"] = entry["map_name"]
                        merged = True
                    local_known = {w["console_name"] for w in local_entry.get("weapons", [])}
                    for w in entry.get("weapons", []):
                        cn = w.get("console_name", "")
                        if cn and cn not in local_known:
                            local_entry.setdefault("weapons", []).append(w)
                            local_known.add(cn)
                            merged = True
            if merged:
                self._dirty = True
                self.save()
            result["merged"] = merged
        return result

    def push_to_remote(self, url, app_config):
        if not url:
            return {"ok": False, "msg": "Map weapons sync URL is not configured."}
        if not self._loaded:
            self.load()
        return push(url, self._data, app_config)


map_weapons_manager = MapWeaponsManager()
