"""Opt-in guards for impossible live XP snapshots.

The normal match XP tracker should stay exact by default. This helper only
classifies snapshots that look like signed-overflow/rank-feed corruption so the
caller can avoid saving them as the next baseline.
"""


def is_higher_tier_promotion(
    current_legend, current_absolute, current_ultimate,
    previous_legend, previous_absolute, previous_ultimate
):
    if previous_legend is None:
        return False

    current_stack = (int(current_ultimate), int(current_absolute), int(current_legend))
    previous_stack = (int(previous_ultimate), int(previous_absolute), int(previous_legend))
    return current_stack > previous_stack


def is_unstable_xp_snapshot(
    current_prestige, current_level, current_xp,
    previous_prestige, previous_level, xp_required,
    current_legend=0, current_absolute=0, current_ultimate=0,
    previous_legend=None, previous_absolute=None, previous_ultimate=None
):
    reasons = []
    tier_promoted = is_higher_tier_promotion(
        current_legend, current_absolute, current_ultimate,
        previous_legend, previous_absolute, previous_ultimate
    )

    if current_xp < 0:
        reasons.append("negative level XP")

    if xp_required > 0 and current_xp > xp_required * 3:
        reasons.append("level XP far above requirement")

    if previous_prestige is not None and current_prestige < previous_prestige and not tier_promoted:
        reasons.append("prestige dropped")

    if (
        previous_level is not None
        and previous_prestige == current_prestige
        and not tier_promoted
        and previous_level >= 90
        and current_level <= 2
    ):
        reasons.append("level collapsed")

    return {
        "unstable": bool(reasons),
        "reason": ", ".join(reasons),
        "tier_promoted": tier_promoted,
    }


def build_recovery_debug(reason, pending_count=1, recovered=False, tier_promoted=False):
    if not reason and not recovered and not tier_promoted:
        return None

    return {
        "enabled": True,
        "reason": reason,
        "pending_count": int(pending_count or 0),
        "recovered": bool(recovered),
        "tier_promoted": bool(tier_promoted),
    }
