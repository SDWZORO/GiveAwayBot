import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from pathlib import Path
import logging
import uuid
import pytz

logger = logging.getLogger(__name__)

class JSONDatabase:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = self._load_data()
        self.lock = asyncio.Lock()
        self.auto_save_counter = 0
        self.auto_save_threshold = 10
        
    def _load_data(self) -> Dict:
        """Load data from JSON file and ensure all required keys exist"""
        Path(os.path.dirname(self.file_path)).mkdir(exist_ok=True)
        
        if not os.path.exists(self.file_path):
            default_data = self._get_default_data()
            self._save_data(default_data)
            return default_data
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Ensure all required keys exist
            data = self._ensure_data_structure(data)
            
            return data
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"Database corrupted or not found: {e}. Creating new database.")
            default_data = self._get_default_data()
            self._save_data(default_data)
            return default_data
    
    def _get_default_data(self) -> Dict:
        """Get default database structure"""
        return {
            "giveaways": {},
            "participants": {},
            "winners": {},
            "banned_users": [],
            "broadcast_chats": [],
            "user_cooldowns": {},
            "logs": [],
            "giveaway_counters": {},
            "user_stats": {},
            "settings": {
                "last_cleanup": datetime.now(pytz.UTC).isoformat(),
                "version": "2.0.0"
            }
        }
    
    def _ensure_data_structure(self, data: Dict) -> Dict:
        """Ensure all required keys exist in the data"""
        default_data = self._get_default_data()
        
        # Add missing top-level keys
        for key, default_value in default_data.items():
            if key not in data:
                data[key] = default_value
            elif key == "settings" and isinstance(data[key], dict):
                # Ensure settings has required subkeys
                for setting_key, setting_default in default_value.items():
                    if setting_key not in data[key]:
                        data[key][setting_key] = setting_default
        
        # Ensure participant data structure for existing giveaways
        if "giveaways" in data:
            for giveaway_id in data["giveaways"]:
                if giveaway_id not in data["participants"]:
                    data["participants"][giveaway_id] = {}
        
        return data
    
    def _save_data(self, data: Dict) -> None:
        """Save data to JSON file"""
        try:
            # Create backup of old file
            if os.path.exists(self.file_path):
                backup_path = f"{self.file_path}.backup"
                import shutil
                shutil.copy2(self.file_path, backup_path)
            
            # Save new data
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False, default=str)
            
            logger.debug(f"Database saved to {self.file_path}")
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            raise
    
    async def save(self) -> None:
        """Async save data"""
        async with self.lock:
            self._save_data(self.data)
    
    async def auto_save_check(self) -> None:
        """Check if auto-save is needed"""
        self.auto_save_counter += 1
        if self.auto_save_counter >= self.auto_save_threshold:
            await self.save()
            self.auto_save_counter = 0
    
    # Giveaway Methods
    async def create_giveaway(self, giveaway_id: str, giveaway_data: Dict) -> bool:
        """Create a new giveaway"""
        try:
            # Generate a unique ID if not provided
            if not giveaway_id:
                giveaway_id = f"GIV_{datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
            
            # Ensure required fields
            required_fields = ['event_name', 'prize_type', 'prize_details', 
                             'winner_count', 'start_time', 'end_time']
            
            for field in required_fields:
                if field not in giveaway_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Make sure times are strings (not datetime objects)
            if isinstance(giveaway_data.get('start_time'), datetime):
                giveaway_data['start_time'] = giveaway_data['start_time'].isoformat()
            if isinstance(giveaway_data.get('end_time'), datetime):
                giveaway_data['end_time'] = giveaway_data['end_time'].isoformat()
            
            # Add metadata
            giveaway_data.update({
                "id": giveaway_id,
                "created_at": datetime.now(pytz.UTC).isoformat(),
                "status": "active",
                "participants_count": 0,
                "messages": [],
                "winners_selected": False,
                "announced": False
            })
            
            self.data["giveaways"][giveaway_id] = giveaway_data
            
            # Initialize participants for this giveaway
            if giveaway_id not in self.data["participants"]:
                self.data["participants"][giveaway_id] = {}
            
            # Update giveaway counter
            date_key = datetime.now(pytz.UTC).strftime("%Y-%m")
            if date_key not in self.data["giveaway_counters"]:
                self.data["giveaway_counters"][date_key] = 0
            self.data["giveaway_counters"][date_key] += 1
            
            await self.save()
            logger.info(f"Created giveaway: {giveaway_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            return False
    
    async def get_giveaway(self, giveaway_id: str) -> Optional[Dict]:
        """Get giveaway by ID"""
        return self.data["giveaways"].get(giveaway_id)
    
    async def get_giveaway_by_name(self, event_name: str) -> Optional[Dict]:
        """Get giveaway by event name"""
        for gid, giveaway in self.data["giveaways"].items():
            if giveaway.get("event_name", "").lower() == event_name.lower():
                return {"id": gid, **giveaway}
        return None
    
    async def get_active_giveaways(self) -> List[Dict]:
        """Get all active giveaways"""
        active = []
        now = datetime.now(pytz.UTC)
        
        for gid, giveaway in self.data["giveaways"].items():
            status = giveaway.get("status", "inactive")
            
            # Check if giveaway is active
            if status != "active":
                continue
            
            # Check if giveaway has ended by time
            end_time_str = giveaway.get("end_time")
            if end_time_str:
                try:
                    # Parse end_time to aware datetime
                    if isinstance(end_time_str, str):
                        # Try to parse as ISO format with timezone
                        if '+' in end_time_str or end_time_str.endswith('Z'):
                            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        else:
                            # Assume UTC if no timezone
                            end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=pytz.UTC)
                    else:
                        # If it's already a datetime, ensure it's aware
                        end_time = end_time_str
                        if end_time.tzinfo is None:
                            end_time = end_time.replace(tzinfo=pytz.UTC)
                    
                    # Check if giveaway is still active
                    if end_time > now:
                        active.append({"id": gid, **giveaway})
                except Exception as e:
                    logger.error(f"Error parsing end_time for giveaway {gid}: {e}")
                    # If we can't parse, assume it's active
                    active.append({"id": gid, **giveaway})
            else:
                # No end time, assume active
                active.append({"id": gid, **giveaway})
        
        return active
    
    async def get_expired_giveaways(self) -> List[Dict]:
        """Get giveaways that have expired but not ended"""
        expired = []
        now = datetime.now(pytz.UTC)
        
        for gid, giveaway in self.data["giveaways"].items():
            status = giveaway.get("status", "inactive")
            
            if status != "active":
                continue
            
            end_time_str = giveaway.get("end_time")
            if end_time_str:
                try:
                    # Parse end_time to aware datetime
                    if isinstance(end_time_str, str):
                        if '+' in end_time_str or end_time_str.endswith('Z'):
                            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        else:
                            end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=pytz.UTC)
                    else:
                        end_time = end_time_str
                        if end_time.tzinfo is None:
                            end_time = end_time.replace(tzinfo=pytz.UTC)
                    
                    if end_time <= now:
                        expired.append({"id": gid, **giveaway})
                except Exception as e:
                    logger.error(f"Error parsing end_time for expired giveaway {gid}: {e}")
        
        return expired
    
    async def update_giveaway(self, giveaway_id: str, updates: Dict) -> bool:
        """Update giveaway data"""
        if giveaway_id in self.data["giveaways"]:
            # Convert datetime objects to strings
            for key, value in updates.items():
                if isinstance(value, datetime):
                    updates[key] = value.isoformat()
            
            self.data["giveaways"][giveaway_id].update(updates)
            await self.auto_save_check()
            return True
        return False
    
    async def delete_giveaway(self, giveaway_id: str) -> bool:
        """Delete a giveaway"""
        if giveaway_id in self.data["giveaways"]:
            # Archive data before deleting
            giveaway_data = self.data["giveaways"][giveaway_id]
            giveaway_data["deleted_at"] = datetime.now(pytz.UTC).isoformat()
            giveaway_data["deleted_by"] = "system"
            
            # Move to archive section if it exists
            if "archived_giveaways" not in self.data:
                self.data["archived_giveaways"] = {}
            self.data["archived_giveaways"][giveaway_id] = giveaway_data
            
            # Delete from active giveaways
            del self.data["giveaways"][giveaway_id]
            
            await self.save()
            return True
        return False
    
    async def end_giveaway(self, giveaway_id: str) -> bool:
        """Mark giveaway as ended"""
        if giveaway_id in self.data["giveaways"]:
            self.data["giveaways"][giveaway_id]["status"] = "ended"
            self.data["giveaways"][giveaway_id]["ended_at"] = datetime.now(pytz.UTC).isoformat()
            await self.save()
            return True
        return False
    
    # Participant Methods
    async def add_participant(self, giveaway_id: str, user_id: int, user_data: Dict) -> Tuple[bool, str]:
        """Add participant to giveaway"""
        try:
            if giveaway_id not in self.data["giveaways"]:
                return False, "Giveaway not found"
            
            # Check if giveaway is active
            giveaway = self.data["giveaways"][giveaway_id]
            if giveaway.get("status") != "active":
                return False, "Giveaway is not active"
            
            # Check if giveaway has ended
            end_time_str = giveaway.get("end_time")
            if end_time_str:
                now = datetime.now(pytz.UTC)
                try:
                    # Parse end_time to aware datetime
                    if isinstance(end_time_str, str):
                        if '+' in end_time_str or end_time_str.endswith('Z'):
                            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        else:
                            end_time = datetime.fromisoformat(end_time_str).replace(tzinfo=pytz.UTC)
                    else:
                        end_time = end_time_str
                        if end_time.tzinfo is None:
                            end_time = end_time.replace(tzinfo=pytz.UTC)
                    
                    if end_time <= now:
                        return False, "Giveaway has ended"
                except Exception as e:
                    logger.error(f"Error parsing end_time in add_participant: {e}")
                    # If we can't parse, don't block participation
                    pass
            
            if giveaway_id not in self.data["participants"]:
                self.data["participants"][giveaway_id] = {}
            
            user_id_str = str(user_id)
            
            if user_id_str not in self.data["participants"][giveaway_id]:
                # Prepare user data
                participant_data = {
                    "user_id": user_id,
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "joined_at": datetime.now(pytz.UTC).isoformat(),
                    "is_active": True,
                    "last_check": datetime.now(pytz.UTC).isoformat()
                }
                
                self.data["participants"][giveaway_id][user_id_str] = participant_data
                
                # Update participant count
                giveaway["participants_count"] = len(self.data["participants"][giveaway_id])
                
                # Update user stats
                await self.update_user_stats(user_id, "participations", 1)
                
                await self.auto_save_check()
                logger.info(f"User {user_id} joined giveaway {giveaway_id}")
                return True, "Successfully joined giveaway"
            else:
                return False, "Already joined this giveaway"
                
        except Exception as e:
            logger.error(f"Error adding participant: {e}")
            return False, f"Error: {str(e)}"
    
    async def remove_participant(self, giveaway_id: str, user_id: int) -> bool:
        """Remove participant from giveaway"""
        try:
            if (giveaway_id in self.data["participants"] and 
                str(user_id) in self.data["participants"][giveaway_id]):
                
                # Get participant info for logging
                participant = self.data["participants"][giveaway_id][str(user_id)]
                participant["removed_at"] = datetime.now(pytz.UTC).isoformat()
                participant["removed_by"] = "admin"
                participant["is_active"] = False
                
                # Move to removed participants
                if "removed_participants" not in self.data:
                    self.data["removed_participants"] = {}
                if giveaway_id not in self.data["removed_participants"]:
                    self.data["removed_participants"][giveaway_id] = {}
                
                self.data["removed_participants"][giveaway_id][str(user_id)] = participant
                
                # Remove from active participants
                del self.data["participants"][giveaway_id][str(user_id)]
                
                # Update participant count
                if giveaway_id in self.data["giveaways"]:
                    self.data["giveaways"][giveaway_id]["participants_count"] = \
                        len(self.data["participants"].get(giveaway_id, {}))
                
                # Update user stats
                await self.update_user_stats(user_id, "removals", 1)
                
                await self.auto_save_check()
                return True
                
        except Exception as e:
            logger.error(f"Error removing participant: {e}")
        
        return False
    
    async def get_participants(self, giveaway_id: str, active_only: bool = True) -> Dict:
        """Get all participants for a giveaway"""
        participants = self.data["participants"].get(giveaway_id, {})
        
        if active_only:
            return {k: v for k, v in participants.items() if v.get("is_active", True)}
        return participants
    
    async def is_participant(self, giveaway_id: str, user_id: int) -> bool:
        """Check if user is participant"""
        participants = self.data["participants"].get(giveaway_id, {})
        user_data = participants.get(str(user_id), {})
        return bool(user_data and user_data.get("is_active", True))
    
    async def get_user_participations(self, user_id: int) -> List[str]:
        """Get all giveaways a user has participated in"""
        participations = []
        user_id_str = str(user_id)
        
        for giveaway_id, participants in self.data["participants"].items():
            if user_id_str in participants and participants[user_id_str].get("is_active", True):
                participations.append(giveaway_id)
        
        return participations
    
    # Winner Methods
    async def add_winner(self, giveaway_id: str, user_id: int, prize_details: str = None) -> bool:
        """Add winner to giveaway"""
        try:
            if giveaway_id not in self.data["winners"]:
                self.data["winners"][giveaway_id] = []
            
            winner_data = {
                "user_id": user_id,
                "won_at": datetime.now(pytz.UTC).isoformat(),
                "prize_claimed": False,
                "claimed_at": None,
                "prize_details": prize_details
            }
            
            # Check if user is already a winner
            existing_winners = self.data["winners"][giveaway_id]
            for winner in existing_winners:
                if winner.get("user_id") == user_id:
                    return False  # Already a winner
            
            self.data["winners"][giveaway_id].append(winner_data)
            
            # Update giveaway status
            if giveaway_id in self.data["giveaways"]:
                self.data["giveaways"][giveaway_id]["winners_selected"] = True
            
            # Update user stats
            await self.update_user_stats(user_id, "wins", 1)
            
            await self.auto_save_check()
            return True
            
        except Exception as e:
            logger.error(f"Error adding winner: {e}")
            return False
    
    async def get_winners(self, giveaway_id: str) -> List[Dict]:
        """Get winners for a giveaway"""
        return self.data["winners"].get(giveaway_id, [])
    
    async def mark_prize_claimed(self, giveaway_id: str, user_id: int) -> bool:
        """Mark prize as claimed by user"""
        if giveaway_id in self.data["winners"]:
            for winner in self.data["winners"][giveaway_id]:
                if winner.get("user_id") == user_id:
                    winner["prize_claimed"] = True
                    winner["claimed_at"] = datetime.now(pytz.UTC).isoformat()
                    await self.save()
                    return True
        return False
    
    # Ban Methods
    async def ban_user(self, user_id: int, reason: str = "No reason provided", banned_by: int = None) -> bool:
        """Ban a user from using the bot"""
        try:
            # Check if user is already banned
            for ban_data in self.data["banned_users"]:
                if ban_data.get("user_id") == user_id and ban_data.get("active", True):
                    return False  # Already banned
            
            ban_data = {
                "user_id": user_id,
                "banned_at": datetime.now(pytz.UTC).isoformat(),
                "banned_by": banned_by,
                "reason": reason,
                "active": True
            }
            
            self.data["banned_users"].append(ban_data)
            await self.save()
            
            # Log the ban
            await self.add_log(
                "user_banned",
                banned_by or 0,
                None,
                f"Banned user {user_id}: {reason}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False
    
    async def unban_user(self, user_id: int, unbanned_by: int = None) -> bool:
        """Unban a user"""
        try:
            for i, ban_data in enumerate(self.data["banned_users"]):
                if ban_data.get("user_id") == user_id and ban_data.get("active", True):
                    # Mark as inactive instead of removing
                    self.data["banned_users"][i]["active"] = False
                    self.data["banned_users"][i]["unbanned_at"] = datetime.now(pytz.UTC).isoformat()
                    self.data["banned_users"][i]["unbanned_by"] = unbanned_by
                    
                    await self.save()
                    
                    # Log the unban
                    await self.add_log(
                        "user_unbanned",
                        unbanned_by or 0,
                        None,
                        f"Unbanned user {user_id}"
                    )
                    
                    return True
            return False
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False
    
    async def is_banned(self, user_id: int) -> bool:
        """Check if user is currently banned"""
        for ban_data in self.data["banned_users"]:
            if ban_data.get("user_id") == user_id and ban_data.get("active", True):
                return True
        return False
    
    async def get_ban_info(self, user_id: int) -> Optional[Dict]:
        """Get ban information for user"""
        for ban_data in self.data["banned_users"]:
            if ban_data.get("user_id") == user_id and ban_data.get("active", True):
                return ban_data
        return None
    
    # Broadcast Methods
    async def add_broadcast_chat(self, chat_info: Dict) -> bool:
        """Add chat to broadcast list using chat info"""
        try:
            # Check if chat already exists (by username or chat_id)
            username = chat_info.get('username')
            chat_id = chat_info.get('chat_id')
            
            for chat in self.data["broadcast_chats"]:
                if (chat.get('username') == username or 
                    (chat_id and chat.get('chat_id') == chat_id)):
                    return False  # Already exists
            
            # Add creation timestamp
            chat_info['added_at'] = datetime.now(pytz.UTC).isoformat()
            chat_info['active'] = True
            
            self.data["broadcast_chats"].append(chat_info)
            await self.save()
            return True
        except Exception as e:
            logger.error(f"Error adding broadcast chat: {e}")
            return False
    
    async def remove_broadcast_chat(self, username: str) -> bool:
        """Remove chat from broadcast list by username"""
        try:
            username_clean = username.lstrip('@')
            for i, chat_data in enumerate(self.data["broadcast_chats"]):
                if chat_data.get('username') == username_clean:
                    # Mark as inactive
                    self.data["broadcast_chats"][i]["active"] = False
                    self.data["broadcast_chats"][i]["removed_at"] = datetime.now(pytz.UTC).isoformat()
                    await self.save()
                    return True
            return False
        except Exception as e:
            logger.error(f"Error removing broadcast chat: {e}")
            return False
    
    async def get_broadcast_chats(self, active_only: bool = True) -> List[Dict]:
        """Get all broadcast chats"""
        if active_only:
            return [chat for chat in self.data["broadcast_chats"] if chat.get('active', True)]
        return self.data["broadcast_chats"]
    
    # Cooldown Methods
    async def set_cooldown(self, user_id: int, action: str, seconds: int) -> None:
        """Set cooldown for user action"""
        key = f"{user_id}_{action}"
        expires = datetime.now(pytz.UTC) + timedelta(seconds=seconds)
        self.data["user_cooldowns"][key] = {
            "expires_at": expires.isoformat(),
            "action": action,
            "set_at": datetime.now(pytz.UTC).isoformat()
        }
        await self.auto_save_check()
    
    async def check_cooldown(self, user_id: int, action: str) -> bool:
        """Check if user has cooldown"""
        key = f"{user_id}_{action}"
        if key in self.data["user_cooldowns"]:
            cooldown_data = self.data["user_cooldowns"][key]
            expires_str = cooldown_data.get("expires_at")
            
            if expires_str:
                try:
                    # Parse to aware datetime
                    if '+' in expires_str or expires_str.endswith('Z'):
                        expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    else:
                        expires = datetime.fromisoformat(expires_str).replace(tzinfo=pytz.UTC)
                    
                    now = datetime.now(pytz.UTC)
                    if now < expires:
                        return False  # Cooldown still active
                except Exception as e:
                    logger.error(f"Error parsing cooldown expiration: {e}")
            
            # Cooldown expired or invalid, remove it
            del self.data["user_cooldowns"][key]
            await self.auto_save_check()
        
        return True  # No cooldown or expired
    
    async def get_remaining_cooldown(self, user_id: int, action: str) -> int:
        """Get remaining cooldown in seconds"""
        key = f"{user_id}_{action}"
        if key in self.data["user_cooldowns"]:
            cooldown_data = self.data["user_cooldowns"][key]
            expires_str = cooldown_data.get("expires_at")
            
            if expires_str:
                try:
                    # Parse to aware datetime
                    if '+' in expires_str or expires_str.endswith('Z'):
                        expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    else:
                        expires = datetime.fromisoformat(expires_str).replace(tzinfo=pytz.UTC)
                    
                    now = datetime.now(pytz.UTC)
                    remaining = (expires - now).seconds
                    return max(0, remaining)
                except Exception as e:
                    logger.error(f"Error parsing cooldown for remaining: {e}")
        
        return 0
    
    async def clear_cooldown(self, user_id: int, action: str = None) -> None:
        """Clear cooldown for user"""
        if action:
            key = f"{user_id}_{action}"
            if key in self.data["user_cooldowns"]:
                del self.data["user_cooldowns"][key]
        else:
            # Clear all cooldowns for user
            keys_to_remove = [k for k in self.data["user_cooldowns"].keys() if k.startswith(f"{user_id}_")]
            for key in keys_to_remove:
                del self.data["user_cooldowns"][key]
        
        await self.auto_save_check()
    
    # Log Methods
    async def add_log(self, log_type: str, user_id: int, giveaway_id: str = None, 
                     details: str = None, level: str = "INFO") -> None:
        """Add log entry"""
        try:
            log_entry = {
                "id": str(uuid.uuid4()),
                "type": log_type,
                "user_id": user_id,
                "giveaway_id": giveaway_id,
                "details": details,
                "level": level,
                "timestamp": datetime.now(pytz.UTC).isoformat(),
            }
            
            self.data["logs"].append(log_entry)
            
            # Keep only last 5000 logs
            if len(self.data["logs"]) > 5000:
                self.data["logs"] = self.data["logs"][-5000:]
            
            await self.auto_save_check()
            
        except Exception as e:
            logger.error(f"Error adding log: {e}")
    
    async def get_recent_logs(self, limit: int = 100, log_type: str = None, 
                             user_id: int = None, giveaway_id: str = None) -> List[Dict]:
        """Get recent logs with optional filtering"""
        logs = self.data["logs"]
        
        # Apply filters
        if log_type:
            logs = [log for log in logs if log.get("type") == log_type]
        if user_id:
            logs = [log for log in logs if log.get("user_id") == user_id]
        if giveaway_id:
            logs = [log for log in logs if log.get("giveaway_id") == giveaway_id]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs[:limit]
    
    # User Stats Methods
    async def update_user_stats(self, user_id: int, stat_type: str, value: int = 1) -> None:
        """Update user statistics"""
        # Ensure user_stats exists
        if "user_stats" not in self.data:
            self.data["user_stats"] = {}
        
        user_id_str = str(user_id)
        
        if user_id_str not in self.data["user_stats"]:
            self.data["user_stats"][user_id_str] = {
                "user_id": user_id,
                "first_seen": datetime.now(pytz.UTC).isoformat(),
                "last_seen": datetime.now(pytz.UTC).isoformat(),
                "total_participations": 0,
                "total_wins": 0,
                "total_removals": 0,
            }
        
        user_stats = self.data["user_stats"][user_id_str]
        user_stats["last_seen"] = datetime.now(pytz.UTC).isoformat()
        
        if stat_type == "participations":
            user_stats["total_participations"] += value
        elif stat_type == "wins":
            user_stats["total_wins"] += value
        elif stat_type == "removals":
            user_stats["total_removals"] += value
        
        await self.auto_save_check()
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user statistics"""
        # Ensure user_stats exists
        if "user_stats" not in self.data:
            return None
        
        return self.data["user_stats"].get(str(user_id))
    
    async def get_top_participants(self, limit: int = 10) -> List[Dict]:
        """Get top participants by participation count"""
        # Ensure user_stats exists
        if "user_stats" not in self.data:
            return []
        
        users = []
        for user_id_str, stats in self.data["user_stats"].items():
            users.append({
                "user_id": int(user_id_str),
                "total_participations": stats.get("total_participations", 0),
                "total_wins": stats.get("total_wins", 0),
                "first_seen": stats.get("first_seen"),
                "last_seen": stats.get("last_seen")
            })
        
        # Sort by participations (descending)
        users.sort(key=lambda x: x["total_participations"], reverse=True)
        return users[:limit]
    
    # Utility Methods
    async def cleanup_expired_cooldowns(self) -> int:
        """Cleanup expired cooldowns, returns number cleaned"""
        now = datetime.now(pytz.UTC)
        expired_keys = []
        
        for key, cooldown_data in self.data["user_cooldowns"].items():
            expires_str = cooldown_data.get("expires_at", "")
            if expires_str:
                try:
                    # Parse to aware datetime
                    if '+' in expires_str or expires_str.endswith('Z'):
                        expires = datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
                    else:
                        expires = datetime.fromisoformat(expires_str).replace(tzinfo=pytz.UTC)
                    
                    if now > expires:
                        expired_keys.append(key)
                except Exception as e:
                    logger.error(f"Error parsing cooldown expiration in cleanup: {e}")
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.data["user_cooldowns"][key]
        
        if expired_keys:
            await self.save()
        
        return len(expired_keys)
    
    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Cleanup logs older than specified days"""
        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days_to_keep)
        initial_count = len(self.data["logs"])
        
        self.data["logs"] = [
            log for log in self.data["logs"]
            if datetime.fromisoformat(log.get("timestamp", "2000-01-01")) > cutoff_date
        ]
        
        removed_count = initial_count - len(self.data["logs"])
        if removed_count > 0:
            await self.save()
            await self.add_log(
                "cleanup",
                0,
                None,
                f"Cleaned up {removed_count} logs older than {days_to_keep} days"
            )
        
        return removed_count
    
    async def get_database_stats(self) -> Dict:
        """Get database statistics"""
        now = datetime.now(pytz.UTC)
        active_giveaways = await self.get_active_giveaways()
        total_participants = sum(len(participants) for participants in self.data["participants"].values())
        
        return {
            "total_giveaways": len(self.data["giveaways"]),
            "active_giveaways": len(active_giveaways),
            "total_participants": total_participants,
            "banned_users": len([b for b in self.data["banned_users"] if b.get("active", True)]),
            "broadcast_chats": len([c for c in self.data["broadcast_chats"] if c.get("active", True)]),
            "total_logs": len(self.data["logs"]),
            "total_users": len(self.data["user_stats"]) if "user_stats" in self.data else 0,
            "active_cooldowns": len(self.data["user_cooldowns"]),
            "database_size": os.path.getsize(self.file_path) if os.path.exists(self.file_path) else 0,
            "last_save": now.isoformat()
        }
    
    async def backup_database(self, backup_dir: str = "backups") -> str:
        """Create a backup of the database"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir, 
                f"database_backup_{datetime.now(pytz.UTC).strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            
            await self.add_log(
                "backup",
                0,
                None,
                f"Database backed up to {backup_path}"
            )
            
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not os.path.exists(backup_path):
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Create a backup of current data
            current_backup = await self.backup_database("restore_backups")
            
            # Restore from backup
            self.data = backup_data
            await self.save()
            
            await self.add_log(
                "restore",
                0,
                None,
                f"Database restored from {backup_path}. Original backed up to {current_backup}"
            )
            
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False