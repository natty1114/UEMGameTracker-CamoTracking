"""Shared filesystem paths and runtime-file migration for BO3 Tracker."""

import os
import shutil
import sys


CONFIG_DIR_NAME = "config"

RUNTIME_FILENAMES = {
    "config.json",
    "best_matches.json",
    "challenges.json",
    "unlocked_rewards.json",
    "damage_history.json",
    "damage_log.json",
    "favorites.json",
    "global_stats_state.json",
    "match_xp_cache.json",
    "map_challenges.json",
    "points_history.json",
    "remote_management_cache.json",
    "xpm_graph_memory.json",
    "map_index_cache.json",
    "map_detail_summary.json",
}

RUNTIME_DIRNAMES = {
    "workshop_image_cache",
}


def get_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_config_dir():
    config_dir = os.path.join(get_base_path(), CONFIG_DIR_NAME)
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def _move_if_unclaimed(old_path, new_path):
    if not os.path.exists(old_path) or os.path.exists(new_path):
        return False

    base_path = os.path.normcase(os.path.abspath(get_base_path()))
    old_abs = os.path.normcase(os.path.abspath(old_path))
    new_abs = os.path.normcase(os.path.abspath(new_path))
    if not old_abs.startswith(base_path + os.sep) or not new_abs.startswith(base_path + os.sep):
        return False

    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    shutil.move(old_path, new_path)
    return True


def migrate_runtime_path(name):
    old_path = os.path.join(get_base_path(), name)
    new_path = os.path.join(get_config_dir(), name)
    _move_if_unclaimed(old_path, new_path)
    return new_path


def get_runtime_path(filename):
    return migrate_runtime_path(filename)


def get_runtime_dir(dirname):
    return migrate_runtime_path(dirname)


def migrate_all_runtime_paths():
    moved = []
    for filename in sorted(RUNTIME_FILENAMES):
        old_path = os.path.join(get_base_path(), filename)
        new_path = os.path.join(get_config_dir(), filename)
        if _move_if_unclaimed(old_path, new_path):
            moved.append(filename)

    for dirname in sorted(RUNTIME_DIRNAMES):
        old_path = os.path.join(get_base_path(), dirname)
        new_path = os.path.join(get_config_dir(), dirname)
        if _move_if_unclaimed(old_path, new_path):
            moved.append(dirname)

    return moved
