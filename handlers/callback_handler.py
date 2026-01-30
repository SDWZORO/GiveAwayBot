[file name]: callback_handler.py
[file content begin]
from pyrogram import Client
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime
import pytz
import asyncio
import logging

logger = logging.getLogger(__name__)

class CallbackHandler:
    def __init__(self, bot: Client, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        
        # Register callback handlers
        self.bot.on_callback_query()(self.handle_callback)
    
    async def handle_callback(self, client: Client, callback_query: CallbackQuery):
        """Handle all callback queries"""
        data = callback_query.data
        
        try:
            # Check if user is banned
            user_id = callback_query.from_user.id
            if await self.db.is_banned(user_id):
                await callback_query.answer("🚫 You are banned from using this bot!", show_alert=True)
                return
            
            if data.startswith("verify_sub_"):
                await self.handle_verify_subscription(callback_query)
            elif data.startswith("check_subscription"):
                await self.handle_check_subscription(callback_query)
            elif data.startswith("admin_parts_"):
                await self.handle_admin_participants(callback_query)
            elif data.startswith("remove_part_menu_"):
                await self.handle_remove_participant_menu(callback_query)
            elif data.startswith("remove_part_"):
                await self.handle_remove_participant(callback_query)
            elif data == "confirm_create":
                await self.handle_confirm_create(callback_query)
            elif data == "cancel_create":
                await self.handle_cancel_create(callback_query)
            elif data.startswith("giveaway_end_"):
                await self.handle_end_giveaway(callback_query)
            elif data == "noop":
                await callback_query.answer()
            else:
                await callback_query.answer("❌ Unknown action!", show_alert=True)
        
        except Exception as e:
            logger.error(f"❌ Error handling callback: {e}", exc_info=True)
            try:
                await callback_query.answer("❌ An error occurred! Please try again.", show_alert=True)
            except:
                pass
    
    async def get_giveaway_handler(self):
        """Get giveaway handler instance"""
        # Try to get from bot attribute
        if hasattr(self.bot, 'giveaway_handler'):
            return self.bot.giveaway_handler
        
        # Try to create new instance
        from handlers.giveaway_handler import GiveawayHandler
        giveaway_handler = GiveawayHandler(self.bot, self.db, self.config)
        self.bot.giveaway_handler = giveaway_handler
        return giveaway_handler
    
    async def handle_verify_subscription(self, callback_query: CallbackQuery):
        """Handle subscription verification"""
        user_id = callback_query.from_user.id
        giveaway_id = callback_query.data.replace("verify_sub_", "")
        
        # Check if in group chat - redirect to private
        if callback_query.message.chat.type != "private":
            try:
                await callback_query.answer(
                    "⚠️ Please use this button in private chat with me for better experience!",
                    show_alert=True
                )
                # Try to send a message in private
                try:
                    await self.bot.send_message(
                        user_id,
                        f"👋 Hello! Please click the button below to continue:\n\n"
                        f"Giveaway ID: `{giveaway_id}`",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(
                                "✅ Verify Subscription",
                                callback_data=f"verify_sub_{giveaway_id}"
                            )
                        ]])
                    )
                except:
                    pass
                return
            except:
                pass
        
        # Check cooldown
        if not await self.db.check_cooldown(user_id, "check_subscription"):
            remaining = await self.db.get_remaining_cooldown(user_id, "check_subscription")
            await callback_query.message.edit_text(
                f"⏳ **Please wait {remaining} seconds before checking again.**"
            )
            await callback_query.answer()
            return
        
        # Set cooldown
        await self.db.set_cooldown(user_id, "check_subscription", self.config.COOLDOWN_CHECK)
        
        # Show checking message
        await callback_query.message.edit_text("🔍 **Checking your subscriptions...**")
        
        # Check subscription
        from utils.channel_checker import ChannelChecker
        checker = ChannelChecker(self.bot, self.config.REQUIRED_CHANNELS)
        subscribed, missing = await checker.check_subscription(user_id)
        
        if not subscribed:
            # Still not subscribed
            text = "❌ **Subscription Check Failed**\n\n"
            text += "You must join all these channels to participate:\n\n"
            
            for channel in missing:
                text += f"• {channel['name']}\n"
            
            text += "\nClick the buttons below to join, then verify again."
            
            # Create new buttons
            buttons = []
            for channel in missing:
                if channel.get('username'):
                    url = f"https://t.me/{channel['username']}"
                else:
                    url = f"tg://resolve?domain={channel['id']}"
                
                buttons.append([
                    InlineKeyboardButton(
                        f"📢 Join {channel['name']}",
                        url=url
                    )
                ])
            
            buttons.append([
                InlineKeyboardButton(
                    "🔄 Check Again",
                    callback_data=f"verify_sub_{giveaway_id}"
                )
            ])
            
            markup = InlineKeyboardMarkup(buttons)
            await callback_query.message.edit_text(text, reply_markup=markup)
            await callback_query.answer("❌ Please join all channels!")
            return
        
        # User is subscribed, check other requirements
        from utils.validation import UserValidator
        validator = UserValidator(self.config)
        
        valid, reason, _ = await validator.validate_participation(
            callback_query.from_user, giveaway_id, self.db, self.bot
        )
        
        if not valid and reason != "subscription_required":
            await callback_query.message.edit_text(reason)
            await callback_query.answer()
            return
        
        # Get giveaway
        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            await callback_query.message.edit_text("❌ Giveaway not found.")
            await callback_query.answer()
            return
        
        # Add participant
        user_data = {
            "username": callback_query.from_user.username,
            "first_name": callback_query.from_user.first_name,
            "last_name": callback_query.from_user.last_name,
            "joined_at": datetime.now(pytz.UTC).isoformat()
        }
        
        success, message = await self.db.add_participant(giveaway_id, user_id, user_data)
        
        if success:
            # Set participation cooldown
            await self.db.set_cooldown(user_id, "participate", self.config.COOLDOWN_PARTICIPATE)
            
            # Update message with success
            success_text = f"""
🎉 **Entry Confirmed!** 🎉

**🏷 Event:** {giveaway['event_name']}
**🎁 Prize:** {giveaway['prize_details']}
**🎫 Your Entry ID:** `{user_id}_{giveaway_id}`
**⏰ Joined At:** {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}

Good luck! 🍀 May you win this giveaway!
            """
            
            await callback_query.message.edit_text(success_text)
            
            # Log to owner
            from handlers.user_commands import UserCommands
            user_handler = UserCommands(self.bot, self.db, self.config)
            await user_handler.log_participation_to_owner(
                callback_query.from_user, giveaway
            )
            
            # Add to logs
            await self.db.add_log(
                "user_joined",
                user_id,
                giveaway_id,
                f"User joined via subscription check: {giveaway['event_name']}"
            )
            
            await callback_query.answer("✅ Successfully joined giveaway!")
        else:
            await callback_query.message.edit_text(f"❌ {message}")
            await callback_query.answer()
    
    async def handle_check_subscription(self, callback_query: CallbackQuery):
        """Handle check subscription callback"""
        # Get active giveaway
        active_giveaways = await self.db.get_active_giveaways()
        if not active_giveaways:
            await callback_query.message.edit_text("🎭 No active giveaway at the moment.")
            await callback_query.answer()
            return
        
        giveaway_id = active_giveaways[0]['id']
        callback_query.data = f"verify_sub_{giveaway_id}"
        await self.handle_verify_subscription(callback_query)
    
    async def handle_admin_participants(self, callback_query: CallbackQuery):
        """Handle admin participants pagination"""
        try:
            data_parts = callback_query.data.split("_")
            if len(data_parts) < 4:
                await callback_query.answer("❌ Invalid callback data!")
                return
            
            giveaway_id = data_parts[2]
            page = int(data_parts[3])
            
            # Check if user is owner
            if callback_query.from_user.id != self.config.OWNER_ID:
                await callback_query.answer("❌ Only owner can view participants!", show_alert=True)
                return
            
            # Get giveaway
            giveaway = await self.db.get_giveaway(giveaway_id)
            if not giveaway:
                await callback_query.message.edit_text("❌ Giveaway not found.")
                await callback_query.answer()
                return
            
            participants = await self.db.get_participants(giveaway_id)
            
            if not participants:
                await callback_query.message.edit_text("📭 No participants found for this giveaway.")
                await callback_query.answer()
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
            giveaway_name = giveaway.get('event_name', giveaway_id)
            
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
                    user = await self.bot.get_users(user_id)
                    username = f"@{user.username}" if user.username else user.first_name
                except:
                    username = f"User {user_id}"
                
                text += f"**{start_idx + i}. {username}**\n"
                text += f"   🆔 ID: `{user_id}`\n"
                text += f"   ⏰ Joined: {joined_at[:19]}\n\n"
            
            # Create pagination buttons
            buttons = []
            if page > 0:
                buttons.append(InlineKeyboardButton("◀️ Previous", 
                             callback_data=f"admin_parts_{giveaway_id}_{page-1}"))
            
            buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", 
                         callback_data="noop"))
            
            if page < total_pages - 1:
                buttons.append(InlineKeyboardButton("Next ▶️", 
                             callback_data=f"admin_parts_{giveaway_id}_{page+1}"))
            
            # Add action buttons
            action_buttons = []
            action_buttons.append(InlineKeyboardButton("❌ Remove Participant", 
                            callback_data=f"remove_part_menu_{giveaway_id}"))
            action_buttons.append(InlineKeyboardButton("🏁 End Giveaway", 
                            callback_data=f"giveaway_end_{giveaway_id}"))
            
            markup = InlineKeyboardMarkup([buttons, action_buttons]) if buttons else InlineKeyboardMarkup([action_buttons])
            
            await callback_query.message.edit_text(text, reply_markup=markup)
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Error in handle_admin_participants: {e}", exc_info=True)
            await callback_query.answer("❌ Error loading participants!")
    
    async def handle_remove_participant_menu(self, callback_query: CallbackQuery):
        """Show remove participant menu"""
        try:
            giveaway_id = callback_query.data.replace("remove_part_menu_", "")
            
            # Check if user is owner
            if callback_query.from_user.id != self.config.OWNER_ID:
                await callback_query.answer("❌ Only owner can remove participants!", show_alert=True)
                return
            
            participants = await self.db.get_participants(giveaway_id)
            
            if not participants:
                await callback_query.message.edit_text("📭 No participants to remove.")
                await callback_query.answer()
                return
            
            # Get first 10 participants
            buttons = []
            participant_list = list(participants.items())[:10]
            
            text = "**Select a participant to remove:**\n\n"
            
            for idx, (user_id_str, user_data) in enumerate(participant_list, 1):
                user_id = int(user_id_str)
                username = user_data.get('username', f'User {user_id}')
                first_name = user_data.get('first_name', '')
                
                display_name = f"{first_name} (@{username})" if username else f"User {user_id}"
                if len(display_name) > 30:
                    display_name = display_name[:27] + "..."
                
                buttons.append([
                    InlineKeyboardButton(
                        f"❌ Remove {display_name}",
                        callback_data=f"remove_part_{giveaway_id}_{user_id}"
                    )
                ])
                
                text += f"{idx}. {display_name}\n"
            
            # Add back button
            buttons.append([
                InlineKeyboardButton("🔙 Back to Participants", 
                callback_data=f"admin_parts_{giveaway_id}_0")
            ])
            
            markup = InlineKeyboardMarkup(buttons)
            
            await callback_query.message.edit_text(
                text,
                reply_markup=markup
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Error in handle_remove_participant_menu: {e}", exc_info=True)
            await callback_query.answer("❌ Error loading menu!")
    
    async def handle_remove_participant(self, callback_query: CallbackQuery):
        """Remove participant"""
        try:
            data_parts = callback_query.data.split("_")
            if len(data_parts) < 4:
                await callback_query.answer("❌ Invalid callback data!")
                return
            
            giveaway_id = data_parts[2]
            user_id = int(data_parts[3])
            
            # Check if user is owner
            if callback_query.from_user.id != self.config.OWNER_ID:
                await callback_query.answer("❌ Only owner can remove participants!", show_alert=True)
                return
            
            # Get user info before removing
            try:
                user = await self.bot.get_users(user_id)
                user_info = f"@{user.username}" if user.username else user.first_name
            except:
                user_info = str(user_id)
            
            # Remove participant
            if await self.db.remove_participant(giveaway_id, user_id):
                # Get giveaway info
                giveaway = await self.db.get_giveaway(giveaway_id)
                giveaway_name = giveaway.get('event_name', giveaway_id) if giveaway else giveaway_id
                
                success_text = f"""
✅ **Participant Removed**

**👤 User:** {user_info}
**🆔 ID:** `{user_id}`
**🎁 Giveaway:** {giveaway_name}
**🎫 Giveaway ID:** `{giveaway_id}`

User has been removed from the giveaway.
                """
                
                await callback_query.message.edit_text(success_text)
                
                # Log the action
                await self.db.add_log(
                    "participant_removed",
                    callback_query.from_user.id,
                    giveaway_id,
                    f"Removed user {user_id} ({user_info})"
                )
                
                # Add back button
                keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Participants", 
                    callback_data=f"admin_parts_{giveaway_id}_0")
                ]])
                
                await callback_query.message.edit_text(success_text, reply_markup=keyboard)
                await callback_query.answer("✅ Participant removed!")
            else:
                await callback_query.message.edit_text("❌ User not found in giveaway.")
                await callback_query.answer()
                
        except ValueError:
            await callback_query.answer("❌ Invalid user ID!")
        except Exception as e:
            logger.error(f"Error in handle_remove_participant: {e}", exc_info=True)
            await callback_query.answer("❌ Error removing participant!")
    
    async def handle_end_giveaway(self, callback_query: CallbackQuery):
        """End giveaway from callback"""
        giveaway_id = callback_query.data.replace("giveaway_end_", "")
        
        # Check if user is owner
        if callback_query.from_user.id != self.config.OWNER_ID:
            await callback_query.answer("❌ Only owner can end giveaways!", show_alert=True)
            return
        
        try:
            # Show confirmation
            await callback_query.answer("⏳ Ending giveaway...", show_alert=False)
            
            # Get giveaway info
            giveaway = await self.db.get_giveaway(giveaway_id)
            if not giveaway:
                await callback_query.message.edit_text("❌ Giveaway not found.")
                return
            
            # Update message to show processing
            await callback_query.message.edit_text(
                f"🔄 **Ending Giveaway...**\n\n"
                f"**Event:** {giveaway.get('event_name', giveaway_id)}\n"
                f"**Giveaway ID:** `{giveaway_id}`\n\n"
                f"Please wait while winners are selected..."
            )
            
            # End the giveaway
            from utils.scheduler import GiveawayScheduler
            scheduler = GiveawayScheduler(self.bot, self.db)
            await scheduler.end_giveaway(giveaway_id)
            
            # Update message
            success_text = f"""
✅ **Giveaway Ended Successfully**

**🏷 Event:** {giveaway.get('event_name', giveaway_id)}
**🎫 Giveaway ID:** `{giveaway_id}`

Winners have been selected and announced in all broadcast channels.
Winners will also receive DM notifications.

Thank you for using Smash Giveaway Bot! 🎮
            """
            
            await callback_query.message.edit_text(success_text)
            await callback_query.answer("✅ Giveaway ended successfully!")
            
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}", exc_info=True)
            await callback_query.answer("❌ Error ending giveaway!", show_alert=True)
    
    async def handle_confirm_create(self, callback_query: CallbackQuery):
        """Confirm giveaway creation"""
        user_id = callback_query.from_user.id
        
        # Check if user is owner
        if user_id != self.config.OWNER_ID:
            await callback_query.answer("❌ Only owner can create giveaways!", show_alert=True)
            return
        
        # Show processing message
        await callback_query.message.edit_text("🔄 **Creating giveaway...**")
        
        # Get giveaway handler
        giveaway_handler = await self.get_giveaway_handler()
        
        if giveaway_handler:
            giveaway_id = await giveaway_handler.create_giveaway(user_id)
            
            if giveaway_id:
                # Get giveaway details
                giveaway = await self.db.get_giveaway(giveaway_id)
                giveaway_name = giveaway.get('event_name', 'Unknown') if giveaway else 'Unknown'
                
                success_text = f"""
✅ **Giveaway Created Successfully!** 🎉

**🏷 Event:** {giveaway_name}
**🎫 Giveaway ID:** `{giveaway_id}`

The giveaway has been announced in all broadcast channels.
Participants can now join using `/part`

**⚡️ Good luck to all participants!**
                """
                
                await callback_query.message.edit_text(success_text)
                await callback_query.answer("✅ Giveaway created!")
                
                # Log the creation
                await self.db.add_log(
                    "giveaway_created",
                    user_id,
                    giveaway_id,
                    f"Created giveaway: {giveaway_name}"
                )
            else:
                error_text = """
❌ **Failed to create giveaway!**

Possible reasons:
• No preview data found
• Database error
• No broadcast channels set
• Bot cannot access broadcast channels

Please check your settings and try again using `/sgive`
                """
                
                await callback_query.message.edit_text(error_text)
                await callback_query.answer("❌ Creation failed!")
        else:
            await callback_query.message.edit_text(
                "❌ Giveaway handler not found. Please restart the bot."
            )
            await callback_query.answer("❌ Error!")
    
    async def handle_cancel_create(self, callback_query: CallbackQuery):
        """Cancel giveaway creation"""
        user_id = callback_query.from_user.id
        
        # Get giveaway handler
        giveaway_handler = await self.get_giveaway_handler()
        
        # Clear creation state
        if giveaway_handler and user_id in giveaway_handler.creation_states:
            del giveaway_handler.creation_states[user_id]
        
        await callback_query.message.edit_text(
            "❌ **Giveaway creation cancelled.**\n\n"
            "Use `/sgive` to start a new giveaway creation."
        )
        await callback_query.answer("❌ Cancelled!")
[file content end]
