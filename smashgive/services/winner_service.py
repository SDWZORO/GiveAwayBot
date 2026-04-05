"""
Winner Service — handles winner selection and announcement.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict

from db.sqlite import db
from utils.weights import weighted_select

logger = logging.getLogger(__name__)


async def pick_winners(giveaway_id: str, count: int) -> List[Dict]:
    """
    Pick winners for a giveaway using weighted random selection.
    Manual winners are prioritized.
    """
    participants = await db.get_participants(giveaway_id)

    if not participants:
        return []

    # Filter out banned users
    eligible = []
    for p in participants:
        if not await db.is_banned(p["user_id"]):
            eligible.append(p)

    if not eligible:
        return []

    # Separate manual winners
    manual_winners = [p for p in eligible if p.get("manual_selected")]

    # Pick winners
    winners = weighted_select(eligible, count, manual_winners)

    # Update stats for winners
    for w in winners:
        await db.update_user_stats_win(w["user_id"])

    logger.info(f"Picked {len(winners)} winners for {giveaway_id}")
    return winners


async def save_giveaway_history(giveaway: dict, winners: List[Dict], ended_by: int = None):
    """Save completed giveaway to history."""
    participants_count = await db.get_participant_count(giveaway["giveaway_id"])

    history_data = {
        "giveaway_id": giveaway["giveaway_id"],
        "title": giveaway["title"],
        "reward": giveaway["reward"],
        "participants_count": participants_count,
        "winner_ids": [w["user_id"] for w in winners],
        "winner_usernames": [w.get("username", "") for w in winners],
        "status": giveaway.get("status", "ended"),
        "ended_by": ended_by,
    }

    await db.save_history(history_data)
    logger.info(f"History saved for {giveaway['giveaway_id']}")
