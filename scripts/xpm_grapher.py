import json
import os
import sys

# Helper to get the correct path whether running as a .py script or compiled .exe
def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class XPMGrapher:
    def __init__(self):
        # Define where the graph memory file will be saved
        self.memory_file = os.path.join(get_base_path(), "xpm_graph_memory.json")
        # Load existing memory from previous sessions, or start fresh
        self.live_history = self._load_memory()

    def _load_memory(self):
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Graph memory load error: {e}")
        return {}

    def _save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.live_history, f, indent=4)
        except Exception as e:
            print(f"Graph memory save error: {e}")

    def update_live_data(self, game_id, player_id, current_round, current_time, match_xp, zpm=0):
        # Initialize memory if missing
        if game_id not in self.live_history:
            self.live_history[game_id] = {}
        if player_id not in self.live_history[game_id]:
            self.live_history[game_id][player_id] = {}
            
        r_str = str(current_round)
        
        # Continuously overwrite the current round with the latest stats.
        self.live_history[game_id][player_id][r_str] = {
            "xp": match_xp,
            "time": current_time,
            "zpm": zpm
        }
        
        # --- NEW: Save to disk every time the game updates ---
        self._save_memory()
        # -----------------------------------------------------
        
        return self.live_history[game_id][player_id]

    def generate_graph_data(self, player_round_history):
        if not player_round_history:
            return {"labels": [], "data": []}
            
        labels = []
        data = []
        
        # Sort rounds numerically
        rounds = sorted([int(k) for k in player_round_history.keys()])
        
        for r in rounds:
            r_str = str(r)
            r_data = player_round_history[r_str]
            
            total_xp_at_round = r_data.get("xp", 0)
            total_time_at_round = r_data.get("time", 0)
            
            # Takes the total accumulated XP up to this round, divided by total accumulated time
            if total_time_at_round > 0:
                xpm = int(total_xp_at_round / (total_time_at_round / 60.0))
            else:
                xpm = 0
                
            labels.append(f"Round {r}")
            data.append(xpm)
            
        return {"labels": labels, "data": data}
        
    def generate_xp_per_round_data(self, player_round_history):
        if not player_round_history:
            return {"labels": [], "data": []}
            
        labels = []
        data = []
        
        # Sort rounds numerically
        rounds = sorted([int(k) for k in player_round_history.keys()])
        
        previous_xp = 0
        
        for r in rounds:
            r_str = str(r)
            r_data = player_round_history[r_str]
            
            total_xp_at_round = r_data.get("xp", 0)
            
            # Calculate the XP gained specifically during this round
            xp_gained_this_round = total_xp_at_round - previous_xp
            
            # Failsafe for any weird memory resets
            if xp_gained_this_round < 0:
                xp_gained_this_round = 0
                
            labels.append(f"Round {r}")
            data.append(xp_gained_this_round)
            
            # Update previous_xp for the next iteration loop
            previous_xp = total_xp_at_round
            
        return {"labels": labels, "data": data}

    def generate_zpm_data(self, player_round_history):
        if not player_round_history:
            return {"labels": [], "data": []}

        labels = []
        data = []
        rounds = sorted([int(k) for k in player_round_history.keys()])

        for r in rounds:
            r_str = str(r)
            r_data = player_round_history[r_str]
            try:
                zpm = float(r_data.get("zpm", 0))
            except (TypeError, ValueError):
                zpm = 0

            labels.append(f"Round {r}")
            data.append(zpm)

        return {"labels": labels, "data": data}

# Singleton instance to be imported
xpm_grapher_instance = XPMGrapher()
