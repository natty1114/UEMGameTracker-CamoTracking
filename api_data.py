import glob
import json
import os
import sys
import time
from datetime import datetime

from app_paths import get_runtime_path
from asset_helpers import get_level_icon_src, get_prestige_icon_src, get_tier_icon_src
from best_matches import (
    add_best_match_from_data,
    find_archive_data,
    get_best_matches_with_archive_status,
    remove_best_match_by_id,
    sanitize_game_id,
)
from map_weapons import map_weapons_manager, normalize_steam_link
from match_xp import xp_tracker_instance
from xpm_grapher import xpm_grapher_instance
from weapon_categories import WEAPON_CATEGORY_LABELS, get_weapon_category, normalise_weapon_category
from file_utils import load_json, save_json
from workshop_images import get_workshop_image

_bt = lambda: sys.modules["bo3tracker"]


def safe_int(value, default=0):
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return default


def format_aat_name(value):
    text = str(value or "").replace("\x00", "").strip()
    if not text or text.lower() in ("none", "null", "0"):
        return ""
    for prefix in ("zm_aat_", "aat_", "specialty_"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
            break
    return text.replace("_", " ").replace("-", " ").title()


def clean_weapon_name(value, fallback=""):
    text = str(value if value is not None else fallback).replace("\x00", "").strip()
    return text or str(fallback or "").replace("\x00", "").strip()


class DataAPI:
    # --- Map Index ---
    MAP_DETAIL_SUMMARY_VERSION = 2
    _map_index = None
    _index_file_count = 0
    _map_detail_cache = None
    _map_detail_summary = None
    _detail_summary_index_count = 0

    def _get_combined_weapon_data(self, player):
        if not isinstance(player, dict):
            return {}

        combined = {}
        for source_key in ("weapon_data", "top5"):
            weapons = player.get(source_key, {})
            if not isinstance(weapons, dict):
                continue
            for console_name, weapon in weapons.items():
                if not isinstance(weapon, dict):
                    continue

                key = str(console_name or weapon.get("console_name") or "").strip()
                if not key:
                    key = clean_weapon_name(weapon.get("display", weapon.get("display_name")), "")
                if not key:
                    continue

                existing = combined.setdefault(key, dict(weapon))
                if existing is weapon:
                    existing = dict(weapon)
                    combined[key] = existing

                for field in ("kills", "headshots", "damage"):
                    existing[field] = max(safe_int(existing.get(field)), safe_int(weapon.get(field)))

                for field, value in weapon.items():
                    if existing.get(field) in ("", None, "none", "Unknown"):
                        existing[field] = value

        return combined

    def _ensure_map_index(self, hist_path):
        cache_path = get_runtime_path("map_index_cache.json")
        current_file_count = sum(1 for f in os.listdir(hist_path) if f.startswith("Game_") and f.endswith(".json"))

        if self._map_index is not None and self._index_file_count == current_file_count:
            return self._map_index

        cached = load_json(cache_path)
        if cached and isinstance(cached, dict) and cached.get("_file_count") == current_file_count and cached.get("_version") == 2:
            self._map_index = cached.get("maps", {})
            self._index_file_count = current_file_count
            return self._map_index

        maps = {}
        for f in glob.glob(os.path.join(hist_path, "Game_*.json")):
            try:
                data = load_json(f)
                if not data:
                    continue
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue
                p = list(players.values())[0] if isinstance(players, dict) else None
                if not isinstance(p, dict):
                    continue
                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                file_game_id = os.path.basename(f).replace("Game_", "").replace(".json", "")
                maps.setdefault(map_name, []).append({
                    "path": f,
                    "game_id": file_game_id,
                    "round": safe_int(game.get('rounds_total') or game.get('round') or game.get('current_round')),
                    "time_sec": safe_int(game.get('time_total')),
                    "kills": safe_int(p.get('kills')),
                    "headshots": safe_int(p.get('headshots')),
                    "downs": safe_int(p.get('downs')),
                    "steam_link": self._get_game_workshop_link(game),
                    "mtime": os.path.getmtime(f),
                })
            except Exception:
                pass

        self._map_index = maps
        self._index_file_count = current_file_count
        save_json(cache_path, {"_version": 2, "_file_count": current_file_count, "_build_time": time.time(), "maps": maps})
        return maps

    # --- Camo ---
    def get_camo_content(self, user_path):
        self.last_user_path = user_path
        return _bt().process_camo_data(user_json_path=user_path)

    def sync_custom_camos_now(self):
        result = _bt().sync_custom_camos(_bt().app_config, force=True)
        _bt().app_config["custom_camos_last_message"] = result.get("msg", "Custom camos sync complete.")
        _bt().save_app_config()
        return result

    def toggle_star(self, w_id):
        try:
            starred = list(_bt().app_config.get('starred', []))
            w_id = str(w_id)
            if w_id in starred:
                starred.remove(w_id)
            else:
                if len(starred) >= 3:
                    return {"success": False, "msg": "Maximum of 3 priority weapons allowed."}
                starred.append(w_id)
            _bt().app_config['starred'] = starred
            _bt().save_app_config()
            return {"success": True, "starred": starred}
        except Exception as e:
            return {"success": False, "msg": f"System Error: {str(e)}"}

    def update_camo_progress(self, user_path, weapon_id, new_val):
        if not user_path or not os.path.exists(user_path):
            return False
        self.last_user_path = user_path
        try:
            data = load_json(user_path)
            if 'progress' not in data:
                data['progress'] = {}
            data['progress'][str(weapon_id)] = int(new_val)
            return _bt().save_json(user_path, data)
        except Exception:
            return False

    # --- Live / History Stats ---
    def get_live_stats(self):
        data = _bt().get_live_game_data()
        if not data:
            return None
        return _bt().process_stats(
            data,
            is_live=True,
            overflow_recovery_enabled=_bt().app_config.get('xp_overflow_recovery_enabled', False)
        )

    def _read_history_meta(self, filepath):
        cache = getattr(self, "_history_meta_cache", {})
        mtime = os.path.getmtime(filepath)
        cached = cache.get(filepath)
        if cached and cached.get("_mtime") == mtime:
            return dict(cached)

        fname = os.path.basename(filepath)
        gid = fname.replace("Game_", "").replace(".json", "")
        dt = time.localtime(mtime)
        date_str = time.strftime("%b %d, %Y %I:%M %p", dt)
        date_iso = time.strftime("%Y-%m-%d", dt)

        map_name = "Unknown Map"
        round_num = 0
        match_xp = 0
        player_names = []
        try:
            data = load_json(filepath) or {}
            game = data.get('game') or data.get('data', {}).get('game', {})
            players = data.get('players') or data.get('data', {}).get('players', {})
            archive_game_id = str(game.get('game_id') or gid)

            map_val = game.get('map_played') or game.get('map') or game.get('map_name')
            if map_val:
                map_name = str(map_val).replace('_', ' ').title()

            round_num = safe_int(
                game.get('round')
                or game.get('round_number')
                or game.get('round_num')
                or game.get('current_round')
            )
            if isinstance(players, dict):
                first_player = True
                first_player_id = ""
                for player_id, player in players.items():
                    if not isinstance(player, dict):
                        continue
                    name = player.get("name") or player.get("player_name") or player.get("username")
                    if name:
                        player_names.append(str(name))
                    player_match_xp = safe_int(player.get("match_xp_earned") or player.get("match_xp") or player.get("total_match_xp"))
                    if first_player:
                        first_player_id = str(player_id)
                        match_xp = player_match_xp
                        first_player = False
                    elif match_xp <= 0:
                        match_xp = max(match_xp, player_match_xp)
                    round_num = max(
                        round_num,
                        safe_int(
                            player.get('round')
                            or player.get('round_number')
                            or player.get('round_num')
                            or player.get('current_round')
                        )
                    )
                if match_xp <= 0 and first_player_id:
                    xp_cache = getattr(self, "_match_xp_cache", None)
                    if xp_cache is None:
                        xp_cache = load_json(get_runtime_path("match_xp_cache.json")) or {}
                        self._match_xp_cache = xp_cache
                    match_xp = safe_int(
                        xp_cache.get(archive_game_id, {}).get(first_player_id, {}).get("total_match_xp")
                    )
        except Exception:
            pass

        item = {
            "id": gid,
            "map": map_name,
            "date": date_str,
            "date_iso": date_iso,
            "round": round_num,
            "match_xp": match_xp,
            "players": player_names,
            "_mtime": mtime,
        }
        cache[filepath] = item
        self._history_meta_cache = cache
        return dict(item)

    def _build_history_xp_ranges(self, items):
        values = [int(item.get("match_xp", 0) or 0) for item in items]
        positive_values = [value for value in values if value > 0]
        ranges = []

        if any(value <= 0 for value in values):
            ranges.append({"value": "0-0", "label": "XP not recorded"})

        if not positive_values:
            return ranges

        max_xp = max(positive_values)
        target_bands = 6
        raw_step = max(1, max_xp / target_bands)
        magnitude = 10 ** (len(str(int(raw_step))) - 1)
        step = magnitude
        for multiplier in (1, 2, 5, 10):
            candidate = multiplier * magnitude
            if candidate >= raw_step:
                step = candidate
                break

        band_start = 1
        while band_start <= max_xp:
            band_end = band_start + step - 1
            count = sum(1 for value in positive_values if band_start <= value <= band_end)
            if count:
                ranges.append({
                    "value": f"{band_start}-{band_end}",
                    "label": f"{band_start:,} - {band_end:,} XP",
                })
            band_start += step

        return ranges

    def get_history_list(self, page=1, filters=None):
        import math
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"items": [], "total_pages": 0, "current_page": 1, "total_items": 0, "filtered_items": 0, "maps": [], "xp_ranges": []}

        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        filters = filters if isinstance(filters, dict) else {}
        query = str(filters.get("query") or "").strip().lower()
        map_filter = str(filters.get("map") or "").strip().lower()
        date_from = str(filters.get("date_from") or "").strip()
        date_to = str(filters.get("date_to") or "").strip()
        xp_min = safe_int(filters.get("xp_min"), None)
        xp_max = safe_int(filters.get("xp_max"), None)
        sort_mode = str(filters.get("sort") or "newest").strip().lower()

        items = [self._read_history_meta(f) for f in json_files]
        map_options = sorted({item["map"] for item in items if item.get("map")}, key=str.lower)
        xp_ranges = self._build_history_xp_ranges(items)

        def matches_filter(item):
            if query:
                haystack = " ".join([
                    str(item.get("id", "")),
                    str(item.get("map", "")),
                    " ".join(item.get("players", [])),
                ]).lower()
                if query not in haystack:
                    return False
            if map_filter and str(item.get("map", "")).lower() != map_filter:
                return False
            date_iso = item.get("date_iso", "")
            if date_from and date_iso < date_from:
                return False
            if date_to and date_iso > date_to:
                return False
            match_xp = int(item.get("match_xp", 0) or 0)
            if xp_min is not None and match_xp < xp_min:
                return False
            if xp_max is not None and match_xp > xp_max:
                return False
            return True

        filtered_items = [item for item in items if matches_filter(item)]

        if sort_mode == "oldest":
            filtered_items.sort(key=lambda item: item.get("_mtime", 0))
        elif sort_mode == "map":
            filtered_items.sort(key=lambda item: (str(item.get("map", "")).lower(), -item.get("_mtime", 0)))
        elif sort_mode == "round":
            filtered_items.sort(key=lambda item: (int(item.get("round", 0)), item.get("_mtime", 0)), reverse=True)
        elif sort_mode == "xp":
            filtered_items.sort(key=lambda item: (int(item.get("match_xp", 0)), item.get("_mtime", 0)), reverse=True)
        elif sort_mode == "xp_low":
            filtered_items.sort(key=lambda item: (int(item.get("match_xp", 0)), item.get("_mtime", 0)))
        else:
            filtered_items.sort(key=lambda item: item.get("_mtime", 0), reverse=True)

        items_per_page = 50
        total_items = len(items)
        filtered_count = len(filtered_items)
        total_pages = max(1, math.ceil(filtered_count / items_per_page))

        page = max(1, min(int(page), total_pages))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        results = []
        for item in filtered_items[start_idx:end_idx]:
            clean_item = dict(item)
            clean_item.pop("_mtime", None)
            results.append(clean_item)

        return {
            "items": results,
            "total_pages": total_pages,
            "current_page": page,
            "total_items": total_items,
            "filtered_items": filtered_count,
            "maps": map_options,
            "xp_ranges": xp_ranges,
        }

    def get_history_report(self, game_id):
        hist_path = _bt().app_config.get('history_path')
        target = os.path.join(hist_path, "Game_" + game_id + ".json")
        if not os.path.exists(target):
            return {"status": "ERROR"}
        data = load_json(target)
        return _bt().process_stats(data, is_live=False)

    def remove_history_match(self, game_id):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.isdir(hist_path):
            return {"success": False, "msg": "History folder is not configured."}

        safe_id = sanitize_game_id(game_id)
        if not safe_id:
            return {"success": False, "msg": "Invalid archived match ID."}

        hist_root = os.path.abspath(hist_path)
        target = os.path.abspath(os.path.join(hist_root, f"Game_{safe_id}.json"))
        try:
            if os.path.commonpath([os.path.normcase(hist_root), os.path.normcase(target)]) != os.path.normcase(hist_root):
                return {"success": False, "msg": "Invalid archived match path."}
        except ValueError:
            return {"success": False, "msg": "Invalid archived match path."}

        if not os.path.exists(target):
            return {"success": False, "msg": "Archived match was not found."}

        archive_data = load_json(target) or {}
        game = archive_data.get('game') or archive_data.get('data', {}).get('game', {})
        archive_game_id = str(game.get('game_id') or safe_id)

        try:
            os.remove(target)
        except OSError as exc:
            return {"success": False, "msg": f"Could not remove archived match: {exc}"}

        cache = getattr(self, "_history_meta_cache", {})
        if isinstance(cache, dict):
            cache.pop(target, None)
            self._history_meta_cache = cache
        self._map_index = None
        self._map_detail_cache = None
        self._map_detail_summary = None
        self._detail_summary_index_count = 0

        xp_cache_path = get_runtime_path("match_xp_cache.json")
        xp_cache = load_json(xp_cache_path) or {}
        if isinstance(xp_cache, dict):
            removed_any = False
            for key in {safe_id, archive_game_id}:
                if key in xp_cache:
                    xp_cache.pop(key, None)
                    removed_any = True
            if removed_any:
                save_json(xp_cache_path, xp_cache)
                self._match_xp_cache = xp_cache

        best_match_removed = False
        for key in {safe_id, archive_game_id}:
            result = remove_best_match_by_id(key)
            if result.get("success"):
                best_match_removed = True

        return {
            "success": True,
            "msg": "Archived match removed.",
            "id": safe_id,
            "best_match_removed": best_match_removed,
        }

    def get_lifetime_stats(self):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"error": "No History Folder Found"}

        totals = {
            "kills": 0, "headshots": 0, "downs": 0, "rounds": 0,
            "time_sec": 0, "matches": 0, "doors": 0, "gums": 0,
            "box": 0, "pts": 0,
            "shots_fired": 0, "shots_hit": 0, "shots_missed": 0,
        }
        weapon_stats = {}
        map_high_rounds = {}
        map_play_counts = {}
        map_play_times = {}

        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))

        for f in json_files:
            try:
                data = load_json(f)
                if not data:
                    continue

                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue

                p = list(players.values())[0]

                totals["matches"] += 1
                totals["kills"] += int(p.get('kills', 0))
                totals["headshots"] += int(p.get('headshots', 0))
                totals["downs"] += int(p.get('downs', 0))
                totals["rounds"] += int(game.get('rounds_total', 0))
                totals["time_sec"] += int(game.get('time_total', 0))
                totals["doors"] += int(p.get('doors_purchased', 0))
                totals["gums"] += int(p.get('gobblegums_used', 0))
                totals["box"] += int(p.get('true_match_box', 0))
                totals["pts"] += int(p.get('true_match_points', 0))

                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                rnd = int(game.get('rounds_total', 0))
                if map_name not in map_high_rounds or rnd > map_high_rounds[map_name]:
                    map_high_rounds[map_name] = rnd

                if map_name not in map_play_counts:
                    map_play_counts[map_name] = 0
                map_play_counts[map_name] += 1

                if map_name not in map_play_times:
                    map_play_times[map_name] = 0
                map_play_times[map_name] += int(game.get('time_total', 0))

                w_data = self._get_combined_weapon_data(p)
                for k, w in w_data.items():
                    name = clean_weapon_name(w.get('display', w.get('display_name')), k)
                    if name.lower() in ("none", "unknown"):
                        continue
                    if name not in weapon_stats:
                        weapon_stats[name] = 0
                    weapon_stats[name] += safe_int(w.get('kills'))

            except Exception:
                pass

        try:
            live_data = _bt().get_live_game_data()
            if live_data:
                live_players = live_data.get('players') or live_data.get('data', {}).get('players', {})
                if live_players:
                    lp = list(live_players.values())[0]
                    totals["doors"] = int(lp.get('doors_purchased', 0))
                    totals["gums"] = int(lp.get('gobblegums_used', 0))
                    totals["pts"] = int(lp.get('total_points', lp.get('player_points_gained', 0)))
                    shots_hit = safe_int(lp.get('shots_hit'))
                    shots_missed = safe_int(lp.get('shots_missed'))
                    shots_fired = safe_int(lp.get('shots_fired'))
                    if shots_fired <= 0 and (shots_hit > 0 or shots_missed > 0):
                        shots_fired = shots_hit + shots_missed
                    totals["shots_fired"] = shots_fired
                    totals["shots_hit"] = shots_hit
                    totals["shots_missed"] = shots_missed
        except Exception:
            pass

        hs_ratio = 0
        if totals["kills"] > 0:
            hs_ratio = round((totals["headshots"] / totals["kills"]) * 100, 1)

        shot_accuracy = None
        if totals["shots_fired"] > 0:
            shot_accuracy = round((totals["shots_hit"] / totals["shots_fired"]) * 100, 1)

        top_weapons = []
        if weapon_stats:
            sorted_w = sorted(weapon_stats.items(), key=lambda item: item[1], reverse=True)
            for w_name, w_kills in sorted_w[:3]:
                top_weapons.append({"name": w_name, "kills": w_kills})

        if not top_weapons:
            top_weapons = [{"name": "None", "kills": 0}]

        kpd = totals["kills"]
        if totals["downs"] > 0:
            kpd = round(totals["kills"] / totals["downs"], 2)

        sorted_played = sorted(map_play_counts.items(), key=lambda item: item[1], reverse=True)
        top_played = [{"name": m[0], "count": m[1]} for m in sorted_played[:15]]

        sorted_played_time = sorted(map_play_times.items(), key=lambda item: item[1], reverse=True)
        top_played_time = []
        for mt in sorted_played_time[:15]:
            map_min, map_sec = divmod(mt[1], 60)
            map_h, map_min = divmod(map_min, 60)
            top_played_time.append({"name": mt[0], "time_str": f"{map_h}h {map_min}m"})

        total_m, total_s = divmod(totals["time_sec"], 60)
        total_h, total_m = divmod(total_m, 60)

        return {
            "totals": totals,
            "ratios": {"hs_percent": hs_ratio, "kpd": kpd, "shot_accuracy": shot_accuracy},
            "time_str": f"{total_h}h {total_m}m",
            "best_map_rounds": map_high_rounds,
            "favorite_weapons": top_weapons,
            "top_played_maps": top_played,
            "top_played_maps_time": top_played_time,
        }

    def _get_archived_match_xp(self, game_id, player_id, player):
        if isinstance(player, dict):
            direct_xp = safe_int(
                player.get("match_xp_earned")
                or player.get("match_xp")
                or player.get("total_match_xp")
            )
            if direct_xp > 0:
                return direct_xp

        xp_cache = getattr(self, "_match_xp_cache", None)
        if xp_cache is None:
            xp_cache = load_json(get_runtime_path("match_xp_cache.json")) or {}
            self._match_xp_cache = xp_cache
        return safe_int(
            xp_cache.get(str(game_id), {}).get(str(player_id), {}).get("total_match_xp")
        )

    def _get_game_workshop_link(self, game):
        return normalize_steam_link(
            game.get("steam_link")
            or game.get("workshop_link")
            or game.get("workshop_url")
            or game.get("workshop_id")
            or game.get("ugc")
            or ""
        )

    def get_map_selection(self, player_id="0"):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"error": "No History Folder Found", "maps": []}

        index = self._ensure_map_index(hist_path)
        include_images = _bt().app_config.get('workshop_images_enabled', True)

        rows = []
        for map_name, entries in index.items():
            best_round = 0
            total_time = 0
            last_ts = 0
            last_gid = ""
            link = ""
            for entry in entries:
                if entry["round"] > best_round:
                    best_round = entry["round"]
                total_time += entry["time_sec"]
                if entry["mtime"] >= last_ts:
                    last_ts = entry["mtime"]
                    last_gid = entry["game_id"]
                if entry["steam_link"] and not link:
                    link = entry["steam_link"]

            total_h, rem = divmod(int(total_time or 0), 3600)
            total_m = rem // 60
            image = None
            if include_images and link:
                image = get_workshop_image(link)
            rows.append({
                "name": map_name,
                "matches": len(entries),
                "best_round": best_round,
                "time_sec": total_time,
                "time_str": f"{total_h}h {total_m}m",
                "last_played_ts": int(last_ts),
                "last_played": time.strftime("%b %d, %Y", time.localtime(last_ts)) if last_ts else "",
                "last_game_id": last_gid,
                "steam_link": link,
                "workshop_image": image,
            })

        rows.sort(key=lambda item: (int(item.get("matches", 0)), int(item.get("best_round", 0))), reverse=True)
        return {"maps": rows, "total": len(rows)}

    def refresh_map_selection(self, player_id="0"):
        self._map_index = None
        self._index_file_count = 0
        self._map_detail_cache = None
        self._map_detail_summary = None
        self._detail_summary_index_count = 0
        for name in ["map_index_cache.json", "map_detail_summary.json"]:
            try:
                p = get_runtime_path(name)
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        return self.get_map_selection(player_id)

    def _compute_map_detail(self, map_name, entries, player_id="0"):
        entries = sorted(entries, key=lambda e: e["mtime"])
        totals = {
            "matches": 0, "rounds": 0, "time_sec": 0,
            "kills": 0, "headshots": 0, "downs": 0,
            "match_xp": 0, "xp_recorded_matches": 0,
        }
        best = {"round": 0, "xp": 0, "kpm": 0, "xpm": 0, "round_game_id": "", "xp_game_id": ""}
        weapons = {}
        steam_link = ""
        workshop_image = None
        all_matches = []

        for entry in entries:
            try:
                data = load_json(entry["path"])
                if not data:
                    continue
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue

                actual_player_id = player_id
                player = players.get(player_id) if isinstance(players, dict) else None
                if not isinstance(player, dict) and player_id == "0" and isinstance(players, dict) and players:
                    actual_player_id, player = next(iter(players.items()))
                if not isinstance(player, dict):
                    continue
                actual_player_id = str(actual_player_id)

                game_id = entry["game_id"]
                round_num = entry["round"]
                duration_seconds = entry["time_sec"]
                kills = entry["kills"]
                headshots = entry["headshots"]
                downs = entry["downs"]
                match_xp = self._get_archived_match_xp(game_id, actual_player_id, player)
                minutes = duration_seconds / 60.0 if duration_seconds > 0 else 0
                kpm = round(kills / minutes, 1) if minutes > 0 else 0
                xpm = int(match_xp / minutes) if minutes > 0 and match_xp > 0 else 0
                match_date = time.strftime("%b %d, %Y %I:%M %p", time.localtime(entry["mtime"]))

                if entry["steam_link"] and not steam_link:
                    steam_link = entry["steam_link"]
                    if _bt().app_config.get('workshop_images_enabled', True):
                        workshop_image = get_workshop_image(steam_link)

                totals["matches"] += 1
                totals["rounds"] += round_num
                totals["time_sec"] += duration_seconds
                totals["kills"] += kills
                totals["headshots"] += headshots
                totals["downs"] += downs
                totals["match_xp"] += match_xp
                if match_xp > 0:
                    totals["xp_recorded_matches"] += 1

                if round_num > best["round"]:
                    best["round"] = round_num
                    best["round_game_id"] = game_id
                if match_xp > best["xp"]:
                    best["xp"] = match_xp
                    best["xp_game_id"] = game_id
                best["kpm"] = max(best["kpm"], kpm)
                best["xpm"] = max(best["xpm"], xpm)

                weapons_data = self._get_combined_weapon_data(player)
                if isinstance(weapons_data, dict):
                    for console_name, weapon in weapons_data.items():
                        if not isinstance(weapon, dict):
                            continue
                        display = clean_weapon_name(weapon.get('display', weapon.get('display_name')), console_name)
                        if display.lower() in ("none", "unknown"):
                            continue
                        weapon_kills = safe_int(weapon.get('kills'))
                        weapon_headshots = safe_int(weapon.get('headshots'))
                        try:
                            raw_damage = int(float(weapon.get('damage', 0) or 0))
                        except Exception:
                            raw_damage = 0
                        damage = _bt().damage_tracker.get_real_damage(game_id, actual_player_id, str(console_name), raw_damage)
                        wentry = weapons.setdefault(display, {
                            "name": display,
                            "console_name": str(console_name),
                            "kills": 0,
                            "headshots": 0,
                            "damage": 0,
                            "matches": 0,
                            "best_round": 0,
                        })
                        wentry["kills"] += weapon_kills
                        wentry["headshots"] += weapon_headshots
                        wentry["damage"] += damage
                        wentry["matches"] += 1
                        wentry["best_round"] = max(wentry["best_round"], round_num)

                all_matches.append({
                    "game_id": game_id,
                    "_mtime": entry["mtime"],
                    "date": match_date,
                    "round": round_num,
                    "duration_seconds": duration_seconds,
                    "time": f"{duration_seconds // 3600}h {(duration_seconds % 3600) // 60}m" if duration_seconds >= 3600 else f"{duration_seconds // 60}m {duration_seconds % 60}s",
                    "kills": kills,
                    "headshots": headshots,
                    "headshot_pct": round((headshots / kills) * 100, 1) if kills > 0 else 0,
                    "downs": downs,
                    "match_xp": match_xp,
                    "kpm": kpm,
                    "xpm": xpm,
                })
            except Exception:
                pass

        if totals["matches"] <= 0:
            return None

        total_minutes = totals["time_sec"] / 60.0 if totals["time_sec"] > 0 else 0
        avg_round = round(totals["rounds"] / totals["matches"], 1) if totals["matches"] else 0
        avg_xp = int(totals["match_xp"] / totals["xp_recorded_matches"]) if totals["xp_recorded_matches"] else 0
        avg_kpm = round(totals["kills"] / total_minutes, 1) if total_minutes > 0 else 0
        avg_xpm = int(totals["match_xp"] / total_minutes) if total_minutes > 0 and totals["match_xp"] > 0 else 0
        total_h, rem = divmod(totals["time_sec"], 3600)
        total_m = rem // 60

        weapon_rows = []
        for wentry in weapons.values():
            wkills = safe_int(wentry.get("kills"))
            wheadshots = safe_int(wentry.get("headshots"))
            wentry["headshot_pct"] = round((wheadshots / wkills) * 100, 1) if wkills > 0 else 0
            weapon_rows.append(wentry)
        weapon_rows.sort(key=lambda item: (int(item.get("kills", 0)), int(item.get("damage", 0))), reverse=True)

        all_matches.sort(key=lambda m: m["_mtime"])

        return {
            "all_matches": all_matches,
            "weapon_rows": weapon_rows,
            "totals": totals,
            "best": best,
            "summary": {
                "matches": totals["matches"],
                "highest_round": best["round"],
                "average_round": avg_round,
                "best_xp": best["xp"],
                "average_xp": avg_xp,
                "kpm": avg_kpm,
                "xpm": avg_xpm,
                "best_kpm": best["kpm"],
                "best_xpm": best["xpm"],
                "headshot_pct": round((totals["headshots"] / totals["kills"]) * 100, 1) if totals["kills"] > 0 else 0,
                "xp_recorded_matches": totals["xp_recorded_matches"],
            },
            "steam_link": steam_link,
            "workshop_image": workshop_image,
            "time_str": f"{total_h}h {total_m}m",
            "_entry_count": len(all_matches),
        }

    def _ensure_map_detail_summary(self, hist_path):
        if self._map_detail_summary is not None and self._detail_summary_index_count == self._index_file_count:
            return self._map_detail_summary

        summary_path = get_runtime_path("map_detail_summary.json")
        cached = load_json(summary_path)
        maps_data = {}

        if cached and isinstance(cached, dict) and cached.get("_version") == self.MAP_DETAIL_SUMMARY_VERSION:
            maps_data = cached.get("maps", {}) or {}
            cached_fc = cached.get("_file_count", 0)

            if cached_fc == self._index_file_count and self._map_index is not None:
                changed = False
                for map_name, entries in self._map_index.items():
                    cached_entry = maps_data.get(map_name)
                    cached_count = cached_entry.get("_entry_count", -1) if isinstance(cached_entry, dict) else -1
                    if cached_count != len(entries) and len(entries) > 0:
                        computed = self._compute_map_detail(map_name, entries)
                        if computed:
                            maps_data[map_name] = computed
                            changed = True
                if changed:
                    maps_data = {k: v for k, v in maps_data.items() if k in self._map_index}
                    save_json(summary_path, {
                        "_version": self.MAP_DETAIL_SUMMARY_VERSION,
                        "_file_count": self._index_file_count,
                        "maps": maps_data,
                    })
                self._map_detail_summary = maps_data
                self._detail_summary_index_count = self._index_file_count
                return maps_data

        self._map_detail_summary = {}
        self._detail_summary_index_count = 0
        return {}

    def get_map_detail(self, map_name, player_id="0", page=1, per_page=25):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"error": "No History Folder Found"}

        target_name = str(map_name or "").replace("_", " ").title().strip()
        if not target_name:
            return {"error": "Map name is required."}

        player_id = str(player_id or "0")
        page = max(1, int(page))
        per_page = max(1, min(100, int(per_page)))

        if self._map_detail_cache is None:
            self._map_detail_cache = {}

        if target_name in self._map_detail_cache:
            cached = self._map_detail_cache[target_name]
        else:
            index = self._ensure_map_index(hist_path)
            entries = index.get(target_name, [])
            if not entries:
                return {"error": "No archived matches found for this map.", "map": target_name}

            summary_data = self._ensure_map_detail_summary(hist_path)
            map_summary = summary_data.get(target_name) if isinstance(summary_data, dict) else None

            if map_summary and map_summary.get("_entry_count") == len(entries):
                cached = map_summary
            else:
                computed = self._compute_map_detail(target_name, entries, player_id)
                if not computed:
                    return {"error": "No archived matches found for this map.", "map": target_name}
                summary_data[target_name] = computed
                save_json(get_runtime_path("map_detail_summary.json"), {
                    "_version": self.MAP_DETAIL_SUMMARY_VERSION,
                    "_file_count": self._index_file_count,
                    "maps": {k: v for k, v in summary_data.items()},
                })
                self._map_detail_summary = summary_data
                cached = computed

            self._map_detail_cache[target_name] = cached

        all_matches = cached["all_matches"]
        weapon_rows = cached["weapon_rows"]
        totals = cached["totals"]
        best = cached["best"]
        summary = cached["summary"]
        steam_link = cached["steam_link"]
        workshop_image = cached["workshop_image"]
        time_str = cached["time_str"]

        total = len(all_matches)
        start = (page - 1) * per_page
        end = start + per_page
        page_matches = all_matches[start:end] if start < total else []
        has_more = end < total

        return {
            "map": target_name,
            "steam_link": steam_link,
            "workshop_image": workshop_image,
            "totals": totals,
            "time_str": time_str,
            "summary": summary,
            "best": best,
            "weapons": weapon_rows[:12],
            "recent_matches": page_matches,
            "round_history": [{"label": str(i + 1), "round": row["round"], "xp": row["match_xp"]} for i, row in enumerate(page_matches)],
            "page": page,
            "per_page": per_page,
            "total_matches": total,
            "has_more": has_more,
        }

    def get_player_weapon_usage(self):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"error": "No History Folder Found", "weapons": []}

        map_weapons_manager.load()
        weapon_stats = {}
        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime)

        for f in json_files:
            try:
                data = load_json(f)
                if not data:
                    continue
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue

                p = players.get('0') or list(players.values())[0]
                game_id = str(game.get('game_id', os.path.basename(f)))
                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                round_num = int(game.get('rounds_total', 0) or 0)
                weapons = self._get_combined_weapon_data(p)
                if not isinstance(weapons, dict):
                    continue

                for console_name, weapon in weapons.items():
                    if not isinstance(weapon, dict):
                        continue
                    display = clean_weapon_name(weapon.get('display', weapon.get('display_name')), console_name)
                    if display.lower() in ("none", "unknown"):
                        continue
                    key = display
                    steam_link = str(
                        game.get("steam_link")
                        or game.get("workshop_link")
                        or game.get("workshop_url")
                        or game.get("workshop_id")
                        or game.get("ugc")
                        or ""
                    )
                    map_category = map_weapons_manager.get_weapon_category_for(steam_link, console_name, display)
                    console_category = map_weapons_manager.get_console_category_override(console_name)
                    category = normalise_weapon_category(
                        console_category
                        or map_category
                        or weapon.get("category")
                        or get_weapon_category(console_name, display)
                    )
                    if key not in weapon_stats:
                        weapon_stats[key] = {
                            "name": display,
                            "console_name": str(console_name),
                            "category": category,
                            "kills": 0,
                            "headshots": 0,
                            "damage": 0,
                            "matches": 0,
                            "best_round": 0,
                            "best_map": "",
                            "pap_uses": 0,
                            "pap_name": "",
                        }

                    try:
                        kills = int(weapon.get('kills', 0) or 0)
                    except Exception:
                        kills = 0
                    try:
                        headshots = int(weapon.get('headshots', 0) or 0)
                    except Exception:
                        headshots = 0
                    try:
                        raw_damage = int(float(weapon.get('damage', 0) or 0))
                    except Exception:
                        raw_damage = 0

                    corrected_damage = _bt().damage_tracker.get_real_damage(game_id, "0", console_name, raw_damage)
                    entry = weapon_stats[key]
                    if console_category and console_category != "other":
                        entry["category"] = console_category
                    elif entry.get("category") == "other" and category != "other":
                        entry["category"] = category
                    entry["kills"] += kills
                    entry["headshots"] += headshots
                    entry["damage"] += corrected_damage
                    entry["matches"] += 1

                    is_pap = (
                        safe_int(weapon.get('enchant')) > 0
                        or
                        int(weapon.get('repack_level', 0) or 0) > 0
                        or (weapon.get('display_name_upgraded') and weapon.get('display_name_upgraded') != "none")
                    )
                    if is_pap:
                        entry["pap_uses"] += 1
                        raw_pap = weapon.get('display_name_upgraded', '') or ''
                        if raw_pap and raw_pap.lower() not in ("", "none", "unknown"):
                            entry["pap_name"] = raw_pap
                        elif not entry.get("pap_name"):
                            for mp in map_weapons_manager._data.values():
                                for mw in mp.get("weapons", []):
                                    if mw.get("console_name") == console_name:
                                        up = mw.get("upgraded_display_name", "")
                                        if up:
                                            entry["pap_name"] = up
                                        break
                                if entry.get("pap_name"):
                                    break
                    if round_num > entry["best_round"]:
                        entry["best_round"] = round_num
                        entry["best_map"] = map_name
            except Exception:
                pass

        weapons = []
        for entry in weapon_stats.values():
            kills = int(entry.get("kills", 0))
            headshots = int(entry.get("headshots", 0))
            entry["headshot_pct"] = round((headshots / kills) * 100, 1) if kills > 0 else 0
            weapons.append(entry)

        weapons.sort(key=lambda item: (int(item.get("kills", 0)), int(item.get("damage", 0))), reverse=True)
        category_totals = {}
        for weapon in weapons:
            category = normalise_weapon_category(weapon.get("category", "other"))
            kills = int(weapon.get("kills", 0) or 0)
            damage = int(weapon.get("damage", 0) or 0)
            if kills <= 0 and damage <= 0:
                continue
            if category not in category_totals:
                category_totals[category] = {
                    "category": category,
                    "label": WEAPON_CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
                    "kills": 0,
                    "damage": 0,
                    "weapon_count": 0,
                }
            category_totals[category]["kills"] += kills
            category_totals[category]["damage"] += damage
            category_totals[category]["weapon_count"] += 1
        category_breakdown = sorted(
            category_totals.values(),
            key=lambda item: int(item.get("kills", 0)),
            reverse=True,
        )
        return {
            "weapons": weapons,
            "category_breakdown": category_breakdown,
            "totals": {
                "weapon_count": len(weapons),
                "kills": sum(int(w.get("kills", 0)) for w in weapons),
                "headshots": sum(int(w.get("headshots", 0)) for w in weapons),
                "damage": sum(int(w.get("damage", 0)) for w in weapons),
            },
        }

    def get_weapon_detail(self, weapon_name, player_id="0"):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"error": "No History Folder Found"}

        target_name = str(weapon_name or "").strip()
        if not target_name:
            return {"error": "Weapon name is required."}

        player_id = str(player_id or "0")
        matches = []
        map_totals = {}
        totals = {
            "kills": 0,
            "headshots": 0,
            "damage": 0,
            "matches": 0,
            "pap_uses": 0,
            "aat_uses": 0,
        }
        aat_counts = {}
        best_match = None
        category = "other"
        console_name_result = ""

        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime)

        for f in json_files:
            try:
                data = load_json(f)
                if not data:
                    continue

                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue

                actual_player_id = player_id
                p = players.get(player_id)
                if not isinstance(p, dict) and player_id == "0" and players:
                    actual_player_id, p = next(iter(players.items()))
                if not isinstance(p, dict):
                    continue
                actual_player_id = str(actual_player_id)

                weapons = self._get_combined_weapon_data(p)
                if not isinstance(weapons, dict):
                    continue

                game_id = str(game.get('game_id', os.path.basename(f)))
                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                round_num = int(game.get('rounds_total', 0) or 0)
                duration_seconds = int(game.get('time_total', 0) or 0)
                match_date = time.strftime("%b %d, %Y %I:%M %p", time.localtime(os.path.getmtime(f)))

                matched_weapon = None
                matched_console_name = ""
                for console_name, weapon in weapons.items():
                    if not isinstance(weapon, dict):
                        continue
                    display = clean_weapon_name(weapon.get('display', weapon.get('display_name')), console_name)
                    if display == target_name or str(console_name).strip() == target_name:
                        matched_weapon = weapon
                        matched_console_name = str(console_name)
                        break

                if not matched_weapon:
                    continue

                kills = safe_int(matched_weapon.get('kills'))
                headshots = safe_int(matched_weapon.get('headshots'))
                try:
                    raw_damage = int(float(matched_weapon.get('damage', 0) or 0))
                except Exception:
                    raw_damage = 0
                damage = _bt().damage_tracker.get_real_damage(game_id, actual_player_id, matched_console_name, raw_damage)
                is_pap = (
                    safe_int(matched_weapon.get('enchant')) > 0
                    or
                    int(matched_weapon.get('repack_level', 0) or 0) > 0
                    or (matched_weapon.get('display_name_upgraded') and matched_weapon.get('display_name_upgraded') != "none")
                )
                aat_name = format_aat_name(
                    matched_weapon.get("currentAAT")
                    or matched_weapon.get("current_aat")
                    or matched_weapon.get("aat")
                )

                steam_link = str(
                    game.get("steam_link")
                    or game.get("workshop_link")
                    or game.get("workshop_url")
                    or game.get("workshop_id")
                    or game.get("ugc")
                    or ""
                )
                map_category = map_weapons_manager.get_weapon_category_for(steam_link, matched_console_name, target_name)
                console_category = map_weapons_manager.get_console_category_override(matched_console_name)
                resolved_category = normalise_weapon_category(
                    console_category
                    or map_category
                    or matched_weapon.get("category")
                    or get_weapon_category(matched_console_name, target_name)
                )
                if console_category and console_category != "other":
                    category = console_category
                elif category == "other" and resolved_category != "other":
                    category = resolved_category
                if not console_name_result and matched_console_name:
                    console_name_result = matched_console_name

                pap_name = matched_weapon.get('display_name_upgraded', '') or ''
                if pap_name.lower() in ("", "none", "unknown", "0"):
                    pap_name = ""
                if not pap_name and matched_console_name:
                    for mp in map_weapons_manager._data.values():
                        for mw in mp.get("weapons", []):
                            if mw.get("console_name") == matched_console_name:
                                up = mw.get("upgraded_display_name", "")
                                if up:
                                    pap_name = up
                                break
                        if pap_name:
                            break
                row = {
                    "game_id": game_id,
                    "map": map_name,
                    "date": match_date,
                    "round": round_num,
                    "duration_seconds": duration_seconds,
                    "kills": kills,
                    "headshots": headshots,
                    "headshot_pct": round((headshots / kills) * 100, 1) if kills > 0 else 0,
                    "damage": damage,
                    "pap": bool(is_pap),
                    "pap_name": pap_name,
                    "aat": aat_name,
                }
                matches.append(row)

                totals["kills"] += kills
                totals["headshots"] += headshots
                totals["damage"] += damage
                totals["matches"] += 1
                if is_pap:
                    totals["pap_uses"] += 1
                if aat_name:
                    totals["aat_uses"] += 1
                    aat_counts[aat_name] = aat_counts.get(aat_name, 0) + 1

                if map_name not in map_totals:
                    map_totals[map_name] = {
                        "map": map_name,
                        "matches": 0,
                        "kills": 0,
                        "headshots": 0,
                        "damage": 0,
                        "best_round": 0,
                    }
                map_entry = map_totals[map_name]
                map_entry["matches"] += 1
                map_entry["kills"] += kills
                map_entry["headshots"] += headshots
                map_entry["damage"] += damage
                if round_num > map_entry["best_round"]:
                    map_entry["best_round"] = round_num

                if not best_match or (kills, damage, round_num) > (
                    int(best_match.get("kills", 0)),
                    int(best_match.get("damage", 0)),
                    int(best_match.get("round", 0)),
                ):
                    best_match = row
            except Exception:
                pass

        totals["headshot_pct"] = round((totals["headshots"] / totals["kills"]) * 100, 1) if totals["kills"] > 0 else 0
        aat_breakdown = [
            {"name": name, "count": count}
            for name, count in sorted(aat_counts.items(), key=lambda item: item[1], reverse=True)
        ]
        totals["top_aat"] = aat_breakdown[0]["name"] if aat_breakdown else ""
        map_breakdown = sorted(
            map_totals.values(),
            key=lambda item: (int(item.get("kills", 0)), int(item.get("damage", 0))),
            reverse=True,
        )
        pap_names = [m.get("pap_name", "") for m in matches if m.get("pap_name")]
        most_common_pap = max(set(pap_names), key=pap_names.count) if pap_names else ""
        return {
            "weapon": {
                "name": target_name,
                "console_name": console_name_result,
                "category": category,
                "pap_name": most_common_pap,
            },
            "totals": totals,
            "best_match": best_match,
            "matches": matches,
            "map_breakdown": map_breakdown,
            "aat_breakdown": aat_breakdown,
        }

    def get_career_level_info(self):
        data = _bt().get_live_game_data()
        if not data:
            hist_path = _bt().app_config.get('history_path')
            if hist_path and os.path.exists(hist_path):
                game_files = sorted(
                    [f for f in os.listdir(hist_path) if f.startswith("Game_") and f.endswith(".json")],
                    key=lambda f: os.path.getmtime(os.path.join(hist_path, f)),
                    reverse=True,
                )
                if game_files:
                    data = load_json(os.path.join(hist_path, game_files[0]))
        if not data:
            return {"error": "No game data available"}
        game = data.get('game') or data.get('data', {}).get('game', {})
        players = data.get('players') or data.get('data', {}).get('players', {})
        p = players.get('0', {})
        prestige = int(p.get('prestige', 0))
        level = int(p.get('level', 1))
        current_xp = int(p.get('xp', p.get('total_xp', 0)))
        ult = int(p.get('prestige_ultimate', 0))
        abso = int(p.get('prestige_absolute', 0))
        leg = int(p.get('prestige_legend', 0))
        title = p.get('title', '')
        map_name = game.get('map_played', 'Unknown')
        steam_link = game.get('steam_link', '')
        xp_required = xp_tracker_instance.get_xp_required(level, leg)
        if ult > 0:
            rank_main = "ULTIMATE PRESTIGE"
        elif abso > 0:
            rank_main = "ABSOLUTE PRESTIGE"
        elif leg > 0:
            rank_main = "PRESTIGE LEGEND"
        elif prestige > 0:
            rank_main = f"PRESTIGE {prestige}"
        else:
            rank_main = "RECRUIT"
        rank_parts = []
        if ult > 0:
            rank_parts.append(f"Ult Tier {ult}")
        if abso > 0:
            rank_parts.append(f"Abs Tier {abso}")
        if leg > 0:
            rank_parts.append(f"Leg Tier {leg}")
        if prestige > 0:
            rank_parts.append(f"Prestige {prestige}")
        rank_parts.append(f"Level {level}")
        rank_sub = " // ".join(rank_parts)
        progress_pct = round((current_xp / xp_required) * 100, 1) if xp_required > 0 else 0
        return {
            "prestige": prestige,
            "level": level,
            "current_xp": current_xp,
            "xp_required": xp_required,
            "progress_pct": progress_pct,
            "r_main": rank_main,
            "r_sub": rank_sub,
            "title": title,
            "prest_icon": get_prestige_icon_src(prestige),
            "lvl_icon": get_level_icon_src(level),
            "ult_icon": get_tier_icon_src("ultimate", ult),
            "abso_icon": get_tier_icon_src("absolute", abso),
            "leg_icon": get_tier_icon_src("legend", leg),
            "map_name": map_name,
            "steam_link": steam_link,
            "workshop_image": get_workshop_image(steam_link) if _bt().app_config.get('workshop_images_enabled', True) else None,
        }

    def get_top_10_xp_maps(self, player_id="0"):
        xp_cache_path = get_runtime_path("match_xp_cache.json")
        xp_data = load_json(xp_cache_path) or {}

        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return []

        map_highest_xp = {}

        for filepath in glob.glob(os.path.join(hist_path, "Game_*.json")):
            match_data = load_json(filepath)
            if not match_data:
                continue

            game = match_data.get('game') or match_data.get('data', {}).get('game', {})
            players = match_data.get('players') or match_data.get('data', {}).get('players', {})

            game_id = str(game.get('game_id', ''))
            map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()

            match_xp = 0

            if game_id in xp_data and str(player_id) in xp_data[game_id]:
                match_xp = xp_data[game_id][str(player_id)].get('total_match_xp', 0)
            elif str(player_id) in players:
                p_data = players[str(player_id)]
                match_xp = int(p_data.get('match_xp_earned', 0))

            if match_xp > 0:
                if map_name not in map_highest_xp or match_xp > map_highest_xp[map_name]:
                    map_highest_xp[map_name] = match_xp

        sorted_maps = sorted(map_highest_xp.items(), key=lambda x: x[1], reverse=True)
        return [{"map": m[0], "xp": m[1]} for m in sorted_maps[:10]]

    def get_xp_per_round_graph(self, game_id, player_id):
        history = xpm_grapher_instance.live_history.get(str(game_id), {}).get(str(player_id), {})
        return xpm_grapher_instance.generate_xp_per_round_data(history)

    # --- Best Matches ---
    def add_current_best_match(self, target_game_id=None):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"success": False, "msg": "History folder is not configured or available."}

        raw_id = str(target_game_id or "").strip()
        if not raw_id or raw_id == "0":
            if not _bt().has_live_game_source():
                return {"success": False, "msg": "No displayed match ID is available, and Live Game Path is not configured."}
            live_data = _bt().get_live_game_data()
            if not live_data:
                return {"success": False, "msg": "CurrentGame.json could not be read."}
            live_game = live_data.get('game') or live_data.get('data', {}).get('game', {})
            raw_id = str(live_game.get('game_id', '0'))
            if not raw_id or raw_id == "0":
                return {"success": False, "msg": "No active match game ID is available yet."}
        else:
            live_data = None

        safe_id = sanitize_game_id(raw_id)
        archive_data, _ = find_archive_data(hist_path, safe_id, live_data=live_data)
        return add_best_match_from_data(safe_id, archive_data)

    def get_best_matches(self):
        hist_path = _bt().app_config.get('history_path')
        return get_best_matches_with_archive_status(hist_path)

    def remove_best_match(self, game_id):
        return remove_best_match_by_id(game_id)

    def get_xp_trend_data(self, player_id="0", limit=30):
        hist_path = _bt().app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return []

        xp_cache_path = get_runtime_path("match_xp_cache.json")
        xp_data = load_json(xp_cache_path) or {}

        files = sorted(
            [f for f in glob.glob(os.path.join(hist_path, "Game_*.json"))],
            key=lambda f: os.path.getmtime(f),
        )
        entries = []
        for filepath in files[-limit:]:
            try:
                data = load_json(filepath)
                if not data:
                    continue
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players:
                    continue

                game_id = str(game.get('game_id', ''))
                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                round_num = int(game.get('rounds_total', 0))
                time_sec = int(game.get('time_total', 0))
                mtime = os.path.getmtime(filepath)

                match_xp = 0
                if game_id in xp_data and str(player_id) in xp_data[game_id]:
                    match_xp = xp_data[game_id][str(player_id)].get('total_match_xp', 0)
                elif str(player_id) in players:
                    p_data = players[str(player_id)]
                    match_xp = int(p_data.get('match_xp_earned', 0))

                entries.append({
                    "map": map_name,
                    "xp": match_xp,
                    "round": round_num,
                    "time_sec": time_sec,
                    "date_iso": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else "",
                })
            except Exception:
                continue

        return entries

    # --- Challenges ---
    def get_challenges(self):
        return _bt().challenge_manager.get_frontend_data()

    def force_sync_challenges(self):
        hist_path = _bt().app_config.get('history_path')
        if hist_path:
            _bt().challenge_manager.scan_all_history(hist_path)
            return True
        return False

    def reset_challenges_api(self):
        live_data = _bt().get_live_game_data()

        _bt().challenge_manager.reset_all_challenges(live_data)
        return True
