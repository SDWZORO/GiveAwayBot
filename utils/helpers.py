import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import pytz
from pyrogram.types import User, InlineKeyboardButton, InlineKeyboardMarkup
import random
import string

class Helpers:
    # Timezone for IST
    IST = pytz.timezone('Asia/Kolkata')
    
    @staticmethod
    def generate_giveaway_id() -> str:
        """Generate unique giveaway ID"""
        timestamp = int(datetime.now().timestamp())
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"GIVEAWAY_{timestamp}_{random_str}"
    
    @staticmethod
    def parse_ist_time(time_str: str) -> Optional[datetime]:
        """
        Parse IST time string (format: YYYY-MM-DD HH:MM AM/PM)
        """
        try:
            # Remove any extra spaces and normalize
            time_str = time_str.strip().upper()
            
            # Parse the date and time
            dt = datetime.strptime(time_str, "%Y-%m-%d %I:%M %p")
            
            # Localize to IST
            dt = Helpers.IST.localize(dt)
            
            # Convert to UTC for storage
            return dt.astimezone(pytz.UTC)
        except ValueError:
            return None
    
    @staticmethod
    def format_ist_time(dt: datetime) -> str:
        """Format datetime to IST time string"""
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        dt_ist = dt.astimezone(Helpers.IST)
        return dt_ist.strftime("%Y-%m-%d %I:%M %p")
    
    @staticmethod
    def format_time_difference(start: datetime, end: datetime) -> str:
        """Format time difference in human readable format"""
        diff = end - start
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        
        return ", ".join(parts) if parts else "Less than a minute"
    
    @staticmethod
    def calculate_account_age(user: User) -> int:
        """Calculate account age in days"""
        if not hasattr(user, 'date') or not user.date:
            return 0
        
        account_created = user.date.replace(tzinfo=pytz.UTC)
        now = datetime.now(pytz.UTC)
        
        age_days = (now - account_created).days
        return age_days
    
    @staticmethod
    def create_pagination_buttons(page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
        """Create pagination buttons"""
        buttons = []
        
        if page > 0:
            buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"{prefix}_page_{page-1}"))
        
        buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}_page_{page+1}"))
        
        return InlineKeyboardMarkup([buttons]) if buttons else None
    
    @staticmethod
    def create_join_channels_markup(channels: List[Dict]) -> InlineKeyboardMarkup:
        """Create markup for joining channels"""
        buttons = []
        for channel in channels:
            buttons.append([
                InlineKeyboardButton(
                    f"Join {channel['name']}",
                    url=f"https://t.me/{channel['username']}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")
        ])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def select_winners(participants: Dict[str, Dict], winner_count: int) -> List[int]:
        """Randomly select winners from participants"""
        if not participants or winner_count <= 0:
            return []
        
        participant_ids = list(participants.keys())
        
        if len(participant_ids) <= winner_count:
            return [int(pid) for pid in participant_ids]
        
        winners = random.sample(participant_ids, winner_count)
        return [int(pid) for pid in winners]
    
    @staticmethod
    def format_user_mention(user: User) -> str:
        """Format user mention with username or first name"""
        if user.username:
            return f"@{user.username}"
        else:
            return f"[{user.first_name}](tg://user?id={user.id})"
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'

        return bool(re.match(pattern, phone))

    @staticmethod
    def get_time_remaining(end_time: datetime) -> str:
        """Get formatted time remaining until end time"""
        now = datetime.now(pytz.UTC)
        
        if isinstance(end_time, str):
            if '+' in end_time or end_time.endswith('Z'):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            else:
                end_time = datetime.fromisoformat(end_time).replace(tzinfo=pytz.UTC)
        
        if now > end_time:
            return "Ended"
        
        diff = end_time - now
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        seconds = diff.seconds % 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 and not parts:  # Only show seconds if less than a minute
            parts.append(f"{seconds}s")
        
        return " ".join(parts) if parts else "Less than a minute"
