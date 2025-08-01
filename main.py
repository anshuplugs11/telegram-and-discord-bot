import asyncio
import logging
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import discord
from discord.ext import commands
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from music_handler import MusicHandler
from database import Database
from utils import Utils
from config import Config

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MusicBot:
    def __init__(self):
        self.config = Config()
        self.db = Database()
        self.utils = Utils()
        self.music_handler = MusicHandler()
        
        # Discord Bot Setup
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        self.discord_bot = commands.Bot(command_prefix='/', intents=intents)
        
        # Telegram Bot Setup
        self.telegram_app = Application.builder().token(self.config.TELEGRAM_TOKEN).build()
        
        # Bot Statistics
        self.start_time = time.time()
        self.stats = {
            'commands_executed': 0,
            'songs_played': 0,
            'users_served': set(),
            'chats_served': set()
        }
        
        # Setup handlers
        self.setup_discord_commands()
        self.setup_telegram_commands()
    
    def setup_discord_commands(self):
        @self.discord_bot.event
        async def on_ready():
            logger.info(f'Discord bot logged in as {self.discord_bot.user}')
            await self.discord_bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.listening, name="music | /help")
            )
        
        @self.discord_bot.command(name='start')
        async def start_discord(ctx):
            await self.start_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='help')
        async def help_discord(ctx):
            await self.help_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='play')
        async def play_discord(ctx, *, query):
            await self.play_command(ctx, query, platform='discord')
        
        @self.discord_bot.command(name='vplay')
        async def vplay_discord(ctx, *, query):
            await self.vplay_command(ctx, query, platform='discord')
        
        @self.discord_bot.command(name='song')
        async def song_discord(ctx, *, query):
            await self.song_command(ctx, query, platform='discord')
        
        @self.discord_bot.command(name='queue')
        async def queue_discord(ctx):
            await self.queue_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='shuffle')
        async def shuffle_discord(ctx):
            await self.shuffle_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='skip')
        async def skip_discord(ctx):
            await self.skip_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='stop')
        async def stop_discord(ctx):
            await self.stop_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='pause')
        async def pause_discord(ctx):
            await self.pause_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='resume')
        async def resume_discord(ctx):
            await self.resume_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='loop')
        async def loop_discord(ctx, mode: Optional[int] = None):
            await self.loop_command(ctx, mode, platform='discord')
        
        @self.discord_bot.command(name='speed')
        async def speed_discord(ctx, speed: float):
            await self.speed_command(ctx, speed, platform='discord')
        
        @self.discord_bot.command(name='seek')
        async def seek_discord(ctx, position: int):
            await self.seek_command(ctx, position, platform='discord')
        
        @self.discord_bot.command(name='ping')
        async def ping_discord(ctx):
            await self.ping_command(ctx, platform='discord')
        
        # Admin Commands
        @self.discord_bot.command(name='stats')
        async def stats_discord(ctx):
            await self.stats_command(ctx, platform='discord')
        
        @self.discord_bot.command(name='broadcast')
        async def broadcast_discord(ctx, *, message):
            await self.broadcast_command(ctx, message, platform='discord')
        
        @self.discord_bot.command(name='gban')
        async def gban_discord(ctx, user_id: int):
            await self.gban_command(ctx, user_id, platform='discord')
        
        @self.discord_bot.command(name='ungban')
        async def ungban_discord(ctx, user_id: int):
            await self.ungban_command(ctx, user_id, platform='discord')
    
    def setup_telegram_commands(self):
        # Basic Commands
        self.telegram_app.add_handler(CommandHandler("start", self.start_telegram))
        self.telegram_app.add_handler(CommandHandler("help", self.help_telegram))
        self.telegram_app.add_handler(CommandHandler("play", self.play_telegram))
        self.telegram_app.add_handler(CommandHandler("vplay", self.vplay_telegram))
        self.telegram_app.add_handler(CommandHandler("song", self.song_telegram))
        self.telegram_app.add_handler(CommandHandler("queue", self.queue_telegram))
        self.telegram_app.add_handler(CommandHandler("shuffle", self.shuffle_telegram))
        self.telegram_app.add_handler(CommandHandler("skip", self.skip_telegram))
        self.telegram_app.add_handler(CommandHandler("stop", self.stop_telegram))
        self.telegram_app.add_handler(CommandHandler("pause", self.pause_telegram))
        self.telegram_app.add_handler(CommandHandler("resume", self.resume_telegram))
        self.telegram_app.add_handler(CommandHandler("loop", self.loop_telegram))
        self.telegram_app.add_handler(CommandHandler("speed", self.speed_telegram))
        self.telegram_app.add_handler(CommandHandler("seek", self.seek_telegram))
        self.telegram_app.add_handler(CommandHandler("ping", self.ping_telegram))
        
        # Channel Commands
        self.telegram_app.add_handler(CommandHandler("cplay", self.cplay_telegram))
        self.telegram_app.add_handler(CommandHandler("cvplay", self.cvplay_telegram))
        self.telegram_app.add_handler(CommandHandler("cspeed", self.cspeed_telegram))
        self.telegram_app.add_handler(CommandHandler("channelplay", self.channelplay_telegram))
        
        # Admin Commands
        self.telegram_app.add_handler(CommandHandler("stats", self.stats_telegram))
        self.telegram_app.add_handler(CommandHandler("broadcast", self.broadcast_telegram))
        self.telegram_app.add_handler(CommandHandler("gban", self.gban_telegram))
        self.telegram_app.add_handler(CommandHandler("ungban", self.ungban_telegram))
        self.telegram_app.add_handler(CommandHandler("auth", self.auth_telegram))
        self.telegram_app.add_handler(CommandHandler("unauth", self.unauth_telegram))
        self.telegram_app.add_handler(CommandHandler("maintenance", self.maintenance_telegram))
        self.telegram_app.add_handler(CommandHandler("logs", self.logs_telegram))
        
        # Callback Query Handler
        self.telegram_app.add_handler(CallbackQueryHandler(self.button_callback))
    
    # Telegram Command Handlers
    async def start_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.start_command(update, platform='telegram')
    
    async def help_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.help_command(update, platform='telegram')
    
    async def play_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = ' '.join(context.args)
        await self.play_command(update, query, platform='telegram')
    
    async def vplay_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = ' '.join(context.args)
        await self.vplay_command(update, query, platform='telegram')
    
    async def song_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = ' '.join(context.args)
        await self.song_command(update, query, platform='telegram')
    
    async def queue_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.queue_command(update, platform='telegram')
    
    async def shuffle_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.shuffle_command(update, platform='telegram')
    
    async def skip_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.skip_command(update, platform='telegram')
    
    async def stop_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.stop_command(update, platform='telegram')
    
    async def pause_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.pause_command(update, platform='telegram')
    
    async def resume_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.resume_command(update, platform='telegram')
    
    async def loop_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mode = int(context.args[0]) if context.args else None
        await self.loop_command(update, mode, platform='telegram')
    
    async def speed_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        speed = float(context.args[0]) if context.args else 1.0
        await self.speed_command(update, speed, platform='telegram')
    
    async def seek_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        position = int(context.args[0]) if context.args else 0
        await self.seek_command(update, position, platform='telegram')
    
    async def ping_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.ping_command(update, platform='telegram')
    
    async def cplay_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = ' '.join(context.args)
        await self.cplay_command(update, query, platform='telegram')
    
    async def cvplay_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = ' '.join(context.args)
        await self.cvplay_command(update, query, platform='telegram')
    
    async def cspeed_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        speed = float(context.args[0]) if context.args else 1.0
        await self.cspeed_command(update, speed, platform='telegram')
    
    async def channelplay_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.channelplay_command(update, platform='telegram')
    
    async def stats_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.stats_command(update, platform='telegram')
    
    async def broadcast_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = ' '.join(context.args)
        await self.broadcast_command(update, message, platform='telegram')
    
    async def gban_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = int(context.args[0]) if context.args else None
        await self.gban_command(update, user_id, platform='telegram')
    
    async def ungban_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = int(context.args[0]) if context.args else None
        await self.ungban_command(update, user_id, platform='telegram')
    
    async def auth_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = int(context.args[0]) if context.args else None
        await self.auth_command(update, user_id, platform='telegram')
    
    async def unauth_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = int(context.args[0]) if context.args else None
        await self.unauth_command(update, user_id, platform='telegram')
    
    async def maintenance_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        mode = context.args[0] if context.args else None
        await self.maintenance_command(update, mode, platform='telegram')
    
    async def logs_telegram(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.logs_command(update, platform='telegram')
    
    # Universal Command Implementations
    async def start_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        
        if platform == 'telegram':
            keyboard = [
                [
                    InlineKeyboardButton("🎵 Music Commands", callback_data="music_help"),
                    InlineKeyboardButton("⚙️ Admin Commands", callback_data="admin_help")
                ],
                [
                    InlineKeyboardButton("📊 Bot Stats", callback_data="bot_stats"),
                    InlineKeyboardButton("📞 Support", url="https://t.me/your_support_channel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = """
🎵 **Welcome to the Ultimate Music Bot!** 🎵

I can play music in both Discord and Telegram voice calls!

**Quick Start:**
• `/play <song name>` - Play audio
• `/vplay <song name>` - Play with video
• `/song <song name>` - Download MP3/MP4
• `/help` - See all commands

**Features:**
✅ Multi-platform support (Discord + Telegram)
✅ High-quality audio streaming
✅ YouTube downloads
✅ Queue management
✅ Speed control
✅ Loop modes
✅ Channel streaming
✅ Admin controls

Let's get the party started! 🎉
            """
            
            await ctx.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            embed = discord.Embed(
                title="🎵 Welcome to Ultimate Music Bot!",
                description="I can play music in voice channels with advanced features!",
                color=0x00ff00
            )
            embed.add_field(name="🎵 Basic Commands", value="`/play`, `/vplay`, `/song`, `/queue`", inline=True)
            embed.add_field(name="⚙️ Controls", value="`/pause`, `/resume`, `/skip`, `/stop`", inline=True)
            embed.add_field(name="🔄 Advanced", value="`/loop`, `/shuffle`, `/speed`, `/seek`", inline=True)
            embed.set_footer(text="Use /help for detailed command list")
            
            await ctx.send(embed=embed)
    
    async def help_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        
        if platform == 'telegram':
            keyboard = [
                [
                    InlineKeyboardButton("🎵 Music", callback_data="music_help"),
                    InlineKeyboardButton("📺 Video", callback_data="video_help")
                ],
                [
                    InlineKeyboardButton("⚙️ Admin", callback_data="admin_help"),
                    InlineKeyboardButton("📊 Stats", callback_data="stats_help")
                ],
                [
                    InlineKeyboardButton("🔧 Advanced", callback_data="advanced_help"),
                    InlineKeyboardButton("📱 Channel", callback_data="channel_help")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            help_text = """
🎵 **Music Bot Help Menu** 🎵

Select a category below to see detailed commands:

**Quick Commands:**
• `/play <song>` - Play music
• `/vplay <song>` - Play with video
• `/song <song>` - Download song
• `/queue` - Show queue
• `/skip` - Skip current song
• `/stop` - Stop playback

Use the buttons below for detailed help!
            """
            
            await ctx.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            embed = discord.Embed(title="🎵 Music Bot Commands", color=0x00ff00)
            
            embed.add_field(
                name="🎵 Music Commands",
                value="`/play <song>` - Play audio\n`/vplay <song>` - Play video\n`/song <song>` - Download\n`/queue` - Show queue\n`/shuffle` - Shuffle queue",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Playback Controls",
                value="`/pause` - Pause\n`/resume` - Resume\n`/skip` - Skip\n`/stop` - Stop\n`/loop [1-10]` - Loop mode",
                inline=False
            )
            
            embed.add_field(
                name="🔧 Advanced",
                value="`/speed <0.5-2.0>` - Playback speed\n`/seek <seconds>` - Seek position\n`/seekback <seconds>` - Seek backward",
                inline=False
            )
            
            if await self.is_admin(ctx.author.id):
                embed.add_field(
                    name="👑 Admin Commands",
                    value="`/stats` - Bot statistics\n`/gban <user>` - Global ban\n`/broadcast <msg>` - Broadcast\n`/maintenance` - Toggle maintenance",
                    inline=False
                )
            
            await ctx.send(embed=embed)
    
    async def play_command(self, ctx, query, platform='discord'):
        if not query:
            msg = "Please provide a song name or URL!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        self.stats['commands_executed'] += 1
        self.stats['songs_played'] += 1
        
        # Check if user is in voice channel
        if platform == 'discord':
            if not ctx.author.voice:
                await ctx.send("You need to be in a voice channel!")
                return
            
            voice_channel = ctx.author.voice.channel
            
            if ctx.voice_client is None:
                await voice_channel.connect()
            elif ctx.voice_client.channel != voice_channel:
                await ctx.voice_client.move_to(voice_channel)
        
        # Process the song
        try:
            result = await self.music_handler.search_and_play(query, ctx, platform, video=False)
            
            if platform == 'telegram':
                keyboard = [
                    [
                        InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
                        InlineKeyboardButton("⏭️ Skip", callback_data="skip"),
                        InlineKeyboardButton("⏹️ Stop", callback_data="stop")
                    ],
                    [
                        InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
                        InlineKeyboardButton("📜 Queue", callback_data="queue"),
                        InlineKeyboardButton("🔄 Loop", callback_data="loop")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await ctx.message.reply_text(
                    f"🎵 **Now Playing:** {result['title']}\n"
                    f"⏱️ **Duration:** {result['duration']}\n"
                    f"👀 **Views:** {result['views']}\n"
                    f"📤 **Requested by:** {ctx.effective_user.mention}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                embed = discord.Embed(
                    title="🎵 Now Playing",
                    description=f"**{result['title']}**",
                    color=0x00ff00
                )
                embed.add_field(name="Duration", value=result['duration'], inline=True)
                embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)
                if result.get('thumbnail'):
                    embed.set_thumbnail(url=result['thumbnail'])
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            error_msg = f"Error playing song: {str(e)}"
            if platform == 'telegram':
                await ctx.message.reply_text(error_msg)
            else:
                await ctx.send(error_msg)
    
    async def vplay_command(self, ctx, query, platform='discord'):
        if not query:
            msg = "Please provide a song name or URL for video play!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        self.stats['commands_executed'] += 1
        self.stats['songs_played'] += 1
        
        try:
            result = await self.music_handler.search_and_play(query, ctx, platform, video=True)
            
            if platform == 'telegram':
                keyboard = [
                    [
                        InlineKeyboardButton("⏸️ Pause", callback_data="pause"),
                        InlineKeyboardButton("⏭️ Skip", callback_data="skip"),
                        InlineKeyboardButton("⏹️ Stop", callback_data="stop")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await ctx.message.reply_text(
                    f"📺 **Now Playing Video:** {result['title']}\n"
                    f"⏱️ **Duration:** {result['duration']}\n"
                    f"📤 **Requested by:** {ctx.effective_user.mention}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                embed = discord.Embed(
                    title="📺 Now Playing Video",
                    description=f"**{result['title']}**",
                    color=0xff0000
                )
                embed.add_field(name="Duration", value=result['duration'], inline=True)
                embed.add_field(name="Requested by", value=ctx.author.mention, inline=True)
                
                await ctx.send(embed=embed)
                
        except Exception as e:
            error_msg = f"Error playing video: {str(e)}"
            if platform == 'telegram':
                await ctx.message.reply_text(error_msg)
            else:
                await ctx.send(error_msg)
    
    async def song_command(self, ctx, query, platform='discord'):
        if not query:
            msg = "Please provide a song name or URL to download!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        self.stats['commands_executed'] += 1
        
        try:
            result = await self.music_handler.download_song(query, platform)
            
            if platform == 'telegram':
                keyboard = [
                    [
                        InlineKeyboardButton("🎵 MP3", callback_data=f"download_mp3_{result['id']}"),
                        InlineKeyboardButton("📹 MP4", callback_data=f"download_mp4_{result['id']}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await ctx.message.reply_text(
                    f"🎵 **Song Found:** {result['title']}\n"
                    f"⏱️ **Duration:** {result['duration']}\n"
                    f"📊 **Quality:** High\n\n"
                    f"Choose format to download:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                embed = discord.Embed(
                    title="🎵 Song Download",
                    description=f"**{result['title']}**",
                    color=0x00ff00
                )
                embed.add_field(name="Duration", value=result['duration'], inline=True)
                embed.add_field(name="Size", value=result.get('size', 'Unknown'), inline=True)
                
                # Send file if available
                if result.get('file_path'):
                    file = discord.File(result['file_path'])
                    await ctx.send(embed=embed, file=file)
                else:
                    await ctx.send(embed=embed)
                    
        except Exception as e:
            error_msg = f"Error downloading song: {str(e)}"
            if platform == 'telegram':
                await ctx.message.reply_text(error_msg)
            else:
                await ctx.send(error_msg)
    
    async def queue_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        queue_info = await self.music_handler.get_queue(ctx, platform)
        
        if platform == 'telegram':
            if not queue_info['queue']:
                await ctx.message.reply_text("📜 Queue is empty!")
                return
            
            queue_text = f"📜 **Current Queue ({len(queue_info['queue'])} songs):**\n\n"
            
            if queue_info['current']:
                queue_text += f"🎵 **Now Playing:** {queue_info['current']['title']}\n\n"
            
            for i, song in enumerate(queue_info['queue'][:10], 1):
                queue_text += f"{i}. {song['title']} - {song['duration']}\n"
            
            if len(queue_info['queue']) > 10:
                queue_text += f"\n... and {len(queue_info['queue']) - 10} more songs"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
                    InlineKeyboardButton("🗑️ Clear", callback_data="clear_queue")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await ctx.message.reply_text(queue_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            if not queue_info['queue']:
                await ctx.send("📜 Queue is empty!")
                return
            
            embed = discord.Embed(title="📜 Music Queue", color=0x00ff00)
            
            if queue_info['current']:
                embed.add_field(
                    name="🎵 Now Playing",
                    value=f"{queue_info['current']['title']} - {queue_info['current']['duration']}",
                    inline=False
                )
            
            queue_list = ""
            for i, song in enumerate(queue_info['queue'][:10], 1):
                queue_list += f"{i}. {song['title']} - {song['duration']}\n"
            
            if queue_list:
                embed.add_field(name="📋 Up Next", value=queue_list, inline=False)
            
            if len(queue_info['queue']) > 10:
                embed.set_footer(text=f"... and {len(queue_info['queue']) - 10} more songs")
            
            await ctx.send(embed=embed)
    
    async def ping_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        start_time = time.time()
        
        if platform == 'telegram':
            message = await ctx.message.reply_text("🏓 Pinging...")
            end_time = time.time()
            ping = round((end_time - start_time) * 1000, 2)
            
            await message.edit_text(
                f"🏓 **Pong!**\n"
                f"📶 **Latency:** {ping}ms\n"
                f"⏰ **Uptime:** {self.get_uptime()}\n"
                f"🤖 **Bot Status:** Online ✅",
                parse_mode='Markdown'
            )
        else:
            msg = await ctx.send("🏓 Pinging...")
            end_time = time.time()
            ping = round((end_time - start_time) * 1000, 2)
            
            embed = discord.Embed(title="🏓 Pong!", color=0x00ff00)
            embed.add_field(name="📶 Bot Latency", value=f"{ping}ms", inline=True)
            embed.add_field(name="📡 Discord Latency", value=f"{round(self.discord_bot.latency * 1000, 2)}ms", inline=True)
            embed.add_field(name="⏰ Uptime", value=self.get_uptime(), inline=True)
            
            await msg.edit(content="", embed=embed)
    
    async def stats_command(self, ctx, platform='discord'):
        if not await self.is_admin(ctx.author.id if platform == 'discord' else ctx.effective_user.id):
            return
        
        self.stats['commands_executed'] += 1
        uptime = self.get_uptime()
        
        stats_text = f"""
📊 **Bot Statistics:**

⏰ **Uptime:** {uptime}
🎵 **Songs Played:** {self.stats['songs_played']}
⚡ **Commands Executed:** {self.stats['commands_executed']}
👥 **Users Served:** {len(self.stats['users_served'])}
💬 **Chats Served:** {len(self.stats['chats_served'])}
🖥️ **Memory Usage:** {self.utils.get_memory_usage()} MB
💾 **CPU Usage:** {self.utils.get_cpu_usage()}%
        """
        
        if platform == 'telegram':
            await ctx.message.reply_text(stats_text, parse_mode='Markdown')
        else:
            embed = discord.Embed(title="📊 Bot Statistics", description=stats_text, color=0x00ff00)
            await ctx.send(embed=embed)
    
    # Additional command implementations...
    async def shuffle_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.shuffle_queue(ctx, platform)
        
        msg = "🔀 Queue shuffled!" if result else "❌ No songs in queue to shuffle!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def skip_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.skip_song(ctx, platform)
        
        if platform == 'telegram':
            await ctx.message.reply_text(f"⏭️ {result}")
        else:
            await ctx.send(f"⏭️ {result}")
    
    async def stop_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        await self.music_handler.stop_playback(ctx, platform)
        
        msg = "⏹️ Playback stopped and queue cleared!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def pause_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.pause_playback(ctx, platform)
        
        msg = "⏸️ Playback paused!" if result else "❌ Nothing is playing!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def resume_command(self, ctx, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.resume_playback(ctx, platform)
        
        msg = "▶️ Playback resumed!" if result else "❌ Nothing is paused!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def loop_command(self, ctx, mode, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.set_loop_mode(ctx, mode, platform)
        
        if platform == 'telegram':
            await ctx.message.reply_text(result)
        else:
            await ctx.send(result)
    
    async def speed_command(self, ctx, speed, platform='discord'):
        self.stats['commands_executed'] += 1
        
        if speed < 0.5 or speed > 2.0:
            msg = "❌ Speed must be between 0.5 and 2.0!"
        else:
            result = await self.music_handler.set_playback_speed(ctx, speed, platform)
            msg = f"🏃 Playback speed set to {speed}x" if result else "❌ Nothing is playing!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def seek_command(self, ctx, position, platform='discord'):
        self.stats['commands_executed'] += 1
        result = await self.music_handler.seek_position(ctx, position, platform)
        
        msg = f"⏩ Seeked to {position} seconds" if result else "❌ Cannot seek!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    # Channel commands for Telegram
    async def cplay_command(self, ctx, query, platform='telegram'):
        if not await self.is_admin(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only admins can use channel commands!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.music_handler.channel_play(ctx, query, video=False)
        
        await ctx.message.reply_text(f"🎵 Playing in channel: {result}")
    
    async def cvplay_command(self, ctx, query, platform='telegram'):
        if not await self.is_admin(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only admins can use channel commands!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.music_handler.channel_play(ctx, query, video=True)
        
        await ctx.message.reply_text(f"📺 Playing video in channel: {result}")
    
    async def cspeed_command(self, ctx, speed, platform='telegram'):
        if not await self.is_admin(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only admins can use channel commands!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.music_handler.set_channel_speed(ctx, speed)
        
        await ctx.message.reply_text(f"🏃 Channel playback speed set to {speed}x")
    
    async def channelplay_command(self, ctx, platform='telegram'):
        if not await self.is_admin(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only admins can use this command!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.music_handler.connect_channel(ctx)
        
        await ctx.message.reply_text(result)
    
    # Admin commands
    async def broadcast_command(self, ctx, message, platform='discord'):
        user_id = ctx.author.id if platform == 'discord' else ctx.effective_user.id
        
        if not await self.is_sudoer(user_id):
            return
        
        self.stats['commands_executed'] += 1
        
        # Parse broadcast flags
        flags = {
            'pin': '-pin' in message,
            'pinloud': '-pinloud' in message,
            'user': '-user' in message,
            'assistant': '-assistant' in message,
            'nobot': '-nobot' in message
        }
        
        # Clean message
        for flag in ['-pin', '-pinloud', '-user', '-assistant', '-nobot']:
            message = message.replace(flag, '')
        message = message.strip()
        
        if not message:
            msg = "❌ Please provide a message to broadcast!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        # Execute broadcast
        result = await self.utils.broadcast_message(message, flags, platform)
        
        success_msg = f"📢 Broadcast sent to {result['success']} chats! Failed: {result['failed']}"
        
        if platform == 'telegram':
            await ctx.message.reply_text(success_msg)
        else:
            await ctx.send(success_msg)
    
    async def gban_command(self, ctx, user_id, platform='discord'):
        if not await self.is_sudoer(ctx.author.id if platform == 'discord' else ctx.effective_user.id):
            return
        
        if not user_id:
            msg = "❌ Please provide a user ID to ban!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        self.stats['commands_executed'] += 1
        result = await self.db.global_ban_user(user_id)
        
        msg = f"🔨 User {user_id} has been globally banned!" if result else "❌ Failed to ban user!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def ungban_command(self, ctx, user_id, platform='discord'):
        if not await self.is_sudoer(ctx.author.id if platform == 'discord' else ctx.effective_user.id):
            return
        
        if not user_id:
            msg = "❌ Please provide a user ID to unban!"
            if platform == 'telegram':
                await ctx.message.reply_text(msg)
            else:
                await ctx.send(msg)
            return
        
        self.stats['commands_executed'] += 1
        result = await self.db.global_unban_user(user_id)
        
        msg = f"✅ User {user_id} has been unbanned!" if result else "❌ Failed to unban user!"
        
        if platform == 'telegram':
            await ctx.message.reply_text(msg)
        else:
            await ctx.send(msg)
    
    async def auth_command(self, ctx, user_id, platform='telegram'):
        if not await self.is_sudoer(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only sudoers can authorize users!")
            return
        
        if not user_id:
            await ctx.message.reply_text("❌ Please provide a user ID to authorize!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.db.authorize_user(user_id)
        
        msg = f"✅ User {user_id} has been authorized!" if result else "❌ Failed to authorize user!"
        await ctx.message.reply_text(msg)
    
    async def unauth_command(self, ctx, user_id, platform='telegram'):
        if not await self.is_sudoer(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only sudoers can unauthorize users!")
            return
        
        if not user_id:
            await ctx.message.reply_text("❌ Please provide a user ID to unauthorize!")
            return
        
        self.stats['commands_executed'] += 1
        result = await self.db.unauthorize_user(user_id)
        
        msg = f"❌ User {user_id} has been unauthorized!" if result else "❌ Failed to unauthorize user!"
        await ctx.message.reply_text(msg)
    
    async def maintenance_command(self, ctx, mode, platform='telegram'):
        if not await self.is_sudoer(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only sudoers can toggle maintenance!")
            return
        
        self.stats['commands_executed'] += 1
        
        if mode == 'enable':
            self.config.MAINTENANCE_MODE = True
            msg = "🔧 Maintenance mode enabled!"
        elif mode == 'disable':
            self.config.MAINTENANCE_MODE = False
            msg = "✅ Maintenance mode disabled!"
        else:
            current_status = "Enabled" if self.config.MAINTENANCE_MODE else "Disabled"
            msg = f"🔧 Maintenance mode is currently: {current_status}"
        
        await ctx.message.reply_text(msg)
    
    async def logs_command(self, ctx, platform='telegram'):
        if not await self.is_sudoer(ctx.effective_user.id):
            await ctx.message.reply_text("❌ Only sudoers can access logs!")
            return
        
        self.stats['commands_executed'] += 1
        
        try:
            with open('bot.log', 'r') as f:
                logs = f.read()[-4000:]  # Last 4000 characters
            
            await ctx.message.reply_text(f"📝 **Recent Logs:**\n\n```\n{logs}\n```", parse_mode='Markdown')
        except FileNotFoundError:
            await ctx.message.reply_text("❌ No log file found!")
        except Exception as e:
            await ctx.message.reply_text(f"❌ Error reading logs: {str(e)}")
    
    # Button callback handler for Telegram
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "music_help":
            help_text = """
🎵 **Music Commands:**

**Basic Playback:**
• `/play <song>` - Play audio in voice chat
• `/vplay <song>` - Play video in voice chat
• `/song <song>` - Download MP3/MP4
• `/stop` - Stop playback
• `/pause` - Pause current song
• `/resume` - Resume playback

**Queue Management:**
• `/queue` - Show current queue
• `/skip` - Skip current song
• `/shuffle` - Shuffle queue
• `/loop [1-10]` - Set loop mode

**Controls:**
• `/speed <0.5-2.0>` - Adjust speed
• `/seek <seconds>` - Seek to position
• `/seekback <seconds>` - Seek backward
            """
            await query.edit_message_text(help_text, parse_mode='Markdown')
        
        elif data == "admin_help":
            help_text = """
⚙️ **Admin Commands:**

**User Management:**
• `/auth <user_id>` - Authorize user
• `/unauth <user_id>` - Remove authorization
• `/gban <user_id>` - Global ban user
• `/ungban <user_id>` - Remove global ban

**Bot Management:**
• `/maintenance enable/disable` - Toggle maintenance
• `/broadcast <message>` - Broadcast message
• `/stats` - Show bot statistics
• `/logs` - Get bot logs

**Channel Commands:**
• `/cplay <song>` - Play in linked channel
• `/cvplay <song>` - Play video in channel
• `/channelplay` - Connect channel to group
            """
            await query.edit_message_text(help_text, parse_mode='Markdown')
        
        elif data == "bot_stats":
            stats_text = f"""
📊 **Bot Statistics:**

⏰ **Uptime:** {self.get_uptime()}
🎵 **Songs Played:** {self.stats['songs_played']}
⚡ **Commands Used:** {self.stats['commands_executed']}
👥 **Users Served:** {len(self.stats['users_served'])}
💬 **Chats Active:** {len(self.stats['chats_served'])}
🖥️ **Memory Usage:** {self.utils.get_memory_usage()} MB
💾 **CPU Usage:** {self.utils.get_cpu_usage()}%
            """
            await query.edit_message_text(stats_text, parse_mode='Markdown')
        
        elif data in ["pause", "resume", "skip", "stop", "shuffle", "queue", "loop"]:
            # Handle music control buttons
            ctx_mock = type('MockContext', (), {
                'message': query.message,
                'effective_user': query.from_user
            })()
            
            if data == "pause":
                await self.pause_command(ctx_mock, platform='telegram')
            elif data == "resume":
                await self.resume_command(ctx_mock, platform='telegram')
            elif data == "skip":
                await self.skip_command(ctx_mock, platform='telegram')
            elif data == "stop":
                await self.stop_command(ctx_mock, platform='telegram')
            elif data == "shuffle":
                await self.shuffle_command(ctx_mock, platform='telegram')
            elif data == "queue":
                await self.queue_command(ctx_mock, platform='telegram')
            elif data == "loop":
                await self.loop_command(ctx_mock, None, platform='telegram')
    
    # Utility methods
    async def is_admin(self, user_id):
        return await self.db.is_authorized(user_id) or await self.is_sudoer(user_id)
    
    async def is_sudoer(self, user_id):
        return user_id in self.config.SUDOERS
    
    def get_uptime(self):
        uptime_seconds = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    # Main run method
    async def run(self):
        """Run both Discord and Telegram bots concurrently"""
        logger.info("Starting Music Bot...")
        
        # Start both bots concurrently
        await asyncio.gather(
            self.discord_bot.start(self.config.DISCORD_TOKEN),
            self.telegram_app.run_polling(),
            return_exceptions=True
        )

if __name__ == "__main__":
    bot = MusicBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
