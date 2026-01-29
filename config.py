class Config:
    # Bot Configuration
    API_ID = 23212132
    API_HASH = "1c17efa86bdef8f806ed70e81b473c20"
    BOT_TOKEN = "8224658326:AAFRhXOTDBsB0coCMZUgwwaPOvOVfFaMbD4"
    
    # Owner Configuration
    OWNER_ID = 8301883098
    
    # Required Channels/Groups (for subscription check)
    # Format: "username" without @
    REQUIRED_CHANNELS = ["Smash_uploads", "ShadowBotsHQ", "Main_smash"]
    
    # Timezone
    TIMEZONE = "Asia/Kolkata"
    
    # Cooldown Settings (in seconds)
    COOLDOWN_PARTICIPATE = 10
    COOLDOWN_CHECK = 5
    
    # Data Paths
    DATA_DIR = "data"
    DATABASE_FILE = f"{DATA_DIR}/database.json"
    LOGS_FILE = f"{DATA_DIR}/logs.json"
    
    # Bot Settings
    MAX_PARTICIPANTS_PER_PAGE = 50
    GIVEAWAY_CHECK_INTERVAL = 60  # seconds