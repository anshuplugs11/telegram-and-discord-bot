import os
from typing import List

class Config:
    """Configuration class for the Music Bot"""
    
    def __init__(self):
        # Bot Tokens
        self.DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "your_discord_bot_token_here")
        self.TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "your_telegram_bot_token_here")
        
        # Owner/Sudoer Configuration
        self.OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))  # Replace with your user ID
        self.SUDOERS = [
            self.OWNER_ID,
            # Add more sudoer IDs here
            # int(os.getenv("SUDOER_2", "987654321")),
        ]
        
        # Database Configuration
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///musicbot.db")
        
        # Music Configuration
        self.MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "100"))
        self.MAX_SONG_DURATION = int(os.getenv("MAX_SONG_DURATION", "3600"))  # 1 hour in seconds
        self.DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.5"))
        self.DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
        
        # YouTube Configuration
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "your_youtube_api_key_here")
        
        # Bot Settings
        self.MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        self.LOGGING_ENABLED = os.getenv("LOGGING_ENABLED", "true").lower() == "true"
        self.AUTO_LEAVE_TIMEOUT = int(os.getenv("AUTO_LEAVE_TIMEOUT", "300"))  # 5 minutes
        
        # Spotify Configuration (Optional)
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        
        # Rate Limiting
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.MAX_COMMANDS_PER_MINUTE = int(os.getenv("MAX_COMMANDS_PER_MINUTE", "30"))
        
        # Channel Configuration
        self.SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/your_support_channel")
        self.LOG_CHANNEL = os.getenv("LOG_CHANNEL", "")  # Telegram channel ID for logging
        
        # Advanced Settings
        self.ENABLE_CHANNEL_PLAY = os.getenv("ENABLE_CHANNEL_PLAY", "true").lower() == "true"
        self.ENABLE_VIDEO_CALLS = os.getenv("ENABLE_VIDEO_CALLS", "true").lower() == "true"
        self.MAX_CONCURRENT_STREAMS = int(os.getenv("MAX_CONCURRENT_STREAMS", "10"))
        
        # Create directories
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
        os.makedirs("logs", exist_ok=True)
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.DISCORD_TOKEN == "your_discord_bot_token_here":
            raise ValueError("Please set DISCORD_TOKEN environment variable")
        
        if self.TELEGRAM_TOKEN == "your_telegram_bot_token_here":
            raise ValueError("Please set TELEGRAM_TOKEN environment variable")
        
        if self.OWNER_ID == 123456789:
            print("⚠️ WARNING: Please set OWNER_ID environment variable to your actual user ID")
        
        if self.MAX_QUEUE_SIZE < 1:
            raise ValueError("MAX_QUEUE_SIZE must be at least 1")
        
        if self.DEFAULT_VOLUME < 0 or self.DEFAULT_VOLUME > 1:
            raise ValueError("DEFAULT_VOLUME must be between 0 and 1")
    
    def is_sudoer(self, user_id: int) -> bool:
        """Check if user is a sudoer"""
        return user_id in self.SUDOERS
    
    def add_sudoer(self, user_id: int):
        """Add a sudoer"""
        if user_id not in self.SUDOERS:
            self.SUDOERS.append(user_id)
    
    def remove_sudoer(self, user_id: int):
        """Remove a sudoer (except owner)"""
        if user_id in self.SUDOERS and user_id != self.OWNER_ID:
            self.SUDOERS.remove(user_id)
    
    def get_env_template(self) -> str:
        """Get environment template for deployment"""
        return f"""
# Bot Tokens
DISCORD_TOKEN=your_discord_bot_token_here
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Owner Configuration
OWNER_ID=123456789

# Database
DATABASE_URL=sqlite:///musicbot.db

# Music Settings
MAX_QUEUE_SIZE=100
MAX_SONG_DURATION=3600
DEFAULT_VOLUME=0.5
DOWNLOAD_DIR=./downloads

# YouTube API (Optional - for better search)
YOUTUBE_API_KEY=your_youtube_api_key_here

# Bot Settings
MAINTENANCE_MODE=false
LOGGING_ENABLED=true
AUTO_LEAVE_TIMEOUT=300

# Spotify (Optional)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Rate Limiting
RATE_LIMIT_ENABLED=true
MAX_COMMANDS_PER_MINUTE=30

# Channels
SUPPORT_CHANNEL=https://t.me/your_support_channel
LOG_CHANNEL=

# Advanced
ENABLE_CHANNEL_PLAY=true
ENABLE_VIDEO_CALLS=true
MAX_CONCURRENT_STREAMS=10
        """.strip()

# Create a global config instance
config = Config()
