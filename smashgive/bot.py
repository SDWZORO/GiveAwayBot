"""
Smash Giveaway Bot — Main Entry Point
A professional, scalable, multilingual Telegram giveaway system.
"""

import json
import logging
import asyncio
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes,
)

from config import BOT_TOKEN, DEFAULT_CHANNELS, OWNER_IDS
from db.sqlite import db
from handlers.owner import (
    get_sg_conversation_handler,
    set_channels, choose_winner, chance_up, rm_user, pban,
    glist, glist_page_callback, gstats, ghistory, gend,
    sg_confirm_callback, sg_cancel_callback, fwd_broadcast,
)
from handlers.user import (
    start, part, part_callback, verify_join_callback, mypart,
)
from handlers.language import language_command, language_callback

# ─── Logging ───
logging.basicConfig(
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("SmashGiveaway")


async def post_init(application: Application):
    """Run after bot starts — initialize DB and default config."""
    await db.connect()
    logger.info("Database initialized.")

    # Set default channels if not set
    existing = await db.get_config("target_chats")
    if not existing:
        await db.set_config("target_chats", json.dumps(DEFAULT_CHANNELS))
        logger.info(f"Default channels configured: {DEFAULT_CHANNELS}")

    # Reschedule active giveaway if bot restarts
    from services.giveaway_service import get_active
    from utils.time import IST
    active = await get_active()
    if active and active["status"] in ("active", "scheduled"):
        end_dt = datetime.fromisoformat(active["end_time"])
        if end_dt.tzinfo is None:
            end_dt = IST.localize(end_dt)
        from utils.time import now_ist
        now = now_ist()
        remaining = (end_dt - now).total_seconds()
        if remaining > 0:
            application.job_queue.run_once(
                _scheduled_end_job,
                when=remaining,
                data={"giveaway_id": active["giveaway_id"]},
                name=f"end_{active['giveaway_id']}"
            )
            logger.info(f"Rescheduled end for {active['giveaway_id']} in {remaining:.0f}s")

        # If scheduled and past start time, activate
        if active["status"] == "scheduled":
            start_dt = datetime.fromisoformat(active["start_time"])
            if start_dt.tzinfo is None:
                start_dt = IST.localize(start_dt)
            if start_dt <= now:
                from handlers.owner import _do_start_giveaway
                await _do_start_giveaway(application.bot, active["giveaway_id"])
                logger.info(f"Auto-activated {active['giveaway_id']}")
            else:
                start_remaining = (start_dt - now).total_seconds()
                application.job_queue.run_once(
                    _scheduled_start_job,
                    when=start_remaining,
                    data={"giveaway_id": active["giveaway_id"]},
                    name=f"start_{active['giveaway_id']}"
                )
                logger.info(f"Rescheduled start for {active['giveaway_id']} in {start_remaining:.0f}s")

    # Notify owners that bot is online
    for owner_id in OWNER_IDS:
        try:
            await application.bot.send_message(
                chat_id=owner_id,
                text="🟢 <b>Smash Giveaway Bot is Online!</b>\n\n"
                     "📋 Commands: /sg /gstats /glist /gend /ghistory\n"
                     "⚙️ Config: /set /choosewinner /chanceup /rmuser /pban",
                parse_mode="HTML"
            )
        except Exception:
            pass

    logger.info("Bot started successfully!")


async def post_shutdown(application: Application):
    """Clean up on shutdown."""
    await db.close()
    logger.info("Database closed. Bot shut down.")


async def _scheduled_start_job(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled start job."""
    from handlers.owner import _do_start_giveaway
    data = context.job.data
    await _do_start_giveaway(context.bot, data["giveaway_id"])


async def _scheduled_end_job(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled end job."""
    from handlers.owner import _do_end_giveaway
    data = context.job.data
    await _do_end_giveaway(context.bot, data["giveaway_id"])


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler."""
    logger.error(f"Exception: {context.error}", exc_info=context.error)


def main():
    """Build and run the bot."""
    logger.info("Starting Smash Giveaway Bot...")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ─── Register Handlers ───

    # Giveaway setup conversation (must be first)
    app.add_handler(get_sg_conversation_handler())

    # Owner commands
    app.add_handler(CommandHandler("set", set_channels))
    app.add_handler(CommandHandler("choosewinner", choose_winner))
    app.add_handler(CommandHandler("chanceup", chance_up))
    app.add_handler(CommandHandler("rmuser", rm_user))
    app.add_handler(CommandHandler("pban", pban))
    app.add_handler(CommandHandler("glist", glist))
    app.add_handler(CommandHandler("gstats", gstats))
    app.add_handler(CommandHandler("ghistory", ghistory))
    app.add_handler(CommandHandler("gend", gend))
    app.add_handler(CommandHandler("fwd", fwd_broadcast))

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("part", part))
    app.add_handler(CommandHandler("mypart", mypart))

    # Language
    app.add_handler(CommandHandler("language", language_command))

    # Callback queries
    app.add_handler(CallbackQueryHandler(sg_confirm_callback, pattern=r"^sg_confirm$"))
    app.add_handler(CallbackQueryHandler(sg_cancel_callback, pattern=r"^sg_cancel$"))
    app.add_handler(CallbackQueryHandler(part_callback, pattern=r"^part_"))
    app.add_handler(CallbackQueryHandler(verify_join_callback, pattern=r"^verify_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern=r"^lang_"))
    app.add_handler(CallbackQueryHandler(glist_page_callback, pattern=r"^glist_"))

    # Error handler
    app.add_error_handler(error_handler)

    # Run
    logger.info("Bot polling started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
