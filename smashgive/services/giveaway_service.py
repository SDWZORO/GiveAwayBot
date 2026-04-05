"""
Giveaway Service — handles giveaway lifecycle operations.
"""

import json
import random
import logging
from datetime import datetime

from db.sqlite import db
from config import GIVEAWAY_ID_PREFIX

logger = logging.getLogger(__name__)


async def generate_giveaway_id() -> str:
    """Generate a unique giveaway ID."""
    num = random.randint(100, 9999)
    gid = f"{GIVEAWAY_ID_PREFIX}_{num}"
    # Ensure uniqueness
    existing = await db.get_giveaway(gid)
    while existing:
        num = random.randint(100, 9999)
        gid = f"{GIVEAWAY_ID_PREFIX}_{num}"
        existing = await db.get_giveaway(gid)
    return gid


async def create_giveaway(data: dict) -> str:
    """Create a new giveaway and return its ID."""
    giveaway_id = await generate_giveaway_id()
    data["giveaway_id"] = giveaway_id
    await db.create_giveaway(data)
    logger.info(f"Giveaway created: {giveaway_id}")
    return giveaway_id


async def activate_giveaway(giveaway_id: str):
    """Set giveaway status to active."""
    await db.update_giveaway_status(giveaway_id, "active")
    logger.info(f"Giveaway activated: {giveaway_id}")


async def end_giveaway(giveaway_id: str, ended_by: int = None, forced: bool = False):
    """End a giveaway."""
    status = "forced_end" if forced else "ended"
    await db.update_giveaway_status(giveaway_id, status, datetime.now().isoformat())
    logger.info(f"Giveaway ended: {giveaway_id} (forced={forced})")


async def get_active() -> dict:
    """Get the current active/scheduled giveaway."""
    return await db.get_active_giveaway()


async def get_target_chats(giveaway: dict) -> list:
    """Parse target chats from giveaway data."""
    try:
        return json.loads(giveaway.get("target_chats", "[]"))
    except json.JSONDecodeError:
        return []


async def get_join_requirements(giveaway: dict) -> list:
    """Parse join requirements from giveaway data."""
    try:
        return json.loads(giveaway.get("join_requirements", "[]"))
    except json.JSONDecodeError:
        return []
