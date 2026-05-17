"""Weapon category helpers for challenge and usage tracking."""

WEAPON_CATEGORIES = [
    "assault_rifle",
    "smg",
    "lmg",
    "pistol",
    "shotgun",
    "sniper",
    "launcher",
    "special",
    "melee",
    "other",
]

WEAPON_CATEGORY_LABELS = {
    "assault_rifle": "Assault Rifle",
    "smg": "Submachine Gun",
    "lmg": "LMG",
    "pistol": "Pistol",
    "shotgun": "Shotgun",
    "sniper": "Sniper",
    "launcher": "Launcher",
    "special": "Special / Wonder Weapon",
    "melee": "Melee",
    "other": "Other",
}

WEAPON_CATEGORY_PREFIXES = {
    "ar_": "assault_rifle",
    "smg_": "smg",
    "lmg_": "lmg",
    "pistol_": "pistol",
    "shotgun_": "shotgun",
    "sniper_": "sniper",
    "launcher_": "launcher",
    "special_": "special",
    "hero_": "special",
    "staff_": "special",
    "melee_": "melee",
    "knife_": "melee",
}

WEAPON_CATEGORY_TOKENS = {
    "_ar_": "assault_rifle",
    "_smg_": "smg",
    "_lmg_": "lmg",
    "_pistol_": "pistol",
    "_shotgun_": "shotgun",
    "_sniper_": "sniper",
    "_launcher_": "launcher",
    "_melee_": "melee",
}

WONDER_WEAPON_KEYWORDS = {
    "apothicon",
    "baby_gun",
    "blundergat",
    "dg4",
    "gersch",
    "ray_gun",
    "raygun",
    "scavenger",
    "servant",
    "staff_fire",
    "staff_ice",
    "staff_lightning",
    "staff_wind",
    "staff_air",
    "staff_water",
    "sliquifier",
    "thundergun",
    "vr11",
    "wave_gun",
    "wintershowl",
    "wonderwaffe",
}

CONSOLE_NAME_CATEGORY_OVERRIDES = {
    "cso2_ak47flash": "assault_rifle",
    "h1_p90": "smg",
    "hr_fuelrod": "launcher",
    "h1_rpg7": "launcher",
    "iw4_ump45": "smg",
    "iw5_aa12": "shotgun",
    "iw5_44magnum": "pistol",
    "iw5_g36c": "assault_rifle",
    "iw5_mp5": "smg",
    "iw5_striker": "shotgun",
    "iw5_usas12": "shotgun",
    "iw6_bizon": "smg",
    "iw6_ia2": "assault_rifle",
    "iw6_ak12": "assault_rifle",
    "iw6_kastet": "launcher",
    "iw6_m27_iar": "lmg",
    "iw6_mk32": "launcher",
    "iw6_mr28": "sniper",
    "iw6_panzerfaust3": "launcher",
    "iw6_sc2010": "assault_rifle",
    "iw6_venomx": "special",
    "iw6_vepr": "smg",
    "iw8_357": "pistol",
    "iw8_bizon": "smg",
    "iw8_grau556": "assault_rifle",
    "iw8_oden": "assault_rifle",
    "iw8_origin12": "shotgun",
    "iw8_p90": "smg",
    "iw8_rpg7": "launcher",
    "iw8_sig550": "assault_rifle",
    "iw8_sks": "sniper",
    "iw8_vks": "sniper",
    "s1_ae4": "assault_rifle",
    "s2_grease_gun": "smg",
    "s2_m1a1carbine": "assault_rifle",
    "s2_m1garand": "assault_rifle",
    "s2_m1919": "lmg",
    "s2_ppsh41_drum": "smg",
    "s4_ppsh41_base": "smg",
    "s4_ppsh41_drum": "smg",
    "s4_tesla_gun": "special",
    "s4_volkstg": "assault_rifle",
    "t5_ak74u": "smg",
    "t5_famas": "assault_rifle",
    "t5_galil": "assault_rifle",
    "t5_m16a1": "assault_rifle",
    "t6_peacekeeper": "assault_rifle",
    "t6_stinger": "launcher",
    "t6_type25": "assault_rifle",
    "t6_war_machine": "launcher",
    "t6_xpr50": "sniper",
    "t7_idgun": "special",
    "t7_idgun_genesis": "special",
    "t8_abr223": "assault_rifle",
    "t8_hades": "lmg",
    "t8_hellion_salvo": "launcher",
    "t8_hitchcock_m9": "pistol",
    "t8_icr7": "assault_rifle",
    "t8_gks": "smg",
    "t8_kn57": "assault_rifle",
    "t8_m1897": "shotgun",
    "t8_maddox_rfb": "assault_rifle",
    "t8_mog12": "shotgun",
    "t8_mozu": "pistol",
    "t8_overkill": "shotgun",
    "t8_rampage": "shotgun",
    "t8_sg12": "shotgun",
    "t8_spitfire": "smg",
    "t8_swat_rft": "assault_rifle",
    "t8_titan": "lmg",
    "t8_vapr_xkg": "assault_rifle",
    "t8_vendetta": "sniper",
    "t8_zweihander": "lmg",
    "t9_ak47": "assault_rifle",
    "t9_crossbow": "special",
    "t9_crossbow_skull": "special",
    "t9_gallo_sa12": "shotgun",
    "t9_grav": "assault_rifle",
    "t9_m60": "lmg",
    "t9_qbz83": "assault_rifle",
    "t9_rpg7": "launcher",
    "t4_ppsh": "smg",
    "t4_ppsh41_drum": "smg",
    "iw5_cm901": "assault_rifle",
    "iw7_mactav45": "smg",
    "sw_lightsaber": "melee",
}

