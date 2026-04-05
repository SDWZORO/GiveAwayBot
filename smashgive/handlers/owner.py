"""
Owner Handlers — All owner/admin commands.
/sg, /set, /choosewinner, /chanceup, /rmuser, /pban, /glist, /gstats, /ghistory, /gend
"""

import json
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters,
)

from config import OWNER_IDS, DEFAULT_CHANNELS, USERS_PER_PAGE, MAX_BOOST
from db.sqlite import db
from templates.messages import t
from services import giveaway_service, winner_service, log_service
from services.membership_service import get_channel_info
from utils.time import parse_ist, format_ist, format_duration, format_runtime, now_ist, IST
from utils.pagination import paginate

logger = logging.getLogger(__name__)

# Conversation states for /sg
(SG_TITLE, SG_REWARD, SG_WINNERS, SG_START, SG_END, SG_REQUIREMENTS) = range(6)


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


# ─── /sg — Setup Giveaway ───

async def sg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start giveaway setup wizard."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return ConversationHandler.END

    # Check for existing active giveaway
    active = await giveaway_service.get_active()
    if active:
        await update.message.reply_text(t("en", "sg_already_active"), parse_mode="HTML")
        return ConversationHandler.END

    context.user_data["sg"] = {}
    await update.message.reply_text(t("en", "sg_ask_title"), parse_mode="HTML")
    return SG_TITLE


async def sg_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sg"]["title"] = update.message.text.strip()
    await update.message.reply_text(t("en", "sg_ask_reward"), parse_mode="HTML")
    return SG_REWARD


async def sg_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["sg"]["reward"] = update.message.text.strip()
    await update.message.reply_text(t("en", "sg_ask_winners"), parse_mode="HTML")
    return SG_WINNERS


async def sg_winners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text(t("en", "sg_invalid_winners"), parse_mode="HTML")
        return SG_WINNERS

    context.user_data["sg"]["winners_count"] = count
    await update.message.reply_text(t("en", "sg_ask_start"), parse_mode="HTML")
    return SG_START


async def sg_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start_dt = parse_ist(update.message.text.strip())
        now = now_ist()
        if start_dt < now:
            await update.message.reply_text(t("en", "sg_start_in_past"), parse_mode="HTML")
            return SG_START
    except ValueError:
        await update.message.reply_text(t("en", "sg_invalid_time"), parse_mode="HTML")
        return SG_START

    context.user_data["sg"]["start_time"] = start_dt.isoformat()
    await update.message.reply_text(t("en", "sg_ask_end"), parse_mode="HTML")
    return SG_END


async def sg_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        end_dt = parse_ist(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(t("en", "sg_invalid_time"), parse_mode="HTML")
        return SG_END

    start_dt = datetime.fromisoformat(context.user_data["sg"]["start_time"])
    if end_dt.tzinfo is None:
        end_dt = IST.localize(end_dt)
    if start_dt.tzinfo is None:
        start_dt = IST.localize(start_dt)

    if end_dt <= start_dt:
        await update.message.reply_text(t("en", "sg_end_before_start"), parse_mode="HTML")
        return SG_END

    context.user_data["sg"]["end_time"] = end_dt.isoformat()
    await update.message.reply_text(t("en", "sg_ask_requirements"), parse_mode="HTML")
    return SG_REQUIREMENTS


async def sg_requirements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.lower() == "none":
        context.user_data["sg"]["join_requirements"] = []
    else:
        try:
            reqs = [int(x.strip()) for x in text.split(",")]
            context.user_data["sg"]["join_requirements"] = reqs
        except ValueError:
            context.user_data["sg"]["join_requirements"] = []

    # Get target channels from config or use defaults
    target_chats_str = await db.get_config("target_chats", json.dumps(DEFAULT_CHANNELS))
    target_chats = json.loads(target_chats_str)
    context.user_data["sg"]["target_chats"] = target_chats
    context.user_data["sg"]["created_by"] = update.effective_user.id

    # Generate preview
    sg = context.user_data["sg"]
    duration = format_duration(sg["start_time"], sg["end_time"])

    # Generate a temp ID for preview
    giveaway_id = await giveaway_service.generate_giveaway_id()
    context.user_data["sg"]["giveaway_id"] = giveaway_id

    preview = t("en", "sg_preview",
                title=sg["title"],
                reward=sg["reward"],
                winners_count=sg["winners_count"],
                start_time=format_ist(sg["start_time"]),
                end_time=format_ist(sg["end_time"]),
                duration=duration,
                giveaway_id=giveaway_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data="sg_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="sg_cancel"),
        ]
    ])

    await update.message.reply_text(preview, parse_mode="HTML", reply_markup=keyboard)
    return ConversationHandler.END


