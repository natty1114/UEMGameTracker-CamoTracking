import os
import json
import glob
import time
import base64
import threading
import webview # pip install pywebview
import sys
from pathlib import Path

# --- CONSTANTS ---
CONFIG_FILE = "config.json"
DAMAGE_HISTORY_FILE = "damage_history.json" # New persistent storage file
ICONS_DIR_NAME = "perk icons" 
CAMO_DB_FILE = "custom_camos.json"
CAMO_IMG_DIR = "camoimages"
CSS_MAIN_FILE = "style.css"
CSS_SETUP_FILE = "setup.css"

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

# --- NEW: DAMAGE MEMORY SYSTEM ---
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
        """
        Calculates true damage by detecting 32-bit integer overflows.
        Uses RAM for speed, but saves to disk when an overflow is detected.
        """
        with self.lock:
            # Initialize game entry if missing
            if game_id not in self.cache:
                self.cache[game_id] = {}

            # Initialize weapon entry if missing
            if weapon_name not in self.cache[game_id]:
                self.cache[game_id][weapon_name] = {
                    "last_seen": 0,
                    "overflow_offset": 0
                }

            w_data = self.cache[game_id][weapon_name]
            last_val = w_data["last_seen"]
            offset = w_data["overflow_offset"]
            
            # --- OVERFLOW LOGIC ---
            # If the value drops significantly (e.g., from positive to negative),
            # we assume a 32-bit signed wrap-around occurred.
            # 2^32 = 4,294,967,296
            
            if current_raw_val < last_val:
                # If the drop is huge (more than 100k difference), assume overflow
                if (last_val - current_raw_val) > 100000:
                    offset += 4294967296
                    w_data["overflow_offset"] = offset
                    self._save_to_disk() # Critical: Persist immediately on overflow

            w_data["last_seen"] = current_raw_val
            
            # Always update RAM cache
            self.cache[game_id][weapon_name] = w_data
            
            # Calculate final number
            return current_raw_val + offset

# Initialize the damage memory system
damage_tracker = DamageMemory()

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

    # Determine Main Title (Highest Rank)
    if ult > 0: rank_main = "ULTIMATE PRESTIGE"
    elif abso > 0: rank_main = "ABSOLUTE PRESTIGE"
    elif leg > 0: rank_main = "PRESTIGE LEGEND"
    elif prest > 0: rank_main = f"PRESTIGE {prest}"
    else: rank_main = "RECRUIT"

    # Build Sub-line with ALL active ranks in specific order
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
    if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
    for perk in raw_perks:
        if any(x in perk.lower() for x in IGNORE_KEYWORDS): continue
        pretty = PERK_NAMES.get(perk, perk.replace('specialty_', '').replace('_', ' ').title())
        if "null" in pretty.lower(): continue
        icon = get_base_path() + perk 
        icon_b64 = get_base64_icon(perk)
        if icon_b64: perks_html += f'<div class="perk-item"><img src="{icon_b64}" class="perk-img" title="{pretty}"></div>'
        else: perks_html += f'<div class="perk-item"><div class="perk-fallback" style="font-size:0.5em; text-align:center;">{pretty[:3]}</div></div>'
    if not perks_html: perks_html = "<span style='color:#555; font-style:italic;'>No Active Perks</span>"

    weapons_html = ""
    weapons = p.get('top5', p.get('weapon_data', {}))
    for k, w in weapons.items():
        if w.get('display') == 'none': continue
        is_pap = (int(w.get('repack_level', 0)) > 0) or (w.get('display_name_upgraded') and w.get('display_name_upgraded') != "none")
        status = '<span style="color:#66fcf1; font-weight:bold;">PAP</span>' if is_pap else '<span style="color:#888">STD</span>'
        dname = str(w.get('display', 'Unknown'))
        kills_w = str(w.get('kills', 0))
        
        # --- FIXED DAMAGE DISPLAY ---
        try:
            # We use float() first because the game might send "1.71e+09" as a string
            # int("1.71e+09") crashes, but int(float("1.71e+09")) works perfectly.
            raw_damage = int(float(w.get('damage', 0)))
        except:
            raw_damage = 0
            
        # This calls our new system to fix the number if it's broken/overflowed
        corrected_damage = damage_tracker.get_real_damage(game_id, dname, raw_damage)
        dmg_w = "{:,}".format(corrected_damage)
        # ----------------------------

        weapons_html += f"<tr><td>{dname}</td><td>{kills_w}</td><td>{dmg_w}</td><td>{status}</td></tr>"

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
        "perks": perks_html, "leth": lethal, "tact": tactical, "weaps": weapons_html
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

