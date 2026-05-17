"""Multi-player stats processing for BO3 Tracker."""

from asset_helpers import (
    get_aat_icon_src,
    get_base64_icon,
    get_level_icon_src,
    get_prestige_icon_src,
    get_tier_icon_src,
)
from game_data import IGNORE_KEYWORDS, PERK_NAMES
from damage_memory import DamageMemory
from match_xp import xp_tracker_instance
from xpm_grapher import xpm_grapher_instance

damage_tracker = DamageMemory()


ENCHANTMENT_TIERS = {
    0: ("Unpacked Weapon", "#e8e0cf", "#111"),
    1: ("Common Enchantment", "#55ff2f", "#050505"),
    2: ("Rare Enchantment", "#3568ff", "#050505"),
    3: ("Epic Enchantment", "#c833c8", "#050505"),
    4: ("Legendary Enchantment", "#ea7b17", "#050505"),
    5: ("Mythic Enchantment", "#f1c800", "#050505"),
    6: ("Exotic Enchantment", "#ec453c", "#050505"),
    7: ("Divine Enchantment", "#ef58c7", "#050505"),
    8: ("Eternal Enchantment", "#8d42ad", "#050505"),
    9: ("Cosmic Enchantment", "#4b0077", "#f3e8ff"),
    10: ("Celestial Enchantment", "#60c7ed", "#050505"),
    11: ("Ultimate Enchantment", "#10e6a7", "#050505"),
}


def get_weapon_status_html(weapon):
    try:
        enchant = int(float(weapon.get("enchant")))
    except (TypeError, ValueError):
        enchant = None

    if enchant is not None:
        label, bg, fg = ENCHANTMENT_TIERS.get(
            enchant,
            (f"Enchantment {enchant}", "#333", "#eee"),
        )
        enchant_html = (
            f'<span class="weapon-status-enchant" '
            f'style="background:{bg};color:{fg};border-color:{bg}" '
            f'title="Enchant level {enchant}">{label}</span>'
        )
    else:
        is_pap = (
            int(weapon.get('repack_level', 0) or 0) > 0
            or (weapon.get('display_name_upgraded') and weapon.get('display_name_upgraded') != "none")
        )
        enchant_html = '<span class="weapon-status-pap">PAP</span>' if is_pap else '<span class="weapon-status-std">Unpacked Weapon</span>'

    aat_key = weapon.get("currentAAT") or weapon.get("current_aat") or weapon.get("aat")
    aat_name = format_aat_name(aat_key)
    if not aat_name:
        return enchant_html
    aat_icon = get_aat_icon_src(str(aat_key or ""))
    if aat_icon:
        aat_html = (
            f'<img class="weapon-status-aat-icon" src="{aat_icon}" '
            f'alt="{aat_name}" title="{aat_name}">'
        )
    else:
        aat_html = f'<span class="weapon-status-aat" title="Alternate Ammo Type">{aat_name}</span>'
    return (
        f'<div class="weapon-status-stack">{enchant_html}'
        f'{aat_html}</div>'
    )


