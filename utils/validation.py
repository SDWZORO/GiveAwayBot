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
        
        # Check subscription requirement
        from utils.channel_checker import ChannelChecker
        checker = ChannelChecker(client, self.config.REQUIRED_CHANNELS)
        subscribed, missing = await checker.check_subscription(user_id)
        
        if not subscribed:
            return False, "subscription_required", missing
        
        return True, "Valid user", None
