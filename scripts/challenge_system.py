import os
import json
import glob
import time

CHALLENGES_FILE = "challenges.json"
UNLOCKS_FILE = "unlocked_rewards.json"
CALLING_CARD_DIR = "callingcards"

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return None

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except: return False

class ChallengeManager:
    def __init__(self, base_path):
        self.base_path = base_path
        self.filepath = os.path.join(base_path, CHALLENGES_FILE)
        self.unlocks_path = os.path.join(base_path, UNLOCKS_FILE)
        self.cards_path = os.path.join(base_path, CALLING_CARD_DIR)
        
        self.theme_requirements = {
            "void":            ["c_void_1", "c_void_2", "c_void_3"],
            "115_Origins":     ["c_org_1", "c_org_2", "c_org_3"],
            "RedHex":          ["c_red_1", "c_red_2", "c_red_3"],
            "Golden Divinium": ["c_gold_1", "c_gold_2", "c_gold_3"],
            "retro":           ["c_retro_1", "c_retro_2", "c_retro_3"],
            "matrix":          ["c_mat_1", "c_mat_2", "c_mat_3"]
        }
        
        self.unlocked_rewards = self._load_unlocks()
        self.challenges = self._load_or_create()
        self.check_theme_unlocks()

    def _load_unlocks(self):
        data = load_json(self.unlocks_path)
        if not data:
            defaults = ["default"]
            save_json(self.unlocks_path, defaults)
            return defaults
        return data

    def _load_or_create(self):
        defaults = [
            # --- THEME: VOID ---
            {"id": "c_void_1", "cat": "lifetime", "title": "Void I: Focus", "desc": "Get 500 Headshots", "target": 500, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_1"},
            {"id": "c_void_2", "cat": "lifetime", "title": "Void II: Clarity", "desc": "Get 1,500 Headshots", "target": 1500, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_2"},
            {"id": "c_void_3", "cat": "lifetime", "title": "Void III: Mastery", "desc": "Get 5,000 Headshots. Unlocks VOID Theme.", "target": 5000, "stat": "headshots", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_3"},
            # --- THEME: 115 ORIGINS ---
            {"id": "c_org_1", "cat": "lifetime", "title": "Origins I: Power", "desc": "Earn 50,000 Points", "target": 50000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_4"},
            {"id": "c_org_2", "cat": "lifetime", "title": "Origins II: Unleashed", "desc": "Get 1,000 Kills", "target": 1000, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_5"},
            {"id": "c_org_3", "cat": "lifetime", "title": "Origins III: Ancient", "desc": "Reach Round 30 in one game. Unlocks 115 THEME.", "target": 30, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_6"},
            # --- THEME: RED HEX ---
            {"id": "c_red_1", "cat": "lifetime", "title": "Red Hex I: Thirsty", "desc": "Finish games with 10 Perks active total", "target": 10, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_7"},
            {"id": "c_red_2", "cat": "lifetime", "title": "Red Hex II: Addict", "desc": "Finish games with 50 Perks active total", "target": 50, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_8"},
            {"id": "c_red_3", "cat": "lifetime", "title": "Red Hex III: Overdose", "desc": "Finish games with 100 Perks active total. Unlocks RED HEX Theme.", "target": 100, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_9"},
            # --- THEME: GOLDEN DIVINIUM ---
            {"id": "c_gold_1", "cat": "lifetime", "title": "Gold I: Nugget", "desc": "Earn 100,000 Points", "target": 100000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_10"},
            {"id": "c_gold_2", "cat": "lifetime", "title": "Gold II: Bullion", "desc": "Earn 500,000 Points", "target": 500000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_11"},
            {"id": "c_gold_3", "cat": "lifetime", "title": "Gold III: Tycoon", "desc": "Earn 1,000,000 Points. Unlocks GOLD Theme.", "target": 1000000, "stat": "points", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_12"},
            
            # --- THEME: RETRO (LOWERED REQUIREMENTS) ---
            {"id": "c_retro_1", "cat": "lifetime", "title": "Retro I: 8-Bit", "desc": "Get 1,000 Kills", "target": 1000, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_13"},
            {"id": "c_retro_2", "cat": "lifetime", "title": "Retro II: 16-Bit", "desc": "Get 2,500 Kills", "target": 2500, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_14"},
            {"id": "c_retro_3", "cat": "lifetime", "title": "Retro III: High Score", "desc": "Get 5,000 Kills. Unlocks RETRO Theme.", "target": 5000, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_15"},
            
            # --- THEME: MATRIX ---
            {"id": "c_mat_1", "cat": "lifetime", "title": "Matrix I: Blue Pill", "desc": "Reach Round 20", "target": 20, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_16"},
            {"id": "c_mat_2", "cat": "lifetime", "title": "Matrix II: Red Pill", "desc": "Reach Round 35", "target": 35, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_17"},
            {"id": "c_mat_3", "cat": "lifetime", "title": "Matrix III: The One", "desc": "Reach Round 50. Unlocks MATRIX Theme.", "target": 50, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_18"},
            # --- CAREER ---
            {"id": "c_card_master", "cat": "lifetime", "title": "Prestige Master", "desc": "Get 100,000 Total Kills", "target": 100000, "stat": "kills", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_19"},
            {"id": "c_door_master", "cat": "lifetime", "title": "Keymaster", "desc": "Open 1,000 Doors", "target": 1000, "stat": "doors", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_20"},
            {"id": "c_round_100", "cat": "lifetime", "title": "Century Club", "desc": "Reach Round 100 in one game", "target": 100, "stat": "round", "type": "single_game", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_21"},
            {"id": "c_perk_addict", "cat": "lifetime", "title": "Soda Fountain", "desc": "Finish games with 500 Perks active total", "target": 500, "stat": "perks_drank", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_22"},
            
            # --- CAREER: CQC ---
            {"id": "c_melee_1", "cat": "lifetime", "title": "Brawler", "desc": "Get 100 Melee Kills", "target": 100, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_23"},
            {"id": "c_melee_2", "cat": "lifetime", "title": "Knife Master", "desc": "Get 500 Melee Kills", "target": 500, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_24"},
            {"id": "c_melee_3", "cat": "lifetime", "title": "Samurai", "desc": "Get 1,000 Melee Kills", "target": 1000, "stat": "melee", "type": "cumulative", "progress": 0, "completed": False, "reward_type": "calling_card", "reward_val": "playercard_25"},
        ]
        
        saved_data = load_json(self.filepath)
        if isinstance(saved_data, list): saved_data = {"challenges": saved_data} 
        if not saved_data: saved_data = {"challenges": defaults}
        
        current_list = saved_data.get("challenges", [])
        cleaned_list = [c for c in current_list if not c['id'].startswith("c_theme_") and not c.get('cat') in ['daily', 'weekly']]
        default_map = {d['id']: d for d in defaults}
        
        for c in cleaned_list:
            if c['id'] in default_map: c.update(default_map[c['id']]) 
        
        existing_ids = [c['id'] for c in cleaned_list]
        for d in defaults:
            if d['id'] not in existing_ids: cleaned_list.append(d)

        final_list = self._scan_and_create_card_challenges(cleaned_list)
        
        saved_data["challenges"] = final_list
        saved_data.pop("last_daily", None)
        saved_data.pop("last_weekly", None)
        save_json(self.filepath, saved_data)
        
        return final_list

    def _scan_and_create_card_challenges(self, current_challenges):
        if not os.path.exists(self.cards_path):
             os.makedirs(self.cards_path)
             return current_challenges

        image_files = []
        for ext in ["*.jpg", "*.png", "*.webp", "*.mp4", "*.webm"]:
            image_files.extend(glob.glob(os.path.join(self.cards_path, ext)))
            
        found_card_names = set()
        for f in image_files:
            base = os.path.splitext(os.path.basename(f))[0]
            if base != "default": found_card_names.add(base)

        existing_rewards = set()
        for c in current_challenges:
            if c.get('reward_type') == 'calling_card': existing_rewards.add(c.get('reward_val'))
        
        new_cards_to_add = found_card_names - existing_rewards
        
        for card_name in new_cards_to_add:
            pretty_name = card_name.replace("_", " ").title()
            new_chal = {
                "id": f"c_auto_{card_name}",
                "cat": "operations",
                "title": f"Op: {pretty_name}",
                "desc": f"Complete 10 matches to unlock {pretty_name}.",
                "target": 10,
                "stat": "matches", 
                "type": "cumulative",
                "progress": 0, 
                "completed": False,
                "reward_type": "calling_card", 
                "reward_val": card_name
            }
            current_challenges.append(new_chal)
            
        return current_challenges

    def get_frontend_data(self):
        return self.challenges

    def get_unlocked_themes(self):
        return self.unlocked_rewards

    def check_theme_unlocks(self):
        changed = False
        completed_ids = [c['id'] for c in self.challenges if c['completed']]
        
        for theme_name, req_ids in self.theme_requirements.items():
            if theme_name in self.unlocked_rewards: continue
            if all(rid in completed_ids for rid in req_ids):
                self.unlocked_rewards.append(theme_name)
                changed = True
        
        if changed: save_json(self.unlocks_path, self.unlocked_rewards)

    def _is_challenge_active(self, c_id):
        for theme, chain in self.theme_requirements.items():
            if c_id in chain:
                idx = chain.index(c_id)
                if idx == 0: return True 
                prev_id = chain[idx - 1]
                prev_c = next((x for x in self.challenges if x['id'] == prev_id), None)
                return prev_c and prev_c['completed']
        return True 

    def process_completed_game(self, game_data, save=True):
        if not game_data: return

        game = game_data.get('game') or game_data.get('data', {}).get('game', {})
        players = game_data.get('players') or game_data.get('data', {}).get('players', {})
        if not players: return
        p = list(players.values())[0]

        raw_perks = p.get('perks', [])
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        valid_perks = [x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x]
        perks_drank_val = game_data.get('calculated_perks_drank', len(valid_perks))

        stats = {
            "matches": 1,
            "kills": int(p.get('kills', 0)),
            "headshots": int(p.get('headshots', 0)),
            "doors": int(p.get('doors_purchased', 0)),
            "round": int(game.get('rounds_total', 0)),
            "points": int(p.get('player_points_gained', p.get('points', 0))), 
            "melee": int(p.get('melee_kills', 0)), 
            "perks_drank": perks_drank_val,
            "rounds_added": int(game.get('rounds_total', 0))
        }

        changed = False
        for c in self.challenges:
            if c['completed']: continue
            if not self._is_challenge_active(c['id']): continue

            val = stats.get(c['stat'], 0)
            if val == 0: continue

            if c['type'] == 'cumulative':
                c['progress'] += val
                if c['progress'] >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
                changed = True
            
            elif c['type'] == 'single_game':
                if val >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
                    changed = True
                elif val > c['progress']:
                    c['progress'] = val
                    changed = True
        
        self.check_theme_unlocks()
        
        if save and changed:
            full = load_json(self.filepath)
            if not isinstance(full, dict): full = {}
            full["challenges"] = self.challenges
            full.pop("last_daily", None)
            full.pop("last_weekly", None)
            save_json(self.filepath, full)

    def process_update(self, history_path):
        if not history_path or not os.path.exists(history_path): return

        for c in self.challenges:
            if c['type'] == 'cumulative': 
                c['progress'] = 0
                c['completed'] = False

        json_files = glob.glob(os.path.join(history_path, "Game_*.json"))
        json_files.sort(key=os.path.getmtime) 
        
        for f in json_files:
            try:
                data = load_json(f)
                if not data: continue
                self._apply_game_stats(data)
            except: pass
            
        self.check_theme_unlocks()
        full = {"challenges": self.challenges}
        save_json(self.filepath, full)

    def _apply_game_stats(self, game_data):
        game = game_data.get('game') or game_data.get('data', {}).get('game', {})
        players = game_data.get('players') or game_data.get('data', {}).get('players', {})
        if not players: return
        p = list(players.values())[0]

        raw_perks = p.get('perks', [])
        valid_perks_count = 0
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        if raw_perks:
             valid_perks_count = len([x for x in raw_perks if x and "null" not in x and "pistoldeath" not in x])
        
        perks_drank_val = game_data.get('calculated_perks_drank', valid_perks_count)

        stats = {
            "matches": 1,
            "kills": int(p.get('kills', 0)),
            "headshots": int(p.get('headshots', 0)),
            "doors": int(p.get('doors_purchased', 0)),
            "round": int(game.get('rounds_total', 0)),
            "points": int(p.get('player_points_gained', p.get('points', 0))), 
            "melee": int(p.get('melee_kills', 0)),
            "perks_drank": perks_drank_val,
            "rounds_added": int(game.get('rounds_total', 0))
        }

        for c in self.challenges:
            if not self._is_challenge_active(c['id']): continue
            if c['completed']: continue 

            val = stats.get(c['stat'], 0)
            if val == 0: continue

            if c['type'] == 'cumulative':
                c['progress'] += val
                if c['progress'] >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
            
            elif c['type'] == 'single_game':
                if val >= c['target']:
                    c['progress'] = c['target']
                    c['completed'] = True
                elif val > c['progress']:
                    c['progress'] = val

    def reset_all_challenges(self):
        for c in self.challenges:
            c['progress'] = 0
            c['completed'] = False
        
        self.unlocked_rewards = ["default"]
        save_json(self.unlocks_path, self.unlocked_rewards)
        
        full = {"challenges": self.challenges}
        save_json(self.filepath, full)
        return True

    def scan_all_history(self, history_path):
        self.process_update(history_path)