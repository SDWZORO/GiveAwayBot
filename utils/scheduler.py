
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import logging

logger = logging.getLogger(__name__)

class GiveawayScheduler:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db
        self.scheduler = AsyncIOScheduler(timezone="UTC")
        self.active_giveaways = {}
    
    async def start(self):
        """Start the scheduler and load existing giveaways"""
        self.scheduler.start()
        
        # Load active giveaways from database
        active_giveaways = await self.db.get_active_giveaways()
        
        for giveaway in active_giveaways:
            await self.schedule_giveaway_end(giveaway['id'], giveaway)
        
        logger.info(f"✅ Scheduler started with {len(active_giveaways)} active giveaways")
        
        # Schedule periodic checks
        self.scheduler.add_job(
            self.check_expired_giveaways,
            'interval',
            minutes=1,
            id="check_expired_giveaways",
            replace_existing=True
        )
    
    async def schedule_giveaway_end(self, giveaway_id: str, giveaway_data: Dict):
        """Schedule giveaway end"""
        end_time_str = giveaway_data.get('end_time')
        if not end_time_str:
            logger.error(f"❌ No end time for giveaway {giveaway_id}")
            return
        
        try:
            # Parse end time to aware datetime
            if isinstance(end_time_str, str):
                if '+' in end_time_str or end_time_str.endswith('Z'):
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                else:
                    end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=pytz.UTC)
            else:
                end_time = end_time_str
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=pytz.UTC)
            
            now = datetime.now(pytz.UTC)
            
            # If giveaway already ended, end it immediately
            if end_time <= now:
                logger.warning(f"⚠️ Giveaway {giveaway_id} already ended, ending now")
                await self.end_giveaway(giveaway_id)
                return
            
            # Calculate time until end
            time_until_end = end_time - now
            logger.info(f"⏰ Scheduling giveaway {giveaway_id} to end in {time_until_end}")
            
            # Schedule the end
            trigger = DateTrigger(run_date=end_time)
            self.scheduler.add_job(
                self.end_giveaway,
                trigger,
                args=[giveaway_id],
                id=f"giveaway_end_{giveaway_id}",
                replace_existing=True,
                misfire_grace_time=60  # Allow 60 seconds grace period
            )
            
            self.active_giveaways[giveaway_id] = giveaway_data
            logger.info(f"✅ Scheduled giveaway {giveaway_id} to end at {end_time}")
            
        except Exception as e:
            logger.error(f"❌ Error scheduling giveaway {giveaway_id}: {e}", exc_info=True)
    
    async def end_giveaway(self, giveaway_id: str):
        """End a giveaway and select winners"""
        logger.info(f"🎯 Ending giveaway: {giveaway_id}")
        
        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            logger.error(f"❌ Giveaway {giveaway_id} not found")
            return
        
        # Check if already ended
        if giveaway.get('status') == 'ended':
            logger.warning(f"⚠️ Giveaway {giveaway_id} already ended")
            return
        
        # Update giveaway status
        await self.db.update_giveaway(giveaway_id, {
            "status": "ended",
            "ended_at": datetime.now(pytz.UTC).isoformat(),
            "winners_selected": True
        })
        
        # Remove from active giveaways
        if giveaway_id in self.active_giveaways:
            del self.active_giveaways[giveaway_id]
        
        # Remove the scheduled job
        job_id = f"giveaway_end_{giveaway_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Get participants
        participants = await self.db.get_participants(giveaway_id)
        winner_count = giveaway.get('winner_count', 1)
        
        logger.info(f"📊 Giveaway {giveaway_id} has {len(participants)} participants, selecting {winner_count} winners")
        
        if not participants:
            logger.warning(f"⚠️ No participants for giveaway {giveaway_id}")
            # Still announce that giveaway ended with no participants
            await self.announce_no_winners(giveaway_id, giveaway)
            return
        
        # Select winners
        from utils.helpers import Helpers
        winners = Helpers.select_winners(participants, winner_count)
        
        logger.info(f"🏆 Selected {len(winners)} winners for giveaway {giveaway_id}: {winners}")
        
        # Store winners in database
        for winner_id in winners:
            await self.db.add_winner(giveaway_id, winner_id)
        
        # Announce winners in broadcast channels
        await self.announce_winners(giveaway_id, giveaway, winners)
        
        # DM winners
        await self.notify_winners(giveaway_id, giveaway, winners)
        
        # Log completion
        await self.db.add_log(
            "giveaway_ended",
            0,  # system
            giveaway_id,
            f"Giveaway ended with {len(winners)} winners out of {len(participants)} participants"
        )
        
        logger.info(f"✅ Giveaway {giveaway_id} ended successfully with {len(winners)} winners")
    
    async def announce_no_winners(self, giveaway_id: str, giveaway: Dict):
        """Announce giveaway ended with no participants"""
        from utils.helpers import Helpers
        
        announcement_text = f"""
🎊 **GIVEAWAY ENDED** 🎊

**🏷 Event:** {giveaway['event_name']}
**🎁 Prize:** {giveaway['prize_type'].title()} - {giveaway['prize_details']}

**🏆 WINNERS:** No participants joined this giveaway.

The giveaway has ended without any participants.
        """
        
        # Get broadcast chats
        broadcast_chats = await self.db.get_broadcast_chats()
        
        sent_count = 0
        for chat in broadcast_chats:
            try:
                chat_id = chat.get('chat_id')
                if chat_id:
                    await self.bot.send_message(chat_id, announcement_text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error announcing no winners in chat {chat.get('name', 'Unknown')}: {e}")
        
        logger.info(f"📢 Announced no winners for giveaway {giveaway_id} in {sent_count} chats")
        
        # Notify owner
        await self.bot.send_message(
            await self.get_owner_id(),
            f"ℹ️ Giveaway `{giveaway_id}` ended with no participants."
        )
    
    async def announce_winners(self, giveaway_id: str, giveaway: Dict, winners: List[int]):
        """Announce winners in broadcast channels"""
        from utils.helpers import Helpers
        
        # Format winners list
        winners_text = ""
        for i, winner_id in enumerate(winners, 1):
            try:
                user = await self.bot.get_users(winner_id)
                mention = Helpers.format_user_mention(user)
                if i == 1:
                    winners_text += f"🥇 {mention}\n"
                elif i == 2:
                    winners_text += f"🥈 {mention}\n"
                elif i == 3:
                    winners_text += f"🥉 {mention}\n"
                else:
                    winners_text += f"{i}. {mention}\n"
            except Exception as e:
                logger.error(f"Error getting user info for winner {winner_id}: {e}")
                winners_text += f"{i}. User ID: {winner_id}\n"
        
        announcement_text = f"""
🎊 **GIVEAWAY ENDED** 🎊

**🏷 Event:** {giveaway['event_name']}
**🎁 Prize:** {giveaway['prize_type'].title()} - {giveaway['prize_details']}

**🏆 CONGRATULATIONS TO THE WINNERS!** 🏆

{winners_text if winners else "No winners selected"}

Winners will be contacted via DM to claim their prizes.

Thank you to all participants! 🎮
        """
        
        # Get broadcast chats
        broadcast_chats = await self.db.get_broadcast_chats()
        
        sent_count = 0
        for chat in broadcast_chats:
            try:
                chat_id = chat.get('chat_id')
                if chat_id:
                    await self.bot.send_message(chat_id, announcement_text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error announcing winners in chat {chat.get('name', 'Unknown')}: {e}")
        
        logger.info(f"📢 Announced winners for giveaway {giveaway_id} in {sent_count} chats")
    
    async def notify_winners(self, giveaway_id: str, giveaway: Dict, winners: List[int]):
        """Send DM to winners"""
        from utils.helpers import Helpers
        
        notified_count = 0
        failed_count = 0
        
        for winner_id in winners:
            try:
                message_text = f"""
🎉 **CONGRATULATIONS! YOU WON!** 🎉

**🏷 Event:** {giveaway['event_name']}
**🎁 Prize:** {giveaway['prize_type'].title()} - {giveaway['prize_details']}

**Giveaway ID:** `{giveaway_id}`

**🏆 You have been selected as a winner!**

Please contact the admin @{self.bot.me.username} to claim your reward.

Thank you for participating! 🎮
                """
                
                await self.bot.send_message(winner_id, message_text)
                logger.info(f"📨 Notified winner: {winner_id}")
                notified_count += 1
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error notifying winner {winner_id}: {e}")
                failed_count += 1
        
        # Notify owner about notification status
        if notified_count > 0 or failed_count > 0:
            owner_id = await self.get_owner_id()
            try:
                await self.bot.send_message(
                    owner_id,
                    f"📋 **Winner Notification Report**\n\n"
                    f"**Giveaway:** {giveaway['event_name']}\n"
                    f"**Giveaway ID:** `{giveaway_id}`\n"
                    f"**Total Winners:** {len(winners)}\n"
                    f"**Successfully Notified:** {notified_count}\n"
                    f"**Failed to Notify:** {failed_count}\n\n"
                    f"Winners: {', '.join(str(w) for w in winners)}"
                )
            except Exception as e:
                logger.error(f"Error sending notification report to owner: {e}")
    
    async def check_expired_giveaways(self):
        """Periodically check for expired giveaways that weren't ended"""
        try:
            expired_giveaways = await self.db.get_expired_giveaways()
            
            for giveaway in expired_giveaways:
                giveaway_id = giveaway['id']
                logger.info(f"⏰ Found expired giveaway: {giveaway_id}")
                
                # Check if job already exists
                job_id = f"giveaway_end_{giveaway_id}"
                if not self.scheduler.get_job(job_id):
                    # End the giveaway now
                    await self.end_giveaway(giveaway_id)
        
        except Exception as e:
            logger.error(f"Error checking expired giveaways: {e}", exc_info=True)
    
    async def get_owner_id(self):
        """Get owner ID from config"""
        try:
            from config import Config
            config = Config()
            return config.OWNER_ID
        except:
            # Fallback to environment variable or hardcoded value
            return 8301883098  # Your owner ID from config
    
    async def add_giveaway(self, giveaway_id: str, giveaway_data: Dict):
        """Add new giveaway to scheduler"""
        await self.schedule_giveaway_end(giveaway_id, giveaway_data)
    
    async def remove_giveaway(self, giveaway_id: str):
        """Remove giveaway from scheduler"""
        job_id = f"giveaway_end_{giveaway_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        if giveaway_id in self.active_giveaways:
            del self.active_giveaways[giveaway_id]
        
        logger.info(f"Removed giveaway {giveaway_id} from scheduler")
    
    async def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
[file content end]

