import discord
from discord.ext import commands
import json
import uuid
import time
import datetime
import asyncio
import os
from typing import Optional, Dict, List
import aiofiles
import http.server
import socketserver
import threading

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Configuration
GUILD_ID = 1402622761246916628
ROLE_ID = 1404221578782183556
ADMIN_ROLE_ID = 1404221578782183556  # Role that can manage keys

# Load bot token from environment variable for security
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Fallback methods (for local development only)
if not BOT_TOKEN:
    # Try to load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = os.getenv('BOT_TOKEN')
    except ImportError:
        pass
    
    # If still no token, try alternative methods
    if not BOT_TOKEN:
        # Method 1: Check for a config file
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    BOT_TOKEN = config.get('BOT_TOKEN')
            except:
                pass
        
        # Method 2: Check for a hidden file
        if not BOT_TOKEN and os.path.exists('.bot_config'):
            try:
                with open('.bot_config', 'r') as f:
                    BOT_TOKEN = f.read().strip()
            except:
                pass
        
        # Method 3: Check for encoded token
        if not BOT_TOKEN and os.path.exists('.encoded_token'):
            try:
                from token_encoder import load_encoded_token
                BOT_TOKEN = load_encoded_token()
            except:
                pass

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    print("Please set it as an environment variable, in .env file, or config.json")
    print("For hosting: Set BOT_TOKEN environment variable")
    print("For local: Create .env file with BOT_TOKEN=your_token")
    exit(1)

# Data storage
KEYS_FILE = "keys.json"
BACKUP_FILE = "keys_backup.json"
USAGE_FILE = "key_usage.json"

