from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Dict, List
import asyncio
from datetime import datetime
import pytz

class AdminCommands:
    def __init__(self, bot: Client, db, config, bot_instance=None):
        self.bot = bot
        self.db = db
        self.config = config
        self.bot_instance = bot_instance  # Reference to main bot instance
        
        # Register admin commands (private only for security)
        self.bot.on_message(filters.command("sgive") & filters.private)(self.create_giveaway)
        self.bot.on_message(filters.command("end") & filters.private)(self.end_giveaway)
        self.bot.on_message(filters.command("cwinner") & filters.private)(self.manual_winner)
        self.bot.on_message(filters.command("parts") & filters.private)(self.view_participants)
        self.bot.on_message(filters.command("rmpart") & filters.private)(self.remove_participant)
        self.bot.on_message(filters.command("pban") & filters.private)(self.ban_user)
        self.bot.on_message(filters.command("punban") & filters.private)(self.unban_user)
        self.bot.on_message(filters.command("set") & filters.private)(self.set_broadcast)
        self.bot.on_message(filters.command("gstats") & filters.private)(self.giveaway_stats)
    
    async def is_owner(self, user_id: int) -> bool:
        """Check if user is owner"""
        return user_id == self.config.OWNER_ID
    
    async def create_giveaway(self, client: Client, message: Message):
        """Create giveaway wizard (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        # Start giveaway creation wizard
        giveaway_handler = None
        
        # Try to get giveaway_handler from bot attribute
        if hasattr(self.bot, 'giveaway_handler'):
            giveaway_handler = self.bot.giveaway_handler
        
        # If not found, try to get from bot_instance
        if not giveaway_handler and self.bot_instance:
            giveaway_handler = getattr(self.bot_instance, 'giveaway_handler', None)
        
        # If still not found, create new instance
        if not giveaway_handler:
            from handlers.giveaway_handler import GiveawayHandler
            giveaway_handler = GiveawayHandler(self.bot, self.db, self.config)
            # Store it for future use
            self.bot.giveaway_handler = giveaway_handler
        
        await giveaway_handler.start_creation_wizard(message)
    
    async def end_giveaway(self, client: Client, message: Message):
        """Force end a giveaway (works in both private and groups for admin)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply("Usage: /end <giveaway_id>")
            return
        
        giveaway_id = args[1]
        giveaway = await self.db.get_giveaway(giveaway_id)
        
        if not giveaway:
            await message.reply("❌ Giveaway not found.")
            return
        
        # End giveaway
        from utils.scheduler import GiveawayScheduler
        scheduler = GiveawayScheduler(self.bot, self.db)
        await scheduler.end_giveaway(giveaway_id)
        
        await message.reply(f"""
✅ **Giveaway Ended Successfully**

**Event:** {giveaway.get('event_name', 'Unknown')}
**Giveaway ID:** `{giveaway_id}`

Winners have been selected and announced.
        """)
    
    async def manual_winner(self, client: Client, message: Message):
        """Manually set winner (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 3:
            await message.reply("Usage: /cwinner <giveaway_id> <user_id>")
            return
        
        giveaway_id = args[1]
        try:
            user_id = int(args[2])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
        
        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            await message.reply("❌ Giveaway not found.")
            return
        
        # Check if user is participant
        if not await self.db.is_participant(giveaway_id, user_id):
            await message.reply("❌ User is not a participant in this giveaway.")
            return
        
        # Add as winner
        await self.db.add_winner(giveaway_id, user_id)
        
        # Get user info
        try:
            user = await client.get_users(user_id)
            user_mention = user.username if user.username else user.first_name
        except:
            user_mention = str(user_id)
        
        await message.reply(f"""
✅ **Manual Winner Set**

**User:** {user_mention}
**User ID:** `{user_id}`
**Giveaway:** {giveaway.get('event_name', giveaway_id)}
**Giveaway ID:** `{giveaway_id}`

