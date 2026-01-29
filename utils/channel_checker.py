from typing import List, Tuple, Dict, Optional
from pyrogram import Client
from pyrogram.errors import UserNotParticipant, UsernameInvalid, UsernameNotOccupied

class ChannelChecker:
    def __init__(self, client: Client, required_channels: List[str]):
        self.client = client
        # Store usernames (without @)
        self.required_channels = [ch.lstrip('@') for ch in required_channels if ch.strip()]
    
    async def check_subscription(self, user_id: int) -> Tuple[bool, List[Dict]]:
        """Check if user is subscribed to all required channels using usernames"""
        missing_channels = []
        
        for channel_username in self.required_channels:
            try:
                # Add @ prefix for the get_chat method
                chat_username = f"@{channel_username}"
                
                # Get the chat/channel
                chat = await self.client.get_chat(chat_username)
                
                # Try to get chat member
                try:
                    chat_member = await self.client.get_chat_member(chat.id, user_id)
                    
                    # Check if user is a member (not left/kicked)
                    if chat_member.status in ['left', 'kicked']:
                        missing_channels.append({
                            'username': channel_username,
                            'name': chat.title,
                            'id': chat.id
                        })
                        
                except UserNotParticipant:
                    # User is not a member
                    missing_channels.append({
                        'username': channel_username,
                        'name': chat.title,
                        'id': chat.id
                    })
                    
            except (UsernameInvalid, UsernameNotOccupied) as e:
                # Username is invalid or doesn't exist
                print(f"⚠️ Channel @{channel_username} is invalid or doesn't exist: {e}")
                missing_channels.append({
                    'username': channel_username,
                    'name': f"@{channel_username}",
                    'id': None
                })
            except Exception as e:
                print(f"⚠️ Error checking channel @{channel_username}: {e}")
                missing_channels.append({
                    'username': channel_username,
                    'name': f"@{channel_username}",
                    'id': None
                })
        
        # If no required channels, consider user subscribed
        if not self.required_channels:
            return True, []
        
        return len(missing_channels) == 0, missing_channels
    
    async def get_channel_links(self) -> List[Dict]:
        """Get invite links for all required channels"""
        channel_links = []
        
        for channel_username in self.required_channels:
            try:
                # Add @ prefix for the get_chat method
                chat_username = f"@{channel_username}"
                chat = await self.client.get_chat(chat_username)
                
                # Create invite link
                link = f"https://t.me/{channel_username}"
                
                channel_links.append({
                    'username': channel_username,
                    'name': chat.title,
                    'link': link,
                    'id': chat.id
                })
            except (UsernameInvalid, UsernameNotOccupied) as e:
                print(f"⚠️ Cannot access channel @{channel_username}: {e}")
                # Still add with basic info
                channel_links.append({
                    'username': channel_username,
                    'name': f"@{channel_username}",
                    'link': f"https://t.me/{channel_username}",
                    'id': None
                })
            except Exception as e:
                print(f"⚠️ Error getting channel @{channel_username} info: {e}")
                channel_links.append({
                    'username': channel_username,
                    'name': f"@{channel_username}",
                    'link': f"https://t.me/{channel_username}",
                    'id': None
                })
        
        return channel_links