DISPLAY_NAME_CATEGORY_OVERRIDES = {
    "3 line rifle": "sniper",
    "ak47": "assault_rifle",
    "ak 47": "assault_rifle",
    "ak74u": "smg",
    "an 94": "assault_rifle",
    "as44": "assault_rifle",
    "ballista": "sniper",
    "bar": "assault_rifle",
    "barrett m82a1": "sniper",
    "b23r": "pistol",
    "browning hp": "pistol",
    "china lake": "launcher",
    "chicom cqb": "smg",
    "colt m16a1": "assault_rifle",
    "combat shotgun": "shotgun",
    "cz75": "pistol",
    "cz75 dual wield": "pistol",
    "death machine": "lmg",
    "desert eagle": "pistol",
    "dragunov": "sniper",
    "dsr 50": "sniper",
    "einhorn revolving": "shotgun",
    "enfield": "assault_rifle",
    "executioner": "pistol",
    "fal": "assault_rifle",
    "fal osw": "assault_rifle",
    "five seven": "pistol",
    "five seven dual wield": "pistol",
    "fn fal": "assault_rifle",
    "g11": "assault_rifle",
    "galil": "assault_rifle",
    "gewehr 43": "assault_rifle",
    "gorenko anti tank rifle": "sniper",
    "hamr": "lmg",
    "hk21": "lmg",
    "hs 10": "shotgun",
    "kap 40": "pistol",
    "kar98k": "sniper",
    "kiparis": "smg",
    "ks 23": "shotgun",
    "ksg": "shotgun",
    "l96a1": "sniper",
    "lsat": "lmg",
    "m1 garand": "assault_rifle",
    "m1a1 carbine": "assault_rifle",
    "m8a1": "assault_rifle",
    "m14": "assault_rifle",
    "m16a1": "assault_rifle",
    "m27": "assault_rifle",
    "m60": "lmg",
    "m60e3": "lmg",
    "m72 law": "launcher",
    "m1216": "shotgun",
    "m1911": "pistol",
    "m1927": "smg",
    "mac11": "smg",
    "mauser c96": "pistol",
    "mg 42": "lmg",
    "mg08 15": "lmg",
    "mk 48": "lmg",
    "mm1 grenade launcher": "launcher",
    "mp5": "smg",
    "mp5k": "smg",
    "mp7": "smg",
    "mp40": "smg",
    "mpl": "smg",
    "msmc": "smg",
    "mtar": "assault_rifle",
    "olympia": "shotgun",
    "panzerschreck": "launcher",
    "pdw 57": "smg",
    "peacekeeper": "assault_rifle",
    "pm63": "smg",
    "ppsh 41 w drum magazine": "smg",
    "psg1": "sniper",
    "python": "pistol",
    "qbb lsw": "lmg",
    "remington 870 mcs": "shotgun",
    "remington new model army": "pistol",
    "rpd": "lmg",
    "rpg": "launcher",
    "rpk": "lmg",
    "s12": "shotgun",
    "scar h": "assault_rifle",
    "skorpion": "smg",
    "skorpion evo": "smg",
    "smaw": "launcher",
    "smr": "assault_rifle",
    "spas 12": "shotgun",
    "spectre": "smg",
    "stakeout": "shotgun",
    "stg 44": "assault_rifle",
    "stg44": "assault_rifle",
    "stoner63": "lmg",
    "storm psr": "sniper",
    "stinger": "launcher",
    "svt 40": "assault_rifle",
    "svu as": "sniper",
    "swat 556": "assault_rifle",
    "tac 45": "pistol",
    "thompson m1a1": "smg",
    "titus 6": "launcher",
    "type 25": "assault_rifle",
    "type 100": "smg",
    "uzi": "smg",
    "wa2000": "sniper",
}


