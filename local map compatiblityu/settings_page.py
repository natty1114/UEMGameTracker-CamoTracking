import json
import os
from pathlib import Path

import webview

import app
import image_fetcher
import sheet_db


ROOT = Path(__file__).resolve().parent


def _fmt_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024


def _folder_size(path):
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def _file_state(path):
    return "Found" if path.exists() else "Missing"


def _load_config():
    config_path = ROOT / app.CONFIG_FILE
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"theme": "default"}


def _save_config(config):
    config_path = ROOT / app.CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _build_rows():
    config = _load_config()
    image_settings = image_fetcher.get_image_cache_settings()
    submission_state = sheet_db.get_submission_endpoint_state()
    image_folder = ROOT / "steam_images"
    rows = [
        ("Active theme", config.get("theme", "default")),
        ("Theme audio", "Enabled" if config.get("theme_audio_enabled", True) else "Disabled"),
        ("Current full version", app.CURRENT_FULL),
        ("Current barebones version", app.CURRENT_BB),
        ("Config folder", str(ROOT / app.CONFIG_DIR)),
        ("App config", f"{app.CONFIG_FILE} ({_file_state(ROOT / app.CONFIG_FILE)})"),
        ("Favorites", f"{app.FAVORITES_FILE} ({_file_state(ROOT / app.FAVORITES_FILE)})"),
        ("Google credentials", f"{sheet_db.CREDENTIALS_FILE} ({_file_state(ROOT / sheet_db.CREDENTIALS_FILE)})"),
        ("Submission mode", submission_state["mode"]),
        ("Submission endpoint", "Configured" if submission_state["configured"] else "Not configured"),
        ("Submission secret", "Configured" if submission_state["has_secret"] else "Not configured"),
        ("Map cache", f"{app.JSON_FILE_NAME} ({_file_state(ROOT / app.JSON_FILE_NAME)})"),
        ("Image cache folder", str(image_folder)),
        ("Image cache used", _fmt_size(_folder_size(image_folder))),
        ("Image cache enabled", "Yes" if image_settings["enabled"] else "No"),
        ("Image cache limit", _fmt_size(image_settings["limit_bytes"])),
        ("Pending image cap", str(image_fetcher.MAX_PENDING_DOWNLOADS)),
        ("Steam 429 backoff", f"{image_fetcher.RATE_LIMIT_BACKOFF // 60} minutes"),
        ("Submissions tab", sheet_db.SUBMISSIONS_TAB),
        ("Metadata tab", sheet_db.SUBMISSION_METADATA_TAB),
    ]
    return rows


class SettingsApi:
    def save_image_cache_settings(self, enabled, limit_mb):
        try:
            limit_mb = int(limit_mb)
        except (TypeError, ValueError):
            limit_mb = image_fetcher.DEFAULT_STORAGE_LIMIT_MB

        limit_mb = max(0, min(image_fetcher.MAX_STORAGE_LIMIT_MB, limit_mb))
        config = _load_config()
        config["image_cache_enabled"] = bool(enabled)
        config["image_cache_limit_mb"] = limit_mb
        _save_config(config)
        return {
            "ok": True,
            "enabled": bool(enabled),
            "limit_mb": limit_mb,
        }

    def save_theme_audio_setting(self, enabled):
        config = _load_config()
        config["theme_audio_enabled"] = bool(enabled)
        _save_config(config)
        return {"ok": True, "enabled": bool(enabled)}


def _render_rows(rows):
    return "\n".join(
        f'<div class="row"><span class="key">{key}</span><span class="val">{value}</span></div>'
        for key, value in rows
    )


