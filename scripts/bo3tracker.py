import os
import json
import glob
import time
import base64
import threading
import webview # pip install pywebview
import sys
from pathlib import Path

# --- NEW IMPORT ---
from challenge_system import ChallengeManager

# --- CONSTANTS ---
CONFIG_FILE = "config.json"
DAMAGE_HISTORY_FILE = "damage_history.json"
ICONS_DIR_NAME = "perk icons" 
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

# --- GLOBAL STATE ---
app_config = {}
window = None
# -- OVERLAY GLOBALS --
unified_window = None
stop_overlays = False
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
    
def get_classic_mode_icon():
    path = os.path.join(get_base_path(), "trackericons", "classic_zombie.webp")
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/webp;base64,{b64}"
        except: pass
    return ""

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
    # UPDATED: Check for Video formats first
    for ext in [".mp4", ".webm", ".jpg", ".png", ".webp"]:
        img_name = f"{card_name}{ext}"
        target = os.path.join(base_dir, CALLING_CARD_DIR, img_name)
        if os.path.exists(target):
            try:
                with open(target, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                    # Determine Mime Type
                    mime = ""
                    if ext == ".mp4": mime = "video/mp4"
                    elif ext == ".webm": mime = "video/webm"
                    elif ext == ".jpg": mime = "image/jpeg"
                    else: mime = f"image/{ext[1:]}"
                    
                    return f"data:{mime};base64,{b64}"
            except: pass
    return None

# --- DAMAGE MEMORY SYSTEM ---
class DamageMemory:
    def __init__(self):
        self.file_path = os.path.join(get_base_path(), DAMAGE_HISTORY_FILE)
        self.cache = self._load_from_disk()
        self.lock = threading.Lock()

    def _load_from_disk(self):
        return load_json(self.file_path) or {}

    def _save_to_disk(self):
        save_json(self.file_path, self.cache)

    def get_real_damage(self, game_id, weapon_name, current_raw_val):
        with self.lock:
            if game_id not in self.cache:
                self.cache[game_id] = {}

            if weapon_name not in self.cache[game_id]:
                self.cache[game_id][weapon_name] = {
                    "last_seen": 0,
                    "overflow_offset": 0
                }

            w_data = self.cache[game_id][weapon_name]
            last_val = w_data["last_seen"]
            offset = w_data["overflow_offset"]
            
            if current_raw_val < last_val:
                if (last_val - current_raw_val) > 100000:
                    offset += 4294967296
                    w_data["overflow_offset"] = offset
                    self._save_to_disk() 

            w_data["last_seen"] = current_raw_val
            self.cache[game_id][weapon_name] = w_data
            return current_raw_val + offset

# Initialize Systems
damage_tracker = DamageMemory()
challenge_manager = ChallengeManager(get_base_path()) 

# --- DATA PROCESSOR (GAME STATS) ---
def process_stats(data, is_live=False):
    if not data: return None
    
    game = data.get('game') or data.get('data', {}).get('game', {})
    players = data.get('players') or data.get('data', {}).get('players', {})
    game_id = str(game.get('game_id', 'unknown_match'))
    
    if not players: p = {} 
    else: p = list(players.values())[0]

    time_sec = int(game.get('time_total', 0))
    mins, secs = divmod(time_sec, 60)
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

    # Determine Main Title
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
    status_text = "LIVE FEED" if is_live else f"ARCHIVED: {game.get('game_id')}"
    status_color = "#66fcf1" if is_live else "#444" 

    nerf_html = ""
    if str(game.get('nerfed')) == "1":
        reason = str(game.get('nerfed_reason', '')).replace('|', ' ')
        nerf_html = f"<div class='nerf-box'>⚠ ACTIVE MODIFIERS: {reason}</div>"

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
        
        try: raw_damage = int(float(w.get('damage', 0)))
        except: raw_damage = 0
            
        corrected_damage = damage_tracker.get_real_damage(game_id, dname, raw_damage)
        
        processed_weapons.append({
            "name": dname,
            "kills": kills_w,
            "damage_val": corrected_damage, 
            "damage_str": "{:,}".format(corrected_damage),
            "status": status_html
        })

    processed_weapons.sort(key=lambda x: x['damage_val'], reverse=True)

    for pw in processed_weapons:
        weapons_html += f"<tr><td>{pw['name']}</td><td>{pw['kills']}</td><td>{pw['damage_str']}</td><td>{pw['status']}</td></tr>"

    equip = p.get('equipment', {})
    lethal = equip.get('lethal', {}).get('name', 'None').replace('_', ' ').title()
    tactical = equip.get('tactical', {}).get('name', 'None').replace('_', ' ').title()

    return {
        "status": status_text, "color": status_color, "nerf": nerf_html,
        "map": str(game.get('map_played', 'Unknown')).replace('_',' ').title(), 
        "round": game.get('rounds_total', 0),
        "time": "{:02d}:{:02d}".format(mins, secs), "mode": game.get('gamemode', 'Standard'),
        "r_main": rank_main, "title": player_title, "r_sub": rank_sub, "gums": p.get('gobblegums_used', 0),
        "xp": "{:,}".format(xp_val), "mult": xp_mult,
        "k": kills, "pts": "{:,}".format(int(p.get('points', 0))), "acc": accuracy,
        "melee": p.get('melee_kills', 0), "equip": p.get('equipment_kills', 0), "downs": p.get('downs', 0),
        "perks": perks_html, "perk_count": valid_perk_count, "leth": lethal, "tact": tactical, "weaps": weapons_html
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
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            html, body {
                margin: 0; padding: 0; overflow: hidden;
                background-color: #0b0c10 !important;
            }
            #unified-box {
                display: inline-flex; flex-direction: column;
                background: #0b0c10; border: 2px solid #66fcf1;
                padding: 12px; box-sizing: border-box;
                font-family: 'Segoe UI', sans-serif; color: #fff;
                width: 100%; height: 100%;
            }
            #perk-area {
                display: flex; flex-wrap: wrap; justify-content: center;
                gap: 5px; margin-bottom: 10px; min-height: 45px;
            }
            .perk-item img { width: 40px; height: 40px; object-fit: contain; filter: drop-shadow(0 0 2px rgba(0,0,0,0.5)); }
            .perk-fallback {
                width: 40px; height: 40px; background: #333; color: #fff; 
                display: flex; align-items: center; justify-content: center; font-size: 10px; 
                border-radius: 50%; border: 1px solid #666;
            }
            #damage-area { border-top: 1px solid #333; padding-top: 8px; }
            .title { font-size: 10px; color: #66fcf1; margin-bottom: 5px; letter-spacing: 1px; font-weight: bold; text-transform: uppercase; }
            .row { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; }
            .name { font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 120px; }
            .dmg { color: #ff9d00; font-weight: bold; margin-left: 10px; }
        </style>
    </head>
    <body>
        <div id="unified-box">
            <div id="perk-area"></div>
            <div id="damage-area">
                <div class="title">Top Weapon Damage</div>
                <div id="damage-list"></div>
            </div>
        </div>
        <script>
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
                    
                    if stats:
                        game = data.get('game') or data.get('data', {}).get('game', {})
                        game_id = str(game.get('game_id', 'unknown'))
                        players = data.get('players') or data.get('data', {}).get('players', {})
                        top_3_weapons = []
                        
                        if players:
                            p = list(players.values())[0]
                            weapons = p.get('top5', p.get('weapon_data', {}))
                            processed = []
                            for k, w in weapons.items():
                                if w.get('display') == 'none': continue
                                dname = str(w.get('display', 'Unknown'))
                                try: raw_dmg = int(float(w.get('damage', 0)))
                                except: raw_dmg = 0
                                real_dmg = damage_tracker.get_real_damage(game_id, dname, raw_dmg)
                                processed.append({
                                    "name": dname,
                                    "kills": str(w.get('kills', 0)),
                                    "damage": real_dmg,
                                    "damage_str": "{:,}".format(real_dmg)
                                })
                            processed.sort(key=lambda x: x['damage'], reverse=True)
                            top_3_weapons = processed[:3]

                        json_dmg = json.dumps(top_3_weapons)
                        unified_window.evaluate_js(f'updateOverlay(`{stats["perks"]}`, {json_dmg})')
                        
                        import math
                        perk_count = stats.get('perk_count', 0)
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
    classic_icon_src = get_classic_mode_icon() 
    
    overlays_on = app_config.get('overlays_enabled', False)
    chk_str = "checked" if overlays_on else ""

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style id="theme-injector"></style>
        <style>""" + css_content + """
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
            <div class="nav-btn" id="chal-btn" onclick="switchTab('challenges')">CHALLENGES</div>
            <div style="padding:20px; color:#555; font-size:0.7em; font-weight:bold; letter-spacing:1px; margin-top:10px;">MATCH LOGS</div>
            <div class="list" id="history-list"></div>
            <div class="config-btn" onclick="switchTab('help')">HELP & FAQ</div>
            <div class="config-btn" onclick="switchTab('settings')">SETTINGS</div>
        </div>
        
        <div class="main-view">
            <div id="tab-live" class="tab-content active">
                <div id="d_status_bar" class="status-bar">CONNECTING...</div>
                <div id="d_nerf"></div>
               
                <div class="card" style="position: relative;">
                    <img id="classic_badge" src=\"""" + classic_icon_src + """\" alt="Classic" style="display: none;">
                    <div class="card-title">CURRENT MISSION</div>
                    <div class="stat-grid-2">
                        <div>
                            <div id="d_map" class="stat-big" style="font-size: 2em;">-</div>
                            <div class="stat-sub">ROUND <span id="d_round" style="color:#fff; font-weight:bold;">0</span></div>
                        </div>
                        <div style="text-align:right;">
                             <div class="detail-row"><span>TIME</span><span id="d_time">00:00</span></div>
                             <div class="detail-row"><span>MODE</span><span id="d_mode">-</span></div>
                        </div>
                    </div>
                </div>

                <div class="stat-grid-2">
                    <div class="card">
                        <div class="card-title">SERVICE RECORD</div>
                        <div id="d_rmain" class="stat-rank">-</div>
                        <div id="d_title" style="color:#aaa; font-style:italic; font-size:0.9em; margin-bottom:5px;">-</div>
                        <div id="d_rsub" style="color:#888; font-size:0.8em;">-</div>
                        <div style="margin-top:15px;">
                            <div class="detail-row"><span>XP EARNED</span><span id="d_xp">0</span></div>
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
                        <thead><tr><th>WEAPON</th><th>KILLS</th><th>DAMAGE</th><th>STATUS</th></tr></thead>
                        <tbody id="d_weaps"></tbody>
                    </table>
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
                    <div style="font-size:0.8em; color:#777;">LIFETIME STATISTICS</div>
                </div>

                <div class="stat-grid-2">
                    <div class="card">
                        <div class="card-title">COMBAT RECORD</div>
                        <div class="detail-row"><span>TOTAL KILLS</span><span id="life_kills" style="color:var(--highlight); font-size:1.2em;">0</span></div>
                        <div class="detail-row"><span>HEADSHOTS</span><span id="life_headshots">0</span></div>
                        <div class="detail-row"><span>PRECISION</span><span id="life_hs_pct" style="color:#ff9d00">0%</span></div>
                        <div style="margin-top:10px; border-top:1px solid #333; padding-top:5px;">
                             <div class="detail-row"><span>FAVORITE WEAPON</span><span id="life_fav_gun" style="text-align:right">None</span></div>
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
                    </div>
                     <div class="card">
                        <div class="card-title">PERSONAL BESTS (ROUNDS)</div>
                        <div id="life_map_list" style="max-height:150px; overflow-y:auto; font-size:0.8em; color:#aaa;">
                            </div>
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
                    <div class="card-title">DATA MANAGEMENT</div>
                    <button class="nav-btn-small" style="background: var(--danger); width:100%;" onclick="reconfigure()">RESET FILE PATHS</button>
                    <p style="color:#777; font-size:0.8em; margin-top:10px;">Use this if you moved your game installation or history folder.</p>
                </div>
            </div>

            <div id="tab-help" class="tab-content">
                <div style="max-width:800px; margin:0 auto;">
                    <h1 style="color:var(--highlight); border-bottom:1px solid #333; padding-bottom:15px;">OPERATIONAL GUIDE</h1>

                    <div class="card">
                        <div class="card-title">OVERLAY CONTROL</div>
                        <div style="display:flex; justify-content:space-between; align-items:center;">
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
                            <li><b>Higher Visble Gun Damage:</b> The tracker automatically trys to work out how much damage you are doing once the game cap is reached using the data of damage each round. This is a test function
                            and might be removed as it is a lot of damage I cannot gaurantee that it will be correct as there are lost of factors to take into account.</li>
                            <li><b>Camo Tracker:</b> Built in camo tracker for come custom maps.</li>
                         </ul>
                    </div>
                </div>
            </div>

        </div>
        
        <input type="hidden" id="current-user-path" value="">

        <script>
            let isLive = true;
            let lastRound = 0;
            let GLOBAL_NAMES = [];
            let GLOBAL_MAPS = {};
            let MAP_KEYS = [];
            let currentMapIndex = 0;
            let currentStarredWeapons = [];
            let currentChalFilter = 'operations';

            function toggleOverlays(checkbox) {
                window.pywebview.api.toggle_overlay_system(checkbox.checked);
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
                } else if(tabName === 'camo') {
                    isLive = false;
                    document.getElementById('camo-btn').classList.add('active');
                } else if(tabName === 'career') {
                    isLive = false;
                    document.getElementById('career-btn').classList.add('active');
                    loadCareerData();
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

            // HELPER: Handles Displaying Image OR Video
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
                alert("Theme Applied: " + themeName);
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
                        c.id.startsWith('c_gold') || c.id.startsWith('c_retro') || c.id.startsWith('c_mat')) {
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
            
            async function loadCareerData() {
                const activeCard = await window.pywebview.api.get_active_card();
                if(activeCard && activeCard !== 'default') {
                    const src = await window.pywebview.api.get_card_image(activeCard);
                    showMedia(src, 'card-display', 'card-display-video');
                } else {
                    showMedia(null, 'card-display', 'card-display-video');
                }

                try {
                    const data = await window.pywebview.api.get_lifetime_stats();
                    if(data && !data.error) {
                        document.getElementById('life_kills').innerText = parseInt(data.totals.kills).toLocaleString();
                        document.getElementById('life_headshots').innerText = parseInt(data.totals.headshots).toLocaleString();
                        document.getElementById('life_hs_pct').innerText = data.ratios.hs_percent + "%";
                        document.getElementById('life_fav_gun').innerText = data.favorite_weapon.name + " (" + data.favorite_weapon.kills + ")";
                        
                        document.getElementById('life_rounds').innerText = parseInt(data.totals.rounds).toLocaleString();
                        document.getElementById('life_time').innerText = data.time_str;
                        document.getElementById('life_matches').innerText = data.totals.matches;
                        document.getElementById('life_kpd').innerText = data.ratios.kpd;
                        
                        document.getElementById('life_doors').innerText = parseInt(data.totals.doors).toLocaleString();
                        document.getElementById('life_gums').innerText = parseInt(data.totals.gums).toLocaleString();
                        
                        let mapHtml = "";
                        for (const [map, rnd] of Object.entries(data.best_map_rounds)) {
                            mapHtml += `<div style="display:flex; justify-content:space-between; border-bottom:1px solid #333; padding:2px 0;"><span>${map}</span><span style="color:#fff">${rnd}</span></div>`;
                        }
                        document.getElementById('life_map_list').innerHTML = mapHtml;
                    }
                } catch(e) { console.error("Career Load Error", e); }
            }
            
            async function init() {
                updateSidebar();
                switchTab('live');
                
                await window.pywebview.api.force_sync_challenges();
                
                const savedTheme = await window.pywebview.api.get_active_theme();
                if (savedTheme && savedTheme !== 'default') {
                    const css = await window.pywebview.api.get_theme_content(savedTheme);
                    document.getElementById('theme-injector').innerHTML = css;
                }
                
                setInterval(async () => {
                    if (isLive) {
                        try {
                            const data = await window.pywebview.api.get_live_stats();
                            if (isLive) updateData(data); 
                        } catch(e) {}
                    }
                    updateSidebar();
                    
                    // Update challenges if visible
                    const chalTab = document.getElementById('tab-challenges');
                    if (chalTab && chalTab.classList.contains('active')) {
                        loadChallenges();
                    }
                }, 3000);
            }
            
            function updateData(d) {
                if(!d) return;

                const currentRound = parseInt(d.round);
                if (currentRound > lastRound && lastRound !== 0) {
                    if (currentRound % 5 === 0) {
                        triggerMilestoneAnim(currentRound);
                    }
                }
                lastRound = currentRound;

                document.getElementById('d_status_bar').innerText = d.status;
                document.getElementById('d_status_bar').style.borderLeftColor = d.color;
                document.getElementById('d_map').innerText = d.map;
                document.getElementById('d_round').innerText = d.round;
                document.getElementById('d_time').innerText = d.time;
                document.getElementById('d_mode').innerText = d.mode;
                const badge = document.getElementById('classic_badge');
                if (d.mode && d.mode.toLowerCase().includes('classic')) {
                    badge.style.display = 'block';
                } else {
                    badge.style.display = 'none';
                }
                document.getElementById('d_rmain').innerText = d.r_main;
                document.getElementById('d_title').innerText = d.title;
                document.getElementById('d_rsub').innerText = d.r_sub;
                document.getElementById('d_gums').innerText = d.gums;
                document.getElementById('d_xp').innerText = d.xp;
                document.getElementById('d_mult').innerText = d.mult;
                document.getElementById('d_kills').innerText = d.k;
                document.getElementById('d_score').innerText = d.pts;
                document.getElementById('d_acc').innerText = d.acc;
                document.getElementById('d_melee').innerText = d.melee;
                document.getElementById('d_equip').innerText = d.equip;
                document.getElementById('d_downs').innerText = d.downs;
                document.getElementById('d_leth').innerText = d.leth;
                document.getElementById('d_tact').innerText = d.tact;
                document.getElementById('d_nerf').innerHTML = d.nerf;
                document.getElementById('d_perks').innerHTML = d.perks;
                document.getElementById('d_weaps').innerHTML = d.weaps;
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
                    const newHistory = await window.pywebview.api.get_history_list();
                    const listEl = document.getElementById('history-list');
                    if (newHistory.length !== listEl.children.length) {
                        listEl.innerHTML = "";
                        newHistory.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'sb-item';
                            div.innerText = item.label;
                            div.onclick = () => loadHistory(item.id, div);
                            listEl.appendChild(div);
                        });
                    }
                } catch(e) {}
            }
            
            async function loadHistory(id, el) {
                switchTab('live'); 
                isLive = false; 
                document.querySelectorAll('.sb-item').forEach(i => i.classList.remove('active'));
                el.classList.add('active');
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
    
    def get_history_list(self):
        hist_path = app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path): return []
        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime, reverse=True)
        results = []
        for f in json_files[:50]: 
            fname = os.path.basename(f)
            gid = fname.replace("Game_", "").replace(".json", "")
            label = f"Match {gid[:8]}..." 
            try:
                with open(f, 'r', encoding='utf-8') as jf:
                    d = json.load(jf)
                    game = d.get('game') or d.get('data', {}).get('game', {})
                    map_val = game.get('map_played')
                    if map_val:
                        clean_map = str(map_val).replace('_', ' ').title()
                        label = f"{clean_map} - {gid[:6]}.."
            except: pass
            results.append({"id": gid, "label": label})
        return results
    
    def get_live_stats(self):
        path = app_config.get('live_path')
        if not path or not os.path.exists(path): return None
        data = load_json(path)
        return process_stats(data, is_live=True)

    def get_history_report(self, game_id):
        hist_path = app_config.get('history_path')
        target = os.path.join(hist_path, "Game_" + game_id + ".json")
        if not os.path.exists(target): return {"status": "ERROR"}
        data = load_json(target)
        return process_stats(data, is_live=False)

    def toggle_overlay_system(self, enabled):
        global app_config
        app_config['overlays_enabled'] = enabled
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
        t = threading.Thread(target=toggle_overlays_logic, args=(enabled,))
        t.start()
        return True

    def get_lifetime_stats(self):
        hist_path = app_config.get('history_path')
        if not hist_path or not os.path.exists(hist_path): 
            return {"error": "No History Folder Found"}

        totals = {
            "kills": 0, "headshots": 0, "downs": 0, "rounds": 0, 
            "time_sec": 0, "matches": 0, "doors": 0, "gums": 0
        }
        weapon_stats = {} 
        map_high_rounds = {} 

        json_files = glob.glob(os.path.join(hist_path, "Game_*.json"))
        
        for f in json_files:
            try:
                data = load_json(f)
                if not data: continue
                
                game = data.get('game') or data.get('data', {}).get('game', {})
                players = data.get('players') or data.get('data', {}).get('players', {})
                if not players: continue
                
                p = list(players.values())[0]

                totals["matches"] += 1
                totals["kills"] += int(p.get('kills', 0))
                totals["headshots"] += int(p.get('headshots', 0))
                totals["downs"] += int(p.get('downs', 0))
                totals["rounds"] += int(game.get('rounds_total', 0))
                totals["time_sec"] += int(game.get('time_total', 0))
                totals["doors"] += int(p.get('doors_purchased', 0))
                totals["gums"] += int(p.get('gobblegums_used', 0))

                map_name = str(game.get('map_played', 'Unknown')).replace('_', ' ').title()
                rnd = int(game.get('rounds_total', 0))
                if map_name not in map_high_rounds or rnd > map_high_rounds[map_name]:
                    map_high_rounds[map_name] = rnd

                w_data = p.get('weapon_data', p.get('top5', {}))
                for k, w in w_data.items():
                    name = w.get('display', 'Unknown')
                    if name == "none" or name == "Unknown": continue
                    if name not in weapon_stats: weapon_stats[name] = 0
                    weapon_stats[name] += int(w.get('kills', 0))

            except Exception: pass

        hs_ratio = 0
        if totals["kills"] > 0:
            hs_ratio = round((totals["headshots"] / totals["kills"]) * 100, 1)

        fav_weapon = "N/A"
        fav_weapon_kills = 0
        if weapon_stats:
            sorted_w = sorted(weapon_stats.items(), key=lambda item: item[1], reverse=True)
            if sorted_w:
                fav_weapon = sorted_w[0][0]
                fav_weapon_kills = sorted_w[0][1]

        m, s = divmod(totals["time_sec"], 60)
        h, m = divmod(m, 60)
        
        kpd = totals["kills"]
        if totals["downs"] > 0:
            kpd = round(totals["kills"] / totals["downs"], 2)

        return {
            "totals": totals,
            "ratios": { "hs_percent": hs_ratio, "kpd": kpd },
            "time_str": f"{h}h {m}m",
            "best_map_rounds": map_high_rounds,
            "favorite_weapon": {"name": fav_weapon, "kills": fav_weapon_kills}
        }
    
    # --- NEW: CHALLENGE API METHODS ---
    def get_challenges(self):
        return challenge_manager.get_frontend_data()

    def set_theme(self, theme_name):
        global app_config
        app_config['active_theme'] = theme_name
        save_json(os.path.join(get_base_path(), CONFIG_FILE), app_config)
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
        return True
    
    def reset_challenges_api(self):
        challenge_manager.reset_all_challenges()
        return True

    def get_card_image(self, card_name):
        return get_calling_card_src(card_name)

    # --- CALLING CARD METHODS ---
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