async def sg_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle giveaway confirmation."""
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    sg = context.user_data.get("sg")
    if not sg:
        await query.edit_message_text("⚠️ No giveaway data found. Please run /sg again.")
        return

    # Create in database
    await db.create_giveaway(sg)
    giveaway_id = sg["giveaway_id"]

    await query.edit_message_text(
        t("en", "sg_confirmed", giveaway_id=giveaway_id),
        parse_mode="HTML"
    )

    # Log action
    await log_service.log_action("giveaway_created", query.from_user.id, giveaway_id=giveaway_id)

    # Schedule the giveaway
    start_dt = datetime.fromisoformat(sg["start_time"])
    end_dt = datetime.fromisoformat(sg["end_time"])
    now = now_ist()

    if start_dt.tzinfo is None:
        start_dt = IST.localize(start_dt)
    if end_dt.tzinfo is None:
        end_dt = IST.localize(end_dt)

    # Schedule start job
    start_delay = (start_dt - now).total_seconds()
    if start_delay > 0:
        context.job_queue.run_once(
            _scheduled_start,
            when=start_delay,
            data={"giveaway_id": giveaway_id},
            name=f"start_{giveaway_id}"
        )
    else:
        # Start immediately if start time has passed
        await _do_start_giveaway(context.bot, giveaway_id)

    # Schedule end job
    end_delay = (end_dt - now).total_seconds()
    if end_delay > 0:
        context.job_queue.run_once(
            _scheduled_end,
            when=end_delay,
            data={"giveaway_id": giveaway_id},
            name=f"end_{giveaway_id}"
        )

    # Clear user data
    context.user_data.pop("sg", None)


async def sg_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle giveaway cancel."""
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    context.user_data.pop("sg", None)
    await query.edit_message_text(t("en", "sg_cancelled"), parse_mode="HTML")


async def _scheduled_start(context: ContextTypes.DEFAULT_TYPE):
    """Job callback to start a giveaway."""
    data = context.job.data
    giveaway_id = data["giveaway_id"]
    await _do_start_giveaway(context.bot, giveaway_id)


async def _do_start_giveaway(bot, giveaway_id: str):
    """Activate a giveaway and send announcements."""
    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway:
        return

    await giveaway_service.activate_giveaway(giveaway_id)

    # Build announcement
    duration = format_duration(giveaway["start_time"], giveaway["end_time"])
    announcement = t("en", "giveaway_announcement",
                     title=giveaway["title"],
                     reward=giveaway["reward"],
                     winners_count=giveaway["winners_count"],
                     start_time=format_ist(giveaway["start_time"]),
                     end_time=format_ist(giveaway["end_time"]),
                     duration=duration,
                     giveaway_id=giveaway_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📩 Start in DM", url=f"https://t.me/{(await bot.get_me()).username}?start=join_{giveaway_id}"),
            InlineKeyboardButton("🎉 Take Part", callback_data=f"part_{giveaway_id}"),
        ]
    ])

    # Post to target chats
    target_chats = json.loads(giveaway.get("target_chats", "[]"))
    msg_ids = {}

    for chat_id in target_chats:
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=announcement,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            msg_ids[str(chat_id)] = msg.message_id
        except Exception as e:
            logger.error(f"Cannot send announcement to {chat_id}: {e}")

    await db.save_announcement_ids(giveaway_id, msg_ids)

    # Log to owners
    await log_service.log_to_owners(bot,
        f"🟢 <b>Giveaway Started!</b>\n\n"
        f"🆔 <code>{giveaway_id}</code>\n"
        f"🏷 {giveaway['title']}\n"
        f"🎁 {giveaway['reward']}\n"
        f"📡 Announced to {len(msg_ids)} chats"
    )


