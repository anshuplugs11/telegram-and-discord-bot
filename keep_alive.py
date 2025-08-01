from flask import Flask, jsonify
import threading
import requests
import time
import logging
import os
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot status tracking
bot_status = {
    'status': 'starting',
    'start_time': datetime.now(),
    'last_ping': None,
    'error_count': 0,
    'restart_count': 0
}

@app.route('/')
def home():
    """Health check endpoint"""
    uptime = datetime.now() - bot_status['start_time']
    return jsonify({
        'status': 'alive',
        'message': 'Ultimate Music Bot is running!',
        'uptime': str(uptime),
        'bot_status': bot_status['status'],
        'last_ping': bot_status['last_ping'].isoformat() if bot_status['last_ping'] else None,
        'error_count': bot_status['error_count'],
        'restart_count': bot_status['restart_count'],
        'features': [
            'Discord Music Bot',
            'Telegram Music Bot', 
            'YouTube Downloads',
            'Queue Management',
            'Admin Controls',
            'Multi-platform Support'
        ]
    })

@app.route('/health')
def health():
    """Detailed health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime_seconds': (datetime.now() - bot_status['start_time']).total_seconds(),
        'bot_details': bot_status
    })

@app.route('/stats')
def stats():
    """Bot statistics endpoint"""
    try:
        # Import here to avoid circular imports
        from main import bot
        
        return jsonify({
            'commands_executed': bot.stats.get('commands_executed', 0),
            'songs_played': bot.stats.get('songs_played', 0),
            'users_served': len(bot.stats.get('users_served', set())),
            'chats_served': len(bot.stats.get('chats_served', set())),
            'uptime': str(datetime.now() - bot_status['start_time'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/restart', methods=['POST'])
def restart_bot():
    """Restart bot endpoint (for authorized users only)"""
    try:
        # Add authentication here if needed
        bot_status['restart_count'] += 1
        bot_status['status'] = 'restarting'
        
        # This would trigger a bot restart
        # Implementation depends on your deployment setup
        
        return jsonify({
            'message': 'Bot restart initiated',
            'restart_count': bot_status['restart_count']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def keep_alive():
    """Keep the web server alive"""
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)

def start_keep_alive():
    """Start the keep alive server in a separate thread"""
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    logger.info("Keep-alive server started")

def self_ping():
    """Ping self to prevent sleeping (for free hosting services)"""
    url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:8080')
    
    while True:
        try:
            time.sleep(300)  # Wait 5 minutes
            
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                bot_status['last_ping'] = datetime.now()
                bot_status['status'] = 'running'
                logger.info("Self-ping successful")
            else:
                logger.warning(f"Self-ping failed with status: {response.status_code}")
                bot_status['error_count'] += 1
                
        except Exception as e:
            logger.error(f"Self-ping error: {e}")
            bot_status['error_count'] += 1
            bot_status['status'] = 'error'

def start_self_ping():
    """Start self-ping in a separate thread"""
    if os.environ.get('RENDER_EXTERNAL_URL'):
        t = threading.Thread(target=self_ping, daemon=True)
        t.start()
        logger.info("Self-ping started")
    else:
        logger.info("RENDER_EXTERNAL_URL not set, skipping self-ping")

# Uptime monitoring for external services
class UptimeBot:
    """Monitor and report uptime to external services"""
    
    def __init__(self):
        self.uptime_urls = [
            # Add your uptime monitoring URLs here
            # os.environ.get('UPTIME_URL_1'),
            # os.environ.get('UPTIME_URL_2'),
        ]
        self.check_interval = 600  # 10 minutes
    
    def start_monitoring(self):
        """Start uptime monitoring"""
        if not any(self.uptime_urls):
            logger.info("No uptime URLs configured")
            return
        
        t = threading.Thread(target=self._monitor_loop, daemon=True)
        t.start()
        logger.info("Uptime monitoring started")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                time.sleep(self.check_interval)
                self._send_heartbeat()
            except Exception as e:
                logger.error(f"Uptime monitoring error: {e}")
    
    def _send_heartbeat(self):
        """Send heartbeat to uptime services"""
        for url in self.uptime_urls:
            if not url:
                continue
            
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    logger.info(f"Heartbeat sent to {url}")
                else:
                    logger.warning(f"Heartbeat failed for {url}: {response.status_code}")
            except Exception as e:
                logger.error(f"Heartbeat error for {url}: {e}")

# Environment check
def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'DISCORD_TOKEN',
        'TELEGRAM_TOKEN',
        'OWNER_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("Environment check passed")
    return True

def setup_logging():
    """Setup enhanced logging for production"""
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # File handler
    file_handler = logging.FileHandler('logs/bot.log')
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)

def initialize_keep_alive():
    """Initialize all keep-alive components"""
    logger.info("Initializing keep-alive system...")
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed!")
        return False
    
    # Setup logging
    setup_logging()
    
    # Start web server
    start_keep_alive()
    
    # Start self-ping
    start_self_ping()
    
    # Start uptime monitoring
    uptime_bot = UptimeBot()
    uptime_bot.start_monitoring()
    
    # Update status
    bot_status['status'] = 'initialized'
    logger.info("Keep-alive system initialized successfully")
    
    return True

if __name__ == "__main__":
    # Run as standalone keep-alive server
    initialize_keep_alive()
