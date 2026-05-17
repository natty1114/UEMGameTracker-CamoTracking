import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from tkinter import Tk, Label, Button, StringVar, Frame, messagebox
from tkinter import ttk

from app_metadata import APP_VERSION

BACKUP_ROOT_NAME = "Backups"
UPDATE_BACKUP_PREFIX = "app_update_"
MAX_UPDATE_BACKUPS = 5
UI_BG = "#0b0c10"
UI_PANEL = "#101820"
UI_BORDER = "#66fcf1"
UI_TEXT = "#ffffff"
UI_MUTED = "#9aa5aa"
UI_ACCENT = "#ff9d00"
UI_BUTTON_BG = "#16252a"
UI_BUTTON_ACTIVE = "#23393f"

MANAGED_PATHS = [
    "BO3Tracker.exe",
    "BO3Updater.exe",
    "style.css",
    "setup.css",
    "custom_camos.json",
    "xp_requirements.csv",
    "perk icons",
    "camoimages",
    "callingcards",
    "emblems",
    "themes",
    "app_version.json",
    "rank icons",
    "aat icons",
    "chart.js",
    "default_tactical_background.jpg",
    "default_tactical_background.png",
    "scripts",
    "local map compatiblityu",
    "locales"
]

PRESERVED_PATHS = {
    "config",
    "config.json",
    "best_matches.json",
    "challenges.json",
    "unlocked_rewards.json",
    "damage_history.json",
    "damage_log.json",
    "favorites.json",
    "global_stats_state.json",
    "match_xp_cache.json",
    "xpm_graph_memory.json",
    "points_history.json",
    "workshop_image_cache",
}


def parse_args():
    parser = argparse.ArgumentParser(description="BO3 Tracker optional updater")
    parser.add_argument("--app-pid", type=int, default=0)
    parser.add_argument("--install-dir", required=True)
    parser.add_argument("--exe-name", default="BO3Tracker.exe")
    parser.add_argument("--download-url")
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--backup-dir")
    return parser.parse_args()


def fail(message):
    raise RuntimeError(message)


def wait_for_process(pid, timeout=30):
    if pid <= 0:
        return
    if os.name == "nt":
        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return
        try:
            wait_ms = max(int(timeout * 1000), 1)
            ctypes.windll.kernel32.WaitForSingleObject(handle, wait_ms)
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        return

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.5)


