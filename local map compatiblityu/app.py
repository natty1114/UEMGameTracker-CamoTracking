import webview
import json
import os
import sys
import threading
import functools
import http.server
import socketserver
from image_fetcher import SteamImageFetcher
import update_db  # <--- IMPORT YOUR UPDATER SCRIPT HERE
import sheet_db
import steam_scraper

# --- CONFIGURATION ---
def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_app_dir()
os.chdir(BASE_DIR)

CONFIG_DIR = 'config'
JSON_FILE_NAME = 'uem_cache.json'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'uem_config.json')
FAVORITES_FILE = os.path.join(CONFIG_DIR, 'favorites.json')
CURRENT_FULL = 'Public-V1.3.1 (build-005)'
CURRENT_BB = 'V 1.3.1 (build-002)'

THEMES_FILE = os.path.join(BASE_DIR, 'themesmap', 'themes.json')

def load_themes():
    try:
        with open(THEMES_FILE, 'r', encoding='utf-8') as f:
            themes = json.load(f)
        if 'default' not in themes:
            raise ValueError('themes.json must include a default theme')
        return themes
    except Exception as e:
        print(f'Error loading themes: {e}')
        return {
            'default': {
                'name': 'Default Tactical',
                'colors': {
                    'bg-color': '#121212', 'card-bg': '#1e1e1e',
                    'text-main': '#e0e0e0', 'text-dim': '#aaa',
                    'accent-gold': '#d4af37', 'accent-green': '#5cb85c', 'accent-red': '#d9534f',
                    'border-color': '#333', 'hover-border': '#777',
                    'btn-bg': '#222', 'btn-hover': '#333',
                    'input-bg': '#000', 'modal-bg': '#1a1a1a',
                    'stat-box-bg': '#252525', 'map-title-color': '#fff',
                }
            }
        }

THEMES = load_themes()


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"theme": "default", "theme_audio_enabled": True}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        cfg.setdefault("theme_audio_enabled", True)
        return cfg
    except Exception:
        return {"theme": "default", "theme_audio_enabled": True}

def save_config(config):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass

def load_favorites():
    if not os.path.exists(FAVORITES_FILE):
        return []
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_favorites(favorites):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, indent=2)
    except Exception:
        pass

def open_help_window():
    try:
        import help_page
        webview.create_window(
            'UEM Database - Help',
            html=help_page.HTML,
            width=720,
            height=780,
            background_color='#121212',
        )
        return True
    except Exception as e:
        print(f"Help window failed: {e}")
        return False

def open_settings_window():
    try:
        import settings_page
        webview.create_window(
            "UEM Database - Settings",
            html=settings_page.get_html(),
            js_api=settings_page.SettingsApi(),
            width=760,
            height=760,
            background_color="#121212",
        )
        return True
    except Exception as e:
        print(f"Settings window failed: {e}")
        return False

def start_theme_asset_server():
    asset_dir = os.path.join(BASE_DIR, "themesmap")
    if not os.path.isdir(asset_dir):
        return ""

    class QuietAssetHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def handle(self):
            try:
                super().handle()
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

    handler = functools.partial(QuietAssetHandler, directory=asset_dir)
    try:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        return f"http://{host}:{port}"
    except Exception as e:
        print(f"Theme asset server failed: {e}")
        return ""

class JSApi:
    def __init__(self, fetcher_queue_method):
        self.queue_method = fetcher_queue_method

    def request_images(self, items):
        self.queue_method(items)

    def save_theme(self, theme_name):
        config = load_config()
        config["theme"] = theme_name
        save_config(config)

    def get_favorites(self):
        return load_favorites()

    def toggle_favorite(self, map_name):
        favorites = load_favorites()
        if map_name in favorites:
            favorites.remove(map_name)
        else:
            favorites.append(map_name)
        save_favorites(favorites)
        return favorites

    def open_help(self):
        open_help_window()

    def open_settings(self):
        open_settings_window()

    def lookup_steam_info(self, steam_url):
        try:
            info = steam_scraper.get_workshop_info(steam_url)
            return json.dumps(info)
        except Exception as e:
            return json.dumps({'error': str(e), 'map_name': '', 'author_str': '', 'steam_id': None, 'authors': []})

    def submit_report(self, steam_link, map_name, author, report_type, notes, submitter, uem_version, bb_version=''):
        try:
            sheet_db.submit_report(steam_link, map_name, author, report_type, notes, submitter, uem_version, bb_version)
            return 'ok'
        except Exception as e:
            return str(e)

