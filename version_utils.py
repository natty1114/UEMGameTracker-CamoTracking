"""Version comparison and updater-launch utilities for BO3 Tracker."""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile

from app_metadata import APP_VERSION
from game_data import UPDATER_EXE_NAME


def parse_version_parts(value):
    cleaned = str(value or "").strip().lower().lstrip("v")
    parts = []
    for chunk in cleaned.replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return parts or [0]


def is_version_newer(remote_version, local_version=APP_VERSION):
    remote = parse_version_parts(remote_version)
    local = parse_version_parts(local_version)
    width = max(len(remote), len(local))
    remote += [0] * (width - len(remote))
    local += [0] * (width - len(local))
    return remote > local


def extract_updater_from_release(download_url):
    if not download_url:
        return None
    temp_dir = tempfile.mkdtemp(prefix="bo3tracker_updater_launch_")
    package_path = os.path.join(temp_dir, "release.zip")
    request = urllib.request.Request(download_url, headers={"User-Agent": f"BO3Tracker/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        with open(package_path, "wb") as handle:
            shutil.copyfileobj(response, handle)

    with zipfile.ZipFile(package_path, "r") as archive:
        updater_entry = None
        for entry in archive.infolist():
            if entry.filename.replace("\\", "/").split("/")[-1] == UPDATER_EXE_NAME:
                updater_entry = entry
                break
        if updater_entry is None:
            return None
        temp_updater_path = os.path.join(temp_dir, UPDATER_EXE_NAME)
        with archive.open(updater_entry) as source, open(temp_updater_path, "wb") as target:
            shutil.copyfileobj(source, target)
        return temp_updater_path


def get_updater_launch_path(base_path, download_url=None):
    if download_url:
        try:
            release_updater = extract_updater_from_release(download_url)
            if release_updater and os.path.exists(release_updater):
                return release_updater
        except Exception:
            pass

    source_path = os.path.join(base_path, UPDATER_EXE_NAME)
    if not os.path.exists(source_path):
        return None
    temp_name = f"BO3Updater_launch_{os.getpid()}_{int(time.time())}.exe"
    temp_path = os.path.join(tempfile.gettempdir(), temp_name)
    shutil.copy2(source_path, temp_path)
    return temp_path