def normalise_weapon_category(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if "|" in text:
        text = text.split("|", 1)[0].strip("_ ")
    aliases = {
        "ar": "assault_rifle",
        "assault": "assault_rifle",
        "assault_rifles": "assault_rifle",
        "submachine_gun": "smg",
        "submachine_guns": "smg",
        "machine_pistol": "pistol",
        "wonder": "special",
        "wonder_weapon": "special",
        "wonder_weapons": "special",
        "special_weapon": "special",
        "special_weapons": "special",
        "knife": "melee",
        "unknown": "other",
        "misc": "other",
        "miscellaneous": "other",
    }
    text = aliases.get(text, text)
    return text if text in WEAPON_CATEGORIES else "other"


def get_weapon_category(console_name, display_name=""):
    name = str(console_name or "").strip().lower()
    display = str(display_name or "").strip().lower()
    combined = f"{name} {display}"

    for keyword in WONDER_WEAPON_KEYWORDS:
        if keyword in combined:
            return "special"

    for prefix, category in WEAPON_CATEGORY_PREFIXES.items():
        if name.startswith(prefix):
            return category

    lookup_name = name
    for suffix in ("_upgraded", "_up"):
        if lookup_name.endswith(suffix):
            lookup_name = lookup_name[:-len(suffix)]
            break

    if lookup_name in CONSOLE_NAME_CATEGORY_OVERRIDES:
        return CONSOLE_NAME_CATEGORY_OVERRIDES[lookup_name]
    for override, category in CONSOLE_NAME_CATEGORY_OVERRIDES.items():
        if lookup_name.startswith(f"{override}_"):
            return category

    if lookup_name.startswith("gobblegun"):
        return "special"

    token_name = f"_{lookup_name}_"
    for token, category in WEAPON_CATEGORY_TOKENS.items():
        if token in token_name:
            return category

    normalised_display = "".join(ch if ch.isalnum() else " " for ch in display)
    normalised_display = " ".join(normalised_display.split())
    if normalised_display in DISPLAY_NAME_CATEGORY_OVERRIDES:
        return DISPLAY_NAME_CATEGORY_OVERRIDES[normalised_display]

    return "other"
