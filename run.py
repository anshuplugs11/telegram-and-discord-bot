# run.py - Main startup script
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import keep_alive first to start web server
from keep_alive import initialize_keep_alive, bot_status

# Configure logging before importing other modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    try:
        logger.info("🎵 Starting Ultimate Music Bot...")
        
        # Initialize keep-alive system
        if not initialize_keep_alive():
            logger.error("❌ Failed to initialize keep-alive system")
            return
        
        # Update bot status
        bot_status['status'] = 'starting_bot'
        
        # Import and start the bot
        from main import MusicBot
        
        bot = MusicBot()
        bot_status['status'] = 'running'
        
        logger.info("🚀 Bot started successfully!")
        
        # Run the bot
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
        bot_status['status'] = 'stopped'
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")
        bot_status['status'] = 'crashed'
        bot_status['error_count'] += 1
        raise

if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs('logs', exist_ok=True)
    os.makedirs('downloads', exist_ok=True)
    os.makedirs('cache', exist_ok=True)
    
    # Run the bot
    try:
        if sys.platform == 'win32':
            # Windows specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main())
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        sys.exit(1)
