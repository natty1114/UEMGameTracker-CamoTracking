"""Map weapon discovery for BO3 Tracker."""
import os
import time

from app_paths import get_runtime_path
from game_data import MAP_WEAPONS_FILE, UEM_BASE_WEAPONS_FILE, EXPLOSIVES_FILE
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


def _manual_timestamp(weapon):
    try:
        return float(weapon.get("manual_updated_at", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _merge_manual_weapon_update(existing, incoming):
    incoming_ts = _manual_timestamp(incoming)
    if incoming_ts <= 0 or incoming_ts < _manual_timestamp(existing):
        return False

    changed = False
    for field in ("display_name", "upgraded_console_name", "upgraded_display_name", "category"):
        value = incoming.get(field)
        if value not in (None, "", "none") and existing.get(field) != value:
            existing[field] = value
            changed = True

    if existing.get("manual_updated_at") != incoming.get("manual_updated_at"):
        existing["manual_updated_at"] = incoming.get("manual_updated_at")
        changed = True
    return changed


class MapWeaponsManager:
    def __init__(self):
        self.filepath = get_runtime_path(MAP_WEAPONS_FILE)
        self.base_filepath = get_runtime_path(UEM_BASE_WEAPONS_FILE)
        self.explosives_filepath = get_runtime_path(EXPLOSIVES_FILE)
        self._data = {}
        self._base_weapons = {}
        self._base_loaded = False
        self._explosives_data = {}
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
        self._load_base_weapons()
        self._load_explosives()
        if self._strip_old_tracking_fields():
            self.save()
        elif self._backfill_missing_categories():
            self.save()
        if self._strip_base_duplicates():
            self.save()
        return self._data

    def _load_base_weapons(self):
        if self._base_loaded:
            return
        self._base_loaded = True
        self._base_weapons = {}
        data = load_json(self.base_filepath)
        if not isinstance(data, dict):
            return
        for w in data.get("weapons", []):
            if not isinstance(w, dict):
                continue
            cn = str(w.get("console_name", "")).strip()
            if cn:
                w["category"] = normalise_weapon_category(
                    w.get("category", get_weapon_category(cn, w.get("display_name", "")))
                )
                self._base_weapons[cn] = w

    def _load_explosives(self):
        self._explosives_data = {}
        data = load_json(self.explosives_filepath)
        if not isinstance(data, dict):
            return
        self._explosives_data = data

    def _strip_base_duplicates(self):
        """Remove UEM base weapons from per-map entries since they're supplied globally."""
        base_cns = set(self._base_weapons.keys())
        if not base_cns:
            return False
        changed = False
        for entry in self._data.values():
            if not isinstance(entry, dict):
                continue
            before = len(entry.get("weapons", []))
            entry["weapons"] = [w for w in entry.get("weapons", [])
                                if w.get("console_name", "") not in base_cns]
            if len(entry["weapons"]) < before:
                changed = True
        if changed:
            self._dirty = True
        return changed

    def _strip_old_tracking_fields(self):
        changed = False
        for entry in self._data.values():
            if not isinstance(entry, dict):
                continue
            for weapon in entry.get("weapons", []):
                if not isinstance(weapon, dict):
                    continue
                had_old = any(k in weapon for k in ("first_seen", "last_seen", "seen_count"))
                if had_old:
                    weapon.pop("first_seen", None)
                    weapon.pop("last_seen", None)
                    weapon.pop("seen_count", None)
                    changed = True
        if changed:
            self._dirty = True
        return changed

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
        known.update(self._base_weapons.keys())
        for w in self._explosives_data.get(steam_link, {}).get("weapons", []):
            known.add(w.get("console_name", ""))
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
                        }
                        entry["weapons"].append(weapon_entry)
                        known.add(console_name)
                        new_weapons = True
                    else:
                        for existing in entry["weapons"]:
                            if existing["console_name"] == console_name:
                                if _manual_timestamp(existing) <= 0 and existing["display_name"] != display:
                                    existing["display_name"] = display
                                    self._dirty = True
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
        per_map = entry.get("weapons", [])
        known = {w["console_name"] for w in per_map}
        result = list(per_map)
        for cn, w in self._base_weapons.items():
            if cn not in known:
                result.append(w)
        exp_entry = self._explosives_data.get(steam_link, {})
        for w in exp_entry.get("weapons", []):
            cn = w.get("console_name", "")
            if cn and cn not in known:
                result.append(w)
                known.add(cn)
        return result

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
        known.update(self._base_weapons.keys())
        for w in self._explosives_data.get(steam_link, {}).get("weapons", []):
            known.add(w.get("console_name", ""))
        if console_name in known:
            return False
        weapon_entry = {
            "console_name": console_name,
            "display_name": display_name,
            "category": normalise_weapon_category(category) if category else get_weapon_category(console_name, display_name),
            "manual_updated_at": int(time.time()),
        }
        entry["weapons"].append(weapon_entry)
        self._dirty = True
        self.save()
        return True

    def set_weapon_category(self, steam_link, console_name, category, display_name=""):
        if not self._loaded:
            self.load()
        steam_link = normalize_steam_link(steam_link)
        if steam_link not in self._data:
            self._data[steam_link] = {
                "steam_link": steam_link,
                "map_name": "",
                "weapons": [],
            }
        entry = self._data[steam_link]
        console_name = str(console_name or "").strip()
        display_name = str(display_name or console_name).strip()
        if not console_name:
            return False
        category = normalise_weapon_category(category)
        for weapon in entry.get("weapons", []):
            if weapon.get("console_name") == console_name:
                if weapon.get("category") != category:
                    weapon["category"] = category
                    weapon["manual_updated_at"] = int(time.time())
                    self._dirty = True
                    self.save()
                return True
        entry["weapons"].append({
            "console_name": console_name,
            "display_name": display_name or console_name,
            "category": category,
            "manual_updated_at": int(time.time()),
        })
        self._dirty = True
        self.save()
        return True

    def get_weapon_category_for(self, steam_link, console_name, display_name=""):
        if not self._loaded:
            self.load()
        steam_link = normalize_steam_link(steam_link)
        console_name = str(console_name or "").strip()
        entry = self._data.get(steam_link, {})
        # Exact per-map entries are manual overrides for a specific console stat row.
        for weapon in entry.get("weapons", []):
            if str(weapon.get("console_name", "")).strip() == console_name:
                category = str(weapon.get("category", "")).strip()
                if category:
                    return normalise_weapon_category(category)
        # Then check per-map base entries that name an upgraded console variant.
        for weapon in entry.get("weapons", []):
            base_cn = str(weapon.get("console_name", "")).strip()
            up_cn = str(weapon.get("upgraded_console_name", "")).strip()
            if console_name in {base_cn, up_cn, f"{base_cn}_up", f"{base_cn}_upgraded"}:
                category = str(weapon.get("category", "")).strip()
                if category:
                    normalized = normalise_weapon_category(category)
                    if normalized != "other":
                        return normalized
        # Check explosives
        for w in self._explosives_data.get(steam_link, {}).get("weapons", []):
            if w.get("console_name") == console_name:
                cat = str(w.get("category", "")).strip()
                if cat:
                    return normalise_weapon_category(cat)
        # Finally, fall back to global/base weapons.
        base = self._base_weapons.get(console_name)
        if base:
            cat = str(base.get("category", "")).strip()
            if cat:
                normalized = normalise_weapon_category(cat)
                if normalized != "other":
                    return normalized
        return get_weapon_category(console_name, display_name)

    def get_console_category_override(self, console_name):
        if not self._loaded:
            self.load()
        console_name = str(console_name or "").strip()
        if not console_name:
            return ""

        best_category = ""
        best_timestamp = -1
        for entry in self._data.values():
            if not isinstance(entry, dict):
                continue
            for weapon in entry.get("weapons", []):
                if not isinstance(weapon, dict):
                    continue
                base_cn = str(weapon.get("console_name", "")).strip()
                up_cn = str(weapon.get("upgraded_console_name", "")).strip()
                if console_name not in {base_cn, up_cn, f"{base_cn}_up", f"{base_cn}_upgraded"}:
                    continue
                category = normalise_weapon_category(weapon.get("category", ""))
                if not category or category == "other":
                    continue
                timestamp = _manual_timestamp(weapon)
                if timestamp >= best_timestamp:
                    best_timestamp = timestamp
                    best_category = category
        return best_category

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
            base_cns = set(self._base_weapons.keys())
            explosive_cns = set()
            for exp_entry in self._explosives_data.values():
                if isinstance(exp_entry, dict):
                    for w in exp_entry.get("weapons", []):
                        cn = w.get("console_name", "")
                        if cn:
                            explosive_cns.add(cn)
            skip_cns = base_cns | explosive_cns
            for steam_link, entry in remote.items():
                if not isinstance(entry, dict):
                    continue
                if steam_link not in self._data:
                    entry["weapons"] = [w for w in entry.get("weapons", [])
                                        if w.get("console_name", "") not in skip_cns]
                    self._data[steam_link] = entry
                    merged = True
                else:
                    local_entry = self._data[steam_link]
                    if not local_entry.get("map_name") and entry.get("map_name"):
                        local_entry["map_name"] = entry["map_name"]
                        merged = True
                    local_weapons = local_entry.setdefault("weapons", [])
                    local_by_console = {
                        w.get("console_name", ""): w
                        for w in local_weapons
                        if isinstance(w, dict) and w.get("console_name", "")
                    }
                    local_known = set(local_by_console.keys())
                    local_known.update(skip_cns)
                    for w in entry.get("weapons", []):
                        cn = w.get("console_name", "")
                        if not cn:
                            continue
                        if cn in local_by_console:
                            if _merge_manual_weapon_update(local_by_console[cn], w):
                                merged = True
                        elif cn not in local_known:
                            local_weapons.append(w)
                            local_known.add(cn)
                            merged = True
            if merged:
                self._dirty = True
                self.save()
            result["merged"] = merged
        return result

    def push_to_remote(self, url, app_config, preflight_pull=True):
        if not url:
            return {"ok": False, "msg": "Map weapons sync URL is not configured."}
        if not self._loaded:
            self.load()
        if preflight_pull:
            pull_result = self.sync_from_remote(url, app_config, force=True)
            if not pull_result.get("ok"):
                return {
                    "ok": False,
                    "msg": "Map weapons push skipped: could not fetch latest remote data first.",
                    "pull": pull_result,
                }
        return push(url, self._data, app_config)


map_weapons_manager = MapWeaponsManager()