# --- UNIFIED DASHBOARD HTML ---
def get_main_app_html():
    css_content = load_css(CSS_MAIN_FILE)
    classic_icon_src = get_classic_mode_icon() 

    return """
    <!DOCTYPE html>
    <html>
    <head>
        <style>""" + css_content + """</style>
        <style id="dynamic-camo-styles"></style>
    </head>
    <body>
        <div class="sidebar">
            <div class="header" id="live-btn" onclick="switchTab('live')">DASHBOARD</div>
            <div class="nav-btn" id="camo-btn" onclick="switchTab('camo')">CAMO MATRIX</div>
            <div style="padding:20px; color:#555; font-size:0.7em; font-weight:bold; letter-spacing:1px; margin-top:10px;">MATCH LOGS</div>
            <div class="list" id="history-list"></div>
            <div class="config-btn" onclick="switchTab('help')">HELP & FAQ</div>
            <div class="config-btn" onclick="reconfigure()">SYSTEM CONFIG</div>
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
                         </ul>
                    </div>

                </div>
            </div>

        </div>
        
        <input type="hidden" id="current-user-path" value="">

        <script>
            let isLive = true;
            let GLOBAL_NAMES = [];
            let GLOBAL_MAPS = {};
            let MAP_KEYS = [];
            let currentMapIndex = 0;
            let currentStarredWeapons = [];

            function switchTab(tabName) {
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.sb-item').forEach(el => el.classList.remove('active'));
                
                document.getElementById('tab-' + tabName).classList.add('active');
                
                if(tabName === 'live') {
                    isLive = true;
                    document.getElementById('live-btn').classList.add('active');
                } else if(tabName === 'camo') {
                    isLive = false;
                    document.getElementById('camo-btn').classList.add('active');
                } else {
                    isLive = false; 
                }
            }
            
            async function init() {
                updateSidebar();
                switchTab('live');
                setInterval(async () => {
                    if (isLive) {
                        try {
                            const data = await window.pywebview.api.get_live_stats();
                            if (isLive) updateData(data); 
                        } catch(e) {}
                    }
                    updateSidebar();
                }, 3000);
            }
            
            function updateData(d) {
                if(!d) return;
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
        window.load_html(get_main_app_html())
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

# --- BACKGROUND LOGIC ---
def monitor_game():
    last_id = None
    while True:
        if not app_config.get('live_path'): 
            time.sleep(1)
            continue
        live_path = app_config.get('live_path')
        hist_path = app_config.get('history_path')
        if live_path and os.path.exists(live_path):
            data = load_json(live_path)
            if data:
                game = data.get('game', {})
                raw_id = str(game.get('game_id', '0'))
                if raw_id and raw_id != "0":
                    if raw_id != last_id:
                        safe_id = sanitize_filename(raw_id)
                        if hist_path and os.path.exists(hist_path):
                            target = os.path.join(hist_path, "Game_" + safe_id + ".json")
                            save_json(target, data)
                            last_id = raw_id
        time.sleep(3)

def get_entry_point_html():
    if not app_config or not app_config.get('live_path'):
        return get_setup_html()
    return get_main_app_html()

if __name__ == "__main__":
    config_path = os.path.join(get_base_path(), CONFIG_FILE)
    if os.path.exists(config_path):
        app_config = load_json(config_path) or {}
    t = threading.Thread(target=monitor_game)
    t.daemon = True
    t.start()
    api = TrackerAPI()
    window = webview.create_window('BO3 Tracker & Camo Matrix', html=get_entry_point_html(), width=1300, height=900, background_color='#0b0c10', js_api=api)
    webview.start()