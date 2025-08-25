import os
import io
import re
import json
import time
import uuid
import asyncio
import datetime
from typing import Optional, Dict

import requests
import discord
from discord import app_commands
from discord.ext import commands, tasks


# --------------------------- Configuration ---------------------------
GUILD_ID = int(os.getenv('GUILD_ID', '0') or 0)

DATA_DIR = os.getenv('DATA_DIR', '.')
os.makedirs(DATA_DIR, exist_ok=True)

KEYS_FILE = os.path.join(DATA_DIR, 'keys.json')
USAGE_FILE = os.path.join(DATA_DIR, 'key_usage.json')
DELETED_KEYS_FILE = os.path.join(DATA_DIR, 'deleted_keys.json')
LOGS_FILE = os.path.join(DATA_DIR, 'key_logs.json')
BACKUPS_DIR = os.path.join(DATA_DIR, 'backups')
os.makedirs(BACKUPS_DIR, exist_ok=True)

STATS_FILE = os.path.join(DATA_DIR, 'selfbot_message_stats.json')

BACKUP_WEBHOOK_URL = (os.getenv('BACKUP_WEBHOOK_URL', '') or '').strip()
BACKUP_CHANNEL_ID = int(os.getenv('BACKUP_CHANNEL_ID', '0') or 0)
AUTO_RESTORE_ON_START = (os.getenv('AUTO_RESTORE_ON_START', 'true').lower() in ('1', 'true', 'yes'))
try:
    BACKUP_INTERVAL_MIN = int(os.getenv('BACKUP_INTERVAL_MIN', '10') or 10)
except Exception:
    BACKUP_INTERVAL_MIN = 10

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
if not BOT_TOKEN:
    raise SystemExit('BOT_TOKEN is required')


