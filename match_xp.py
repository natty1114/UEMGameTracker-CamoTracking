import os
import csv
import json
import threading

from app_paths import get_base_path, get_runtime_path
from xp_overflow_recovery import (
    build_recovery_debug,
    is_higher_tier_promotion,
    is_unstable_xp_snapshot,
)

class MatchXPTracker:
    def __init__(self, csv_filename="xp_requirements.csv", cache_filename="match_xp_cache.json"):
        self.level_xp_required = {}
        self.legend1_xp_required = {}
        self.legend2_xp_required = {}
        self._csv_loaded = False
        # Memory Format: { game_id: { player_id: { prestige, level, last_cumulative_xp, total_match_xp, start_xp_required } } }
        self.match_data = {} 
        self.last_debug = {}
        self.lock = threading.Lock()
        
        self.csv_path = os.path.join(get_base_path(), csv_filename)
        self.cache_path = get_runtime_path(cache_filename)
        
        self.load_cache()

    def load_csv(self):
        if self._csv_loaded:
            return
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
                                
                            # Load Legend XP values for levels 91+.
                            # Columns are: base/no legend, Legend 1, Legend 2.
                            if len(row) >= 5 and row[4].strip():
                                try:
                                    if level >= 91:
                                        self.legend1_xp_required[level] = int(row[4])
                                except ValueError:
                                    pass
                            if len(row) >= 6 and row[5].strip():
                                try:
                                    if level >= 91:
                                        self.legend2_xp_required[level] = int(row[5])
                                except ValueError:
                                    pass
                                
                        except ValueError:
                            # Safely skip any rows that don't have standard numbers
                            continue
        except Exception as e:
            print(f"Failed to read CSV: {e}")
            return

        self._csv_loaded = True

    def get_xp_required(self, level, legend_tier=0):
        if not self._csv_loaded:
            self.load_csv()
        if legend_tier >= 2 and level >= 91:
            return self.legend2_xp_required.get(level, 0)
        if legend_tier >= 1 and level >= 91:
            return self.legend1_xp_required.get(level, 0)
        return self.level_xp_required.get(level, 0)

    def _calculate_level_rollover_xp(self, previous_level, previous_xp, current_level, current_xp, legend_tier=0):
        if previous_level is None or current_level <= previous_level:
            return 0

        previous_level_required = self.get_xp_required(previous_level, legend_tier)
        if previous_level_required <= 0:
            return 0

        xp_gained = max(previous_level_required - previous_xp, 0)

        for skipped_level in range(previous_level + 1, current_level):
            xp_gained += max(self.get_xp_required(skipped_level, legend_tier), 0)

        xp_gained += current_xp
        return xp_gained

    def _get_level_rollover_debug(self, previous_level, previous_xp, current_level, current_xp, legend_tier=0):
        if previous_level is None or current_level <= previous_level:
            return None

        previous_level_required = self.get_xp_required(previous_level, legend_tier)
        if previous_level_required <= 0:
            return None

        remaining_previous_level = max(previous_level_required - previous_xp, 0)
        skipped_level_xp = 0
        for skipped_level in range(previous_level + 1, current_level):
            skipped_level_xp += max(self.get_xp_required(skipped_level, legend_tier), 0)

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
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.match_data, f)
        except Exception:
            pass

    def _set_debug_snapshot(
        self, game_id, player_id, current_prestige, current_level, current_xp,
        previous_prestige, previous_level, previous_xp, xp_gained, total_match_xp,
        xp_required, rollover_debug=None, recovery_debug=None,
        current_legend=0, current_absolute=0, current_ultimate=0,
        previous_legend=None, previous_absolute=None, previous_ultimate=None
    ):
        if game_id not in self.last_debug:
            self.last_debug[game_id] = {}

        self.last_debug[game_id][player_id] = {
            "game_id": game_id,
            "player_id": player_id,
            "prestige": current_prestige,
            "prestige_legend": current_legend,
            "prestige_absolute": current_absolute,
            "prestige_ultimate": current_ultimate,
            "level": current_level,
            "current_xp": current_xp,
            "previous_prestige": previous_prestige,
            "previous_prestige_legend": previous_legend,
            "previous_prestige_absolute": previous_absolute,
            "previous_prestige_ultimate": previous_ultimate,
            "previous_level": previous_level,
            "previous_xp": previous_xp,
            "tick_xp": xp_gained,
            "total_match_xp": total_match_xp,
            "xp_required": xp_required,
            "rollover_debug": rollover_debug,
            "recovery_debug": recovery_debug
        }

    def get_last_debug_snapshot(self, game_id, player_id):
        with self.lock:
            snapshot = self.last_debug.get(game_id, {}).get(player_id)
            if not snapshot:
                return None
            return dict(snapshot)

    def get_total_levels_gained(self, game_id, player_id):
        with self.lock:
            return self.match_data.get(game_id, {}).get(player_id, {}).get("total_levels_gained", 0)

    def calculate_match_xp(
        self, game_id, player_id, current_prestige, current_level, current_xp,
        legend_tier=0, overflow_recovery_enabled=False, absolute_tier=0, ultimate_tier=0
    ):
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
                
            xp_required = self.get_xp_required(current_level, legend_tier)
            initial_recovery = None
                
            # INITIALIZE NEW PLAYER
            if player_id not in self.match_data[game_id]:
                stable_baseline = True
                baseline_xp = current_xp
                if overflow_recovery_enabled:
                    initial_check = is_unstable_xp_snapshot(
                        current_prestige, current_level, current_xp, None, None, xp_required,
                        legend_tier, absolute_tier, ultimate_tier
                    )
                    if initial_check["unstable"]:
                        stable_baseline = False
                        baseline_xp = 0
                        initial_recovery = build_recovery_debug(initial_check["reason"], pending_count=1)

                self.match_data[game_id][player_id] = {
                    "prestige": current_prestige,
                    "prestige_legend": legend_tier,
                    "prestige_absolute": absolute_tier,
                    "prestige_ultimate": ultimate_tier,
                    "level": current_level,
                    "last_cumulative_xp": baseline_xp,
                    "total_match_xp": 0,
                    "total_levels_gained": 0,
                    "start_xp_required": xp_required,
                    "xp_baseline_stable": stable_baseline,
                    "overflow_recovery_pending": 1 if initial_recovery else 0,
                    "overflow_recovery_reason": initial_recovery.get("reason", "") if initial_recovery else ""
                }
                self._set_debug_snapshot(
                    game_id, player_id, current_prestige, current_level, current_xp,
                    None, None, None, 0, 0, xp_required, recovery_debug=initial_recovery,
                    current_legend=legend_tier,
                    current_absolute=absolute_tier,
                    current_ultimate=ultimate_tier
                )
                if cache_needs_saving: 
                    self.save_cache()
                return 0

            p_data = self.match_data[game_id][player_id]
            previous_prestige = p_data.get("prestige")
            previous_legend = p_data.get("prestige_legend", 0)
            previous_absolute = p_data.get("prestige_absolute", 0)
            previous_ultimate = p_data.get("prestige_ultimate", 0)
            previous_level = p_data.get("level", current_level)
            previous_xp = p_data.get("last_cumulative_xp", 0)
            previous_level_required = p_data.get("start_xp_required", 0)
            if previous_level_required <= 0:
                previous_level_required = self.get_xp_required(previous_level, legend_tier)
            xp_gained = 0
            rollover_debug = None
            recovery_debug = None

            if overflow_recovery_enabled:
                stability = is_unstable_xp_snapshot(
                    current_prestige, current_level, current_xp,
                    previous_prestige, previous_level, xp_required,
                    legend_tier, absolute_tier, ultimate_tier,
                    previous_legend, previous_absolute, previous_ultimate
                )
                if stability["unstable"]:
                    pending_count = int(p_data.get("overflow_recovery_pending", 0)) + 1
                    p_data["overflow_recovery_pending"] = pending_count
                    p_data["overflow_recovery_reason"] = stability["reason"]
                    self.save_cache()
                    recovery_debug = build_recovery_debug(
                        stability["reason"],
                        pending_count=pending_count,
                        tier_promoted=stability.get("tier_promoted", False)
                    )
                    self._set_debug_snapshot(
                        game_id, player_id, current_prestige, current_level, current_xp,
                        previous_prestige, previous_level, previous_xp, 0,
                        p_data["total_match_xp"], xp_required, recovery_debug=recovery_debug,
                        current_legend=legend_tier,
                        current_absolute=absolute_tier,
                        current_ultimate=ultimate_tier,
                        previous_legend=previous_legend,
                        previous_absolute=previous_absolute,
                        previous_ultimate=previous_ultimate
                    )
                    return p_data["total_match_xp"]

                if not p_data.get("xp_baseline_stable", True):
                    p_data["last_cumulative_xp"] = current_xp
                    p_data["prestige"] = current_prestige
                    p_data["prestige_legend"] = legend_tier
                    p_data["prestige_absolute"] = absolute_tier
                    p_data["prestige_ultimate"] = ultimate_tier
                    p_data["level"] = current_level
                    p_data["start_xp_required"] = xp_required
                    p_data["xp_baseline_stable"] = True
                    self.save_cache()
                    recovery_debug = build_recovery_debug(
                        p_data.get("overflow_recovery_reason", "unstable baseline"),
                        pending_count=p_data.get("overflow_recovery_pending", 0),
                        recovered=True
                    )
                    p_data["overflow_recovery_pending"] = 0
                    p_data["overflow_recovery_reason"] = ""
                    self._set_debug_snapshot(
                        game_id, player_id, current_prestige, current_level, current_xp,
                        previous_prestige, previous_level, previous_xp, 0,
                        p_data["total_match_xp"], xp_required, recovery_debug=recovery_debug,
                        current_legend=legend_tier,
                        current_absolute=absolute_tier,
                        current_ultimate=ultimate_tier,
                        previous_legend=previous_legend,
                        previous_absolute=previous_absolute,
                        previous_ultimate=previous_ultimate
                    )
                    self.save_cache()
                    return p_data["total_match_xp"]
            
            higher_tier_promoted = is_higher_tier_promotion(
                legend_tier, absolute_tier, ultimate_tier,
                previous_legend, previous_absolute, previous_ultimate
            )

            # Scenario A: Same Prestige/Tier
            if current_prestige == p_data["prestige"] and not higher_tier_promoted:
                if current_level > previous_level:
                    levels_gained_this_tick = current_level - previous_level
                    p_data["total_levels_gained"] = p_data.get("total_levels_gained", 0) + levels_gained_this_tick
                    xp_gained = self._calculate_level_rollover_xp(
                        previous_level, previous_xp, current_level, current_xp, legend_tier
                    )
                    rollover_debug = self._get_level_rollover_debug(
                        previous_level, previous_xp, current_level, current_xp, legend_tier
                    )
                else:
                    xp_gained = current_xp - previous_xp
                
                if xp_gained > 0:
                    p_data["total_match_xp"] += xp_gained
                    if overflow_recovery_enabled and int(p_data.get("overflow_recovery_pending", 0)) > 0:
                        recovery_debug = build_recovery_debug(
                            p_data.get("overflow_recovery_reason", "unstable snapshot"),
                            pending_count=p_data.get("overflow_recovery_pending", 0),
                            recovered=True
                        )
                        p_data["overflow_recovery_pending"] = 0
                        p_data["overflow_recovery_reason"] = ""
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
                        if overflow_recovery_enabled and int(p_data.get("overflow_recovery_pending", 0)) > 0:
                            recovery_debug = build_recovery_debug(
                                p_data.get("overflow_recovery_reason", "unstable snapshot"),
                                pending_count=p_data.get("overflow_recovery_pending", 0),
                                recovered=True
                            )
                            p_data["overflow_recovery_pending"] = 0
                            p_data["overflow_recovery_reason"] = ""
                    else:
                        xp_gained = 0
                else:
                    xp_gained = current_xp - previous_xp
                    if xp_gained > 0:
                        p_data["total_match_xp"] += xp_gained
                        if overflow_recovery_enabled and int(p_data.get("overflow_recovery_pending", 0)) > 0:
                            recovery_debug = build_recovery_debug(
                                p_data.get("overflow_recovery_reason", "unstable snapshot"),
                                pending_count=p_data.get("overflow_recovery_pending", 0),
                                recovered=True
                            )
                            p_data["overflow_recovery_pending"] = 0
                            p_data["overflow_recovery_reason"] = ""
                    else:
                        xp_gained = 0

            # Scenario C: Higher Tier Promotion Reset
            elif higher_tier_promoted:
                if previous_xp > current_xp:
                    remaining_to_tier = max(previous_level_required - previous_xp, 0)
                    xp_gained = remaining_to_tier + max(current_xp, 0)
                    rollover_debug = {
                        "previous_level_required": previous_level_required,
                        "remaining_previous_level": remaining_to_tier,
                        "skipped_level_xp": 0,
                        "current_level_progress": max(current_xp, 0),
                    }
                else:
                    xp_gained = current_xp - previous_xp

                if xp_gained > 0:
                    p_data["total_match_xp"] += xp_gained
                    recovery_debug = build_recovery_debug(
                        "valid higher-tier promotion",
                        pending_count=p_data.get("overflow_recovery_pending", 0),
                        recovered=int(p_data.get("overflow_recovery_pending", 0)) > 0,
                        tier_promoted=True
                    )
                    p_data["overflow_recovery_pending"] = 0
                    p_data["overflow_recovery_reason"] = ""
                else:
                    xp_gained = 0

            # Update tracked states for the next tick
            if (
                current_xp != p_data["last_cumulative_xp"]
                or current_prestige != p_data["prestige"]
                or current_level != p_data.get("level")
                or legend_tier != p_data.get("prestige_legend", 0)
                or absolute_tier != p_data.get("prestige_absolute", 0)
                or ultimate_tier != p_data.get("prestige_ultimate", 0)
            ):
                p_data["last_cumulative_xp"] = current_xp
                p_data["prestige"] = current_prestige
                p_data["prestige_legend"] = legend_tier
                p_data["prestige_absolute"] = absolute_tier
                p_data["prestige_ultimate"] = ultimate_tier
                p_data["level"] = current_level
                p_data["start_xp_required"] = xp_required
                self.save_cache()

            self._set_debug_snapshot(
                game_id, player_id, current_prestige, current_level, current_xp,
                previous_prestige, previous_level, previous_xp, xp_gained,
                p_data["total_match_xp"], xp_required, rollover_debug, recovery_debug,
                current_legend=legend_tier,
                current_absolute=absolute_tier,
                current_ultimate=ultimate_tier,
                previous_legend=previous_legend,
                previous_absolute=previous_absolute,
                previous_ultimate=previous_ultimate
            )
                
            return p_data["total_match_xp"]

# Singleton instance to be imported by bo3tracker.py
xp_tracker_instance = MatchXPTracker()
