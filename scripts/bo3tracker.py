import os
import json
import glob
import time
import base64
import threading
import webview # pip install pywebview
import sys
import zipfile # --- NEW IMPORT FOR BACKUPS ---
from pathlib import Path

# --- CUSTOM IMPORTS ---
from challenge_system import ChallengeManager
from match_xp import xp_tracker_instance
from xpm_grapher import xpm_grapher_instance
from workshop_images import get_workshop_image

# --- CONSTANTS ---
CONFIG_FILE = "config.json"
BEST_MATCHES_FILE = "best_matches.json"
DAMAGE_HISTORY_FILE = "damage_history.json"
ICONS_DIR_NAME = "perk icons" 
RANK_ICONS_DIR_NAME = "rank icons"
CAMO_DB_FILE = "custom_camos.json"
CAMO_IMG_DIR = "camoimages"
CALLING_CARD_DIR = "callingcards"
CSS_MAIN_FILE = "style.css"
CSS_SETUP_FILE = "setup.css"
THEMES_DIR = "themes"

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
IGNORE_KEYWORDS = [ "null", "specialty_pistoldeath"]

CAMO_NAMES = [
    "Gold Camo", "Diamond Camo", "Glacial Frost", "Oil Slick", "Nebula Shroud",
    "Liquid Midnight", "Icy Stellar", "Galaxy Stars", "Blood Camo", "Enchanted Emerald",
    "Orion's Veil", "Stellar Eclipse", "Deep Depth", "Yellow Maelstrom", "Astral Red Storm",
    "Green Aurora", "White Cosmos", "Andromeda Drift", "Acidic Radiance", "Galactic Amethyst",
    "Electralized Diamonds"
]

OVERLAY_THEMES = {
    "default": {
        "bg": "#0b0c10", "panel": "#0b0c10", "border": "#66fcf1",
        "title": "#66fcf1", "text": "#ffffff", "muted": "#777777",
        "damage": "#ff9d00", "divider": "#333333", "fallback": "#333333",
        "shadow": "0 0 10px rgba(102, 252, 241, 0.25)"
    },
    "void": {
        "bg": "#050510", "panel": "#100b22", "border": "#7b4397",
        "title": "#e0b0ff", "text": "#f3eaff", "muted": "#9b86c7",
        "damage": "#b19cd9", "divider": "#352253", "fallback": "#231437",
        "shadow": "0 0 16px rgba(148, 0, 211, 0.35)"
    },
    "115_Origins": {
        "bg": "#071018", "panel": "#0b1824", "border": "#00a8ff",
        "title": "#58a6ff", "text": "#d7f3ff", "muted": "#7e9db5",
        "damage": "#ffb347", "divider": "#19384c", "fallback": "#13293a",
        "shadow": "0 0 14px rgba(0, 168, 255, 0.28)"
    },
    "RedHex": {
        "bg": "#120606", "panel": "#1a0808", "border": "#ff3333",
        "title": "#ff7777", "text": "#fff0f0", "muted": "#aa7777",
        "damage": "#ffcc00", "divider": "#4a1515", "fallback": "#2a1010",
        "shadow": "0 0 14px rgba(255, 0, 0, 0.3)"
    },
    "Golden Divinium": {
        "bg": "#151004", "panel": "#201806", "border": "#ffd700",
        "title": "#fff3a6", "text": "#fff8d8", "muted": "#b8a45d",
        "damage": "#ffd700", "divider": "#5a4610", "fallback": "#382a08",
        "shadow": "0 0 14px rgba(255, 215, 0, 0.28)"
    },
    "retro": {
        "bg": "#080416", "panel": "#100725", "border": "#00f2ff",
        "title": "#ff00ff", "text": "#f3f3ff", "muted": "#9d8dcc",
        "damage": "#00f2ff", "divider": "#36215f", "fallback": "#211238",
        "shadow": "0 0 16px rgba(255, 0, 255, 0.3)"
    },
    "matrix": {
        "bg": "#000800", "panel": "#031203", "border": "#00ff00",
        "title": "#88ff88", "text": "#d8ffd8", "muted": "#5f9f5f",
        "damage": "#00ff00", "divider": "#0c3a0c", "fallback": "#071f07",
        "shadow": "0 0 14px rgba(0, 255, 0, 0.28)"
    },
    "trench": {
        "bg": "#100d09", "panel": "#1c1710", "border": "#c9bca7",
        "title": "#d4b56a", "text": "#f1e5d0", "muted": "#9b8f7a",
        "damage": "#d4b56a", "divider": "#453927", "fallback": "#2b2419",
        "shadow": "0 0 12px rgba(201, 188, 167, 0.22)"
    },
    "neon_pulse": {
        "bg": "#050514", "panel": "#0a0a1e", "border": "#00f5ff",
        "title": "#ff00ff", "text": "#effcff", "muted": "#84a9b7",
        "damage": "#00f5ff", "divider": "#26315a", "fallback": "#12142e",
        "shadow": "0 0 18px rgba(0, 245, 255, 0.35)"
    }
}

# --- GLOBAL STATE ---
app_config = {}
window = None
# -- OVERLAY GLOBALS --
unified_window = None
stop_overlays = False
xp_debug_window = None
xp_debug_rows = []
xp_debug_lock = threading.Lock()
# ---------------------
CAMO_ICON_CACHE = None 

# --- PATH HELPERS ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# --- FILE HELPERS ---
def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return None

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except: return False