async def _scheduled_end(context: ContextTypes.DEFAULT_TYPE):
    """Job callback to end a giveaway."""
    data = context.job.data
    giveaway_id = data["giveaway_id"]
    await _do_end_giveaway(context.bot, giveaway_id)


async def _do_end_giveaway(bot, giveaway_id: str, ended_by: int = None, forced: bool = False):
    """End the giveaway, pick winners, announce results."""
    giveaway = await db.get_giveaway(giveaway_id)
    if not giveaway or giveaway["status"] in ("ended", "forced_end", "cancelled"):
        return

    # End it
    await giveaway_service.end_giveaway(giveaway_id, ended_by, forced)

    # Pick winners
    winners = await winner_service.pick_winners(giveaway_id, giveaway["winners_count"])

    # Build winner list text
    if winners:
        winner_lines = []
        for i, w in enumerate(winners, 1):
            name = w.get("full_name", "Unknown")
            uname = w.get("username", "")
            line = f"  {i}. {name}"
            if uname:
                line += f" (@{uname})"
            winner_lines.append(line)
        winner_list = "\n".join(winner_lines)
    else:
        winner_list = "  No winners"

    total_participants = await db.get_participant_count(giveaway_id)

    # Announcement
    announcement = t("en", "winner_announcement",
                     title=giveaway["title"],
                     reward=giveaway["reward"],
                     winner_list=winner_list,
                     total_participants=total_participants,
                     giveaway_id=giveaway_id)

    # Post to target chats
    target_chats = json.loads(giveaway.get("target_chats", "[]"))
    for chat_id in target_chats:
        try:
            await bot.send_message(chat_id=chat_id, text=announcement, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Cannot send winner announcement to {chat_id}: {e}")

    # DM winners
    for w in winners:
        try:
            await bot.send_message(
                chat_id=w["user_id"],
                text=t("en", "winner_dm",
                       title=giveaway["title"],
                       reward=giveaway["reward"],
                       giveaway_id=giveaway_id),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Cannot DM winner {w['user_id']}: {e}")

    # Save history
    await winner_service.save_giveaway_history(giveaway, winners, ended_by)

    # Log to owners
    await log_service.log_to_owners(bot,
        f"🔴 <b>Giveaway Ended!</b>\n\n"
        f"🆔 <code>{giveaway_id}</code>\n"
        f"🏷 {giveaway['title']}\n"
        f"🏆 Winners: {len(winners)}\n"
        f"👥 Participants: {total_participants}\n"
        f"📌 {'Forced' if forced else 'Scheduled'}"
    )


# ─── /set ───

async def set_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set target channel/group IDs."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(t("en", "set_channels_usage"), parse_mode="HTML")
        return

    try:
        channels = [int(x.strip()) for x in " ".join(context.args).split(",")]
        await db.set_config("target_chats", json.dumps(channels))
        await update.message.reply_text(
            t("en", "set_channels_success", channels=str(channels)),
            parse_mode="HTML"
        )
        await log_service.log_action("set_channels", update.effective_user.id, details=str(channels))
    except ValueError:
        await update.message.reply_text(t("en", "set_channels_usage"), parse_mode="HTML")


# ─── /choosewinner ───

async def choose_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually select a winner."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    if len(context.args) < 2:
        await update.message.reply_text(t("en", "choosewinner_usage"), parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])
        winner_number = int(context.args[1])
    except ValueError:
        await update.message.reply_text(t("en", "choosewinner_usage"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    # Check if participant and not banned
    is_participant = await db.is_participant(active["giveaway_id"], user_id)
    is_banned = await db.is_banned(user_id)

    if not is_participant or is_banned:
        await update.message.reply_text(
            t("en", "choosewinner_fail", user_id=user_id), parse_mode="HTML"
        )
        return

    await db.set_manual_winner(active["giveaway_id"], user_id)
    await update.message.reply_text(
        t("en", "choosewinner_success", user_id=user_id, winner_number=winner_number),
        parse_mode="HTML"
    )
    await log_service.log_action(
        "manual_winner", update.effective_user.id,
        target_id=user_id, giveaway_id=active["giveaway_id"],
        details=f"Winner #{winner_number}"
    )


# ─── /chanceup ───

async def chance_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Boost a user's chances."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    if len(context.args) < 2:
        await update.message.reply_text(t("en", "chanceup_usage"), parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])
        percentage = float(context.args[1])
    except ValueError:
        await update.message.reply_text(t("en", "chanceup_usage"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    boost = min(percentage / 100.0, MAX_BOOST - 1.0)
    weight = round(1.0 + boost, 2)

    success = await db.set_participant_boost(active["giveaway_id"], user_id, boost)
    if success:
        await update.message.reply_text(
            t("en", "chanceup_success", user_id=user_id, percentage=int(percentage), weight=weight),
            parse_mode="HTML"
        )
        await log_service.log_action(
            "chance_boost", update.effective_user.id,
            target_id=user_id, giveaway_id=active["giveaway_id"],
            details=f"+{percentage}% (weight={weight})"
        )
    else:
        await update.message.reply_text(
            t("en", "chanceup_fail", user_id=user_id), parse_mode="HTML"
        )


# ─── /rmuser ───

async def rm_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Silently remove a user from current giveaway."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(t("en", "rmuser_usage"), parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t("en", "rmuser_usage"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    success = await db.remove_participant(active["giveaway_id"], user_id)
    if success:
        await update.message.reply_text(
            t("en", "rmuser_success", user_id=user_id), parse_mode="HTML"
        )
        await log_service.log_action(
            "remove_user", update.effective_user.id,
            target_id=user_id, giveaway_id=active["giveaway_id"]
        )
    else:
        await update.message.reply_text(
            t("en", "rmuser_fail", user_id=user_id), parse_mode="HTML"
        )


# ─── /pban ───

async def pban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permanently ban a user from all giveaways."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    if not context.args:
        await update.message.reply_text(t("en", "pban_usage"), parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t("en", "pban_usage"), parse_mode="HTML")
        return

    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason"

    success = await db.ban_user(user_id, reason, update.effective_user.id)
    if success:
        # Remove from active giveaway if present
        active = await giveaway_service.get_active()
        if active:
            await db.remove_participant(active["giveaway_id"], user_id)

        await update.message.reply_text(
            t("en", "pban_success", user_id=user_id), parse_mode="HTML"
        )
        await log_service.log_action(
            "permanent_ban", update.effective_user.id,
            target_id=user_id, details=reason
        )
    else:
        await update.message.reply_text(
            t("en", "pban_already", user_id=user_id), parse_mode="HTML"
        )


# ─── /glist ───

async def glist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current giveaway participants."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    participants = await db.get_participants(active["giveaway_id"])

    if not participants:
        await update.message.reply_text(t("en", "glist_empty"), parse_mode="HTML")
        return

    page = 1
    if context.args:
        try:
            page = int(context.args[0])
        except ValueError:
            page = 1

    page_items, total_pages, current_page = paginate(participants, page, USERS_PER_PAGE)

    text = t("en", "glist_header", total=len(participants), page=current_page, total_pages=total_pages)

    for i, p in enumerate(page_items, (current_page - 1) * USERS_PER_PAGE + 1):
        text += t("en", "glist_user",
                  num=i,
                  full_name=p.get("full_name", "Unknown"),
                  user_id=p["user_id"],
                  username=p.get("username", "N/A")) + "\n"

    # Pagination buttons
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"glist_{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"glist_{current_page + 1}"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def glist_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination for /glist."""
    query = update.callback_query
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    page = int(query.data.split("_")[1])

    active = await giveaway_service.get_active()
    if not active:
        return

    participants = await db.get_participants(active["giveaway_id"])
    page_items, total_pages, current_page = paginate(participants, page, USERS_PER_PAGE)

    text = t("en", "glist_header", total=len(participants), page=current_page, total_pages=total_pages)

    for i, p in enumerate(page_items, (current_page - 1) * USERS_PER_PAGE + 1):
        text += t("en", "glist_user",
                  num=i,
                  full_name=p.get("full_name", "Unknown"),
                  user_id=p["user_id"],
                  username=p.get("username", "N/A")) + "\n"

    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"glist_{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"glist_{current_page + 1}"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


# ─── /gstats ───

async def gstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current giveaway stats."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    total_participants = await db.get_participant_count(active["giveaway_id"])
    boosted = await db.get_boosted_count(active["giveaway_id"])
    banned = await db.get_ban_count()
    target_chats = json.loads(active.get("target_chats", "[]"))
    duration = format_duration(active["start_time"], active["end_time"])
    runtime = format_runtime(active["start_time"])

    text = t("en", "gstats_output",
             giveaway_id=active["giveaway_id"],
             title=active["title"],
             reward=active["reward"],
             status=active["status"].upper(),
             start_time=format_ist(active["start_time"]),
             end_time=format_ist(active["end_time"]),
             duration=duration,
             total_participants=total_participants,
             boosted_users=boosted,
             banned_users=banned,
             winners_count=active["winners_count"],
             target_chats=len(target_chats),
             runtime=runtime)

    await update.message.reply_text(text, parse_mode="HTML")


# ─── /ghistory ───

async def ghistory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show giveaway history."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    history = await db.get_history()
    if not history:
        await update.message.reply_text(t("en", "ghistory_empty"), parse_mode="HTML")
        return

    text = t("en", "ghistory_header")

    for h in history[:10]:  # Last 10
        winner_usernames = json.loads(h.get("winner_usernames", "[]"))
        winners_str = ", ".join(winner_usernames) if winner_usernames else "None"

        text += t("en", "ghistory_item",
                  giveaway_id=h["giveaway_id"],
                  title=h["title"],
                  reward=h["reward"],
                  start_time="N/A",
                  end_time=h.get("finalized_at", "N/A"),
                  winners=winners_str,
                  participants_count=h.get("participants_count", 0),
                  status=h["status"],
                  created_by="Owner",
                  ended_by=h.get("ended_by", "Auto"))

    await update.message.reply_text(text, parse_mode="HTML")


# ─── /gend ───

async def gend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force end the current giveaway."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    active = await giveaway_service.get_active()
    if not active:
        await update.message.reply_text(t("en", "gend_no_active"), parse_mode="HTML")
        return

    giveaway_id = active["giveaway_id"]

    # Remove scheduled end job if exists
    current_jobs = context.job_queue.get_jobs_by_name(f"end_{giveaway_id}")
    for job in current_jobs:
        job.schedule_removal()

    # End giveaway
    await _do_end_giveaway(context.bot, giveaway_id, update.effective_user.id, forced=True)

    await update.message.reply_text(
        t("en", "gend_success", giveaway_id=giveaway_id), parse_mode="HTML"
    )


# ─── /fwd — Broadcast to all DMs ───

async def fwd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a replied message to all user DMs with real-time progress bar."""
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(t("en", "not_owner"), parse_mode="HTML")
        return

    # Must reply to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ <b>Reply to a message</b> to broadcast it.\n"
            "Usage: Reply to any message with <code>/fwd</code>",
            parse_mode="HTML"
        )
        return

    replied = update.message.reply_to_message

    # Get all user IDs
    user_ids = await db.get_all_dm_user_ids()

    if not user_ids:
        await update.message.reply_text("📭 No users found to broadcast to.", parse_mode="HTML")
        return

    total = len(user_ids)
    sent = 0
    failed = 0
    blocked = 0

    # Send initial progress message
    def build_progress(current, total_count, s, f, b):
        pct = int((current / total_count) * 100) if total_count > 0 else 0
        filled = int(pct / 5)  # 20 blocks total
        bar = "█" * filled + "░" * (20 - filled)
        return (
            f"📡 <b>BROADCASTING...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"[{bar}] {pct}%\n\n"
            f"📊 <b>Progress:</b> {current}/{total_count}\n"
            f"✅ <b>Sent:</b> {s}\n"
            f"🚫 <b>Blocked:</b> {b}\n"
            f"❌ <b>Failed:</b> {f}"
        )

    progress_msg = await update.message.reply_text(
        build_progress(0, total, 0, 0, 0),
        parse_mode="HTML"
    )

    # Broadcast to each user
    update_interval = max(1, min(5, total // 20))  # Update every ~5% or every 5 users

    for i, user_id in enumerate(user_ids, 1):
        try:
            # Forward or copy the message depending on type
            if replied.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=replied.text_html or replied.text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            elif replied.photo:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=replied.photo[-1].file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            elif replied.video:
                await context.bot.send_video(
                    chat_id=user_id,
                    video=replied.video.file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            elif replied.document:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=replied.document.file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            elif replied.sticker:
                await context.bot.send_sticker(
                    chat_id=user_id,
                    sticker=replied.sticker.file_id,
                )
            elif replied.animation:
                await context.bot.send_animation(
                    chat_id=user_id,
                    animation=replied.animation.file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            elif replied.voice:
                await context.bot.send_voice(
                    chat_id=user_id,
                    voice=replied.voice.file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            elif replied.audio:
                await context.bot.send_audio(
                    chat_id=user_id,
                    audio=replied.audio.file_id,
                    caption=replied.caption_html or replied.caption or "",
                    parse_mode="HTML",
                )
            else:
                # Fallback: try forwarding
                await replied.forward(chat_id=user_id)

            sent += 1

        except Exception as e:
            err_msg = str(e).lower()
            if "blocked" in err_msg or "deactivated" in err_msg or "not found" in err_msg:
                blocked += 1
            else:
                failed += 1
                logger.warning(f"Broadcast failed for {user_id}: {e}")

        # Update progress bar periodically
        if i % update_interval == 0 or i == total:
            try:
                await progress_msg.edit_text(
                    build_progress(i, total, sent, failed, blocked),
                    parse_mode="HTML"
                )
            except Exception:
                pass  # Ignore edit throttle errors

    # Final summary
    final_text = (
        f"✅ <b>BROADCAST COMPLETE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"[{'█' * 20}] 100%\n\n"
        f"📊 <b>Total Users:</b> {total}\n"
        f"✅ <b>Delivered:</b> {sent}\n"
        f"🚫 <b>Blocked/Deactivated:</b> {blocked}\n"
        f"❌ <b>Failed:</b> {failed}\n\n"
        f"📈 <b>Success Rate:</b> {round(sent / total * 100, 1) if total > 0 else 0}%"
    )

    try:
        await progress_msg.edit_text(final_text, parse_mode="HTML")
    except Exception:
        await update.message.reply_text(final_text, parse_mode="HTML")

    # Log action
    await log_service.log_action(
        "broadcast", update.effective_user.id,
        details=f"Total={total}, Sent={sent}, Blocked={blocked}, Failed={failed}"
    )


# ─── Cancel handler for conversation ───

async def sg_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the giveaway setup."""
    context.user_data.pop("sg", None)
    await update.message.reply_text(t("en", "sg_cancelled"), parse_mode="HTML")
    return ConversationHandler.END


def get_sg_conversation_handler():
    """Build the /sg ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("sg", sg_start)],
        states={
            SG_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_title)],
            SG_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_reward)],
            SG_WINNERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_winners)],
            SG_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_start_time)],
            SG_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_end_time)],
            SG_REQUIREMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sg_requirements)],
        },
        fallbacks=[CommandHandler("cancel", sg_cancel)],
        per_user=True,
        per_chat=True,
    )

