"""
User Handlers — /start, /part, /mypart
"""

import json
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from db.sqlite import db
from templates.messages import t
from services import giveaway_service, language_service, log_service
from services.membership_service import verify_membership, get_channel_info
from utils.time import now_ist

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command. Also handles deep links for joining."""
    user = update.effective_user
    lang = await language_service.get_language(user.id)

    # Check for deep link join
    if context.args and context.args[0].startswith("join_"):
        giveaway_id = context.args[0].replace("join_", "")
        await _handle_join_dm(update, context, giveaway_id, lang)
        return

    await update.message.reply_text(
        t(lang, "start_welcome"),
        parse_mode="HTML"
    )


async def part(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /part command — join giveaway."""
    user = update.effective_user
    lang = await language_service.get_language(user.id)

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(
            t(lang, "no_active_giveaway"), parse_mode="HTML"
        )
        return

    if active["status"] != "active":
        await update.message.reply_text(
            t(lang, "join_fail_not_active"), parse_mode="HTML"
        )
        return

    # If in group, show buttons
    if update.effective_chat.type != "private":
        bot_me = await context.bot.get_me()
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    t(lang, "join_button_dm"),
                    url=f"https://t.me/{bot_me.username}?start=join_{active['giveaway_id']}"
                ),
                InlineKeyboardButton(
                    t(lang, "join_button_part"),
                    callback_data=f"part_{active['giveaway_id']}"
                ),
            ]
        ])
        await update.message.reply_text(
            f"🎉 <b>{active['title']}</b>\n\n📌 Join this giveaway!",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # In DM, process join
    await _handle_join_dm(update, context, active["giveaway_id"], lang)


async def part_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Take Part' button click."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    lang = await language_service.get_language(user.id)

    giveaway_id = query.data.replace("part_", "")

    # Redirect to DM
    bot_me = await context.bot.get_me()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t(lang, "join_button_dm"),
            url=f"https://t.me/{bot_me.username}?start=join_{giveaway_id}"
        )]
    ])

    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception:
        pass

    # Try to send DM directly
    try:
        await _send_join_prompt(context.bot, user.id, giveaway_id, lang)
    except Exception as e:
        logger.warning(f"Cannot DM user {user.id}: {e}")


async def _handle_join_dm(update: Update, context, giveaway_id: str, lang: str):
    """Handle join flow in DM."""
    user = update.effective_user

    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway:
        await update.message.reply_text(
            t(lang, "join_fail_invalid"), parse_mode="HTML"
        )
        return

    if giveaway["status"] != "active":
        await update.message.reply_text(
            t(lang, "join_fail_not_active"), parse_mode="HTML"
        )
        return

    # Check ban
    if await db.is_banned(user.id):
        await update.message.reply_text(
            t(lang, "join_fail_banned"), parse_mode="HTML"
        )
        return

    # Check already joined
    if await db.is_participant(giveaway_id, user.id):
        await update.message.reply_text(
            t(lang, "join_fail_already"), parse_mode="HTML"
        )
        return

    # Show join prompt with requirements
    await _send_join_prompt(context.bot, user.id, giveaway_id, lang)


async def _send_join_prompt(bot, user_id: int, giveaway_id: str, lang: str):
    """Send the join prompt with channel requirements."""
    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway:
        return

    requirements = json.loads(giveaway.get("join_requirements", "[]"))

    # Build requirement buttons
    req_text_parts = []
    buttons = []

    if requirements:
        for chat_id in requirements:
            info = await get_channel_info(bot, chat_id)
            req_text_parts.append(f"  • {info['title']}")
            if info.get("invite_link"):
                buttons.append([InlineKeyboardButton(
                    f"📢 {info['title']}", url=info["invite_link"]
                )])
    else:
        req_text_parts.append("  None — open to all!")

    req_text = "\n".join(req_text_parts)

    # Add "I Joined" button
    buttons.append([InlineKeyboardButton(
        t(lang, "join_button_joined"),
        callback_data=f"verify_{giveaway_id}"
    )])

    keyboard = InlineKeyboardMarkup(buttons)

    await bot.send_message(
        chat_id=user_id,
        text=t(lang, "join_prompt",
               title=giveaway["title"],
               reward=giveaway["reward"],
               winners_count=giveaway["winners_count"],
               requirements=req_text),
        parse_mode="HTML",
        reply_markup=keyboard
    )


async def verify_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'I Joined' button — verify membership and register."""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    lang = await language_service.get_language(user.id)

    giveaway_id = query.data.replace("verify_", "")

    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway:
        await query.edit_message_text(t(lang, "join_fail_invalid"), parse_mode="HTML")
        return

    if giveaway["status"] != "active":
        await query.edit_message_text(t(lang, "join_fail_not_active"), parse_mode="HTML")
        return

    if await db.is_banned(user.id):
        await query.edit_message_text(t(lang, "join_fail_banned"), parse_mode="HTML")
        return

    if await db.is_participant(giveaway_id, user.id):
        await query.edit_message_text(t(lang, "join_fail_already"), parse_mode="HTML")
        return

    # Verify membership
    requirements = json.loads(giveaway.get("join_requirements", "[]"))
    verified, missing = await verify_membership(context.bot, user.id, requirements)

    if not verified:
        await query.edit_message_text(t(lang, "join_fail_missing"), parse_mode="HTML")
        return

    # Register participant
    await db.add_participant({
        "giveaway_id": giveaway_id,
        "user_id": user.id,
        "username": user.username or "",
        "full_name": user.full_name or "",
        "source": "dm",
        "language_code": lang,
    })

    # Update user stats
    await db.update_user_stats_join(user.id)

    await query.edit_message_text(
        t(lang, "join_success", title=giveaway["title"]),
        parse_mode="HTML"
    )

    # Log to owners
    total = await db.get_participant_count(giveaway_id)
    from utils.time import format_ist
    await log_service.log_to_owners(
        context.bot,
        t("en", "join_log",
          full_name=user.full_name or "Unknown",
          user_id=user.id,
          username=user.username or "N/A",
          total_users=total,
          giveaway_id=giveaway_id,
          join_time=format_ist(datetime.now().isoformat()),
          verification="Passed ✅",
          language=lang,
          source="DM")
    )


async def mypart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's participation stats."""
    user = update.effective_user
    lang = await language_service.get_language(user.id)

    stats = await db.get_user_stats(user.id)
    if not stats:
        await update.message.reply_text(t(lang, "mypart_empty"), parse_mode="HTML")
        return

    joined = stats.get("joined_count", 0)
    won = stats.get("won_count", 0)
    win_rate = round((won / joined * 100), 1) if joined > 0 else 0

    from utils.time import format_ist
    last_joined = format_ist(stats["last_joined"]) if stats.get("last_joined") else "N/A"
    last_won = format_ist(stats["last_won"]) if stats.get("last_won") else "N/A"

    await update.message.reply_text(
        t(lang, "mypart_stats",
          joined_count=joined,
          won_count=won,
          win_rate=win_rate,
          last_joined=last_joined,
          last_won=last_won),
        parse_mode="HTML"
    )