class KeyManager:
    def __init__(self):
        self.keys = {}
        self.key_usage = {}
        self.load_data()
    
    def load_data(self):
        """Load keys and usage data from files"""
        try:
            if os.path.exists(KEYS_FILE):
                with open(KEYS_FILE, 'r') as f:
                    self.keys = json.load(f)
            
            if os.path.exists(USAGE_FILE):
                with open(USAGE_FILE, 'r') as f:
                    self.key_usage = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.keys = {}
            self.key_usage = {}
    
    def save_data(self):
        """Save keys and usage data to files"""
        try:
            with open(KEYS_FILE, 'w') as f:
                json.dump(self.keys, f, indent=2)
            
            with open(USAGE_FILE, 'w') as f:
                json.dump(self.key_usage, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def generate_key(self, user_id: int, channel_id: Optional[int] = None, duration_days: int = 30) -> str:
        """Generate a new key for a user"""
        key = str(uuid.uuid4())
        activation_time = int(time.time())
        expiration_time = activation_time + (duration_days * 24 * 60 * 60)
        
        self.keys[key] = {
            "user_id": user_id,
            "channel_id": channel_id,
            "activation_time": activation_time,
            "expiration_time": expiration_time,
            "is_active": True,
            "machine_id": None,
            "activated_by": None,
            "created_by": user_id
        }
        
        self.key_usage[key] = {
            "created": activation_time,
            "activated": None,
            "last_used": None,
            "usage_count": 0
        }
        
        self.save_data()
        return key
    
    def revoke_key(self, key: str) -> bool:
        """Revoke a key"""
        if key in self.keys:
            self.keys[key]["is_active"] = False
            self.save_data()
            return True
        return False
    
    def activate_key(self, key: str, machine_id: str, user_id: int) -> Dict:
        """Activate a key for a specific machine"""
        if key not in self.keys:
            return {"success": False, "error": "Invalid key"}
        
        key_data = self.keys[key]
        
        if not key_data["is_active"]:
            return {"success": False, "error": "Key has been revoked"}
        
        if key_data["machine_id"] and key_data["machine_id"] != machine_id:
            return {"success": False, "error": "Key is already activated on another machine"}
        
        if key_data["expiration_time"] < int(time.time()):
            return {"success": False, "error": "Key has expired"}
        
        # Activate the key
        key_data["machine_id"] = machine_id
        key_data["activated_by"] = user_id
        key_data["activated"] = int(time.time())
        
        # Update usage
        if key in self.key_usage:
            self.key_usage[key]["activated"] = int(time.time())
            self.key_usage[key]["last_used"] = int(time.time())
            self.key_usage[key]["usage_count"] += 1
        
        self.save_data()
        
        return {
            "success": True,
            "expiration_time": key_data["expiration_time"],
            "channel_id": key_data["channel_id"]
        }
    
    def get_key_info(self, key: str) -> Optional[Dict]:
        """Get information about a key"""
        if key in self.keys:
            key_data = self.keys[key].copy()
            if key in self.key_usage:
                key_data.update(self.key_usage[key])
            return key_data
        return None
    
    def get_user_keys(self, user_id: int) -> List[Dict]:
        """Get all keys for a specific user"""
        user_keys = []
        for key, data in self.keys.items():
            if data["created_by"] == user_id:
                key_info = data.copy()
                if key in self.key_usage:
                    key_info.update(self.key_usage[key])
                user_keys.append({"key": key, **key_info})
        return user_keys
    
    def backup_keys(self) -> str:
        """Create a backup of all keys"""
        backup_data = {
            "timestamp": int(time.time()),
            "keys": self.keys,
            "usage": self.key_usage
        }
        
        with open(BACKUP_FILE, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        return BACKUP_FILE
    
    def restore_from_backup(self, backup_file: str) -> bool:
        """Restore keys from a backup file"""
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            self.keys = backup_data["keys"]
            self.key_usage = backup_data["usage"]
            self.save_data()
            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False

# Initialize key manager
key_manager = KeyManager()

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'🌐 Connected to {len(bot.guilds)} guild(s)')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Managing Keys | !help"))
    
    print("🤖 Bot is now ready and online!")

@bot.command(name='help')
async def help_command(ctx):
    """Show help information"""
    if not await check_permissions(ctx):
        return
    
    embed = discord.Embed(
        title="🔑 Key Management Bot Help",
        description="Commands for managing Discord keys",
        color=0x2d6cdf
    )
    
    commands_info = {
        "!generate [@user] [channel_id] [days]": "Generate a new key for a user",
        "!revoke [key]": "Revoke a specific key",
        "!keys [@user]": "Show all keys for a user",
        "!info [key]": "Get detailed information about a key",
        "!backup": "Create a backup of all keys",
        "!restore [backup_file]": "Restore keys from backup",
        "!status": "Show bot status and statistics"
    }
    
    for cmd, desc in commands_info.items():
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="Only users with the required role can use these commands")
    await ctx.send(embed=embed)

async def check_permissions(ctx) -> bool:
    """Check if user has permission to use bot commands"""
    if not ctx.guild:
        await ctx.send("❌ This bot can only be used in a server.")
        return False
    
    if ctx.guild.id != GUILD_ID:
        await ctx.send("❌ This bot is not configured for this server.")
        return False
    
    member = ctx.guild.get_member(ctx.author.id)
    if not member:
        await ctx.send("❌ Unable to verify your permissions.")
        return False
    
    if ADMIN_ROLE_ID not in [role.id for role in member.roles]:
        await ctx.send("❌ You don't have permission to use this bot.")
        return False
    
    return True

