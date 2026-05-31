import json
import os
import subprocess
import sys
import threading
import time
import urllib.request

_bt = lambda: sys.modules["bo3tracker"]
from app_paths import get_base_path, get_runtime_path
from app_metadata import APP_VERSION, GLOBAL_STATS_PROMPT_VERSION
from discord_presence import discord_presence
from game_data import (
    DEFAULT_DISCORD_APPLICATION_ID,
    GITHUB_RELEASES_API,
    UEM_WORKSHOP_URL,
    TRACKER_GITHUB_URL,
    UPDATER_EXE_NAME,
)
from remote_management_client import fetch_remote_management
from version_utils import parse_version_parts, is_version_newer, get_updater_launch_path, count_newer_release_versions
from file_utils import load_json


class NetworkAPI:
    # --- Updates ---
    def check_for_updates(self):
        stale_update_threshold = 4
        try:
            request = urllib.request.Request(
                GITHUB_RELEASES_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"BO3Tracker/{APP_VERSION}",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"success": False, "update_available": False, "msg": f"Update check failed: {exc}"}

        tag = str(release.get("tag_name") or "").strip()
        version = tag.lstrip("vV") or str(release.get("name") or "").strip()
        assets = release.get("assets") or []
        zip_asset = None
        for asset in assets:
            name = str(asset.get("name") or "")
            if name.lower().endswith(".zip"):
                zip_asset = asset
                break

        if not zip_asset:
            return {
                "success": False,
                "update_available": False,
                "version": version,
                "msg": "Latest GitHub release has no zip asset to install.",
            }

        if not is_version_newer(version):
            return {
                "success": True,
                "update_available": False,
                "version": version,
                "newer_release_count": 0,
                "stale_update_threshold": stale_update_threshold,
                "stale_update_notice": False,
                "msg": f"You are on the latest version ({APP_VERSION}).",
            }

        newer_release_count = 1
        try:
            releases_url = GITHUB_RELEASES_API.rsplit("/", 1)[0] + "?per_page=30"
            request = urllib.request.Request(
                releases_url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"BO3Tracker/{APP_VERSION}",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                releases = json.loads(response.read().decode("utf-8"))
            newer_release_count = max(
                1,
                count_newer_release_versions(releases, APP_VERSION),
            )
        except Exception:
            newer_release_count = 1

        return {
            "success": True,
            "update_available": True,
            "version": version,
            "tag": tag,
            "name": release.get("name") or f"BO3 Tracker {version}",
            "notes": release.get("body") or "",
            "download_url": zip_asset.get("browser_download_url"),
            "asset_name": zip_asset.get("name"),
            "html_url": release.get("html_url"),
            "newer_release_count": newer_release_count,
            "stale_update_threshold": stale_update_threshold,
            "stale_update_notice": newer_release_count >= stale_update_threshold,
        }

    def get_latest_changelog(self):
        try:
            request = urllib.request.Request(
                GITHUB_RELEASES_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": f"BO3Tracker/{APP_VERSION}",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                release = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return {"success": False, "msg": f"Changelog check failed: {exc}"}

        tag = str(release.get("tag_name") or "").strip()
        version = tag.lstrip("vV") or str(release.get("name") or "").strip()
        remote = parse_version_parts(version)
        local = parse_version_parts(APP_VERSION)
        width = max(len(remote), len(local))
        remote += [0] * (width - len(remote))
        local += [0] * (width - len(local))
        return {
            "success": True,
            "version": version,
            "tag": tag,
            "name": release.get("name") or f"BO3 Tracker {version}",
            "notes": release.get("body") or "",
            "html_url": release.get("html_url"),
            "is_current": remote == local,
            "is_older_than_app": remote < local,
        }

    def launch_updater(self, update_info):
        if not isinstance(update_info, dict):
            return {"success": False, "msg": "No update information was provided."}
        download_url = update_info.get("download_url")
        version = update_info.get("version")
        if not download_url or not version:
            return {"success": False, "msg": "Update information is missing a download URL or version."}

        base_path = get_base_path()
        updater_path = os.path.join(base_path, UPDATER_EXE_NAME)
        if not os.path.exists(updater_path):
            return {"success": False, "msg": f"{UPDATER_EXE_NAME} was not found beside the app. Install the latest release manually once to enable automatic updates."}

        try:
            launch_path = get_updater_launch_path(base_path, download_url)
            if not launch_path:
                return {"success": False, "msg": f"{UPDATER_EXE_NAME} was not found beside the app."}
            subprocess.Popen([
                launch_path,
                "--app-pid", str(os.getpid()),
                "--install-dir", base_path,
                "--exe-name", os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "BO3Tracker.exe",
                "--download-url", str(download_url),
                "--version", str(version),
            ], cwd=base_path, close_fds=True)
            threading.Timer(0.5, _bt().window.destroy).start()
            return {"success": True, "msg": "Updater started. BO3 Tracker will close and restart after the update."}
        except Exception as exc:
            return {"success": False, "msg": f"Updater could not be started: {exc}"}

    def rollback_last_update(self):
        base_path = get_base_path()
        updater_path = os.path.join(base_path, UPDATER_EXE_NAME)
        backups_root = os.path.join(base_path, "Backups")

        if not os.path.exists(updater_path):
            return {"success": False, "msg": f"{UPDATER_EXE_NAME} was not found beside the app."}
        if not os.path.isdir(backups_root):
            return {"success": False, "msg": "No update backups were found."}

        try:
            backups = [
                os.path.join(backups_root, name)
                for name in os.listdir(backups_root)
                if name.startswith("app_update_") and os.path.isdir(os.path.join(backups_root, name))
            ]
            backups.sort(key=os.path.getmtime, reverse=True)
            if not backups:
                return {"success": False, "msg": "No update backups were found."}

            launch_path = get_updater_launch_path(base_path)
            if not launch_path:
                return {"success": False, "msg": f"{UPDATER_EXE_NAME} was not found beside the app."}
            subprocess.Popen([
                launch_path,
                "--rollback",
                "--app-pid", str(os.getpid()),
                "--install-dir", base_path,
                "--exe-name", os.path.basename(sys.executable) if getattr(sys, "frozen", False) else "BO3Tracker.exe",
                "--backup-dir", backups[0],
            ], cwd=base_path, close_fds=True)
            threading.Timer(0.5, _bt().window.destroy).start()
            return {"success": True, "msg": "Rollback started. BO3 Tracker will close and restart after restore."}
        except Exception as exc:
            return {"success": False, "msg": f"Rollback could not be started: {exc}"}

    # --- Discord Presence ---
    def get_discord_presence_settings(self):
        image_source = str(_bt().app_config.get("discord_presence_image_source", "workshop") or "workshop").strip().lower()
        if image_source not in ("workshop", "emblem"):
            image_source = "workshop"
        return {
            "enabled": bool(_bt().app_config.get("discord_presence_enabled", False)),
            "client_id": _bt().get_discord_presence_client_id(),
            "large_image": str(_bt().app_config.get("discord_presence_large_image", "") or ""),
            "image_source": image_source,
            "status": str(_bt().app_config.get("discord_presence_last_status", "") or ""),
            "diagnostics": discord_presence.get_connection_diagnostics(),
        }

    def save_discord_presence_settings(self, enabled, client_id, large_image="", image_source=None):
        if image_source is not None:
            image_source = str(image_source or "workshop").strip().lower()
            if image_source not in ("workshop", "emblem"):
                image_source = "workshop"
            _bt().app_config["discord_presence_image_source"] = image_source
        _bt().app_config["discord_presence_enabled"] = bool(enabled)
        _bt().app_config["discord_presence_client_id"] = str(client_id or "").strip()
        _bt().app_config["discord_presence_large_image"] = str(large_image or "").strip()
        _bt().save_app_config()
        _bt().configure_discord_presence()

        if not _bt().app_config["discord_presence_enabled"]:
            _bt().clear_discord_presence()
            _bt().app_config["discord_presence_last_status"] = "Discord Rich Presence disabled."
            _bt().save_app_config()
            return {"success": True, "msg": _bt().app_config["discord_presence_last_status"]}

        if not _bt().app_config["discord_presence_client_id"]:
            _bt().app_config["discord_presence_last_status"] = "Enter a Discord application client ID first."
            _bt().save_app_config()
            return {"success": False, "msg": _bt().app_config["discord_presence_last_status"]}

        current_data = _bt().get_live_game_data()
        if current_data:
            try:
                ok = _bt().update_discord_presence_from_game(current_data, force=True)
                msg = _bt().app_config.get("discord_presence_last_status") or ("Connected to Discord." if ok else discord_presence.last_error)
                return {"success": bool(ok), "msg": msg}
            except Exception as exc:
                _bt().app_config["discord_presence_last_status"] = f"Discord update failed: {exc}"
                _bt().save_app_config()
                return {"success": False, "msg": _bt().app_config["discord_presence_last_status"]}

        _bt().app_config["discord_presence_last_status"] = "Discord Rich Presence enabled. Waiting for live game data."
        _bt().save_app_config()
        return {"success": True, "msg": _bt().app_config["discord_presence_last_status"]}

    def get_t7_discord_presence_settings(self):
        path, data = _bt().load_t7_config()
        if not path:
            return {
                "success": False,
                "enabled": None,
                "path": "",
                "msg": "Live path is not configured, so t7.json could not be located.",
            }
        if data is None:
            return {
                "success": False,
                "enabled": None,
                "path": path,
                "msg": "t7.json could not be read.",
            }
        return {
            "success": True,
            "enabled": bool(data.get("discord_enabled", False)),
            "path": path,
            "msg": "UEM/T7 Discord presence is enabled." if data.get("discord_enabled", False) else "UEM/T7 Discord presence is disabled.",
        }

    def set_t7_discord_presence(self, enabled):
        path, data = _bt().load_t7_config()
        if not path:
            return {"success": False, "enabled": None, "msg": "Live path is not configured, so t7.json could not be located."}
        if data is None:
            return {"success": False, "enabled": None, "msg": f"t7.json could not be read: {path}"}
        data["discord_enabled"] = bool(enabled)
        try:
            _bt().save_json(path, data)
        except Exception as exc:
            return {"success": False, "enabled": None, "msg": f"Could not update t7.json: {exc}"}
        msg = "UEM/T7 Discord presence enabled. Restart BO3/UEM for it to take effect." if enabled else "UEM/T7 Discord presence disabled. Restart BO3/UEM for it to take effect."
        return {"success": True, "enabled": bool(enabled), "msg": msg}

    # --- Global Stats ---
    def set_global_stats_opt_in(self, enabled):
        management_message = _bt().get_global_stats_management_message()
        if enabled and management_message:
            return {"success": False, "msg": management_message}
        _bt().app_config['global_stats_enabled'] = bool(enabled)
        _bt().app_config['global_stats_prompt_version'] = GLOBAL_STATS_PROMPT_VERSION
        _bt().save_app_config()
        if enabled:
            scheduled = _bt().schedule_global_stats_sync("opt-in", force=True)
            if scheduled:
                return {"success": True, "msg": "Anonymous global stats enabled. Sync started in the background."}
            return {"success": True, "msg": "Anonymous global stats enabled. Sync will run when a history folder is available."}
        return {"success": True, "msg": "Anonymous global stats disabled."}

    def sync_global_stats_now(self):
        management_message = _bt().get_global_stats_management_message()
        if management_message:
            return {"success": False, "msg": management_message}
        if not _bt().is_global_stats_enabled():
            return {"success": False, "msg": "Enable anonymous global stats before syncing."}
        scheduled = _bt().schedule_global_stats_sync("manual", force=True)
        if scheduled:
            return {"success": True, "msg": "Global stats sync started in the background."}
        msg = _bt().app_config.get('global_stats_last_message') or "Sync is already running or history folder is unavailable."
        return {"success": False, "msg": msg}

    # --- Remote Management ---
    def refresh_remote_management_api(self):
        result = _bt().refresh_remote_management()
        applied = _bt().apply_remote_management()
        return {
            "success": bool(result.get("ok", False)),
            "source": result.get("source", ""),
            "version": str((result.get("management") or {}).get("version", "")),
            "challenges_applied": bool(applied),
            "error": result.get("error", ""),
        }
