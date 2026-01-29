from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import pytz

class UserCommands:
    def __init__(self, bot: Client, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        
        # Register user commands
        self.bot.on_message(filters.command("start") & filters.private)(self.start_command)
        self.bot.on_message(filters.command("part") & filters.private)(self.participate_command)
        self.bot.on_message(filters.command("gstats") & filters.private)(self.giveaway_stats_user)
    
    async def start_command(self, client: Client, message: Message):
        """Start command handler"""
        user_id = message.from_user.id
        
        # Check if user is banned
        if await self.db.is_banned(user_id):
            await message.reply("🚫 Access Restricted\nYou are banned from using this bot.")
            return
        
        welcome_text = """
🎮🤖 **SMASH GIVEAWAY & CONTEST MANAGEMENT BOT**

Welcome to the official Smash Giveaway Bot!

**Available Commands:**
/part - Join active giveaway
/gstats - Check giveaway status

**Features:**
✅ Automated & Fair Giveaways
✅ Secure Participation System
✅ Real-time Winner Selection
✅ Anti-cheat Protection

**Requirements:**
1. Must join all required channels
2. No multiple accounts

**NO Account Age Restriction**
**NO Profile Photo Required**
        """
        
        await message.reply(welcome_text)
    
    async def participate_command(self, client: Client, message: Message):
        """Participate in giveaway"""
        user_id = message.from_user.id
        
        # Check if user is banned
        if await self.db.is_banned(user_id):
            await message.reply("🚫 Access Restricted\nYou are banned from using this bot.")
            return
        
        # Check cooldown
        if not await self.db.check_cooldown(user_id, "participate"):
            remaining = await self.db.get_remaining_cooldown(user_id, "participate")
            await message.reply(f"⏳ Please wait {remaining} seconds before joining again.")
            return
        
        # Get active giveaway
        active_giveaways = await self.db.get_active_giveaways()
        
        if not active_giveaways:
            await message.reply("🎭 No active giveaway at the moment.")
            return
        
        # For simplicity, get the first active giveaway
        giveaway = active_giveaways[0]
        giveaway_id = giveaway['id']
        
        # Validate user for participation
        from utils.validation import UserValidator
        validator = UserValidator(self.config)
        
        valid, reason, missing = await validator.validate_participation(
            message.from_user, giveaway_id, self.db, client
        )
        
        if not valid:
            if reason == "subscription_required" and missing:
                # Show channels to join
                from utils.channel_checker import ChannelChecker
                checker = ChannelChecker(client, self.config.REQUIRED_CHANNELS)
                channels = await checker.get_channel_links()
                
                # If we can't get channel links, use the missing list
                if not channels and missing:
                    text = "📢 **Join Required Channels**\n\n"
                    text += "To participate in the giveaway, you must join these channels:\n\n"
                    
                    for channel in missing:
                        text += f"• {channel['name']}\n"
                    
                    text += "\nAfter joining, click the button below to verify."
                    
                    # Create buttons
                    buttons = []
                    for channel in missing:
                        username = channel.get('username')
                        if username:
                            url = f"https://t.me/{username}"
                            buttons.append([
                                InlineKeyboardButton(
                                    f"Join {channel['name']}",
                                    url=url
                                )
                            ])
                    
                    buttons.append([
                        InlineKeyboardButton(
                            "✅ I've Joined All",
                            callback_data=f"verify_sub_{giveaway_id}"
                        )
                    ])
                    
                    markup = InlineKeyboardMarkup(buttons)
                    await message.reply(text, reply_markup=markup)
                elif channels:
                    text = "📢 **Join Required Channels**\n\n"
                    text += "To participate in the giveaway, you must join these channels:\n\n"
                    
                    for channel in channels:
                        text += f"• {channel['name']}\n"
                    
                    text += "\nAfter joining, click the button below to verify."
                    
                    # Create buttons
                    buttons = []
                    for channel in channels:
                        buttons.append([
                            InlineKeyboardButton(
                                f"Join {channel['name']}",
                                url=channel['link']
                            )
                        ])
                    
                    buttons.append([
                        InlineKeyboardButton(
                            "✅ I've Joined All",
                            callback_data=f"verify_sub_{giveaway_id}"
                        )
                    ])
                    
                    markup = InlineKeyboardMarkup(buttons)
                    await message.reply(text, reply_markup=markup)
                else:
                    # No channels to check, allow participation
                    await self.complete_participation(message, user_id, giveaway_id, giveaway)
            else:
                await message.reply(reason)
            return
        
        # If validation passed, complete participation
        await self.complete_participation(message, user_id, giveaway_id, giveaway)
    
    async def complete_participation(self, message: Message, user_id: int, giveaway_id: str, giveaway: dict):
        """Complete the participation process"""
        # Add participant
        user_data = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
            "joined_at": datetime.now(pytz.UTC).isoformat()
        }
        
        success, db_message = await self.db.add_participant(giveaway_id, user_id, user_data)
        
        if success:
            # Set cooldown
            await self.db.set_cooldown(user_id, "participate", self.config.COOLDOWN_PARTICIPATE)
            
            # Send success message
            await message.reply("🎉 **Entry Confirmed!**\nGood luck 🍀")
            
            # Log participation to owner
            await self.log_participation_to_owner(message.from_user, giveaway)
            
            # Add to logs
            await self.db.add_log(
                "user_joined",
                user_id,
                giveaway_id,
                f"User joined giveaway: {giveaway['event_name']}"
            )
        else:
            await message.reply(f"❌ {db_message}")
    
    async def giveaway_stats_user(self, client: Client, message: Message):
        """Show giveaway stats for users"""
        active_giveaways = await self.db.get_active_giveaways()
        
        if not active_giveaways:
            await message.reply("🎭 No active giveaways at the moment.")
            return
        
        from utils.helpers import Helpers
        
        for giveaway in active_giveaways[:3]:  # Show max 3 active giveaways
            giveaway_id = giveaway['id']
            participants = await self.db.get_participants(giveaway_id)
            
            # Calculate time remaining
            end_time = datetime.fromisoformat(giveaway['end_time'])
            time_remaining = Helpers.format_time_difference(datetime.now(pytz.UTC), end_time)
            
            # Check if user is participant
            is_participant = await self.db.is_participant(giveaway_id, message.from_user.id)
            
            text = f"**🎁 Active Giveaway**\n\n"
            text += f"**Event:** {giveaway['event_name']}\n"
            text += f"**Prize:** {giveaway['prize_type'].title()} - {giveaway['prize_details']}\n"
            text += f"**Winners:** {giveaway['winner_count']}\n"
            text += f"**Participants:** {len(participants)}\n"
            text += f"**Time Remaining:** {time_remaining}\n"
            text += f"**Your Status:** {'✅ Joined' if is_participant else '❌ Not Joined'}\n\n"
            
            if not is_participant:
                text += "Click /part to join!"
            
            await message.reply(text)
    
    async def log_participation_to_owner(self, user, giveaway):
        """Send log message to owner about user joining giveaway"""
        try:
            log_text = f"📝 **User Joined Giveaway**\n\n"
            log_text += f"**User:** {user.first_name}\n"
            log_text += f"**ID:** `{user.id}`\n"
            log_text += f"**Username:** @{user.username if user.username else 'N/A'}\n"
            log_text += f"**Giveaway:** {giveaway['event_name']}\n"
            log_text += f"**Giveaway ID:** `{giveaway['id']}`\n"
            log_text += f"**Time:** {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            log_text += f"\nTotal Participants: {giveaway.get('participants_count', 0)}"
            
            await self.bot.send_message(self.config.OWNER_ID, log_text)
        except Exception as e:
            print(f"Error sending log to owner: {e}")