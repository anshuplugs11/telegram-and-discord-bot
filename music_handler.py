import asyncio
import os
import random
import re
import time
from typing import Dict, List, Optional, Union
import logging

import yt_dlp
import discord
from discord import FFmpegPCMAudio, FFmpegOpusAudio
import aiofiles
import aiohttp

from config import Config
from database import Database
from utils import Utils

logger = logging.getLogger(__name__)

class MusicHandler:
    """Handles all music-related functionality"""
    
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.utils = Utils()
        
        # Music queues for different chats
        self.queues: Dict[int, List[Dict]] = {}
        self.current_songs: Dict[int, Dict] = {}
        self.loop_modes: Dict[int, int] = {}  # 0=off, 1=song, 2=queue, 3-10=repeat N times
        self.playback_speeds: Dict[int, float] = {}
        self.voice_clients: Dict[int, Union[discord.VoiceClient, object]] = {}
        
        # Channel connections for Telegram
        self.channel_connections: Dict[int, int] = {}  # group_id -> channel_id
        
        # YouTube downloader configuration
        self.ydl_opts_audio = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': f'{self.config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        self.ydl_opts_video = {
            'format': 'best[height<=720]/best',
            'noplaylist': True,
            'outtmpl': f'{self.config.DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        self.ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    async def search_and_play(self, query: str, ctx, platform: str, video: bool = False) -> Dict:
        """Search for a song and add it to the queue"""
        try:
            chat_id = self._get_chat_id(ctx, platform)
            
            # Initialize queue if not exists
            if chat_id not in self.queues:
                self.queues[chat_id] = []
            
            # Search for the song
            song_info = await self._search_song(query)
            
            if not song_info:
                raise Exception("Song not found!")
            
            # Add to queue
            song_data = {
                'title': song_info['title'],
                'url': song_info['url'],
                'duration': song_info['duration'],
                'thumbnail': song_info.get('thumbnail', ''),
                'views': song_info.get('view_count', 'Unknown'),
                'uploader': song_info.get('uploader', 'Unknown'),
                'video': video,
                'requested_by': self._get_user_id(ctx, platform),
                'platform': platform
            }
            
            self.queues[chat_id].append(song_data)
            
            # Start playing if nothing is currently playing
            if chat_id not in self.current_songs or not self.current_songs[chat_id]:
                await self._play_next(chat_id, ctx, platform)
            
            return song_data
            
        except Exception as e:
            logger.error(f"Error in search_and_play: {e}")
            raise
    
    async def _search_song(self, query: str) -> Optional[Dict]:
        """Search for a song using yt-dlp"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts_info) as ydl:
                if not self._is_url(query):
                    query = f"ytsearch:{query}"
                
                info = await asyncio.to_thread(ydl.extract_info, query, download=False)
                
                if 'entries' in info and info['entries']:
                    return info['entries'][0]
                elif info:
                    return info
                
                return None
                
        except Exception as e:
            logger.error(f"Error searching song: {e}")
            return None
    
    async def _play_next(self, chat_id: int, ctx, platform: str):
        """Play the next song in queue"""
        try:
            if not self.queues.get(chat_id):
                # Queue is empty
                self.current_songs.pop(chat_id, None)
                return
            
            song = self.queues[chat_id].pop(0)
            self.current_songs[chat_id] = song
            
            # Get audio source
            audio_source = await self._get_audio_source(song['url'], chat_id)
            
            if platform == 'discord':
                await self._play_discord(ctx, audio_source, chat_id)
            else:
                await self._play_telegram(ctx, song, chat_id)
            
        except Exception as e:
            logger.error(f"Error playing next song: {e}")
            # Try next song in queue
            if self.queues.get(chat_id):
                await self._play_next(chat_id, ctx, platform)
    
    async def _get_audio_source(self, url: str, chat_id: int) -> str:
        """Get audio source URL for streaming"""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts_audio) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                if 'url' in info:
                    return info['url']
                elif 'entries' in info and info['entries']:
                    return info['entries'][0]['url']
                
                raise Exception("Could not extract audio URL")
                
        except Exception as e:
            logger.error(f"Error getting audio source: {e}")
            raise
    
    async def _play_discord(self, ctx, audio_source: str, chat_id: int):
        """Play audio in Discord voice channel"""
        try:
            voice_client = ctx.voice_client
            if not voice_client:
                if hasattr(ctx.author, 'voice') and ctx.author.voice:
                    voice_client = await ctx.author.voice.channel.connect()
                else:
                    raise Exception("User not in voice channel")
            
            # FFMPEG options for better audio quality
            ffmpeg_options = {
                'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                'options': '-vn'
            }
            
            # Apply speed if set
            speed = self.playback_speeds.get(chat_id, 1.0)
            if speed != 1.0:
                ffmpeg_options['options'] += f' -filter:a "atempo={speed}"'
            
            def after_playing(error):
                if error:
                    logger.error(f'Discord player error: {error}')
                
                # Handle loop mode
                loop_mode = self.loop_modes.get(chat_id, 0)
                if loop_mode == 1:  # Loop current song
                    asyncio.create_task(self._play_next(chat_id, ctx, 'discord'))
                elif loop_mode > 1:  # Loop N times or queue
                    if loop_mode == 2:  # Loop queue
                        if self.current_songs.get(chat_id):
                            self.queues[chat_id].append(self.current_songs[chat_id])
                    else:  # Loop N times
                        self.loop_modes[chat_id] -= 1
                        if self.current_songs.get(chat_id):
                            self.queues[chat_id].insert(0, self.current_songs[chat_id])
                    
                    asyncio.create_task(self._play_next(chat_id, ctx, 'discord'))
                else:
                    # Play next song
                    asyncio.create_task(self._play_next(chat_id, ctx, 'discord'))
            
            # Create audio source
            audio = FFmpegPCMAudio(audio_source, **ffmpeg_options)
            
            # Play audio
            voice_client.play(audio, after=after_playing)
            self.voice_clients[chat_id] = voice_client
            
        except Exception as e:
            logger.error(f"Error playing Discord audio: {e}")
            raise
    
    async def _play_telegram(self, ctx, song: Dict, chat_id: int):
        """Play audio/video in Telegram voice chat"""
        try:
            # Note: This requires pytgcalls library for Telegram voice chats
            # Implementation depends on your Telegram voice chat setup
            from pytgcalls import PyTgCalls
            from pytgcalls.types import AudioPiped, VideoPiped
            
            # Get the audio/video stream
            if song['video']:
                # Video call
                stream = VideoPiped(song['url'])
            else:
                # Audio call
                stream = AudioPiped(song['url'])
            
            # Apply speed if set
            speed = self.playback_speeds.get(chat_id, 1.0)
            # Note: Speed adjustment implementation depends on your setup
            
            # Join and play
            # Implementation specific to your Telegram voice chat setup
            logger.info(f"Playing {song['title']} in Telegram chat {chat_id}")
            
        except ImportError:
            logger.error("pytgcalls not installed. Telegram voice chat not available.")
            raise Exception("Telegram voice chat not supported. Install pytgcalls.")
        except Exception as e:
            logger.error(f"Error playing Telegram audio: {e}")
            raise
    
    async def download_song(self, query: str, platform: str) -> Dict:
        """Download a song and return file info"""
        try:
            # Search for the song
            song_info = await self._search_song(query)
            
            if not song_info:
                raise Exception("Song not found!")
            
            # Create download options
            download_opts = self.ydl_opts_audio.copy()
            download_opts['outtmpl'] = f'{self.config.DOWNLOAD_DIR}/%(title)s-%(id)s.%(ext)s'
            
            # Download the song
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, song_info['url'], download=True)
                
                # Get file path
                file_path = ydl.prepare_filename(info)
                file_path = file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3')
                
                # Get file size
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                return {
                    'id': info['id'],
                    'title': info['title'],
                    'duration': self._format_duration(info.get('duration', 0)),
                    'file_path': file_path,
                    'size': self._format_file_size(file_size),
                    'thumbnail': info.get('thumbnail', ''),
                    'uploader': info.get('uploader', 'Unknown')
                }
                
        except Exception as e:
            logger.error(f"Error downloading song: {e}")
            raise
    
    async def get_queue(self, ctx, platform: str) -> Dict:
        """Get current queue information"""
        chat_id = self._get_chat_id(ctx, platform)
        
        return {
            'current': self.current_songs.get(chat_id),
            'queue': self.queues.get(chat_id, []),
            'loop_mode': self.loop_modes.get(chat_id, 0),
            'speed': self.playback_speeds.get(chat_id, 1.0)
        }
    
    async def shuffle_queue(self, ctx, platform: str) -> bool:
        """Shuffle the current queue"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if chat_id in self.queues and self.queues[chat_id]:
            random.shuffle(self.queues[chat_id])
            return True
        
        return False
    
    async def skip_song(self, ctx, platform: str) -> str:
        """Skip the current song"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if platform == 'discord':
            voice_client = self.voice_clients.get(chat_id)
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                return "Skipped current song!"
        else:
            # Telegram skip implementation
            # This depends on your pytgcalls setup
            pass
        
        # If nothing is playing, play next from queue
        if self.queues.get(chat_id):
            await self._play_next(chat_id, ctx, platform)
            return "Playing next song from queue!"
        
        return "Nothing to skip!"
    
    async def stop_playback(self, ctx, platform: str):
        """Stop playback and clear queue"""
        chat_id = self._get_chat_id(ctx, platform)
        
        # Clear queue and current song
        self.queues.pop(chat_id, None)
        self.current_songs.pop(chat_id, None)
        self.loop_modes.pop(chat_id, None)
        
        if platform == 'discord':
            voice_client = self.voice_clients.get(chat_id)
            if voice_client:
                if voice_client.is_playing() or voice_client.is_paused():
                    voice_client.stop()
                await voice_client.disconnect()
                self.voice_clients.pop(chat_id, None)
        else:
            # Telegram stop implementation
            pass
    
    async def pause_playback(self, ctx, platform: str) -> bool:
        """Pause current playback"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if platform == 'discord':
            voice_client = self.voice_clients.get(chat_id)
            if voice_client and voice_client.is_playing():
                voice_client.pause()
                return True
        else:
            # Telegram pause implementation
            pass
        
        return False
    
    async def resume_playback(self, ctx, platform: str) -> bool:
        """Resume paused playback"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if platform == 'discord':
            voice_client = self.voice_clients.get(chat_id)
            if voice_client and voice_client.is_paused():
                voice_client.resume()
                return True
        else:
            # Telegram resume implementation
            pass
        
        return False
    
    async def set_loop_mode(self, ctx, mode: Optional[int], platform: str) -> str:
        """Set loop mode for the current chat"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if mode is None:
            # Toggle between off and queue loop
            current_mode = self.loop_modes.get(chat_id, 0)
            mode = 2 if current_mode == 0 else 0
        
        if mode < 0 or mode > 10:
            return "❌ Loop mode must be between 0-10!"
        
        self.loop_modes[chat_id] = mode
        
        mode_names = {
            0: "disabled",
            1: "current song",
            2: "queue"
        }
        
        if mode in mode_names:
            return f"🔄 Loop mode set to: {mode_names[mode]}"
        else:
            return f"🔄 Loop mode set to: repeat {mode} times"
    
    async def set_playback_speed(self, ctx, speed: float, platform: str) -> bool:
        """Set playback speed"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if speed < 0.5 or speed > 2.0:
            return False
        
        self.playback_speeds[chat_id] = speed
        
        # If something is currently playing, restart with new speed
        if self.current_songs.get(chat_id):
            current_song = self.current_songs[chat_id]
            self.queues[chat_id].insert(0, current_song)
            
            if platform == 'discord':
                voice_client = self.voice_clients.get(chat_id)
                if voice_client and voice_client.is_playing():
                    voice_client.stop()
        
        return True
    
    async def seek_position(self, ctx, position: int, platform: str) -> bool:
        """Seek to a specific position in the current song"""
        chat_id = self._get_chat_id(ctx, platform)
        
        if not self.current_songs.get(chat_id):
            return False
        
        # Note: Seeking requires more complex implementation
        # This is a placeholder - actual implementation depends on your audio framework
        logger.info(f"Seeking to position {position} for chat {chat_id}")
        
        return True
    
    # Channel-specific methods for Telegram
    async def channel_play(self, ctx, query: str, video: bool = False) -> str:
        """Play in connected channel"""
        chat_id = self._get_chat_id(ctx, 'telegram')
        
        if chat_id not in self.channel_connections:
            return "❌ No channel connected! Use /channelplay first."
        
        channel_id = self.channel_connections[chat_id]
        
        try:
            # Search and play in channel
            song_info = await self._search_song(query)
            
            if not song_info:
                return "❌ Song not found!"
            
            # Implementation depends on pytgcalls setup for channels
            logger.info(f"Playing {song_info['title']} in channel {channel_id}")
            
            return f"🎵 Playing {song_info['title']} in connected channel!"
            
        except Exception as e:
            logger.error(f"Error in channel play: {e}")
            return f"❌ Error playing in channel: {str(e)}"
    
    async def set_channel_speed(self, ctx, speed: float) -> bool:
        """Set playback speed for channel"""
        chat_id = self._get_chat_id(ctx, 'telegram')
        
        if chat_id not in self.channel_connections:
            return False
        
        # Implementation specific to channel playback
        return True
    
    async def connect_channel(self, ctx) -> str:
        """Connect a channel to the current group"""
        try:
            # This requires admin permissions and specific setup
            # Implementation depends on your Telegram bot setup
            
            chat_id = self._get_chat_id(ctx, 'telegram')
            
            # For now, return instruction message
            return (
                "📱 **Channel Connection Guide:**\n\n"
                "1. Add the bot to your channel as admin\n"
                "2. Add the bot to your group as admin\n"
                "3. Use this command in the group\n"
                "4. Bot will connect and start streaming\n\n"
                "**Note:** This feature requires additional setup with pytgcalls."
            )
            
        except Exception as e:
            logger.error(f"Error connecting channel: {e}")
            return f"❌ Error connecting channel: {str(e)}"
    
    # Utility methods
    def _get_chat_id(self, ctx, platform: str) -> int:
        """Get chat ID based on platform"""
        if platform == 'discord':
            return ctx.guild.id if ctx.guild else ctx.author.id
        else:
            return ctx.effective_chat.id
    
    def _get_user_id(self, ctx, platform: str) -> int:
        """Get user ID based on platform"""
        if platform == 'discord':
            return ctx.author.id
        else:
            return ctx.effective_user.id
    
    def _is_url(self, text: str) -> bool:
        """Check if text is a URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+), re.IGNORECASE)
        return url_pattern.match(text) is not None
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS or HH:MM:SS"""
        if not seconds:
            return "00:00"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    async def cleanup_downloads(self):
        """Clean up old downloaded files"""
        try:
            download_path = self.config.DOWNLOAD_DIR
            current_time = time.time()
            
            for filename in os.listdir(download_path):
                file_path = os.path.join(download_path, filename)
                
                # Delete files older than 1 hour
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > 3600:  # 1 hour
                        os.remove(file_path)
                        logger.info(f"Cleaned up old download: {filename}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up downloads: {e}")