def load_css(filename):
    try:
        path = os.path.join(get_base_path(), filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    except: pass
    return "/* CSS FILE NOT FOUND */"

def sanitize_filename(name):
    return str(name).replace(":", "_").replace("|", "_").replace("/", "_").replace("\\", "_")

def get_base64_icon(perk_key):
    base_dir = get_base_path()
    icons_folder = os.path.join(base_dir, ICONS_DIR_NAME)
    for ext in [".webp", ".png"]:
        target = os.path.join(icons_folder, perk_key + ext)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    mime = "image/webp" if ext == ".webp" else "image/png"
                    return "data:" + mime + ";base64," + b64
            except: pass
    return None

def get_rank_icon_base64(filename):
    base_dir = get_base_path()
    target = os.path.join(base_dir, RANK_ICONS_DIR_NAME, filename)
    if os.path.exists(target):
        try:
            with open(target, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{b64}"
        except: pass
    return None

def get_tier_icon_src(tier_type, tier_value):
    safe_val = int(tier_value)
    if safe_val <= 0: 
        return None
    img_name = f"ui_icon_rank_tier_{tier_type}_{safe_val}_large.png"
    return get_rank_icon_base64(img_name)

def get_prestige_icon_src(prestige):
    safe_prestige = min(max(int(prestige), 0), 20)
    if safe_prestige == 0: return None
    img_name = f"ui_icon_ranks_prestige_{safe_prestige}_large.png"
    return get_rank_icon_base64(img_name)

def get_level_icon_src(level):
    lvl = int(level)
    if lvl < 100:
        safe_level = min(max(lvl, 1), 90)
        img_name = f"ui_icon_rank_mp_level{safe_level}_large.png"
    else:
        rank_tier = (lvl // 100) * 100 
        img_name = f"ui_icon_rank_mp_level{rank_tier}_large.png"
        
    return get_rank_icon_base64(img_name)
    
def get_camo_image_src(index):
    base_dir = get_base_path()
    img_name = f"camo_{index}.png"
    target = os.path.join(base_dir, CAMO_IMG_DIR, img_name)
    if os.path.exists(target):
        try:
            with open(target, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{b64}"
        except: pass
    return None

def get_calling_card_src(card_name):
    if not card_name or card_name == "default": return None
    base_dir = get_base_path()
    for ext in [".mp4", ".webm", ".jpg", ".png", ".webp"]:
        img_name = f"{card_name}{ext}"
        target = os.path.join(base_dir, CALLING_CARD_DIR, img_name)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    mime = ""
                    if ext == ".mp4": mime = "video/mp4"
                    elif ext == ".webm": mime = "video/webm"
                    elif ext == ".jpg": mime = "image/jpeg"
                    else: mime = f"image/{ext[1:]}"
                    
                    return f"data:{mime};base64,{b64}"
            except: pass
    return None

def get_overlay_theme(theme_name=None):
    theme_key = theme_name or app_config.get('active_theme', 'default')
    return OVERLAY_THEMES.get(theme_key, OVERLAY_THEMES["default"])

def get_game_summary(data, fallback_id=None, fallback_date=None):
    game = data.get('game') or data.get('data', {}).get('game', {}) if data else {}
    players = data.get('players') or data.get('data', {}).get('players', {}) if data else {}
    game_id = str(game.get('game_id', fallback_id or 'unknown'))
    map_name = str(game.get('map_played', 'Unknown Map')).replace('_', ' ').title()
    rounds = int(game.get('rounds_total', 0))
    time_sec = int(game.get('time_total', 0))
    mins, secs = divmod(time_sec, 60)
    hours, mins = divmod(mins, 60)
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m {secs}s"
    p0 = players.get('0', next(iter(players.values()), {})) if players else {}
    match_xp = int(p0.get('match_xp_earned', 0)) if p0 else 0
    return {
        "id": game_id,
        "map": map_name,
        "round": rounds,
        "time": time_str,
        "match_xp": match_xp,
        "date": fallback_date or ""
    }

def get_best_matches_path():
    return os.path.join(get_base_path(), BEST_MATCHES_FILE)

def load_best_matches():
    raw = load_json(get_best_matches_path()) or []
    if isinstance(raw, dict):
        raw = raw.get("matches", [])
    matches = []
    seen = set()
    for item in raw:
        if isinstance(item, str):
            item = {"id": item}
        if not isinstance(item, dict) or not item.get("id"):
            continue
        item["id"] = str(item["id"])
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        matches.append(item)
    return matches

def save_best_matches(matches):
    return save_json(get_best_matches_path(), matches)

# --- MULTI-PLAYER DAMAGE MEMORY SYSTEM ---
class DamageMemory:
    def __init__(self):
        self.file_path = os.path.join(get_base_path(), DAMAGE_HISTORY_FILE)
        self.cache = self._load_from_disk()
        self.lock = threading.Lock()

    def _load_from_disk(self):
        return load_json(self.file_path) or {}

    def _save_to_disk(self):
        save_json(self.file_path, self.cache)

    def get_real_damage(self, game_id, player_id, weapon_name, current_raw_val):
        with self.lock:
            if game_id not in self.cache:
                self.cache[game_id] = {}

            if player_id not in self.cache[game_id]:
                self.cache[game_id][player_id] = {}

            if weapon_name not in self.cache[game_id][player_id]:
                self.cache[game_id][player_id][weapon_name] = {
                    "last_seen": 0,
                    "overflow_offset": 0
                }

            w_data = self.cache[game_id][player_id][weapon_name]
            last_val = w_data["last_seen"]
            offset = w_data["overflow_offset"]
            
            if current_raw_val < last_val:
                if (last_val - current_raw_val) > 100000:
                    offset += 4294967296
                    w_data["overflow_offset"] = offset
                    self._save_to_disk() 

            w_data["last_seen"] = current_raw_val
            self.cache[game_id][player_id][weapon_name] = w_data
            return current_raw_val + offset

# Initialize Systems
damage_tracker = DamageMemory()
challenge_manager = ChallengeManager(get_base_path()) 

# --- DATA PROCESSOR (MULTI-PLAYER STATS) ---
def process_stats(data, is_live=False):
    if not data: return None
    
    game = data.get('game') or data.get('data', {}).get('game', {})
    players = data.get('players') or data.get('data', {}).get('players', {})
    game_id = str(game.get('game_id', 'unknown_match'))
    
    time_sec = int(game.get('time_total', 0))
    mins, secs = divmod(time_sec, 60)
    
    status_text = "LIVE FEED" if is_live else f"ARCHIVED: {game.get('game_id')}"
    status_color = "#66fcf1" if is_live else "#444" 

    nerf_html = ""
    if str(game.get('nerfed')) == "1":
        reason = str(game.get('nerfed_reason', '')).replace('|', ' ')
        nerf_html = f"<div class='nerf-box'>⚠ ACTIVE MODIFIERS: {reason}</div>"

    game_info = {
        "id": game_id,
        "status": status_text, "color": status_color, "nerf": nerf_html,
        "map": str(game.get('map_played', 'Unknown')).replace('_',' ').title(), 
        "round": game.get('rounds_total', 0),
        "time": "{:02d}:{:02d}".format(mins, secs), "mode": game.get('gamemode', 'Standard'),
        "version": str(game.get('version', 'Unknown')), 
        "avg_time": str(game.get('average_round_time', '0')),
        "zpm": str(game.get('zpm', '0')),
        "steam_link": str(game.get('steam_link', ''))
    }

    players_list = []
    
    for pid, p in players.items():
        kills = int(p.get('kills', 0))
        headshots = int(p.get('headshots', 0))
        accuracy = round((headshots / kills) * 100, 1) if kills > 0 else 0
        xp_val = int(p.get('xp', p.get('total_xp', 0)))
        
        try:
            raw_mult = game.get('xp_multiplier') or p.get('xp_multiplier') or "100"
            xp_mult = "x{:.3f}".format(float(raw_mult) / 100.0)
        except:
            xp_mult = "x1.000"

        ult = int(p.get('prestige_ultimate', 0))
        abso = int(p.get('prestige_absolute', 0))
        leg = int(p.get('prestige_legend', 0))
        prest = int(p.get('prestige', 0))
        lvl = int(p.get('level', 1))
        
       # --- NEW MATCH XP & XPM LOGIC ---
        if 'match_xp_earned' in p:
            match_xp_earned = int(p['match_xp_earned']) 
        elif is_live:
            # Only calculate/track memory if it is the active live game
            match_xp_earned = xp_tracker_instance.calculate_match_xp(game_id, pid, prest, lvl, xp_val)
        else:
            # It's an old archive. Do not trigger the calculator.
            match_xp_earned = 0 
            
        match_xp_str = "{:,}".format(match_xp_earned)

        # Calculate XP per Minute (XPM)
        xp_per_min = 0
        if time_sec > 0:
            xp_per_min = int(match_xp_earned / (time_sec / 60.0))
        xpm_str = "{:,}".format(xp_per_min)
        # --------------------------------
        
        # New Tier Icons
        ult_icon = get_tier_icon_src("ultimate", ult)
        abso_icon = get_tier_icon_src("absolute", abso)
        leg_icon = get_tier_icon_src("legend", leg)
        
        prestige_icon = get_prestige_icon_src(prest)
        level_icon = get_level_icon_src(lvl)

        if ult > 0: rank_main = "ULTIMATE PRESTIGE"
        elif abso > 0: rank_main = "ABSOLUTE PRESTIGE"
        elif leg > 0: rank_main = "PRESTIGE LEGEND"
        elif prest > 0: rank_main = f"PRESTIGE {prest}"
        else: rank_main = "RECRUIT"

        rank_parts = []
        if ult > 0: rank_parts.append(f"Ult Tier {ult}")
        if abso > 0: rank_parts.append(f"Abs Tier {abso}")
        if leg > 0: rank_parts.append(f"Leg Tier {leg}")
        if prest > 0: rank_parts.append(f"Prestige {prest}")
        rank_parts.append(f"Level {lvl}")
        
        rank_sub = " // ".join(rank_parts)
        player_title = '"{}"'.format(p.get("player_title", "")) if p.get("player_title") else ""

        perks_html = ""
        raw_perks = p.get('perks', [])
        valid_perk_count = 0 
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        for perk in raw_perks:
            if any(x in perk.lower() for x in IGNORE_KEYWORDS): continue
            pretty = PERK_NAMES.get(perk, perk.replace('specialty_', '').replace('_', ' ').title())
            if "null" in pretty.lower(): continue
            
            valid_perk_count += 1
            icon_b64 = get_base64_icon(perk)
            if icon_b64: perks_html += f'<div class="perk-item"><img src="{icon_b64}" class="perk-img" title="{pretty}"></div>'
            else: perks_html += f'<div class="perk-item"><div class="perk-fallback" style="font-size:0.5em; text-align:center;">{pretty[:3]}</div></div>'
        if not perks_html: perks_html = "<span style='color:#555; font-style:italic;'>No Active Perks</span>"

        weapons_html = ""
        weapons = p.get('top5', p.get('weapon_data', {}))
        processed_weapons = []
        
        for k, w in weapons.items():
            if w.get('display') == 'none': continue
            
            is_pap = (int(w.get('repack_level', 0)) > 0) or (w.get('display_name_upgraded') and w.get('display_name_upgraded') != "none")
            status_html = '<span style="color:#66fcf1; font-weight:bold;">PAP</span>' if is_pap else '<span style="color:#888">STD</span>'
            dname = str(w.get('display', 'Unknown'))
            kills_w = str(w.get('kills', 0))
            headshots_w = str(w.get('headshots', 0)) 
            
            try: raw_damage = int(float(w.get('damage', 0)))
            except: raw_damage = 0
                
            corrected_damage = damage_tracker.get_real_damage(game_id, pid, k, raw_damage)
            
            processed_weapons.append({
                "name": dname,
                "kills": kills_w,
                "headshots": headshots_w,
                "damage_val": corrected_damage, 
                "damage_str": "{:,}".format(corrected_damage),
                "status": status_html
            })

        processed_weapons.sort(key=lambda x: x['damage_val'], reverse=True)

        for pw in processed_weapons:
            weapons_html += f"<tr><td>{pw['name']}</td><td>{pw['kills']}</td><td>{pw['headshots']}</td><td>{pw['damage_str']}</td><td>{pw['status']}</td></tr>"

        equip = p.get('equipment', {})
        lethal = equip.get('lethal', {}).get('name', 'None').replace('_', ' ').title()
        tactical = equip.get('tactical', {}).get('name', 'None').replace('_', ' ').title()
        
        # --- NEW: EXTRACT GRAPH DATA ---
        if is_live:
            # Grab the actively tracked history from Python memory for the live game
            round_history = xpm_grapher_instance.live_history.get(game_id, {}).get(pid, {})
        else:
            # Grab the saved history from the JSON file for archived games
            round_history = p.get('round_history', {})
            
        graph_data = xpm_grapher_instance.generate_graph_data(round_history)
        round_xp_data = xpm_grapher_instance.generate_xp_per_round_data(round_history)
        zpm_graph_data = xpm_grapher_instance.generate_zpm_data(round_history)
        # -------------------------------

        players_list.append({
            "pid": pid,
            "r_main": rank_main, "title": player_title, "r_sub": rank_sub, 
            "ult_icon": ult_icon, "abso_icon": abso_icon, "leg_icon": leg_icon, 
            "prest_icon": prestige_icon, "lvl_icon": level_icon,
            "gums": p.get('gobblegums_used', 0), 
            
            # --- MODIFIED XP LINE ---
            "xp": f"{xp_val:,} (+{match_xp_str} Match XP | {xpm_str} XP/min)",
            "mult": xp_mult,
            # ------------------------
            
            "k": kills, "pts": "{:,}".format(int(p.get('points', 0))), "acc": accuracy,
            "melee": p.get('melee_kills', 0), "equip": p.get('equipment_kills', 0), "downs": p.get('downs', 0),
            "perks": perks_html, "perk_count": valid_perk_count, "leth": lethal, "tact": tactical, "weaps": weapons_html,
            
            # --- NEW: APPEND TO UI DATA ---
            "graph_labels": graph_data["labels"],
            "graph_data": graph_data["data"],
            "round_xp_labels": round_xp_data["labels"],
            "round_xp_data": round_xp_data["data"],
            "zpm_labels": zpm_graph_data["labels"],
            "zpm_data": zpm_graph_data["data"]
            # ------------------------------
        })

    return {
        "game": game_info,
        "players": players_list
    }

# --- PROCESSOR (CAMO STATS) ---
def process_camo_data(user_json_path):
    global CAMO_ICON_CACHE
    master_path = os.path.join(get_base_path(), CAMO_DB_FILE)
    if not os.path.exists(master_path):
        return {"error": "Database file 'custom_camos.json' not found."}
    
    master_list = load_json(master_path)
    if not master_list: return {"error": "Database loaded but contains 0 weapons."}
    
    user_progress = {}
    username = "GUEST"
    
    if user_json_path and os.path.exists(user_json_path):
        user_data = load_json(user_json_path)
        username = user_data.get('username', 'Unknown')
        user_progress = user_data.get('progress', {})
    
    starred_list = app_config.get('starred', [])

    if CAMO_ICON_CACHE is None:
        CAMO_ICON_CACHE = []
        for i in range(len(CAMO_NAMES)):
            img_data = get_camo_image_src(i + 1)
            CAMO_ICON_CACHE.append(img_data) 

    grouped_data = {}
    
    for weapon in master_list:
        map_name = weapon.get('map', 'Unknown Sector')
        if not map_name: map_name = "Unknown Sector"
        
        if map_name not in grouped_data:
            grouped_data[map_name] = {"weapons": [], "total_levels": 0, "current_levels": 0}
            
        w_id = str(weapon.get('id'))
        val = user_progress.get(w_id, user_progress.get(int(w_id), 0))
        
        max_val = 20
        current_val = int(val)
        
        grouped_data[map_name]["total_levels"] += max_val
        grouped_data[map_name]["current_levels"] += current_val
        
        camo_name = CAMO_NAMES[current_val] if current_val < len(CAMO_NAMES) else "Unknown Camo"
        
        weapon_entry = {
            "id": w_id,
            "name": str(weapon.get('name', 'Unknown') or 'Unknown'),
            "type": str(weapon.get('type', 'Weapon') or 'Weapon'),
            "packed": str(weapon.get('packedName', '')),
            "gametype": str(weapon.get('GameType', '')),
            "camo_name": camo_name,
            "camo_val": current_val,
            "is_starred": (w_id in starred_list)
        }
        grouped_data[map_name]["weapons"].append(weapon_entry)

    for map_key in grouped_data:
        grouped_data[map_key]["weapons"].sort(key=lambda x: (x['type'], x['name']))

    return {
        "username": username, 
        "camo_icons": CAMO_ICON_CACHE, 
        "camo_names": CAMO_NAMES,
        "maps": grouped_data,
        "weapon_count": len(master_list)
    }

# --- UNIFIED OVERLAY SYSTEM ---
def get_unified_overlay_html():
    initial_theme_json = json.dumps(get_overlay_theme())
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            :root {
                --overlay-bg: #0b0c10;
                --overlay-panel: #0b0c10;
                --overlay-border: #66fcf1;
                --overlay-title: #66fcf1;
                --overlay-text: #ffffff;
                --overlay-muted: #777777;
                --overlay-damage: #ff9d00;
                --overlay-divider: #333333;
                --overlay-fallback: #333333;
                --overlay-shadow: 0 0 10px rgba(102, 252, 241, 0.25);
            }
            html, body {
                margin: 0; padding: 0; overflow: hidden;
                background-color: var(--overlay-bg) !important;
            }
            #unified-box {
                display: inline-flex; flex-direction: column;
                background: var(--overlay-panel); border: 2px solid var(--overlay-border);
                padding: 12px; box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif; color: var(--overlay-text);
                width: 100%; height: 100%;
                box-shadow: var(--overlay-shadow);
            }
            #perk-area {
                display: flex; flex-wrap: wrap; justify-content: center;
                gap: 5px; margin-bottom: 10px; min-height: 45px;
            }
            .perk-item img { width: 40px; height: 40px; object-fit: contain; filter: drop-shadow(0 0 2px rgba(0,0,0,0.5)); }
            .perk-fallback {
                width: 40px; height: 40px; background: var(--overlay-fallback); color: var(--overlay-text); 
                display: flex; align-items: center; justify-content: center; font-size: 10px; 
                border-radius: 50%; border: 1px solid var(--overlay-border);
            }
            #damage-area { border-top: 1px solid var(--overlay-divider); padding-top: 8px; }
            .title { font-size: 10px; color: var(--overlay-title); margin-bottom: 5px; letter-spacing: 1px; font-weight: bold; text-transform: uppercase; }
            .row { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; }
            .name { font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
            .dmg { color: var(--overlay-damage); font-weight: bold; margin-left: 10px; }
        </style>
    </head>
    <body>
        <div id="unified-box">
            <div id="perk-area"></div>
            <div id="damage-area">
                <div class="title">Top Weapon Damage (Player 1)</div>
                <div id="damage-list"></div>
            </div>
        </div>
        <script>
            const INITIAL_OVERLAY_THEME = """ + initial_theme_json + """;

            function applyOverlayTheme(theme) {
                if (!theme) return;
                const root = document.documentElement;
                const keys = {
                    bg: '--overlay-bg',
                    panel: '--overlay-panel',
                    border: '--overlay-border',
                    title: '--overlay-title',
                    text: '--overlay-text',
                    muted: '--overlay-muted',
                    damage: '--overlay-damage',
                    divider: '--overlay-divider',
                    fallback: '--overlay-fallback',
                    shadow: '--overlay-shadow'
                };
                Object.keys(keys).forEach(key => {
                    if (theme[key]) root.style.setProperty(keys[key], theme[key]);
                });
            }

            function updateOverlay(perkHtml, damageItems) {
                document.getElementById('perk-area').innerHTML = perkHtml;
                let dHtml = "";
                if (damageItems && damageItems.length > 0) {
                    damageItems.forEach(i => {
                        dHtml += `<div class="row"><div class="name">${i.name}</div><div><span>K: ${i.kills}</span><span class="dmg">${i.damage_str}</span></div></div>`;
                    });
                } else {
                    dHtml = "<div style='color:#777; font-size:11px; font-style:italic;'>Waiting for data...</div>";
                }
                document.getElementById('damage-list').innerHTML = dHtml;
            }

            applyOverlayTheme(INITIAL_OVERLAY_THEME);
        </script>
    </body>
    </html>
    """

def overlay_loop():
    global unified_window, stop_overlays
    
    while not stop_overlays:
        if unified_window:
            path = app_config.get('live_path')
            if path and os.path.exists(path):
                try:
                    data = load_json(path)
                    stats = process_stats(data, is_live=True)
                    
                    if stats and stats['players']:
                        # Lock Overlay to Player 1 to save screen real estate
                        p_stats = stats['players'][0]
                        pid = p_stats['pid']
                        
                        game = data.get('game') or data.get('data', {}).get('game', {})
                        game_id = str(game.get('game_id', 'unknown'))
                        players = data.get('players') or data.get('data', {}).get('players', {})
                        top_3_weapons = []
                        
                        if players and pid in players:
                            p = players[pid]
                            weapons = p.get('top5', p.get('weapon_data', {}))
                            processed = []
                            for k, w in weapons.items():
                                if w.get('display') == 'none': continue
                                dname = str(w.get('display', 'Unknown'))
                                try: raw_dmg = int(float(w.get('damage', 0)))
                                except: raw_dmg = 0
                                
                                real_dmg = damage_tracker.get_real_damage(game_id, pid, k, raw_dmg)
                                
                                processed.append({
                                    "name": dname,
                                    "kills": str(w.get('kills', 0)),
                                    "damage": real_dmg,
                                    "damage_str": "{:,}".format(real_dmg)
                                })
                            processed.sort(key=lambda x: x['damage'], reverse=True)
                            top_3_weapons = processed[:3]

                        json_dmg = json.dumps(top_3_weapons)
                        json_perks = json.dumps(p_stats["perks"])
                        json_theme = json.dumps(get_overlay_theme())
                        unified_window.evaluate_js(f'applyOverlayTheme({json_theme}); updateOverlay({json_perks}, {json_dmg});')
                        
                        import math
                        perk_count = p_stats.get('perk_count', 0)
                        rows = math.ceil(perk_count / 5) if perk_count > 0 else 1
                        calc_height = 130 + (rows * 45)
                        unified_window.resize(280, int(calc_height))
                                
                except Exception as e:
                    print(f"Unified Overlay Error: {e}")
        
        time.sleep(2)

def toggle_overlays_logic(enable):
    global unified_window, stop_overlays
    
    if enable:
        stop_overlays = False
        if unified_window is None:
            unified_window = webview.create_window(
                'BO3 Overlay', 
                html=get_unified_overlay_html(), 
                width=280, height=300,
                x=50, y=100,
                frameless=True, 
                on_top=True, 
                transparent=False 
            )
        
        t = threading.Thread(target=overlay_loop)
        t.daemon = True
        t.start()
        
    else:
        stop_overlays = True
        if unified_window:
            unified_window.destroy()
            unified_window = None

def push_overlay_theme():
    if not unified_window:
        return
    try:
        unified_window.evaluate_js(f'applyOverlayTheme({json.dumps(get_overlay_theme())});')
    except Exception:
        pass

def get_xp_debugger_html():
    return """
    <html>
    <head>
        <style>
            body { margin:0; background:#07070d; color:#eee; font-family:Consolas, monospace; font-size:12px; }
            header { display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid #28213a; background:#11101a; }
            h1 { font-size:15px; margin:0; color:#c084fc; letter-spacing:0; }
            .status { color:#66fcf1; font-size:11px; }
            table { width:100%; border-collapse:collapse; }
            th, td { padding:7px 8px; border-bottom:1px solid #1e1b2c; text-align:left; white-space:nowrap; }
            th { color:#aaa; background:#0d0c14; position:sticky; top:0; }
            tr.rank-change td { color:#ffcc66; }
            .num { text-align:right; }
            .zero { color:#ff7777; }
        </style>
    </head>
    <body>
        <header>
            <h1>XP Round Debugger</h1>
            <div class="status" id="status">Waiting for live XP updates...</div>
        </header>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Game ID</th>
                    <th>Map</th>
                    <th>Player</th>
                    <th class="num">Round</th>
                    <th class="num">Prestige</th>
                    <th class="num">Level</th>
                    <th class="num">Level XP</th>
                    <th class="num">Tick XP</th>
                    <th class="num">Round XP</th>
                    <th class="num">Match XP</th>
                    <th>XP Math</th>
                    <th>Rank Change</th>
                </tr>
            </thead>
            <tbody id="rows"></tbody>
        </table>
        <script>
            function fmt(n) {
                if (n === null || n === undefined) return "";
                return Number(n).toLocaleString();
            }

            function esc(v) {
                return String(v ?? "").replace(/[&<>"']/g, ch => ({
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                    "'": "&#39;"
                }[ch]));
            }

            function updateXpDebug(rows) {
                const body = document.getElementById("rows");
                document.getElementById("status").innerText = rows.length + " round snapshots";
                body.innerHTML = rows.map(r => {
                    const tickClass = r.tick_xp === 0 ? "zero" : "";
                    const roundClass = r.round_xp === 0 ? "zero" : "";
                    const rowClass = r.rank_changed ? "rank-change" : "";
                    return `<tr class="${rowClass}">
                        <td>${esc(r.updated_at)}</td>
                        <td title="${esc(r.game_id)}">${esc(r.short_game_id)}</td>
                        <td>${esc(r.map_name)}</td>
                        <td>${esc(r.player_id)}</td>
                        <td class="num">${fmt(r.round)}</td>
                        <td class="num">${fmt(r.prestige)}</td>
                        <td class="num">${fmt(r.level)}</td>
                        <td class="num">${fmt(r.current_xp)}</td>
                        <td class="num ${tickClass}">${fmt(r.tick_xp)}</td>
                        <td class="num ${roundClass}">${fmt(r.round_xp)}</td>
                        <td class="num">${fmt(r.total_match_xp)}</td>
                        <td>${esc(r.xp_math_label)}</td>
                        <td>${esc(r.rank_change_label)}</td>
                    </tr>`;
                }).join("");
            }
        </script>
    </body>
    </html>
    """

def _publish_xp_debug_rows():
    global xp_debug_window
    if not xp_debug_window:
        return
    try:
        with xp_debug_lock:
            rows = list(xp_debug_rows)
        xp_debug_window.evaluate_js(f"updateXpDebug({json.dumps(rows)})")
    except Exception:
        pass

def record_xp_debug(snapshot, current_round, current_time, map_name="Unknown"):
    if not app_config.get('xp_debugger_enabled', False) or not snapshot:
        return

    game_id = str(snapshot.get("game_id", "unknown"))
    player_id = str(snapshot.get("player_id", "0"))
    current_round = int(current_round)
    total_match_xp = int(snapshot.get("total_match_xp", 0))
    key = f"{game_id}|{player_id}|{current_round}"

    with xp_debug_lock:
        previous_round_totals = [
            int(row.get("total_match_xp", 0))
            for row in xp_debug_rows
            if row.get("game_id") == game_id
            and row.get("player_id") == player_id
            and int(row.get("round", 0)) < current_round
        ]
        previous_round_total = previous_round_totals[-1] if previous_round_totals else 0
        round_xp = total_match_xp - previous_round_total
        if round_xp < 0:
            round_xp = 0

        previous_level = snapshot.get("previous_level")
        previous_prestige = snapshot.get("previous_prestige")
        prestige = snapshot.get("prestige")
        level = snapshot.get("level")
        rank_changed = (
            previous_level is not None
            and (previous_level != level or previous_prestige != prestige)
        )
        rank_change_label = ""
        if rank_changed:
            rank_change_label = f"P{previous_prestige} L{previous_level} -> P{prestige} L{level}"

        rollover = snapshot.get("rollover_debug") or {}
        xp_math_label = ""
        if rollover:
            remaining = int(rollover.get("remaining_previous_level", 0))
            skipped = int(rollover.get("skipped_level_xp", 0))
            current_progress = int(rollover.get("current_level_progress", 0))
            parts = [f"{remaining:,} remaining"]
            if skipped:
                parts.append(f"{skipped:,} skipped")
            parts.append(f"{current_progress:,} level XP")
            xp_math_label = " + ".join(parts)

        row = {
            "key": key,
            "updated_at": time.strftime("%H:%M:%S"),
            "game_id": game_id,
            "short_game_id": game_id[-18:] if len(game_id) > 18 else game_id,
            "map_name": str(map_name).replace("_", " ").title(),
            "player_id": player_id,
            "round": current_round,
            "time_total": int(current_time),
            "prestige": prestige,
            "level": level,
            "current_xp": snapshot.get("current_xp", 0),
            "tick_xp": snapshot.get("tick_xp", 0),
            "round_xp": round_xp,
            "total_match_xp": total_match_xp,
            "rank_changed": rank_changed,
            "xp_math_label": xp_math_label,
            "rank_change_label": rank_change_label
        }

        replaced = False
        for idx, existing in enumerate(xp_debug_rows):
            if existing.get("key") == key:
                xp_debug_rows[idx] = row
                replaced = True
                break
        if not replaced:
            xp_debug_rows.append(row)

        del xp_debug_rows[:-250]

    _publish_xp_debug_rows()

def toggle_xp_debugger_logic(enable):
    global xp_debug_window
    if enable:
        if xp_debug_window:
            _publish_xp_debug_rows()
            return
        try:
            xp_debug_window = webview.create_window(
                'BO3 XP Debugger',
                html=get_xp_debugger_html(),
                width=1100,
                height=520,
                resizable=True
            )
            threading.Timer(0.5, _publish_xp_debug_rows).start()
        except Exception as e:
            print(f"XP Debugger Error: {e}")
    else:
        try:
            if xp_debug_window:
                xp_debug_window.destroy()
        except Exception:
            pass
        xp_debug_window = None

# --- SETUP SCREEN HTML (INSERTED) ---
def get_setup_html():
    css_content = load_css(CSS_SETUP_FILE)
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BO3 Tracker Setup</title>
        <style>""" + css_content + """</style>
    </head>
    <body>
        <div class="box">
            <h2>System Initialization</h2>
            <div class="label">LIVE DATA FILE (CurrentGame.json)</div>
            <div class="hint-text">Select the file typically located in: steamapps\\common\\Call of Duty Black Ops III\\players\\...</div>
            <div style="display:flex; justify-content:space-between; gap:10px;">
                <input type="text" id="livePath" readonly placeholder="Select File...">
                <button class="browse" onclick="browseLive()">BROWSE</button>
            </div>
           
            <div class="label">HISTORY ARCHIVE FOLDER</div>
            <div class="hint-text">Select a folder where match history will be saved.</div>
            <div style="display:flex; justify-content:space-between; gap:10px;">
                <input type="text" id="histPath" readonly placeholder="Select Folder...">
                <button class="browse" onclick="browseHist()">BROWSE</button>
            </div>
           
            <button class="save" onclick="save()">INITIALIZE SYSTEM</button>
        </div>
        <script>
            function browseLive() {
                window.pywebview.api.browse_live_file().then(path => {
                    if(path) document.getElementById('livePath').value = path;
                });
            }
            function browseHist() {
                window.pywebview.api.browse_history_folder().then(path => {
                    if(path) document.getElementById('histPath').value = path;
                });
            }
            function save() {
                const live = document.getElementById('livePath').value;
                const hist = document.getElementById('histPath').value;
                if (!live || !hist) { alert("Please select both the file and the folder."); return; }
                window.pywebview.api.save_config(live, hist);
            }
        </script>
    </body>
    </html>
    """

# --- UNIFIED DASHBOARD HTML ---
def get_main_app_html():
    css_content = load_css(CSS_MAIN_FILE)
    
    overlays_on = app_config.get('overlays_enabled', False)
    chk_str = "checked" if overlays_on else ""
    xp_debug_on = app_config.get('xp_debugger_enabled', False)
    xp_debug_chk_str = "checked" if xp_debug_on else ""
    workshop_images_on = app_config.get('workshop_images_enabled', True)
    workshop_images_chk_str = "checked" if workshop_images_on else ""
    workshop_images_js = "true" if workshop_images_on else "false"

    return """
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style id="theme-injector"></style>

        <!-- FIREWALL 1: External CSS is now isolated -->
        <style>""" + css_content + """</style>

        <!-- FIREWALL 2: Core UI styles are now protected from external typos -->
        <style>
        .switch { position: relative; display: inline-block; width: 50px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .4s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 4px; bottom: 4px; background-color: white; transition: .4s; border-radius: 50%; }
        input:checked + .slider { background-color: #66fcf1; }
        input:checked + .slider:before { transform: translateX(26px); }
        .perk-item { background: transparent !important; border: none !important; box-shadow: none !important; }

        /* --- CHALLENGE SYSTEM UI --- */
        .chal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top:20px; }
        .chal-card { background: rgba(255,255,255,0.05); border: 1px solid #333; padding: 15px; border-radius: 6px; }
        .chal-card.done { border-color: #66fcf1; background: rgba(102, 252, 241, 0.05); }
        .chal-btn { width:100%; padding:8px; margin-top:10px; background:#333; color:#777; border:none; cursor:not-allowed; font-weight:bold; }
        .chal-btn.active { background:var(--highlight); color:#000; cursor:pointer; }
        .theme-header { grid-column: 1 / -1; margin-top: 20px; color: var(--gold); border-bottom: 1px solid #333; padding-bottom: 5px; font-size: 1.2em; text-transform: uppercase; }
        
        /* PLAYER CARD SELECTOR */
        .card-selector-img { width: 100%; height: 60px; object-fit: cover; margin-top: 5px; border: 1px solid #444; border-radius: 4px; }
        .card-display-header { width: 300px; height: 100px; object-fit: cover; border: 1px solid #444; border-radius: 4px; margin-left: 20px; }

        /* THEME: VOID */
        body.theme-void {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e) !important;
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
        }
        @keyframes gradientBG { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        </style>
        <style id="dynamic-camo-styles"></style>
    </head>
    <body>
        <div class="sidebar">
            <div class="header" id="live-btn" onclick="switchTab('live')">LIVE GAME</div>
            <div class="nav-btn" id="camo-btn" onclick="switchTab('camo')">CAMO MATRIX</div>
            <div class="nav-btn" id="career-btn" onclick="switchTab('career')">CAREER PROFILE</div>
            <div class="nav-btn" id="bestmatches-btn" onclick="switchTab('bestmatches')">BEST MATCHES</div>
            <div class="nav-btn" id="chal-btn" onclick="switchTab('challenges')">CHALLENGES</div>
            <div style="padding:20px; color:#555; font-size:0.7em; font-weight:bold; letter-spacing:1px; margin-top:10px;">MATCH LOGS</div>
            <div class="list" id="history-list"></div>
            
            <div id="history-pagination" style="display:flex; justify-content:space-between; padding: 10px 20px;">
                <button class="nav-btn-small" style="background:#222; color:#aaa; flex:1; margin-right:5px;" onclick="changeHistoryPage(-1)">PREV</button>
                <span id="hist-page-info" style="color:#aaa; font-size: 0.8em; align-self: center; text-align:center; min-width:40px;">1 / 1</span>
                <button class="nav-btn-small" style="background:#222; color:#aaa; flex:1; margin-left:5px;" onclick="changeHistoryPage(1)">NEXT</button>
            </div>
            <div class="config-btn" onclick="switchTab('help')">HELP & FAQ</div>
            <div class="config-btn" onclick="switchTab('settings')">SETTINGS</div>
        </div>
        
        <div class="main-view">
            <div id="tab-live" class="tab-content active">
                <div id="d_status_bar" class="status-bar">CONNECTING...</div>
                <div id="d_nerf"></div>

                <div class="card" style="position: relative;">
                    <div id="live-workshop-container" style="display:none; position:absolute; top:0; left:0; width:100%; height:100%; border-radius:12px; overflow:hidden; z-index:1;">
                        <img id="live-workshop-img" src="" style="width:100%; height:100%; object-fit:contain; opacity:0.3; display:none;">
                    </div>
                    <div style="position: relative; z-index:2;">
                        <div class="card-title" style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                            <span>CURRENT MISSION</span>
                            <button id="best-match-btn" class="nav-btn-small" onclick="addBestMatch()" style="height:28px; padding:0 12px; font-size:0.75em;">ADD BEST MATCH</button>
                        </div>
                        <div style="position: relative; display:flex; align-items:center; justify-content:space-between;">
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div>
                                    <div id="d_map" class="stat-big" style="font-size: 2em;">-</div>
                                    <div class="stat-sub">ROUND <span id="d_round" style="color:#fff; font-weight:bold;">0</span></div>
                                </div>
                            </div>
                         </div>
                         <div style="text-align:right; margin-top:10px;">
                              <div class="detail-row"><span>TIME</span><span id="d_time">00:00</span></div>
                              <div class="detail-row"><span>AVG ROUND</span><span id="d_avg_time">0s</span></div> 
                              <div class="detail-row"><span>ZPM</span><span id="d_zpm">0</span></div>
                              <div class="detail-row"><span>MODE</span><span id="d_mode">-</span></div>
                              <div class="detail-row"><span>VERSION</span><span id="d_version" style="color:#888; font-size: 0.8em;">-</span></div>
                         </div>
                    </div>
                 </div>

                <div id="player-tabs-container" class="player-tabs-container"></div>

                <div id="player-specific-content" style="display: none;">
                    <div class="stat-grid-2">
<div class="card">
                            <div class="card-title">SERVICE RECORD</div>
                            <div style="display: flex; align-items: center; gap: 15px;">
                                <div style="display: flex; gap: 10px; margin-right: 15px;">
                                    <div id="d_prest_box" style="text-align: center; display:none;">
                                        <img id="d_prest_icon" src="" style="width: 50px; height: 50px; object-fit: contain; filter: drop-shadow(0px 0px 4px rgba(0,0,0,0.8));">
                                        <div style="font-size: 0.6em; color: #888; margin-top: -5px;">PRESTIGE</div>
                                    </div>
                                    <div id="d_lvl_box" style="text-align: center; display:none;">
                                        <img id="d_lvl_icon" src="" style="width: 50px; height: 50px; object-fit: contain; filter: drop-shadow(0px 0px 4px rgba(0,0,0,0.8));">
                                        <div style="font-size: 0.6em; color: #888; margin-top: -5px;">LEVEL</div>
                                    </div>
                                </div>
                                <div>
                                    <div id="d_rmain" class="stat-rank">-</div>
                                    <div id="d_title" style="color:#aaa; font-style:italic; font-size:0.9em; margin-bottom:5px;">-</div>
                                    <div id="d_rsub" style="color:#888; font-size:0.8em;">-</div>
                                </div>
                            </div>
                            <div style="margin-top:15px;">
                                
                                <div class="detail-row" style="flex-wrap: wrap; border-bottom: none;">
                                    <div style="display:flex; justify-content:space-between; width:100%; align-items: center;">
                                        <span>XP EARNED 
                                        <button onclick="toggleXpmGraph()" style="margin-left:10px; background:#222; color:#66fcf1; border:1px solid #66fcf1; border-radius:4px; cursor:pointer; font-size:0.7em; padding:2px 5px; transition: 0.2s;">📊 XPM</button>
                                        <button onclick="toggleRoundXpGraph()" style="margin-left:5px; background:#222; color:#ff9d00; border:1px solid #ff9d00; border-radius:4px; cursor:pointer; font-size:0.7em; padding:2px 5px; transition: 0.2s;">📈 ROUND XP</button>
                                        </span>
                                        <button onclick="toggleZpmGraph()" style="margin-left:5px; background:#222; color:#7cff6b; border:1px solid #7cff6b; border-radius:4px; cursor:pointer; font-size:0.7em; padding:2px 5px; transition: 0.2s;">ZPM</button>
                                        <span id="d_xp">0</span>
                                    </div>

                                    <div id="xpm-graph-container" class="xpm-container-base" style="display:none; width: 100%;">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('xpm-graph-container', 'chart-scroll-wrapper', 'xpm')">Pop-Out XPM</button>
                                        <button class="graph-popout-btn" onclick="toggleZpmOverlay()">Overlay ZPM</button>
                                        <div id="chart-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="xpmChart"></canvas> 
                                        </div>
                                    </div>

                                    <div id="roundxp-graph-container" class="xpm-container-base" style="display:none; margin-top:10px; width: 100%;">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('roundxp-graph-container', 'roundxp-scroll-wrapper', 'roundxp')">Pop-Out Round XP</button>
                                        <div id="roundxp-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="roundXpChart"></canvas> 
                                        </div>
                                    </div>
                                </div>
                                    <div id="zpm-graph-container" class="xpm-container-base" style="display:none; margin-top:10px; width: 100%;">
                                        <button class="graph-popout-btn" onclick="toggleGraphPopout('zpm-graph-container', 'zpm-scroll-wrapper', 'zpm')">Pop-Out ZPM</button>
                                        <div id="zpm-scroll-wrapper" class="xpm-scroll-wrapper"> 
                                            <canvas id="zpmChart"></canvas> 
                                        </div>
                                    </div>
                                <div class="detail-row"><span>MULTIPLIER</span><span id="d_mult" style="color:var(--highlight)">x1.0</span></div>
                                <div class="detail-row"><span>GOBBLEGUMS</span><span id="d_gums" style="color:#d400ff">0</span></div>
                            </div>
                        </div>

                        <div class="card">
                            <div class="card-title">COMBAT EFFICIENCY</div>
                            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-bottom:15px;">
                                <div><div style="color:#888; font-size:0.7em;">ELIMINATIONS</div><div id="d_kills" class="stat-big">0</div></div>
                                <div><div style="color:#888; font-size:0.7em;">SCORE</div><div id="d_score" class="stat-big" style="color:#fff">0</div></div>
                            </div>
                            <div class="detail-row"><span>ACCURACY</span><span><span id="d_acc">0</span>%</span></div>
                            <div class="detail-row"><span>MELEE / EQUIP</span><span><span id="d_melee">0</span> / <span id="d_equip">0</span></span></div>
                            <div class="detail-row"><span>DOWNS</span><span id="d_downs" style="color:var(--danger)">0</span></div>
                        </div>
                    </div>

                    <div class="card full-width">
                        <div class="card-title">ACTIVE PERKS</div>
                        <div id="d_perks" class="perk-container"></div>
                    </div>

                    <div class="card full-width">
                        <div class="card-title">ARMORY & LOADOUT</div>
                        <div style="display:flex; gap:30px; margin-bottom:20px; font-size:0.9em; padding:10px; background:rgba(0,0,0,0.2); border-radius:6px;">
                            <span>LETHAL: <b id="d_leth" style="color:#fff">-</b></span>
                            <span>TACTICAL: <b id="d_tact" style="color:#fff">-</b></span>
                        </div>
                        <table>
                            <thead><tr><th>WEAPON</th><th>KILLS</th><th>HS</th><th>DAMAGE</th><th>STATUS</th></tr></thead>
                            <tbody id="d_weaps"></tbody>
                        </table>
                    </div>
                </div>
            </div>
           
           <div id="tab-camo" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1>Armory Matrix</h1>
                        <div style="font-size:0.8em; color:#777; margin-top:5px;">STATUS: <span id="status-txt">DISCONNECTED</span></div>
                    </div>
                    <div style="text-align:right;">
                        <div id="user-display" class="user-badge">GUEST</div>
                        <button class="nav-btn-small" style="margin-top:10px; background:var(--highlight); color:#000;" onclick="askParentToBrowse()">LOAD FILE</button>
                    </div>
                </div>
               
                <div class="controls" id="controls-area" style="display:none;">
                    <button class="nav-btn-small" onclick="changeMap(-1)">PREV</button>
                    <select id="map-select" onchange="onMapSelect()"></select>
                    <button class="nav-btn-small" onclick="changeMap(1)">NEXT</button>
                    <input type="text" id="search-input" placeholder="Find weapon..." onkeyup="onSearch()">
                </div>
               
                <div id="content-area">
                    <div style="text-align:center; margin-top:80px; color:#555;">
                        <h3>INITIALIZATION REQUIRED</h3>
                        <p>Load your profile JSON to view and edit camo progress.</p>
                    </div>
                </div>
            </div>

            <div id="tab-career" class="tab-content">
                <div class="header-camo">
                    <div style="display:flex; align-items:center;">
                        <h1>Career Dossier</h1>
                        <img id="card-display" class="card-display-header" src="" style="display:none;">
                        <video id="card-display-video" class="card-display-header" autoplay loop muted playsinline style="display:none;"></video>
                    </div>
                    <div style="font-size:0.8em; color:#777;">LIFETIME STATISTICS (PLAYER 1)</div>
                </div>

                <div class="card" id="career-rank-card" style="margin-bottom: 16px;">
                    <div class="card-title">CURRENT RANK</div>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="display: flex; gap: 10px; margin-right: 15px;">
                            <div id="career-prest-box" style="text-align: center; display:none;">
                                <img id="career-prest-icon" src="" style="width: 50px; height: 50px;">
                                <div style="font-size: 0.6em; color: #888; margin-top: -5px;">PRESTIGE</div>
                            </div>
                            <div id="career-lvl-box" style="text-align: center; display:none;">
                                <img id="career-lvl-icon" src="" style="width: 50px; height: 50px;">
                                <div style="font-size: 0.6em; color: #888; margin-top: -5px;">LEVEL</div>
                            </div>
                        </div>
                        <div>
                            <div id="career-rmain" style="color:var(--highlight); font-size:1.3em; font-weight:bold;">-</div>
                            <div id="career-rsub" style="color:#aaa; font-size:0.85em;">-</div>
                            <div id="career-title" style="color:#777; font-size:0.8em; font-style:italic;"></div>
                            <div id="career-map-name" style="color:#555; font-size:0.7em; margin-top: 4px;"></div>
                        </div>
                    </div>
                    <div class="progress-bar" style="margin-top: 12px; height: 10px; border-radius: 5px;">
                        <div id="career-xp-bar" class="fill" style="width:0%; height: 100%;"></div>
                    </div>
                    <div style="font-size: 0.75em; color: #888; margin-top: 4px;">
                        <span id="career-xp-text">0 / 0 XP</span>
                        <span id="career-xp-pct" style="float:right;">0%</span>
                    </div>
                </div>

                <div class="stat-grid-2">
                    <div class="card">
                        <div class="card-title">COMBAT RECORD</div>
                        <div class="detail-row"><span>TOTAL KILLS</span><span id="life_kills" style="color:var(--highlight); font-size:1.2em;">0</span></div>
                        <div class="detail-row"><span>HEADSHOTS</span><span id="life_headshots">0</span></div>
                        <div class="detail-row"><span>PRECISION</span><span id="life_hs_pct" style="color:#ff9d00">0%</span></div>
                        <div style="margin-top:10px; border-top:1px solid #333; padding-top:5px;">
                            <div class="detail-row"><span>FAVORITE WEAPONS</span><span id="life_fav_gun" style="text-align:right">None</span></div>
                        </div>
                    </div>

                    <div class="card">
                        <div class="card-title">SURVIVALIST</div>
                        <div class="detail-row"><span>ROUNDS SURVIVED</span><span id="life_rounds">0</span></div>
                        <div class="detail-row"><span>TIME PLAYED</span><span id="life_time">0h 0m</span></div>
                        <div class="detail-row"><span>MATCHES LOGGED</span><span id="life_matches">0</span></div>
                        <div class="detail-row"><span>KILLS PER DOWN</span><span id="life_kpd">0.0</span></div>
                    </div>
                </div>
                
                <div class="stat-grid-2">
    <div class="card">
        <div class="card-title">LOGISTICS</div>
        <div class="detail-row"><span>DOORS OPENED</span><span id="life_doors">0</span></div>
        <div class="detail-row"><span>GOBBLEGUMS</span><span id="life_gums" style="color:#d400ff">0</span></div>
        <div class="detail-row"><span>MYSTERY BOX</span><span id="life_box">0</span></div>
        <div class="detail-row"><span>PLAYER POINTS GAINED</span><span id="life_pts" style="color:#ffd700">0</span></div>
    </div>
    <div class="card">
        <div class="card-title">PERSONAL BESTS (ROUNDS)</div>
        <div id="life_map_list" style="max-height:150px; overflow-y:auto; font-size:0.8em; color:#aaa;">
        </div>
    </div>
</div>

               <div class="stat-grid-2" style="margin-top: 15px;">
    <div class="card">
        <div class="card-title" style="display: flex; justify-content: space-between; align-items: center;">
            <span>MOST PLAYED MAPS</span>
            <select id="map-sort-toggle" onchange="renderMostPlayedMaps()" style="background: #222; color: #aaa; border: 1px solid #444; font-size: 0.7em; padding: 2px; outline: none; cursor: pointer;">
                <option value="matches">By Matches</option>
                <option value="time">By Time</option>
            </select>
        </div>
        <div id="life_most_played" style="max-height: 200px; overflow-y: auto; overflow-x: hidden; font-size: 0.85em; color: #aaa; display: block;">
            <div style='color:#777; font-style:italic; padding: 5px;'>Loading map records...</div>
        </div>
    </div>
                    
                    <div class="card">
                        <div class="card-title">TOP MAPS BY HIGHEST MATCH XP</div>
                        <div id="top_xp_maps_list" style="max-height: 200px; overflow-y: auto; overflow-x: hidden; font-size: 0.85em; color: #aaa; display: block;">
                            <div style='color:#777; font-style:italic; padding: 5px;'>Loading XP records...</div>
                        </div>
                    </div>
                </div>

            </div>

            <div id="tab-bestmatches" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1>Best Matches</h1>
                        <div style="font-size:0.8em; color:#777; margin-top:5px;">PINNED MATCH RECORDS</div>
                    </div>
                    <button class="nav-btn-small" onclick="loadBestMatches()" style="height:36px;">REFRESH</button>
                </div>
                <div class="card">
                    <div class="card-title">SAVED MATCH LINKS</div>
                    <div id="best-matches-list" style="display:flex; flex-direction:column; gap:10px;">
                        <div style="color:#777; font-style:italic; padding:8px 0;">Loading best matches...</div>
                    </div>
                </div>
            </div>

            <div id="tab-challenges" class="tab-content">
                <div class="header-camo">
                    <div>
                        <h1>Active Operations</h1>
                        <div style="font-size:0.8em; color:#777;">COMPLETE CHALLENGES TO UNLOCK REWARDS</div>
                    </div>
                    <div>
                        <button class="nav-btn-small" onclick="filterChallenges('operations')">OPERATIONS</button>
                        <button class="nav-btn-small" onclick="filterChallenges('themes')">THEME INTEL</button>
                        <button class="nav-btn-small" onclick="filterChallenges('lifetime')">LIFETIME</button>
                        <button class="nav-btn-small" style="background:var(--danger); margin-left:10px;" onclick="resetOps()">RESET</button>
                    </div>
                </div>
                <div id="challenge-list" class="chal-grid"></div>
            </div>

            <div id="tab-settings" class="tab-content">
                <div class="header-camo">
                    <h1>System Configuration</h1>
                </div>

                <div class="card">
                    <div class="card-title">VISUAL CUSTOMIZATION</div>
                    <div style="margin-bottom: 10px; color: #aaa; font-size: 0.9em;">Select a visual theme for the tracker:</div>
                    <div style="display:flex; gap:10px;">
                        <select id="theme-selector" style="flex:1; background:#111; color:#fff; padding:10px;">
                            <option value="default">Default Tactical</option>
                        </select>
                        <button class="nav-btn-small" onclick="applySelectedTheme()">APPLY</button>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">PLAYER CARD IDENTITY</div>
                    <div style="margin-bottom: 10px; color: #aaa; font-size: 0.9em;">Select your active Calling Card:</div>
                    <div style="display:flex; gap:10px; align-items:center;">
                        <div style="flex:1">
                            <select id="card-selector" style="width:100%; background:#111; color:#fff; padding:10px;" onchange="previewCard(this.value)">
                                <option value="default">None Equipped</option>
                            </select>
                            <img id="card-preview" src="" class="card-selector-img" style="display:none;">
                            <video id="card-preview-video" class="card-selector-img" autoplay loop muted playsinline style="display:none;"></video>
                        </div>
                        <button class="nav-btn-small" style="height:40px;" onclick="applySelectedCard()">EQUIP</button>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title">UEM STATS BACKUP</div>
                    <div style="margin-bottom: 10px; color: #aaa; font-size: 0.9em;">Create a zip archive containing your local UEM player stats (stats_zm_0.cgp to stats_zm_4.cgp).</div>
                    <button class="nav-btn-small" style="background: var(--highlight); color:#000; width:100%; height:40px;" onclick="backupStats()">CREATE BACKUP</button>
                </div>

                <div class="card">
                    <div class="card-title">DATA MANAGEMENT</div>
                    <button class="nav-btn-small" style="background: var(--danger); width:100%;" onclick="reconfigure()">RESET FILE PATHS</button>
                    <p style="color:#777; font-size:0.8em; margin-top:10px;">Use this if you moved your game installation or history folder.</p>
                </div>

                <div class="card">
                    <div class="card-title">DASHBOARD MEDIA</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:15px;">
                        <div>
                            <div style="color:#fff; font-weight:bold;">Show Steam Workshop Images</div>
                            <div style="color:#aaa; font-size:0.8em;">Displays map preview images on the live dashboard and career rank card when a Steam Workshop link is available.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleWorkshopImages(this)" """ + workshop_images_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">OVERLAY CONTROL</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:15px;">
                        <div>
                            <div style="color:#fff; font-weight:bold;">Enable Live Overlay</div>
                            <div style="color:#aaa; font-size:0.8em;">Displays Perks and Top Damage in a single, smart-resizing window.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleOverlays(this)" """ + chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">XP DEBUGGER</div>
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:15px;">
                        <div>
                            <div style="color:#fff; font-weight:bold;">Enable XP Round Debug Window</div>
                            <div style="color:#aaa; font-size:0.8em;">Shows live game ID, map, player, round, level XP, tick XP, round XP, and rank changes.</div>
                        </div>
                        <label class="switch">
                            <input type="checkbox" onchange="toggleXpDebugger(this)" """ + xp_debug_chk_str + """>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>

            <div id="tab-help" class="tab-content">
                <div style="max-width:800px; margin:0 auto;">
                    <h1 style="color:var(--highlight); border-bottom:1px solid #333; padding-bottom:15px;">OPERATIONAL GUIDE</h1>
                   
                    <div class="card">
                        <div class="card-title">GETTING STARTED</div>
                        <p style="color:#ccc; font-size:0.9em; line-height:1.6;">
                            1. <b>Live Feed:</b> Ensure the tracker is pointing to your <code>CurrentGame.json</code>. This file updates automatically while you play.<br><br>
                            2. <b>Camo Matrix:</b> To track custom camos, you must download your profile data from http://uemmaps.com/ and load it here using the "LOAD FILE" button.
                        </p>
                    </div>

                    <div class="card">
                        <div class="card-title">TROUBLESHOOTING</div>
                        <div style="display:flex; flex-direction:column; gap:15px;">
                            <details style="background:rgba(0,0,0,0.2); padding:10px; border-radius:4px; cursor:pointer;">
                                <summary style="color:#fff; font-weight:bold;">Stats aren't updating live</summary>
                                <p style="color:#aaa; font-size:0.9em; margin-top:10px;">
                                    Ensure the path to <code>CurrentGame.json</code> is correct in System Config. Some mods only write this file at the end of a round or when the game pauses.
                                </p>
                            </details>
                            <details style="background:rgba(0,0,0,0.2); padding:10px; border-radius:4px; cursor:pointer;">
                                <summary style="color:#fff; font-weight:bold;">Camo progress isn't saving</summary>
                                <p style="color:#aaa; font-size:0.9em; margin-top:10px;">
                                    The tracker updates your local JSON file immediately. However, to see these changes on site you will need to upload using the https://uemmaps.com upload tab once logged in.
                                </p>
                            </details>
                            <details style="background:rgba(0,0,0,0.2); padding:10px; border-radius:4px; cursor:pointer;">
                                <summary style="color:#fff; font-weight:bold;">Icons are missing</summary>
                                <p style="color:#aaa; font-size:0.9em; margin-top:10px;">
                                    Ensure the <code>perk icons</code> and <code>camoimages</code> folders are in the same directory as the application executable.
                                </p>
                            </details>
                        </div>
                    </div>
                   
                     <div class="card">
                        <div class="card-title">KEY FEATURES</div>
                         <ul style="color:#aaa; font-size:0.9em; line-height:1.6;">
                            <li><b>Priority Tracking:</b> Click the Star (★) on any weapon in the Camo Matrix to pin it to the top of the list. Max 3 weapons.</li>
                            <li><b>Match History:</b> The tracker automatically archives your games. Click any match in the sidebar to review past performance.</li>
                            <li><b>Higher Visble Gun Damage:</b> The tracker automatically trys to work out how much damage you are doing once the game cap is reached using the data of damage each round.</li>
                            <li><b>Camo Tracker:</b> Built in camo tracker for some custom maps.</li>
                         </ul>
                    </div>
                </div>
            </div>

        </div>
        
        <input type="hidden" id="current-user-path" value="">

        <script>
        // --- NEW GRAPHING VARIABLES ---
        let xpmChartInstance = null;
        let roundXpChartInstance = null; // New chart instance variable
        let zpmChartInstance = null;
        let currentGraphLabels = [];
        let currentGraphData = [];
        let currentRoundXpLabels = []; // Stores the new Round XP labels
        let currentRoundXpData = [];   // Stores the new Round XP values
        let currentZpmLabels = [];
        let currentZpmData = [];
        let zpmOverlayEnabled = false;
        let currentThemeName = 'default';
        let workshopImagesEnabled = """ + workshop_images_js + """;

        const GRAPH_THEMES = {
            default: {
                line: '#66fcf1', lineFill: 'rgba(102, 252, 241, 0.12)',
                point: '#ff9d00', pointBorder: '#fff',
                bar: '#ff9d00', barBorder: '#e68a00',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#66fcf1'
            },
            void: {
                line: '#b19cd9', lineFill: 'rgba(148, 0, 211, 0.14)',
                point: '#e0b0ff', pointBorder: '#4b0082',
                bar: '#9400d3', barBorder: '#e0b0ff',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#e0b0ff'
            },
            '115_Origins': {
                line: '#00a8ff', lineFill: 'rgba(0, 168, 255, 0.14)',
                point: '#58a6ff', pointBorder: '#d7f3ff',
                bar: '#00a8ff', barBorder: '#58a6ff',
                zpm: '#7cff6b', zpmFill: 'rgba(124, 255, 107, 0.08)',
                tooltip: '#58a6ff'
            },
            RedHex: {
                line: '#ff3333', lineFill: 'rgba(255, 0, 0, 0.13)',
                point: '#ffcccc', pointBorder: '#ff0000',
                bar: '#ff0000', barBorder: '#800000',
                zpm: '#ffcc00', zpmFill: 'rgba(255, 204, 0, 0.08)',
                tooltip: '#ff3333'
            },
            'Golden Divinium': {
                line: '#ffd700', lineFill: 'rgba(255, 215, 0, 0.16)',
                point: '#fffac0', pointBorder: '#b8860b',
                bar: '#ffd700', barBorder: '#b8860b',
                zpm: '#fffac0', zpmFill: 'rgba(255, 250, 192, 0.08)',
                tooltip: '#ffd700'
            },
            retro: {
                line: '#00f2ff', lineFill: 'rgba(0, 242, 255, 0.13)',
                point: '#ff00ff', pointBorder: '#00f2ff',
                bar: '#ff00ff', barBorder: '#00f2ff',
                zpm: '#00ff66', zpmFill: 'rgba(0, 255, 102, 0.08)',
                tooltip: '#ff00ff'
            },
            matrix: {
                line: '#00ff00', lineFill: 'rgba(0, 255, 0, 0.12)',
                point: '#000000', pointBorder: '#00ff00',
                bar: '#00ff00', barBorder: '#008800',
                zpm: '#88ff88', zpmFill: 'rgba(136, 255, 136, 0.08)',
                tooltip: '#00ff00'
            },
            trench: {
                line: '#c9bca7', lineFill: 'rgba(201, 188, 167, 0.12)',
                point: '#8b0000', pointBorder: '#c9bca7',
                bar: '#8b0000', barBorder: '#c9bca7',
                zpm: '#d4b56a', zpmFill: 'rgba(212, 181, 106, 0.08)',
                tooltip: '#c9bca7'
            },
            neon_pulse: {
                line: '#00f5ff', lineFill: 'rgba(0, 245, 255, 0.13)',
                point: '#ff00ff', pointBorder: '#00f5ff',
                bar: '#00f5ff', barBorder: '#ff00ff',
                zpm: '#ff00ff', zpmFill: 'rgba(255, 0, 255, 0.08)',
                tooltip: '#00f5ff'
            }
        };

        function getGraphTheme() {
            return GRAPH_THEMES[currentThemeName] || GRAPH_THEMES.default;
        }

        function applyGraphTheme() {
            const theme = getGraphTheme();

            if (xpmChartInstance) {
                const ds = xpmChartInstance.data.datasets[0];
                ds.borderColor = theme.line;
                ds.backgroundColor = theme.lineFill;
                ds.pointBackgroundColor = theme.point;
                ds.pointBorderColor = theme.pointBorder;
                const zpmDs = xpmChartInstance.data.datasets.find(d => d.id === 'zpm-overlay');
                if (zpmDs) {
                    zpmDs.borderColor = theme.zpm;
                    zpmDs.backgroundColor = theme.zpmFill;
                    zpmDs.pointBackgroundColor = theme.zpm;
                    zpmDs.pointBorderColor = theme.pointBorder;
                }
                xpmChartInstance.options.plugins.tooltip.titleColor = theme.tooltip;
                xpmChartInstance.options.plugins.tooltip.borderColor = theme.tooltip;
                xpmChartInstance.update('none');
            }

            if (roundXpChartInstance) {
                const ds = roundXpChartInstance.data.datasets[0];
                ds.backgroundColor = theme.bar;
                ds.borderColor = theme.barBorder;
                roundXpChartInstance.options.plugins.tooltip.titleColor = theme.tooltip;
                roundXpChartInstance.update('none');
            }

            if (zpmChartInstance) {
                const ds = zpmChartInstance.data.datasets[0];
                ds.borderColor = theme.zpm;
                ds.backgroundColor = theme.zpmFill;
                ds.pointBackgroundColor = theme.zpm;
                ds.pointBorderColor = theme.pointBorder;
                zpmChartInstance.options.plugins.tooltip.titleColor = theme.zpm;
                zpmChartInstance.options.plugins.tooltip.borderColor = theme.zpm;
                zpmChartInstance.update('none');
            }
        }

        function getZpmDataset() {
            const theme = getGraphTheme();
            return {
                id: 'zpm-overlay',
                label: 'Zombies Per Minute',
                data: currentZpmData,
                borderColor: theme.zpm,
                backgroundColor: theme.zpmFill,
                borderWidth: 2,
                fill: false,
                tension: 0.2,
                pointBackgroundColor: theme.zpm,
                pointBorderColor: theme.pointBorder,
                pointRadius: 4,
                pointHoverRadius: 7,
                yAxisID: 'zpmAxis'
            };
        }

        function syncXpmOverlayDataset() {
            if (!xpmChartInstance) return;
            const existingIndex = xpmChartInstance.data.datasets.findIndex(d => d.id === 'zpm-overlay');
            if (zpmOverlayEnabled) {
                const zpmDataset = getZpmDataset();
                if (existingIndex >= 0) {
                    xpmChartInstance.data.datasets[existingIndex] = zpmDataset;
                } else {
                    xpmChartInstance.data.datasets.push(zpmDataset);
                }
                xpmChartInstance.options.scales.zpmAxis.display = true;
            } else {
                if (existingIndex >= 0) xpmChartInstance.data.datasets.splice(existingIndex, 1);
                xpmChartInstance.options.scales.zpmAxis.display = false;
            }
        }

        function sizeGraphCanvas(canvas, wrapper, labelCount) {
            const availableWidth = Math.max(wrapper.clientWidth || wrapper.parentElement.clientWidth || 0, 1);
            const targetWidth = Math.max(availableWidth, labelCount * 22);
            canvas.style.width = targetWidth + 'px';
            canvas.style.minWidth = '100%';
            wrapper.style.width = '100%';
            wrapper.style.overflowX = targetWidth > availableWidth ? 'auto' : 'hidden';
            wrapper.style.overflowY = 'hidden';
        }

        function toggleXpmGraph() {
            const container = document.getElementById('xpm-graph-container');
            const otherContainer = document.getElementById('roundxp-graph-container');
            const zpmContainer = document.getElementById('zpm-graph-container');
            if (container.style.display === 'none' || container.style.display === '') {
                otherContainer.style.display = 'none'; // Close the other one
                if (zpmContainer) zpmContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderXpmChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        function toggleZpmOverlay() {
            zpmOverlayEnabled = !zpmOverlayEnabled;
            renderXpmChart();
        }

        // --- NEW: TOGGLE ROUND XP GRAPH ---
        function toggleRoundXpGraph() {
            const container = document.getElementById('roundxp-graph-container');
            const otherContainer = document.getElementById('xpm-graph-container');
            const zpmContainer = document.getElementById('zpm-graph-container');
            
            if (container.style.display === 'none' || container.style.display === '') {
                otherContainer.style.display = 'none'; // Close the other one
                if (zpmContainer) zpmContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderRoundXpChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        function toggleZpmGraph() {
            const container = document.getElementById('zpm-graph-container');
            const xpmContainer = document.getElementById('xpm-graph-container');
            const roundContainer = document.getElementById('roundxp-graph-container');
            if (!container) return;

            if (container.style.display === 'none' || container.style.display === '') {
                if (xpmContainer) xpmContainer.style.display = 'none';
                if (roundContainer) roundContainer.style.display = 'none';
                container.style.display = 'block';
                setTimeout(() => { renderZpmChart(); }, 50);
            } else {
                container.style.display = 'none';
            }
        }

        // --- NEW: SMARTER POPOUT LOGIC ---
        let graphPopoutStates = {}; // Remembers locations for MULTIPLE graphs

        function toggleGraphPopout(containerId, wrapperId, chartType) {
            const container = document.getElementById(containerId);
            const wrapper = document.getElementById(wrapperId);
            
            container.classList.toggle('graph-popout-mode');
            
            if (container.classList.contains('graph-popout-mode')) {
                // Save exactly where this specific graph was
                graphPopoutStates[containerId] = {
                    parent: container.parentNode,
                    sibling: container.nextSibling
                };
                // Move it to the very top layer of the body
                document.body.appendChild(container);
                wrapper.style.height = '85vh'; 
            } else {
                // Put it back exactly where it belongs
                const state = graphPopoutStates[containerId];
                if (state && state.parent) {
                    state.parent.insertBefore(container, state.sibling);
                }
                wrapper.style.height = '300px';
            }
            
            // Just resize the chart to fit its new home, no need to redraw!
            setTimeout(() => {
                if (chartType === 'xpm' && xpmChartInstance) xpmChartInstance.resize();
                if (chartType === 'roundxp' && roundXpChartInstance) roundXpChartInstance.resize();
                if (chartType === 'zpm' && zpmChartInstance) zpmChartInstance.resize();
            }, 50);
        }

        // --- UPDATED XPM CHART (No Flickering!) ---
        function renderXpmChart() {
            const canvas = document.getElementById('xpmChart');
            const wrapper = document.getElementById('chart-scroll-wrapper');
            if (!canvas || !wrapper) return;
            
            sizeGraphCanvas(canvas, wrapper, currentGraphLabels.length);
            
            // If the chart already exists, just update the data silently!
            if (xpmChartInstance) {
                xpmChartInstance.data.labels = currentGraphLabels;
                xpmChartInstance.data.datasets[0].data = currentGraphData;
                syncXpmOverlayDataset();
                xpmChartInstance.resize();
                xpmChartInstance.update('none'); // 'none' prevents the animation from restarting
                return;
            }
            
            // Otherwise, create it for the first time
            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            xpmChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: currentGraphLabels,
                    datasets: [{
                        label: 'XP Per Minute',
                        data: currentGraphData,
                        borderColor: theme.line,
                        backgroundColor: theme.lineFill,
                        borderWidth: 2, fill: true, tension: 0.2,
                        pointBackgroundColor: theme.point, pointRadius: 5,
                        pointHoverRadius: 8, pointBorderColor: theme.pointBorder,
                        pointBorderWidth: 2, pointHitRadius: 15,
                        pointStyle: 'circle'
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    interaction: { mode: 'nearest', axis: 'x', intersect: true },
                    plugins: { 
                        legend: { display: false },
                        tooltip: { 
                            enabled: true, mode: 'nearest', intersect: true,
                            backgroundColor: 'rgba(0,0,0,0.9)', titleColor: theme.tooltip,
                            bodyColor: '#fff', borderColor: theme.tooltip, borderWidth: 1,
                            callbacks: {
                                title: function(t) { return `Round ${t[0].label}`; },
                                label: function(c) { return `XP/min: ${c.parsed.y.toLocaleString()}`; }
                            }
                        }
                    },
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'XP per Minute', color: '#888' }},
                        zpmAxis: { display: zpmOverlayEnabled, position: 'right', beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { color: theme.zpm }, title: { display: true, text: 'Zombies/min', color: theme.zpm }},
                        x: { grid: { color: '#333' }, ticks: { color: '#aaa', maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 8, stepSize: 1 }, title: { display: true, text: 'Round', color: '#888' }}
                    },
                    elements: { point: { hoverBorderWidth: 3, hoverBorderColor: '#fff' } },
                    layout: { padding: { top: 10, bottom: 10, left: 5, right: 5 } }
                }
            });
            syncXpmOverlayDataset();
            xpmChartInstance.update('none');
        }

        // --- UPDATED ROUND XP CHART (No Flickering!) ---
        function renderRoundXpChart() {
            const canvas = document.getElementById('roundXpChart');
            const wrapper = document.getElementById('roundxp-scroll-wrapper');
            if (!canvas || !wrapper) return;
            
            sizeGraphCanvas(canvas, wrapper, currentRoundXpLabels.length);
            
            // If the chart already exists, just update the data silently!
            if (roundXpChartInstance) {
                roundXpChartInstance.data.labels = currentRoundXpLabels;
                roundXpChartInstance.data.datasets[0].data = currentRoundXpData;
                roundXpChartInstance.resize();
                roundXpChartInstance.update('none'); 
                return;
            }
            
            // Otherwise, create it for the first time
            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            roundXpChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: currentRoundXpLabels, 
                    datasets: [{
                        label: 'XP Gained',
                        data: currentRoundXpData, 
                        backgroundColor: theme.bar,
                        borderColor: theme.barBorder,
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    plugins: { 
                        legend: { display: false },
                        tooltip: { mode: 'index', intersect: false, titleColor: theme.tooltip } 
                    },
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'XP Gained', color: '#888' }},
                        x: { grid: { display: false }, ticks: { color: '#aaa' }, title: { display: true, text: 'Round', color: '#888' }}
                    }
                }
            });
        }

        function renderZpmChart() {
            const canvas = document.getElementById('zpmChart');
            const wrapper = document.getElementById('zpm-scroll-wrapper');
            if (!canvas || !wrapper) return;

            sizeGraphCanvas(canvas, wrapper, currentZpmLabels.length);

            if (zpmChartInstance) {
                zpmChartInstance.data.labels = currentZpmLabels;
                zpmChartInstance.data.datasets[0].data = currentZpmData;
                zpmChartInstance.resize();
                zpmChartInstance.update('none');
                return;
            }

            const ctx = canvas.getContext('2d');
            const theme = getGraphTheme();
            zpmChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: currentZpmLabels,
                    datasets: [{
                        label: 'Zombies Per Minute',
                        data: currentZpmData,
                        borderColor: theme.zpm,
                        backgroundColor: theme.zpmFill,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.2,
                        pointBackgroundColor: theme.zpm,
                        pointRadius: 5,
                        pointHoverRadius: 8,
                        pointBorderColor: theme.pointBorder,
                        pointBorderWidth: 2,
                        pointHitRadius: 15
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: false,
                    interaction: { mode: 'nearest', axis: 'x', intersect: true },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            enabled: true, mode: 'nearest', intersect: true,
                            backgroundColor: 'rgba(0,0,0,0.9)', titleColor: theme.zpm,
                            bodyColor: '#fff', borderColor: theme.zpm, borderWidth: 1,
                            callbacks: {
                                title: function(t) { return `Round ${t[0].label}`; },
                                label: function(c) { return `ZPM: ${Number(c.parsed.y).toLocaleString()}`; }
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#333' }, ticks: { color: '#aaa' }, title: { display: true, text: 'Zombies per Minute', color: '#888' }},
                        x: { grid: { color: '#333' }, ticks: { color: '#aaa', maxRotation: 45, minRotation: 45, autoSkip: true, maxTicksLimit: 8, stepSize: 1 }, title: { display: true, text: 'Round', color: '#888' }}
                    },
                    layout: { padding: { top: 10, bottom: 10, left: 5, right: 5 } }
                }
            });
        }
            let isLive = true;
            let lastRound = 0;
            let GLOBAL_NAMES = [];
            let GLOBAL_MAPS = {};
            let MAP_KEYS = [];
            let currentMapIndex = 0;
            let currentStarredWeapons = [];
            let currentChalFilter = 'operations';

            let currentPlayerIndex = 0;
               let cachedPlayers = [];
               let currentGameId = "";

               // --- NEW PAGINATION CODE ---
               let currentHistoryPage = 1;
               let totalHistoryPages = 1;

               function changeHistoryPage(dir) {
                   currentHistoryPage += dir;
                   if (currentHistoryPage < 1) currentHistoryPage = 1;
                   if (currentHistoryPage > totalHistoryPages) currentHistoryPage = totalHistoryPages;
                   
                   document.getElementById('history-list').innerHTML = "";
                   updateSidebar();
               }
               // ---------------------------

            function toggleOverlays(checkbox) {
                window.pywebview.api.toggle_overlay_system(checkbox.checked);
            }

            function toggleXpDebugger(checkbox) {
                window.pywebview.api.toggle_xp_debugger(checkbox.checked);
            }

            function hideWorkshopImages() {
                const targets = [
                    ['live-workshop-container', 'live-workshop-img'],
                    ['career-workshop-container', 'career-workshop-img']
                ];
                targets.forEach(([containerId, imgId]) => {
                    const container = document.getElementById(containerId);
                    const img = document.getElementById(imgId);
                    if (img) {
                        img.removeAttribute('src');
                        img.style.display = 'none';
                    }
                    if (container) container.style.display = 'none';
                });
            }

            function toggleWorkshopImages(checkbox) {
                workshopImagesEnabled = checkbox.checked;
                if (!workshopImagesEnabled) hideWorkshopImages();
                window.pywebview.api.toggle_workshop_images(checkbox.checked);
            }

            function escapeHtml(value) {
                return String(value ?? '').replace(/[&<>"']/g, ch => ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;'
                }[ch]));
            }

            function switchTab(tabName) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.sb-item').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.config-btn').forEach(el => el.classList.remove('active'));
                
                document.getElementById('tab-' + tabName).classList.add('active');
                
                if(tabName === 'live') {
                    isLive = true;
                    document.getElementById('live-btn').classList.add('active');
                    
                    // --- NEW: REDRAW GRAPH WHEN RETURNING ---
                    const graphContainer = document.getElementById('xpm-graph-container');
                    const zpmContainer = document.getElementById('zpm-graph-container');
                    if (graphContainer && graphContainer.style.display === 'block') {
                        // A tiny 50ms delay ensures the tab is fully visible before Chart.js does its math
                        setTimeout(() => { renderXpmChart(); }, 50); 
                    }
                    if (zpmContainer && zpmContainer.style.display === 'block') {
                        setTimeout(() => { renderZpmChart(); }, 50);
                    }
                    // ----------------------------------------
                    
                } else if(tabName === 'camo') {
                    isLive = false;
                    document.getElementById('camo-btn').classList.add('active');
                } else if(tabName === 'career') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                    loadCareerData();
                } else if(tabName === 'bestmatches') {
                    isLive = false;
                    document.getElementById('bestmatches-btn').classList.add('active');
                    loadBestMatches();
                } else if(tabName === 'challenges') {
                    isLive = false;
                    document.getElementById('chal-btn').classList.add('active');
                    loadChallenges(); 
                } else if(tabName === 'settings') {
                    isLive = false;
                    loadThemeList();
                    loadCardList(); 
                } else {
                    isLive = false; 
                }
            }
            
            // --- THEME & CARD FUNCTIONS ---
            async function loadThemeList() {
                const themes = await window.pywebview.api.get_available_themes();
                const select = document.getElementById('theme-selector');
                select.innerHTML = '<option value="default">Default Tactical</option>';
                themes.forEach(t => {
                    const display = t.charAt(0).toUpperCase() + t.slice(1);
                    select.innerHTML += `<option value="${t}">${display}</option>`;
                });
                const current = await window.pywebview.api.get_active_theme();
                if(current) select.value = current;
            }

            async function loadCardList() {
                const cards = await window.pywebview.api.get_unlocked_calling_cards();
                const select = document.getElementById('card-selector');
                select.innerHTML = '<option value="default">None Equipped</option>';
                cards.forEach(c => {
                    if(c !== 'default' && !c.includes('void') && !c.includes('origins') && !c.includes('redhex') && !c.includes('gold') && !c.includes('retro') && !c.includes('matrix')) {
                        select.innerHTML += `<option value="${c}">${c.replace('_',' ').toUpperCase()}</option>`;
                    }
                });
                const current = await window.pywebview.api.get_active_card();
                if(current) {
                    select.value = current;
                    previewCard(current);
                }
            }

            function showMedia(src, imgId, vidId) {
                const img = document.getElementById(imgId);
                const vid = document.getElementById(vidId);
                
                if (!src) {
                    img.style.display = 'none';
                    vid.style.display = 'none';
                    return;
                }

                if (src.startsWith('data:video')) {
                    img.style.display = 'none';
                    vid.src = src;
                    vid.style.display = 'block';
                    vid.play().catch(e => console.log("Autoplay blocked/failed", e)); 
                } else {
                    vid.style.display = 'none';
                    vid.pause();
                    img.src = src;
                    img.style.display = 'block';
                }
            }

            async function previewCard(cardName) {
                if(cardName === 'default') {
                    showMedia(null, 'card-preview', 'card-preview-video');
                    return;
                }
                const src = await window.pywebview.api.get_card_image(cardName);
                showMedia(src, 'card-preview', 'card-preview-video');
            }

            async function applySelectedCard() {
                const sel = document.getElementById('card-selector');
                await window.pywebview.api.set_active_card(sel.value);
                alert("Player Card Equipped!");
            }

            async function applySelectedTheme() {
                const select = document.getElementById('theme-selector');
                const themeName = select.value;
                const cssContent = await window.pywebview.api.get_theme_content(themeName);
                document.getElementById('theme-injector').innerHTML = cssContent;
                await window.pywebview.api.set_active_theme(themeName);
                currentThemeName = themeName || 'default';
                applyGraphTheme();
                alert("Theme Applied: " + themeName);
            }

            // --- NEW: BACKUP LOGIC ---
            async function backupStats() {
                try {
                    const res = await window.pywebview.api.backup_player_stats();
                    if (res.success) {
                        alert(res.msg);
                    } else {
                        alert("Backup Failed: " + res.msg);
                    }
                } catch(e) {
                    alert("An error occurred during backup.");
                    console.error(e);
                }
            }

            async function addBestMatch() {
                const btn = document.getElementById('best-match-btn');
                try {
                    if (btn) btn.disabled = true;
                    const res = await window.pywebview.api.add_current_best_match(currentGameId);
                    alert(res.msg || (res.success ? "Best match saved." : "Could not save best match."));
                    const bestTab = document.getElementById('tab-bestmatches');
                    if (res.success && bestTab && bestTab.classList.contains('active')) {
                        loadBestMatches();
                    }
                } catch(e) {
                    alert("Could not save best match: " + e);
                } finally {
                    if (btn) btn.disabled = false;
                }
            }

            async function loadBestMatches() {
                const container = document.getElementById('best-matches-list');
                if (!container) return;
                try {
                    const matches = await window.pywebview.api.get_best_matches();
                    if (!matches || matches.length === 0) {
                        container.innerHTML = "<div style='color:#777; font-style:italic; padding:8px 0;'>No best matches saved yet. Use Add Best Match on the live dashboard.</div>";
                        return;
                    }
                    let html = "";
                    matches.forEach(item => {
                        const xpText = item.match_xp && item.match_xp > 0 ? `${parseInt(item.match_xp).toLocaleString()} XP` : "XP not recorded";
                        const missingText = item.exists ? "" : "<span style='color:var(--danger); font-size:0.75em; margin-left:8px;'>MISSING ARCHIVE</span>";
                        html += `
                            <div class="sb-item best-match-row" style="border:1px solid rgba(255,255,255,0.08); border-left:3px solid var(--accent); background:rgba(0,0,0,0.18); border-radius:6px; padding:14px 16px; cursor:pointer;" onclick="loadHistory('${escapeHtml(item.id)}', this)">
                                <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start;">
                                    <div style="min-width:0;">
                                        <div class="sb-map">${escapeHtml(item.map)}${missingText}</div>
                                        <div class="sb-date">Round ${escapeHtml(item.round)} // ${escapeHtml(item.time)} // ${escapeHtml(item.date)}</div>
                                        <div class="sb-id" title="${escapeHtml(item.id)}">${escapeHtml(item.id)}</div>
                                    </div>
                                    <div style="display:flex; align-items:center; gap:10px; flex-shrink:0;">
                                        <div style="color:var(--highlight); font-weight:bold; white-space:nowrap;">${xpText}</div>
                                        <button class="nav-btn-small" onclick="removeBestMatch(event, '${escapeHtml(item.id)}')" style="height:28px; padding:0 10px; background:var(--danger); color:#fff; font-size:0.75em;">REMOVE</button>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    container.innerHTML = html;
                } catch(e) {
                    container.innerHTML = "<div style='color:var(--danger); padding:8px 0;'>Could not load best matches.</div>";
                    console.error("Best Matches Load Error", e);
                }
            }

            async function removeBestMatch(event, gameId) {
                event.stopPropagation();
                if (!confirm("Remove this match from Best Matches?")) return;
                try {
                    const res = await window.pywebview.api.remove_best_match(gameId);
                    if (!res.success) {
                        alert(res.msg || "Could not remove best match.");
                        return;
                    }
                    loadBestMatches();
                } catch(e) {
                    alert("Could not remove best match: " + e);
                }
            }

            // --- CHALLENGE LOGIC ---
            function filterChallenges(cat) {
                currentChalFilter = cat;
                const container = document.getElementById('challenge-list');
                container.innerHTML = ""; 
                loadChallenges();
            }

            async function loadChallenges() {
                const list = await window.pywebview.api.get_challenges();
                const container = document.getElementById('challenge-list');
                
                if (currentChalFilter === 'themes') {
                    const themeGroups = {
                        'Void': 'c_void', 'Origins': 'c_org', 'Red Hex': 'c_red',
                        'Gold': 'c_gold', 'Retro': 'c_retro', 'Matrix': 'c_mat'
                    };
                    
                    list.forEach(c => {
                        if (c.id.startsWith('c_auto_th_')) {
                            const parts = c.id.split('_');
                            if (parts.length >= 5) {
                                const tName = parts[3];
                                const displayName = tName.charAt(0).toUpperCase() + tName.slice(1);
                                if (!themeGroups[displayName]) {
                                    themeGroups[displayName] = `c_auto_th_${tName}`;
                                }
                            }
                        }
                    });
                    
                    let html = "";
                    for (const [name, prefix] of Object.entries(themeGroups)) {
                        const themeChallenges = list.filter(c => c.id.startsWith(prefix));
                        if(themeChallenges.length > 0) {
                            html += `<div class="theme-header">${name} MASTERY</div>`;
                            themeChallenges.forEach(c => html += renderChallengeCardInner(c, true));
                        }
                    }
                    container.innerHTML = html;
                    return;
                }

                const filtered = list.filter(c => {
                    if (c.id.startsWith('c_void') || c.id.startsWith('c_org') || c.id.startsWith('c_red') || 
                        c.id.startsWith('c_gold') || c.id.startsWith('c_retro') || c.id.startsWith('c_mat') ||
                        c.id.startsWith('c_auto_th_')) {
                        return false; 
                    }
                    if(currentChalFilter === 'lifetime') return c.cat === 'lifetime';
                    if(currentChalFilter === 'operations') return c.cat === 'operations';
                    return true;
                });

                filtered.forEach(c => {
                    const existingCard = document.getElementById(`chal-${c.id}`);
                    const newHTML = renderChallengeCardInner(c, false);
                    
                    if (existingCard) {
                        if (existingCard.innerHTML !== newHTML) {
                             existingCard.innerHTML = newHTML;
                             existingCard.className = `chal-card ${c.completed?'done':''}`;
                        }
                    } else {
                        const div = document.createElement('div');
                        div.id = `chal-${c.id}`;
                        div.className = `chal-card ${c.completed?'done':''}`;
                        div.innerHTML = newHTML;
                        container.appendChild(div);
                    }
                });
            }

            function renderChallengeCardInner(c, isThemeView) {
                const pct = Math.min(100, Math.round((c.progress / c.target) * 100));
                const isDone = c.completed;
                let btnText = "LOCKED";
                let btnClass = "";
                let action = "";
                let rewardTxt = "";

                if(c.reward_type === 'theme') rewardTxt = `🏆 THEME: ${c.reward_val.toUpperCase()}`;
                else if(c.reward_type === 'xp') rewardTxt = `⭐ XP: ${c.reward_val}`;
                else if(c.reward_type === 'calling_card') rewardTxt = `📇 CARD: ${c.reward_val}`;
                else rewardTxt = `REWARD: ${c.reward_val}`;

                if (isDone) {
                    if (c.reward_type === 'theme') {
                        btnText = "EQUIP THEME";
                        btnClass = "active";
                        action = `applyTheme('${c.reward_val}')`;
                    } else if (c.reward_type === 'calling_card') {
                        btnText = "UNLOCKED"; 
                        btnClass = "active";
                    } else {
                        btnText = "COMPLETED";
                        btnClass = "active"; 
                    }
                }

                if (isThemeView) {
                     return `
                    <div class="chal-card ${isDone?'done':''}">
                        <div style="display:flex; justify-content:space-between;">
                            <div style="font-weight:bold; color:#fff">${c.title}</div>
                            <div style="font-size:0.7em; color:var(--highlight)">${c.cat ? c.cat.toUpperCase() : ''}</div>
                        </div>
                        <div style="font-size:0.8em; color:#aaa; margin-bottom:5px;">${c.desc}</div>
                        <div style="font-size:0.7em; color:#fff; margin-bottom:5px;">${rewardTxt}</div>
                        <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
                        <div style="font-size:0.7em; text-align:right;">${parseInt(c.progress)} / ${c.target}</div>
                        <button class="chal-btn ${btnClass}" onclick="${action}">${btnText}</button>
                    </div>`;
                }

                return `
                        <div style="display:flex; justify-content:space-between;">
                            <div style="font-weight:bold; color:#fff">${c.title}</div>
                            <div style="font-size:0.7em; color:var(--highlight)">${c.cat ? c.cat.toUpperCase() : ''}</div>
                        </div>
                        <div style="font-size:0.8em; color:#aaa; margin-bottom:5px;">${c.desc}</div>
                        <div style="font-size:0.7em; color:#fff; margin-bottom:5px;">${rewardTxt}</div>
                        <div class="progress-bar"><div class="fill" style="width:${pct}%"></div></div>
                        <div style="font-size:0.7em; text-align:right;">${parseInt(c.progress)} / ${c.target}</div>
                        <button class="chal-btn ${btnClass}" onclick="${action}">${btnText}</button>
                `;
            }

            async function resetOps() {
                if(confirm("Are you sure you want to reset all challenge progress? This cannot be undone.")) {
                    await window.pywebview.api.reset_challenges_api();
                    alert("Challenges Reset.");
                    loadChallenges(); 
                }
            }
            
            let careerMapData = null; // Store the map data for toggling
            
            async function loadCareerData() {
                 // Fetch and display Top XP Maps
                 loadTopXPMaps(); 

                 const activeCard = await window.pywebview.api.get_active_card();
                 if(activeCard && activeCard !== 'default') {
                     const src = await window.pywebview.api.get_card_image(activeCard);
                     showMedia(src, 'card-display', 'card-display-video');
                 } else {
                     showMedia(null, 'card-display', 'card-display-video');
                 }

                 try {
                     const levelInfo = await window.pywebview.api.get_career_level_info();
                     if(levelInfo && !levelInfo.error) {
                         const prestBox = document.getElementById('career-prest-box');
                         const prestImg = document.getElementById('career-prest-icon');
                         if(levelInfo.prest_icon || levelInfo.leg_icon || levelInfo.abso_icon || levelInfo.ult_icon) {
                             prestBox.style.display = 'block';
                             
                             const oldIcons = prestBox.querySelectorAll('.custom-tier-icon');
                             oldIcons.forEach(icon => icon.remove());

                             if(levelInfo.prest_icon) {
                                 prestImg.src = levelInfo.prest_icon;
                                 prestImg.style.display = 'inline-block';
                             } else {
                                 prestImg.style.display = 'none';
                             }

                             const addIcon = (src) => {
                                 if (!src) return;
                                 const img = document.createElement('img');
                                 img.src = src;
                                 img.className = 'custom-tier-icon';
                                 let targetHeight = prestImg.clientHeight;
                                 if (targetHeight === 0) {
                                     img.style.height = '28px';
                                 } else {
                                     img.style.height = targetHeight + 'px';
                                 }
                                 img.style.width = 'auto';
                                 img.style.objectFit = 'contain';
                                 img.style.marginRight = '6px';
                                 prestBox.insertBefore(img, prestImg);
                             };

                             addIcon(levelInfo.leg_icon);
                             addIcon(levelInfo.abso_icon);
                             addIcon(levelInfo.ult_icon);
                         }
                         const lvlBox = document.getElementById('career-lvl-box');
                         const lvlImg = document.getElementById('career-lvl-icon');
                         if(levelInfo.lvl_icon) {
                             lvlImg.src = levelInfo.lvl_icon;
                             lvlBox.style.display = 'block';
                         }
                         document.getElementById('career-rmain').innerText = levelInfo.r_main;
                         document.getElementById('career-rsub').innerText = levelInfo.r_sub;
                         document.getElementById('career-title').innerText = levelInfo.title;
                         document.getElementById('career-map-name').innerText = 'Map: ' + levelInfo.map_name;
                         document.getElementById('career-xp-text').innerText = parseInt(levelInfo.current_xp).toLocaleString() + ' / ' + parseInt(levelInfo.xp_required).toLocaleString() + ' XP';
                         document.getElementById('career-xp-pct').innerText = levelInfo.progress_pct + '%';
                         document.getElementById('career-xp-bar').style.width = levelInfo.progress_pct + '%';
                          if(levelInfo.progress_pct >= 100) {
                              document.getElementById('career-xp-bar').classList.add('max');
                          } else {
                              document.getElementById('career-xp-bar').classList.remove('max');
                          }
                          const workshopContainer = document.getElementById('career-workshop-container');
                          const workshopImg = document.getElementById('career-workshop-img');
                          if(workshopImagesEnabled && levelInfo.workshop_image) {
                              workshopImg.src = levelInfo.workshop_image;
                              workshopImg.style.display = 'block';
                              workshopContainer.style.display = 'block';
                          } else {
                              workshopImg.style.display = 'none';
                              workshopContainer.style.display = 'none';
                          }
                      }
                 } catch(e) { console.error("Career Level Load Error", e); }

                 try {
                    const data = await window.pywebview.api.get_lifetime_stats();
                    if(data && !data.error) {
                        document.getElementById('life_kills').innerText = parseInt(data.totals.kills).toLocaleString();
                        document.getElementById('life_headshots').innerText = parseInt(data.totals.headshots).toLocaleString();
                        document.getElementById('life_hs_pct').innerText = data.ratios.hs_percent + "%";
                        let favGunsText = "None (0)";
if (data.favorite_weapons && data.favorite_weapons.length > 0) {
    // Joins the top 3 weapons with a line break so they stack neatly on the right side
    favGunsText = data.favorite_weapons.map(w => w.name + " (" + w.kills.toLocaleString() + ")").join("<br>");
}
document.getElementById('life_fav_gun').innerHTML = favGunsText;
                        
                        document.getElementById('life_rounds').innerText = parseInt(data.totals.rounds).toLocaleString();
                        document.getElementById('life_time').innerText = data.time_str;
                        document.getElementById('life_matches').innerText = data.totals.matches;
                        document.getElementById('life_kpd').innerText = data.ratios.kpd;
                        
                        document.getElementById('life_doors').innerText = parseInt(data.totals.doors).toLocaleString();
                        document.getElementById('life_gums').innerText = parseInt(data.totals.gums).toLocaleString();
                        document.getElementById('life_box').innerText = parseInt(data.totals.box).toLocaleString();
                        document.getElementById('life_pts').innerText = parseInt(data.totals.pts).toLocaleString();
                        
                       let mapHtml = "";
                        const sortedMaps = Object.entries(data.best_map_rounds).sort((a, b) => b[1] - a[1]);
                        for (const [map, rnd] of sortedMaps) {
                            mapHtml += `<div style="display:flex; justify-content:space-between; border-bottom:1px solid #333; padding:2px 0;"><span>${map}</span><span style="color:#fff">${rnd}</span></div>`;
                        }
                        document.getElementById('life_map_list').innerHTML = mapHtml;

                        // --- NEW CODE FOR MOST PLAYED MAPS ---
                        careerMapData = data; 
                        renderMostPlayedMaps(); 
                        // -------------------------------------
                    }
                } catch(e) { console.error("Career Load Error", e); }
            }
            
            // ---> PASTE THE NEW FUNCTION RIGHT HERE <---
            function renderMostPlayedMaps() {
                if (!careerMapData) return;
                const sortBy = document.getElementById('map-sort-toggle').value;
                let playedHtml = "";
                
                if (sortBy === 'matches' && careerMapData.top_played_maps && careerMapData.top_played_maps.length > 0) {
                    careerMapData.top_played_maps.forEach(entry => {
                        playedHtml += `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #333; padding:6px 5px;">
                            <span style="color:#ddd;">${entry.name}</span>
                            <span style="color:var(--highlight); font-weight:bold;">${entry.count} Matches</span>
                        </div>`;
                    });
                } else if (sortBy === 'time' && careerMapData.top_played_maps_time && careerMapData.top_played_maps_time.length > 0) {
                    careerMapData.top_played_maps_time.forEach(entry => {
                        playedHtml += `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #333; padding:6px 5px;">
                            <span style="color:#ddd;">${entry.name}</span>
                            <span style="color:var(--highlight); font-weight:bold;">${entry.time_str}</span>
                        </div>`;
                    });
                } else {
                    playedHtml = "<div style='padding:5px;'>No map data recorded yet.</div>";
                }
                
                document.getElementById('life_most_played').innerHTML = playedHtml;
            }
            // -------------------------------------------
            
            async function loadTopXPMaps() {
    try {
        const topMaps = await window.pywebview.api.get_top_10_xp_maps("0");
        const container = document.getElementById('top_xp_maps_list');
        
        if (!topMaps || topMaps.length === 0) {
            container.innerHTML = "<div style='padding:10px 5px;'>No match XP data recorded yet.</div>";
            return;
        }

        let html = '<div style="display: flex; flex-direction: column;">';
        topMaps.forEach(entry => {
            html += `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #333; padding:10px 5px; flex-shrink:0; min-height:25px;">
                <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; padding-right:15px; color:#ddd;">${entry.map}</span>
                <span style="color:var(--highlight); font-weight:bold; white-space:nowrap;">${entry.xp.toLocaleString()} XP</span>
            </div>`;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch(e) { 
        console.error("Top XP Load Error", e); 
    }
}
            
            async function init() {
                updateSidebar();
                switchTab('live');
                
                await window.pywebview.api.force_sync_challenges();
                
                const savedTheme = await window.pywebview.api.get_active_theme();
                currentThemeName = savedTheme || 'default';
                if (savedTheme && savedTheme !== 'default') {
                    const css = await window.pywebview.api.get_theme_content(savedTheme);
                    document.getElementById('theme-injector').innerHTML = css;
                }
                applyGraphTheme();
                
                setInterval(async () => {
                    if (isLive) {
                        try {
                            const data = await window.pywebview.api.get_live_stats();
                            if (isLive) updateData(data); 
                        } catch(e) {}
                    }
                    updateSidebar();
                    
                    const chalTab = document.getElementById('tab-challenges');
                    if (chalTab && chalTab.classList.contains('active')) {
                        loadChallenges();
                    }
                    const bestTab = document.getElementById('tab-bestmatches');
                    if (bestTab && bestTab.classList.contains('active')) {
                        loadBestMatches();
                    }
                }, 3000);
            }
            
            // --- NEW: MULTI-PLAYER TAB LOGIC ---
            function switchPlayerTab(index) {
                currentPlayerIndex = index;
                document.querySelectorAll('.player-tab').forEach((el, i) => {
                    el.classList.toggle('active', i === index);
                });
                if (cachedPlayers && cachedPlayers.length > index) {
                    updatePlayerUI(cachedPlayers[index]);
                }
            }

            function buildPlayerTabs(players) {
                const container = document.getElementById('player-tabs-container');
                if (!container) return;
                if (players.length !== container.children.length) {
                    container.innerHTML = "";
                    players.forEach((p, i) => {
                        const btn = document.createElement('button');
                        btn.className = `player-tab ${i === currentPlayerIndex ? 'active' : ''}`;
                        btn.innerText = `PLAYER ${i + 1}`; 
                        btn.onclick = () => switchPlayerTab(i);
                        container.appendChild(btn);
                    });
                }
                
                const content = document.getElementById('player-specific-content');
                if (content) {
                    if (players.length > 0) {
                        content.style.display = 'block';
                        if (currentPlayerIndex >= players.length) currentPlayerIndex = 0;
                    } else {
                        content.style.display = 'none';
                    }
                }
            }

            function updateData(d) {
                if(!d || !d.game) return;
                currentGameId = d.game.id || "";

                const currentRound = parseInt(d.game.round);
                if (currentRound > lastRound && lastRound !== 0) {
                    if (currentRound % 5 === 0) {
                        triggerMilestoneAnim(currentRound);
                    }
                }
                lastRound = currentRound;

                const setTxt = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
                const setHtml = (id, val) => { const el = document.getElementById(id); if(el) el.innerHTML = val || ''; };
                
                setTxt('d_status_bar', d.game.status);
                const statusBar = document.getElementById('d_status_bar');
                if(statusBar) statusBar.style.borderLeftColor = d.game.color;
                setTxt('d_map', d.game.map);
                setTxt('d_round', d.game.round);
                setTxt('d_time', d.game.time);
                setTxt('d_avg_time', d.game.avg_time + "s");
                setTxt('d_zpm', d.game.zpm);
                setTxt('d_mode', d.game.mode);
                setTxt('d_version', d.game.version);
                setHtml('d_nerf', d.game.nerf);

                try {
                    var workshopContainer = document.getElementById('live-workshop-container');
                    var workshopImg = document.getElementById('live-workshop-img');
                    if (workshopContainer && workshopImg) {
                        if (!workshopImagesEnabled) {
                            workshopImg.removeAttribute('src');
                            workshopImg.style.display = 'none';
                            workshopContainer.style.display = 'none';
                        } else {
                            var sl = d.game.steam_link;
                            if (sl && sl !== '0' && sl !== '') {
                            if (window._workshopCache && window._workshopCache[sl]) {
                                workshopImg.src = window._workshopCache[sl];
                                workshopImg.style.display = 'block';
                                workshopContainer.style.display = 'block';
                            } else {
                                (function(link) {
                                    window.pywebview.api.get_workshop_image(link).then(function(imgSrc) {
                                        if (imgSrc && workshopImg) {
                                            workshopImg.src = imgSrc;
                                            workshopImg.style.display = 'block';
                                            workshopContainer.style.display = 'block';
                                            if (!window._workshopCache) window._workshopCache = {};
                                            window._workshopCache[link] = imgSrc;
                                        }
                                    }).catch(function() {});
                                })(sl);
                            }
                            } else {
                                workshopImg.style.display = 'none';
                                workshopContainer.style.display = 'none';
                            }
                        }
                    }
                } catch(e) {}

                try {
                    cachedPlayers = d.players || [];
                    buildPlayerTabs(cachedPlayers);
                    
                    if (cachedPlayers.length > 0) {
                        updatePlayerUI(cachedPlayers[currentPlayerIndex]);
                    }
                } catch(e) { console.error("Error updating player data:", e); }
            }

            function updatePlayerUI(p) {
                if (!p) return;
                const setTxt = (id, val) => { const el = document.getElementById(id); if(el) el.innerText = val; };
                const setHtml = (id, val) => { const el = document.getElementById(id); if(el) el.innerHTML = val || ''; };
                
                const prestBox = document.getElementById('d_prest_box');
                const prestImg = document.getElementById('d_prest_icon');
                if (prestBox && (p.prest_icon || p.leg_icon || p.abso_icon || p.ult_icon)) {
                    prestBox.style.display = 'block';
                    
                    const oldIcons = prestBox.querySelectorAll('.custom-tier-icon');
                    oldIcons.forEach(icon => icon.remove());

                    if (p.prest_icon && prestImg) {
                        prestImg.src = p.prest_icon;
                        prestImg.style.display = 'inline-block';
                    } else if (prestImg) {
                        prestImg.style.display = 'none';
                    }

                    const addIcon = (src) => {
                        if (!src || !prestImg) return;
                        const img = document.createElement('img');
                        img.src = src;
                        img.className = 'custom-tier-icon';
                        
                        let targetHeight = prestImg.clientHeight;
                        if (targetHeight === 0) {
                            img.style.height = '28px'; 
                        } else {
                            img.style.height = targetHeight + 'px';
                        }

                        img.style.width = 'auto';
                        img.style.objectFit = 'contain';
                        img.style.marginRight = '6px';
                        
                        prestBox.insertBefore(img, prestImg);
                    };

                    addIcon(p.leg_icon);
                    addIcon(p.abso_icon);
                    addIcon(p.ult_icon);

                } else if (prestBox) {
                    prestBox.style.display = 'none';
                }

                const lvlBox = document.getElementById('d_lvl_box');
                const lvlImg = document.getElementById('d_lvl_icon');
                if (lvlBox && lvlImg) {
                    if (p.lvl_icon) {
                        lvlImg.src = p.lvl_icon;
                        lvlBox.style.display = 'block';
                    } else {
                        lvlBox.style.display = 'none';
                    }
                }

                setTxt('d_rmain', p.r_main);
                setTxt('d_title', p.title);
                setTxt('d_rsub', p.r_sub);
                setTxt('d_gums', p.gums);
                setTxt('d_xp', p.xp);
                setTxt('d_mult', p.mult);
                setTxt('d_kills', p.k);
                setTxt('d_score', p.pts);
                setTxt('d_acc', p.acc);
                setTxt('d_melee', p.melee);
                setTxt('d_equip', p.equip);
                setTxt('d_downs', p.downs);
                setTxt('d_leth', p.leth);
                setTxt('d_tact', p.tact);
                setHtml('d_perks', p.perks);
                setHtml('d_weaps', p.weaps);

               // --- NEW GRAPH DATA BINDING ---
                currentGraphLabels = p.graph_labels || [];
                currentGraphData = p.graph_data || [];
                currentRoundXpLabels = p.round_xp_labels || [];
                currentRoundXpData = p.round_xp_data || [];
                currentZpmLabels = p.zpm_labels || [];
                currentZpmData = p.zpm_data || [];
                
                const graphContainer = document.getElementById('xpm-graph-container');
                const roundXpContainer = document.getElementById('roundxp-graph-container');
                const zpmContainer = document.getElementById('zpm-graph-container');
                const liveTab = document.getElementById('tab-live');
                
                // ONLY render if the graph is open AND the live tab is actually visible!
                if (graphContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderXpmChart();
                }
                if (roundXpContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderRoundXpChart();
                }
                if (zpmContainer && zpmContainer.style.display === 'block' && liveTab.classList.contains('active')) {
                    renderZpmChart();
                }
                // ------------------------------
             }   
               function triggerMilestoneAnim(round) {
                const overlay = document.createElement('div');
                overlay.className = 'milestone-overlay';
                overlay.innerHTML = `<div class="milestone-text">ROUND ${round} REACHED</div>`;
                document.body.appendChild(overlay);
                setTimeout(() => {
                    overlay.remove();
                }, 3000);
            }
            
            async function updateSidebar() {
                try {
                    // Fetch the specific page from Python
                    const response = await window.pywebview.api.get_history_list(currentHistoryPage);
                    const newHistory = response.items;
                    totalHistoryPages = response.total_pages;
                    currentHistoryPage = response.current_page;
                    
                    // Update the page text (e.g. "1 / 4")
                    const pageInfo = document.getElementById('hist-page-info');
                    if (pageInfo) pageInfo.innerText = `${currentHistoryPage} / ${totalHistoryPages}`;

                    const listEl = document.getElementById('history-list');
                    
                    if (listEl.children.length !== newHistory.length || 
                       (newHistory.length > 0 && listEl.dataset.firstId !== newHistory[0].id)) {
                        
                        listEl.innerHTML = "";
                        if (newHistory.length > 0) listEl.dataset.firstId = newHistory[0].id;

                        newHistory.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'sb-item';
                            div.innerHTML = `
                                <div class="sb-map">${item.map}</div>
                                <div class="sb-date">${item.date}</div>
                                <div class="sb-id" title="${item.id}">${item.id}</div>
                            `;
                            div.onclick = () => loadHistory(item.id, div);
                            listEl.appendChild(div);
                        });
                    }
                } catch(e) { console.error("Error updating sidebar:", e); }
            }
            
            async function loadHistory(id, el) {
                switchTab('live'); 
                isLive = false; 
                document.querySelectorAll('.sb-item').forEach(i => i.classList.remove('active'));
                if (el) el.classList.add('active');
                const data = await window.pywebview.api.get_history_report(id);
                if (!isLive) {
                    updateData(data);
                    document.getElementById('d_status_bar').innerText = "ARCHIVED MATCH RECORD";
                    document.getElementById('d_status_bar').style.borderLeftColor = "#999";
                }
            }
            
            function askParentToBrowse() {
                window.pywebview.api.browse_user_json().then(path => {
                    if(path) {
                        updateStatus("DECRYPTING...", "#ff9d00");
                        document.getElementById('current-user-path').value = path;
                        window.pywebview.api.get_camo_content(path).then(renderCamoData);
                    }
                });
            }
            
            function askParentToUpdate(w_id, c_idx) {
                const userPath = document.getElementById('current-user-path').value;
                if(!userPath) { alert("No user file loaded."); return; }
                updateLocalUI(w_id, c_idx);
                window.pywebview.api.update_camo_progress(userPath, w_id, c_idx);
            }
            
            function toggleStar(event, w_id) {
                event.stopPropagation(); 
                let targetWeapon = null;
                for (let mapKey in GLOBAL_MAPS) {
                    let weaponList = GLOBAL_MAPS[mapKey].weapons;
                    targetWeapon = weaponList.find(w => w.id == w_id);
                    if (targetWeapon) break;
                }
                
                if (targetWeapon) {
                    if (!targetWeapon.is_starred && currentStarredWeapons.length >= 3) {
                        alert("Max 3 priority weapons."); return; 
                    }
                    targetWeapon.is_starred = !targetWeapon.is_starred;
                    rebuildStarredList();
                    renderCurrentMap();
                    window.pywebview.api.toggle_star(w_id).then(res => {
                        if (!res.success) {
                            targetWeapon.is_starred = !targetWeapon.is_starred;
                            rebuildStarredList();
                            renderCurrentMap();
                            alert(res.msg);
                        }
                    });
                }
            }
            
            function rebuildStarredList() {
                currentStarredWeapons = [];
                for(let m in GLOBAL_MAPS) {
                    GLOBAL_MAPS[m].weapons.forEach(w => {
                        if(w.is_starred) currentStarredWeapons.push(w);
                    });
                }
            }

            function updateLocalUI(w_id, c_idx) {
                // --- NEW FIX: Update the internal memory so searching doesn't reset it ---
                for (let mapKey in GLOBAL_MAPS) {
                    let weapon = GLOBAL_MAPS[mapKey].weapons.find(w => w.id == w_id);
                    if (weapon) {
                        weapon.camo_val = c_idx;
                        weapon.camo_name = GLOBAL_NAMES[c_idx] || "Unknown Camo";
                        break;
                    }
                }
                // -------------------------------------------------------------------------

                const items = document.querySelectorAll(`.camo-option[data-wid='${w_id}']`);
                items.forEach(i => i.classList.remove('active'));
                const selected = document.querySelectorAll(`.camo-option[data-wid='${w_id}'][data-idx='${c_idx}']`);
                selected.forEach(s => s.classList.add('active'));
                
                const txt = document.getElementById(`txt-${w_id}`);
                const txtStar = document.getElementById(`txt-${w_id}-star`);
                
                if(GLOBAL_NAMES[c_idx]) {
                    if(txt) txt.innerText = GLOBAL_NAMES[c_idx];
                    if(txtStar) txtStar.innerText = GLOBAL_NAMES[c_idx];
                }
                const imgNormal = document.getElementById(`img-div-${w_id}`);
                const imgStar = document.getElementById(`img-div-${w_id}-star`);
                if (imgNormal) imgNormal.className = `camo-display-img asset-${c_idx}`;
                if (imgStar) imgStar.className = `camo-display-img asset-${c_idx}`;

                const barNormal = document.getElementById(`bar-${w_id}`);
                const barStar = document.getElementById(`bar-${w_id}-star`);
                let pct = (c_idx / 20) * 100;
                if (barNormal) barNormal.style.width = pct + "%";
                if (barStar) barStar.style.width = pct + "%";
            }
            
            function updateStatus(msg, color) {
                const el = document.getElementById('status-txt');
                el.innerText = msg;
                if(color) el.style.color = color;
            }
            
            function initControls(maps) {
                GLOBAL_MAPS = maps;
                MAP_KEYS = Object.keys(maps).sort();
                const sel = document.getElementById('map-select');
                sel.innerHTML = "";
                MAP_KEYS.forEach((key, idx) => {
                    const opt = document.createElement('option');
                    opt.value = idx;
                    opt.innerText = key;
                    sel.appendChild(opt);
                });
                document.getElementById('controls-area').style.display = "flex";
                currentMapIndex = 0;
                renderCurrentMap();
            }
            
            function changeMap(dir) {
                currentMapIndex += dir;
                if(currentMapIndex < 0) currentMapIndex = MAP_KEYS.length - 1;
                if(currentMapIndex >= MAP_KEYS.length) currentMapIndex = 0;
                document.getElementById('map-select').value = currentMapIndex;
                renderCurrentMap();
            }
            
            function onMapSelect() {
                const sel = document.getElementById('map-select');
                currentMapIndex = parseInt(sel.value);
                renderCurrentMap();
            }
            
            function onSearch() { renderCurrentMap(); }
            
            function createWeaponCard(w, isPriority=false) {
                let trayHtml = `<div class="camo-tray">`;
                for(let i=0; i < GLOBAL_NAMES.length; i++) {
                    let isActive = (i === w.camo_val) ? 'active' : '';
                    trayHtml += `
                        <div class="camo-option ${isActive}" 
                             data-wid="${w.id}" data-idx="${i}" title="${GLOBAL_NAMES[i]}"
                             onclick="askParentToUpdate('${w.id}', ${i})">
                             <div class="camo-img-ref asset-${i}"></div>
                        </div>
                    `;
                }
                trayHtml += `</div>`;
                
                let wPct = (w.camo_val / 20) * 100;
                let starClass = w.is_starred ? "active" : "";
                let domIdSuffix = isPriority ? "-star" : "";
                
                return `
                    <div class="camo-card">
                        <div class="star-btn ${starClass}" onclick="toggleStar(event, '${w.id}')">★</div>
                        <div class="card-head">
                            <div><div class="w-name">${w.name}</div><div class="w-type">${w.type}</div></div>
                            <div class="game-tag">${w.gametype}</div>
                        </div>
                        <div class="w-packed">${w.packed}</div>
                        <div class="progress-bar"><div id="bar-${w.id}${domIdSuffix}" class="fill" style="width:${wPct}%"></div></div>
                        <div class="camo-display">
                            <div class="camo-img-box">
                                <div id="img-div-${w.id}${domIdSuffix}" class="camo-display-img asset-${w.camo_val}"></div>
                            </div>
                            <div>
                                <div style="font-size:0.65em; color:#777;">CURRENT CAMO</div>
                                <div class="camo-text" id="txt-${w.id}${domIdSuffix}">${w.camo_name}</div>
                            </div>
                        </div>
                        ${trayHtml}
                    </div>
                `;
            }

            function renderCurrentMap() {
                try {
                    if(MAP_KEYS.length === 0) return;
                    const mapName = MAP_KEYS[currentMapIndex];
                    const mapData = GLOBAL_MAPS[mapName];
                    const searchText = document.getElementById('search-input').value.toLowerCase();
                    const container = document.getElementById('content-area');
                    container.innerHTML = "";
                    
                    if (currentStarredWeapons.length > 0) {
                        const prioSection = document.createElement('div');
                        prioSection.className = "priority-section";
                        let prioHtml = `<div class="grid">`;
                        currentStarredWeapons.forEach(w => {
                            prioHtml += createWeaponCard(w, true);
                        });
                        prioHtml += `</div>`;
                        prioSection.innerHTML = prioHtml;
                        container.appendChild(prioSection);
                    }

                    const section = document.createElement('div');
                    const filteredWeapons = mapData.weapons.filter(w => {
                        if (w.is_starred) return false; 
                        const n = String(w.name || "").toLowerCase();
                        const t = String(w.type || "").toLowerCase();
                        return n.includes(searchText) || t.includes(searchText);
                    });
                    
                    let pct = 0;
                    if(mapData.total_levels > 0) pct = Math.round((mapData.current_levels / mapData.total_levels) * 100);
                    
                    let html = `
                        <div class="map-title" style="display:flex; justify-content:space-between; margin-bottom:15px; color:#fff;">
                            <span style="font-size:1.5em; font-weight:bold;">${mapName}</span>
                            <span style="color:var(--highlight); font-weight:bold;">${pct}% COMPLETED</span>
                        </div>
                        <div class="progress-bar" style="margin-bottom:20px;"><div class="fill ${pct==100?'max':''}" style="width:${pct}%"></div></div>
                        <div class="grid">
                    `;
                    
                    if(filteredWeapons.length === 0) {
                        html += `<div style="padding:20px; color:#555;">No weapons found matching search.</div></div>`;
                    } else {
                        filteredWeapons.forEach(w => {
                            html += createWeaponCard(w, false);
                        });
                        html += `</div>`;
                    }
                    section.innerHTML = html;
                    container.appendChild(section);
                    
                } catch (e) {
                    console.error(e);
                    document.getElementById('content-area').innerHTML = "<div style='color:red; padding:20px;'>RENDER ERROR: " + e.message + "</div>";
                }
            }
            
            function renderCamoData(data) {
                if(data.error) { alert(data.error); updateStatus("ERROR", "red"); return; }
                GLOBAL_NAMES = data.camo_names;
                
                currentStarredWeapons = [];
                for(let m in data.maps) {
                    data.maps[m].weapons.forEach(w => {
                        if(w.is_starred) currentStarredWeapons.push(w);
                    });
                }

                let cssStr = "";
                if (data.camo_icons) {
                    data.camo_icons.forEach((src, idx) => {
                        if(src) cssStr += `.asset-${idx} { background-image: url('${src}'); } `;
                    });
                }
                document.getElementById('dynamic-camo-styles').innerHTML = cssStr;
                document.getElementById('user-display').innerText = data.username.toUpperCase();
                updateStatus("READY", "#66fcf1");
                if(Object.keys(data.maps).length === 0) return;
                initControls(data.maps);
            }
            
            function reconfigure() {
                if(confirm("Reconfigure paths?")) {
                    window.pywebview.api.reset_config().then(() => window.pywebview.api.launch_setup());
                }
            }
            
            window.addEventListener('pywebviewready', init);
        </script>
    </body>
    </html>
    """

# --- API CLASS ---
class TrackerAPI:
    def __init__(self):
        self.last_user_path = None 

    def backup_player_stats(self):
        live_path = app_config.get('live_path')
        if not live_path or not os.path.exists(live_path):
            return {"success": False, "msg": "Live Game Path not configured or file not found."}
        
        # Start at the directory containing CurrentGame.json
        players_dir = os.path.dirname(live_path)
        
        # Scan backwards up the path tree until we find the actual 'players' folder
        path_obj = Path(live_path)
        for parent in list(path_obj.parents):
            if parent.name.lower() == 'players':
                players_dir = str(parent)
                break
        
        files_to_backup = []
        for i in range(5):
            fname = f"stats_zm_{i}.cgp"
            fpath = os.path.join(players_dir, fname)
            if os.path.exists(fpath):
                files_to_backup.append(fpath)
                
        if not files_to_backup:
            return {"success": False, "msg": f"No stats_zm_*.cgp files found in the folder ({players_dir})."}
            
        save_result = window.create_file_dialog(
            webview.FileDialog.SAVE, 
            save_filename='uem_stats_backup.zip',
            file_types=('ZIP Archives (*.zip)',)
        )
        
        if not save_result:
            return {"success": False, "msg": "Backup cancelled by user."}
            
        # Handle the return type from pywebview (can be tuple or string based on OS)
        save_path = save_result[0] if isinstance(save_result, tuple) else save_result
        if not save_path.endswith('.zip'):
            save_path += '.zip'
            
        try:
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for f in files_to_backup:
                    zipf.write(f, os.path.basename(f))
            return {"success": True, "msg": f"Successfully backed up {len(files_to_backup)} files to {save_path}"}
        except Exception as e:
            return {"success": False, "msg": f"Error creating zip file: {str(e)}"}

    def browse_live_file(self):
        result = window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False, file_types=('JSON Files (*.json)',))
        return result[0] if result else None
    
    def browse_history_folder(self):
        result = window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None
    
    def browse_user_json(self):
        result = window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False, file_types=('JSON Files (*.json)',))
        if result:
            self.last_user_path = result[0]
            return result[0]
        return None

    def get_camo_content(self, user_path):
        self.last_user_path = user_path 
        return process_camo_data(user_json_path=user_path)
    
    def toggle_star(self, w_id):
        try:
            global app_config
            starred = list(app_config.get('starred', []))
            w_id = str(w_id)
            if w_id in starred: starred.remove(w_id)
            else:
                if len(starred) >= 3: return {"success": False, "msg": "Maximum of 3 priority weapons allowed."}
                starred.append(w_id)
            app_config['starred'] = starred
            save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
            return {"success": True, "starred": starred}
        except Exception as e:
            return {"success": False, "msg": f"System Error: {str(e)}"}
        
    def update_camo_progress(self, user_path, weapon_id, new_val):
        if not user_path or not os.path.exists(user_path): return False
        self.last_user_path = user_path
        try:
            data = load_json(user_path)
            if 'progress' not in data: data['progress'] = {}
            data['progress'][str(weapon_id)] = int(new_val)
            return save_json(user_path, data)
        except Exception as e: return False

    def save_config(self, live, hist):
        global app_config
        app_config['live_path'] = live
        app_config['history_path'] = hist
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        t = threading.Timer(0.1, window.load_html, args=(get_main_app_html(),))
        t.start()
        return True
    
    def launch_dashboard(self): return True
    
    def reset_config(self):
        global app_config
        app_config = {}
        save_json(os.path.join(get_base_path(), CONFIG_FILE), {})
        return True
    
    def launch_setup(self):
        t = threading.Timer(0.1, window.load_html, args=(get_setup_html(),))
        t.start()
        return True

    def add_current_best_match(self, target_game_id=None):
        live_path = app_config.get('live_path')
        hist_path = app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path):
            return {"success": False, "msg": "History folder is not configured or available."}

        raw_id = str(target_game_id or "").strip()
        if not raw_id or raw_id == "0":
            if not live_path or not os.path.exists(live_path):
                return {"success": False, "msg": "No displayed match ID is available, and Live Game Path is not configured."}
            live_data = load_json(live_path)
            if not live_data:
                return {"success": False, "msg": "CurrentGame.json could not be read."}
            live_game = live_data.get('game') or live_data.get('data', {}).get('game', {})
            raw_id = str(live_game.get('game_id', '0'))
            if not raw_id or raw_id == "0":
                return {"success": False, "msg": "No active match game ID is available yet."}
        else:
            live_data = None

        safe_id = sanitize_filename(raw_id)
        archive_path = os.path.join(hist_path, f"Game_{safe_id}.json")
        if os.path.exists(archive_path):
            archive_data = load_json(archive_path)
        else:
            archive_data = live_data

        if not archive_data:
            return {"success": False, "msg": f"Could not find archived match for game ID {safe_id}."}

        summary = get_game_summary(archive_data, fallback_id=safe_id)
        summary["id"] = safe_id
        summary["date"] = time.strftime("%b %d, %Y %I:%M %p", time.localtime())
        summary["added_at"] = int(time.time())

        matches = load_best_matches()
        if any(m.get("id") == safe_id for m in matches):
            return {"success": False, "msg": "This match is already saved as a best match."}

        matches.insert(0, summary)
        if save_best_matches(matches):
            return {"success": True, "msg": f"Saved best match: {summary['map']} // Round {summary['round']}", "item": summary}
        return {"success": False, "msg": "Could not save best_matches.json."}

    def get_best_matches(self):
        hist_path = app_config.get('history_path')
        matches = load_best_matches()
        results = []

        for item in matches:
            game_id = str(item.get("id", ""))
            result = dict(item)
            result["exists"] = False

            if hist_path and game_id:
                archive_path = os.path.join(hist_path, f"Game_{game_id}.json")
                if os.path.exists(archive_path):
                    archive_data = load_json(archive_path)
                    if archive_data:
                        fallback_date = result.get("date", "")
                        result = get_game_summary(archive_data, fallback_id=game_id, fallback_date=fallback_date)
                        result["exists"] = True

            result.setdefault("map", "Unknown Map")
            result.setdefault("round", 0)
            result.setdefault("time", "0m 0s")
            result.setdefault("match_xp", 0)
            result.setdefault("date", "")
            result["id"] = game_id
            results.append(result)

        return results

    def remove_best_match(self, game_id):
        safe_id = sanitize_filename(str(game_id or "").strip())
        if not safe_id:
            return {"success": False, "msg": "No game ID was provided."}

        matches = load_best_matches()
        updated = [m for m in matches if str(m.get("id", "")) != safe_id]
        if len(updated) == len(matches):
            return {"success": False, "msg": "That match is not in Best Matches."}

        if save_best_matches(updated):
            return {"success": True, "msg": "Removed best match."}
        return {"success": False, "msg": "Could not update best_matches.json."}
    
    def get_history_list(self, page=1):
        import math
        hist_path = app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path): 
            return {"items": [], "total_pages": 0, "current_page": 1}
            
        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime, reverse=True)
        
        items_per_page = 50
        total_items = len(json_files)
        total_pages = max(1, math.ceil(total_items / items_per_page))
        
        # Ensure page stays within valid bounds
        page = max(1, min(int(page), total_pages))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        
        results = []
        for f in json_files[start_idx:end_idx]: 
            fname = os.path.basename(f)
            gid = fname.replace("Game_", "").replace(".json", "")
            
            mtime = os.path.getmtime(f)
            dt = time.localtime(mtime)
            date_str = time.strftime("%b %d, %Y %I:%M %p", dt) 
            
            map_name = "Unknown Map"
            try:
                with open(f, 'r', encoding='utf-8') as jf:
                    d = json.load(jf)
                    game = d.get('game') or d.get('data', {}).get('game', {})
                    map_val = game.get('map_played')
                    if map_val:
                        map_name = str(map_val).replace('_', ' ').title()
            except: pass
            
            results.append({"id": gid, "map": map_name, "date": date_str})
            
        return {"items": results, "total_pages": total_pages, "current_page": page}
    
    def get_live_stats(self):
        path = app_config.get('live_path')
        if not path or not os.path.exists(path): return None
        data = load_json(path)
        return process_stats(data, is_live=True)

    def get_career_level_info(self):
        live_path = app_config.get('live_path')
        data = None
        if live_path and os.path.exists(live_path):
            data = load_json(live_path)
        if not data:
            hist_path = app_config.get('history_path')
            if hist_path and os.path.exists(hist_path):
                game_files = sorted(
                    [f for f in os.listdir(hist_path) if f.startswith("Game_") and f.endswith(".json")],
                    key=lambda f: os.path.getmtime(os.path.join(hist_path, f)),
                    reverse=True
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
        xp_required = xp_tracker_instance.get_xp_required(level)
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
        if ult > 0: rank_parts.append(f"Ult Tier {ult}")
        if abso > 0: rank_parts.append(f"Abs Tier {abso}")
        if leg > 0: rank_parts.append(f"Leg Tier {leg}")
        if prestige > 0: rank_parts.append(f"Prestige {prestige}")
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
            "workshop_image": get_workshop_image(steam_link) if app_config.get('workshop_images_enabled', True) else None
        }

    def get_history_report(self, game_id):
        hist_path = app_config.get('history_path')
        target = os.path.join(hist_path, "Game_" + game_id + ".json")
        if not os.path.exists(target): return {"status": "ERROR"}
        data = load_json(target)
        return process_stats(data, is_live=False)

    def get_workshop_image(self, steam_link_id):
        if not app_config.get('workshop_images_enabled', True):
            return None
        return get_workshop_image(steam_link_id)

    def toggle_workshop_images(self, enabled):
        global app_config
        app_config['workshop_images_enabled'] = bool(enabled)
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        return True

    def toggle_overlay_system(self, enabled):
        global app_config
        app_config['overlays_enabled'] = enabled
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        t = threading.Thread(target=toggle_overlays_logic, args=(enabled,))
        t.start()
        return True

    def toggle_xp_debugger(self, enabled):
        global app_config
        app_config['xp_debugger_enabled'] = enabled
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        t = threading.Thread(target=toggle_xp_debugger_logic, args=(enabled,))
        t.start()
        return True

    def get_lifetime_stats(self):
        hist_path = app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path): 
            return {"error": "No History Folder Found"}

        totals = {
            "kills": 0, "headshots": 0, "downs": 0, "rounds": 0, 
            "time_sec": 0, "matches": 0, "doors": 0, "gums": 0,
            "box": 0,
            "pts": 0
        }
        weapon_stats = {} 
        map_high_rounds = {}
        map_play_counts = {}
        map_play_times = {}

        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        
        # 1. ADD UP ALL THE HISTORY FIRST
        for f in json_files:
            try:
                data = load_json(f)
                if not data: continue
                
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players: continue
                
                # Career Stats are locked to Player '0' (The Host/Local Player)
                p = list(players.values())[0]

                totals["matches"] += 1
                totals["kills"] += int(p.get('kills', 0))
                totals["headshots"] += int(p.get('headshots', 0))
                totals["downs"] += int(p.get('downs', 0))
                totals["rounds"] += int(game.get('rounds_total', 0))
                totals["time_sec"] += int(game.get('time_total', 0))
                totals["doors"] += int(p.get('doors_purchased', 0))
                totals["gums"] += int(p.get('gobblegums_used', 0))
                
                # Simple Addition of the custom tracked stats
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

                w_data = p.get('weapon_data', p.get('top5', {}))
                for k, w in w_data.items():
                    name = w.get('display', 'Unknown')
                    if name == "none" or name == "Unknown": continue
                    if name not in weapon_stats: weapon_stats[name] = 0
                    weapon_stats[name] += int(w.get('kills', 0))

            except Exception: pass
        
        # --- 2. OVERRIDE SELECTED LOGISTICS WITH LIVE GAME ---
        live_path = app_config.get('live_path')
        if live_path and os.path.exists(live_path):
            try:
                live_data = load_json(live_path)
                if live_data:
                    live_players = live_data.get('players') or live_data.get('data', {}).get('players', {})
                    if live_players:
                        lp = list(live_players.values())[0]
                        
                        # Set to EXACTLY what the current match says (overwriting the history total)
                        totals["doors"] = int(lp.get('doors_purchased', 0))
                        totals["gums"] = int(lp.get('gobblegums_used', 0))
                        totals["pts"] = int(lp.get('player_points_gained', 0))
                        # Notice we leave "box" alone so it keeps the combined history total!
            except Exception:
                pass
        # -----------------------------------------------------

        hs_ratio = 0
        if totals["kills"] > 0:
            hs_ratio = round((totals["headshots"] / totals["kills"]) * 100, 1)

        top_weapons = []
        if weapon_stats:
            sorted_w = sorted(weapon_stats.items(), key=lambda item: item[1], reverse=True)
            # Grab up to the top 3 weapons
            for w_name, w_kills in sorted_w[:3]:
                top_weapons.append({"name": w_name, "kills": w_kills})
                
        if not top_weapons:
            top_weapons = [{"name": "None", "kills": 0}]

        # 1. Calculate KPD
        kpd = totals["kills"]
        if totals["downs"] > 0:
            kpd = round(totals["kills"] / totals["downs"], 2)

        # 2. Map Sorting Logic (Matches)
        sorted_played = sorted(map_play_counts.items(), key=lambda item: item[1], reverse=True)
        # Using 'map_tuple' instead of 'm' so we don't overwrite the minutes variable!
        top_played = [{"name": map_tuple[0], "count": map_tuple[1]} for map_tuple in sorted_played[:15]]
        
        # 3. Map Sorting Logic (Time)
        sorted_played_time = sorted(map_play_times.items(), key=lambda item: item[1], reverse=True)
        top_played_time = []
        for map_tuple in sorted_played_time[:15]:
            map_min, map_sec = divmod(map_tuple[1], 60)
            map_h, map_min = divmod(map_min, 60)
            top_played_time.append({"name": map_tuple[0], "time_str": f"{map_h}h {map_min}m"})

        # 4. Calculate total lifetime hours/minutes (Do this LAST so it's safe)
        total_m, total_s = divmod(totals["time_sec"], 60)
        total_h, total_m = divmod(total_m, 60)

        return {
            "totals": totals,
            "ratios": { "hs_percent": hs_ratio, "kpd": kpd },
            "time_str": f"{total_h}h {total_m}m", 
            "best_map_rounds": map_high_rounds,
            "favorite_weapons": top_weapons,
            "top_played_maps": top_played,
            "top_played_maps_time": top_played_time
        }
    
    def get_challenges(self):
        return challenge_manager.get_frontend_data()

    def set_theme(self, theme_name):
        global app_config
        app_config['active_theme'] = theme_name
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        push_overlay_theme()
        return True

    def get_active_theme(self):
        return app_config.get('active_theme', 'default')
        
    def force_sync_challenges(self):
        hist_path = app_config.get('history_path')
        if hist_path:
            challenge_manager.scan_all_history(hist_path)
            return True
        return False
        
    def get_available_themes(self):
        theme_path = os.path.join(get_base_path(), THEMES_DIR)
        if not os.path.exists(theme_path):
            os.makedirs(theme_path) 
            return []
        
        files = glob.glob(os.path.join(theme_path, "*.css"))
        all_themes = [os.path.basename(f).replace(".css", "") for f in files]
        
        unlocked = challenge_manager.get_unlocked_themes()
        
        valid_themes = []
        if "default" not in unlocked: unlocked.append("default")
        
        for t in all_themes:
            if t in unlocked or t == "default":
                valid_themes.append(t)
                
        return valid_themes

    def get_theme_content(self, theme_name):
        if theme_name == "default": return ""
        
        path = os.path.join(get_base_path(), THEMES_DIR, f"{theme_name}.css")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except: pass
        return ""

    def set_active_theme(self, theme_name):
        global app_config
        app_config['active_theme'] = theme_name
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        push_overlay_theme()
        return True
    
    def reset_challenges_api(self):
        live_path = app_config.get('live_path')
        live_data = None
        if live_path and os.path.exists(live_path):
            try:
                live_data = load_json(live_path)
            except: pass
            
        challenge_manager.reset_all_challenges(live_data)
        return True

    def get_card_image(self, card_name):
        return get_calling_card_src(card_name)

    def get_unlocked_calling_cards(self):
        challenges = challenge_manager.get_frontend_data()
        unlocked_cards = ["default"]
        for c in challenges:
            if c['completed'] and c['reward_type'] == 'calling_card':
                card_name = c['reward_val']
                if card_name not in unlocked_cards:
                    unlocked_cards.append(card_name)
        return unlocked_cards

    def set_active_card(self, card_name):
        global app_config
        app_config['active_card'] = card_name
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        return True

    def get_active_card(self):
        return app_config.get('active_card', 'default')

    def get_top_10_xp_maps(self, player_id="0"):
        import glob
        import os
        
        xp_cache_path = os.path.join(get_base_path(), "match_xp_cache.json")
        xp_data = load_json(xp_cache_path) or {}
        
        hist_path = app_config.get('history_path')
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
            
            # 1. Try to get XP from the live cache first
            if game_id in xp_data and str(player_id) in xp_data[game_id]:
                match_xp = xp_data[game_id][str(player_id)].get('total_match_xp', 0)
            
            # 2. Fallback: If not in cache, check the archived history file directly!
            elif str(player_id) in players:
                p_data = players[str(player_id)]
                # Safely get the match_xp_earned if it exists in the archive
                match_xp = int(p_data.get('match_xp_earned', 0))

            # 3. Only track maps where XP is greater than 0
            if match_xp > 0:
                if map_name not in map_highest_xp or match_xp > map_highest_xp[map_name]:
                    map_highest_xp[map_name] = match_xp

        # Sort and return the top 10
        sorted_maps = sorted(map_highest_xp.items(), key=lambda x: x[1], reverse=True)
        return [{"map": m[0], "xp": m[1]} for m in sorted_maps[:10]]
        
        # Add this new method to your API class
    def get_xp_per_round_graph(self, game_id, player_id):
        # Fetch the live history for the specific player and game
        history = xpm_grapher_instance.live_history.get(str(game_id), {}).get(str(player_id), {})
        
        # Use our new method to generate the dataset
        return xpm_grapher_instance.generate_xp_per_round_data(history)

# --- LIVE BACKGROUND LOGIC (MULTI-PLAYER) ---
def monitor_game():
    last_saved_data_str = ""  
    last_game_id = None
    known_active_perks = {} 
    session_perk_count = {} 
    
    # Simple live trackers
    session_match_pts = {}
    session_last_raw_pts = {}
    
    session_match_box = {}
    session_last_raw_box = {}

    while True:
        live_path = app_config.get('live_path')
        hist_path = app_config.get('history_path')
        
        if not live_path or not hist_path: 
            time.sleep(5)
            continue
            
        try:
            if os.path.exists(live_path):
                current_data = load_json(live_path)
                
                if current_data:
                    game = current_data.get('game') or current_data.get('data', {}).get('game', {})
                    raw_id = str(game.get('game_id', '0'))
                    
                    if raw_id and raw_id != "0":
                        if raw_id != last_game_id:
                            last_game_id = raw_id
                            known_active_perks = {}
                            session_perk_count = {}
                            
                            # Reset our live tracker when a completely new game starts
                            session_match_pts = {}
                            session_last_raw_pts = {}
                            session_match_box = {}
                            session_last_raw_box = {}
                        
                        players = current_data.get('players') or current_data.get('data', {}).get('players', {})
                        if players:
                            for pid, p in players.items():
                                # --- 1. PERK LOGIC ---
                                if pid not in known_active_perks:
                                    known_active_perks[pid] = set()
                                    session_perk_count[pid] = 0

                                raw_perks = p.get('perks', [])
                                if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
                                current_perks_set = set([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
                                new_perks = current_perks_set - known_active_perks[pid]
                                if new_perks: session_perk_count[pid] += len(new_perks)
                                if len(current_perks_set) < len(known_active_perks[pid]): known_active_perks[pid] = current_perks_set
                                p['calculated_perks_drank'] = session_perk_count[pid]
                                
                                # --- 2. SIMPLE DROP-DETECTION TRACKER ---
                                current_raw_pts = int(p.get('player_points_gained', 0))
                                current_raw_box = int(p.get('mystery_box_used', 0))
                                
                                if pid not in session_match_pts:
                                    # Initialize with the very first reading of the match
                                    session_match_pts[pid] = current_raw_pts
                                    session_last_raw_pts[pid] = current_raw_pts
                                    
                                    session_match_box[pid] = current_raw_box
                                    session_last_raw_box[pid] = current_raw_box
                                
                                # Points Math
                                last_raw_pts = session_last_raw_pts[pid]
                                if current_raw_pts > last_raw_pts:
                                    session_match_pts[pid] += (current_raw_pts - last_raw_pts)
                                elif current_raw_pts < last_raw_pts:
                                    # DROP DETECTED! Just add the new points.
                                    session_match_pts[pid] += current_raw_pts 
                                session_last_raw_pts[pid] = current_raw_pts
                                
                                # Box Math
                                last_raw_box = session_last_raw_box[pid]
                                if current_raw_box > last_raw_box:
                                    session_match_box[pid] += (current_raw_box - last_raw_box)
                                elif current_raw_box < last_raw_box:
                                    # DROP DETECTED!
                                    session_match_box[pid] += current_raw_box
                                session_last_raw_box[pid] = current_raw_box
                                
                                # Save the clean values
                                p['true_match_points'] = session_match_pts[pid]
                                p['true_match_box'] = session_match_box[pid]

                        # --- SAVE LOGIC ---
                        current_data_str = json.dumps(current_data, sort_keys=True)
                        if current_data_str != last_saved_data_str:
                            safe_id = sanitize_filename(raw_id)
                            if os.path.exists(hist_path):
                                target_file = os.path.join(hist_path, f"Game_{safe_id}.json")
                                
                                game_info = current_data.get('game') or current_data.get('data', {}).get('game', {})
                                g_id = str(game_info.get('game_id', 'unknown'))
                                p_dict = current_data.get('players') or current_data.get('data', {}).get('players', {})
                                
                                for pid_key, p_data in p_dict.items():
                                    p_prest = int(p_data.get('prestige', 0))
                                    p_lvl = int(p_data.get('level', 1))
                                    p_xp = int(p_data.get('xp', p_data.get('total_xp', 0)))
                                    p_data['match_xp_earned'] = xp_tracker_instance.calculate_match_xp(g_id, pid_key, p_prest, p_lvl, p_xp)
                                    # --- NEW: UPDATE & INJECT XPM HISTORY ---
                                    current_round = int(game_info.get('rounds_total', 0))
                                    current_time = int(game_info.get('time_total', 0))
                                    try:
                                        current_zpm = float(game_info.get('zpm', 0))
                                    except:
                                        current_zpm = 0
                                    map_name = game_info.get('map_played', 'Unknown')
                                    xp_debug_snapshot = xp_tracker_instance.get_last_debug_snapshot(g_id, pid_key)
                                    record_xp_debug(xp_debug_snapshot, current_round, current_time, map_name)
                                    p_data['round_history'] = xpm_grapher_instance.update_live_data(
                                        g_id, pid_key, current_round, current_time, p_data['match_xp_earned'], current_zpm
                                    )
                                
                                if save_json(target_file, current_data):
                                    last_saved_data_str = current_data_str
                                    challenge_manager.process_update(hist_path)
        except Exception:
            pass
        
        time.sleep(2)

def get_entry_point_html():
    if not app_config or not app_config.get('live_path'):
        return get_setup_html()
    return get_main_app_html()

def on_closed():
    toggle_overlays_logic(False)
    toggle_xp_debugger_logic(False)
    os._exit(0)

def startup_checks():
    if app_config.get('overlays_enabled', False):
        toggle_overlays_logic(True)
    if app_config.get('xp_debugger_enabled', False):
        toggle_xp_debugger_logic(True)

if __name__ == "__main__":
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    if os.path.exists(config_path):
        app_config = load_json(config_path) or {}
    
    t = threading.Thread(target=monitor_game)
    t.daemon = True
    t.start()
    
    api = TrackerAPI()
    window = webview.create_window('BO3 Tracker & Camo Matrix', html=get_entry_point_html(), width=1300, height=900, background_color='#0b0c10', js_api=api)
    
    window.events.closed += on_closed
    webview.start(func=startup_checks)