# --------------------------- Key Manager ---------------------------
class KeyManager:
    def __init__(self) -> None:
        self.keys: Dict[str, dict] = {}
        self.key_usage: Dict[str, dict] = {}
        self.deleted_keys: Dict[str, dict] = {}
        self.key_logs: list[dict] = []
        self.load_data()

    def load_data(self) -> None:
        try:
            if os.path.exists(KEYS_FILE):
                with open(KEYS_FILE, 'r') as f:
                    self.keys = json.load(f) or {}
            if os.path.exists(USAGE_FILE):
                with open(USAGE_FILE, 'r') as f:
                    self.key_usage = json.load(f) or {}
            if os.path.exists(DELETED_KEYS_FILE):
                with open(DELETED_KEYS_FILE, 'r') as f:
                    self.deleted_keys = json.load(f) or {}
            if os.path.exists(LOGS_FILE):
                with open(LOGS_FILE, 'r') as f:
                    self.key_logs = json.load(f) or []
        except Exception:
            self.keys = {}
            self.key_usage = {}
            self.deleted_keys = {}
            self.key_logs = []

    def _atomic_write(self, path: str, data: dict) -> None:
        tmp = f"{path}.tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)

    def save_data(self) -> None:
        try:
            self._atomic_write(KEYS_FILE, self.keys)
            self._atomic_write(USAGE_FILE, self.key_usage)
            self._atomic_write(DELETED_KEYS_FILE, self.deleted_keys)
            self._atomic_write(LOGS_FILE, self.key_logs)
            # rolling snapshot
            ts = int(time.time())
            with open(os.path.join(BACKUPS_DIR, f"keys_{ts}.json"), 'w') as f:
                json.dump({'ts': ts, 'keys': self.keys, 'usage': self.key_usage, 'deleted': self.deleted_keys}, f, indent=2)
        except Exception:
            pass

    def add_log(self, action: str, key: str, user_id: Optional[int] = None, details: Optional[dict] = None) -> None:
        try:
            self.key_logs.append({
                'ts': int(time.time()),
                'action': action,
                'key': key,
                'user_id': user_id,
                'details': details or {}
            })
            self._atomic_write(LOGS_FILE, self.key_logs)
        except Exception:
            pass

    def build_backup_payload(self) -> dict:
        return {
            'timestamp': int(time.time()),
            'keys': self.keys,
            'usage': self.key_usage,
            'deleted': self.deleted_keys,
            'logs': self.key_logs,
        }

    def build_filtered_backup_payload(self) -> dict:
        try:
            active_keys = {k: v for k, v in (self.keys or {}).items() if v.get('is_active', False)}
            active_usage = {k: (self.key_usage.get(k) or {}) for k in active_keys.keys()}
        except Exception:
            active_keys = {}
            active_usage = {}
        return {'timestamp': int(time.time()), 'keys': active_keys, 'usage': active_usage}

    def generate_key(self, created_by: int, channel_id: Optional[int] = None, duration_days: int = 30) -> str:
        import random, string
        key = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(10, 12)))
        now = int(time.time())
        self.keys[key] = {
            'user_id': 0,
            'channel_id': channel_id,
            'created_time': now,
            'activation_time': None,
            'expiration_time': None,
            'duration_days': int(duration_days),
            'is_active': True,
            'machine_id': None,
            'activated_by': None,
            'created_by': int(created_by),
        }
        self.key_usage[key] = {'created': now, 'activated': None, 'last_used': None, 'usage_count': 0}
        self.save_data()
        self.add_log('generate', key, user_id=created_by, details={'duration_days': duration_days, 'channel_id': channel_id})
        # event backup
        try:
            if BACKUP_WEBHOOK_URL:
                data = json.dumps(self.build_filtered_backup_payload(), indent=2).encode()
                files = {'file': (f'backup_change_{int(time.time())}.json', data, 'application/json')}
                requests.post(BACKUP_WEBHOOK_URL, data={'content': 'Backup after key generation'}, files=files, timeout=10)
        except Exception:
            pass
        return key

    def activate_key(self, key: str, machine_id: str, user_id: int) -> Dict:
        key = (key or '').strip()
        if key not in self.keys:
            return {'success': False, 'error': 'Invalid key'}
        data = self.keys[key]
        if not data.get('is_active', False):
            return {'success': False, 'error': 'Access revoked'}
        if data.get('machine_id') and data.get('machine_id') != machine_id:
            return {'success': False, 'error': 'Key is already activated on another machine'}
        if data.get('expiration_time') and data['expiration_time'] < int(time.time()):
            return {'success': False, 'error': 'Key has expired'}
        now = int(time.time())
        data['machine_id'] = machine_id
        data['activated_by'] = int(user_id)
        data['user_id'] = int(user_id)
        if not data.get('activation_time'):
            data['activation_time'] = now
        if not data.get('expiration_time'):
            data['expiration_time'] = now + int(data.get('duration_days', 30)) * 24 * 60 * 60
        if key in self.key_usage:
            self.key_usage[key]['activated'] = now
            self.key_usage[key]['last_used'] = now
            self.key_usage[key]['usage_count'] = int(self.key_usage[key].get('usage_count', 0)) + 1
        self.save_data()
        self.add_log('activate', key, user_id=user_id, details={'machine_id': machine_id, 'expires': data.get('expiration_time')})
        # event backup
        try:
            if BACKUP_WEBHOOK_URL:
                b = json.dumps(self.build_filtered_backup_payload(), indent=2).encode()
                files = {'file': (f'backup_change_{int(time.time())}.json', b, 'application/json')}
                requests.post(BACKUP_WEBHOOK_URL, data={'content': 'Backup after key activation'}, files=files, timeout=10)
        except Exception:
            pass
        return {'success': True, 'expiration_time': data['expiration_time']}

    def restore_from_payload(self, payload: dict) -> bool:
        try:
            keys = payload.get('keys') or {}
            usage = payload.get('usage') or {}
            deleted = payload.get('deleted') or {}
            logs = payload.get('logs') or []
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


# --------------------------- Bot Setup ---------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
key_manager = KeyManager()