def get_html_content(data_json, active_theme_name="default", themes_json="{}", theme_asset_base_url="", theme_audio_enabled=True):
    # Extract unique versions for the dropdown
    versions = set()
    for item in data_json:
        v = item.get("UEM Version (Full)")
        if v and v.strip():
            versions.add(v.strip())
    
    sorted_versions = sorted(list(versions))
    version_options = "".join([f'<option value="{v}">{"&#9733; CURRENT - " if v == CURRENT_FULL else ""}{v}</option>' for v in sorted_versions])

    import re

    def version_family(value):
        match = re.search(r'\d+\.\d+\.\d+', value or '')
        return match.group(0) if match else ''

    def version_sort_key(value):
        parts = re.findall(r'\d+|[A-Za-z]+', value or '')
        return [int(part) if part.isdigit() else part.lower() for part in parts]

    def recent_versions(values, current):
        current_family = version_family(current)
        recent = [value for value in values if version_family(value) == current_family]
        if current not in recent:
            recent.append(current)
        return sorted(set(recent), key=version_sort_key)

    # Full version options for submission form
    recent_full_versions = recent_versions(sorted_versions, CURRENT_FULL)
    version_options_form_full = "<option value=''>-- Select full version --</option>" + "".join([
        f'<option value="{v}"{" selected" if v == CURRENT_FULL else ""}>{"&#9733; CURRENT - " if v == CURRENT_FULL else ""}{v}</option>'
        for v in recent_full_versions
    ])

    # Barebones version options for submission form
    bb_versions = set()
    for item in data_json:
        bv = item.get('Barebones (V 1.1.22 Unless Stated)', '')
        m = re.search(r'V\s*[\d.]+(?:\s*\(build-\d+\))?', bv)
        if m:
            bb_versions.add(m.group())
    bb_versions.add(CURRENT_BB)
    sorted_bb = sorted(list(bb_versions), key=lambda x: [int(p) if p.isdigit() else p for p in re.findall(r'[\d.]+|[^\d.]+', x)])
    recent_bb_versions = recent_versions(sorted_bb, CURRENT_BB)
    version_options_form_bb = "<option value=''>-- Select barebones version --</option>" + "".join([
        f'<option value="{v}"{" selected" if v == CURRENT_BB else ""}>{"&#9733; CURRENT - " if v == CURRENT_BB else ""}{v}</option>'
        for v in recent_bb_versions
    ])

    theme_options = "".join([
        f'<option value="{k}"{" selected" if k == active_theme_name else ""}>{v["name"]}</option>'
        for k, v in THEMES.items()
    ])

    json_str = json.dumps(data_json)
    asset_base = theme_asset_base_url.rstrip("/")
    deadops_gif_src = f"{asset_base}/Deadops.gif" if asset_base else ""
    deadops_audio_src = f"{asset_base}/deadops.mp3" if asset_base else ""
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UEM DATABASE</title>
    <style>
        :root {{
            --bg-color: #121212; --card-bg: #1e1e1e; --text-main: #e0e0e0; --text-dim: #aaa;
            --accent-gold: #d4af37; --accent-green: #5cb85c; --accent-red: #d9534f;
            --border-color: #333; --hover-border: #777; --btn-bg: #222; --btn-hover: #333;
            --input-bg: #000; --modal-bg: #1a1a1a; --stat-box-bg: #252525; --map-title-color: #fff;
            --font-main: "Segoe UI", sans-serif;
            --radius: 8px; --radius-sm: 4px; --shadow: 0 2px 8px rgba(0,0,0,0.25);
            --shadow-hover: 0 8px 25px rgba(0,0,0,0.35);
        }}
        * {{ scrollbar-width: thin; scrollbar-color: var(--border-color) transparent; }}
        body {{ background-color: var(--bg-color); color: var(--text-main); font-family: var(--font-main); margin: 0; padding: 16px 20px 12px; display: flex; flex-direction: column; height: 100vh; box-sizing: border-box; }}

        header {{ border-bottom: 2px solid var(--accent-gold); padding-bottom: 12px; margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: center; flex-shrink: 0; }}
        .header-left {{ display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
        .header-left h1 {{ margin: 0; color: var(--accent-gold); font-size: 1.5rem; text-transform: uppercase; letter-spacing: 2px; }}
        .header-subtitle {{ color: var(--text-dim); font-size: 0.7rem; letter-spacing: 1px; opacity: 0.65; text-transform: uppercase; }}

        .controls {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}

        select, input {{ background: var(--input-bg); border: 1px solid var(--accent-gold); color: var(--accent-gold); padding: 6px 10px; font-size: 0.8rem; outline: none; box-sizing: border-box; border-radius: var(--radius-sm); transition: border-color 0.2s, box-shadow 0.2s; }}
        select:focus, input:focus {{ box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent-gold) 20%, transparent); }}
        select {{ cursor: pointer; text-transform: uppercase; font-weight: bold; padding-right: 4px; min-height: 32px; }}
        #search-box {{ width: 200px; }}
        #version-filter {{ min-width: 200px; }}

        .filter-group {{ display: flex; align-items: center; }}

        #grid-wrapper {{ flex-grow: 1; overflow-y: auto; padding-right: 8px; }}
        #grid-wrapper::-webkit-scrollbar {{ width: 6px; }}
        #grid-wrapper::-webkit-scrollbar-track {{ background: transparent; }}
        #grid-wrapper::-webkit-scrollbar-thumb {{ background: var(--border-color); border-radius: 3px; }}
        #grid-wrapper::-webkit-scrollbar-thumb:hover {{ background: var(--hover-border); }}

        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 14px; padding-bottom: 16px; }}
        .theme-media {{ display: none; margin: 8px 0 0; width: 100%; height: var(--deadops-media-height, 0px); min-height: 0; border: 1px solid var(--border-color); border-radius: var(--radius); overflow: hidden; background: #000; box-shadow: var(--shadow); position: relative; pointer-events: none; }}
        .theme-media.active {{ display: block; }}
        .theme-media-backdrop {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center; filter: blur(14px) saturate(1.15) brightness(0.5); transform: scale(1.06); opacity: 0.82; }}
        .theme-media-main {{ position: relative; display: block; width: 100%; height: 100%; object-fit: contain; object-position: center; image-rendering: auto; }}
        .theme-media audio {{ display: none; }}
        .theme-media-title {{ position: absolute; top: 8px; left: 10px; color: var(--accent-gold); font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; padding: 5px 8px; background: rgba(0,0,0,0.72); border: 1px solid var(--border-color); border-radius: var(--radius-sm); z-index: 2; }}

        .card {{ 
            background-color: var(--card-bg); 
            border: 1px solid var(--border-color); 
            border-radius: var(--radius);
            display: flex; 
            flex-direction: column; 
            min-height: 420px;
            transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease; 
            position: relative; 
            overflow: hidden;
            box-shadow: var(--shadow);
        }}
        .card:hover {{ transform: translateY(-4px); border-color: var(--hover-border); box-shadow: var(--shadow-hover); }}
        
        .card-image {{ height: 180px; background-color: var(--input-bg); background-size: cover; background-position: center; border-bottom: 1px solid var(--border-color); flex-shrink: 0; position: relative; overflow: hidden; }}
        .star-btn {{ position: absolute; top: 6px; right: 6px; background: rgba(0,0,0,0.5); border: none; font-size: 1.4rem; line-height: 1; padding: 2px 6px 4px; border-radius: var(--radius-sm); cursor: pointer; transition: transform 0.15s, background 0.15s; z-index: 2; color: #888; }}
        .star-btn:hover {{ transform: scale(1.2); background: rgba(0,0,0,0.7); }}
        .star-btn.fav {{ color: #ffd700; text-shadow: 0 0 8px rgba(255,215,0,0.6); }}
        .help-btn {{ background: var(--btn-bg); border: 1px solid var(--accent-gold); color: var(--accent-gold); width: 32px; height: 32px; font-size: 1.1rem; font-weight: bold; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s, transform 0.15s; line-height: 1; padding: 0; }}
        .help-btn:hover {{ background: var(--accent-gold); color: #000; transform: scale(1.1); }}
        .settings-btn {{ background: var(--btn-bg); border: 1px solid var(--text-dim); color: var(--text-dim); width: 32px; height: 32px; font-size: 1.1rem; font-weight: bold; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s, transform 0.15s; line-height: 1; padding: 0; }}
        .settings-btn:hover {{ background: var(--text-dim); color: #000; transform: scale(1.1); }}
        .report-btn {{ background: var(--btn-bg); border: 1px solid var(--accent-green); color: var(--accent-green); width: 32px; height: 32px; font-size: 1.3rem; font-weight: bold; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.2s, transform 0.15s; line-height: 1; padding: 0; }}
        .report-btn:hover {{ background: var(--accent-green); color: #000; transform: scale(1.1); }}
        .form-group {{ margin-bottom: 12px; }}
        .form-group label {{ display: block; color: var(--text-dim); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }}
        .form-group input, .form-group select, .form-group textarea {{ width: 100%; background: var(--input-bg); border: 1px solid var(--border-color); color: var(--text-main); padding: 8px 10px; font-size: 0.85rem; outline: none; box-sizing: border-box; border-radius: var(--radius-sm); font-family: var(--font-main); }}
        .form-group select {{ min-width: 0; overflow: hidden; text-overflow: ellipsis; }}
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{ border-color: var(--accent-gold); box-shadow: 0 0 0 2px color-mix(in srgb, var(--accent-gold) 15%, transparent); }}
        .form-group textarea {{ resize: vertical; min-height: 60px; }}
        .submit-btn {{ background: var(--accent-green); color: #000; border: none; padding: 10px 24px; font-size: 0.85rem; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; border-radius: var(--radius-sm); cursor: pointer; transition: opacity 0.2s; }}
        .submit-btn:hover {{ opacity: 0.85; }}
        .submit-btn:disabled {{ opacity: 0.4; cursor: default; }}
        #submit-status {{ font-size: 0.8rem; margin-top: 8px; }}
        .card-image.no-img {{ background: repeating-linear-gradient(45deg, var(--card-bg) 25%, var(--input-bg) 25%, var(--input-bg) 75%, var(--card-bg) 75%); background-size: 20px 20px; display: flex; align-items: center; justify-content: center; color: var(--border-color); font-weight: bold; font-size: 0.8rem; letter-spacing: 2px; text-transform: uppercase; }}
        .card-image.no-img::after {{ content: "NO INTEL"; }}
        
        .card-content {{ padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; flex-grow: 1; overflow: hidden; }}
        
        .map-title {{ font-size: 1.05rem; font-weight: bold; color: var(--map-title-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        
        .author {{ 
            font-size: 0.8rem; 
            color: var(--accent-gold); 
            font-style: italic; 
            margin-bottom: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            line-height: 1.35;
            max-height: 2.7em;
        }}
        
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 0.78rem; margin-top: auto; }}
        .stat-box {{ background: var(--stat-box-bg); padding: 5px 7px; border-radius: var(--radius-sm); display: flex; flex-direction: column; }}
        .stat-label {{ color: var(--text-dim); font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.5px; }}
        .stat-val {{ font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }}
        .stat-val.yes {{ color: var(--accent-green); }}
        .stat-val.no {{ color: var(--accent-red); }}

        .actions {{ display: flex; border-top: 1px solid var(--border-color); height: 38px; flex-shrink: 0; }}
        .btn {{ flex: 1; display: flex; align-items: center; justify-content: center; text-decoration: none; color: var(--text-dim); font-size: 0.75rem; font-weight: 600; letter-spacing: 0.5px; border-right: 1px solid var(--border-color); background: var(--btn-bg); transition: background 0.2s, color 0.2s; cursor: pointer; text-transform: uppercase; }}
        .btn:last-child {{ border-right: none; }}
        .btn:hover {{ background: var(--btn-hover); color: var(--map-title-color); }}
        .btn-yt:hover {{ background: #4a0000; color: #ffaaaa; }}
        .btn-steam:hover {{ background: #1b2838; color: #66c0f4; }}
        .btn-details:hover {{ background: var(--btn-hover); color: var(--accent-gold); }}

        footer {{ border-top: 1px solid var(--border-color); padding-top: 12px; margin-top: 8px; display: flex; flex-direction: column; gap: 8px; align-items: center; flex-shrink: 0; }}
        .pagination-bar {{ display: flex; gap: 4px; align-items: center; }}
        .pg-btn {{ background: var(--btn-bg); color: var(--map-title-color); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 5px 10px; cursor: pointer; font-weight: bold; min-width: 32px; font-size: 0.8rem; transition: background 0.2s, color 0.2s, border-color 0.2s; }}
        .pg-btn:hover:not(:disabled) {{ background: var(--accent-gold); color: black; border-color: var(--accent-gold); }}
        .pg-btn.active {{ background: var(--accent-gold); color: black; border-color: var(--accent-gold); pointer-events: none; }}
        .pg-btn:disabled {{ opacity: 0.3; cursor: default; }}
        #result-count {{ color: var(--text-dim); font-size: 0.75rem; letter-spacing: 0.5px; }}

        .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 1000; align-items: center; justify-content: center; backdrop-filter: blur(4px); }}
        .modal-box {{ background: var(--modal-bg); border: 1px solid var(--accent-gold); border-radius: var(--radius); width: 600px; max-width: 92%; max-height: 80vh; overflow-y: auto; padding: 24px; box-shadow: 0 0 40px rgba(0,0,0,0.5); display: flex; flex-direction: column; gap: 16px; }}
        .modal-header {{ border-bottom: 1px solid var(--border-color); padding-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }}
        .modal-title {{ color: var(--accent-gold); font-size: 1.3rem; text-transform: uppercase; margin: 0; letter-spacing: 1px; }}
        .close-btn {{ background: transparent; border: none; color: var(--text-dim); font-size: 1.6rem; cursor: pointer; transition: color 0.2s; line-height: 1; padding: 0 4px; }}
        .close-btn:hover {{ color: var(--map-title-color); }}
        .detail-row {{ display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-color); padding: 10px 0; gap: 12px; }}
        .detail-label {{ color: var(--text-dim); font-weight: 600; font-size: 0.85rem; width: 38%; flex-shrink: 0; }}
        .detail-value {{ width: 62%; text-align: right; color: var(--map-title-color); word-break: break-word; font-size: 0.85rem; }}
        .full-text {{ color: var(--text-main); font-size: 0.85rem; line-height: 1.6; white-space: pre-wrap; background: var(--btn-bg); padding: 12px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); }}
    </style>
</head>
<body>
    <header>
        <div class="header-left">
            <h1>UEM Database</h1>
            <span class="header-subtitle">CLASSIFIED RECORDS // V.3.2</span>
        </div>
        <div class="controls">
            
            <div class="filter-group">
                <select id="status-filter" onchange="handleSearch()" title="Support Status">
                    <option value="all">ALL STATUS</option>
                    <option value="full">FULL SUPPORT</option>
                    <option value="barebones">BAREBONES</option>
                    <option value="broken">BROKEN</option>
                </select>
            </div>

            <div class="filter-group">
                <select id="version-filter" onchange="handleSearch()" title="UEM Version">
                    <option value="all">ALL VERSIONS</option>
                    {version_options}
                </select>
            </div>

            <div class="filter-group">
                <select id="xp-filter" onchange="handleSearch()" title="XP Multiplier">
                    <option value="all">ALL XP</option>
                    <option value="nerfed">NERFED (< 1.03)</option>
                    <option value="non-nerfed">NON-NERFED (1.03+)</option>
                </select>
            </div>

            <div class="filter-group">
                <select id="fav-filter" onchange="handleSearch()" title="Favorites">
                    <option value="all">ALL MAPS</option>
                    <option value="fav">FAVORITES</option>
                </select>
            </div>

            <input type="text" id="search-box" placeholder="SEARCH..." onkeyup="handleSearch()">

            <div class="filter-group">
                <select id="theme-selector" onchange="applyTheme(this.value)" title="Theme">
                    {theme_options}
                </select>
            </div>

            <button class="help-btn" onclick="openHelp()" title="Help">?</button>
            <button class="settings-btn" onclick="openSettings()" title="Settings">&#9881;</button>
            <button class="report-btn" onclick="openReportModal()" title="Submit Report / Suggest Map">+</button>
        </div>
    </header>

    <div id="grid-wrapper">
        <div id="grid" class="grid-container"></div>
        <div id="deadops-media" class="theme-media">
            <div class="theme-media-title">Dead Ops Arcade</div>
            <img class="theme-media-backdrop" src="{deadops_gif_src}" alt="">
            <img class="theme-media-main" src="{deadops_gif_src}" alt="Dead Ops Arcade animated theme">
            <audio id="deadops-audio" src="{deadops_audio_src}" autoplay loop preload="auto"></audio>
        </div>
    </div>

    <footer>
        <div class="pagination-bar" id="pagination-controls"></div>
        <div id="result-count">Loading...</div>
    </footer>

    <div id="modal" class="modal-overlay" onclick="if(event.target === this) closeModal()">
        <div class="modal-box">
            <div class="modal-header">
                <h2 id="m-title" class="modal-title">CLASSIFIED INTEL</h2>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div id="m-content"></div>
        </div>
    </div>

    <div id="report-modal" class="modal-overlay" onclick="if(event.target === this) closeReportModal()">
        <div class="modal-box" style="max-width: 520px;">
            <div class="modal-header">
                <h2 class="modal-title">SUBMIT REPORT</h2>
                <button class="close-btn" onclick="closeReportModal()">&times;</button>
            </div>
            <div style="padding: 4px 0;">
                <p style="color:var(--text-dim);font-size:0.8rem;margin-bottom:14px;">Report a broken map, confirm one works, or suggest a new map to add.</p>
                <div class="form-group">
                    <label>Steam Workshop Link *</label>
                    <input type="url" id="r-link" placeholder="https://steamcommunity.com/sharedfiles/filedetails/?id=..." oninput="autoFillMap()">
                </div>
                <div class="form-group">
                    <label>Map Name</label>
                    <input type="text" id="r-map" placeholder="Auto-filled if possible">
                </div>
                <div class="form-group">
                    <label>Map Author</label>
                    <input type="text" id="r-author" placeholder="Optional">
                </div>
                <div class="form-group">
                    <label>Report Type *</label>
                    <select id="r-type" onchange="autoFillVersions()">
                        <option value="Works">Map Works (Full Support)</option>
                        <option value="WorksBugs">Map Works (Full Support - Bugs)</option>
                        <option value="Barebones">Map Works (Barebones)</option>
                        <option value="BarebonesBugs">Map Works (Barebones Bugs)</option>
                        <option value="Broken">Map is Broken</option>
                        <option value="Suggestion">Suggest New Map</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Full UEM Version</label>
                    <select id="r-version-full">{version_options_form_full}</select>
                </div>
                <div class="form-group">
                    <label>Barebones UEM Version</label>
                    <select id="r-version-bb">{version_options_form_bb}</select>
                </div>
                <div class="form-group">
                    <label>Notes</label>
                    <textarea id="r-notes" placeholder="Any extra details..."></textarea>
                </div>
                <div class="form-group">
                    <label>Your Name / Discord</label>
                    <input type="text" id="r-submitter" placeholder="Optional">
                </div>
                <button class="submit-btn" id="r-submit" onclick="doSubmit()">SUBMIT REPORT</button>
                <div id="submit-status"></div>
            </div>
        </div>
    </div>

    <script>
        const rawData = {json_str};
        let currentData = rawData;
        const ITEMS_PER_PAGE = 12;
        let currentPage = 1;

        const THEMES = {themes_json};
        const CURRENT_FULL = '{CURRENT_FULL}';
        const CURRENT_BB = '{CURRENT_BB}';
        const THEME_AUDIO_ENABLED = {str(theme_audio_enabled).lower()};
        let currentTheme = '{active_theme_name}';
        let favoritesList = [];

        function loadThemeFont(importUrl) {{
            const id = 'theme-font-link';
            const old = document.getElementById(id);
            if (old) old.remove();
            if (importUrl) {{
                const link = document.createElement('link');
                link.id = id; link.rel = 'stylesheet'; link.href = importUrl;
                document.head.appendChild(link);
            }}
        }}

        function applyTheme(name) {{
            const theme = THEMES[name];
            if (!theme) return;
            const root = document.documentElement;
            const colors = theme.colors;
            for (const [key, val] of Object.entries(colors)) {{
                root.style.setProperty(`--${{key}}`, val);
            }}
            if (theme.font) {{
                document.body.style.fontFamily = theme.font.family;
                loadThemeFont(theme.font.import || '');
            }} else {{
                document.body.style.fontFamily = '';
                loadThemeFont('');
            }}
            if (theme.cursor) {{
                document.body.style.cursor = theme.cursor;
                let cs = document.getElementById('cursor-style');
                if (!cs) {{
                    cs = document.createElement('style');
                    cs.id = 'cursor-style';
                    document.head.appendChild(cs);
                }}
                cs.textContent = 'body *, button, a, select, input, textarea, [onclick] {{ cursor: inherit !important; }}';
            }} else {{
                document.body.style.cursor = '';
                const cs = document.getElementById('cursor-style');
                if (cs) cs.remove();
            }}
            currentTheme = name;
            document.getElementById('theme-selector').value = name;
            const deadopsMedia = document.getElementById('deadops-media');
            const deadopsAudio = document.getElementById('deadops-audio');
            if (deadopsMedia && deadopsAudio) {{
                if (theme.audio) {{
                    deadopsMedia.classList.add('active');
                    requestAnimationFrame(fitDeadopsMediaToEmptySpace);
                    if (THEME_AUDIO_ENABLED) {{
                        deadopsAudio.play().catch(function() {{}});
                    }}
                }} else {{
                    deadopsMedia.classList.remove('active');
                    deadopsMedia.style.removeProperty('--deadops-media-height');
                    deadopsAudio.pause();
                    deadopsAudio.currentTime = 0;
                }}
            }}
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.save_theme(name);
            }}
        }}

        function tryStartDeadopsAudio() {{
            const deadopsAudio = document.getElementById('deadops-audio');
            if (THEME_AUDIO_ENABLED && currentTheme === 'DeadOps Arcade' && deadopsAudio && deadopsAudio.paused) {{
                deadopsAudio.play().catch(function() {{}});
            }}
        }}

        function fitDeadopsMediaToEmptySpace() {{
            const media = document.getElementById('deadops-media');
            const wrapper = document.getElementById('grid-wrapper');
            const grid = document.getElementById('grid');
            if (!media || !wrapper || !grid || !THEMES[currentTheme]?.audio) return;
            const gridBottom = grid.offsetTop + grid.offsetHeight;
            const available = wrapper.clientHeight - gridBottom - 10;
            const height = Math.max(0, Math.floor(available));
            media.style.setProperty('--deadops-media-height', height + 'px');
            media.style.display = height > 24 ? '' : 'none';
        }}
        window.addEventListener('resize', fitDeadopsMediaToEmptySpace);
        window.addEventListener('click', tryStartDeadopsAudio);
        window.addEventListener('keydown', tryStartDeadopsAudio);

        function toggleFavorite(mapName, btn) {{
            const wasFav = favoritesList.includes(mapName);
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.toggle_favorite(mapName).then(function(favs) {{
                    favoritesList = favs;
                    updateStarUI(mapName, btn);
                    if (document.getElementById('fav-filter').value === 'fav') handleSearch();
                }});
            }} else {{
                if (wasFav) favoritesList = favoritesList.filter(f => f !== mapName);
                else favoritesList.push(mapName);
                try {{ localStorage.setItem('uem_favorites', JSON.stringify(favoritesList)); }} catch(e) {{}}
                updateStarUI(mapName, btn);
                if (document.getElementById('fav-filter').value === 'fav') handleSearch();
            }}
        }}

        function updateStarUI(mapName, btn) {{
            const isFav = favoritesList.includes(mapName);
            btn.textContent = isFav ? '\\u2605' : '\\u2606';
            btn.classList.toggle('fav', isFav);
        }}

        function handleSearch() {{
            const query = document.getElementById('search-box').value.toLowerCase();
            const statusFilter = document.getElementById('status-filter').value;
            const versionFilter = document.getElementById('version-filter').value;
            const xpFilter = document.getElementById('xp-filter').value;
            const favFilter = document.getElementById('fav-filter').value;
            
            const xpKey = "XP Value (No Modifiers, Taken from round 1 or 2) \\nNot Legend Rank";

            currentData = rawData.filter(item => {{
                // 1. Text & Link Search
                const mapName = (item["Maps"] || "").toLowerCase();
                const author = (item["Map authors\\n"] || item["Map authors"] || "").toLowerCase();
                const tags = (item["Map Filters"] || "").toLowerCase();
                const link = (item["Hyperlinks For AppSheet"] || "").toLowerCase();
                
                if (query && !mapName.includes(query) && !author.includes(query) && !tags.includes(query) && !link.includes(query)) return false;

                // 2. Status Filter
                const full = (item["Full"] || "").toLowerCase();
                const bare = (item["Barebones (V 1.1.22 Unless Stated)"] || "").toLowerCase();
                
                if (statusFilter === "full" && !full.includes("yes")) return false;
                if (statusFilter === "barebones" && (!bare.includes("yes") || full.includes("yes"))) return false;
                if (statusFilter === "broken" && (full.includes("yes") || bare.includes("yes"))) return false;

                // 3. Version Filter
                const ver = (item["UEM Version (Full)"] || "");
                if (versionFilter !== "all" && ver !== versionFilter) return false;

                // 4. XP Filter (Threshold 1.03)
                let xpVal = parseFloat(item[xpKey]);
                if (isNaN(xpVal)) xpVal = 1.03; // Default to non-nerfed if unknown

                if (xpFilter === "nerfed" && xpVal >= 1.03) return false;
                if (xpFilter === "non-nerfed" && xpVal < 1.03) return false;

                // 5. Favorites filter
                if (favFilter === "fav" && !favoritesList.includes(mapName)) return false;

                return true;
            }});
            
            currentPage = 1;
            renderPage();
        }}

        function renderPage() {{
            const grid = document.getElementById('grid');
            grid.innerHTML = '';
            
            const totalPages = Math.ceil(currentData.length / ITEMS_PER_PAGE) || 1;
            if(currentPage > totalPages) currentPage = totalPages;
            if(currentPage < 1) currentPage = 1;

            const start = (currentPage - 1) * ITEMS_PER_PAGE;
            const end = start + ITEMS_PER_PAGE;
            const itemsToShow = currentData.slice(start, end);
            const imageRequests = [];

            itemsToShow.forEach((item, index) => {{
                const actualIndex = start + index; 

                const mapName = item["Maps"] || "Unknown";
                const author = (item["Map authors\\n"] || item["Map authors"] || "Unknown").replace(/\\n/g, ', ');
                const fullStatus = item["Full"] || "N/A";
                const bareStatus = item["Barebones (V 1.1.22 Unless Stated)"] || "N/A";
                
                // XP Logic
                const xpKey = "XP Value (No Modifiers, Taken from round 1 or 2) \\nNot Legend Rank";
                let xpRaw = item[xpKey];
                let xpDisplay = "-";
                let xpColor = "var(--accent-gold)"; 
                
                if (xpRaw !== null && xpRaw !== undefined && xpRaw !== "") {{
                    const val = parseFloat(xpRaw);
                    if (!isNaN(val)) {{
                        xpDisplay = val.toFixed(2) + "x";
                        if (val < 1.03) xpColor = "#d9534f"; 
                        else xpColor = "#5cb85c"; 
                    }} else {{
                        xpDisplay = xpRaw; 
                    }}
                }}

                const linkSteam = item["Hyperlinks For AppSheet"] || "";
                const linkYt = item["Youtube Links"] || "";
                
                const steamId = getSteamId(linkSteam);
                const imgId = steamId ? `img-${{steamId}}` : '';
                if(steamId) imageRequests.push({{ id: steamId, url: linkSteam }});

                const fullClass = fullStatus.toLowerCase().includes('yes') ? 'yes' : 'no';
                const bareClass = bareStatus.toLowerCase().includes('yes') ? 'yes' : 'no';
                const isFav = favoritesList.includes(mapName);

                const card = document.createElement('div');
                card.className = 'card';
                let html = `
                    <div class="card-image no-img" id="${{imgId}}">
                        <button class="star-btn${{isFav ? ' fav' : ''}}" onclick="toggleFavorite('${{mapName.replace(/'/g, "\\\\'")}}', this);event.stopPropagation();">${{isFav ? '\\u2605' : '\\u2606'}}</button>
                    </div>
                    <div class="card-content">
                        <div class="map-title" title="${{mapName}}">${{mapName}}</div>
                        <div class="author" title="${{author}}">${{author}}</div>
                        <div class="stats-grid">
                            <div class="stat-box"><span class="stat-label">FULL SUPPORT</span><span class="stat-val ${{fullClass}}">${{fullStatus}}</span></div>
                            <div class="stat-box"><span class="stat-label">BAREBONES</span><span class="stat-val ${{bareClass}}">${{bareStatus}}</span></div>
                            <div class="stat-box" style="grid-column: span 2"><span class="stat-label">XP VALUE</span><span class="stat-val" style="color:${{xpColor}}">${{xpDisplay}}</span></div>
                        </div>
                    </div>
                    <div class="actions">
                        <div class="btn btn-details" onclick="openModal(${'{actualIndex}'})">DETAILS</div>
                `;
                
                if (linkSteam) html += `<a href="${{linkSteam}}" target="_blank" class="btn btn-steam">STEAM</a>`;
                if (linkYt && linkYt !== 'N/A') html += `<a href="${{linkYt}}" target="_blank" class="btn btn-yt">YOUTUBE</a>`;
                
                html += `</div>`; 
                
                card.innerHTML = html;
                grid.appendChild(card);
            }});

            renderPagination(totalPages);
            document.getElementById('result-count').innerText = `SHOWING ${{itemsToShow.length}} OF ${{currentData.length}} MAPS`;
            document.getElementById('grid-wrapper').scrollTop = 0;

            if(window.pywebview && window.pywebview.api) {{
                window.pywebview.api.request_images(imageRequests);
            }}
            requestAnimationFrame(fitDeadopsMediaToEmptySpace);
        }}

        function openModal(index) {{
            const item = currentData[index];
            const content = document.getElementById('m-content');
            document.getElementById('m-title').innerText = item["Maps"] || "CLASSIFIED";
            
            let html = '';
            const addRow = (label, val) => {{
                if(val && val !== 'N/A') html += `<div class="detail-row"><span class="detail-label">${{label}}</span><span class="detail-value">${{val}}</span></div>`;
            }};

            addRow("Map Authors", (item["Map authors\\n"] || item["Map authors"] || "").replace(/\\n/g, ', '));
            addRow("UEM Version", item["UEM Version (Full)"]);
            addRow("Date Tested", item["Date Tested Full\\n(UK Date Format)"]);
            addRow("XP Value", item["XP Value (No Modifiers, Taken from round 1 or 2) \\nNot Legend Rank"]);
            addRow("Filters", item["Map Filters"]);
            
            const notes = item["Bugs to report/Notes"];
            if(notes) html += `<div style="margin-top:10px;"><div class="detail-label" style="margin-bottom:5px;">NOTES / BUGS:</div><div class="full-text">${{notes}}</div></div>`;

            content.innerHTML = html;
            document.getElementById('modal').style.display = 'flex';
        }}

        function closeModal() {{ document.getElementById('modal').style.display = 'none'; }}

        function renderPagination(totalPages) {{
            const container = document.getElementById('pagination-controls');
            let html = '';
            html += `<button class="pg-btn" onclick="goToPage(${'{currentPage - 1}'})" ${'{currentPage === 1 ? "disabled" : ""}'}>&lt;</button>`;
            if(currentPage > 5) html += `<button class="pg-btn" onclick="goToPage(${'{currentPage - 5}'})">&lt;&lt; -5</button>`;
            
            let startPage = Math.max(1, currentPage - 2);
            let endPage = Math.min(totalPages, currentPage + 2);
            if (endPage - startPage < 4) {{
                if (startPage === 1) endPage = Math.min(totalPages, startPage + 4);
                else if (endPage === totalPages) startPage = Math.max(1, endPage - 4);
            }}

            for(let i = startPage; i <= endPage; i++) html += `<button class="pg-btn ${'{i === currentPage ? "active" : ""}'}" onclick="goToPage(${'{i}'})">${'{i}'}</button>`;
            
            if(currentPage <= totalPages - 5) html += `<button class="pg-btn" onclick="goToPage(${'{currentPage + 5}'})">+5 &gt;&gt;</button>`;
            html += `<button class="pg-btn" onclick="goToPage(${'{currentPage + 1}'})" ${'{currentPage === totalPages ? "disabled" : ""}'}>&gt;</button>`;
            container.innerHTML = html;
        }}

        function goToPage(p) {{ currentPage = p; renderPage(); }}
        function openHelp() {{ if (window.pywebview && window.pywebview.api) window.pywebview.api.open_help(); }}
        function openSettings() {{ if (window.pywebview && window.pywebview.api) window.pywebview.api.open_settings(); }}

        function openReportModal() {{
            document.getElementById('report-modal').style.display = 'flex';
            document.getElementById('submit-status').textContent = '';
        }}
        function closeReportModal() {{
            document.getElementById('report-modal').style.display = 'none';
        }}
        function autoFillMap() {{
            const link = document.getElementById('r-link').value;
            const match = link.match(/[?&]id=(\\d+)/);
            if (!match) return;
            const id = match[1];
            // Try local DB first
            const item = rawData.find(function(i) {{
                const l = (i['Hyperlinks For AppSheet'] || '');
                return l.includes('id=' + id);
            }});
            if (item) {{
                document.getElementById('r-map').value = item['Maps'] || '';
                const author = item['Map authors\\n'] || item['Map authors'] || '';
                document.getElementById('r-author').value = author.replace(/\\n/g, ', ');
                document.getElementById('r-version-full').value = item['UEM Version (Full)'] || '';
                return;
            }}
            // Fall back to Steam page scrape
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.lookup_steam_info(link).then(function(result) {{
                    const info = JSON.parse(result);
                    if (info.map_name) document.getElementById('r-map').value = info.map_name;
                    if (info.author_str) document.getElementById('r-author').value = info.author_str;
                }});
            }}
        }}
        function autoFillVersions() {{
            const type = document.getElementById('r-type').value;
            const fullSelect = document.getElementById('r-version-full');
            const bbSelect = document.getElementById('r-version-bb');
            if (type === 'Works' || type === 'WorksBugs' || type === 'Broken' || type === 'Suggestion') {{
                fullSelect.value = CURRENT_FULL;
                bbSelect.value = CURRENT_BB;
            }} else if (type === 'Barebones' || type === 'BarebonesBugs') {{
                fullSelect.value = '';
                bbSelect.value = CURRENT_BB;
            }} else {{
                fullSelect.value = '';
                bbSelect.value = '';
            }}
        }}
        function doSubmit() {{
            const link = document.getElementById('r-link').value.trim();
            if (!link) {{ document.getElementById('submit-status').textContent = 'Steam link is required.'; return; }}
            const btn = document.getElementById('r-submit');
            btn.disabled = true;
            btn.textContent = 'SUBMITTING...';
            document.getElementById('submit-status').textContent = '';
            const data = {{
                steam_link: link,
                map_name: document.getElementById('r-map').value.trim(),
                author: document.getElementById('r-author').value.trim(),
                report_type: document.getElementById('r-type').value,
                notes: document.getElementById('r-notes').value.trim(),
                submitter: document.getElementById('r-submitter').value.trim(),
                uem_version: document.getElementById('r-version-full').value.trim(),
                bb_version: document.getElementById('r-version-bb').value.trim()
            }};
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.submit_report(data.steam_link, data.map_name, data.author, data.report_type, data.notes, data.submitter, data.uem_version, data.bb_version).then(function(result) {{
                    btn.disabled = false;
                    btn.textContent = 'SUBMIT REPORT';
                    if (result === 'ok') {{
                        document.getElementById('submit-status').style.color = 'var(--accent-green)';
                        document.getElementById('submit-status').textContent = 'Report submitted! Thank you.';
                        document.getElementById('r-link').value = '';
                        document.getElementById('r-map').value = '';
                        document.getElementById('r-author').value = '';
                        document.getElementById('r-notes').value = '';
                        document.getElementById('r-version-full').value = '';
                        document.getElementById('r-version-bb').value = '';
                        setTimeout(closeReportModal, 2000);
                    }} else {{
                        document.getElementById('submit-status').style.color = 'var(--accent-red)';
                        document.getElementById('submit-status').textContent = 'Error: ' + result;
                    }}
                }});
            }} else {{
                btn.disabled = false;
                btn.textContent = 'SUBMIT REPORT';
                document.getElementById('submit-status').style.color = 'var(--accent-red)';
                document.getElementById('submit-status').textContent = 'Submission only available in the desktop app.';
            }}
        }}
        function getSteamId(url) {{ try {{ return new URL(url).searchParams.get("id"); }} catch(e) {{ return null; }} }}
        function updateImage(steamId, imageSrc) {{
            const el = document.getElementById('img-' + steamId);
            if (el) {{ el.style.backgroundImage = `url('${{imageSrc}}')`; el.classList.remove('no-img'); }}
        }}

        function initApp() {{
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.get_favorites().then(function(favs) {{
                    favoritesList = favs;
                    applyTheme(currentTheme);
                    renderPage();
                }});
            }} else {{
                const stored = localStorage.getItem('uem_favorites');
                if (stored) try {{ favoritesList = JSON.parse(stored); }} catch(e) {{}}
                applyTheme(currentTheme);
                renderPage();
            }}
        }}
        window.addEventListener('pywebviewready', initApp);
        setTimeout(function() {{ if(!window.pywebview) initApp(); }}, 500);
    </script>
</body>
</html>
    """

def main():
    if not os.path.exists(JSON_FILE_NAME):
        print(f"Error: {JSON_FILE_NAME} not found.")
        # Try to download it immediately if missing
        try:
            print("Fetching initial data...")
            update_db.update_database()
        except:
            pass
            
    try:
        with open(JSON_FILE_NAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    config = load_config()
    active_theme = config.get("theme", "default")
    theme_audio_enabled = config.get("theme_audio_enabled", True)
    theme_colors = THEMES.get(active_theme, THEMES["default"])["colors"]
    bg_color = theme_colors.get("bg-color", "#121212")

    fetcher = SteamImageFetcher()
    api = JSApi(fetcher.queue_batch)
    theme_asset_base_url = start_theme_asset_server()
    app_is_closing = {"value": False}
    window = webview.create_window(
        'UEM Classified Database',
        html=get_html_content(data, active_theme, json.dumps(THEMES), theme_asset_base_url, theme_audio_enabled),
        js_api=api,
        width=1300,
        height=950,
        background_color=bg_color
    )

    def safe_ui_update(steam_id, img_src):
        if app_is_closing["value"]:
            return
        try:
            window.evaluate_js(f"updateImage('{steam_id}', '{img_src}')")
        except Exception:
            app_is_closing["value"] = True
            fetcher.stop()

    def on_window_closed():
        app_is_closing["value"] = True
        fetcher.stop()

    try:
        window.events.closed += on_window_closed
    except Exception:
        pass

    fetcher.set_callback(safe_ui_update)
    
    # STARTUP: Launch Image Fetcher AND Database Updater
    def on_start():
        # Start the image fetcher thread
        fetcher.start()
        
        # Start the database updater thread (Daemon = closes when app closes)
        db_thread = threading.Thread(target=update_db.main, daemon=True)
        db_thread.start()

    webview.start(func=on_start)

if __name__ == '__main__':
    main()