Winner has been added to the database.
        """)
        
        # Log the action
        await self.db.add_log(
            "manual_winner_set",
            message.from_user.id,
            giveaway_id,
            f"Manually set user {user_id} as winner"
        )
    
    async def view_participants(self, client: Client, message: Message):
        """View giveaway participants (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply("Usage: /parts <giveaway_id> [page]")
            return
        
        giveaway_id = args[1]
        page = int(args[2]) if len(args) > 2 else 0
        
        participants = await self.db.get_participants(giveaway_id)
        
        if not participants:
            await message.reply("📭 No participants found for this giveaway.")
            return
        
        # Paginate participants
        participant_list = list(participants.items())
        total_participants = len(participant_list)
        items_per_page = self.config.MAX_PARTICIPANTS_PER_PAGE
        
        total_pages = (total_participants + items_per_page - 1) // items_per_page
        page = max(0, min(page, total_pages - 1))
        
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, total_participants)
        
        # Format message
        giveaway = await self.db.get_giveaway(giveaway_id)
        giveaway_name = giveaway.get('event_name', giveaway_id) if giveaway else giveaway_id
        
        text = f"""
👥 **Participants for: {giveaway_name}**

**🎫 Giveaway ID:** `{giveaway_id}`
**📊 Total Participants:** {total_participants}
**📄 Page:** {page + 1}/{total_pages}
        """
        
        for i, (user_id_str, user_data) in enumerate(participant_list[start_idx:end_idx], start=1):
            user_id = int(user_id_str)
            joined_at = user_data.get('joined_at', 'Unknown')
            
            # Try to get user info
            try:
                user = await client.get_users(user_id)
                username = f"@{user.username}" if user.username else user.first_name
            except:
                username = f"User {user_id}"
            
            text += f"\n**{start_idx + i}. {username}**"
            text += f"\n   🆔 ID: `{user_id}`"
            text += f"\n   ⏰ Joined: {joined_at[:19]}"
        
        # Create pagination buttons
        from utils.helpers import Helpers
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("◀️ Previous", 
                         callback_data=f"admin_parts_{giveaway_id}_{page-1}"))
        
        buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", 
                     callback_data="noop"))
        
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ▶️", 
                         callback_data=f"admin_parts_{giveaway_id}_{page+1}"))
        
        # Add remove button
        remove_button = InlineKeyboardButton("❌ Remove Participant", 
                        callback_data=f"remove_part_menu_{giveaway_id}")
        
        markup = InlineKeyboardMarkup([buttons, [remove_button]]) if buttons else InlineKeyboardMarkup([[remove_button]])
        
        await message.reply(text, reply_markup=markup)
    
    async def remove_participant(self, client: Client, message: Message):
        """Remove participant from giveaway (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 3:
            await message.reply("Usage: /rmpart <giveaway_id> <user_id>")
            return
        
        giveaway_id = args[1]
        try:
            user_id = int(args[2])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
        
        # Remove participant
        if await self.db.remove_participant(giveaway_id, user_id):
            await message.reply(f"""
✅ **Participant Removed**

**User ID:** `{user_id}`
**Giveaway ID:** `{giveaway_id}`

