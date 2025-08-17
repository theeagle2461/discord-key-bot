try:
    import audioop  # Will fail on Python 3.13
except Exception:  # pragma: no cover
    try:
        import audioop_lts as audioop  # Fallback for Python 3.13
    except Exception:
        audioop = None

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
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
import urllib.parse
import html
import io

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Note: discord.py automatically creates bot.tree, no need to manually create it

# Configuration
GUILD_ID = int(os.getenv('GUILD_ID', '1402622761246916628') or 0)
ROLE_ID = 1404221578782183556
ROLE_NAME = os.getenv('ROLE_NAME', 'activated key')
OWNER_ROLE_ID = int(os.getenv('OWNER_ROLE_ID', '1402650246538072094') or 0)
CHATSEND_ROLE_ID = int(os.getenv('CHATSEND_ROLE_ID', '1406339861593591900') or 0)
ADMIN_ROLE_ID = 1402650352083402822  # Role that can manage keys
# Backup to Discord channel and auto-restore settings
BACKUP_CHANNEL_ID = int(os.getenv('BACKUP_CHANNEL_ID', '0') or 0)
AUTO_RESTORE_ON_START = (os.getenv('AUTO_RESTORE_ON_START', 'false').lower() in ('1','true','yes'))
try:
	BACKUP_INTERVAL_MIN = int(os.getenv('BACKUP_INTERVAL_MIN', '60') or 60)
except Exception:
	BACKUP_INTERVAL_MIN = 60

# Special admin user IDs for key generation and management
SPECIAL_ADMIN_IDS = [1216851450844413953, 414921052968452098, 485182079923912734]  # Admin user IDs

# Webhook configuration for key notifications and selfbot launches
WEBHOOK_URL = "https://discord.com/api/webhooks/1404537582804668619/6jZeEj09uX7KapHannWnvWHh5a3pSQYoBuV38rzbf_rhdndJoNreeyfFfded8irbccYB"
CHANNEL_ID = 1404537582804668619  # Channel ID from webhook
PURCHASE_LOG_WEBHOOK = os.getenv('PURCHASE_LOG_WEBHOOK','')
# NOWPayments credentials
NWP_API_KEY = os.getenv('NWP_API_KEY','')
NWP_IPN_SECRET = os.getenv('NWP_IPN_SECRET','')
PUBLIC_URL = os.getenv('PUBLIC_URL','')  # optional; used for ipn callback if provided

# Load bot token from environment variable for security
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Secret for signing panel session cookies
PANEL_SECRET = os.getenv('PANEL_SECRET', None)
if not PANEL_SECRET:
    PANEL_SECRET = uuid.uuid4().hex  # ephemeral fallback; set PANEL_SECRET in env for persistent sessions

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

# Data storage (support persistent directory via DATA_DIR)
DATA_DIR = os.getenv('DATA_DIR', '.')
os.makedirs(DATA_DIR, exist_ok=True)
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
BACKUP_FILE = os.path.join(DATA_DIR, "keys_backup.json")
USAGE_FILE = os.path.join(DATA_DIR, "key_usage.json")
DELETED_KEYS_FILE = os.path.join(DATA_DIR, "deleted_keys.json")
LOGS_FILE = os.path.join(DATA_DIR, "key_logs.json")
# Simple site-wide chat storage
CHAT_FILE = os.path.join(DATA_DIR, "chat_messages.json")
ANN_FILE = os.path.join(DATA_DIR, "announcements.json")
STATS_FILE = os.path.join(DATA_DIR, "selfbot_message_stats.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
MESSAGES_THRESHOLD = int(os.getenv('MESSAGES_THRESHOLD', '2500') or 2500)
MESSAGE_STATS: Dict[str, int] = {}
try:
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            MESSAGE_STATS = json.load(f) or {}
except Exception:
    MESSAGE_STATS = {}

# Config helpers
CONFIG: dict = {}

def load_config() -> dict:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}

