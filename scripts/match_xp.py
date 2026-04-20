import os
import csv
import json
import threading

class MatchXPTracker:
    def __init__(self, csv_filename="xp_requirements.csv", cache_filename="match_xp_cache.json"):
        self.level_xp_required = {}
        # Memory Format: { game_id: { player_id: { prestige, last_cumulative_xp, total_match_xp, start_xp_required } } }
        self.match_data = {} 
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
                    if len(row) >= 2:
                        self.level_xp_required[int(row[0])] = int(row[1])
        except Exception:
            pass

    def get_xp_required(self, level):
        return self.level_xp_required.get(level, 0)

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
                    "last_cumulative_xp": current_xp,
                    "total_match_xp": 0,
                    "start_xp_required": xp_required
                }
                if cache_needs_saving: 
                    self.save_cache()
                return 0

            p_data = self.match_data[game_id][player_id]
            
            # === EXACT LOGIC PORTED FROM XPTRACKER.PY ===
            
            # Scenario A: Same Prestige
            if current_prestige == p_data["prestige"]:
                xp_gained = current_xp - p_data["last_cumulative_xp"]
                
                if xp_gained > 0:
                    p_data["total_match_xp"] += xp_gained
                    
            # Scenario B: Prestige Increased Mid-Match
            elif current_prestige > p_data["prestige"]:
                
                if p_data["last_cumulative_xp"] > current_xp:
                    # Add remaining XP to finish the last level before prestige
                    remaining_to_prestige = p_data["start_xp_required"] - p_data["last_cumulative_xp"]
                    xp_gained = remaining_to_prestige + current_xp
                    
                    if xp_gained > 0:
                        p_data["total_match_xp"] += xp_gained
                else:
                    xp_gained = current_xp - p_data["last_cumulative_xp"]
                    if xp_gained > 0:
                        p_data["total_match_xp"] += xp_gained

            # Update tracked states for the next tick
            if current_xp != p_data["last_cumulative_xp"] or current_prestige != p_data["prestige"]:
                p_data["last_cumulative_xp"] = current_xp
                p_data["prestige"] = current_prestige
                self.save_cache()
                
            return p_data["total_match_xp"]

# Singleton instance to be imported by bo3tracker.py
xp_tracker_instance = MatchXPTracker()