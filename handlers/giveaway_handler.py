from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import pytz
from typing import Dict, List, Optional

class GiveawayHandler:
    def __init__(self, bot: Client, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.creation_states = {}  # Store creation states by user_id
    
    async def start_creation_wizard(self, message: Message):
        """Start giveaway creation wizard"""
        user_id = message.from_user.id
        
        # Initialize creation state
        self.creation_states[user_id] = {
            "step": 1,
            "data": {}
        }
        
        await message.reply(
            "🎮 **Giveaway Creation Wizard**\n\n"
            "**Step 1/6:** Enter the event name:"
        )
    
    async def handle_creation_step(self, message: Message):
        """Handle giveaway creation steps"""
        user_id = message.from_user.id
        
        if user_id not in self.creation_states:
            await message.reply("❌ No active giveaway creation session. Use /sgive to start.")
            return
        
        state = self.creation_states[user_id]
        step = state["step"]
        data = state["data"]
        
        if step == 1:
            # Event name
            if not message.text or len(message.text.strip()) < 3:
                await message.reply("❌ Event name must be at least 3 characters. Please enter a valid name:")
                return
            
            data["event_name"] = message.text.strip()
            state["step"] = 2
            
            await message.reply(
                "✅ **Event name saved!**\n\n"
                "**Step 2/6:** Select prize type:\n\n"
                "1️⃣ **Kryps** - Virtual currency\n"
                "2️⃣ **Characters** - Game characters\n\n"
                "Reply with **1** or **2**:"
            )
        
        elif step == 2:
            # Prize type
            choice = message.text.strip()
            if choice == "1":
                data["prize_type"] = "coins"
            elif choice == "2":
                data["prize_type"] = "characters"
            else:
                await message.reply("❌ Invalid choice. Please reply with **1** for Kryps or **2** for Characters:")
                return
            
            state["step"] = 3
            
            prize_example = "1000 Kryps" if data["prize_type"] == "coins" else "Legendary Character Card"
            await message.reply(
                f"✅ **Prize type set to: {data['prize_type'].title()}**\n\n"
                f"**Step 3/6:** Enter prize details:\n\n"
                f"**Example:** `{prize_example}`\n\n"
                "Enter the prize description:"
            )
        
        elif step == 3:
            # Prize details
            if not message.text or len(message.text.strip()) < 3:
                await message.reply("❌ Prize details must be at least 3 characters. Please enter valid details:")
                return
            
            data["prize_details"] = message.text.strip()
            state["step"] = 4
            
            await message.reply(
                f"✅ **Prize details saved!**\n\n"
                f"**Step 4/6:** How many winners?\n\n"
                "Enter a number (e.g., 1, 3, 5):"
            )
        
        elif step == 4:
            # Winner count
            try:
                winner_count = int(message.text.strip())
                if winner_count <= 0:
                    await message.reply("❌ Winner count must be greater than 0. Please enter a valid number:")
                    return
                if winner_count > 100:
                    await message.reply("❌ Winner count cannot exceed 100. Please enter a smaller number:")
                    return
                
                data["winner_count"] = winner_count
                state["step"] = 5
                
                current_time = datetime.now(pytz.timezone('Asia/Kolkata')).strftime("%Y-%m-%d %I:%M %p")
                await message.reply(
                    f"✅ **Winner count set to: {winner_count}**\n\n"
                    f"**Step 5/6:** Enter start time (IST):\n\n"
                    f"**Format:** `YYYY-MM-DD HH:MM AM/PM`\n"
                    f"**Example:** `2024-01-15 08:00 PM`\n\n"
                    f"**Current IST time:** `{current_time}`\n\n"
                    "Enter start time:"
                )
            except ValueError:
                await message.reply("❌ Please enter a valid number for winner count:")
                return
        
        elif step == 5:
            # Start time
            from utils.helpers import Helpers
            start_time = Helpers.parse_ist_time(message.text.strip())
            
            if not start_time:
                await message.reply(
                    "❌ **Invalid time format!**\n\n"
                    "Please use: `YYYY-MM-DD HH:MM AM/PM`\n"
                    "**Example:** `2024-01-15 08:00 PM`\n\n"
                    "Enter start time again:"
                )
                return
            
            if start_time < datetime.now(pytz.UTC):
                await message.reply("❌ Start time cannot be in the past. Please enter a future time:")
                return
            
            data["start_time"] = start_time.isoformat()
            state["step"] = 6
            
            formatted_start = Helpers.format_ist_time(start_time)
            await message.reply(
                f"✅ **Start time set to:** `{formatted_start}`\n\n"
                f"**Step 6/6:** Enter end time (IST):\n\n"
                f"**Format:** `YYYY-MM-DD HH:MM AM/PM`\n"
                f"**Example:** `2024-01-16 08:00 PM`\n\n"
                f"Enter end time:"
            )
        
        elif step == 6:
            # End time
            from utils.helpers import Helpers
            end_time = Helpers.parse_ist_time(message.text.strip())
            
            if not end_time:
                await message.reply(
                    "❌ **Invalid time format!**\n\n"
                    "Please use: `YYYY-MM-DD HH:MM AM/PM`\n"
                    "**Example:** `2024-01-16 08:00 PM`\n\n"
                    "Enter end time again:"
                )
                return
            
            start_time = datetime.fromisoformat(data["start_time"])
            if end_time <= start_time:
                await message.reply("❌ End time must be after start time. Please enter a later time:")
                return
            
            data["end_time"] = end_time.isoformat()
            
            # Show preview
            await self.show_preview(message, data)
    
    async def show_preview(self, message: Message, data: Dict):
        """Show giveaway preview and confirm creation"""
        from utils.helpers import Helpers
        
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
        
        preview_text = f"""
🎉 **GIVEAWAY PREVIEW** 🎉

**🏷 Event:** {data['event_name']}
**🎁 Prize:** {data['prize_type'].title()} - {data['prize_details']}
**🏆 Winners:** {data['winner_count']}
**⏰ Start:** {Helpers.format_ist_time(start_time)}
**⏰ End:** {Helpers.format_ist_time(end_time)}

**Duration:** {Helpers.format_time_difference(start_time, end_time)}

Do you want to create this giveaway?
        """
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Yes, Create", callback_data="confirm_create"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_create")
            ]
        ])
        
        # Store data for confirmation
        user_id = message.from_user.id
        self.creation_states[user_id]["preview_data"] = data
        
        await message.reply(preview_text, reply_markup=keyboard)
    
    async def create_giveaway(self, user_id: int) -> Optional[str]:
        """Create the giveaway from preview data"""
        if user_id not in self.creation_states:
            return None
        
        state = self.creation_states.get(user_id, {})
        data = state.get("preview_data", {})
        
        if not data:
            return None
        
        try:
            # Generate giveaway ID
            from utils.helpers import Helpers
            giveaway_id = Helpers.generate_giveaway_id()
            
            # Add creation timestamp
            data["created_at"] = datetime.now(pytz.UTC).isoformat()
            data["created_by"] = user_id
            data["status"] = "active"
            data["participants_count"] = 0
            
            # Save to database
            await self.db.create_giveaway(giveaway_id, data)
            
            # Schedule giveaway end
            from utils.scheduler import GiveawayScheduler
            scheduler = GiveawayScheduler(self.bot, self.db)
            await scheduler.schedule_giveaway_end(giveaway_id, data)
            
            # Announce in broadcast chats
            await self.announce_giveaway(giveaway_id, data)
            
            # Clear creation state
            if user_id in self.creation_states:
                del self.creation_states[user_id]
            
            return giveaway_id
            
        except Exception as e:
            print(f"Error creating giveaway: {e}")
            return None
    
    async def announce_giveaway(self, giveaway_id: str, giveaway_data: Dict):
        """Announce giveaway in broadcast channels"""
        from utils.helpers import Helpers
        
        start_time = datetime.fromisoformat(giveaway_data['start_time'])
        end_time = datetime.fromisoformat(giveaway_data['end_time'])
        
        announcement_text = f"""
🎉 **SMASH OFFICIAL GIVEAWAY** 🎉

**🏷 Event:** {giveaway_data['event_name']}
**🎁 Reward:** {giveaway_data['prize_type'].title()} - {giveaway_data['prize_details']}
**🏆 Winners:** {giveaway_data['winner_count']}

**⏰ Start:** {Helpers.format_ist_time(start_time)}
**⏰ End:** {Helpers.format_ist_time(end_time)}

**⏳ Duration:** {Helpers.format_time_difference(start_time, end_time)}

**📌 Join using** `/part`

**Giveaway ID:** `{giveaway_id}`
        """
        
        # Get broadcast chats
        broadcast_chats = await self.db.get_broadcast_chats()
        
        if not broadcast_chats:
            # If no broadcast chats set, send to owner
            await self.bot.send_message(
                self.config.OWNER_ID,
                "⚠️ **No broadcast chats set!**\n"
                "Use `/set @username` to add broadcast chats.\n\n"
                f"{announcement_text}"
            )
            return
        
        # Send to all broadcast chats
        sent_count = 0
        failed = []
        
        for chat in broadcast_chats:
            try:
                chat_username = chat.get('username')
                chat_id = chat.get('chat_id')
                
                if chat_id:
                    # Try by ID first
                    await self.bot.send_message(chat_id, announcement_text)
                elif chat_username:
                    # Try by username
                    await self.bot.send_message(f"@{chat_username}", announcement_text)
                else:
                    continue
                    
                sent_count += 1
            except Exception as e:
                chat_name = chat.get('name', f"@{chat.get('username', 'Unknown')}")
                failed.append(f"{chat_name}: {str(e)}")
        
        # Notify owner
        result_text = f"✅ Giveaway announced in {sent_count}/{len(broadcast_chats)} chats.\n"
        result_text += f"**Giveaway ID:** `{giveaway_id}`\n"
        
        if failed:
            result_text += f"\n❌ Failed to send to {len(failed)} chats:\n"
            for fail in failed[:5]:  # Show only first 5 failures
                result_text += f"• {fail}\n"
            if len(failed) > 5:
                result_text += f"... and {len(failed) - 5} more.\n"
        
        await self.bot.send_message(self.config.OWNER_ID, result_text)
    
    @staticmethod
    async def announce_winners(bot: Client, giveaway_id: str, giveaway_data: Dict, winners: List[int]):
        """Announce winners in broadcast channels"""
        from utils.helpers import Helpers
        
        # Format winners list
        winners_text = ""
        for i, winner_id in enumerate(winners, 1):
            try:
                user = await bot.get_users(winner_id)
                mention = Helpers.format_user_mention(user)
                if i == 1:
                    winners_text += f"🥇 {mention}\n"
                elif i == 2:
                    winners_text += f"🥈 {mention}\n"
                elif i == 3:
                    winners_text += f"🥉 {mention}\n"
                else:
                    winners_text += f"{i}. {mention}\n"
            except:
                winners_text += f"{i}. User ID: {winner_id}\n"
        
        announcement_text = f"""
🎊 **GIVEAWAY ENDED** 🎊

**🏷 Event:** {giveaway_data['event_name']}
**🎁 Prize:** {giveaway_data['prize_type'].title()} - {giveaway_data['prize_details']}

**🏆 WINNERS:**
{winners_text if winners else "No winners selected"}

Congratulations to the winners! 🎉
Winners will be contacted via DM.
        """
        
        # Get database instance
        from database import JSONDatabase
        import os
        from config import Config
        config = Config()
        db = JSONDatabase(config.DATABASE_FILE)
        broadcast_chats = await db.get_broadcast_chats()
        
        for chat in broadcast_chats:
            try:
                chat_id = chat.get('chat_id')
                await bot.send_message(chat_id, announcement_text)
            except Exception as e:
                print(f"Error announcing winners in chat {chat_id}: {e}")
        
        return announcement_text
    
    @staticmethod
    async def notify_winners(bot: Client, giveaway_id: str, giveaway_data: Dict, winners: List[int]):
        """Send DM to winners"""
        from utils.helpers import Helpers
        
        for winner_id in winners:
            try:
                message_text = f"""
🎉 **Congratulations! You won the Smash Giveaway!** 🎉

**Event:** {giveaway_data['event_name']}
**Prize:** {giveaway_data['prize_type'].title()} - {giveaway_data['prize_details']}

**Giveaway ID:** `{giveaway_id}`

Please contact the admin @{bot.me.username} to claim your reward.

Thank you for participating! 🎮
                """
                
                await bot.send_message(winner_id, message_text)
                print(f"Notified winner: {winner_id}")
            except Exception as e:

                print(f"Error notifying winner {winner_id}: {e}")