def save_config() -> None:
    try:
        tmp = CONFIG_FILE + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(CONFIG, f, indent=2)
        os.replace(tmp, CONFIG_FILE)
    except Exception:
        pass

# Initialize key manager (moved below after class definition)
# Load config and apply overrides
CONFIG = load_config()
try:
    cfg_backup = CONFIG.get('BACKUP_CHANNEL_ID')
    if cfg_backup:
        BACKUP_CHANNEL_ID = int(cfg_backup)
except Exception:
    pass

async def send_status_webhook(event_name: str):
    try:
        url = (CONFIG.get('STATUS_WEBHOOK_URL') or '').strip()
        if not url:
            return
        embed = {
            'title': f'Bot {event_name.title()}',
            'color': 0x22C55E if event_name.lower()=="online" else 0xEF4444,
            'fields': [
                {'name':'Bot ID','value': str(getattr(bot.user,'id', 'unknown')), 'inline': True},
                {'name':'Guilds','value': str(len(bot.guilds)), 'inline': True},
                {'name':'Keys','value': str(len(key_manager.keys)), 'inline': True},
            ],
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        requests.post(url, json={'embeds':[embed]}, timeout=6)
    except Exception:
        pass

class KeyManager:
    def __init__(self):
        self.keys = {}
        self.key_usage = {}
        self.deleted_keys = {}
        self.key_logs: list[dict] = []
        self.last_generated = None  # In-memory cache of last generated keys for web UI panel
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
            if os.path.exists(LOGS_FILE):
                with open(LOGS_FILE, 'r') as f:
                    self.key_logs = json.load(f)
        except Exception as e:
            print(f"Error loading data: {e}")
            self.keys = {}
            self.key_usage = {}
            self.deleted_keys = {}
            self.key_logs = []
    
    def save_data(self):
        """Save keys and usage data to files (atomically) and also write a timestamped backup"""
        try:
            # Atomic writes via temp files and replace
            def atomic_write(path: str, data: dict):
                tmp = f"{path}.tmp"
                with open(tmp, 'w') as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp, path)
            atomic_write(KEYS_FILE, self.keys)
            atomic_write(USAGE_FILE, self.key_usage)
            atomic_write(DELETED_KEYS_FILE, self.deleted_keys)
            atomic_write(LOGS_FILE, self.key_logs)
            # Extra rolling backup snapshot
            ts = int(time.time())
            snap_dir = "backups"
            os.makedirs(snap_dir, exist_ok=True)
            with open(os.path.join(snap_dir, f"keys_{ts}.json"), 'w') as f:
                json.dump({
                    'ts': ts,
                    'keys': self.keys,
                    'usage': self.key_usage,
                    'deleted': self.deleted_keys
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def generate_key(self, user_id: int, channel_id: Optional[int] = None, duration_days: int = 30) -> str:
        """Generate a new key for general use"""
        # Generate 10-12 random alphanumeric characters
        import random
        import string
        key_length = random.randint(10, 12)
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))
        
        created_time = int(time.time())
        
        self.keys[key] = {
            "user_id": 0,  # 0 means unassigned - anyone can use it
            "channel_id": channel_id,
            "created_time": created_time,
            "activation_time": None,           # not activated yet
            "expiration_time": None,           # will be set on activation
            "duration_days": duration_days,    # store desired duration
            "is_active": True,
            "machine_id": None,
            "activated_by": None,
            "created_by": user_id,
            "key_type": "general"
        }
        
        self.key_usage[key] = {
            "created": created_time,
            "activated": None,
            "last_used": None,
            "usage_count": 0
        }
        
        self.save_data()
        try:
            self.add_log('generate', key, user_id=user_id, details={'duration_days': duration_days, 'channel_id': channel_id})
        except Exception:
            pass
        return key
    
    def revoke_key(self, key: str) -> bool:
        """Revoke a key"""
        if key in self.keys:
            self.keys[key]["is_active"] = False
            self.save_data()
            try:
                self.add_log('revoke', key)
            except Exception:
                pass
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
            try:
                self.add_log('delete', key)
            except Exception:
                pass
            return True
        return False
    
    def is_key_deleted(self, key: str) -> bool:
        """Check if a key has been deleted"""
        return key in self.deleted_keys
    
    def activate_key(self, key: str, machine_id: str, user_id: int) -> Dict:
        """Activate a key for a specific machine"""
        key = normalize_key(key)
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
        
        # If already has expiration_time and it's expired, block
        if key_data.get("expiration_time") and key_data["expiration_time"] < int(time.time()):
            return {"success": False, "error": "Key has expired"}
        
        # Activate the key (first-time activation sets activation/expiration)
        now_ts = int(time.time())
        key_data["machine_id"] = machine_id
        key_data["activated_by"] = user_id
        key_data["user_id"] = user_id
        if not key_data.get("activation_time"):
            key_data["activation_time"] = now_ts
        if not key_data.get("expiration_time"):
            duration_days = int(key_data.get("duration_days", 30))
            key_data["expiration_time"] = now_ts + (duration_days * 24 * 60 * 60)
        
        # Update usage
        if key in self.key_usage:
            self.key_usage[key]["activated"] = now_ts
            self.key_usage[key]["last_used"] = now_ts
            self.key_usage[key]["usage_count"] += 1
        
        self.save_data()
        # Log activation
        try:
            self.add_log('activate', key, user_id=user_id, details={'machine_id': machine_id, 'expires': key_data.get('expiration_time')})
        except Exception:
            pass
        
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
    
    def build_backup_payload(self) -> dict:
        """Return a JSON-serializable payload of all state for upload/restore."""
        return {
            "timestamp": int(time.time()),
            "keys": self.keys,
            "usage": self.key_usage,
            "deleted": self.deleted_keys,
            "logs": getattr(self, 'key_logs', []),
        }
    
    def restore_from_payload(self, payload: dict) -> bool:
        """Restore state from a payload dict (like one retrieved from backup)."""
        try:
            keys = payload.get("keys") or {}
            usage = payload.get("usage") or {}
            deleted = payload.get("deleted") or {}
            logs = payload.get("logs") or []
            if not isinstance(keys, dict) or not isinstance(usage, dict):
                return False
            self.keys = keys
            self.key_usage = usage
            self.deleted_keys = deleted if isinstance(deleted, dict) else {}
            self.key_logs = logs if isinstance(logs, list) else []
            self.save_data()
            return True
        except Exception:
            return False
    
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
            print(f"Error restoring from backup: {e}")
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
            created_time = int(time.time())
            
            self.keys[key] = {
                "user_id": 0,
                "channel_id": None,
                "created_time": created_time,
                "activation_time": None,
                "expiration_time": None,
                "duration_days": 1,
                "key_type": "daily",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": created_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["daily"].append(key)
        
        # Generate weekly keys (7 days)
        for _ in range(weekly_count):
            key = str(uuid.uuid4())
            created_time = int(time.time())
            
            self.keys[key] = {
                "user_id": 0,
                "channel_id": None,
                "created_time": created_time,
                "activation_time": None,
                "expiration_time": None,
                "duration_days": 7,
                "key_type": "weekly",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": created_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["weekly"].append(key)
        
        # Generate monthly keys (30 days)
        for _ in range(monthly_count):
            key = str(uuid.uuid4())
            created_time = int(time.time())
            
            self.keys[key] = {
                "user_id": 0,
                "channel_id": None,
                "created_time": created_time,
                "activation_time": None,
                "expiration_time": None,
                "duration_days": 30,
                "key_type": "monthly",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": created_time,
                "activated": None,
                "last_used": None,
                "usage_count": 0
            }
            
            generated_keys["monthly"].append(key)
        
        # Generate lifetime keys (365 days)
        for _ in range(lifetime_count):
            key = str(uuid.uuid4())
            created_time = int(time.time())
            
            self.keys[key] = {
                "user_id": 0,
                "channel_id": None,
                "created_time": created_time,
                "activation_time": None,
                "expiration_time": None,
                "duration_days": 365,
                "key_type": "lifetime",
                "is_active": True,
                "machine_id": None,
                "activated_by": None,
                "created_by": 0
            }
            
            self.key_usage[key] = {
                "created": created_time,
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
                available_entry = {
                    "key": key,
                    "created": data.get("created_time") or data.get("activation_time") or 0,
                    "expires": data.get("expiration_time") or 0
                }
                if key_type in available_keys:
                    available_keys[key_type].append(available_entry)
        
        return available_keys
    
    async def send_webhook_notification(self, key: str, user_id: int, machine_id: str, ip: Optional[str] = None):
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
                        "name": "IP Address",
                        "value": (ip or "Unknown"),
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

    def rebind_key(self, key: str, user_id: int, new_machine_id: str) -> Dict:
        """Rebind a key to a new machine if requested by the same user who activated it.
        Conditions:
        - key exists, not deleted, is_active True
        - key has an activated_by or user_id that matches the requester
        - key not expired
        """
        if self.is_key_deleted(key):
            return {"success": False, "error": "No access, deleted key"}
        if key not in self.keys:
            return {"success": False, "error": "Invalid key"}
        data = self.keys[key]
        if not data.get("is_active", False):
            return {"success": False, "error": "Access revoked"}
        now_ts = int(time.time())
        expires = data.get("expiration_time") or 0
        if expires and expires <= now_ts:
            return {"success": False, "error": "Key has expired"}
        owner = data.get("activated_by") or data.get("user_id")
        if not owner or int(owner) != int(user_id):
            return {"success": False, "error": "Key is owned by a different user"}
        # Update machine binding
        data["machine_id"] = str(new_machine_id)
        # Touch usage
        if key in self.key_usage:
            self.key_usage[key]["last_used"] = now_ts
        self.save_data()
        return {"success": True, "key": key, "user_id": int(user_id), "machine_id": str(new_machine_id)}

    def add_log(self, event: str, key: str, user_id: int | None = None, details: dict | None = None):
        try:
            entry = {
                'ts': int(time.time()),
                'event': event,
                'key': key,
                'user_id': int(user_id) if user_id is not None else None,
                'details': details or {}
            }
            self.key_logs.append(entry)
            # Keep last 1000 entries
            if len(self.key_logs) > 1000:
                self.key_logs = self.key_logs[-1000:]
        except Exception as e:
            print(f"Failed to append log: {e}")

# Instantiate the key manager now that the class is defined
key_manager = KeyManager()

def normalize_key(raw: str | None) -> str:
    if not raw:
        return ""
    k = raw.strip()
    if k.startswith("`") and k.endswith("`") and len(k) >= 2:
        k = k[1:-1]
    return k.strip()

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'🌐 Connected to {len(bot.guilds)} guild(s)')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Managing Keys | /help"))
    
    print("🤖 Bot is now ready and online!")
    try:
        if not reconcile_roles_task.is_running():
            reconcile_roles_task.start()
    except Exception:
        pass
    try:
        if BACKUP_CHANNEL_ID > 0 and not periodic_backup_task.is_running():
            periodic_backup_task.start()
    except Exception:
        pass
    # Send status webhook (online)
    try:
        await send_status_webhook('online')
    except Exception:
        pass
    # Force-sync application commands to this guild to ensure visibility
    try:
        guild_obj = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild_obj)
        print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}")
        try:
            names = [c.name for c in bot.tree.get_commands()]
            print(f"🔎 Commands in tree: {names}")
        except Exception:
            pass
    except Exception as e:
        print(f"⚠️ Failed to sync commands in on_ready: {e}")
    # Auto-restore from the most recent JSON attachment in backup channel
    if AUTO_RESTORE_ON_START and BACKUP_CHANNEL_ID > 0:
        try:
            channel = bot.get_channel(BACKUP_CHANNEL_ID)
            if channel:
                async for msg in channel.history(limit=50):
                    if msg.attachments:
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.json'):
                                try:
                                    b = await att.read()
                                    payload = json.loads(b.decode('utf-8'))
                                    if isinstance(payload, dict) and key_manager.restore_from_payload(payload):
                                        print("♻️ Restored keys from channel backup")
                                        raise StopAsyncIteration
                                except Exception:
                                    pass
        except StopAsyncIteration:
            pass
        except Exception:
            pass

