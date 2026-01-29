import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

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
        
        print(f"✅ Scheduler started with {len(active_giveaways)} active giveaways")
    
    async def schedule_giveaway_end(self, giveaway_id: str, giveaway_data: Dict):
        """Schedule giveaway end"""
        end_time_str = giveaway_data.get('end_time')
        if not end_time_str:
            print(f"❌ No end time for giveaway {giveaway_id}")
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
                print(f"⚠️ Giveaway {giveaway_id} already ended, ending now")
                await self.end_giveaway(giveaway_id)
                return
            
            # Calculate time until end
            time_until_end = end_time - now
            print(f"⏰ Scheduling giveaway {giveaway_id} to end in {time_until_end}")
            
            # Schedule the end
            trigger = DateTrigger(run_date=end_time)
            self.scheduler.add_job(
                self.end_giveaway,
                trigger,
                args=[giveaway_id],
                id=f"giveaway_end_{giveaway_id}",
                replace_existing=True
            )
            
            self.active_giveaways[giveaway_id] = giveaway_data
            print(f"✅ Scheduled giveaway {giveaway_id} to end at {end_time}")
            
        except Exception as e:
            print(f"❌ Error scheduling giveaway {giveaway_id}: {e}")
    
    async def end_giveaway(self, giveaway_id: str):
        """End a giveaway and select winners"""
        print(f"🎯 Ending giveaway: {giveaway_id}")
        
        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            print(f"❌ Giveaway {giveaway_id} not found")
            return
        
        # Update giveaway status
        await self.db.update_giveaway(giveaway_id, {"status": "ended"})
        
        # Remove from active giveaways
        if giveaway_id in self.active_giveaways:
            del self.active_giveaways[giveaway_id]
        
        # Select winners
        participants = await self.db.get_participants(giveaway_id)
        winner_count = giveaway.get('winner_count', 1)
        
        from utils.helpers import Helpers
        winners = Helpers.select_winners(participants, winner_count)
        
        print(f"🏆 Selected {len(winners)} winners for giveaway {giveaway_id}")
        
        # Store winners
        for winner_id in winners:
            await self.db.add_winner(giveaway_id, winner_id)
        
        # Send announcement
        from handlers.giveaway_handler import GiveawayHandler
        await GiveawayHandler.announce_winners(self.bot, giveaway_id, giveaway, winners)
        
        # DM winners
        await GiveawayHandler.notify_winners(self.bot, giveaway_id, giveaway, winners)
        
        # Log completion
        await self.db.add_log(
            "giveaway_ended",
            0,  # system
            giveaway_id,
            f"Giveaway ended with {len(winners)} winners"
        )
        
        print(f"✅ Giveaway {giveaway_id} ended successfully with {len(winners)} winners")
    
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
    
    async def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()