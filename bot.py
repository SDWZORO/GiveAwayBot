import asyncio
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import Message
import pytz
from datetime import datetime
import os

from config import Config
from database import JSONDatabase
from handlers.admin_commands import AdminCommands
from handlers.user_commands import UserCommands
from handlers.giveaway_handler import GiveawayHandler
from handlers.callback_handler import CallbackHandler
from utils.scheduler import GiveawayScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmashGiveawayBot:
    def __init__(self):
        self.config = Config()
        self.db = JSONDatabase(self.config.DATABASE_FILE)
        self.bot = Client(
            "smash_giveaway_bot",
            api_id=self.config.API_ID,
            api_hash=self.config.API_HASH,
            bot_token=self.config.BOT_TOKEN
        )
        self.scheduler = None
        
        # Initialize handlers
        self.admin_handler = None
        self.user_handler = None
        self.giveaway_handler = None
        self.callback_handler = None
        
        # Register handlers
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all bot handlers"""
        # Message handler for giveaway creation wizard
        @self.bot.on_message(filters.private & ~filters.command(
            ["start", "part", "end", "cwinner", "parts", "rmpart", "pban", "punban", "set", "gstats", "sgive"]
        ))
        async def handle_message(client: Client, message: Message):
            # Check if user is in creation wizard
            user_id = message.from_user.id
            
            if self.giveaway_handler and user_id in self.giveaway_handler.creation_states:
                await self.giveaway_handler.handle_creation_step(message)
                return
        
        # Initialize handlers
        self.admin_handler = AdminCommands(self.bot, self.db, self.config, self)
        self.user_handler = UserCommands(self.bot, self.db, self.config)
        self.giveaway_handler = GiveawayHandler(self.bot, self.db, self.config)
        self.callback_handler = CallbackHandler(self.bot, self.db, self.config)
        
        # Set giveaway_handler as attribute for easy access
        self.bot.giveaway_handler = self.giveaway_handler
    
    async def start(self):
        """Start the bot"""
        logger.info("Starting Smash Giveaway Bot...")
        
        # Start the bot client
        await self.bot.start()
        
        # Get bot info
        me = await self.bot.get_me()
        logger.info(f"Bot started as @{me.username}")
        
        # Initialize scheduler
        self.scheduler = GiveawayScheduler(self.bot, self.db)
        await self.scheduler.start()
        
        # Send startup message to owner
        try:
            await self.bot.send_message(
                self.config.OWNER_ID,
                f"✅ **Smash Giveaway Bot Started**\n\n"
                f"**Bot:** @{me.username}\n"
                f"**Time:** {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"**Active Giveaways:** {len(await self.db.get_active_giveaways())}\n\n"
                f"Ready to manage giveaways! 🎮"
            )
        except Exception as e:
            logger.error(f"Failed to send startup message to owner: {e}")
        
        # Run idle
        logger.info("Bot is now running...")
        await idle()
    
    async def stop(self):
        """Stop the bot"""
        logger.info("Stopping Smash Giveaway Bot...")
        
        # Stop scheduler
        if self.scheduler:
            await self.scheduler.stop()
        
        # Stop the bot
        await self.bot.stop()
        
        logger.info("Bot stopped successfully")

async def main():
    """Main function"""
    bot = SmashGiveawayBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}", exc_info=True)
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Create data directory
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    # Run the bot
    asyncio.run(main())