@bot.command(name='generate')
async def generate_key(ctx, user: discord.Member, channel_id: Optional[int] = None, duration_days: int = 30):
    """Generate a new key for a user"""
    if not await check_permissions(ctx):
        return
    
    if duration_days < 1 or duration_days > 365:
        await ctx.send("❌ Duration must be between 1 and 365 days.")
        return
    
    # Generate the key
    key = key_manager.generate_key(user.id, channel_id, duration_days)
    
    # Create embed
    embed = discord.Embed(
        title="🔑 New Key Generated",
        color=0x00ff00
    )
    
    embed.add_field(name="User", value=f"{user.mention} ({user.display_name})", inline=False)
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
    embed.add_field(name="Expires", value=f"<t:{int(time.time()) + (duration_days * 24 * 60 * 60)}:R>", inline=True)
    
    if channel_id:
        embed.add_field(name="Channel Locked", value=f"<#{channel_id}>", inline=True)
    
    embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
    embed.set_footer(text=f"Generated by {ctx.author.display_name}")
    
    # Send to channel and DM to user
    await ctx.send(embed=embed)
    
    try:
        dm_embed = discord.Embed(
            title="🔑 Your New Key",
            description=f"You have been given a new Discord key by {ctx.author.display_name}",
            color=0x00ff00
        )
        dm_embed.add_field(name="Key", value=f"`{key}`", inline=False)
        dm_embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
        dm_embed.add_field(name="Expires", value=f"<t:{int(time.time()) + (duration_days * 24 * 60 * 60)}:R>", inline=True)
        
        if channel_id:
            dm_embed.add_field(name="Channel Locked", value=f"<#{channel_id}>", inline=True)
        
        await user.send(embed=dm_embed)
    except:
        await ctx.send("⚠️ Could not send DM to user. They may have DMs disabled.")

