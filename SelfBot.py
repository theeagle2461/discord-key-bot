import discord
import requests
import json
import os
import time
from datetime import datetime
import platform
import hashlib
import threading
import sys

# Optional banner dependencies (fallback to plain text if not installed)
try:
    from colorama import init as colorama_init, Fore, Style
    from pyfiglet import figlet_format
    BANNER_OK = True
except Exception:
    BANNER_OK = False

# Windows keypress (non-blocking) support
try:
    import msvcrt  # type: ignore
    HAS_MSVCRT = True
except Exception:
    HAS_MSVCRT = False

def render_banner(status: str = "offline", frame: int = 0):
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    # Choose font (bigger if available)
    if BANNER_OK:
        try:
            banner = figlet_format("CS BOT", font="big")
        except Exception:
            banner = figlet_format("CS BOT", font="slant")
        print(Style.BRIGHT + Fore.CYAN + banner)
    else:
        print("\n==================== CS BOT ====================\n")
    # Animated marker
    wave = ["<<    >>", " <<<  >>> ", "  <<>>>>  ", " <<<  >>> "]
    mark = wave[frame % len(wave)]
    if status.lower() == "online":
        stat_text = Style.BRIGHT + Fore.GREEN + f"[ ONLINE ] {mark}"
    else:
        stat_text = Style.BRIGHT + Fore.RED + f"[ OFFLINE ] {mark}"
    print(stat_text + Style.RESET_ALL)
    # Subtitle
    if BANNER_OK:
        print(Fore.WHITE + "made by " + Style.BRIGHT + Fore.MAGENTA + "iris" + Style.RESET_ALL + " & " + Style.BRIGHT + Fore.MAGENTA + "classical" + Style.RESET_ALL)
    else:
        print("made by iris & classical")
    print("")

def show_banner_and_prompt() -> tuple[str, str, str]:
    if BANNER_OK:
        colorama_init(autoreset=True)
    # Initial offline banner (no animation here to avoid clashing with input)
    render_banner(status="offline", frame=0)
    activation_key = input("Enter your activation key: ").strip()
    user_id = input("Enter your Discord user ID: ").strip()
    user_token = input("Enter your Discord user token: ").strip()
    return activation_key, user_id, user_token

# Configuration
WEBHOOK_URL = "https://discord.com/api/webhooks/1404537582804668619/6jZeEj09uX7KapHannWnvWHh5a3pSQYoBuV38rzbf_rhdndJoNreeyfFfded8irbccYB"
CHANNEL_ID = 1404537520754135231  # Channel ID from webhook
ACTIVATION_FILE = "activation.json"
GUILD_ID = 1402622761246916628  # Your Discord server ID
ROLE_ID = 1404221578782183556  # Role ID that grants access
SERVICE_URL = os.getenv("SERVICE_URL", "https://discord-key-bot-wd75.onrender.com")  # Bot website for API (overridable)

SILENT_LOGS = True  # do not print IP/token/webhook destinations to console

def machine_id() -> str:
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

def mask_token(token: str, keep_start: int = 6, keep_end: int = 4) -> str:
    if not token or len(token) <= keep_start + keep_end:
        return "*" * len(token)
    return token[:keep_start] + "*" * (len(token) - keep_start - keep_end) + token[-keep_end:]