def download_file(url, target, status, progress_bar):
    status.set("Downloading update package...")
    request = urllib.request.Request(url, headers={"User-Agent": f"BO3Tracker-Updater/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        total = int(response.headers.get("Content-Length", 0))
        progress_bar["maximum"] = total if total > 0 else 100
        progress_bar["value"] = 0
        chunk_size = 8192
        downloaded = 0
        with open(target, "wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    progress_bar["value"] = downloaded
                else:
                    progress_bar["value"] = 50
                status.set(f"Downloading... {downloaded // 1024} KB downloaded")
    if total <= 0:
        progress_bar["value"] = progress_bar["maximum"]


def first_payload_root(extract_dir):
    children = [child for child in extract_dir.iterdir() if child.name != "__MACOSX"]
    if len(children) == 1 and children[0].is_dir():
        nested = children[0]
        if (nested / "BO3Tracker.exe").exists() or (nested / "style.css").exists():
            return nested
    return extract_dir


def copy_path(source, target):
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def safe_name(value):
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(value or "unknown"))


def backup_root(install_dir):
    return install_dir / BACKUP_ROOT_NAME


def list_update_backups(install_dir):
    root = backup_root(install_dir)
    if not root.exists():
        return []
    return sorted(
        [path for path in root.iterdir() if path.is_dir() and path.name.startswith(UPDATE_BACKUP_PREFIX)],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def latest_update_backup(install_dir):
    backups = list_update_backups(install_dir)
    return backups[0] if backups else None


def prune_old_backups(install_dir):
    for old_backup in list_update_backups(install_dir)[MAX_UPDATE_BACKUPS:]:
        shutil.rmtree(old_backup, ignore_errors=True)


def create_update_backup(install_dir, target_version, status):
    status.set("Backing up current version...")
    root = backup_root(install_dir)
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = root / f"{UPDATE_BACKUP_PREFIX}{stamp}_to_{safe_name(target_version)}"
    backup_dir.mkdir(parents=True, exist_ok=False)

    copied = []
    for name in MANAGED_PATHS:
        source = install_dir / name
        if source.exists():
            copy_path(source, backup_dir / name)
            copied.append(name)

    metadata = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "target_version": target_version,
        "managed_paths": copied,
    }
    (backup_dir / "rollback_info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    prune_old_backups(install_dir)
    return backup_dir


def install_update(payload_dir, install_dir, status):
    status.set("Installing update...")
    for name in MANAGED_PATHS:
        source = payload_dir / name
        if not source.exists():
            continue
        if name in PRESERVED_PATHS:
            continue
        copy_path(source, install_dir / name)


def restore_backup(backup_dir, install_dir, status):
    if not backup_dir or not backup_dir.exists():
        fail("No update backup was found to restore.")

    status.set("Restoring previous version...")
    for name in MANAGED_PATHS:
        source = backup_dir / name
        if source.exists():
            copy_path(source, install_dir / name)


def restart_app(install_dir, exe_name):
    exe_path = install_dir / exe_name
    if exe_path.exists():
        subprocess.Popen([str(exe_path)], cwd=str(install_dir), close_fds=True)


def style_button(button, primary=False):
    button.configure(
        bg=UI_BORDER if primary else UI_BUTTON_BG,
        fg="#000000" if primary else UI_TEXT,
        activebackground=UI_ACCENT if primary else UI_BUTTON_ACTIVE,
        activeforeground="#000000" if primary else UI_TEXT,
        bd=1,
        relief="solid",
        highlightthickness=0,
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
    )


def main():
    args = parse_args()
    install_dir = Path(args.install_dir).resolve()
    if not install_dir.exists():
        raise SystemExit(f"Install folder not found: {install_dir}")
    if not args.rollback and not args.download_url:
        raise SystemExit("Download URL is required unless rollback mode is used.")

    root = Tk()
    root.title("BO3 Tracker Updater")
    root.geometry("460x230")
    root.resizable(False, False)
    root.configure(bg=UI_BG)
    mode_title = "Rollback BO3 Tracker" if args.rollback else f"BO3 Tracker {args.version}"
    status = StringVar(value="Ready to restore the previous version." if args.rollback else f"Ready to install BO3 Tracker {args.version}.")

    panel = Frame(root, bg=UI_PANEL, bd=1, relief="solid", highlightbackground=UI_BORDER, highlightcolor=UI_BORDER, highlightthickness=1)
    panel.pack(fill="both", expand=True, padx=14, pady=14)

    Label(panel, text=mode_title.upper(), font=("Segoe UI", 13, "bold"), bg=UI_PANEL, fg=UI_BORDER).pack(pady=(18, 4))
    Label(panel, text="BO3 Tracker update utility", font=("Segoe UI", 8), bg=UI_PANEL, fg=UI_ACCENT).pack(pady=(0, 10))
    Label(panel, textvariable=status, wraplength=380, justify="center", font=("Segoe UI", 9), bg=UI_PANEL, fg=UI_MUTED).pack(pady=(0, 6))
    progress_bar = ttk.Progressbar(panel, orient="horizontal", length=380, mode="determinate")
    progress_bar.pack(pady=(0, 10))

    def run_update():
        try:
            install_button.config(state="disabled")
            if args.rollback:
                backup_dir = Path(args.backup_dir).resolve() if args.backup_dir else latest_update_backup(install_dir)
                status.set("Waiting for BO3 Tracker to close...")
                root.update_idletasks()
                wait_for_process(args.app_pid)
                restore_backup(backup_dir, install_dir, status)
                status.set("Previous version restored. Restarting BO3 Tracker...")
                root.update_idletasks()
                restart_app(install_dir, args.exe_name)
                root.after(900, root.destroy)
                return

            with tempfile.TemporaryDirectory(prefix="bo3tracker_update_") as tmp:
                tmp_dir = Path(tmp)
                zip_path = tmp_dir / "update.zip"
                extract_dir = tmp_dir / "payload"
                download_file(args.download_url, zip_path, status, progress_bar)
                progress_bar["value"] = progress_bar["maximum"]
                status.set("Unpacking update...")
                with zipfile.ZipFile(zip_path, "r") as archive:
                    archive.extractall(extract_dir)
                payload_dir = first_payload_root(extract_dir)
                status.set("Waiting for BO3 Tracker to close...")
                root.update_idletasks()
                wait_for_process(args.app_pid)
                create_update_backup(install_dir, args.version, status)
                install_update(payload_dir, install_dir, status)
            status.set("Update installed. Restarting BO3 Tracker...")
            root.update_idletasks()
            restart_app(install_dir, args.exe_name)
            root.after(900, root.destroy)
        except Exception as exc:
            install_button.config(state="normal")
            status.set("Update failed.")
            messagebox.showerror("BO3 Tracker Updater", str(exc))

    def cancel():
        root.destroy()

    button_row = Frame(panel, bg=UI_PANEL)
    button_row.pack(pady=(0, 14))
    install_button = Button(button_row, text="Restore Backup" if args.rollback else "Install Update", command=run_update, width=18)
    install_button.pack(side="left", padx=6)
    style_button(install_button, primary=True)
    cancel_button = Button(button_row, text="Cancel", command=cancel, width=12)
    cancel_button.pack(side="left", padx=6)
    style_button(cancel_button)
    root.mainloop()


if __name__ == "__main__":
    main()
