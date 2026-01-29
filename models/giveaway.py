from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import pytz
from enum import Enum

class GiveawayStatus(Enum):
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"

class PrizeType(Enum):
    COINS = "coins"
    CHARACTERS = "characters"

@dataclass
class Giveaway:
    giveaway_id: str
    event_name: str
    prize_type: PrizeType
    prize_details: str
    winner_count: int
    start_time: datetime
    end_time: datetime
    status: GiveawayStatus = GiveawayStatus.ACTIVE
    created_at: Optional[datetime] = None
    participants_count: int = 0
    message_id: Optional[int] = None
    chat_id: Optional[int] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(pytz.UTC)
        
        if isinstance(self.start_time, str):
            self.start_time = datetime.fromisoformat(self.start_time)
        if isinstance(self.end_time, str):
            self.end_time = datetime.fromisoformat(self.end_time)
        if isinstance(self.status, str):
            self.status = GiveawayStatus(self.status)
        if isinstance(self.prize_type, str):
            self.prize_type = PrizeType(self.prize_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, Enum):
                data[key] = value.value
        return data
    
    @classmethod
    def from_dict(cls, giveaway_id: str, data: Dict[str, Any]) -> 'Giveaway':
        """Create Giveaway object from dictionary"""
        # Convert string values to appropriate types
        if "prize_type" in data and isinstance(data["prize_type"], str):
            data["prize_type"] = PrizeType(data["prize_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = GiveawayStatus(data["status"])
        
        return cls(giveaway_id=giveaway_id, **data)
    
    @property
    def is_active(self) -> bool:
        """Check if giveaway is currently active"""
        now = datetime.now(pytz.UTC)
        return (self.status == GiveawayStatus.ACTIVE and 
                self.start_time <= now <= self.end_time)
    
    @property
    def has_ended(self) -> bool:
        """Check if giveaway has ended"""
        now = datetime.now(pytz.UTC)
        return (self.status == GiveawayStatus.ENDED or 
                now > self.end_time)
    
    @property
    def time_remaining(self) -> str:
        """Get formatted time remaining"""
        now = datetime.now(pytz.UTC)
        if now > self.end_time:
            return "Ended"
        
        diff = self.end_time - now
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
        
        return " ".join(parts)