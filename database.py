import asyncio
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Union
import json

logger = logging.getLogger(__name__)

class Database:
    """Database handler for the Music Bot"""
    
    def __init__(self, db_path: str = "musicbot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        platform TEXT,
                        is_authorized BOOLEAN DEFAULT FALSE,
                        is_banned BOOLEAN DEFAULT FALSE,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_commands INTEGER DEFAULT 0,
                        total_songs_played INTEGER DEFAULT 0
                    )
                ''')
                
                # Chats table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chats (
                        chat_id INTEGER,
                        platform TEXT,
                        chat_title TEXT,
                        chat_type TEXT,
                        is_blacklisted BOOLEAN DEFAULT FALSE,
                        join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_commands INTEGER DEFAULT 0,
                        total_songs_played INTEGER DEFAULT 0,
                        PRIMARY KEY (chat_id, platform)
                    )
                ''')
                
                # Global bans table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS global_bans (
                        user_id INTEGER PRIMARY KEY,
                        reason TEXT,
                        banned_by INTEGER,
                        ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Bot statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        stat_name TEXT PRIMARY KEY,
                        stat_value TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Command logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS command_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        chat_id INTEGER,
                        platform TEXT,
                        command TEXT,
                        arguments TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT TRUE,
                        error_message TEXT
                    )
                ''')
                
                # Music history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS music_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        chat_id INTEGER,
                        platform TEXT,
                        song_title TEXT,
                        song_url TEXT,
                        duration INTEGER,
                        play_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Settings table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_settings (
                        chat_id INTEGER,
                        platform TEXT,
                        setting_name TEXT,
                        setting_value TEXT,
                        PRIMARY KEY (chat_id, platform, setting_name)
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                      last_name: str = None, platform: str = 'telegram') -> bool:
        """Add or update user in database"""
        try:
            def _add_user():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO users 
                        (user_id, username, first_name, last_name, platform, last_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, first_name, last_name, platform, datetime.now()))
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_add_user)
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    async def add_chat(self, chat_id: int, platform: str, chat_title: str = None, 
                      chat_type: str = 'group') -> bool:
        """Add or update chat in database"""
        try:
            def _add_chat():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO chats 
                        (chat_id, platform, chat_title, chat_type, last_active)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (chat_id, platform, chat_title, chat_type, datetime.now()))
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_add_chat)
            
        except Exception as e:
            logger.error(f"Error adding chat: {e}")
            return False
    
    async def is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        try:
            def _check_auth():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT is_authorized FROM users WHERE user_id = ?', (user_id,))
                    result = cursor.fetchone()
                    return result[0] if result else False
            
            return await asyncio.to_thread(_check_auth)
            
        except Exception as e:
            logger.error(f"Error checking authorization: {e}")
            return False
    
    async def authorize_user(self, user_id: int) -> bool:
        """Authorize a user"""
        try:
            def _authorize():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE users SET is_authorized = TRUE 
                        WHERE user_id = ?
                    ''', (user_id,))
                    
                    if cursor.rowcount == 0:
                        # User doesn't exist, create them
                        cursor.execute('''
                            INSERT INTO users (user_id, is_authorized) 
                            VALUES (?, TRUE)
                        ''', (user_id,))
                    
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_authorize)
            
        except Exception as e:
            logger.error(f"Error authorizing user: {e}")
            return False
    
    async def unauthorize_user(self, user_id: int) -> bool:
        """Remove authorization from a user"""
        try:
            def _unauthorize():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE users SET is_authorized = FALSE 
                        WHERE user_id = ?
                    ''', (user_id,))
                    conn.commit()
                    return cursor.rowcount > 0
            
            return await asyncio.to_thread(_unauthorize)
            
        except Exception as e:
            logger.error(f"Error unauthorizing user: {e}")
            return False
    
    async def is_globally_banned(self, user_id: int) -> bool:
        """Check if user is globally banned"""
        try:
            def _check_ban():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT user_id FROM global_bans WHERE user_id = ?', (user_id,))
                    return cursor.fetchone() is not None
            
            return await asyncio.to_thread(_check_ban)
            
        except Exception as e:
            logger.error(f"Error checking global ban: {e}")
            return False
    
    async def global_ban_user(self, user_id: int, reason: str = "No reason provided", 
                             banned_by: int = None) -> bool:
        """Globally ban a user"""
        try:
            def _ban_user():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO global_bans 
                        (user_id, reason, banned_by, ban_date)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, reason, banned_by, datetime.now()))
                    
                    # Also mark user as banned in users table
                    cursor.execute('''
                        UPDATE users SET is_banned = TRUE 
                        WHERE user_id = ?
                    ''', (user_id,))
                    
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_ban_user)
            
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False
    
    async def global_unban_user(self, user_id: int) -> bool:
        """Remove global ban from a user"""
        try:
            def _unban_user():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM global_bans WHERE user_id = ?', (user_id,))
                    
                    # Also update users table
                    cursor.execute('''
                        UPDATE users SET is_banned = FALSE 
                        WHERE user_id = ?
                    ''', (user_id,))
                    
                    conn.commit()
                    return cursor.rowcount > 0
            
            return await asyncio.to_thread(_unban_user)
            
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False
    
    async def is_chat_blacklisted(self, chat_id: int, platform: str) -> bool:
        """Check if chat is blacklisted"""
        try:
            def _check_blacklist():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT is_blacklisted FROM chats 
                        WHERE chat_id = ? AND platform = ?
                    ''', (chat_id, platform))
                    result = cursor.fetchone()
                    return result[0] if result else False
            
            return await asyncio.to_thread(_check_blacklist)
            
        except Exception as e:
            logger.error(f"Error checking chat blacklist: {e}")
            return False
    
    async def blacklist_chat(self, chat_id: int, platform: str) -> bool:
        """Blacklist a chat"""
        try:
            def _blacklist():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE chats SET is_blacklisted = TRUE 
                        WHERE chat_id = ? AND platform = ?
                    ''', (chat_id, platform))
                    
                    if cursor.rowcount == 0:
                        # Chat doesn't exist, create it
                        cursor.execute('''
                            INSERT INTO chats (chat_id, platform, is_blacklisted) 
                            VALUES (?, ?, TRUE)
                        ''', (chat_id, platform))
                    
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_blacklist)
            
        except Exception as e:
            logger.error(f"Error blacklisting chat: {e}")
            return False
    
    async def whitelist_chat(self, chat_id: int, platform: str) -> bool:
        """Remove chat from blacklist"""
        try:
            def _whitelist():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE chats SET is_blacklisted = FALSE 
                        WHERE chat_id = ? AND platform = ?
                    ''', (chat_id, platform))
                    conn.commit()
                    return cursor.rowcount > 0
            
            return await asyncio.to_thread(_whitelist)
            
        except Exception as e:
            logger.error(f"Error whitelisting chat: {e}")
            return False
    
    async def log_command(self, user_id: int, chat_id: int, platform: str, 
                         command: str, arguments: str = None, success: bool = True, 
                         error_message: str = None) -> bool:
        """Log a command execution"""
        try:
            def _log_command():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO command_logs 
                        (user_id, chat_id, platform, command, arguments, success, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, chat_id, platform, command, arguments, success, error_message))
                    
                    # Update user stats
                    cursor.execute('''
                        UPDATE users SET total_commands = total_commands + 1, last_active = ?
                        WHERE user_id = ?
                    ''', (datetime.now(), user_id))
                    
                    # Update chat stats
                    cursor.execute('''
                        UPDATE chats SET total_commands = total_commands + 1, last_active = ?
                        WHERE chat_id = ? AND platform = ?
                    ''', (datetime.now(), chat_id, platform))
                    
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_log_command)
            
        except Exception as e:
            logger.error(f"Error logging command: {e}")
            return False
    
    async def log_music_play(self, user_id: int, chat_id: int, platform: str, 
                           song_title: str, song_url: str, duration: int = 0) -> bool:
        """Log a music play event"""
        try:
            def _log_music():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO music_history 
                        (user_id, chat_id, platform, song_title, song_url, duration)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, chat_id, platform, song_title, song_url, duration))
                    
                    # Update user music stats
                    cursor.execute('''
                        UPDATE users SET total_songs_played = total_songs_played + 1
                        WHERE user_id = ?
                    ''', (user_id,))
                    
                    # Update chat music stats
                    cursor.execute('''
                        UPDATE chats SET total_songs_played = total_songs_played + 1
                        WHERE chat_id = ? AND platform = ?
                    ''', (chat_id, platform))
                    
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_log_music)
            
        except Exception as e:
            logger.error(f"Error logging music play: {e}")
            return False
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict]:
        """Get user statistics"""
        try:
            def _get_stats():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT username, first_name, last_name, platform, is_authorized, 
                               is_banned, join_date, last_active, total_commands, total_songs_played
                        FROM users WHERE user_id = ?
                    ''', (user_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'user_id': user_id,
                            'username': result[0],
                            'first_name': result[1],
                            'last_name': result[2],
                            'platform': result[3],
                            'is_authorized': result[4],
                            'is_banned': result[5],
                            'join_date': result[6],
                            'last_active': result[7],
                            'total_commands': result[8],
                            'total_songs_played': result[9]
                        }
                    return None
            
            return await asyncio.to_thread(_get_stats)
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None
    
    async def get_chat_stats(self, chat_id: int, platform: str) -> Optional[Dict]:
        """Get chat statistics"""
        try:
            def _get_stats():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT chat_title, chat_type, is_blacklisted, join_date, 
                               last_active, total_commands, total_songs_played
                        FROM chats WHERE chat_id = ? AND platform = ?
                    ''', (chat_id, platform))
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            'chat_id': chat_id,
                            'platform': platform,
                            'chat_title': result[0],
                            'chat_type': result[1],
                            'is_blacklisted': result[2],
                            'join_date': result[3],
                            'last_active': result[4],
                            'total_commands': result[5],
                            'total_songs_played': result[6]
                        }
                    return None
            
            return await asyncio.to_thread(_get_stats)
            
        except Exception as e:
            logger.error(f"Error getting chat stats: {e}")
            return None
    
    async def get_bot_stats(self) -> Dict:
        """Get overall bot statistics"""
        try:
            def _get_stats():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Total users
                    cursor.execute('SELECT COUNT(*) FROM users')
                    total_users = cursor.fetchone()[0]
                    
                    # Total chats
                    cursor.execute('SELECT COUNT(*) FROM chats')
                    total_chats = cursor.fetchone()[0]
                    
                    # Total commands
                    cursor.execute('SELECT SUM(total_commands) FROM users')
                    total_commands = cursor.fetchone()[0] or 0
                    
                    # Total songs played
                    cursor.execute('SELECT SUM(total_songs_played) FROM users')
                    total_songs = cursor.fetchone()[0] or 0
                    
                    # Active users (last 24 hours)
                    cursor.execute('''
                        SELECT COUNT(*) FROM users 
                        WHERE last_active > datetime('now', '-1 day')
                    ''')
                    active_users = cursor.fetchone()[0]
                    
                    # Active chats (last 24 hours)
                    cursor.execute('''
                        SELECT COUNT(*) FROM chats 
                        WHERE last_active > datetime('now', '-1 day')
                    ''')
                    active_chats = cursor.fetchone()[0]
                    
                    # Banned users
                    cursor.execute('SELECT COUNT(*) FROM global_bans')
                    banned_users = cursor.fetchone()[0]
                    
                    # Blacklisted chats
                    cursor.execute('SELECT COUNT(*) FROM chats WHERE is_blacklisted = TRUE')
                    blacklisted_chats = cursor.fetchone()[0]
                    
                    return {
                        'total_users': total_users,
                        'total_chats': total_chats,
                        'total_commands': total_commands,
                        'total_songs_played': total_songs,
                        'active_users_24h': active_users,
                        'active_chats_24h': active_chats,
                        'banned_users': banned_users,
                        'blacklisted_chats': blacklisted_chats
                    }
            
            return await asyncio.to_thread(_get_stats)
            
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {}
    
    async def get_top_users(self, limit: int = 10, by: str = 'commands') -> List[Dict]:
        """Get top users by commands or songs played"""
        try:
            def _get_top():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    order_by = 'total_commands' if by == 'commands' else 'total_songs_played'
                    
                    cursor.execute(f'''
                        SELECT user_id, username, first_name, {order_by}
                        FROM users 
                        WHERE {order_by} > 0
                        ORDER BY {order_by} DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    results = cursor.fetchall()
                    return [
                        {
                            'user_id': row[0],
                            'username': row[1],
                            'first_name': row[2],
                            'count': row[3]
                        }
                        for row in results
                    ]
            
            return await asyncio.to_thread(_get_top)
            
        except Exception as e:
            logger.error(f"Error getting top users: {e}")
            return []
    
    async def get_top_chats(self, limit: int = 10, by: str = 'commands') -> List[Dict]:
        """Get top chats by commands or songs played"""
        try:
            def _get_top():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    order_by = 'total_commands' if by == 'commands' else 'total_songs_played'
                    
                    cursor.execute(f'''
                        SELECT chat_id, platform, chat_title, {order_by}
                        FROM chats 
                        WHERE {order_by} > 0
                        ORDER BY {order_by} DESC 
                        LIMIT ?
                    ''', (limit,))
                    
                    results = cursor.fetchall()
                    return [
                        {
                            'chat_id': row[0],
                            'platform': row[1],
                            'chat_title': row[2],
                            'count': row[3]
                        }
                        for row in results
                    ]
            
            return await asyncio.to_thread(_get_top)
            
        except Exception as e:
            logger.error(f"Error getting top chats: {e}")
            return []
    
    async def get_recent_songs(self, limit: int = 10, chat_id: int = None, 
                              platform: str = None) -> List[Dict]:
        """Get recently played songs"""
        try:
            def _get_recent():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    query = '''
                        SELECT mh.song_title, mh.song_url, mh.duration, mh.play_date,
                               u.username, u.first_name, mh.chat_id, mh.platform
                        FROM music_history mh
                        LEFT JOIN users u ON mh.user_id = u.user_id
                    '''
                    params = []
                    
                    if chat_id and platform:
                        query += ' WHERE mh.chat_id = ? AND mh.platform = ?'
                        params.extend([chat_id, platform])
                    
                    query += ' ORDER BY mh.play_date DESC LIMIT ?'
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    return [
                        {
                            'song_title': row[0],
                            'song_url': row[1],
                            'duration': row[2],
                            'play_date': row[3],
                            'username': row[4],
                            'first_name': row[5],
                            'chat_id': row[6],
                            'platform': row[7]
                        }
                        for row in results
                    ]
            
            return await asyncio.to_thread(_get_recent)
            
        except Exception as e:
            logger.error(f"Error getting recent songs: {e}")
            return []
    
    async def get_command_logs(self, limit: int = 50, user_id: int = None, 
                              chat_id: int = None, platform: str = None) -> List[Dict]:
        """Get command execution logs"""
        try:
            def _get_logs():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    query = '''
                        SELECT cl.user_id, cl.chat_id, cl.platform, cl.command, 
                               cl.arguments, cl.timestamp, cl.success, cl.error_message,
                               u.username, u.first_name
                        FROM command_logs cl
                        LEFT JOIN users u ON cl.user_id = u.user_id
                    '''
                    params = []
                    conditions = []
                    
                    if user_id:
                        conditions.append('cl.user_id = ?')
                        params.append(user_id)
                    
                    if chat_id:
                        conditions.append('cl.chat_id = ?')
                        params.append(chat_id)
                    
                    if platform:
                        conditions.append('cl.platform = ?')
                        params.append(platform)
                    
                    if conditions:
                        query += ' WHERE ' + ' AND '.join(conditions)
                    
                    query += ' ORDER BY cl.timestamp DESC LIMIT ?'
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    return [
                        {
                            'user_id': row[0],
                            'chat_id': row[1],
                            'platform': row[2],
                            'command': row[3],
                            'arguments': row[4],
                            'timestamp': row[5],
                            'success': row[6],
                            'error_message': row[7],
                            'username': row[8],
                            'first_name': row[9]
                        }
                        for row in results
                    ]
            
            return await asyncio.to_thread(_get_logs)
            
        except Exception as e:
            logger.error(f"Error getting command logs: {e}")
            return []
    
    async def set_chat_setting(self, chat_id: int, platform: str, 
                              setting_name: str, setting_value: str) -> bool:
        """Set a chat setting"""
        try:
            def _set_setting():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO chat_settings 
                        (chat_id, platform, setting_name, setting_value)
                        VALUES (?, ?, ?, ?)
                    ''', (chat_id, platform, setting_name, setting_value))
                    conn.commit()
                    return True
            
            return await asyncio.to_thread(_set_setting)
            
        except Exception as e:
            logger.error(f"Error setting chat setting: {e}")
            return False
    
    async def get_chat_setting(self, chat_id: int, platform: str, 
                              setting_name: str, default_value: str = None) -> str:
        """Get a chat setting"""
        try:
            def _get_setting():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT setting_value FROM chat_settings 
                        WHERE chat_id = ? AND platform = ? AND setting_name = ?
                    ''', (chat_id, platform, setting_name))
                    result = cursor.fetchone()
                    return result[0] if result else default_value
            
            return await asyncio.to_thread(_get_setting)
            
        except Exception as e:
            logger.error(f"Error getting chat setting: {e}")
            return default_value
    
    async def get_all_users(self) -> List[int]:
        """Get all user IDs"""
        try:
            def _get_users():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT DISTINCT user_id FROM users')
                    return [row[0] for row in cursor.fetchall()]
            
            return await asyncio.to_thread(_get_users)
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []
    
    async def get_all_chats(self, platform: str = None) -> List[Dict]:
        """Get all chats"""
        try:
            def _get_chats():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    if platform:
                        cursor.execute('''
                            SELECT chat_id, platform, chat_title, chat_type 
                            FROM chats WHERE platform = ? AND is_blacklisted = FALSE
                        ''', (platform,))
                    else:
                        cursor.execute('''
                            SELECT chat_id, platform, chat_title, chat_type 
                            FROM chats WHERE is_blacklisted = FALSE
                        ''')
                    
                    return [
                        {
                            'chat_id': row[0],
                            'platform': row[1],
                            'chat_title': row[2],
                            'chat_type': row[3]
                        }
                        for row in cursor.fetchall()
                    ]
            
            return await asyncio.to_thread(_get_chats)
            
        except Exception as e:
            logger.error(f"Error getting all chats: {e}")
            return []
    
    async def cleanup_old_logs(self, days: int = 30) -> int:
        """Clean up old logs (older than specified days)"""
        try:
            def _cleanup():
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Clean command logs
                    cursor.execute('''
                        DELETE FROM command_logs 
                        WHERE timestamp < datetime('now', '-{} days')
                    '''.format(days))
                    cmd_deleted = cursor.rowcount
                    
                    # Clean music history
                    cursor.execute('''
                        DELETE FROM music_history 
                        WHERE play_date < datetime('now', '-{} days')
                    '''.format(days))
                    music_deleted = cursor.rowcount
                    
                    conn.commit()
                    return cmd_deleted + music_deleted
            
            return await asyncio.to_thread(_cleanup)
            
        except Exception as e:
            logger.error(f"Error cleaning up logs: {e}")
            return 0
    
    async def backup_database(self, backup_path: str) -> bool:
        """Create a backup of the database"""
        try:
            def _backup():
                import shutil
                shutil.copy2(self.db_path, backup_path)
                return True
            
            return await asyncio.to_thread(_backup)
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            return False
