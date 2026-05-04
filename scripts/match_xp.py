import os
import csv
import json
import threading

class MatchXPTracker:
    def __init__(self, csv_filename="xp_requirements.csv", cache_filename="match_xp_cache.json"):
        self.level_xp_required = {}
        # Memory Format: { game_id: { player_id: { prestige, level, last_cumulative_xp, total_match_xp, start_xp_required } } }
        self.match_data = {} 
        self.last_debug = {}
        self.lock = threading.Lock()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = os.path.join(base_dir, csv_filename)
        self.cache_path = os.path.join(base_dir, cache_filename)
        
        self.load_csv()
        self.load_cache()

    def load_csv(self):
        if not os.path.exists(self.csv_path): return
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 4:
                        try:
                            level = int(row[1])
                            xp_req = int(row[2])
                            
                            # Only add the level if we haven't mapped it yet!
                            # This protects against duplicates and the 0 XP reset row.
                            if level not in self.level_xp_required:
                                self.level_xp_required[level] = xp_req
                                
                        except ValueError:
                            # Safely skip any rows that don't have standard numbers
                            continue
        except Exception as e:
            print(f"Failed to read CSV: {e}")

    def get_xp_required(self, level):
        return self.level_xp_required.get(level, 0)

    def _calculate_level_rollover_xp(self, previous_level, previous_xp, current_level, current_xp):
        if previous_level is None or current_level <= previous_level:
            return 0

        previous_level_required = self.get_xp_required(previous_level)
        if previous_level_required <= 0:
            return 0

        xp_gained = max(previous_level_required - previous_xp, 0)

        for skipped_level in range(previous_level + 1, current_level):
            xp_gained += max(self.get_xp_required(skipped_level), 0)

        xp_gained += current_xp
        return xp_gained

    def _get_level_rollover_debug(self, previous_level, previous_xp, current_level, current_xp):
        if previous_level is None or current_level <= previous_level:
            return None

        previous_level_required = self.get_xp_required(previous_level)
        if previous_level_required <= 0:
            return None

        remaining_previous_level = max(previous_level_required - previous_xp, 0)
        skipped_level_xp = 0
        for skipped_level in range(previous_level + 1, current_level):
            skipped_level_xp += max(self.get_xp_required(skipped_level), 0)

        return {
            "previous_level_required": previous_level_required,
            "remaining_previous_level": remaining_previous_level,
            "skipped_level_xp": skipped_level_xp,
            "current_level_progress": current_xp
        }

    def load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    self.match_data = json.load(f)
            except Exception:
                pass

    def save_cache(self):
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.match_data, f)
        except Exception:
            pass

    def _set_debug_snapshot(
        self, game_id, player_id, current_prestige, current_level, current_xp,
        previous_prestige, previous_level, previous_xp, xp_gained, total_match_xp,
        xp_required, rollover_debug=None
    ):
        if game_id not in self.last_debug:
            self.last_debug[game_id] = {}

        self.last_debug[game_id][player_id] = {
            "game_id": game_id,
            "player_id": player_id,
            "prestige": current_prestige,
            "level": current_level,
            "current_xp": current_xp,
            "previous_prestige": previous_prestige,
            "previous_level": previous_level,
            "previous_xp": previous_xp,
            "tick_xp": xp_gained,
            "total_match_xp": total_match_xp,
            "xp_required": xp_required,
            "rollover_debug": rollover_debug
        }

    def get_last_debug_snapshot(self, game_id, player_id):
        with self.lock:
            snapshot = self.last_debug.get(game_id, {}).get(player_id)
            if not snapshot:
                return None
            return dict(snapshot)

    def calculate_match_xp(self, game_id, player_id, current_prestige, current_level, current_xp):
        with self.lock:
            cache_needs_saving = False
            
            # Clean up old games from cache
            for old_game_id in list(self.match_data.keys()):
                if old_game_id != game_id:
                    del self.match_data[old_game_id]
                    cache_needs_saving = True
                    
            if game_id not in self.match_data:
                self.match_data[game_id] = {}
                cache_needs_saving = True
                
            xp_required = self.get_xp_required(current_level)
                
            # INITIALIZE NEW PLAYER
            if player_id not in self.match_data[game_id]:
                self.match_data[game_id][player_id] = {
                    "prestige": current_prestige,
                    "level": current_level,
                    "last_cumulative_xp": current_xp,
                    "total_match_xp": 0,
                    "start_xp_required": xp_required
                }
                self._set_debug_snapshot(
                    game_id, player_id, current_prestige, current_level, current_xp,
                    None, None, None, 0, 0, xp_required
                )
                if cache_needs_saving: 
                    self.save_cache()
                return 0

            p_data = self.match_data[game_id][player_id]
            previous_prestige = p_data.get("prestige")
            previous_level = p_data.get("level", current_level)
            previous_xp = p_data.get("last_cumulative_xp", 0)
            previous_level_required = p_data.get("start_xp_required", 0)
            if previous_level_required <= 0:
                previous_level_required = self.get_xp_required(previous_level)
            xp_gained = 0
            rollover_debug = None
            
            # Scenario A: Same Prestige
            if current_prestige == p_data["prestige"]:
                if current_level > previous_level:
                    xp_gained = self._calculate_level_rollover_xp(
                        previous_level, previous_xp, current_level, current_xp
                    )
                    rollover_debug = self._get_level_rollover_debug(
                        previous_level, previous_xp, current_level, current_xp
                    )
                else:
                    xp_gained = current_xp - previous_xp
                
                if xp_gained > 0:
                    p_data["total_match_xp"] += xp_gained
                else:
                    xp_gained = 0
                    
            # Scenario B: Prestige Increased Mid-Match
            elif current_prestige > p_data["prestige"]:
                
                if previous_xp > current_xp:
                    # Add remaining XP to finish the last level before prestige
                    remaining_to_prestige = previous_level_required - previous_xp
                    xp_gained = remaining_to_prestige + current_xp
                    
                    if xp_gained > 0:
                        p_data["total_match_xp"] += xp_gained
                    else:
                        xp_gained = 0
                else:
                    xp_gained = current_xp - previous_xp
                    if xp_gained > 0:
                        p_data["total_match_xp"] += xp_gained
                    else:
                        xp_gained = 0

            # Update tracked states for the next tick
            if (
                current_xp != p_data["last_cumulative_xp"]
                or current_prestige != p_data["prestige"]
                or current_level != p_data.get("level")
            ):
                p_data["last_cumulative_xp"] = current_xp
                p_data["prestige"] = current_prestige
                p_data["level"] = current_level
                p_data["start_xp_required"] = xp_required
                self.save_cache()

            self._set_debug_snapshot(
                game_id, player_id, current_prestige, current_level, current_xp,
                previous_prestige, previous_level, previous_xp, xp_gained,
                p_data["total_match_xp"], xp_required, rollover_debug
            )
                
            return p_data["total_match_xp"]

# Singleton instance to be imported by bo3tracker.py
xp_tracker_instance = MatchXPTracker()