def format_aat_name(value):
    text = str(value or "").replace("\x00", "").strip()
    if not text or text.lower() in ("none", "null", "0"):
        return ""
    for prefix in ("zm_aat_", "aat_", "specialty_"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
            break
    return text.replace("_", " ").replace("-", " ").title()


def process_stats(data, is_live=False, overflow_recovery_enabled=False):
    if not data: return None

    game = data.get('game') or data.get('data', {}).get('game', {})
    players = data.get('players') or data.get('data', {}).get('players', {})
    game_id = str(game.get('game_id', 'unknown_match'))

    time_sec = int(game.get('time_total', 0))
    mins, secs = divmod(time_sec, 60)

    status_text = "LIVE FEED" if is_live else f"ARCHIVED: {game.get('game_id')}"
    status_color = "#66fcf1" if is_live else "#444"

    nerf_html = ""
    if str(game.get('nerfed')) == "1":
        reason = str(game.get('nerfed_reason', '')).replace('|', ' ')
        nerf_html = f"<div class='nerf-box'>\u26a0 ACTIVE MODIFIERS: {reason}</div>"

    game_info = {
        "id": game_id,
        "status": status_text, "color": status_color, "nerf": nerf_html,
        "map": str(game.get('map_played', 'Unknown')).replace('_',' ').title(),
        "round": game.get('rounds_total', 0),
        "time": "{:02d}:{:02d}".format(mins, secs), "mode": game.get('gamemode', 'Standard'),
        "version": str(game.get('version', 'Unknown')),
        "avg_time": str(game.get('average_round_time', '0')),
        "zpm": str(game.get('zpm', '0')),
        "steam_link": str(game.get('steam_link', ''))
    }

    players_list = []

    def player_sort_key(item):
        pid = str(item[0])
        try:
            return (0, int(pid))
        except ValueError:
            return (1, pid)

    for pid, p in sorted(players.items(), key=player_sort_key):
        kills = int(p.get('kills', 0))
        headshots = int(p.get('headshots', 0))
        accuracy = round((headshots / kills) * 100, 1) if kills > 0 else 0
        xp_val = int(p.get('xp', p.get('total_xp', 0)))

        try:
            raw_mult = game.get('xp_multiplier') or p.get('xp_multiplier') or "100"
            xp_mult = "x{:.3f}".format(float(raw_mult) / 100.0)
        except:
            xp_mult = "x1.000"

        ult = int(p.get('prestige_ultimate', 0))
        abso = int(p.get('prestige_absolute', 0))
        leg = int(p.get('prestige_legend', 0))
        prest = int(p.get('prestige', 0))
        lvl = int(p.get('level', 1))

        if 'match_xp_earned' in p:
            match_xp_earned = int(p['match_xp_earned'])
        elif is_live:
            match_xp_earned = xp_tracker_instance.calculate_match_xp(
                game_id, pid, prest, lvl, xp_val, leg, overflow_recovery_enabled, abso, ult
            )
        else:
            match_xp_earned = 0

        match_xp_str = "{:,}".format(match_xp_earned)

        xp_per_min = 0
        if time_sec > 0:
            xp_per_min = int(match_xp_earned / (time_sec / 60.0))
        xpm_str = "{:,}".format(xp_per_min)

        ult_icon = get_tier_icon_src("ultimate", ult)
        abso_icon = get_tier_icon_src("absolute", abso)
        leg_icon = get_tier_icon_src("legend", leg)

        prestige_icon = get_prestige_icon_src(prest)
        level_icon = get_level_icon_src(lvl)
        xp_required = xp_tracker_instance.get_xp_required(lvl, leg)
        progress_pct = 0
        if xp_required > 0:
            progress_pct = max(0, min(100, round((xp_val / xp_required) * 100, 1)))

        if ult > 0: rank_main = "ULTIMATE PRESTIGE"
        elif abso > 0: rank_main = "ABSOLUTE PRESTIGE"
        elif leg > 0: rank_main = "PRESTIGE LEGEND"
        elif prest > 0: rank_main = f"PRESTIGE {prest}"
        else: rank_main = "RECRUIT"

        if prest >= 20:
            overlay_rank = "Master Prestige"
        elif prest > 0:
            overlay_rank = f"Prestige {prest}"
        else:
            overlay_rank = "Recruit"

        if ult > 0: overlay_tier = f"Ultimate {ult}"
        elif abso > 0: overlay_tier = f"Absolute {abso}"
        elif leg > 0: overlay_tier = f"Legend {leg}"
        else: overlay_tier = ""

        if is_live:
            level_ups = xp_tracker_instance.get_total_levels_gained(game_id, pid)
        else:
            try:
                level_ups = int(p.get('total_levels_gained', p.get('levels_gained', 0)))
            except:
                level_ups = 0

        rank_parts = []
        if ult > 0: rank_parts.append(f"Ult Tier {ult}")
        if abso > 0: rank_parts.append(f"Abs Tier {abso}")
        if leg > 0: rank_parts.append(f"Leg Tier {leg}")
        if prest > 0: rank_parts.append(f"Prestige {prest}")
        rank_parts.append(f"Level {lvl}")

        rank_sub = " // ".join(rank_parts)
        player_title = '"{}"'.format(p.get("player_title", "")) if p.get("player_title") else ""

        perks_html = ""
        raw_perks = p.get('perks', [])
        valid_perk_count = 0
        if isinstance(raw_perks, dict): raw_perks = list(raw_perks.values())
        for perk in raw_perks:
            if any(x in perk.lower() for x in IGNORE_KEYWORDS): continue
            pretty = PERK_NAMES.get(perk, perk.replace('specialty_', '').replace('_', ' ').title())
            if "null" in pretty.lower(): continue

            valid_perk_count += 1
            icon_b64 = get_base64_icon(perk)
            if icon_b64: perks_html += f'<div class="perk-item"><img src="{icon_b64}" class="perk-img" title="{pretty}"></div>'
            else: perks_html += f'<div class="perk-item"><div class="perk-fallback">{pretty[:3]}</div></div>'
        if not perks_html: perks_html = "<span class='no-perks'>No Active Perks</span>"

        weapons_html = ""
        weapons = p.get('top5') or p.get('weapon_data') or {}
        processed_weapons = []

        for k, w in weapons.items():
            if w.get('display') == 'none': continue

            status_html = get_weapon_status_html(w)
            dname = str(w.get('display', 'Unknown'))
            kills_w = str(w.get('kills', 0))
            headshots_w = str(w.get('headshots', 0))

            try: raw_damage = int(float(w.get('damage', 0)))
            except: raw_damage = 0

            corrected_damage = damage_tracker.get_real_damage(game_id, pid, k, raw_damage)

            processed_weapons.append({
                "name": dname,
                "kills": kills_w,
                "headshots": headshots_w,
                "damage_val": corrected_damage,
                "damage_str": "{:,}".format(corrected_damage),
                "status": status_html
            })

        processed_weapons.sort(key=lambda x: x['damage_val'], reverse=True)

        for pw in processed_weapons:
            weapons_html += (
                f"<tr class='weapon-row'>"
                f"<td class='weapon-name-cell'>{pw['name']}</td>"
                f"<td class='weapon-number-cell'>{pw['kills']}</td>"
                f"<td class='weapon-number-cell'>{pw['headshots']}</td>"
                f"<td class='weapon-number-cell'>{pw['damage_str']}</td>"
                f"<td class='weapon-status-cell'>{pw['status']}</td>"
                f"</tr>"
            )

        equip = p.get('equipment', {})
        lethal = equip.get('lethal', {}).get('name', 'None').replace('_', ' ').title()
        tactical = equip.get('tactical', {}).get('name', 'None').replace('_', ' ').title()

        if is_live:
            round_history = xpm_grapher_instance.live_history.get(game_id, {}).get(pid, {})
        else:
            round_history = p.get('round_history', {})

        graph_data = xpm_grapher_instance.generate_graph_data(round_history)
        round_xp_data = xpm_grapher_instance.generate_xp_per_round_data(round_history)
        zpm_graph_data = xpm_grapher_instance.generate_zpm_data(round_history)

        player_name = (
            p.get("name")
            or p.get("playername")
            or p.get("player_name")
            or p.get("username")
            or p.get("display_name")
            or ""
        )

        players_list.append({
            "pid": pid, "name": str(player_name),
            "r_main": rank_main, "title": player_title, "r_sub": rank_sub,
            "ult_icon": ult_icon, "abso_icon": abso_icon, "leg_icon": leg_icon,
            "prest_icon": prestige_icon, "lvl_icon": level_icon,
            "gums": p.get('gobblegums_used', 0),

            "xp": f"{xp_val:,} (+{match_xp_str} Match XP | {xpm_str} XP/min)",
            "match_xp": match_xp_str,
            "xpm": xpm_str,
            "mult": xp_mult,
            "rank_label": rank_main,
            "overlay_rank": overlay_rank,
            "overlay_tier": overlay_tier,
            "level": lvl,
            "level_ups": level_ups,
            "level_xp": xp_val,
            "level_xp_required": xp_required,
            "level_progress_pct": progress_pct,

            "k": kills, "pts": "{:,}".format(int(p.get('points', 0))), "acc": accuracy,
            "melee": p.get('melee_kills', 0), "equip": p.get('equipment_kills', 0), "downs": p.get('downs', 0),
            "perks": perks_html, "perk_count": valid_perk_count, "leth": lethal, "tact": tactical, "weaps": weapons_html,

            "graph_labels": graph_data["labels"],
            "graph_data": graph_data["data"],
            "round_xp_labels": round_xp_data["labels"],
            "round_xp_data": round_xp_data["data"],
            "zpm_labels": zpm_graph_data["labels"],
            "zpm_data": zpm_graph_data["data"]
        })

    return {
        "game": game_info,
        "players": players_list
    }
