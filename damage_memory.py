"""Multi-player damage memory system for tracking 32-bit integer overflow."""

import threading

from app_paths import get_runtime_path
from file_utils import load_json, save_json
from game_data import DAMAGE_HISTORY_FILE


class DamageMemory:
    def __init__(self):
        self.file_path = get_runtime_path(DAMAGE_HISTORY_FILE)
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
