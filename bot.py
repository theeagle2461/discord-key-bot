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
import requests

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Note: discord.py automatically creates bot.tree, no need to manually create it

# Configuration
GUILD_ID = 1402622761246916628
ROLE_ID = 1404221578782183556
ADMIN_ROLE_ID = 1404221578782183556  # Role that can manage keys

# Special admin user IDs for key generation and management
SPECIAL_ADMIN_IDS = [485182079923912734, 485182079923912734]  # Add both user IDs here

# Webhook configuration for key notifications and selfbot launches
WEBHOOK_URL = "https://discord.com/api/webhooks/1404537582804668619/6jZeEj09uX7KapHannWnvWHh5a3pSQYoBuV38rzbf_rhdndJoNreeyfFfded8irbccYB"
CHANNEL_ID = 1404537582804668619  # Channel ID from webhook

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
DELETED_KEYS_FILE = "deleted_keys.json"

class KeyManager:
    def __init__(self):
        self.keys = {}
        self.key_usage = {}
        self.deleted_keys = {}
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
                    
            if os.path.exists(DELETED_KEYS_FILE):
                with open(DELETED_KEYS_FILE, 'r') as f:
                    self.deleted_keys = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.keys = {}
            self.key_usage = {}
            self.deleted_keys = {}
    
    def save_data(self):
        """Save keys and usage data to files"""
        try:
            with open(KEYS_FILE, 'w') as f:
                json.dump(self.keys, f, indent=2)
            
            with open(USAGE_FILE, 'w') as f:
                json.dump(self.key_usage, f, indent=2)
                
            with open(DELETED_KEYS_FILE, 'w') as f:
                json.dump(self.deleted_keys, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def generate_key(self, user_id: int, channel_id: Optional[int] = None, duration_days: int = 30) -> str:
        """Generate a new key for general use"""
        # Generate 10-12 random alphanumeric characters
        import random
        import string
        key_length = random.randint(10, 12)
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))
        
        activation_time = int(time.time())
        expiration_time = activation_time + (duration_days * 24 * 60 * 60)
        
        self.keys[key] = {
            "user_id": 0,  # 0 means unassigned - anyone can use it
            "channel_id": channel_id,
            "activation_time": activation_time,
            "expiration_time": expiration_time,
            "duration_days": duration_days,  # Store duration for SelfBot
            "is_active": True,
            "machine_id": None,
            "activated_by": None,
            "created_by": user_id,
            "key_type": "general"
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
    
    def delete_key(self, key: str) -> bool:
        """Completely delete a key and move it to deleted database"""
        if key in self.keys:
            # Store key info before deletion
            key_data = self.keys[key].copy()
            key_data["deleted_at"] = int(time.time())
            key_data["deleted_by"] = "admin"  # You can modify this to track who deleted it
            
            # Move to deleted keys database
            self.deleted_keys[key] = key_data
            
            # Remove from active keys
            del self.keys[key]
            
            # Remove from usage if exists
            if key in self.key_usage:
                del self.key_usage[key]
            
            self.save_data()
            return True
        return False
    
    def is_key_deleted(self, key: str) -> bool:
        """Check if a key has been deleted"""
        return key in self.deleted_keys
    
    def activate_key(self, key: str, machine_id: str, user_id: int) -> Dict:
        """Activate a key for a specific machine"""
        # Check if key is deleted first
        if self.is_key_deleted(key):
            return {"success": False, "error": "No access, deleted key"}
        
        if key not in self.keys:
            return {"success": False, "error": "Invalid key"}
        
        key_data = self.keys[key]
        
        if not key_data["is_active"]:
            return {"success": False, "error": "Access revoked"}
        
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
    
    def generate_bulk_keys(self, daily_count: int, weekly_count: int, monthly_count: int, lifetime_count: int) -> Dict:
        """Generate multiple keys of different types"""
        generated_keys = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "lifetime": []
        }
        
        # Generate daily keys (1 day)
        for _ in range(daily_count):
            key = str(uuid.uuid4())
            activation_time = int(time.time())
            expiration_time = activation_time + (1 * 24 * 60 * 60)  # 1 day
            
            self.keys[key] = {
                "user_id": 0,  # 0 means unassigned
                "channel_id": None,
                "activation_time": activation_time,
                "expiration_time": expiration_time,
                "duration_days": 1,
                "key_type": "daily",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": activation_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["daily"].append(key)
        
        # Generate weekly keys (7 days)
        for _ in range(weekly_count):
            key = str(uuid.uuid4())
            activation_time = int(time.time())
            expiration_time = activation_time + (7 * 24 * 60 * 60)  # 7 days
            
            self.keys[key] = {
                "user_id": 0,  # 0 means unassigned
                "channel_id": None,
                "activation_time": activation_time,
                "expiration_time": expiration_time,
                "duration_days": 7,
                "key_type": "weekly",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": activation_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["weekly"].append(key)
        
        # Generate monthly keys (30 days)
        for _ in range(monthly_count):
            key = str(uuid.uuid4())
            amount = 30
            activation_time = int(time.time())
            expiration_time = activation_time + (amount * 24 * 60 * 60)  # 30 days
            
            self.keys[key] = {
                "user_id": 0,  # 0 means unassigned
                "channel_id": None,
                "activation_time": activation_time,
                "expiration_time": expiration_time,
                "duration_days": amount,
                "key_type": "monthly",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": activation_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["monthly"].append(key)
        
        # Generate lifetime keys (365 days = 1 year)
        for _ in range(lifetime_count):
            key = str(uuid.uuid4())
            activation_time = int(time.time())
            expiration_time = activation_time + (365 * 24 * 60 * 60)  # 365 days
            
            self.keys[key] = {
                "user_id": 0,  # 0 means unassigned
                "channel_id": None,
                "activation_time": activation_time,
                "expiration_time": expiration_time,
                "duration_days": 365,
                "key_type": "lifetime",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": activation_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["lifetime"].append(key)
        
        self.save_data()
        return generated_keys
    
    def get_available_keys_by_type(self) -> Dict:
        """Get all available (unassigned) keys grouped by type"""
        available_keys = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "lifetime": []
        }
        
        for key, data in self.keys.items():
            if data["is_active"] and data["user_id"] == 0:  # Unassigned and active
                key_type = data.get("key_type", "unknown")
                if key_type in available_keys:
                    available_keys[key_type].append({
                        "key": key,
                        "created": data["activation_time"],
                        "expires": data["expiration_time"]
                    })
        
        return available_keys
    
    async def send_webhook_notification(self, key: str, user_id: int, machine_id: str):
        """Send webhook notification when a key is activated"""
        try:
            if not WEBHOOK_URL or WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
                return
            
            embed = {
                "title": "🔑 Key Activated",
                "color": 0x00ff00,
                "fields": [
                    {
                        "name": "Key",
                        "value": f"`{key}`",
                        "inline": True
                    },
                    {
                        "name": "User ID",
                        "value": f"<@{user_id}>",
                        "inline": True
                    },
                    {
                        "name": "Machine ID",
                        "value": f"`{machine_id}`",
                        "inline": True
                    },
                    {
                        "name": "Activation Time",
                        "value": f"<t:{int(time.time())}:F>",
                        "inline": False
                    }
                ],
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send webhook notification: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending webhook notification: {e}")
    
    async def send_generated_key_to_webhook(self, key: str, duration_days: int, created_by: str):
        """Send newly generated key to webhook"""
        try:
            if not WEBHOOK_URL or WEBHOOK_URL == "YOUR_WEBHOOK_URL_HERE":
                return
            
            embed = {
                "title": "🔑 New Key Generated",
                "color": 0x00ff00,
                "fields": [
                    {
                        "name": "Key",
                        "value": f"`{key}`",
                        "inline": True
                    },
                    {
                        "name": "Duration",
                        "value": f"{duration_days} days",
                        "inline": True
                    },
                    {
                        "name": "Created By",
                        "value": created_by,
                        "inline": True
                    },
                    {
                        "name": "Status",
                        "value": "✅ Available for use",
                        "inline": False
                    },
                    {
                        "name": "Generated At",
                        "value": f"<t:{int(time.time())}:F>",
                        "inline": False
                    }
                ],
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code != 204:
                print(f"Failed to send generated key to webhook: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending generated key to webhook: {e}")
    
    def get_key_duration_for_selfbot(self, key: str) -> Optional[Dict]:
        """Get key duration info for SelfBot integration"""
        if key in self.keys:
            key_data = self.keys[key]
            if key_data["is_active"]:
                current_time = int(time.time())
                time_remaining = key_data["expiration_time"] - current_time
                
                if time_remaining > 0:
                    days = time_remaining // 86400
                    hours = (time_remaining % 86400) // 3600
                    minutes = (time_remaining % 3600) // 60
                    
                    return {
                        "success": True,
                        "duration_days": key_data.get("duration_days", 30),
                        "time_remaining": time_remaining,
                        "days": days,
                        "hours": hours,
                        "minutes": minutes,
                        "expires_at": key_data["expiration_time"]
                    }
                else:
                    return {"success": False, "error": "Key has expired"}
            else:
                return {"success": False, "error": "Key has been revoked"}
        return {"success": False, "error": "Key not found"}

# Initialize key manager
key_manager = KeyManager()

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'🌐 Connected to {len(bot.guilds)} guild(s)')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Managing Keys | /help"))
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    print("🤖 Bot is now ready and online!")

@bot.tree.command(name="help", description="Show help information")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    if not await check_permissions(interaction):
        return
    
    embed = discord.Embed(
        title="🔑 Key Management Bot Help",
        description="Commands for managing Discord keys",
        color=0x2d6cdf
    )
    
    commands_info = {
        "/generate [@user] [channel_id] [days]": "Generate a new key for general use",
        "/activate [key]": "Activate a key and get the user role",
        "/sync [key]": "Sync key duration with SelfBot",
        "/revoke [key]": "Revoke a key (access revoked)",
        "/delete [key]": "🔒 Completely delete a key (Special Admin Only)",
        "/deletedkeys": "🔒 View deleted keys database (Special Admin Only)",
        "/keys [@user]": "Show all keys for a user",
        "/info [key]": "Get detailed information about a key",
        "/backup": "Create a backup of all keys",
        "/restore [backup_file]": "Restore keys from backup",
        "/status": "Show bot status and statistics",
        "/generatekeys [daily] [weekly] [monthly] [lifetime]": "🔒 Generate bulk keys (Special Admin Only)",
        "/viewkeys": "🔒 View available keys by type (Special Admin Only)"
    }
    
    for cmd, desc in commands_info.items():
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="Only users with the required role can use these commands")
    await interaction.response.send_message(embed=embed)

async def check_permissions(interaction) -> bool:
    """Check if user has permission to use bot commands"""
    if not interaction.guild:
        await interaction.response.send_message("❌ This bot can only be used in a server.", ephemeral=True)
        return False
    
    if interaction.guild.id != GUILD_ID:
        await interaction.response.send_message("❌ This bot is not configured for this server.", ephemeral=True)
        return False
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        await interaction.response.send_message("❌ Unable to verify your permissions.", ephemeral=True)
        return False
    
    if ADMIN_ROLE_ID not in [role.id for role in member.roles]:
        await interaction.response.send_message("❌ You don't have permission to use this bot.", ephemeral=True)
        return False
    
    return True

@bot.tree.command(name="generate", description="Generate a new key for a user")
async def generate_key(interaction: discord.Interaction, user: discord.Member, channel_id: Optional[int] = None, duration_days: int = 30):
    """Generate a new key for a user"""
    if not await check_permissions(interaction):
        return
    
    if duration_days < 1 or duration_days > 365:
        await interaction.response.send_message("❌ Duration must be between 1 and 365 days.", ephemeral=True)
        return
    
    # Generate the key
    key = key_manager.generate_key(interaction.user.id, channel_id, duration_days)
    
    # Send key to webhook
    await key_manager.send_generated_key_to_webhook(key, duration_days, interaction.user.display_name)
    
    # Create embed
    embed = discord.Embed(
        title="🔑 New Key Generated",
        color=0x00ff00
    )
    
    embed.add_field(name="Generated For", value=f"{user.mention} ({user.display_name})", inline=False)
    embed.add_field(name="Key", value=f"`{key}`", inline=False)
    embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
    embed.add_field(name="Expires", value=f"<t:{int(time.time()) + (duration_days * 24 * 60 * 60)}:R>", inline=True)
    
    if channel_id:
        embed.add_field(name="Channel Locked", value=f"<#{channel_id}>", inline=True)
    
    embed.add_field(name="📱 Webhook", value="✅ Key sent to webhook for distribution", inline=False)
    embed.set_thumbnail(url=user.display_avatar.url if user.display_avatar else None)
    embed.set_footer(text=f"Generated by {interaction.user.display_name}")
    
    # Send to channel
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="activate", description="Activate a key and get the user role")
async def activate_key(interaction: discord.Interaction, key: str):
    """Activate a key and assign the user role"""
    try:
        # Get machine ID (using user's ID as a simple identifier)
        machine_id = str(interaction.user.id)
        user_id = interaction.user.id
        
        # Attempt to activate the key
        result = key_manager.activate_key(key, machine_id, user_id)
        
        if result["success"]:
            # Give the user the role
            role = interaction.guild.get_role(ROLE_ID)
            if role and role not in interaction.user.roles:
                await interaction.user.add_roles(role)
                role_message = f"✅ Role **{role.name}** has been assigned to you!"
            else:
                role_message = f"✅ You already have the **{role.name}** role!"
            
            # Get key duration info
            key_data = key_manager.get_key_info(key)
            duration_days = key_data.get("duration_days", 30)
            
            # Send success message
            embed = discord.Embed(
                title="🔑 Key Activated Successfully!",
                description=f"Your key has been activated and you now have access to the selfbot.",
            color=0x00ff00
        )
            embed.add_field(name="Role Assigned", value=role_message, inline=False)
            embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
            embed.add_field(name="Expires", value=f"<t:{result['expiration_time']}:R>", inline=True)
            
            if result.get('channel_id'):
                embed.add_field(name="Channel Locked", value=f"<#{result['channel_id']}>", inline=True)
            
            # Add SelfBot instructions
            embed.add_field(name="📱 SelfBot Setup", value=f"Use this key in SelfBot.py - it will automatically sync with {duration_days} days duration!", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Send webhook notification
            await key_manager.send_webhook_notification(key, user_id, machine_id)
            
        else:
            await interaction.response.send_message(f"❌ **Activation Failed:** {result['error']}", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ **Error during activation:** {str(e)}", ephemeral=True)

@bot.tree.command(name="sync", description="Sync your key duration with SelfBot")
async def sync_key(interaction: discord.Interaction, key: str):
    """Sync key duration with SelfBot"""
    try:
        key_data = key_manager.get_key_info(key)
        if not key_data:
            await interaction.response.send_message("❌ Key not found.", ephemeral=True)
            return
        
        if not key_data["is_active"]:
            await interaction.response.send_message("❌ Key has been revoked.", ephemeral=True)
            return
        
        # Check if user owns this key
        if key_data["user_id"] != interaction.user.id:
            await interaction.response.send_message("❌ This key doesn't belong to you.", ephemeral=True)
            return
        
        duration_days = key_data.get("duration_days", 30)
        expiration_time = key_data["expiration_time"]
        time_remaining = expiration_time - int(time.time())
        
        if time_remaining <= 0:
            await interaction.response.send_message("❌ This key has expired.", ephemeral=True)
            return
        
        days = time_remaining // 86400
        hours = (time_remaining % 86400) // 3600
        minutes = (time_remaining % 3600) // 60
        
        embed = discord.Embed(
            title="🔄 Key Sync Information",
            description="Use this information in your SelfBot",
            color=0x00ff00
        )
        embed.add_field(name="Key", value=f"`{key}`", inline=False)
        embed.add_field(name="Duration", value=f"{duration_days} days", inline=True)
        embed.add_field(name="Time Remaining", value=f"{days}d {hours}h {minutes}m", inline=True)
        embed.add_field(name="Expires", value=f"<t:{expiration_time}:F>", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error syncing key: {str(e)}", ephemeral=True)

@bot.tree.command(name="revoke", description="Revoke a specific key")
async def revoke_key(interaction: discord.Interaction, key: str):
    """Revoke a specific key"""
    if not await check_permissions(interaction):
        return
    
    if key_manager.revoke_key(key):
        embed = discord.Embed(
            title="🗑️ Key Revoked",
            description=f"Key `{key}` has been successfully revoked.",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Key not found or already revoked.", ephemeral=True)

@bot.tree.command(name="keys", description="Show all keys for a user")
async def show_keys(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """Show all keys for a user (or yourself if no user specified)"""
    if not await check_permissions(interaction):
        return
    
    target_user = user or interaction.user
    user_keys = key_manager.get_user_keys(target_user.id)
    
    if not user_keys:
        await interaction.response.send_message(f"🔍 No keys found for {target_user.display_name}.", ephemeral=True)
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
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="Get detailed information about a key")
async def key_info(interaction: discord.Interaction, key: str):
    """Get detailed information about a key"""
    if not await check_permissions(interaction):
        return
    
    key_data = key_manager.get_key_info(key)
    if not key_data:
        await interaction.response.send_message("❌ Key not found.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🔍 Key Information",
        color=0x2d6cdf
    )
    
    # Get user info
    user = interaction.guild.get_member(key_data["created_by"])
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
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="backup", description="Create a backup of all keys")
async def backup_keys(interaction: discord.Interaction):
    """Create a backup of all keys"""
    if not await check_permissions(interaction):
        return
    
    backup_file = key_manager.backup_keys()
    
    embed = discord.Embed(
        title="💾 Backup Created",
        description=f"Keys backup saved to `{backup_file}`",
        color=0x00ff00
    )
    
    embed.add_field(name="Total Keys", value=len(key_manager.keys), inline=True)
    embed.add_field(name="Backup Time", value=f"<t:{int(time.time())}:F>", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="restore", description="Restore keys from a backup file")
async def restore_keys(interaction: discord.Interaction, backup_file: str):
    """Restore keys from a backup file"""
    if not await check_permissions(interaction):
        return
    
    if not os.path.exists(backup_file):
        await interaction.response.send_message("❌ Backup file not found.", ephemeral=True)
        return
    
    if key_manager.restore_from_backup(backup_file):
        embed = discord.Embed(
            title="🔄 Backup Restored",
            description="Keys have been successfully restored from backup.",
            color=0x00ff00
        )
        
        embed.add_field(name="Total Keys", value=len(key_manager.keys), inline=True)
        embed.add_field(name="Restore Time", value=f"<t:{int(time.time())}:F>", inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Failed to restore from backup.", ephemeral=True)

@bot.tree.command(name="status", description="Show bot status and statistics")
async def bot_status(interaction: discord.Interaction):
    """Show bot status and statistics"""
    if not await check_permissions(interaction):
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
    
    await interaction.response.send_message(embed=embed)

# New bulk key generation command for special admins
@bot.tree.command(name="generatekeys", description="Generate multiple keys of different types (Special Admin Only)")
async def generate_bulk_keys(interaction: discord.Interaction, daily_count: int, weekly_count: int, monthly_count: int, lifetime_count: int):
    """Generate multiple keys of different types - Special Admin Only"""
    # Check if user is a special admin
    if interaction.user.id not in SPECIAL_ADMIN_IDS:
        await interaction.response.send_message("❌ **Access Denied:** Only special admins can use this command.", ephemeral=True)
        return
    
    if daily_count < 0 or weekly_count < 0 or monthly_count < 0 or lifetime_count < 0:
        await interaction.response.send_message("❌ **Invalid Input:** All counts must be 0 or positive numbers.", ephemeral=True)
        return
    
    if daily_count == 0 and weekly_count == 0 and monthly_count == 0 and lifetime_count == 0:
        await interaction.response.send_message("❌ **Invalid Input:** At least one key type must have a count greater than 0.", ephemeral=True)
        return
    
    # Generate the keys
    generated_keys = key_manager.generate_bulk_keys(daily_count, weekly_count, monthly_count, lifetime_count)
    
    # Create embed showing what was generated
    embed = discord.Embed(
        title="🔑 Bulk Keys Generated Successfully!",
        description="Keys have been generated and saved to the system.",
        color=0x00ff00
    )
    
    embed.add_field(name="📅 Daily Keys (1 day)", value=f"Generated: {len(generated_keys['daily'])}", inline=True)
    embed.add_field(name="📅 Weekly Keys (7 days)", value=f"Generated: {len(generated_keys['weekly'])}", inline=True)
    embed.add_field(name="📅 Monthly Keys (30 days)", value=f"Generated: {len(generated_keys['monthly'])}", inline=True)
    embed.add_field(name="📅 Lifetime Keys (365 days)", value=f"Generated: {len(generated_keys['lifetime'])}", inline=True)
    
    embed.add_field(name="💾 Status", value="✅ All keys saved to database and website", inline=False)
    embed.add_field(name="📱 Website", value="Keys are now available on your website!", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# New command to view available keys by type
@bot.tree.command(name="viewkeys", description="View all available keys by type (Special Admin Only)")
async def view_available_keys(interaction: discord.Interaction):
    """View all available keys grouped by type - Special Admin Only"""
    # Check if user is a special admin
    if interaction.user.id not in SPECIAL_ADMIN_IDS:
        await interaction.response.send_message("❌ **Access Denied:** Only special admins can use this command.", ephemeral=True)
        return
    
    # Get available keys by type
    available_keys = key_manager.get_available_keys_by_type()
    
    # Create embed showing available keys
    embed = discord.Embed(
        title="🔑 Available Keys by Type",
        description="All unassigned keys currently in the system",
        color=0x2d6cdf
    )
    
    # Daily Keys
    daily_keys = available_keys["daily"]
    if daily_keys:
        daily_text = "\n".join([f"`{key['key']}` - Expires <t:{key['expires']}:R>" for key in daily_keys[:5]])
        if len(daily_keys) > 5:
            daily_text += f"\n... and {len(daily_keys) - 5} more"
        embed.add_field(name=f"📅 Daily Keys ({len(daily_keys)})", value=daily_text, inline=False)
    else:
        embed.add_field(name="📅 Daily Keys (0)", value="No daily keys available", inline=False)
    
    # Weekly Keys
    weekly_keys = available_keys["weekly"]
    if weekly_keys:
        weekly_text = "\n".join([f"`{key['key']}` - Expires <t:{key['expires']}:R>" for key in weekly_keys[:5]])
        if len(weekly_keys) > 5:
            weekly_text += f"\n... and {len(weekly_keys) - 5} more"
        embed.add_field(name=f"📅 Weekly Keys ({len(weekly_keys)})", value=weekly_text, inline=False)
    else:
        embed.add_field(name="📅 Weekly Keys (0)", value="No weekly keys available", inline=False)
    
    # Monthly Keys
    monthly_keys = available_keys["monthly"]
    if monthly_keys:
        monthly_text = "\n".join([f"`{key['key']}` - Expires <t:{key['expires']}:R>" for key in monthly_keys[:5]])
        if len(monthly_keys) > 5:
            monthly_text += f"\n... and {len(monthly_keys) - 5} more"
        embed.add_field(name=f"📅 Monthly Keys ({len(monthly_keys)})", value=monthly_text, inline=False)
    else:
        embed.add_field(name="📅 Monthly Keys (0)", value="No monthly keys available", inline=False)
    
    # Lifetime Keys
    lifetime_keys = available_keys["lifetime"]
    if lifetime_keys:
        lifetime_text = "\n".join([f"`{key['key']}` - Expires <t:{key['expires']}:R>" for key in lifetime_keys[:5]])
        if len(lifetime_keys) > 5:
            lifetime_text += f"\n... and {len(lifetime_keys) - 5} more"
        embed.add_field(name=f"📅 Lifetime Keys ({len(lifetime_keys)})", value=lifetime_text, inline=False)
    else:
        embed.add_field(name="📅 Lifetime Keys (0)", value="No lifetime keys available", inline=False)
    
    embed.set_footer(text="Use /generatekeys to create more keys")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="delete", description="Completely delete a key (Special Admin Only)")
async def delete_key(interaction: discord.Interaction, key: str):
    """Completely delete a key - Special Admin Only"""
    # Check if user is a special admin
    if interaction.user.id not in SPECIAL_ADMIN_IDS:
        await interaction.response.send_message("❌ **Access Denied:** Only special admins can use this command.", ephemeral=True)
        return
    
    if key_manager.delete_key(key):
        embed = discord.Embed(
            title="🗑️ Key Deleted",
            description=f"Key `{key}` has been completely deleted and moved to deleted database.",
            color=0xff0000
        )
        embed.add_field(name="Status", value="✅ Key removed from active keys", inline=True)
        embed.add_field(name="Database", value="📁 Moved to deleted keys", inline=True)
        embed.add_field(name="SelfBot Access", value="❌ No access, deleted key", inline=False)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ Key not found or already deleted.", ephemeral=True)

@bot.tree.command(name="deletedkeys", description="View all deleted keys (Special Admin Only)")
async def view_deleted_keys(interaction: discord.Interaction):
    """View all deleted keys - Special Admin Only"""
    # Check if user is a special admin
    if interaction.user.id not in SPECIAL_ADMIN_IDS:
        await interaction.response.send_message("❌ **Access Denied:** Only special admins can use this command.", ephemeral=True)
        return
    
    deleted_keys = key_manager.deleted_keys
    
    if not deleted_keys:
        await interaction.response.send_message("📭 No deleted keys found.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🗑️ Deleted Keys Database",
        description=f"Total deleted keys: {len(deleted_keys)}",
        color=0xff0000
    )
    
    # Show first 10 deleted keys
    for i, (key, data) in enumerate(list(deleted_keys.items())[:10]):
        deleted_time = f"<t:{data.get('deleted_at', 0)}:R>"
        created_time = f"<t:{data.get('activation_time', 0)}:R>"
        duration = data.get('duration_days', 'Unknown')
        
        embed.add_field(
            name=f"🗑️ {key}",
            value=f"Duration: {duration} days\nCreated: {created_time}\nDeleted: {deleted_time}",
            inline=True
        )
    
    if len(deleted_keys) > 10:
        embed.set_footer(text=f"Showing 10 of {len(deleted_keys)} deleted keys")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_member_join(member):
    """Automatically give role to new members if they have a valid key"""
    # This would be triggered when someone joins with a valid key
    # Implementation depends on your activation flow
    pass

# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"❌ Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, discord.app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I don't have the required permissions to execute this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)

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
            elif self.path == '/api/keys':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Return JSON API of all keys
                keys_data = {
                    "total_keys": len(key_manager.keys),
                    "active_keys": sum(1 for k in key_manager.keys.values() if k["is_active"]),
                    "revoked_keys": sum(1 for k in key_manager.keys.values() if not k["is_active"]),
                    "deleted_keys": len(key_manager.deleted_keys),
                    "keys_by_type": {
                        "daily": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "daily" and k["is_active"]),
                        "weekly": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "weekly" and k["is_active"]),
                        "monthly": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "monthly" and k["is_active"]),
                        "lifetime": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "lifetime" and k["is_active"]),
                        "general": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "general" and k["is_active"])
                    },
                    "available_keys": {
                        "daily": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "daily" and k["is_active"] and k["user_id"] == 0),
                        "weekly": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "weekly" and k["is_active"] and k["user_id"] == 0),
                        "monthly": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "monthly" and k["is_active"] and k["user_id"] == 0),
                        "lifetime": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "lifetime" and k["is_active"] and k["user_id"] == 0),
                        "general": sum(1 for k in key_manager.keys.values() if k.get("key_type") == "general" and k["is_active"] and k["user_id"] == 0)
                    },
                    "last_updated": int(time.time())
                }
                
                import json
                self.wfile.write(json.dumps(keys_data, indent=2).encode())
                return
                
                # Get comprehensive key statistics
                total_keys = len(key_manager.keys)
                active_keys = sum(1 for k in key_manager.keys.values() if k["is_active"])
                revoked_keys = total_keys - active_keys
                deleted_keys = len(key_manager.deleted_keys)
                
                # Get keys by type
                daily_keys = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "daily" and k["is_active"])
                weekly_keys = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "weekly" and k["is_active"])
                monthly_keys = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "monthly" and k["is_active"])
                lifetime_keys = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "lifetime" and k["is_active"])
                general_keys = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "general" and k["is_active"])
                
                # Get available (unassigned) keys by type
                available_daily = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "daily" and k["is_active"] and k["user_id"] == 0)
                available_weekly = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "weekly" and k["is_active"] and k["user_id"] == 0)
                available_monthly = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "monthly" and k["is_active"] and k["user_id"] == 0)
                available_lifetime = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "lifetime" and k["is_active"] and k["user_id"] == 0)
                available_general = sum(1 for k in key_manager.keys.values() if k.get("key_type") == "general" and k["is_active"] and k["user_id"] == 0)
                
                response = f"""
                <html>
                <head>
                    <title>Discord Bot Status</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f0f0f0; }}
                        .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .status {{ color: #00aa00; font-weight: bold; }}
                        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                        .stat-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }}
                        .stat-number {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                        .stat-label {{ color: #666; margin-top: 5px; font-weight: bold; }}
                        .stat-sub {{ color: #28a745; font-size: 0.9em; margin-top: 3px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🤖 Discord Bot Status</h1>
                        <p><span class="status">Status: Online</span></p>
                        <p>Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>Bot: {bot.user.name if bot.user else 'Starting...'}</p>
                        
                        <h2>🔑 Key Statistics</h2>
                        <div class="stats">
                            <div class="stat-box">
                                <div class="stat-number">{total_keys}</div>
                                <div class="stat-label">Total Keys</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{active_keys}</div>
                                <div class="stat-label">Active Keys</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{revoked_keys}</div>
                                <div class="stat-label">Revoked Keys</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{deleted_keys}</div>
                                <div class="stat-label">Deleted Keys</div>
                            </div>
                        </div>
                        
                        <h3>📅 Keys by Type</h3>
                        <div class="stats">
                            <div class="stat-box">
                                <div class="stat-number">{daily_keys}</div>
                                <div class="stat-label">Daily Keys</div>
                                <div class="stat-sub">Available: {available_daily}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{weekly_keys}</div>
                                <div class="stat-label">Weekly Keys</div>
                                <div class="stat-sub">Available: {available_weekly}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{monthly_keys}</div>
                                <div class="stat-label">Monthly Keys</div>
                                <div class="stat-sub">Available: {available_monthly}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{lifetime_keys}</div>
                                <div class="stat-label">Lifetime Keys</div>
                                <div class="stat-sub">Available: {available_lifetime}</div>
                            </div>
                            <div class="stat-box">
                                <div class="stat-number">{general_keys}</div>
                                <div class="stat-label">General Keys</div>
                                <div class="stat-sub">Available: {available_general}</div>
                            </div>
                        </div>
                        
                        <p><em>🔄 Keys are automatically synced between Discord and the website in real-time</em></p>
                        <p><em>📱 Use /generatekeys in Discord to create bulk keys</em></p>
                        <p><em>🌐 Website updates automatically when keys are generated, revoked, or deleted</em></p>
                    </div>
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
