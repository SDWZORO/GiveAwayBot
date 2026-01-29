from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, List, Any
from pyrogram.types import User
import pytz

class UserValidator:
    def __init__(self, config):
        self.config = config
    
    async def validate_participation(self, user: User, giveaway_id: str, 
                                   db, client) -> Tuple[bool, str, Optional[List]]:
        """Validate user for giveaway participation"""
        # Check if user is banned
        if await db.is_banned(user.id):
            return False, "🚫 Access Restricted\nYou are banned from using this bot.", None
        
        # Check if giveaway exists and is active
        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway:
            return False, "No active giveaway found.", None
        
        if giveaway.get("status") != "active":
            return False, "This giveaway is not active.", None
        
        # Check if user already participated
        if await db.is_participant(giveaway_id, user.id):
            return False, "You have already joined this giveaway.", None
        
        # Check cooldown
        if not await db.check_cooldown(user.id, "participate"):
            remaining = await db.get_remaining_cooldown(user.id, "participate")
            return False, f"⏳ Please wait {remaining} seconds before joining again.", None
        
        # NO ACCOUNT AGE CHECK - REMOVED
        # NO PROFILE PHOTO CHECK - REMOVED
        
        # Check channel subscriptions
        from utils.channel_checker import ChannelChecker
        checker = ChannelChecker(client, self.config.REQUIRED_CHANNELS)
        subscribed, missing = await checker.check_subscription(user.id)
        
        if not subscribed:
            return False, "subscription_required", missing
        
        return True, "User validated successfully", None
    
    async def validate_giveaway_creation(self, data: Dict) -> Tuple[bool, str]:
        """Validate giveaway creation data"""
        required_fields = ['event_name', 'prize_type', 'prize_details', 
                          'winner_count', 'start_time', 'end_time']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return False, f"Missing required field: {field}"
        
        # Validate winner count
        try:
            winner_count = int(data['winner_count'])
            if winner_count <= 0:
                return False, "Winner count must be greater than 0"
        except ValueError:
            return False, "Invalid winner count"
        
        # Validate prize type
        if data['prize_type'] not in ['coins', 'characters']:
            return False, "Prize type must be either 'coins' or 'characters'"
        
        # Validate times
        from utils.helpers import Helpers
        start_time = Helpers.parse_ist_time(data['start_time'])
        end_time = Helpers.parse_ist_time(data['end_time'])
        
        if not start_time or not end_time:
            return False, "Invalid time format. Use: YYYY-MM-DD HH:MM AM/PM"
        
        if end_time <= start_time:
            return False, "End time must be after start time"
        
        if start_time < datetime.now(pytz.UTC):
            return False, "Start time cannot be in the past"
        
        return True, "Giveaway data validated successfully"