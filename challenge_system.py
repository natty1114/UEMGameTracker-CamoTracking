import os
import json
import glob
import time
import random
from datetime import datetime, timezone

from app_paths import get_runtime_path
from map_weapons import map_weapons_manager
from sync_map_challenges import fetch as fetch_map_challenges
from weapon_categories import get_weapon_category, normalise_weapon_category

CHALLENGES_FILE = "challenges.json"
MAP_CHALLENGES_FILE = "map_challenges.json"
UNLOCKS_FILE = "unlocked_rewards.json"
CALLING_CARD_DIR = "callingcards"
LOCAL_WEEKLY_PREFIX = "weekly_local_"
REMOTE_WEEKLY_PREFIX = "weekly_remote_"
LOCAL_WEEKLY_COUNT = 4

LOCAL_WEEKLY_TEMPLATES = [
    {"stat": "kills", "target": 2000, "type": "cumulative", "title": "Weekly Slayer", "desc": "Get 2,000 Kills this week"},
    {"stat": "headshots", "target": 500, "type": "cumulative", "title": "Weekly Deadeye", "desc": "Get 500 Headshots this week"},
    {"stat": "points", "target": 250000, "type": "cumulative", "title": "Weekly Bankroll", "desc": "Earn 250,000 Points this week"},
    {"stat": "round", "target": 35, "type": "single_game", "title": "Weekly Deep Run", "desc": "Reach Round 35 in one game this week"},
    {"stat": "matches", "target": 10, "type": "cumulative", "title": "Weekly Grinder", "desc": "Complete 10 Matches this week"},
    {"stat": "doors", "target": 100, "type": "cumulative", "title": "Weekly Keymaster", "desc": "Open 100 Doors this week"},
    {"stat": "perks_drank", "target": 40, "type": "cumulative", "title": "Weekly Soda Run", "desc": "Finish games with 40 total active perks this week"},
    {"stat": "melee", "target": 125, "type": "cumulative", "title": "Weekly Brawler", "desc": "Get 125 Melee Kills this week"},
    {"stat": "gobblegums_used", "target": 25, "type": "cumulative", "title": "Weekly Chewer", "desc": "Use 25 GobbleGums this week"},
    {"stat": "box", "target": 25, "type": "cumulative", "title": "Weekly Gambler", "desc": "Hit the box 25 times this week"},
    {"stat": "xp", "target": 1000000, "type": "cumulative", "title": "Weekly XP Hunt", "desc": "Earn 1,000,000 Match XP this week"},
]

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return None

def save_json(path, data):
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except: return False

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

def get_game_steam_link(game):
    if not isinstance(game, dict):
        return ""
    return normalize_steam_link(
        game.get("steam_link")
        or game.get("workshop_link")
        or game.get("workshop_url")
        or game.get("workshop_id")
        or game.get("ugc")
    )

def extract_weapon_stats(player, steam_link=""):
    weapons = player.get('top5', player.get('weapon_data', {}))
    if not isinstance(weapons, dict):
        return {}
    result = {}
    for k, w in weapons.items():
        if not isinstance(w, dict):
            continue
        if w.get('display') == 'none':
            continue
        display = str(w.get('display', 'Unknown'))
        result[k] = {
            "kills": int(w.get('kills', 0)),
            "headshots": int(w.get('headshots', 0)),
            "display": display,
            "category": map_weapons_manager.get_weapon_category_for(steam_link, k, display) if steam_link else get_weapon_category(k, display),
        }
    return result


def normalize_map_challenge(raw):
    item = {
        "id": "",
        "cat": "operations",
        "title": "",
        "desc": "",
        "target": 1,
        "stat": "kills",
        "type": "cumulative",
        "progress": 0,
        "completed": False,
        "reward_type": "none",
        "reward_val": "",
        "map_name": "",
        "map_steam_link": "",
        "weapon_console_name": "",
        "weapon_display_name": "",
        "weapon_category": "",
    }
    if isinstance(raw, dict):
        item.update(raw)
    for key in ("id", "cat", "title", "desc", "stat", "type", "reward_type", "reward_val", "map_name", "weapon_console_name", "weapon_display_name", "weapon_category"):
        item[key] = str(item.get(key, "")).strip()
    item["map_steam_link"] = normalize_steam_link(item.get("map_steam_link") or item.get("steam_link"))
    item["cat"] = "operations"
    item["map_challenge"] = True
    try:
        item["target"] = max(0, int(item.get("target", 0)))
    except:
        item["target"] = 0
    try:
        item["progress"] = max(0, int(item.get("progress", 0)))
    except:
        item["progress"] = 0
    item["completed"] = bool(item.get("completed", False))
    if not item["title"]:
        name = item["map_name"] or f"Workshop {item['map_steam_link']}"
        item["title"] = f"{name}: Map Operation"
    if not item["desc"]:
        item["desc"] = f"Complete this objective on {item['map_name'] or item['map_steam_link']}."
    return item

class ChallengeManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.filepath = get_runtime_path(CHALLENGES_FILE)
        self.map_challenges_path = get_runtime_path(MAP_CHALLENGES_FILE)
        self.unlocks_path = get_runtime_path(UNLOCKS_FILE)
        self.cards_path = os.path.join(base_path, CALLING_CARD_DIR)
        self.themes_path = os.path.join(base_path, "themes")
        self.reset_timestamp = 0
        self.reset_offset = {}
        self.live_game_id = None
        self.live_snapshot = {}
        self.live_state = {}
        self._lifetime_high_water = {}
        self._weapon_stat_last = {}
        self.weekly_rotation = {}
        self.remote_weekly_pool = []
        self.remote_weekly_active_count = LOCAL_WEEKLY_COUNT
        
        self.theme_requirements = {}
        
        self.unlocked_rewards = self._load_unlocks()
        self.challenges = self._load_or_create()
        self.map_challenges = self._load_map_challenges()
        self.check_theme_unlocks()

    def _load_map_challenges(self):
        data = load_json(self.map_challenges_path)
        if isinstance(data, dict):
            raw = data.get("challenges", [])
        elif isinstance(data, list):
            raw = data
        else:
            raw = []
        return [normalize_map_challenge(item) for item in raw if isinstance(item, dict)]

    def _save_map_challenges(self):
        full = load_json(self.map_challenges_path)
        if not isinstance(full, dict):
            full = {}
        full["challenges"] = self.map_challenges
        return save_json(self.map_challenges_path, full)

    def sync_map_challenges_from_remote(self, url, app_config, force=False):
        """Sync site map challenges while preserving locally-created map operations."""
        if not url:
            return {"ok": False, "msg": "Map challenges sync URL is not configured."}

        result = fetch_map_challenges(url, app_config, force=force)
        if not result.get("ok") or not result.get("changed"):
            return result

        remote_challenges = result.get("challenges")
        if not isinstance(remote_challenges, list):
            return {"ok": False, "msg": "Remote map challenges response was not a list."}

        stored = load_json(self.map_challenges_path)
        if not isinstance(stored, dict):
            stored = {}

        archived_progress = stored.get("removed_challenge_progress", {})
        if not isinstance(archived_progress, dict):
            archived_progress = {}

        current_by_id = {
            str(c.get("id", "")): c
            for c in self.map_challenges
            if isinstance(c, dict) and c.get("id")
        }
        progress_by_id = {}
        for cid, challenge in archived_progress.items():
            if isinstance(challenge, dict):
                progress_by_id[str(cid)] = challenge
        for cid, challenge in current_by_id.items():
            progress_by_id[cid] = challenge

        next_challenges = []
        active_ids = set()
        removed_ids = set()
        for raw in remote_challenges:
            if not isinstance(raw, dict):
                continue
            challenge = normalize_map_challenge(raw)
            cid = str(challenge.get("id", ""))
            if not cid:
                continue
            if raw.get("remove") is True:
                removed_ids.add(cid)
                previous = progress_by_id.get(cid, challenge)
                archived_progress[cid] = {
                    "progress": previous.get("progress", challenge.get("progress", 0)),
                    "completed": previous.get("completed", challenge.get("completed", False)),
                    "title": previous.get("title", challenge.get("title", "")),
                    "map_name": previous.get("map_name", challenge.get("map_name", "")),
                    "map_steam_link": previous.get("map_steam_link", challenge.get("map_steam_link", "")),
                    "removed_at": int(time.time()),
                }
                continue
            previous = progress_by_id.get(cid, {})
            challenge["progress"] = previous.get("progress", challenge.get("progress", 0))
            challenge["completed"] = previous.get("completed", challenge.get("completed", False))
            next_challenges.append(challenge)
            active_ids.add(cid)

        for cid, challenge in current_by_id.items():
            if cid in active_ids or cid in removed_ids:
                continue
            next_challenges.append(challenge)
            active_ids.add(cid)
            archived_progress.pop(cid, None)

        self.map_challenges = next_challenges
        stored["challenges"] = self.map_challenges
        stored["removed_challenge_progress"] = archived_progress
        stored["remote_version"] = result.get("version", "")
        stored["remote_mode"] = result.get("mode", "replace")
        stored["remote_synced_at"] = int(time.time())
        save_json(self.map_challenges_path, stored)
        result["active_count"] = len(self.map_challenges)
        return result

    def _frontend_challenges(self):
        return list(self.challenges) + list(self.map_challenges)

    def _load_unlocks(self):
        data = load_json(self.unlocks_path)
        if not data:
            defaults = ["default"]
            save_json(self.unlocks_path, defaults)
            return defaults
        return data

    def _load_or_create(self):
        defaults = [
            # --- THEME: VOID ---
            {"id": "c_void_1", "cat": "lifetime", "title": "Void I: Focus", "desc": "Get 650 Headshots", "target": 650, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_1"},
            {"id": "c_void_2", "cat": "lifetime", "title": "Void II: Clarity", "desc": "Get 2,000 Headshots", "target": 2000, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_2"},
            {"id": "c_void_3", "cat": "lifetime", "title": "Void III: Mastery", "desc": "Get 6,500 Headshots", "target": 6500, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_3"},
            # --- THEME: 115 ORIGINS ---
            {"id": "c_org_1", "cat": "lifetime", "title": "Origins I: Power", "desc": "Earn 50,000 Points", "target": 50000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_4"},
            {"id": "c_org_2", "cat": "lifetime", "title": "Origins II: Unleashed", "desc": "Get 1,250 Kills", "target": 1250, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_5"},
            {"id": "c_org_3", "cat": "lifetime", "title": "Origins III: Ancient", "desc": "Reach Round 30 in one game", "target": 30, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_6"},
            # --- THEME: RED HEX ---
            {"id": "c_red_1", "cat": "lifetime", "title": "Red Hex I: Thirsty", "desc": "Finish games with 10 Perks active total", "target": 10, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_7"},
            {"id": "c_red_2", "cat": "lifetime", "title": "Red Hex II: Addict", "desc": "Finish games with 50 Perks active total", "target": 50, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_8"},
            {"id": "c_red_3", "cat": "lifetime", "title": "Red Hex III: Overdose", "desc": "Finish games with 100 Perks active total", "target": 100, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_9"},
            # --- THEME: GOLDEN DIVINIUM ---
            {"id": "c_gold_1", "cat": "lifetime", "title": "Gold I: Nugget", "desc": "Earn 100,000 Points", "target": 100000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_10"},
            {"id": "c_gold_2", "cat": "lifetime", "title": "Gold II: Bullion", "desc": "Earn 500,000 Points", "target": 500000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_11"},
            {"id": "c_gold_3", "cat": "lifetime", "title": "Gold III: Tycoon", "desc": "Earn 1,000,000 Points", "target": 1000000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_12"},
            # --- THEME: RETRO ---
            {"id": "c_retro_1", "cat": "lifetime", "title": "Retro I: 8-Bit", "desc": "Get 1,250 Kills", "target": 1250, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_13"},
            {"id": "c_retro_2", "cat": "lifetime", "title": "Retro II: 16-Bit", "desc": "Get 3,250 Kills", "target": 3250, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_14"},
            {"id": "c_retro_3", "cat": "lifetime", "title": "Retro III: High Score", "desc": "Get 6,500 Kills", "target": 6500, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_15"},
            # --- THEME: MATRIX ---
            {"id": "c_mat_1", "cat": "lifetime", "title": "Matrix I: Blue Pill", "desc": "Reach Round 20", "target": 20, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_16"},
            {"id": "c_mat_2", "cat": "lifetime", "title": "Matrix II: Red Pill", "desc": "Reach Round 35", "target": 35, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_17"},
            {"id": "c_mat_3", "cat": "lifetime", "title": "Matrix III: The One", "desc": "Reach Round 50", "target": 50, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_18"},
            # --- CAREER ---
            {"id": "c_card_master", "cat": "lifetime", "title": "Prestige Master", "desc": "Get 125,000 Total Kills", "target": 125000, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_19"},
            {"id": "c_door_master", "cat": "lifetime", "title": "Keymaster", "desc": "Open 1,000 Doors", "target": 1000, "stat": "doors", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_20"},
            {"id": "c_round_100", "cat": "lifetime", "title": "Century Club", "desc": "Reach Round 100 in one game", "target": 100, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_21"},
            {"id": "c_perk_addict", "cat": "lifetime", "title": "Soda Fountain", "desc": "Finish games with 500 Perks active total", "target": 500, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_22"},
            # --- CAREER: CQC ---
            {"id": "c_melee_1", "cat": "lifetime", "title": "Brawler", "desc": "Get 125 Melee Kills", "target": 125, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_23"},
            {"id": "c_melee_2", "cat": "lifetime", "title": "Knife Master", "desc": "Get 650 Melee Kills", "target": 650, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_24"},
            {"id": "c_melee_3", "cat": "lifetime", "title": "Samurai", "desc": "Get 1,250 Melee Kills", "target": 1250, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_25"},
        ]
        
        saved_data = load_json(self.filepath)
        if isinstance(saved_data, list): saved_data = {"challenges": saved_data} 
        if not saved_data: saved_data = {"challenges": defaults}
        
        self.reset_timestamp = saved_data.get("reset_timestamp", 0)
        self.reset_offset = saved_data.get("reset_offset", {})
        self.live_state = saved_data.get("live_state", {})
        if not isinstance(self.live_state, dict):
            self.live_state = {}
        self.weekly_rotation = saved_data.get("weekly_rotation", {})
        if not isinstance(self.weekly_rotation, dict):
            self.weekly_rotation = {}
        self.remote_weekly_pool = saved_data.get("remote_weekly_pool", [])
        if not isinstance(self.remote_weekly_pool, list):
            self.remote_weekly_pool = []
        try:
            self.remote_weekly_active_count = max(1, int(saved_data.get("remote_weekly_active_count", LOCAL_WEEKLY_COUNT)))
        except:
            self.remote_weekly_active_count = LOCAL_WEEKLY_COUNT
        
        current_list = saved_data.get("challenges", [])
        cleaned_list = [c for c in current_list if not c['id'].startswith("c_theme_")]
        default_map = {d['id']: d for d in defaults}
        
        for c in cleaned_list:
            if c['id'] in default_map:
                saved_progress = c.get('progress', 0)
                saved_completed = c.get('completed', False)
                c.update(default_map[c['id']])
                c['progress'] = saved_progress
                c['completed'] = saved_completed
        
        existing_ids = [c['id'] for c in cleaned_list]
        for d in defaults:
            if d['id'] not in existing_ids: cleaned_list.append(d)

        final_list = self._scan_and_create_card_challenges(cleaned_list)
        final_list = self._scan_and_create_theme_challenges(final_list)
        final_list = self._ensure_local_weekly_rotation(final_list)
        
        saved_data["challenges"] = final_list
        saved_data["reset_timestamp"] = self.reset_timestamp
        saved_data["reset_offset"] = self.reset_offset
        saved_data["live_state"] = self.live_state
        saved_data["weekly_rotation"] = self.weekly_rotation
        saved_data["remote_weekly_pool"] = self.remote_weekly_pool
        saved_data["remote_weekly_active_count"] = self.remote_weekly_active_count
        save_json(self.filepath, saved_data)
        
        return final_list

    def _current_week_key(self):
        now = datetime.now(timezone.utc)
        iso_year, iso_week, _ = now.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    def _current_week_start_timestamp(self):
        now = datetime.now(timezone.utc)
        week_start = datetime.fromisocalendar(now.isocalendar().year, now.isocalendar().week, 1)
        return week_start.replace(tzinfo=timezone.utc).timestamp()

    def _ensure_local_weekly_rotation(self, current_challenges):
        week_key = self._current_week_key()
        existing_week = str(self.weekly_rotation.get("week_key", ""))
        active_from = float(self.weekly_rotation.get("active_from", 0) or 0)
        source = "remote" if self.remote_weekly_pool else "local"

        active_prefix = REMOTE_WEEKLY_PREFIX if source == "remote" else LOCAL_WEEKLY_PREFIX
        if existing_week == week_key and self.weekly_rotation.get("source") == source and any(
            isinstance(c, dict) and str(c.get("id", "")).startswith(active_prefix)
            for c in current_challenges
        ):
            return current_challenges

        active_from = self._current_week_start_timestamp()
        preserved = [
            c for c in current_challenges
            if not (
                isinstance(c, dict)
                and (
                    str(c.get("cat", "")).strip() == "weekly"
                    or str(c.get("id", "")).startswith("weekly_")
                    or str(c.get("id", "")).startswith("weekly-")
                    or str(c.get("source", "")).endswith("weekly_rotation")
                    or
                    str(c.get("id", "")).startswith(LOCAL_WEEKLY_PREFIX)
                    or str(c.get("id", "")).startswith(REMOTE_WEEKLY_PREFIX)
                )
            )
        ]

        if self.remote_weekly_pool:
            rng = random.Random(f"{week_key}|remote|{len(self.remote_weekly_pool)}")
            pool = [dict(c) for c in self.remote_weekly_pool if isinstance(c, dict)]
            rng.shuffle(pool)
            active_count = max(1, int(self.remote_weekly_active_count or LOCAL_WEEKLY_COUNT))
            selected = pool[:active_count]
            for index, source_challenge in enumerate(selected, start=1):
                source_id = str(source_challenge.get("id", f"remote_{index}"))
                challenge = dict(source_challenge)
                challenge["id"] = f"{REMOTE_WEEKLY_PREFIX}{week_key.replace('-', '_')}_{index:02d}"
                challenge["cat"] = "weekly"
                challenge["progress"] = 0
                challenge["completed"] = False
                challenge["source"] = "remote_weekly_rotation"
                challenge["remote_pool_id"] = source_id
                challenge["week_key"] = week_key
                challenge["active_from"] = active_from
                preserved.append(challenge)
        else:
            rng = random.Random(week_key)
            templates = list(LOCAL_WEEKLY_TEMPLATES)
            rng.shuffle(templates)

            for index, template in enumerate(templates[:LOCAL_WEEKLY_COUNT], start=1):
                challenge = {
                    "id": f"{LOCAL_WEEKLY_PREFIX}{week_key.replace('-', '_')}_{index:02d}",
                    "cat": "weekly",
                    "title": template["title"],
                    "desc": template["desc"],
                    "target": template["target"],
                    "stat": template["stat"],
                    "type": template["type"],
                    "progress": 0,
                    "completed": False,
                    "reward_type": "none",
                    "reward_val": "",
                    "source": "local_weekly_rotation",
                    "week_key": week_key,
                    "active_from": active_from
                }
                preserved.append(challenge)

        self.weekly_rotation = {
            "week_key": week_key,
            "active_from": active_from,
            "count": len([c for c in preserved if isinstance(c, dict) and str(c.get("id", "")).startswith(active_prefix)]),
            "source": source
        }
        return preserved

    def _normalise_remote_weekly_pool(self, manifest, incoming):
        pool = []
        if isinstance(manifest, dict):
            rotation = manifest.get("weekly_rotation", {})
            if isinstance(rotation, dict) and isinstance(rotation.get("pool"), list):
                pool = rotation.get("pool", [])
                try:
                    self.remote_weekly_active_count = max(1, int(rotation.get("active_count", LOCAL_WEEKLY_COUNT)))
                except:
                    self.remote_weekly_active_count = LOCAL_WEEKLY_COUNT
            elif isinstance(manifest.get("weekly_pool"), list):
                pool = manifest.get("weekly_pool", [])

        if not pool:
            pool = [
                c for c in incoming
                if isinstance(c, dict) and str(c.get("cat", "")).strip() == "weekly"
            ]

        cleaned = []
        for challenge in pool:
            if not isinstance(challenge, dict):
                continue
            item = dict(challenge)
            item["cat"] = "weekly"
            item["progress"] = 0
            item["completed"] = False
            if item.get("remove") is True:
                continue
            if not item.get("id"):
                item["id"] = f"remote_weekly_pool_{len(cleaned) + 1}"
            cleaned.append(item)
        return cleaned

    def _scan_and_create_card_challenges(self, current_challenges):
        if not os.path.exists(self.cards_path):
             os.makedirs(self.cards_path)
             return current_challenges

        image_files = []
        for ext in ["*.jpg", "*.png", "*.webp", "*.mp4", "*.webm"]:
            image_files.extend(glob.glob(os.path.join(self.cards_path, ext)))
            
        found_card_names = set()
        for f in image_files:
            base = os.path.splitext(os.path.basename(f))[0]
            if base != "default": found_card_names.add(base)

        existing_rewards = set()
        for c in current_challenges:
            if c.get('reward_type') == 'calling_card': existing_rewards.add(c.get('reward_val'))
        
        new_cards_to_add = found_card_names - existing_rewards
        
        for card_name in new_cards_to_add:
            pretty_name = card_name.replace("_", " ").title()
            new_chal = {
                "id": f"c_auto_{card_name}",
                "cat": "operations",
                "title": f"Op: {pretty_name}",
                "desc": f"Complete 10 matches to unlock {pretty_name}.",
                "target": 10,
                "stat": "matches", 
                "type": "cumulative",
                "progress": 0, 
                "completed": False,
                "reward_type": "calling_card", 
                "reward_val": card_name
            }
            current_challenges.append(new_chal)
            
        return current_challenges

    def _scan_and_create_theme_challenges(self, current_challenges):
        if not os.path.exists(self.themes_path):
             os.makedirs(self.themes_path)
             return current_challenges

        css_files = glob.glob(os.path.join(self.themes_path, "*.css"))

        # Find the highest playercard index currently in use
        max_card_idx = 0
        for c in current_challenges:
            if c.get('reward_type') == 'calling_card' and str(c.get('reward_val', '')).startswith('playercard_'):
                try:
                    idx = int(c['reward_val'].split('_')[1])
                    if idx > max_card_idx:
                        max_card_idx = idx
                except:
                    pass
            
        for f in css_files:
            theme_name = os.path.splitext(os.path.basename(f))[0]
            if theme_name == "default": 
                continue

            pretty_name = theme_name.replace("_", " ").title()
            
            c_id_1 = f"c_auto_th_{theme_name}_1"
            c_id_2 = f"c_auto_th_{theme_name}_2"
            c_id_3 = f"c_auto_th_{theme_name}_3"
            
            if theme_name not in self.theme_requirements:
                self.theme_requirements[theme_name] = [c_id_1, c_id_2, c_id_3]
            
            # Helper to generate playercard sequence
            def get_or_assign_card(c_id):
                nonlocal max_card_idx
                for existing_c in current_challenges:
                    if existing_c['id'] == c_id:
                        if not str(existing_c.get('reward_val', '')).startswith('playercard_'):
                            max_card_idx += 1
                            existing_c['reward_type'] = 'calling_card'
                            existing_c['reward_val'] = f"playercard_{max_card_idx}"
                        return existing_c['reward_val']
                
                max_card_idx += 1
                return f"playercard_{max_card_idx}"

            card_1 = get_or_assign_card(c_id_1)
            card_2 = get_or_assign_card(c_id_2)
            card_3 = get_or_assign_card(c_id_3)

            existing_ids = [c['id'] for c in current_challenges]

            def update_existing_theme_challenge(c_id, target, desc):
                for existing_c in current_challenges:
                    if existing_c.get("id") == c_id:
                        existing_c["target"] = target
                        existing_c["desc"] = desc
                        existing_c["stat"] = "kills"
                        existing_c["type"] = "cumulative"
                        existing_c["cat"] = "themes"
                        return True
                return False

            update_existing_theme_challenge(c_id_1, 1600, "Get 1,600 Kills")
            update_existing_theme_challenge(c_id_2, 4000, "Get 4,000 Kills")
            update_existing_theme_challenge(
                c_id_3,
                7500,
                f"Get 7,500 Kills. Unlocks {pretty_name.upper()} Theme.",
            )
            
            if c_id_1 not in existing_ids:
                current_challenges.append({
                    "id": c_id_1, "cat": "themes", "title": f"{pretty_name} I: Initiate",
                    "desc": "Get 1,600 Kills", "target": 1600, "stat": "kills",
                    "type": "cumulative", "progress": 0, "completed": False,
                    "reward_type": "calling_card", "reward_val": card_1
                })
            if c_id_2 not in existing_ids:
                current_challenges.append({
                    "id": c_id_2, "cat": "themes", "title": f"{pretty_name} II: Veteran",
                    "desc": "Get 4,000 Kills", "target": 4000, "stat": "kills",
                    "type": "cumulative", "progress": 0, "completed": False,
                    "reward_type": "calling_card", "reward_val": card_2
                })
            if c_id_3 not in existing_ids:
                current_challenges.append({
                    "id": c_id_3, "cat": "themes", "title": f"{pretty_name} III: Master",
                    "desc": f"Get 7,500 Kills. Unlocks {pretty_name.upper()} Theme.", "target": 7500, "stat": "kills",
                    "type": "cumulative", "progress": 0, "completed": False,
                    "reward_type": "calling_card", "reward_val": card_3
                })
                
        return current_challenges

    def get_frontend_data(self):
        self.challenges = self._ensure_local_weekly_rotation(self.challenges)
        self._save_challenges()
        self.map_challenges = self._load_map_challenges()
        return self._frontend_challenges()

    def apply_remote_manifest(self, manifest, replace=True):
        if not isinstance(manifest, dict):
            return False
        incoming = manifest.get("challenges", [])
        if not isinstance(incoming, list):
            return False

        self.remote_weekly_pool = self._normalise_remote_weekly_pool(manifest, incoming)
        incoming = [
            c for c in incoming
            if not (isinstance(c, dict) and str(c.get("cat", "")).strip() == "weekly")
        ]
        if not incoming and self.remote_weekly_pool:
            self.challenges = self._ensure_local_weekly_rotation(self.challenges)
            self._save_challenges(manifest)
            return True

        current_by_id = {
            str(c.get("id", "")): c
            for c in self.challenges
            if isinstance(c, dict) and c.get("id")
        }
        incoming_by_id = {
            str(c.get("id", "")): c
            for c in incoming
            if isinstance(c, dict) and c.get("id")
        }

        if not incoming_by_id:
            return False

        # Remove challenges flagged with "remove": true
        remove_ids = {
            cid
            for cid, challenge in incoming_by_id.items()
            if challenge.get("remove") is True
        }
        if remove_ids:
            self.challenges = [
                c for c in self.challenges
                if not (isinstance(c, dict) and str(c.get("id", "")) in remove_ids)
            ]
            current_by_id = {
                cid: c for cid, c in current_by_id.items()
                if cid not in remove_ids
            }
            incoming_by_id = {
                cid: c for cid, c in incoming_by_id.items()
                if cid not in remove_ids
            }

        if not incoming_by_id:
            self._save_challenges(manifest)
            return True

        if replace:
            next_challenges = list(self.challenges)
            for cid, challenge in incoming_by_id.items():
                found = False
                for i, c in enumerate(next_challenges):
                    if isinstance(c, dict) and str(c.get("id", "")) == cid:
                        merged = dict(challenge)
                        merged["progress"] = c.get("progress", merged.get("progress", 0))
                        merged["completed"] = c.get("completed", merged.get("completed", False))
                        next_challenges[i] = merged
                        found = True
                        break
                if not found:
                    next_challenges.append(challenge)
        else:
            next_challenges = list(self.challenges)
            existing_ids = {str(c.get("id", "")) for c in next_challenges if isinstance(c, dict)}
            for cid, challenge in incoming_by_id.items():
                if cid not in existing_ids:
                    next_challenges.append(challenge)

        cleaned = []
        for challenge in next_challenges:
            if not isinstance(challenge, dict):
                continue
            cid = str(challenge.get("id", ""))
            previous = current_by_id.get(cid, {})
            item = dict(challenge)
            item["progress"] = previous.get("progress", item.get("progress", 0))
            item["completed"] = previous.get("completed", item.get("completed", False))
            cleaned.append(item)

        self.challenges = cleaned
        self.challenges = self._ensure_local_weekly_rotation(self.challenges)
        self.check_theme_unlocks()
        self._save_challenges(manifest)
        return True

    def _save_challenges(self, manifest=None):
        full = load_json(self.filepath)
        if not isinstance(full, dict):
            full = {}
        full["challenges"] = self.challenges
        full["weekly_rotation"] = self.weekly_rotation
        full["remote_weekly_pool"] = self.remote_weekly_pool
        full["remote_weekly_active_count"] = self.remote_weekly_active_count
        full["live_state"] = self.live_state
        if manifest and isinstance(manifest, dict):
            full["remote_manifest_version"] = str(manifest.get("version", "remote"))
        save_json(self.filepath, full)

    def _weapon_totals_from_stats(self, stats):
        totals = {}
        weapons = stats.get("_weapons", {}) if isinstance(stats, dict) else {}
        if not isinstance(weapons, dict):
            return totals
        for weapon_name, weapon_stats in weapons.items():
            if not isinstance(weapon_stats, dict):
                continue
            for stat_name, value in weapon_stats.items():
                if stat_name == "category":
                    continue
                try:
                    int_value = int(value)
                except:
                    continue
                totals[f"weapon:{weapon_name}|{stat_name}"] = int_value
                category = normalise_weapon_category(
                    weapon_stats.get("category") or get_weapon_category(weapon_name, weapon_stats.get("display", ""))
                )
                category_key = f"category:{category}|{stat_name}"
                totals[category_key] = totals.get(category_key, 0) + int_value
        return totals

    def _save_live_state(self, game_id, stats):
        if not game_id or not isinstance(stats, dict):
            return
        saved_stats = {}
        for key, value in stats.items():
            if str(key).startswith("_"):
                continue
            if key == "points":
                continue
            try:
                saved_stats[key] = int(value)
            except:
                saved_stats[key] = 0
        self.live_state = {
            "game_id": str(game_id),
            "stats": saved_stats,
            "weapon_totals": self._weapon_totals_from_stats(stats),
            "updated_at": time.time(),
        }
        self._save_challenges()

    def _restore_live_baseline(self, game_id):
        if not self.live_state or str(self.live_state.get("game_id", "")) != str(game_id):
            return False
        saved_stats = self.live_state.get("stats", {})
        if not isinstance(saved_stats, dict):
            return False
        self.live_snapshot = {}
        for key, value in saved_stats.items():
            if key == "points":
                continue
            try:
                self.live_snapshot[key] = int(value)
            except:
                self.live_snapshot[key] = 0
        self._lifetime_high_water["doors"] = max(
            self._lifetime_high_water.get("doors", 0),
            self.live_snapshot.get("doors", 0),
        )
        weapon_totals = self.live_state.get("weapon_totals", {})
        if isinstance(weapon_totals, dict):
            for key, value in weapon_totals.items():
                if "|" not in str(key):
                    continue
                try:
                    self._weapon_stat_last[str(key)] = (int(value), str(game_id))
                except:
                    continue
        return True

    def get_unlocked_themes(self):
        return self.unlocked_rewards

    def check_theme_unlocks(self):
        changed = False
        completed_ids = [c['id'] for c in self.challenges if c['completed']]
        
        for theme_name, req_ids in self.theme_requirements.items():
            if theme_name in self.unlocked_rewards: continue
            if all(rid in completed_ids for rid in req_ids):
                self.unlocked_rewards.append(theme_name)
                changed = True
        
        if changed: save_json(self.unlocks_path, self.unlocked_rewards)

    def _is_challenge_active(self, c_id):
        for theme, chain in self.theme_requirements.items():
            if c_id in chain:
                idx = chain.index(c_id)
                if idx == 0: return True 
                prev_id = chain[idx - 1]
                prev_c = next((x for x in self.challenges if x['id'] == prev_id), None)
                return prev_c and prev_c['completed']
        return True 

    def process_completed_game(self, game_data, save=True):
        if not game_data: return

        game = game_data.get('game') or game_data.get('data', {}).get('game', {})
        players = game_data.get('players') or game_data.get('data', {}).get('players', {})
        if not players: return
        p = list(players.values())[0]

        raw_perks = p.get('perks', [])
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        valid_perks = [x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x]
        perks_drank_val = game_data.get('calculated_perks_drank', len(valid_perks))

        stats = {
            "matches": 1,
            "kills": int(p.get('kills', 0)),
            "headshots": int(p.get('headshots', 0)),
            "doors": int(p.get('doors_purchased', 0)),
            "round": int(game.get('rounds_total', 0)),
            "points": 0,
            "melee": int(p.get('melee_kills', 0)), 
            "perks_drank": perks_drank_val,
            "rounds_added": int(game.get('rounds_total', 0)),
            "xp": int(p.get('match_xp_earned', 0)),
            "_steam_link": get_game_steam_link(game),
            "_map_name": str(game.get("map_played", game.get("map_name", "Unknown")) or "Unknown"),
            "_weapons": extract_weapon_stats(p, get_game_steam_link(game)),
        }

        chain_available = {chain: stats.copy() for chain in self.theme_requirements.keys()}
        changed = False

        for c in self.challenges:
            if c['completed']: continue
            if not self._is_challenge_active(c['id']): continue

            my_chain = None
            for chain_name, chain_list in self.theme_requirements.items():
                if c['id'] in chain_list:
                    my_chain = chain_name
                    break
                    
            if my_chain:
                if str(c.get("stat", "")).startswith("weapon_"):
                    val = self._get_challenge_weapon_stat_value(c, chain_available[my_chain])
                else:
                    val = chain_available[my_chain].get(c['stat'], 0)
            else:
                if str(c.get("stat", "")).startswith("weapon_"):
                    val = self._get_challenge_weapon_stat_value(c, stats)
                else:
                    val = stats.get(c['stat'], 0)

            if val <= 0: continue

            if c['type'] == 'cumulative':
                if c['progress'] + val >= c['target']:
                    excess = (c['progress'] + val) - c['target']
                    c['progress'] = c['target']
                    c['completed'] = True
                    if my_chain:
                        chain_available[my_chain][c['stat']] = excess 
                    changed = True
                else:
                    c['progress'] += val
                    if my_chain:
                        chain_available[my_chain][c['stat']] = 0 
                    changed = True
            elif c['type'] == 'single_game':
                if val >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
                    changed = True
                elif val > c['progress']:
                    c['progress'] = val
                    changed = True
        
        self.check_theme_unlocks()
        
        if save and changed:
            full = load_json(self.filepath)
            if not isinstance(full, dict): full = {}
            full["challenges"] = self.challenges
            full["weekly_rotation"] = self.weekly_rotation
            full["remote_weekly_pool"] = self.remote_weekly_pool
            full["remote_weekly_active_count"] = self.remote_weekly_active_count
            full["live_state"] = self.live_state
            save_json(self.filepath, full)

    def process_update(self, history_path):
        if not history_path or not os.path.exists(history_path): return

        preserved_points = {}
        for c in self.challenges:
            if c.get('type') == 'cumulative' and c.get('stat') == 'points':
                preserved_points[c.get('id')] = {
                    "progress": int(c.get('progress', 0)),
                    "completed": bool(c.get('completed', False)),
                }

        for c in self.challenges:
            if c['type'] == 'cumulative': 
                c['progress'] = 0
                c['completed'] = False

        json_files = glob.glob(os.path.join(history_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime) 
        
        for f in json_files:
            if os.path.getmtime(f) < self.reset_timestamp:
                continue
                
            try:
                data = load_json(f)
                if not data: continue
                self._apply_game_stats_with_time(data, os.path.getmtime(f))
            except: pass

        for c in self.challenges:
            saved = preserved_points.get(c.get('id'))
            if not saved or c.get('type') != 'cumulative' or c.get('stat') != 'points':
                continue
            target = int(c.get('target', 0))
            current_progress = int(c.get('progress', 0))
            saved_progress = int(saved.get("progress", 0))
            c['progress'] = min(max(current_progress, saved_progress), target) if target > 0 else max(current_progress, saved_progress)
            c['completed'] = bool(saved.get("completed", False)) or (target > 0 and c['progress'] >= target)
            
        self.check_theme_unlocks()
        full = {
            "challenges": self.challenges,
            "reset_timestamp": self.reset_timestamp,
            "reset_offset": self.reset_offset,
            "live_state": self.live_state,
            "weekly_rotation": self.weekly_rotation,
            "remote_weekly_pool": self.remote_weekly_pool,
            "remote_weekly_active_count": self.remote_weekly_active_count
        }
        save_json(self.filepath, full)

    def apply_single_game(self, game_path):
        if not game_path or not os.path.exists(game_path): return
        try:
            data = load_json(game_path)
            if not data: return
            self._apply_game_stats_with_time(data, os.path.getmtime(game_path))
            self.check_theme_unlocks()
            full = {
                "challenges": self.challenges,
                "reset_timestamp": self.reset_timestamp,
                "reset_offset": self.reset_offset,
                "live_state": self.live_state,
                "weekly_rotation": self.weekly_rotation,
                "remote_weekly_pool": self.remote_weekly_pool,
                "remote_weekly_active_count": self.remote_weekly_active_count
            }
            save_json(self.filepath, full)
        except: pass

    def _apply_game_stats(self, game_data):
        self._apply_game_stats_with_time(game_data)

    def _apply_game_stats_with_time(self, game_data, game_timestamp=None):
        game = game_data.get('game') or game_data.get('data', {}).get('game', {})
        players = game_data.get('players') or game_data.get('data', {}).get('players', {})
        if not players: return
        p = list(players.values())[0]
        game_id = str(game.get('game_id', ''))

        raw_perks = p.get('perks', [])
        valid_perks_count = 0
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        if raw_perks:
             valid_perks_count = len([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
        
        perks_drank_val = game_data.get('calculated_perks_drank', valid_perks_count)

        stats = {
            "matches": 1,
            "kills": int(p.get('kills', 0)),
            "headshots": int(p.get('headshots', 0)),
            "doors": int(p.get('doors_purchased', 0)),
            "round": int(game.get('rounds_total', 0)),
            "points": 0,
            "melee": int(p.get('melee_kills', 0)),
            "perks_drank": perks_drank_val,
            "rounds_added": int(game.get('rounds_total', 0)),
            "xp": int(p.get('match_xp_earned', 0)),
            "_steam_link": get_game_steam_link(game),
            "_map_name": str(game.get("map_played", game.get("map_name", "Unknown")) or "Unknown"),
            "_weapons": extract_weapon_stats(p, get_game_steam_link(game)),
        }

        # Apply Mid-Match Offset Subtraction
        if self.reset_offset and self.reset_offset.get("game_id") == game_id:
            stats["matches"] = 0
            stats["kills"] = max(0, stats["kills"] - self.reset_offset.get("kills", 0))
            stats["headshots"] = max(0, stats["headshots"] - self.reset_offset.get("headshots", 0))
            stats["doors"] = max(0, stats["doors"] - self.reset_offset.get("doors", 0))
            stats["round"] = max(0, stats["round"] - self.reset_offset.get("round", 0))
            stats["points"] = max(0, stats["points"] - self.reset_offset.get("points", 0))
            stats["melee"] = max(0, stats["melee"] - self.reset_offset.get("melee", 0))
            stats["perks_drank"] = max(0, stats["perks_drank"] - self.reset_offset.get("perks_drank", 0))
            stats["rounds_added"] = max(0, stats["rounds_added"] - self.reset_offset.get("rounds_added", 0))
            stats["xp"] = max(0, stats["xp"] - self.reset_offset.get("xp", 0))

        changed = self._apply_stats_to_challenges(stats, game_timestamp=game_timestamp)

    def _is_challenge_in_time_window(self, challenge, game_timestamp=None):
        try:
            active_from = float(challenge.get("active_from", 0) or 0)
        except:
            active_from = 0
        if active_from <= 0 or game_timestamp is None:
            return True
        return float(game_timestamp) >= active_from

    def _challenge_matches_map(self, challenge, stats, full_stats=None):
        target = normalize_steam_link(
            challenge.get("map_steam_link")
            or challenge.get("steam_link")
            or challenge.get("workshop_id")
        )
        if not target:
            return False
        current_stats = full_stats if isinstance(full_stats, dict) else stats
        current = normalize_steam_link(current_stats.get("_steam_link") if isinstance(current_stats, dict) else "")
        if not (current and current == target):
            return False

        weapon_filter = challenge.get("weapon_console_name", "")
        if weapon_filter:
            weapons_data = self._get_weapons_data(stats, full_stats)
            if not self._weapon_in_data(weapon_filter, weapons_data):
                return False
        return True

    def _get_weapons_data(self, stats, full_stats=None):
        src = full_stats if isinstance(full_stats, dict) else stats
        return src.get("_weapons", {}) if isinstance(src, dict) else {}

    def _weapon_in_data(self, weapon_filter, weapons_data):
        if weapon_filter in weapons_data:
            return True
        up_variant = weapon_filter + "_up"
        if up_variant in weapons_data:
            return True
        upgraded_variant = weapon_filter + "_upgraded"
        if upgraded_variant in weapons_data:
            return True
        for k in weapons_data:
            base = k.rsplit("_up", 1)[0]
            if base and base == weapon_filter:
                return True
            if k.endswith("_upgraded") and k[:-9] == weapon_filter:
                return True
        return False

    def _get_weapon_stat_value(self, weapon_filter, stat_name, weapons_data):
        # Weapon data entries use "kills"/"headshots" keys, not "weapon_kills"/"weapon_headshots"
        if stat_name.startswith("weapon_"):
            stat_name = stat_name[len("weapon_"):]
        total = 0
        if weapon_filter in weapons_data:
            total += int(weapons_data[weapon_filter].get(stat_name, 0))
        up_variant = weapon_filter + "_up"
        if up_variant in weapons_data:
            total += int(weapons_data[up_variant].get(stat_name, 0))
        upgraded_variant = weapon_filter + "_upgraded"
        if upgraded_variant in weapons_data:
            total += int(weapons_data[upgraded_variant].get(stat_name, 0))
        for k, w in weapons_data.items():
            if k.startswith(weapon_filter + "_up_"):
                total += int(w.get(stat_name, 0))
        # Handle reverse: if weapon_filter is already an upgraded name, also sum base
        if weapon_filter.endswith("_upgraded"):
            base = weapon_filter[:-9]
            if base in weapons_data:
                total += int(weapons_data[base].get(stat_name, 0))
        elif weapon_filter.endswith("_up"):
            base = weapon_filter[:-3]
            if base in weapons_data:
                total += int(weapons_data[base].get(stat_name, 0))
        return total

    def _get_weapon_category_stat_value(self, weapon_category, stat_name, weapons_data):
        if stat_name.startswith("weapon_"):
            stat_name = stat_name[len("weapon_"):]
        target_category = normalise_weapon_category(weapon_category)
        total = 0
        for console_name, weapon_stats in weapons_data.items():
            if not isinstance(weapon_stats, dict):
                continue
            category = normalise_weapon_category(
                weapon_stats.get("category") or get_weapon_category(console_name, weapon_stats.get("display", ""))
            )
            if category != target_category:
                continue
            try:
                total += int(weapon_stats.get(stat_name, 0))
            except:
                continue
        return total

    def _get_challenge_weapon_stat_value(self, challenge, stats, full_stats=None):
        weapons_data = self._get_weapons_data(stats, full_stats)
        stat_name = str(challenge.get("stat", "kills"))
        weapon_category = str(challenge.get("weapon_category", "")).strip()
        weapon_filter = str(challenge.get("weapon_console_name", "")).strip()

        if weapon_category:
            current_total = self._get_weapon_category_stat_value(weapon_category, stat_name, weapons_data)
            ws_stat = stat_name[len("weapon_"):] if stat_name.startswith("weapon_") else stat_name
            generic_ws_key = f"category:{normalise_weapon_category(weapon_category)}|{ws_stat}"
        elif weapon_filter:
            current_total = self._get_weapon_stat_value(weapon_filter, stat_name, weapons_data)
            ws_stat = stat_name[len("weapon_"):] if stat_name.startswith("weapon_") else stat_name
            generic_ws_key = f"weapon:{weapon_filter}|{ws_stat}"
        else:
            return 0

        if full_stats:
            challenge_id = str(challenge.get("id", "")).strip()
            ws_key = f"{challenge_id}|{generic_ws_key}" if challenge_id else generic_ws_key
            last_total, last_game = self._weapon_stat_last.get(ws_key, (0, None))
            if last_game != self.live_game_id and generic_ws_key in self._weapon_stat_last:
                last_total, last_game = self._weapon_stat_last.get(generic_ws_key, (0, None))
            if last_game != self.live_game_id:
                last_total = 0
            val = current_total - last_total
            self._weapon_stat_last[ws_key] = (current_total, self.live_game_id)
            return val
        return current_total

    def _apply_map_stats_to_challenges(self, stats, full_stats=None, game_timestamp=None):
        changed = False
        for c in self.map_challenges:
            if c.get("completed"):
                continue
            if not self._is_challenge_in_time_window(c, game_timestamp):
                continue
            if not self._challenge_matches_map(c, stats, full_stats):
                continue

            weapon_filter = c.get("weapon_console_name", "")
            weapon_category = c.get("weapon_category", "")
            if weapon_filter or weapon_category:
                val = self._get_challenge_weapon_stat_value(c, stats, full_stats)
            else:
                if c.get("type") == "single_game" and full_stats:
                    val = full_stats.get(c.get("stat"), 0)
                else:
                    val = stats.get(c.get("stat"), 0)
            try:
                val = int(val)
            except:
                val = 0
            if val <= 0:
                continue

            if c.get("type") == "cumulative":
                next_progress = int(c.get("progress", 0)) + val
                c["progress"] = min(next_progress, int(c.get("target", 0)))
                c["completed"] = c["progress"] >= int(c.get("target", 0))
                changed = True
            elif c.get("type") == "single_game":
                if val >= int(c.get("target", 0)):
                    c["progress"] = int(c.get("target", 0))
                    c["completed"] = True
                    changed = True
                elif val > int(c.get("progress", 0)):
                    c["progress"] = val
                    changed = True
        return changed

    def _apply_stats_to_challenges(self, stats, full_stats=None, game_timestamp=None, include_map_challenges=False):
        changed = False
        map_changed = False
        chain_available = {chain: stats.copy() for chain in self.theme_requirements.keys()}
        if full_stats:
            chain_full = {chain: full_stats.copy() for chain in self.theme_requirements.keys()}

        for c in self.challenges:
            if not self._is_challenge_active(c['id']): continue
            if not self._is_challenge_in_time_window(c, game_timestamp): continue
            if c['completed']: continue 

            my_chain = None
            for chain_name, chain_list in self.theme_requirements.items():
                if c['id'] in chain_list:
                    my_chain = chain_name
                    break
                    
            if str(c.get("stat", "")).startswith("weapon_"):
                val = self._get_challenge_weapon_stat_value(c, stats, full_stats)
            elif my_chain:
                if c['type'] == 'single_game' and full_stats:
                    val = chain_full[my_chain].get(c['stat'], 0)
                else:
                    val = chain_available[my_chain].get(c['stat'], 0)
            else:
                if c['type'] == 'single_game' and full_stats:
                    val = full_stats.get(c['stat'], 0)
                else:
                    val = stats.get(c['stat'], 0)

            if val <= 0: continue

            if c['type'] == 'cumulative':
                if c['progress'] + val >= c['target']:
                    excess = (c['progress'] + val) - c['target']
                    c['progress'] = c['target']
                    c['completed'] = True
                    if my_chain:
                        chain_available[my_chain][c['stat']] = excess
                else:
                    c['progress'] += val
                    if my_chain:
                        chain_available[my_chain][c['stat']] = 0
                changed = True
            elif c['type'] == 'single_game':
                if val >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
                    changed = True
                elif val > c['progress']:
                    c['progress'] = val
                    changed = True

        if include_map_challenges:
            map_changed = self._apply_map_stats_to_challenges(stats, full_stats, game_timestamp)
        if changed:
            self.check_theme_unlocks()
            full = load_json(self.filepath)
            if not isinstance(full, dict): full = {}
            full["challenges"] = self.challenges
            full["weekly_rotation"] = self.weekly_rotation
            full["remote_weekly_pool"] = self.remote_weekly_pool
            full["remote_weekly_active_count"] = self.remote_weekly_active_count
            full["live_state"] = self.live_state
            save_json(self.filepath, full)
        if map_changed:
            self._save_map_challenges()
        return changed or map_changed

    def apply_live_update(self, game_id, p, game=None):
        game = game if isinstance(game, dict) else {}
        raw_perks = p.get('perks', [])
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        valid_perks = [x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x]

        stats = {
            "kills": int(p.get('kills', 0)),
            "headshots": int(p.get('headshots', 0)),
            "doors": int(p.get('doors_purchased', 0)),
            "round": int(game.get('rounds_total', p.get('round', 0))),
            "points": int(p.get('live_score_points_earned', 0)),
            "melee": int(p.get('melee_kills', 0)),
            "perks_drank": p.get('calculated_perks_drank', len(valid_perks)),
            "xp": int(p.get('match_xp_earned', 0)),
            "_steam_link": get_game_steam_link(game),
            "_map_name": str(game.get("map_played", game.get("map_name", "Unknown")) or "Unknown"),
            "_weapons": extract_weapon_stats(p, get_game_steam_link(game)),
        }

        if game_id != self.live_game_id:
            self.live_game_id = game_id
            restored = self._restore_live_baseline(game_id)
            if not restored:
                self.live_snapshot = {s: 0 for s in ("kills", "headshots", "melee", "xp", "points", "round", "perks_drank")}
                for ls in ("doors",):
                    self.live_snapshot[ls] = self._lifetime_high_water.get(ls, 0)

        delta = {}
        for stat, val in stats.items():
            if str(stat).startswith("_"):
                continue
            last = self.live_snapshot.get(stat, 0)
            if val > last:
                d = val - last
                if stat in ("doors",) and d > 10:
                    self._lifetime_high_water[stat] = val
                    continue
                delta[stat] = d

        if not delta:
            for stat, val in stats.items():
                if str(stat).startswith("_"):
                    self.live_snapshot[stat] = val
                    continue
                last = self.live_snapshot.get(stat, 0)
                if val != last:
                    self.live_snapshot[stat] = val
            for ls in ("doors",):
                self._lifetime_high_water[ls] = max(self._lifetime_high_water.get(ls, 0), stats.get(ls, 0))
            self._save_live_state(game_id, stats)
            return

        self._apply_stats_to_challenges(delta, full_stats=stats, include_map_challenges=True)
        self.live_snapshot = stats
        for ls in ("doors",):
            self._lifetime_high_water[ls] = max(self._lifetime_high_water.get(ls, 0), stats.get(ls, 0))
        self._save_live_state(game_id, stats)

    def reset_all_challenges(self, live_data=None):
        for c in self.challenges:
            c['progress'] = 0
            c['completed'] = False
        for c in self.map_challenges:
            c['progress'] = 0
            c['completed'] = False
        
        self.unlocked_rewards = ["default"]
        save_json(self.unlocks_path, self.unlocked_rewards)
        
        self.reset_timestamp = time.time()
        self.reset_offset = {}
        self.live_state = {}
        
        # Snapshot current live game stats
        if live_data:
            game = live_data.get('game') or live_data.get('data', {}).get('game', {})
            players = live_data.get('players') or live_data.get('data', {}).get('players', {})
            if players:
                p = list(players.values())[0]
                game_id = str(game.get('game_id', ''))
                if game_id:
                    raw_perks = p.get('perks', [])
                    valid_perks_count = 0
                    if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
                    if raw_perks:
                         valid_perks_count = len([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
                    
                    self.reset_offset = {
                        "game_id": game_id,
                        "kills": int(p.get('kills', 0)),
                        "headshots": int(p.get('headshots', 0)),
                        "doors": int(p.get('doors_purchased', 0)),
                        "round": int(game.get('rounds_total', 0)),
                        "points": int(p.get('live_score_points_earned', 0)),
                        "melee": int(p.get('melee_kills', 0)),
                        "perks_drank": live_data.get('calculated_perks_drank', valid_perks_count),
                        "rounds_added": int(game.get('rounds_total', 0)),
                        "xp": int(p.get('match_xp_earned', 0))
                    }
        
        full = {
            "challenges": self.challenges,
            "reset_timestamp": self.reset_timestamp,
            "reset_offset": self.reset_offset,
            "live_state": self.live_state,
            "weekly_rotation": self.weekly_rotation,
            "remote_weekly_pool": self.remote_weekly_pool,
            "remote_weekly_active_count": self.remote_weekly_active_count
        }
        save_json(self.filepath, full)
        self._save_map_challenges()
        return True

    def scan_all_history(self, history_path):
        self.process_update(history_path)