@bot.command(name='revoke')
async def revoke_key(ctx, key: str):
    """Revoke a specific key"""
    if not await check_permissions(ctx):
        return
    
    if key_manager.revoke_key(key):
        embed = discord.Embed(
            title="🗑️ Key Revoked",
            description=f"Key `{key}` has been successfully revoked.",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Key not found or already revoked.")

@bot.command(name='keys')
async def show_keys(ctx, user: Optional[discord.Member] = None):
    """Show all keys for a user (or yourself if no user specified)"""
    if not await check_permissions(ctx):
        return
    
    target_user = user or ctx.author
    user_keys = key_manager.get_user_keys(target_user.id)
    
    if not user_keys:
        await ctx.send(f"🔍 No keys found for {target_user.display_name}.")
        return
    
    embed = discord.Embed(
        title=f"🔑 Keys for {target_user.display_name}",
        color=0x2d6cdf
    )
    
    for key_data in user_keys[:10]:  # Limit to 10 keys to avoid embed limits
        key = key_data["key"]
        status = "✅ Active" if key_data["is_active"] else "❌ Revoked"
        expires = f"<t:{key_data['expiration_time']}:R>"
        
        embed.add_field(
            name=f"Key: {key[:8]}...",
            value=f"Status: {status}\nExpires: {expires}\nUsage: {key_data.get('usage_count', 0)} times",
            inline=True
        )
    
    if len(user_keys) > 10:
        embed.set_footer(text=f"Showing 10 of {len(user_keys)} keys")
    
    embed.set_thumbnail(url=target_user.display_avatar.url if target_user.display_avatar else None)
    await ctx.send(embed=embed)

@bot.command(name='info')
async def key_info(ctx, key: str):
    """Get detailed information about a key"""
    if not await check_permissions(ctx):
        return
    
    key_data = key_manager.get_key_info(key)
    if not key_data:
        await ctx.send("❌ Key not found.")
        return
    
    embed = discord.Embed(
        title=f"🔍 Key Information",
        color=0x2d6cdf
    )
    
    # Get user info
    user = ctx.guild.get_member(key_data["created_by"])
    user_name = user.display_name if user else "Unknown User"
    
    embed.add_field(name="Created By", value=user_name, inline=True)
    embed.add_field(name="Status", value="✅ Active" if key_data["is_active"] else "❌ Revoked", inline=True)
    embed.add_field(name="Created", value=f"<t:{key_data['activation_time']}:R>", inline=True)
    embed.add_field(name="Expires", value=f"<t:{key_data['expiration_time']}:R>", inline=True)
    
    if key_data["channel_id"]:
        embed.add_field(name="Channel Locked", value=f"<#{key_data['channel_id']}>", inline=True)
    
    if key_data["machine_id"]:
        embed.add_field(name="Machine ID", value=f"`{key_data['machine_id']}`", inline=True)
        embed.add_field(name="Activated", value=f"<t:{key_data['activated']}:R>", inline=True)
    
    embed.add_field(name="Usage Count", value=key_data.get("usage_count", 0), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='backup')
async def backup_keys(ctx):
    """Create a backup of all keys"""
    if not await check_permissions(ctx):
        return
    
    backup_file = key_manager.backup_keys()
    
    embed = discord.Embed(
        title="💾 Backup Created",
        description=f"Keys backup saved to `{backup_file}`",
        color=0x00ff00
    )
    
    embed.add_field(name="Total Keys", value=len(key_manager.keys), inline=True)
    embed.add_field(name="Backup Time", value=f"<t:{int(time.time())}:F>", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='restore')
async def restore_keys(ctx, backup_file: str):
    """Restore keys from a backup file"""
    if not await check_permissions(ctx):
        return
    
    if not os.path.exists(backup_file):
        await ctx.send("❌ Backup file not found.")
        return
    
    if key_manager.restore_from_backup(backup_file):
        embed = discord.Embed(
            title="🔄 Backup Restored",
            description="Keys have been successfully restored from backup.",
            color=0x00ff00
        )
        
        embed.add_field(name="Total Keys", value=len(key_manager.keys), inline=True)
        embed.add_field(name="Restore Time", value=f"<t:{int(time.time())}:F>", inline=True)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to restore from backup.")

@bot.command(name='status')
async def bot_status(ctx):
    """Show bot status and statistics"""
    if not await check_permissions(ctx):
        return
    
    total_keys = len(key_manager.keys)
    active_keys = sum(1 for k in key_manager.keys.values() if k["is_active"])
    revoked_keys = total_keys - active_keys
    
    # Calculate total usage
    total_usage = sum(k.get("usage_count", 0) for k in key_manager.key_usage.values())
    
    embed = discord.Embed(
        title="📊 Bot Status",
        color=0x2d6cdf
    )
    
    embed.add_field(name="Total Keys", value=total_keys, inline=True)
    embed.add_field(name="Active Keys", value=active_keys, inline=True)
    embed.add_field(name="Revoked Keys", value=revoked_keys, inline=True)
    embed.add_field(name="Total Usage", value=total_usage, inline=True)
    embed.add_field(name="Uptime", value=f"<t:{int(bot.start_time.timestamp())}:R>", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    """Automatically give role to new members if they have a valid key"""
    # This would be triggered when someone joins with a valid key
    # Implementation depends on your activation flow
    pass

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Add a simple health check for Render
import http.server
import socketserver
import threading

def start_health_check():
    """Start a simple HTTP server for health checks"""
    class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                response = f"""
                <html>
                <head><title>Discord Bot Status</title></head>
                <body>
                    <h1>🤖 Discord Bot is Running</h1>
                    <p>Status: Online</p>
                    <p>Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Bot: {bot.user.name if bot.user else 'Starting...'}</p>
                </body>
                </html>
                """
                self.wfile.write(response.encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Suppress logging for health checks
            pass
    
    try:
        # Use Render's PORT environment variable or default to 8080
        port = int(os.getenv('PORT', 8080))
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            print(f"🌐 Health check server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Health check server failed: {e}")

# Error handling
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Error in {event}: {args}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    else:
        print(f"❌ Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Run the bot
if __name__ == "__main__":
    print("🚀 Starting Discord Bot...")
    print("=" * 40)
    
    try:
        # Start health check server in a separate thread
        health_thread = threading.Thread(target=start_health_check, daemon=True)
        health_thread.start()
        print("✅ Health check server started")
        
        # Start the Discord bot
        print("🔗 Connecting to Discord...")
        bot.run(BOT_TOKEN)
        
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)