@tasks.loop(minutes=BACKUP_INTERVAL_MIN)
async def periodic_backup_task():
    if (BACKUP_CHANNEL_ID <= 0) and (not BACKUP_WEBHOOK_URL):
        return
    payload = key_manager.build_backup_payload()
    data = json.dumps(payload, indent=2).encode()
    filename = f"backup_{int(time.time())}.json"
    # channel upload
    if BACKUP_CHANNEL_ID > 0:
        try:
            ch = bot.get_channel(BACKUP_CHANNEL_ID)
            if ch:
                await ch.send(content='Automated backup', file=discord.File(io.BytesIO(data), filename=filename))
        except Exception:
            pass
    # webhook upload
    if BACKUP_WEBHOOK_URL:
        try:
            files = {'file': (filename, data, 'application/json')}
            requests.post(BACKUP_WEBHOOK_URL, data={'content': 'Automated backup'}, files=files, timeout=10)
        except Exception:
            pass


@bot.event
async def on_ready():
    print(f"✅ {bot.user} connected. Guilds: {len(bot.guilds)}")
    try:
        if not periodic_backup_task.is_running() and (BACKUP_CHANNEL_ID > 0 or BACKUP_WEBHOOK_URL):
            periodic_backup_task.start()
    except Exception:
        pass

    if AUTO_RESTORE_ON_START:
        # Try to derive channel from webhook if not set
        derived_channel_id = BACKUP_CHANNEL_ID
        if derived_channel_id <= 0 and BACKUP_WEBHOOK_URL:
            try:
                m = re.search(r"/webhooks/(\d+)/", BACKUP_WEBHOOK_URL)
                if m:
                    wid = int(m.group(1))
                    try:
                        wh = await bot.fetch_webhook(wid)
                        if getattr(wh, 'channel_id', None):
                            derived_channel_id = int(wh.channel_id)
                    except Exception:
                        pass
            except Exception:
                pass
        # Restore from channel
        if derived_channel_id > 0:
            try:
                ch = bot.get_channel(derived_channel_id)
                if ch:
                    async for msg in ch.history(limit=50):
                        for att in msg.attachments:
                            if att.filename.lower().endswith('.json'):
                                try:
                                    raw = await att.read()
                                    payload = json.loads(raw.decode('utf-8'))
                                    if isinstance(payload, dict) and key_manager.restore_from_payload(payload):
                                        print('♻️ Restored keys from channel backup')
                                        raise StopAsyncIteration
                                except Exception:
                                    pass
            except StopAsyncIteration:
                pass
            except Exception:
                pass
        # Fallback: local latest
        try:
            latest = None
            latest_ts = -1
            for name in os.listdir(BACKUPS_DIR):
                if name.startswith('keys_') and name.endswith('.json'):
                    ts = name[5:-5]
                    if ts.isdigit():
                        v = int(ts)
                        if v > latest_ts:
                            latest_ts = v
                            latest = os.path.join(BACKUPS_DIR, name)
            if latest:
                with open(latest, 'r') as f:
                    payload = json.load(f)
                if isinstance(payload, dict) and key_manager.restore_from_payload(payload):
                    print(f'♻️ Restored keys from local backup: {latest}')
        except Exception:
            pass


# --------------------------- Commands ---------------------------
@app_commands.guilds(discord.Object(id=GUILD_ID) if GUILD_ID else None)
@bot.tree.command(name='leaderboard', description='Show the top 10 users by selfbot messages')
async def leaderboard(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        stats: Dict[str, int]
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    stats = json.load(f) or {}
            else:
                stats = {}
        except Exception:
            stats = {}
        top = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)[:10]
        if not top:
            await interaction.followup.send('No stats yet.')
            return
        em = discord.Embed(title='Selfbot Leaderboard', color=0x5a3e99)
        lines = []
        rank = 1
        for uid, cnt in top:
            try:
                user = await bot.fetch_user(int(uid))
                name = f"{user.name}#{user.discriminator}" if user else uid
            except Exception:
                name = uid
            lines.append(f"**{rank}.** {name} — {cnt}")
            rank += 1
        em.description = "\n".join(lines)
        await interaction.followup.send(embed=em)
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f'Error: {e}')
        else:
            await interaction.response.send_message(f'Error: {e}', ephemeral=True)


def main() -> None:
    bot.run(BOT_TOKEN)


if __name__ == '__main__':
    main()

