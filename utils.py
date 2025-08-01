import asyncio
import psutil
import logging
import os
import time
from typing import Dict, List, Union
import aiohttp
import json
from datetime import datetime, timedelta

from config import Config
from database import Database

logger = logging.getLogger(__name__)

class Utils:
    """Utility functions for the Music Bot"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database()
        
        # Rate limiting storage
        self.rate_limits = {}
        
        # Broadcast statistics
        self.broadcast_stats = {
            'last_broadcast': None,
            'total_broadcasts': 0,
            'successful_sends': 0,
            'failed_sends': 0
        }
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            return round(memory_mb, 2)
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0.0
    
    def get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return round(psutil.cpu_percent(interval=1), 2)
        except Exception as e:
            logger.error(f"Error getting CPU usage: {e}")
            return 0.0
    
    def get_disk_usage(self) -> Dict[str, float]:
        """Get disk usage information"""
        try:
            usage = psutil.disk_usage('/')
            return {
                'total': round(usage.total / (1024**3), 2),  # GB
                'used': round(usage.used / (1024**3), 2),    # GB
                'free': round(usage.free / (1024**3), 2),    # GB
                'percent': round((usage.used / usage.total) * 100, 2)
            }
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
    
    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        try:
            return {
                'memory': {
                    'usage_mb': self.get_memory_usage(),
                    'total_mb': round(psutil.virtual_memory().total / 1024 / 1024, 2),
                    'percent': round(psutil.virtual_memory().percent, 2)
                },
                'cpu': {
                    'usage_percent': self.get_cpu_usage(),
                    'count': psutil.cpu_count(),
                    'freq': psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                'disk': self.get_disk_usage(),
                'uptime': self.get_uptime_seconds(),
                'python_version': f"{psutil.version_info}",
                'platform': psutil.os.name
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def get_uptime_seconds(self) -> int:
        """Get system uptime in seconds"""
        try:
            return int(time.time() - psutil.boot_time())
        except Exception as e:
            logger.error(f"Error getting uptime: {e}")
            return 0
    
    def format_uptime(self, seconds: int) -> str:
        """Format uptime seconds to human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}m {seconds}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}d {hours}h"
    
    async def check_rate_limit(self, user_id: int, command: str = None) -> bool:
        """Check if user is rate limited"""
        if not self.config.RATE_LIMIT_ENABLED:
            return True
        
        current_time = time.time()
        user_key = f"{user_id}_{command}" if command else str(user_id)
        
        # Clean old entries
        if user_key in self.rate_limits:
            self.rate_limits[user_key] = [
                timestamp for timestamp in self.rate_limits[user_key]
                if current_time - timestamp < 60  # Keep last 1 minute
            ]
        else:
            self.rate_limits[user_key] = []
        
        # Check rate limit
        if len(self.rate_limits[user_key]) >= self.config.MAX_COMMANDS_PER_MINUTE:
            return False
        
        # Add current timestamp
        self.rate_limits[user_key].append(current_time)
        return True
    
    async def is_maintenance_mode(self) -> bool:
        """Check if bot is in maintenance mode"""
        return self.config.MAINTENANCE_MODE
    
    async def broadcast_message(self, message: str, flags: Dict, platform: str) -> Dict:
        """Broadcast message to all chats"""
        try:
            self.broadcast_stats['total_broadcasts'] += 1
            self.broadcast_stats['last_broadcast'] = datetime.now()
            
            success_count = 0
            failed_count = 0
            
            # Get all chats
            all_chats = await self.db.get_all_chats(platform if not flags.get('nobot') else None)
            
            for chat in all_chats:
                try:
                    chat_id = chat['chat_id']
                    chat_platform = chat['platform']
                    
                    # Skip if platform specific and doesn't match
                    if platform and chat_platform != platform:
                        continue
                    
                    # Send message based on platform
                    if chat_platform == 'telegram':
                        await self._send_telegram_broadcast(chat_id, message, flags)
                    elif chat_platform == 'discord':
                        await self._send_discord_broadcast(chat_id, message, flags)
                    
                    success_count += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Failed to broadcast to chat {chat_id}: {e}")
                    failed_count += 1
                    continue
            
            self.broadcast_stats['successful_sends'] += success_count
            self.broadcast_stats['failed_sends'] += failed_count
            
            return {
                'success': success_count,
                'failed': failed_count,
                'total': success_count + failed_count
            }
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            return {'success': 0, 'failed': 0, 'total': 0}
    
    async def _send_telegram_broadcast(self, chat_id: int, message: str, flags: Dict):
        """Send broadcast message to Telegram chat"""
        # This would integrate with your telegram bot instance
        # Implementation depends on how you access the telegram app
        pass
    
    async def _send_discord_broadcast(self, chat_id: int, message: str, flags: Dict):
        """Send broadcast message to Discord chat"""
        # This would integrate with your discord bot instance
        # Implementation depends on how you access the discord bot
        pass
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename for safe file operations"""
        import re
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove multiple spaces and replace with single underscore
        filename = re.sub(r'\s+', '_', filename)
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    async def download_file(self, url: str, file_path: str, 
                           max_size_mb: int = 50) -> bool:
        """Download file from URL with size limit"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    # Check file size
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                        logger.warning(f"File too large: {content_length} bytes")
                        return False
                    
                    # Download file
                    with open(file_path, 'wb') as f:
                        downloaded = 0
                        async for chunk in response.content.iter_chunked(8192):
                            downloaded += len(chunk)
                            
                            # Check size during download
                            if downloaded > max_size_mb * 1024 * 1024:
                                logger.warning(f"File exceeded size limit during download")
                                os.remove(file_path)
                                return False
                            
                            f.write(chunk)
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return False
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is properly formatted"""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+), re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    async def get_youtube_info(self, url: str) -> Dict:
        """Get basic YouTube video information"""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:500],  # Limit description
                    'upload_date': info.get('upload_date', ''),
                    'url': info.get('webpage_url', url)
                }
                
        except Exception as e:
            logger.error(f"Error getting YouTube info: {e}")
            return {}
    
    def create_progress_bar(self, current: int, total: int, length: int = 20) -> str:
        """Create a text progress bar"""
        if total == 0:
            return "█" * length
        
        progress = current / total
        filled_length = int(length * progress)
        bar = "█" * filled_length + "░" * (length - filled_length)
        percentage = round(progress * 100, 1)
        
        return f"{bar} {percentage}%"
    
    async def log_error(self, error: Exception, context: str = None):
        """Log error with context"""
        error_msg = f"Error in {context}: {str(error)}" if context else str(error)
        logger.error(error_msg, exc_info=True)
        
        # Optionally send to error tracking service
        # await self.send_error_notification(error_msg)
    
    def truncate_text(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    def escape_markdown(self, text: str) -> str:
        """Escape markdown special characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    def format_number(self, number: int) -> str:
        """Format large numbers with suffixes (K, M, B)"""
        if number < 1000:
            return str(number)
        elif number < 1000000:
            return f"{number/1000:.1f}K"
        elif number < 1000000000:
            return f"{number/1000000:.1f}M"
        else:
            return f"{number/1000000000:.1f}B"
    
    async def check_permissions(self, user_id: int, command: str) -> bool:
        """Check if user has permission to execute command"""
        # Check if user is banned
        if await self.db.is_globally_banned(user_id):
            return False
        
        # Check if maintenance mode (only sudoers allowed)
        if self.config.MAINTENANCE_MODE and not self.config.is_sudoer(user_id):
            return False
        
        # Admin-only commands
        admin_commands = [
            'stats', 'broadcast', 'gban', 'ungban', 'auth', 'unauth', 
            'maintenance', 'logs', 'blacklistchat', 'whitelistchat'
        ]
        
        if command in admin_commands:
            return await self.db.is_authorized(user_id) or self.config.is_sudoer(user_id)
        
        # Sudoer-only commands
        sudoer_commands = ['logs', 'maintenance', 'broadcast']
        if command in sudoer_commands:
            return self.config.is_sudoer(user_id)
        
        return True
    
    def get_random_color(self) -> int:
        """Get random color for Discord embeds"""
        import random
        colors = [
            0xFF6B6B,  # Red
            0x4ECDC4,  # Teal
            0x45B7D1,  # Blue
            0x96CEB4,  # Green
            0xFECE2B,  # Yellow
            0xFD79A8,  # Pink
            0xE17055,  # Orange
            0x6C5CE7,  # Purple
        ]
        return random.choice(colors)
    
    async def send_notification(self, message: str, level: str = "info"):
        """Send notification to log channel if configured"""
        if not self.config.LOG_CHANNEL:
            return
        
        try:
            # Implementation depends on your telegram bot setup
            # This would send to the configured log channel
            logger.info(f"Notification ({level}): {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def get_command_help(self, command: str) -> str:
        """Get help text for a specific command"""
        help_texts = {
            'play': "Play audio in voice chat\nUsage: /play <song name or URL>",
            'vplay': "Play video in voice chat\nUsage: /vplay <song name or URL>",
            'song': "Download song as MP3/MP4\nUsage: /song <song name or URL>",
            'queue': "Show current music queue\nUsage: /queue",
            'skip': "Skip current song\nUsage: /skip",
            'stop': "Stop playback and clear queue\nUsage: /stop",
            'pause': "Pause current playback\nUsage: /pause",
            'resume': "Resume paused playback\nUsage: /resume",
            'shuffle': "Shuffle current queue\nUsage: /shuffle",
            'loop': "Set loop mode (0=off, 1=song, 2=queue, 3-10=repeat N times)\nUsage: /loop [mode]",
            'speed': "Set playback speed (0.5-2.0)\nUsage: /speed <speed>",
            'seek': "Seek to position in seconds\nUsage: /seek <seconds>",
            'ping': "Check bot latency and status\nUsage: /ping",
            'help': "Show this help message\nUsage: /help [command]",
            'stats': "Show bot statistics (Admin only)\nUsage: /stats",
            'broadcast': "Broadcast message to all chats (Sudoer only)\nUsage: /broadcast [-flags] <message>",
            'gban': "Globally ban a user (Sudoer only)\nUsage: /gban <user_id>",
            'ungban': "Remove global ban (Sudoer only)\nUsage: /ungban <user_id>",
            'auth': "Authorize user as admin (Sudoer only)\nUsage: /auth <user_id>",
            'unauth': "Remove admin authorization (Sudoer only)\nUsage: /unauth <user_id>",
            'maintenance': "Toggle maintenance mode (Sudoer only)\nUsage: /maintenance [enable/disable]",
            'logs': "Get bot logs (Sudoer only)\nUsage: /logs",
            'cplay': "Play in connected channel (Admin only)\nUsage: /cplay <song>",
            'cvplay': "Play video in connected channel (Admin only)\nUsage: /cvplay <song>",
            'channelplay': "Connect channel for streaming (Admin only)\nUsage: /channelplay"
        }
        
        return help_texts.get(command, "Unknown command. Use /help to see all commands.")
    
    async def cleanup_temp_files(self):
        """Clean up temporary files and downloads"""
        try:
            temp_dirs = [self.config.DOWNLOAD_DIR, './temp', './cache']
            
            for temp_dir in temp_dirs:
                if not os.path.exists(temp_dir):
                    continue
                
                current_time = time.time()
                
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    
                    if os.path.isfile(file_path):
                        # Delete files older than 1 hour
                        file_age = current_time - os.path.getctime(file_path)
                        if file_age > 3600:  # 1 hour
                            os.remove(file_path)
                            logger.info(f"Cleaned up temp file: {filename}")
                            
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
    
    def get_platform_emoji(self, platform: str) -> str:
        """Get emoji for platform"""
        emojis = {
            'discord': '🎮',
            'telegram': '✈️',
            'youtube': '📺',
            'spotify': '🎵'
        }
        return emojis.get(platform.lower(), '🤖')
    
    def format_timestamp(self, timestamp: Union[str, datetime]) -> str:
        """Format timestamp to readable format"""
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            now = datetime.now(timestamp.tzinfo)
            diff = now - timestamp
            
            if diff.days > 0:
                return f"{diff.days} days ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hours ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minutes ago"
            else:
                return "Just now"
                
        except Exception as e:
            logger.error(f"Error formatting timestamp: {e}")
            return "Unknown"
    
    async def get_bot_info(self) -> Dict:
        """Get comprehensive bot information"""
        try:
            bot_stats = await self.db.get_bot_stats()
            system_stats = self.get_system_stats()
            
            return {
                'version': '1.0.0',
                'name': 'Ultimate Music Bot',
                'description': 'Multi-platform music bot for Discord and Telegram',
                'features': [
                    'Multi-platform support (Discord + Telegram)',
                    'High-quality audio streaming',
                    'YouTube downloads (MP3/MP4)',
                    'Queue management with shuffle/loop',
                    'Speed control and seeking',
                    'Channel streaming for Telegram',
                    'Admin controls and statistics',
                    'Global ban system',
                    'Rate limiting and spam protection'
                ],
                'stats': bot_stats,
                'system': system_stats,
                'broadcast_stats': self.broadcast_stats,
                'config': {
                    'max_queue_size': self.config.MAX_QUEUE_SIZE,
                    'max_song_duration': self.config.MAX_SONG_DURATION,
                    'auto_leave_timeout': self.config.AUTO_LEAVE_TIMEOUT,
                    'rate_limit_enabled': self.config.RATE_LIMIT_ENABLED,
                    'maintenance_mode': self.config.MAINTENANCE_MODE
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return {}
    
    def create_embed_dict(self, title: str, description: str = None, 
                         color: int = None, fields: List[Dict] = None,
                         thumbnail: str = None, footer: str = None) -> Dict:
        """Create embed dictionary for cross-platform compatibility"""
        embed = {
            'title': title,
            'color': color or self.get_random_color()
        }
        
        if description:
            embed['description'] = description
        
        if fields:
            embed['fields'] = fields
        
        if thumbnail:
            embed['thumbnail'] = {'url': thumbnail}
        
        if footer:
            embed['footer'] = {'text': footer}
        
        return embed
    
    async def schedule_task(self, func, delay: int, *args, **kwargs):
        """Schedule a task to run after delay"""
        await asyncio.sleep(delay)
        try:
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")
    
    def get_queue_info_text(self, queue_data: Dict) -> str:
        """Generate formatted queue information text"""
        if not queue_data.get('queue') and not queue_data.get('current'):
            return "📜 Queue is empty!"
        
        text = "📜 **Music Queue:**\n\n"
        
        if queue_data.get('current'):
            current = queue_data['current']
            text += f"🎵 **Now Playing:**\n{current['title']}\n\n"
        
        if queue_data.get('queue'):
            text += f"📋 **Up Next ({len(queue_data['queue'])} songs):**\n"
            for i, song in enumerate(queue_data['queue'][:10], 1):
                text += f"{i}. {song['title']}\n"
            
            if len(queue_data['queue']) > 10:
                text += f"\n... and {len(queue_data['queue']) - 10} more songs"
        
        # Add loop info if enabled
        loop_mode = queue_data.get('loop_mode', 0)
        if loop_mode > 0:
            loop_text = {
                1: "🔂 Loop: Current Song",
                2: "🔁 Loop: Queue"
            }.get(loop_mode, f"🔄 Loop: {loop_mode} times")
            text += f"\n\n{loop_text}"
        
        # Add speed info if not default
        speed = queue_data.get('speed', 1.0)
        if speed != 1.0:
            text += f"\n🏃 Speed: {speed}x"
        
        return text
