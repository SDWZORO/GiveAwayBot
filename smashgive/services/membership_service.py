"""
Membership Verification Service — checks if users joined required channels.
"""

import json
import logging
from telegram import Bot

logger = logging.getLogger(__name__)


async def verify_membership(bot: Bot, user_id: int, requirements: list) -> tuple:
    """
    Verify user has joined all required channels/groups.

    Returns: (is_verified: bool, missing_channels: list)
    """
    if not requirements:
        return True, []

    missing = []

    for chat_id in requirements:
        try:
            chat_id = int(chat_id)
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ["left", "kicked"]:
                missing.append(chat_id)
        except Exception as e:
            logger.warning(f"Cannot verify membership for {user_id} in {chat_id}: {e}")
            missing.append(chat_id)

    return len(missing) == 0, missing


async def get_channel_info(bot: Bot, chat_id: int) -> dict:
    """Get channel/group info for display."""
    try:
        chat = await bot.get_chat(chat_id)
        invite_link = chat.invite_link
        if not invite_link:
            try:
                invite_link = await bot.export_chat_invite_link(chat_id)
            except Exception:
                invite_link = None
        return {
            "id": chat_id,
            "title": chat.title or str(chat_id),
            "invite_link": invite_link,
        }
    except Exception as e:
        logger.warning(f"Cannot get info for channel {chat_id}: {e}")
        return {
            "id": chat_id,
            "title": str(chat_id),
            "invite_link": None,
        }
