"""
Centralized multilingual text templates.
All user-facing strings go here as key-based templates.
"""

TEXT = {
    "en": {
        # ─── Language ───
        "language_prompt": "🌍 <b>Select Your Language</b>",
        "language_updated": "✅ Language updated to <b>English</b>.",

        # ─── Start ───
        "start_welcome": (
            "👋 <b>Welcome to Smash Giveaway Bot!</b>\n\n"
            "🎁 Use /part to join active giveaways\n"
            "🌍 Use /language to set your language\n"
            "📊 Use /mypart to see your stats"
        ),

        # ─── Giveaway Setup ───
        "sg_ask_title": "📝 <b>Step 1/6</b> — Enter the giveaway <b>title</b>:",
        "sg_ask_reward": "🎁 <b>Step 2/6</b> — Enter the <b>reward</b>:",
        "sg_ask_winners": "🏆 <b>Step 3/6</b> — How many <b>winners</b>?",
        "sg_ask_start": "⏰ <b>Step 4/6</b> — Enter <b>start time</b> (IST)\nFormat: <code>YYYY-MM-DD HH:MM</code>",
        "sg_ask_end": "⏰ <b>Step 5/6</b> — Enter <b>end time</b> (IST)\nFormat: <code>YYYY-MM-DD HH:MM</code>",
        "sg_ask_requirements": (
            "📌 <b>Step 6/6</b> — Enter join <b>requirements</b>\n"
            "Send channel/group IDs separated by commas, or <code>none</code> for no requirements."
        ),
        "sg_invalid_winners": "❌ Please enter a valid number greater than 0.",
        "sg_invalid_time": "❌ Invalid time format. Use: <code>YYYY-MM-DD HH:MM</code>",
        "sg_end_before_start": "❌ End time must be after start time.",
        "sg_start_in_past": "❌ Start time cannot be in the past.",

        # ─── Giveaway Preview ───
        "sg_preview": (
            "📋 <b>GIVEAWAY PREVIEW</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏷 <b>Title:</b> {title}\n"
            "🎁 <b>Reward:</b> {reward}\n"
            "🏆 <b>Winners:</b> {winners_count}\n\n"
            "⏰ <b>Start:</b> {start_time}\n"
            "⏰ <b>End:</b> {end_time}\n"
            "⏳ <b>Duration:</b> {duration}\n\n"
            "🆔 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "✅ Confirm or ❌ Cancel?"
        ),
        "sg_confirmed": "✅ Giveaway <b>{giveaway_id}</b> has been created and scheduled!",
        "sg_cancelled": "❌ Giveaway setup cancelled.",
        "sg_already_active": "⚠️ A giveaway is already active. End it first with /gend.",

        # ─── Giveaway Announcement ───
        "giveaway_announcement": (
            "🎉 <b>SMASH OFFICIAL GIVEAWAY</b> 🎉\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏷 <b>Event:</b> {title}\n"
            "🎁 <b>Reward:</b> {reward}\n"
            "🏆 <b>Winners:</b> {winners_count}\n\n"
            "⏰ <b>Start:</b> {start_time}\n"
            "⏰ <b>End:</b> {end_time}\n\n"
            "⏳ <b>Duration:</b> {duration}\n\n"
            "📌 Join using /part\n\n"
            "🆔 <b>Giveaway ID:</b> <code>{giveaway_id}</code>"
        ),

        # ─── Join / Part ───
        "join_prompt": (
            "🎉 <b>Join Giveaway: {title}</b>\n\n"
            "🎁 <b>Reward:</b> {reward}\n"
            "🏆 <b>Winners:</b> {winners_count}\n\n"
            "📌 <b>Required Channels/Groups:</b>\n{requirements}\n\n"
            "After joining all channels, tap <b>✅ I Joined</b> below."
        ),
        "join_success": "✅ You have successfully joined the giveaway <b>{title}</b>!",
        "join_fail_missing": "❌ You haven't joined all required channels. Please join them first.",
        "join_fail_banned": "🚫 You are permanently banned from giveaways.",
        "join_fail_already": "⚠️ You have already joined this giveaway.",
        "join_fail_not_active": "⚠️ There is no active giveaway right now.",
        "join_fail_invalid": "❌ Invalid giveaway ID.",
        "join_button_dm": "📩 Start in DM",
        "join_button_part": "🎉 Take Part",
        "join_button_joined": "✅ I Joined",
        "no_active_giveaway": "⚠️ There is no active giveaway at the moment.",

        # ─── My Participation ───
        "mypart_stats": (
            "📊 <b>Your Giveaway Stats</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>Total Joined:</b> {joined_count}\n"
            "🏆 <b>Total Wins:</b> {won_count}\n"
            "📈 <b>Win Rate:</b> {win_rate}%\n\n"
            "📅 <b>Last Joined:</b> {last_joined}\n"
            "🏅 <b>Last Won:</b> {last_won}"
        ),
        "mypart_empty": "📭 You haven't participated in any giveaways yet.",

        # ─── Winner Announcement ───
        "winner_announcement": (
            "🏆 <b>GIVEAWAY ENDED!</b> 🏆\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🏷 <b>Event:</b> {title}\n"
            "🎁 <b>Reward:</b> {reward}\n\n"
            "🎉 <b>Winners:</b>\n{winner_list}\n\n"
            "👥 <b>Total Participants:</b> {total_participants}\n\n"
            "🆔 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n\n"
            "Congratulations to all winners! 🥳"
        ),
        "winner_dm": (
            "🎉 <b>Congratulations!</b> 🎉\n\n"
            "You won the giveaway <b>{title}</b>!\n"
            "🎁 <b>Reward:</b> {reward}\n\n"
            "🆔 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n\n"
            "Please wait for the owner to contact you."
        ),
        "no_participants": "⚠️ No eligible participants found. Cannot pick winners.",

        # ─── Owner Commands ───
        "set_channels_success": "✅ Target channels updated: {channels}",
        "set_channels_usage": "Usage: <code>/set channel_id1,channel_id2,...</code>",
        "choosewinner_success": "✅ User <code>{user_id}</code> manually selected as winner #{winner_number}.",
        "choosewinner_fail": "❌ User <code>{user_id}</code> is not a valid participant or is banned.",
        "choosewinner_usage": "Usage: <code>/choosewinner user_id winner_number</code>",
        "chanceup_success": "✅ User <code>{user_id}</code> boost set to <b>+{percentage}%</b> (weight: {weight}).",
        "chanceup_fail": "❌ User <code>{user_id}</code> is not a participant in the current giveaway.",
        "chanceup_usage": "Usage: <code>/chanceup user_id percentage</code>",
        "rmuser_success": "✅ User <code>{user_id}</code> silently removed from giveaway.",
        "rmuser_fail": "❌ User <code>{user_id}</code> not found in current giveaway.",
        "rmuser_usage": "Usage: <code>/rmuser user_id</code>",
        "pban_success": "🚫 User <code>{user_id}</code> permanently banned from all giveaways.",
        "pban_already": "⚠️ User <code>{user_id}</code> is already banned.",
        "pban_usage": "Usage: <code>/pban user_id [reason]</code>",
        "not_owner": "🚫 You do not have permission to use this command.",

        # ─── Giveaway List ───
        "glist_header": "👥 <b>Total Participants:</b> {total}\n📄 <b>Page:</b> {page}/{total_pages}\n━━━━━━━━━━━━━━━━━━━━\n",
        "glist_user": (
            "{num}. <b>ᴜsᴇʀ:</b> {full_name}\n"
            "   <b>ɪᴅ:</b> <code>{user_id}</code>\n"
            "   <b>ᴜsᴇʀɴᴀᴍᴇ:</b> @{username}\n"
        ),
        "glist_empty": "📭 No participants yet.",

        # ─── Giveaway Stats ───
        "gstats_output": (
            "📊 <b>GIVEAWAY STATS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🆔 <b>ID:</b> <code>{giveaway_id}</code>\n"
            "🏷 <b>Title:</b> {title}\n"
            "🎁 <b>Reward:</b> {reward}\n"
            "📌 <b>Status:</b> {status}\n\n"
            "⏰ <b>Start:</b> {start_time}\n"
            "⏰ <b>End:</b> {end_time}\n"
            "⏳ <b>Duration:</b> {duration}\n\n"
            "👥 <b>Total Participants:</b> {total_participants}\n"
            "⚡ <b>Boosted Users:</b> {boosted_users}\n"
            "🚫 <b>Banned Users:</b> {banned_users}\n"
            "🏆 <b>Winners Count:</b> {winners_count}\n"
            "📡 <b>Target Chats:</b> {target_chats}\n"
            "⏱ <b>Runtime:</b> {runtime}"
        ),

        # ─── Giveaway History ───
        "ghistory_header": "📜 <b>GIVEAWAY HISTORY</b>\n━━━━━━━━━━━━━━━━━━━━\n",
        "ghistory_item": (
            "\n🆔 <code>{giveaway_id}</code>\n"
            "🏷 {title} — 🎁 {reward}\n"
            "⏰ {start_time} → {end_time}\n"
            "🏆 Winners: {winners}\n"
            "👥 Participants: {participants_count}\n"
            "📌 Status: {status}\n"
            "👤 By: {created_by} | Ended: {ended_by}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        "ghistory_empty": "📭 No giveaway history yet.",

        # ─── Giveaway End ───
        "gend_success": "✅ Giveaway <b>{giveaway_id}</b> has been force-ended.",
        "gend_no_active": "⚠️ No active giveaway to end.",

        # ─── Join Log (Owner DM) ───
        "join_log": (
            "🚀 <b>ɴᴇᴡ ᴜsᴇʀ Joined!</b>\n\n"
            "ᴜsᴇʀ: {full_name}\n"
            "ɪᴅ: <code>{user_id}</code>\n"
            "ᴜsᴇʀɴᴀᴍᴇ: @{username}\n"
            "ᴛᴏᴛᴀʟ ᴜsᴇʀs: {total_users}\n\n"
            "Giveaway ID: <code>{giveaway_id}</code>\n"
            "Join Time: {join_time}\n"
            "Verification: {verification}\n"
            "Language: {language}\n"
            "Source: {source}"
        ),

        # ─── Errors ───
        "error_generic": "❌ An error occurred. Please try again.",
        "error_not_dm": "📩 Please use this command in a DM with the bot.",
        "error_bot_not_admin": "⚠️ Bot is not an admin in the required channel: {channel}",
    },

    "fr": {
        "language_prompt": "🌍 <b>Sélectionnez votre langue</b>",
        "language_updated": "✅ Langue définie sur <b>Français</b>.",
        "start_welcome": (
            "👋 <b>Bienvenue sur Smash Giveaway Bot !</b>\n\n"
            "🎁 Utilisez /part pour rejoindre les giveaways\n"
            "🌍 Utilisez /language pour changer la langue\n"
            "📊 Utilisez /mypart pour voir vos stats"
        ),
        "join_success": "✅ Vous avez rejoint le giveaway <b>{title}</b> avec succès !",
        "join_fail_missing": "❌ Vous n'avez pas rejoint tous les canaux requis.",
        "join_fail_banned": "🚫 Vous êtes banni des giveaways.",
        "join_fail_already": "⚠️ Vous avez déjà rejoint ce giveaway.",
        "join_fail_not_active": "⚠️ Aucun giveaway actif en ce moment.",
        "join_button_dm": "📩 Démarrer en DM",
        "join_button_part": "🎉 Participer",
        "join_button_joined": "✅ J'ai rejoint",
        "no_active_giveaway": "⚠️ Aucun giveaway actif en ce moment.",
        "mypart_stats": (
            "📊 <b>Vos Stats de Giveaway</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎯 <b>Total Rejoint:</b> {joined_count}\n"
            "🏆 <b>Total Victoires:</b> {won_count}\n"
            "📈 <b>Taux de Victoire:</b> {win_rate}%\n\n"
            "📅 <b>Dernier Rejoint:</b> {last_joined}\n"
            "🏅 <b>Dernière Victoire:</b> {last_won}"
        ),
        "mypart_empty": "📭 Vous n'avez participé à aucun giveaway.",
        "winner_dm": (
            "🎉 <b>Félicitations !</b> 🎉\n\n"
            "Vous avez gagné le giveaway <b>{title}</b> !\n"
            "🎁 <b>Récompense:</b> {reward}\n\n"
            "🆔 <b>ID Giveaway:</b> <code>{giveaway_id}</code>\n\n"
            "Veuillez attendre que le propriétaire vous contacte."
        ),
        "join_prompt": (
            "🎉 <b>Rejoindre le Giveaway : {title}</b>\n\n"
            "🎁 <b>Récompense :</b> {reward}\n"
            "🏆 <b>Gagnants :</b> {winners_count}\n\n"
            "📌 <b>Canaux requis :</b>\n{requirements}\n\n"
            "Après avoir rejoint tous les canaux, appuyez sur <b>✅ J'ai rejoint</b>."
        ),
        "error_generic": "❌ Une erreur s'est produite. Réessayez.",
    },

    "id": {
        "language_prompt": "🌍 <b>Pilih Bahasa Anda</b>",
        "language_updated": "✅ Bahasa diatur ke <b>Bahasa Indonesia</b>.",
        "start_welcome": (
            "👋 <b>Selamat datang di Smash Giveaway Bot!</b>\n\n"
            "🎁 Gunakan /part untuk bergabung giveaway\n"
            "🌍 Gunakan /language untuk mengatur bahasa\n"
            "📊 Gunakan /mypart untuk melihat statistik"
        ),
        "join_success": "✅ Anda berhasil bergabung dengan giveaway <b>{title}</b>!",
        "join_fail_missing": "❌ Anda belum bergabung dengan semua channel yang diperlukan.",
        "join_fail_banned": "🚫 Anda dilarang dari giveaway.",
        "join_fail_already": "⚠️ Anda sudah bergabung dengan giveaway ini.",
        "join_fail_not_active": "⚠️ Tidak ada giveaway aktif saat ini.",
        "no_active_giveaway": "⚠️ Tidak ada giveaway aktif saat ini.",
        "mypart_empty": "📭 Anda belum berpartisipasi dalam giveaway apa pun.",
        "error_generic": "❌ Terjadi kesalahan. Silakan coba lagi.",
    },

    "fa": {
        "language_prompt": "🌍 <b>زبان خود را انتخاب کنید</b>",
        "language_updated": "✅ زبان به <b>فارسی</b> تنظیم شد.",
        "start_welcome": (
            "👋 <b>به ربات قرعه‌کشی Smash خوش آمدید!</b>\n\n"
            "🎁 از /part برای شرکت در قرعه‌کشی استفاده کنید\n"
            "🌍 از /language برای تنظیم زبان استفاده کنید\n"
            "📊 از /mypart برای مشاهده آمار استفاده کنید"
        ),
        "join_success": "✅ شما با موفقیت در قرعه‌کشی <b>{title}</b> شرکت کردید!",
        "join_fail_missing": "❌ شما هنوز به همه کانال‌های مورد نیاز نپیوسته‌اید.",
        "join_fail_banned": "🚫 شما از قرعه‌کشی‌ها محروم شده‌اید.",
        "join_fail_already": "⚠️ شما قبلاً در این قرعه‌کشی شرکت کرده‌اید.",
        "join_fail_not_active": "⚠️ در حال حاضر قرعه‌کشی فعالی وجود ندارد.",
        "no_active_giveaway": "⚠️ در حال حاضر قرعه‌کشی فعالی وجود ندارد.",
        "mypart_empty": "📭 شما هنوز در هیچ قرعه‌کشی شرکت نکرده‌اید.",
        "error_generic": "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
    },

    "ru": {
        "language_prompt": "🌍 <b>Выберите ваш язык</b>",
        "language_updated": "✅ Язык изменен на <b>Русский</b>.",
        "start_welcome": (
            "👋 <b>Добро пожаловать в Smash Giveaway Bot!</b>\n\n"
            "🎁 Используйте /part для участия в розыгрышах\n"
            "🌍 Используйте /language для выбора языка\n"
            "📊 Используйте /mypart для просмотра статистики"
        ),
        "join_success": "✅ Вы успешно присоединились к розыгрышу <b>{title}</b>!",
        "join_fail_missing": "❌ Вы не вступили во все необходимые каналы.",
        "join_fail_banned": "🚫 Вы заблокированы в розыгрышах.",
        "join_fail_already": "⚠️ Вы уже участвуете в этом розыгрыше.",
        "join_fail_not_active": "⚠️ Сейчас нет активных розыгрышей.",
        "no_active_giveaway": "⚠️ Сейчас нет активных розыгрышей.",
        "mypart_empty": "📭 Вы еще не участвовали ни в одном розыгрыше.",
        "error_generic": "❌ Произошла ошибка. Попробуйте снова.",
    },
}


def t(user_lang: str, key: str, **kwargs) -> str:
    """Get translated text by key with fallback to English."""
    lang_pack = TEXT.get(user_lang, TEXT["en"])
    text = lang_pack.get(key, TEXT["en"].get(key, key))
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