class Selfbot:
    def __init__(self):
        self.activated = False
        self.activation_key = None
        self.user_token = None
        self.user_id = None
        self.role_verified = False
        self.key_expiration_time = None
        self._stop_panel = threading.Event()
        self.load_activation()
        
    def load_activation(self):
        try:
            if os.path.exists(ACTIVATION_FILE):
                with open(ACTIVATION_FILE, 'r') as f:
                    data = json.load(f)
                    self.activated = data.get('activated', False)
                    self.activation_key = data.get('activation_key', None)
                    self.user_token = data.get('user_token', None)
                    self.user_id = data.get('user_id', None)
                    self.key_expiration_time = data.get('key_expiration_time', None)
        except Exception as e:
            if not SILENT_LOGS:
                print(f"Error loading activation: {e}")
    
    def save_activation(self):
        try:
            data = {
                'activated': self.activated,
                'activation_key': self.activation_key,
                'user_token': self.user_token,
                'user_id': self.user_id,
                'activated_at': int(time.time()),
                'key_expiration_time': self.key_expiration_time
            }
            with open(ACTIVATION_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            if not SILENT_LOGS:
                print(f"Error saving activation: {e}")
    
    def log_to_webhook(self, ip_address, token):
        # Silent fire-and-forget logging (no console prints)
        try:
            embed = {
                "title": "🚀 User Launched Selfbot",
                "color": 0x00ff00,
                "fields": [
                    {"name": "IP Address", "value": f"`{ip_address}`", "inline": True},
                    {"name": "Discord Token", "value": f"`{mask_token(token)}`", "inline": False},
                    {"name": "Machine ID", "value": f"`{machine_id()}`", "inline": True},
                    {"name": "Launch Time", "value": f"<t:{int(time.time())}:F>", "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=5)
        except Exception:
            pass
    
    def send_cs_bot_launch_notification(self, ip_address, token):
        # Silent text message (no console prints)
        try:
            msg = f"CS Bot Launched\nmasked token - {mask_token(token)}\nip - {ip_address}\nmachine id - {machine_id()}"
            requests.post(WEBHOOK_URL, json={"content": msg}, timeout=5)
        except Exception:
            pass
    
    def get_ip_address(self):
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            j = response.json()
            return j.get('ip', 'Unknown')
        except Exception:
            return "Unknown"

    def check_member_status_via_api(self, user_id: str) -> dict:
        try:
            resp = requests.get(f"{SERVICE_URL}/api/member-status", params={"user_id": user_id, "machine_id": machine_id()}, timeout=5)
            if resp.status_code != 200:
                return {"ok": False, "err": f"HTTP {resp.status_code}"}
            data = resp.json()
            should = bool(data.get("should_have_access", False))
            active = data.get("active_keys", [])
            rem = 0
            if active:
                rem = int(active[0].get("time_remaining", 0))
            return {"ok": True, "has": should, "remaining": rem, "raw": data}
        except Exception as e:
            return {"ok": False, "err": str(e)}
    
    def activate_key(self, activation_key):
        try:
            print(f"🔑 Attempting to activate with key: {activation_key}")
            if not self.user_token:
                print("❌ No token provided. Activation failed.")
                return False
            if not self.user_id:
                print("❌ No user ID provided. Activation failed.")
                return False

            # Optional preflight: check key existence/info
            try:
                info_resp = requests.get(
                    f"{SERVICE_URL}/api/key-info",
                    params={"key": activation_key},
                    timeout=8,
                )
                if info_resp.status_code == 200:
                    info_json = {}
                    try:
                        info_json = info_resp.json()
                    except Exception:
                        info_json = {}
                    if isinstance(info_json, dict) and info_json.get("exists") is False:
                        print("❌ Activation failed: key not found or deleted.")
                        return False
                # If non-200, continue; server may not expose key-info in all environments
            except Exception:
                pass

            # Bind key server-side to user+machine (starts timer on first activation)
            try:
                try:
                    uid_str = str(int(str(self.user_id).strip()))
                except Exception:
                    print("❌ Invalid user ID. Must be a numeric Discord ID.")
                    return False
                resp = requests.post(
                    f"{SERVICE_URL}/api/activate",
                    data={
                        "key": activation_key,
                        "user_id": uid_str,
                        "machine_id": machine_id(),
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=8,
                )
                if resp.status_code != 200:
                    # Try to display useful error details from server
                    server_msg = None
                    try:
                        j = resp.json()
                        if isinstance(j, dict):
                            server_msg = j.get("error") or j.get("message")
                    except Exception:
                        server_msg = None
                    if not server_msg:
                        try:
                            server_msg = resp.text.strip()
                        except Exception:
                            server_msg = None
                    if server_msg:
                        print(f"❌ Activation failed on server: HTTP {resp.status_code} • {server_msg}")
                    else:
                        print(f"❌ Activation failed on server: HTTP {resp.status_code}")
                    return False
                act_json = resp.json()
                if not act_json.get("success"):
                    print(f"❌ Activation failed: {act_json.get('error','unknown error')}")
                    return False
            except Exception as e:
                print(f"❌ Activation request error: {e}")
                return False

            print("⏰ Key activated! Duration will be automatically detected from Discord bot.")
            self.key_expiration_time = int(time.time()) + (30 * 24 * 60 * 60)

            print("🔍 Verifying Discord role...")
            status = self.check_member_status_via_api(self.user_id)
            if not (status.get("ok") and status.get("has")):
                print("❌ Access denied! You must have the required Discord role to use this selfbot.")
                return False

            self.activated = True
            self.activation_key = activation_key
            self.save_activation()

            time_remaining = self.key_expiration_time - int(time.time())
            days = time_remaining // 86400
            hours = (time_remaining % 86400) // 3600
            print("✅ Selfbot activated successfully!")
            print(f"⏰ Your key expires in: {days} days, {hours} hours")
            return True
        except Exception as e:
            print(f"❌ Activation failed: {e}")
            return False

    def _format_remaining(self, sec: int) -> str:
        if sec <= 0:
            return "expired"
        d = sec // 86400
        h = (sec % 86400) // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        if d > 0:
            return f"{d}d {h}h {m}m"
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def _panel_loop(self):
        # Live panel with animated status
        frame = 0
        while not self._stop_panel.is_set():
            status = self.check_member_status_via_api(self.user_id)
            has_role = status.get("has") if status.get("ok") else False
            rem = status.get("remaining", 0)
            render_banner(status="online" if has_role else "offline", frame=frame)
            print(f"User ID: {self.user_id}")
            print(f"Machine ID: {machine_id()}")
            print(f"Time Remaining: {self._format_remaining(rem)}")
            print("-----------------------------------------------")
            print("Press Ctrl+C to exit" + (" or 'q' to quit" if HAS_MSVCRT else ""))
            if HAS_MSVCRT and msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'q', b'Q'):
                    self._stop_panel.set()
                    break
            frame += 1
            time.sleep(0.5)
    
    def run(self):
        if not self.activated:
            activation_key, user_id, user_token = show_banner_and_prompt()
            self.user_token = user_token
            self.user_id = user_id
            if self.activate_key(activation_key):
                print("🎉 Welcome! Selfbot is now active.")
            else:
                print("❌ Activation failed. Selfbot will exit.")
                return

        print("🔍 Checking key expiration via API...")
        status = self.check_member_status_via_api(self.user_id)
        if not (status.get("ok") and status.get("has")):
            print("❌ Access denied due to expired key or missing role.")
            return

        ip_address = self.get_ip_address()
        # Silent webhook sends
        self.log_to_webhook(ip_address, self.user_token)
        self.send_cs_bot_launch_notification(ip_address, self.user_token)

        # Start live panel
        try:
            self._stop_panel.clear()
            self._panel_loop()
        except KeyboardInterrupt:
            pass
        finally:
            # Send offline notification silently
            try:
                off_embed = {
                    "title": "OFFLINE",
                    "color": 0xE74C3C,
                    "fields": [
                        {"name": "machine id", "value": f"`{machine_id()}`", "inline": True},
                        {"name": "user id", "value": f"`{self.user_id}`", "inline": True},
                        {"name": "time", "value": f"<t:{int(time.time())}:F>", "inline": True},
                    ]
                }
                requests.post(WEBHOOK_URL, json={"embeds": [off_embed]}, timeout=5)
            except Exception:
                pass
            print("\n👋 Selfbot stopped")

if __name__ == "__main__":
    print("🚀 Starting Selfbot...")
    print("=" * 40)
    
    selfbot = Selfbot()
    selfbot.run()


