"""
Language Handler — /language command with inline keyboard selector.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from templates.messages import t
from services.language_service import get_language, set_language

# Language display names and flags
LANGUAGE_OPTIONS = {
    "en": "🇬🇧 English",
    "fr": "🇫🇷 Français",
    "id": "🇮🇩 Bahasa Indonesia",
    "fa": "🇮🇷 فارسی",
    "ru": "🇷🇺 Русский",
}


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selector."""
    user = update.effective_user
    lang = await get_language(user.id)

    buttons = []
    row = []
    for code, name in LANGUAGE_OPTIONS.items():
        row.append(InlineKeyboardButton(name, callback_data=f"lang_{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        t(lang, "language_prompt"),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    lang_code = query.data.replace("lang_", "")

    success = await set_language(user.id, lang_code)
    if success:
        await query.edit_message_text(
            t(lang_code, "language_updated"),
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❌ Invalid language.", parse_mode="HTML")