User has been removed from the giveaway.
            """)
            
            # Log the action
            await self.db.add_log(
                "participant_removed",
                message.from_user.id,
                giveaway_id,
                f"Removed user {user_id}"
            )
        else:
            await message.reply("❌ User not found in giveaway.")
    
    async def ban_user(self, client: Client, message: Message):
        """Ban user globally (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply("Usage: /pban <user_id> [reason]")
            return
        
        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
        
        reason = " ".join(args[2:]) if len(args) > 2 else "No reason provided"
        
        # Ban user
        await self.db.ban_user(user_id, reason, message.from_user.id)
        
        try:
            user = await client.get_users(user_id)
            user_info = f"@{user.username}" if user.username else user.first_name
        except:
            user_info = str(user_id)
        
        await message.reply(f"""
✅ **User Banned Globally**

**👤 User:** {user_info}
**🆔 ID:** `{user_id}`
**📝 Reason:** {reason}

User can no longer use the bot.
        """)
    
    async def unban_user(self, client: Client, message: Message):
        """Unban user (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.reply("Usage: /punban <user_id>")
            return
        
        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid user ID.")
            return
        
        # Unban user
        if await self.db.unban_user(user_id, message.from_user.id):
            try:
                user = await client.get_users(user_id)
                user_info = f"@{user.username}" if user.username else user.first_name
            except:
                user_info = str(user_id)
            
            await message.reply(f"""
✅ **User Unbanned**

**👤 User:** {user_info}
**🆔 ID:** `{user_id}`

User can now use the bot again.
            """)
        else:
            await message.reply("❌ User not found in ban list.")
    
    async def set_broadcast(self, client: Client, message: Message):
        """Set broadcast chats using usernames (private only)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            # Show current broadcast chats
            broadcast_chats = await self.db.get_broadcast_chats()
            if not broadcast_chats:
                await message.reply("📭 No broadcast chats set.\n\nUsage: /set @username1 @username2 ...")
                return
            
            text = "📢 **Current Broadcast Chats:**\n\n"
            for chat in broadcast_chats:
                chat_username = chat.get('username', 'Unknown')
                chat_name = chat.get('name', f"@{chat_username}")
                text += f"• {chat_name} (@{chat_username})\n"
            
            text += "\nTo add more, use: /set @username1 @username2 ..."
            await message.reply(text)
            return
        
        # Parse usernames
        usernames = []
        for arg in args[1:]:
            username = arg.strip().lstrip('@')
            if username:
                usernames.append(username)
        
        if not usernames:
            await message.reply("❌ Please provide valid usernames (with or without @).")
            return
        
        # Add new broadcast chats
        added = 0
        failed = []
        
        for username in usernames:
            try:
                # Verify the chat exists and bot can access it
                chat = await client.get_chat(f"@{username}")
                
                # Store chat info
                chat_info = {
                    'username': username,
                    'name': chat.title,
                    'chat_id': chat.id,
                    'added_by': message.from_user.id,
                }
                
                if await self.db.add_broadcast_chat(chat_info):
                    added += 1
                else:
                    failed.append(f"@{username} (already exists)")
                    
            except Exception as e:
                failed.append(f"@{username} (error: {str(e)})")
        
        result_text = f"✅ Added {added} broadcast chats.\n"
        if failed:
            result_text += f"\n❌ Failed to add {len(failed)} chats:\n"
            for fail in failed:
                result_text += f"• {fail}\n"
        
        await message.reply(result_text)
    
    async def giveaway_stats(self, client: Client, message: Message):
        """Show giveaway statistics (works in both private and groups for admin)"""
        if not await self.is_owner(message.from_user.id):
            await message.reply("❌ This command is only for bot owner.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            # Show all giveaways if no ID specified
            giveaways = await self.db.get_active_giveaways()
            
            if not giveaways:
                await message.reply("📊 No active giveaways found.")
                return
            
            text = "📊 **Active Giveaways**\n\n"
            for giveaway in giveaways[:10]:  # Show only first 10
                giveaway_id = giveaway['id']
                participants = await self.db.get_participants(giveaway_id)
                winners = await self.db.get_winners(giveaway_id)
                
                from utils.helpers import Helpers
                start_time = datetime.fromisoformat(giveaway.get('start_time'))
                end_time = datetime.fromisoformat(giveaway.get('end_time'))
                
                text += f"**🏷 Event:** {giveaway.get('event_name', 'N/A')}\n"
                text += f"**🎫 ID:** `{giveaway_id}`\n"
                text += f"**🎁 Prize:** {giveaway.get('prize_type', 'N/A').title()} - {giveaway.get('prize_details', 'N/A')}\n"
                text += f"**👥 Participants:** {len(participants)}\n"
                text += f"**🏆 Winners:** {len(winners)}\n"
                text += f"**⏰ Ends:** {Helpers.format_ist_time(end_time)}\n"
                text += f"**⏳ Time Left:** {Helpers.get_time_remaining(end_time)}\n"
                text += "─" * 30 + "\n"
            
            if len(giveaways) > 10:
                text += f"\n... and {len(giveaways) - 10} more giveaways."
            
            await message.reply(text)
            return
        
        # Show specific giveaway stats
        giveaway_id = args[1]
        giveaway = await self.db.get_giveaway(giveaway_id)
        
        if not giveaway:
            await message.reply("❌ Giveaway not found.")
            return
        
        participants = await self.db.get_participants(giveaway_id)
        winners = await self.db.get_winners(giveaway_id)
        
        from utils.helpers import Helpers
        
        text = f"""
📊 **Giveaway Statistics** 📊

**🎫 ID:** `{giveaway_id}`
**🏷 Event:** {giveaway.get('event_name', 'N/A')}
**🎁 Prize:** {giveaway.get('prize_type', 'N/A').title()} - {giveaway.get('prize_details', 'N/A')}
**🏆 Winner Count:** {giveaway.get('winner_count', 0)}
**📊 Status:** {giveaway.get('status', 'unknown').upper()}
**⏰ Start Time:** {Helpers.format_ist_time(datetime.fromisoformat(giveaway.get('start_time')))}
**⏰ End Time:** {Helpers.format_ist_time(datetime.fromisoformat(giveaway.get('end_time')))}
**👥 Participants:** {len(participants)}
**🏆 Winners:** {len(winners)}
        """
        
        # Add time remaining if active
        if giveaway.get('status') == 'active':
            end_time = datetime.fromisoformat(giveaway.get('end_time'))
            time_left = Helpers.get_time_remaining(end_time)
            text += f"\n**⏳ Time Left:** {time_left}"
        
        if winners:
            text += "\n\n**🏆 Winners:**\n"
            for i, winner in enumerate(winners, 1):
                user_id = winner.get('user_id')
                try:
                    user = await client.get_users(user_id)
                    username = f"@{user.username}" if user.username else user.first_name
                except:
                    username = str(user_id)
                
                claimed = "✅" if winner.get('prize_claimed') else "❌"
                text += f"{i}. {username} (ID: {user_id}) {claimed}\n"
        
        # Add button to view participants
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("👥 View Participants", callback_data=f"admin_parts_{giveaway_id}_0")
        ]])
        
        await message.reply(text, reply_markup=keyboard)
