# utils/validation.py
from datetime import datetime
import pytz

class UserValidator:
    def __init__(self, config):
        self.config = config
    
    async def validate_participation(self, user, giveaway_id, db, client):
        """Validate user for giveaway participation"""
        user_id = user.id
        
        # Check if giveaway exists
        giveaway = await db.get_giveaway(giveaway_id)
        if not giveaway:
            return False, "❌ Giveaway not found.", None
        
        # Check if giveaway is active
        if giveaway.get('status') != 'active':
            return False, "❌ This giveaway is not active.", None
        
        # Check if user is already a participant
        if await db.is_participant(giveaway_id, user_id):
            return False, "❌ You have already joined this giveaway.", None
        
        # Check account age (at least 1 day old to prevent spam)
        account_age = await self.calculate_account_age(user)
        if account_age < 1:
            return False, "❌ Your account must be at least 1 day old to participate.", None
        
        # Check subscription requirement
        from utils.channel_checker import ChannelChecker
        checker = ChannelChecker(client, self.config.REQUIRED_CHANNELS)
        subscribed, missing = await checker.check_subscription(user_id)
        
        if not subscribed:
            return False, "subscription_required", missing
        
        return True, "Valid user", None
    
    async def calculate_account_age(self, user):
        """Calculate account age in days"""
        if not hasattr(user, 'date') or not user.date:
            return 0
        
        account_created = user.date.replace(tzinfo=pytz.UTC)
        now = datetime.now(pytz.UTC)
        
        age_days = (now - account_created).days
        return age_days
