"""
Log Service — sends owner DM logs for giveaway actions.
"""

import logging
from telegram import Bot
from db.sqlite import db
from config import OWNER_IDS

logger = logging.getLogger(__name__)


async def log_to_owners(bot: Bot, message: str):
    """Send a log message to all owner DMs."""
    for owner_id in OWNER_IDS:
        try:
            await bot.send_message(
                chat_id=owner_id,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Cannot send log to owner {owner_id}: {e}")


async def log_action(action: str, actor_id: int, target_id: int = None,
                     giveaway_id: str = None, details: str = ""):
    """Log an admin action to the database."""
    await db.add_log(
        action=action,
        actor_id=actor_id,
        target_id=target_id,
        giveaway_id=giveaway_id,
        details=details
    )