# --- LIVE BACKGROUND LOGIC ---
def monitor_game():
    last_saved_data_str = ""  
    last_game_id = None
    known_active_perks = set()
    session_perk_count = 0

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
                        # Detect New Game
                        if raw_id != last_game_id:
                            last_game_id = raw_id
                            known_active_perks = set()
                            session_perk_count = 0
                        
                        # Live Perk Tracking
                        players = current_data.get('players') or current_data.get('data', {}).get('players', {})
                        if players:
                            p = list(players.values())[0]
                            raw_perks = p.get('perks', [])
                            if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
                            
                            # Filter valid perks
                            current_perks_set = set([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
                            
                            # Find newly bought perks
                            new_perks = current_perks_set - known_active_perks
                            if new_perks:
                                session_perk_count += len(new_perks)
                                known_active_perks = current_perks_set
                            
                            # If perks lost (downed), known_active_perks must update to reflect current state
                            # so re-buying counts again.
                            if len(current_perks_set) < len(known_active_perks):
                                known_active_perks = current_perks_set

                        # Inject Calculated Value
                        current_data['calculated_perks_drank'] = session_perk_count

                        # Save Logic
                        current_data_str = json.dumps(current_data, sort_keys=True)
                        if current_data_str != last_saved_data_str:
                            safe_id = sanitize_filename(raw_id)
                            if os.path.exists(hist_path):
                                target_file = os.path.join(hist_path, f"Game_{safe_id}.json")
                                if save_json(target_file, current_data):
                                    last_saved_data_str = current_data_str
                                    # Call the robust update method
                                    challenge_manager.process_update(hist_path)
        except Exception:
            pass
        
        # Faster loop for live tracking (2s)
        time.sleep(2)

def get_entry_point_html():
    if not app_config or not app_config.get('live_path'):
        return get_setup_html()
    return get_main_app_html()

def on_closed():
    toggle_overlays_logic(False)
    os._exit(0)

def startup_checks():
    if app_config.get('overlays_enabled', False):
        toggle_overlays_logic(True)

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
    webview.start(func=startup_checks, gui='edgechromium')