def get_html():
    image_settings = image_fetcher.get_image_cache_settings()
    config = _load_config()
    enabled_checked = "checked" if image_settings["enabled"] else ""
    audio_checked = "checked" if config.get("theme_audio_enabled", True) else ""
    current_limit = image_settings["limit_mb"]
    rows = _render_rows(_build_rows())
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Settings - UEM Database</title>
    <style>
        :root {{
            --bg: #121212; --card: #1e1e1e; --text: #e0e0e0; --dim: #aaa;
            --gold: #d4af37; --green: #5cb85c; --border: #333; --btn: #222;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: var(--bg); color: var(--text);
            font-family: 'Segoe UI', sans-serif; padding: 24px 32px;
            line-height: 1.6;
        }}
        h1 {{
            color: var(--gold); font-size: 1.55rem; text-transform: uppercase;
            letter-spacing: 2px; border-bottom: 2px solid var(--gold);
            padding-bottom: 12px; margin-bottom: 18px;
        }}
        h2 {{
            color: var(--gold); font-size: 1.05rem; margin-bottom: 10px;
            text-transform: uppercase; letter-spacing: 1px;
        }}
        p {{ color: var(--dim); margin-bottom: 12px; font-size: 0.9rem; }}
        button {{
            background: var(--btn); color: var(--gold); border: 1px solid var(--gold);
            border-radius: 6px; padding: 8px 12px; cursor: pointer; font-weight: 700;
            letter-spacing: 0.5px; text-transform: uppercase;
        }}
        button:hover {{ background: var(--gold); color: #000; }}
        input[type="range"] {{ width: 100%; accent-color: var(--gold); }}
        input[type="checkbox"] {{ width: 18px; height: 18px; accent-color: var(--gold); }}
        .section {{
            background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; padding: 16px 18px; margin-bottom: 14px;
        }}
        .setting-row {{
            display: grid; grid-template-columns: 190px 1fr; gap: 14px;
            align-items: center; padding: 10px 0;
        }}
        .setting-row label {{ color: var(--gold); font-weight: 700; }}
        .slider-head {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 6px; }}
        .slider-value {{ color: var(--green); font-weight: 700; white-space: nowrap; }}
        .status {{ margin-top: 10px; color: var(--green); min-height: 20px; font-size: 0.86rem; }}
        .hint {{ color: var(--dim); font-size: 0.82rem; margin-top: 6px; }}
        .row {{
            display: grid; grid-template-columns: 190px 1fr; gap: 14px;
            padding: 9px 0; border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }}
        .row:last-child {{ border-bottom: 0; }}
        .key {{ color: var(--gold); font-weight: 700; }}
        .val {{ color: var(--text); word-break: break-word; }}
        code {{
            background: #000; color: var(--green); padding: 1px 6px;
            border-radius: 3px; font-size: 0.85rem;
        }}
        footer {{
            margin-top: 22px; padding-top: 12px; border-top: 1px solid var(--border);
            color: var(--dim); font-size: 0.8rem; text-align: center;
        }}
    </style>
</head>
<body>
    <h1>Settings</h1>

    <div class="section">
        <h2>Steam Image Cache</h2>
        <p>Control how many Workshop thumbnails the app keeps locally. These settings are used next time the main app starts.</p>
        <div class="setting-row">
            <label for="cache-enabled">Image caching</label>
            <div>
                <input id="cache-enabled" type="checkbox" {enabled_checked}>
                <span class="hint">When off, images can still load for the current page, but they are not stored in <code>steam_images/</code>.</span>
            </div>
        </div>
        <div class="setting-row">
            <label for="cache-limit">Cache limit</label>
            <div>
                <div class="slider-head">
                    <span class="hint">0 MB to 1024 MB</span>
                    <span class="slider-value"><span id="cache-limit-value">{current_limit}</span> MB</span>
                </div>
                <input id="cache-limit" type="range" min="0" max="{image_fetcher.MAX_STORAGE_LIMIT_MB}" step="25" value="{current_limit}" oninput="updateCacheLimitLabel()">
            </div>
        </div>
        <button onclick="saveImageCacheSettings()">Save Cache Settings</button>
        <div id="cache-status" class="status"></div>
    </div>

    <div class="section">
        <h2>Theme Audio</h2>
        <p>Some themes include background audio (e.g. Dead Ops Arcade). Turn it off here if you prefer silence.</p>
        <div class="setting-row">
            <label for="theme-audio-enabled">Theme audio</label>
            <div>
                <input id="theme-audio-enabled" type="checkbox" {audio_checked}>
                <span class="hint">When off, theme music and sound effects will not play. Requires app restart.</span>
            </div>
        </div>
        <button onclick="saveThemeAudioSetting()">Save Audio Setting</button>
        <div id="theme-audio-status" class="status"></div>
    </div>

    <div class="section">
        <h2>Project State</h2>
        <p>Current app paths and runtime limits.</p>
        {rows}
    </div>

    <div class="section">
        <h2>Notes</h2>
        <p>Theme and favorites are stored in <code>config/</code>. Workshop thumbnails are cached in <code>steam_images/</code> and trimmed when the cache exceeds the configured limit.</p>
        <p>Submission metadata is kept on a separate Google Sheets tab so rows in <code>Submissions</code> stay clean to copy into the main tracker.</p>
    </div>

    <footer>UEM CLASSIFIED DATABASE V.3.3 // SETTINGS v1.0</footer>
    <script>
        function updateCacheLimitLabel() {{
            document.getElementById('cache-limit-value').textContent = document.getElementById('cache-limit').value;
        }}

        function saveImageCacheSettings() {{
            const enabled = document.getElementById('cache-enabled').checked;
            const limitMb = parseInt(document.getElementById('cache-limit').value, 10);
            const status = document.getElementById('cache-status');
            status.textContent = 'Saving...';
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.save_image_cache_settings(enabled, limitMb).then(function(result) {{
                    status.textContent = 'Saved. Restart the main app for this to affect the active image worker.';
                }});
            }} else {{
                status.textContent = 'Settings can only be saved from the desktop app.';
            }}
        }}

        function saveThemeAudioSetting() {{
            const enabled = document.getElementById('theme-audio-enabled').checked;
            const status = document.getElementById('theme-audio-status');
            status.textContent = 'Saving...';
            if (window.pywebview && window.pywebview.api) {{
                window.pywebview.api.save_theme_audio_setting(enabled).then(function(result) {{
                    status.textContent = 'Saved. Restart the main app for this to take effect.';
                }});
            }} else {{
                status.textContent = 'Settings can only be saved from the desktop app.';
            }}
        }}
    </script>
</body>
</html>
"""


def main():
    window = webview.create_window(
        "UEM Database - Settings",
        html=get_html(),
        js_api=SettingsApi(),
        width=760,
        height=760,
        background_color="#121212",
    )
    webview.start()


if __name__ == "__main__":
    main()
