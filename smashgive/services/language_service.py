"""
Language Service — handles user language preferences.
"""

from db.sqlite import db
from config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE


async def get_language(user_id: int) -> str:
    """Get user's preferred language."""
    lang = await db.get_user_language(user_id)
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


async def set_language(user_id: int, lang: str) -> bool:
    """Set user's preferred language."""
    if lang not in SUPPORTED_LANGUAGES:
        return False
    await db.set_user_language(user_id, lang)
    return True