@bot.event
async def on_disconnect():
    try:
        await send_status_webhook('offline')
    except Exception:
        pass

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

    # Special admins always allowed
    if interaction.user.id in SPECIAL_ADMIN_IDS:
        return True

    # Commands that everyone can use
    public_commands = {
        "help", "activate", "keys", "info", "status", "activekeys", "expiredkeys",
        "sync", "synccommands"
    }
    cmd_name = None
    try:
        cmd_name = getattr(interaction.command, "name", None)
    except Exception:
        cmd_name = None

    if cmd_name in public_commands:
        return True

    # For all other commands, require admin role
    has_admin_role = ADMIN_ROLE_ID in [role.id for role in member.roles]
    if not has_admin_role:
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
    key = key_manager.generate_key(interaction.user.id, channel_id, duration_days)  # saved immediately; atomic and snapshotted
    
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
            
            # Send webhook notification (with IP if available)
            user_ip = None
            try:
                import os
                user_ip = os.getenv('SELF_IP')
            except Exception:
                user_ip = None
            await key_manager.send_webhook_notification(key, user_id, machine_id, ip=user_ip)
            
        else:
            await interaction.response.send_message(f"❌ **Activation Failed:** {result['error']}", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ **Error during activation:** {str(e)}", ephemeral=True)

# Removed duplicate sync command name to avoid conflicts
@bot.tree.command(name="syncduration", description="Sync your key duration with SelfBot")
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
        exp_ts = key_data.get('expiration_time')
        expires = "Not activated yet" if not exp_ts else f"<t:{exp_ts}:R>"
        
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
    embed.add_field(name="Created", value=("Not activated yet" if not key_data.get('activation_time') else f"<t:{key_data['activation_time']}:R>"), inline=True)
    embed.add_field(name="Expires", value=("Not activated yet" if not key_data.get('expiration_time') else f"<t:{key_data['expiration_time']}:R>"), inline=True)
    
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
    
    def list_block(items):
        if not items:
            return ["None"]
        lines = [f"`{i['key']}` - Expires <t:{i['expires']}:R>" for i in items]
        chunks = []
        current = ""
        for line in lines:
            if len(current) + len(line) + 1 > 1024:
                if current:
                    chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line
        if current:
            chunks.append(current)
        return chunks

    daily_keys = available_keys["daily"]
    for idx, chunk in enumerate(list_block(daily_keys), start=1):
        suffix = f" (part {idx})" if idx > 1 else ""
        embed.add_field(name=f"📅 Daily Keys ({len(daily_keys)}){suffix}", value=chunk, inline=False)

    weekly_keys = available_keys["weekly"]
    for idx, chunk in enumerate(list_block(weekly_keys), start=1):
        suffix = f" (part {idx})" if idx > 1 else ""
        embed.add_field(name=f"📅 Weekly Keys ({len(weekly_keys)}){suffix}", value=chunk, inline=False)

    monthly_keys = available_keys["monthly"]
    for idx, chunk in enumerate(list_block(monthly_keys), start=1):
        suffix = f" (part {idx})" if idx > 1 else ""
        embed.add_field(name=f"📅 Monthly Keys ({len(monthly_keys)}){suffix}", value=chunk, inline=False)

    lifetime_keys = available_keys["lifetime"]
    for idx, chunk in enumerate(list_block(lifetime_keys), start=1):
        suffix = f" (part {idx})" if idx > 1 else ""
        embed.add_field(name=f"📅 Lifetime Keys ({len(lifetime_keys)}){suffix}", value=chunk, inline=False)
    
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
            value=f"Duration: {duration} days\nCreated: {created_time}\nDele