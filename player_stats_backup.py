"""Manual UEM player stats backup helpers."""

import os
import time
import zipfile
from pathlib import Path

STAT_FILENAMES = {f"stats_zm_{i}.cgp" for i in range(5)}


def get_players_dir(live_path):
    players_dir = os.path.dirname(live_path)

    path_obj = Path(live_path)
    for parent in list(path_obj.parents):
        if parent.name.lower() == "players":
            players_dir = str(parent)
            break

    return players_dir


def find_player_stats_files(live_path):
    players_dir = get_players_dir(live_path)
    files_to_backup = []

    for fname in sorted(STAT_FILENAMES):
        fpath = os.path.join(players_dir, fname)
        if os.path.exists(fpath):
            files_to_backup.append(fpath)

    return players_dir, files_to_backup


def normalize_backup_path(save_path):
    save_path = str(save_path)
    if not save_path.lower().endswith(".zip"):
        save_path += ".zip"
    return save_path


def create_player_stats_backup(files_to_backup, save_path):
    save_path = normalize_backup_path(save_path)

    with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fpath in files_to_backup:
            zipf.write(fpath, os.path.basename(fpath))

    return save_path


def _stats_members(zip_path):
    members = []
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for info in zipf.infolist():
            if info.is_dir():
                continue
            fname = os.path.basename(info.filename.replace("\\", "/"))
            if fname in STAT_FILENAMES:
                members.append((info, fname))
    return members


def restore_player_stats_backup(zip_path, live_path):
    if not zip_path or not zipfile.is_zipfile(zip_path):
        raise ValueError("Selected file is not a valid zip archive.")

    players_dir = get_players_dir(live_path)
    if not players_dir or not os.path.isdir(players_dir):
        raise ValueError(f"Players folder could not be found ({players_dir}).")

    members = _stats_members(zip_path)
    if not members:
        raise ValueError("No stats_zm_*.cgp files were found in the selected backup.")

    existing_files = [
        os.path.join(players_dir, fname)
        for _, fname in members
        if os.path.exists(os.path.join(players_dir, fname))
    ]
    safety_backup = ""
    if existing_files:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safety_backup = os.path.join(players_dir, f"uem_stats_before_restore_{timestamp}.zip")
        create_player_stats_backup(existing_files, safety_backup)

    restored = []
    with zipfile.ZipFile(zip_path, "r") as zipf:
        for info, fname in members:
            target = os.path.abspath(os.path.join(players_dir, fname))
            with zipf.open(info, "r") as src, open(target, "wb") as dst:
                dst.write(src.read())
            restored.append(target)

    return {
        "players_dir": players_dir,
        "restored": restored,
        "safety_backup": safety_backup,
    }
