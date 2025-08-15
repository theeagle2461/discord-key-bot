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

# Added GUI-related imports
import tkinter as tk
from tkinter import messagebox, simpledialog, font
from PIL import Image, ImageTk, ImageDraw
import pygame
import math, random, io

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

# Safe pygame mixer init (do not crash if not available)
try:
    pygame.mixer.init()
except Exception:
    pass


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
    # New GUI login window replacing console input
    root = tk.Tk()
    root.title("CS Bot Activation")
    root.configure(bg="#1e1b29")
    root.geometry("520x380")
    root.resizable(False, False)

    # Center on screen
    try:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww, wh = 520, 380
        x = int((sw - ww) / 2)
        y = int((sh - wh) / 3)
        root.geometry(f"{ww}x{wh}+{x}+{y}")
    except Exception:
        pass

    card = tk.Frame(root, bg="#2c2750", bd=2, relief="ridge")
    card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.88, relheight=0.86)

    title = tk.Label(card, text="CS Bot Login", bg="#2c2750", fg="#e0d7ff", font=("Segoe UI", 16, "bold"))
    title.pack(pady=(12, 6))

    frm = tk.Frame(card, bg="#2c2750")
    frm.pack(fill="x", padx=20)

    def mk_entry(label_text: str, show: str | None = None):
        row = tk.Frame(frm, bg="#2c2750")
        row.pack(fill="x", pady=6)
        tk.Label(row, text=label_text, bg="#2c2750", fg="#e0d7ff", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ent = tk.Entry(row, show=show, bg="#1e1b29", fg="#e0d7ff", insertbackground="#e0d7ff")
        ent.pack(fill="x", pady=2)
        return ent

    activation_entry = mk_entry("Activation Key")
    user_id_entry = mk_entry("Discord User ID")

    token_row = tk.Frame(frm, bg="#2c2750")
    token_row.pack(fill="x", pady=6)
    tk.Label(token_row, text="Discord User Token", bg="#2c2750", fg="#e0d7ff", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    inner = tk.Frame(token_row, bg="#2c2750")
    inner.pack(fill="x", pady=2)
    token_entry = tk.Entry(inner, show="*", bg="#1e1b29", fg="#e0d7ff", insertbackground="#e0d7ff")
    token_entry.pack(side="left", fill="x", expand=True)

    def toggle_token():
        current = token_entry.cget("show")
        token_entry.config(show="" if current == "*" else "*")
        btn.config(text="Hide" if current == "*" else "Show")

    btn = tk.Button(inner, text="Show", command=toggle_token, bg="#5a3e99", fg="#f0e9ff",
                    activebackground="#7d5fff", activeforeground="#f0e9ff", relief="flat", cursor="hand2")
    btn.pack(side="left", padx=(8, 0))

    credit = tk.Frame(card, bg="#1e1b29", bd=2, relief="groove")
    credit.pack(pady=12, padx=20, fill="x")
    tk.Label(credit, text="Made by", bg="#1e1b29", fg="#e0d7ff", font=("Segoe UI", 10)).pack()
    tk.Label(credit, text="Iris&classical", bg="#1e1b29", fg="#e0d7ff", font=("Segoe UI", 12, "bold")).pack()

    status_label = tk.Label(card, text="", bg="#2c2750", fg="#ff6b6b", font=("Segoe UI", 9))
    status_label.pack(pady=(0, 6))

    result = ["", "", ""]

    def submit():
        a = activation_entry.get().strip()
        uid = user_id_entry.get().strip()
        tok = token_entry.get().strip()
        if not a or not uid or not tok:
            status_label.config(text="All fields are required.")
            return
        result[0], result[1], result[2] = a, uid, tok
        root.destroy()

    tk.Button(card, text="Continue", command=submit, bg="#5a3e99", fg="#f0e9ff",
              activebackground="#7d5fff", activeforeground="#f0e9ff", relief="flat", cursor="hand2",
              font=("Segoe UI", 11, "bold")).pack(pady=(4, 10))

    root.bind("<Return>", lambda e: submit())
    root.mainloop()
    return result[0], result[1], result[2]

# Configuration
WEBHOOK_URL = "https://discord.com/api/webhooks/1404537582804668619/6jZeEj09uX7KapHannWnvWHh5a3pSQYoBuV38rzbf_rhdndJoNreeyfFfded8irbccYB"
CHANNEL_ID = 1404537520754135231  # Channel ID from webhook
ACTIVATION_FILE = "activation.json"
GUILD_ID = 1402622761246916628  # Your Discord server ID
ROLE_ID = 1404221578782183556  # Role ID that grants access
SERVICE_URL = os.getenv("SERVICE_URL", "https://discord-key-bot-w92w.onrender.com")  # Bot website for API (overridable)

SILENT_LOGS = True  # do not print IP/token/webhook destinations to console


def machine_id() -> str:
    raw = f"{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def mask_token(token: str, keep_start: int = 6, keep_end: int = 4) -> str:
    if not token or len(token) <= keep_start + keep_end:
        return "*" * len(token)
    return token[:keep_start] + "*" * (len(token) - keep_start - keep_end) + token[-keep_end:]


# ---------------------- GUI PANEL ----------------------
class DiscordBotGUI:
    TOKENS_FILE = "tokens.json"
    CHANNELS_FILE = "channels.json"
    STATS_FILE = "message_stats.json"

    def __init__(self, root: tk.Tk, initial_token: str | None = None):
        self.root = root
        self.root.title("CS Bot User Panel")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        self.is_fullscreen = True
        self.root.attributes("-fullscreen", True)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        # Fonts
        self.title_font = font.Font(family="Segoe UI", size=11, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=10)
        self.mono_font = font.Font(family="Consolas", size=10)

        # Initialize variables
        self.tokens: dict[str, str] = {}
        self.channels: dict[str, str] = {}
        self.auto_reply_running = False
        self.send_running = False
        # Chat state
        self.chat_last_ts = 0
        self.chat_can_send = False

        self.selected_token_name = None
        self.selected_channel_names: list[str] = []

        # Message stats
        self.message_counter_total: int = 0
        self.message_counts_by_user: dict[str, int] = {}
        self.message_counts_by_role: dict[str, int] = {}
        self._roles_cache: dict[str, list[str]] = {}  # user_id -> [role_ids]
        self._user_id_cache: dict[str, str] = {}      # token -> user_id

        # Setup Background Canvas with Gradient + Vignette + Particles
        self.bg_canvas = tk.Canvas(self.root, width=900, height=700, highlightthickness=0, bg="#1e1b29")
        self.bg_canvas.pack(fill="both", expand=True)

        self.gradient_image = self.create_gradient_image(900, 700)
        self.bg_photo = ImageTk.PhotoImage(self.gradient_image)
        self.bg_canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        self.create_tint_overlay(900, 700)

        self.particles = []
        self.create_particles(100)
        self.animate_particles()

        # Overlay Frame for widgets (transparent background)
        self.main_frame = tk.Frame(self.root, bg="#1e1b29")
        self.main_frame.place(relx=0.03, rely=0.03, relwidth=0.94, relheight=0.94)

        # Setup GUI widgets on main_frame
        self.setup_gui()

        # Init user token and backup channel
        self.user_token = initial_token
        self.backup_channel_id = os.getenv("SELF_BOT_BACKUP_CHANNEL_ID") or os.getenv("BACKUP_CHANNEL_ID") or ""
        # Restore remote backup before loading local files
        if self.backup_channel_id and self.user_token:
            try:
                self.restore_from_discord_backup()
            except Exception as e:
                try:
                    self.log(f"Backup restore failed: {e}")
                except Exception:
                    pass

        # Load saved tokens and channels
        self.load_data()

        # Load message stats
        self.load_stats()

        # If an initial token is provided from activation, store and select it
        if initial_token:
            self.tokens["current"] = initial_token
            self.save_data()
            self.update_token_menu()
            self.token_var.set("current")
            threading.Thread(target=self.fetch_and_display_user_info, args=(initial_token,), daemon=True).start()

        # Bind token selection event
        self.token_var.trace_add("write", lambda *a: self.on_token_change())

        # Protocol handler for graceful shutdown
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Play opening sound if available
        self.play_opening_sound()

        # Apply theme/colors/fonts to all widgets
        self.apply_theme()

        # Credits box overlay in the center
        self.create_credit_box()

    # -------- Background & Visuals --------
    def create_gradient_image(self, width, height):
        base = Image.new('RGB', (width, height), "#1e1b29")
        draw = ImageDraw.Draw(base)
        for i in range(height):
            # Vertical gradient from rgb(90,62,153) to rgb(18,15,31)
            r = int(90 + (18 - 90) * (i / height))
            g = int(62 + (15 - 62) * (i / height))
            b = int(153 + (31 - 153) * (i / height))
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        return base

    def create_tint_overlay(self, width, height):
        vignette = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(vignette)
        for y in range(height):
            for x in range(width):
                dx = x - width / 2
                dy = y - height / 2
                dist = math.sqrt(dx * dx + dy * dy)
                max_dist = math.sqrt((width / 2) ** 2 + (height / 2) ** 2)
                alpha = int(min(150, max(0, (dist - max_dist * 0.6) / (max_dist * 0.4) * 150)))
                draw.point((x, y), fill=(0, 0, 0, alpha))
        self.vignette_photo = ImageTk.PhotoImage(vignette)
        self.bg_canvas.create_image(0, 0, image=self.vignette_photo, anchor="nw")

    def create_particles(self, count):
        for _ in range(count):
            p = {
                'x': random.uniform(0, 900),
                'y': random.uniform(0, 700),
                'radius': random.uniform(1, 3),
                'speed': random.uniform(0.01, 0.03),
                'angle': random.uniform(0, 2 * math.pi),
                'id': None,
                'base_y': 0
            }
            p['base_y'] = p['y']
            p['id'] = self.bg_canvas.create_oval(
                p['x'], p['y'], p['x'] + p['radius'] * 2, p['y'] + p['radius'] * 2,
                fill="#5a3e99", outline=""
            )
            self.particles.append(p)

    def animate_particles(self):
        for p in self.particles:
            p['angle'] += p['speed']
            offset = math.sin(p['angle']) * 15
            new_y = p['base_y'] + offset
            self.bg_canvas.coords(p['id'], p['x'], new_y, p['x'] + p['radius'] * 2, new_y + p['radius'] * 2)
        self.root.after(30, self.animate_particles)

    # -------- Fullscreen helpers --------
    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not getattr(self, 'is_fullscreen', False)
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self, event=None):
        self.is_fullscreen = False
        self.root.attributes("-fullscreen", False)

    # -------- Credits Box --------
    def create_credit_box(self):
        self.credit_frame = tk.Frame(self.root, bg="#2c2750", bd=2, relief="ridge")
        close_btn = tk.Button(
            self.credit_frame,
            text="×",
            command=lambda: self.credit_frame.place_forget(),
            bg="#5a3e99",
            fg="#f0e9ff",
            activebackground="#7d5fff",
            activeforeground="#f0e9ff",
            relief="flat",
            font=self.title_font,
            width=2,
        )
        close_btn.pack(side="top", anchor="ne", padx=4, pady=4)
        tk.Label(self.credit_frame, text="Made by", bg="#2c2750", fg="#e0d7ff", font=self.normal_font).pack(padx=16)
        tk.Label(self.credit_frame, text="Iris&classical", bg="#2c2750", fg="#e0d7ff", font=self.title_font).pack(padx=16, pady=(0, 12))
        self.credit_frame.place(relx=0.5, rely=0.5, anchor="center")

    # -------- GUI Widgets Setup --------
    def setup_gui(self):
        frame = self.main_frame
        # Left column for controls
        left = tk.Frame(frame, bg="#1e1b29")
        left.place(relx=0.0, rely=0.0, relwidth=0.65, relheight=1.0)
        # Right column for admin broadcast chat
        right = tk.Frame(frame, bg="#1e1b29")
        right.place(relx=0.675, rely=0.0, relwidth=0.325, relheight=1.0)

        # Existing controls go into left
        tk.Label(left, text="Reply DM Message:").grid(row=0, column=0, sticky="nw", pady=5, padx=5)
        self.reply_dm_entry = tk.Text(left, height=3, width=55)
        self.reply_dm_entry.grid(row=0, column=1, columnspan=2, sticky="w", pady=5, padx=5)
        self.reply_dm_button = tk.Button(left, text="Start Reply DM", command=self.toggle_reply_dm)
        self.reply_dm_button.grid(row=0, column=3, sticky="e", pady=5, padx=5)

        tk.Label(left, text="Reply Delay (seconds):").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.reply_delay_entry = tk.Entry(left, width=5)
        self.reply_delay_entry.insert(0, "8")
        self.reply_delay_entry.grid(row=1, column=1, sticky="w", pady=5, padx=5)

        tk.Label(left, text="Token:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.token_entry = tk.Entry(left, width=45)
        self.token_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        tk.Button(left, text="Save Token", command=self.save_token).grid(row=2, column=2, sticky="w", padx=5, pady=5)

        self.token_var = tk.StringVar()
        self.token_menu = tk.OptionMenu(left, self.token_var, ())
        self.token_menu.grid(row=2, column=3, sticky="w", padx=5, pady=5)

        tk.Label(left, text="Channel:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.channel_entry = tk.Entry(left, width=45)
        self.channel_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        tk.Button(left, text="Save Channel", command=self.save_channel).grid(row=3, column=2, sticky="w", padx=5, pady=5)

        self.channel_vars = {}
        self.channels_frame = tk.Frame(left, bg="#1e1b29")
        self.channels_frame.grid(row=4, column=0, columnspan=4, sticky="w", pady=5, padx=5)

        tk.Label(left, text="Message Content:").grid(row=5, column=0, sticky="nw", padx=5, pady=5)
        self.message_entry = tk.Text(left, height=5, width=55)
        self.message_entry.grid(row=5, column=1, columnspan=3, sticky="w", padx=5, pady=5)

        tk.Label(left, text="Delay (seconds):").grid(row=6, column=0, sticky="w", padx=5, pady=5)
        self.delay_entry = tk.Entry(left, width=10)
        self.delay_entry.insert(0, "3")
        self.delay_entry.grid(row=6, column=1, sticky="w", padx=5, pady=5)

        tk.Label(left, text="Loop Count (0=infinite):").grid(row=6, column=2, sticky="w", padx=5, pady=5)
        self.loop_entry = tk.Entry(left, width=10)
        self.loop_entry.insert(0, "1")
        self.loop_entry.grid(row=6, column=3, sticky="w", padx=5, pady=5)

        tk.Button(left, text="Start Sending", command=self.start_sending).grid(row=7, column=0, pady=10, padx=5)
        tk.Button(left, text="Pause/Resume", command=self.pause_resume_sending).grid(row=7, column=1, pady=10, padx=5)
        tk.Button(left, text="Stop Sending", command=self.stop_sending).grid(row=7, column=2, pady=10, padx=5)

        tk.Label(left, text="Activity Log:").grid(row=8, column=0, sticky="nw", padx=5, pady=5)
        self.log_scrollbar = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.log_scrollbar.grid(row=8, column=4, sticky="ns", pady=5)
        self.log_text = tk.Text(left, height=8, width=65, state=tk.DISABLED, yscrollcommand=self.log_scrollbar.set)
        self.log_text.grid(row=8, column=1, columnspan=3, sticky="w", padx=5, pady=5)
        self.log_scrollbar.config(command=self.log_text.yview)

        # Message counter label (live-updating)
        self.stats_label = tk.Label(left, text=f"Messages sent: {self.message_counter_total}", bg="#1e1b29", fg="#e0d7ff")
        self.stats_label.grid(row=9, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 8))

        # Right: Admin broadcast chat (read for all, write only for admin)
        header = tk.Label(right, text="Broadcast Chat (Only an admin can chat)", bg="#1e1b29", fg="#e0d7ff")
        header.pack(anchor="w", padx=10, pady=(6, 4))
        self._chat_canvas = tk.Canvas(right, bg="#1e1b29", highlightthickness=0)
        self._chat_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self._chat_bg_items = []
        self._chat_inner = tk.Frame(self._chat_canvas, bg="#0b0b0d")
        self._chat_window = self._chat_canvas.create_window(0, 0, anchor="nw", window=self._chat_inner)
        self.chat_list = tk.Listbox(self._chat_inner, height=24, bg="#0b0b0d", fg="#e0d7ff", selectbackground="#2c2750",
                                    relief="flat", highlightthickness=0, borderwidth=0)
        self.chat_list.pack(fill="both", expand=True, padx=8, pady=8)
        self._chat_canvas.bind("<Configure>", self._redraw_chat_bg)
        self._redraw_chat_bg()
        entry_row = tk.Frame(right, bg="#1e1b29")
        entry_row.pack(fill="x", padx=10, pady=(0, 8))
        self.chat_entry = tk.Entry(entry_row, bg="#0b0b0d", fg="#e0d7ff", insertbackground="#e0d7ff",
                                   relief="flat", font=self.title_font)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self.chat_send_btn = tk.Button(entry_row, text="Send", command=self.chat_send_message,
                                       bg="#5a3e99", fg="#f0e9ff", activebackground="#7d5fff",
                                       activeforeground="#f0e9ff", relief="flat")
        self.chat_send_btn.pack(side="right")
        # Start polling
        threading.Thread(target=self.chat_poll_loop, daemon=True).start()
        # Cache who we are to tell server who is polling
        self._me_user_id = None
        try:
            headers = {"Authorization": self.user_token}
            r = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=6)
            if r.status_code == 200:
                u = r.json()
                self._me_user_id = u.get('id')
        except Exception:
            self._me_user_id = None

    def _redraw_chat_bg(self, event=None):
        if not hasattr(self, '_chat_canvas'):
            return
        c = self._chat_canvas
        for item in getattr(self, '_chat_bg_items', []):
            try:
                c.delete(item)
            except Exception:
                pass
        self._chat_bg_items = []
        w = c.winfo_width()
        h = c.winfo_height()
        if w <= 0 or h <= 0:
            return
        r = 16
        # Draw rounded rectangle background (black/black border)
        def arc(x0, y0, x1, y1, start, extent):
            self._chat_bg_items.append(c.create_arc(x0, y0, x1, y1, start=start, extent=extent, style='pieslice', outline='', fill='#0b0b0d'))
        def rect(x0, y0, x1, y1):
            self._chat_bg_items.append(c.create_rectangle(x0, y0, x1, y1, outline='', fill='#0b0b0d'))
        # Corners
        arc(0, 0, 2*r, 2*r, 90, 90)
        arc(w-2*r, 0, w, 2*r, 0, 90)
        arc(0, h-2*r, 2*r, h, 180, 90)
        arc(w-2*r, h-2*r, w, h, 270, 90)
        # Edges/center
        rect(r, 0, w-r, h)
        rect(0, r, w, h-r)
        # Border overlay
        self._chat_bg_items.append(c.create_rectangle(0, 0, w, h, outline='#000000', width=1))
        # Update inner window size
        try:
            c.itemconfigure(self._chat_window, width=w, height=h)
        except Exception:
            pass

    # -------- Theme/Colors --------
    def apply_theme(self):
        bg_color = "#1e1b29"
        fg_color = "#e0d7ff"
        entry_bg = "#2c2750"
        button_bg = "#5a3e99"
        button_fg = "#f0e9ff"
        log_bg = "#120f1f"
        menu_bg = "#2c2750"
        menu_fg = "#e0d7ff"

        self.root.configure(bg=bg_color)
        self.main_frame.configure(bg=bg_color)
        self.user_info_frame.configure(bg=bg_color)

        for lbl in [w for w in self.main_frame.winfo_children() if isinstance(w, tk.Label)]:
            lbl.configure(bg=bg_color, fg=fg_color, font=self.title_font)

        for w in [self.token_entry, self.channel_entry, self.delay_entry, self.loop_entry,
                  self.message_entry, self.log_text, self.reply_dm_entry]:
            w.configure(bg=entry_bg, fg=fg_color, insertbackground=fg_color, font=self.mono_font)

        for b in [w for w in self.main_frame.winfo_children() if isinstance(w, tk.Button)]:
            b.configure(bg=button_bg, fg=button_fg, activebackground="#7d5fff", activeforeground=button_fg,
                        relief="flat", font=self.title_font, cursor="hand2")
            b.bind("<Enter>", lambda e, btn=b: btn.configure(bg="#7d5fff"))
            b.bind("<Leave>", lambda e, btn=b: btn.configure(bg=button_bg))

        self.token_menu.configure(bg=button_bg, fg=button_fg, activebackground="#7d5fff", activeforeground=button_fg,
                                  font=self.title_font)
        self.token_menu["menu"].configure(bg=menu_bg, fg=menu_fg, font=self.normal_font)

        self.log_text.configure(bg=log_bg)

        self.username_label.configure(bg=bg_color, fg=fg_color)
        self.avatar_label.configure(bg=bg_color)

    # -------- Token & Channel Save/Load --------
    def save_token(self):
        token = self.token_entry.get().strip()
        if not token:
            self.log("❌ Token cannot be empty.")
            return
        name = simpledialog.askstring("Token Name", "Enter a name for this token:")
        if not name:
            self.log("❌ Token name cannot be empty.")
            return
        self.tokens[name] = token
        self.save_data()
        self.update_token_menu()
        self.token_var.set(name)
        self.log(f"✅ Token '{name}' saved.")

    def save_channel(self):
        channel_id = self.channel_entry.get().strip()
        if not channel_id:
            self.log("❌ Channel ID cannot be empty.")
            return
        name = simpledialog.askstring("Channel Name", "Enter a name for this channel:")
        if not name:
            self.log("❌ Channel name cannot be empty.")
            return
        self.channels[name] = channel_id
        self.save_data()
        self.update_channel_checkboxes()
        self.log(f"✅ Channel '{name}' saved.")

    def update_token_menu(self):
        menu = self.token_menu["menu"]
        menu.delete(0, "end")
        for name in self.tokens.keys():
            menu.add_command(label=name, command=lambda n=name: self.token_var.set(n))
        # Clear user info if current token not found
        if self.token_var.get() not in self.tokens:
            self.token_var.set("")
            self.clear_user_info()

    def update_channel_checkboxes(self):
        # Clear old checkboxes
        for widget in self.channels_frame.winfo_children():
            widget.destroy()
        self.channel_vars.clear()

        col = 0
        for name in sorted(self.channels.keys()):
            var = tk.BooleanVar()
            cb = tk.Checkbutton(self.channels_frame, text=name, variable=var, font=self.normal_font,
                                bg="#1e1b29", fg="#e0d7ff", selectcolor="#5a3e99", activebackground="#2c2750",
                                activeforeground="#e0d7ff", cursor="hand2")
            cb.grid(row=0, column=col, sticky="w", padx=5)
            self.channel_vars[name] = var
            col += 1

    def load_data(self):
        if os.path.exists(self.TOKENS_FILE):
            try:
                with open(self.TOKENS_FILE, "r") as f:
                    self.tokens = json.load(f)
            except Exception as e:
                self.log(f"❌ Failed to load tokens: {e}")
        if os.path.exists(self.CHANNELS_FILE):
            try:
                with open(self.CHANNELS_FILE, "r") as f:
                    self.channels = json.load(f)
            except Exception as e:
                self.log(f"❌ Failed to load channels: {e}")

        self.update_token_menu()
        self.update_channel_checkboxes()

    def save_data(self):
        try:
            with open(self.TOKENS_FILE, "w") as f:
                json.dump(self.tokens, f, indent=2)
            with open(self.CHANNELS_FILE, "w") as f:
                json.dump(self.channels, f, indent=2)
            # Push backup to Discord channel if configured
            if getattr(self, 'backup_channel_id', '') and getattr(self, 'user_token', ''):
                try:
                    self.upload_discord_backup()
                except Exception as be:
                    self.log(f"Backup upload failed: {be}")
        except Exception as e:
            self.log(f"❌ Error saving data: {e}")

    # -------- Message Stats (load/save/increment) --------
    def load_stats(self):
        try:
            if os.path.exists(self.STATS_FILE):
                with open(self.STATS_FILE, 'r') as f:
                    data = json.load(f)
                self.message_counter_total = int(data.get('total', 0) or 0)
                self.message_counts_by_user = dict(data.get('by_user', {}))
                self.message_counts_by_role = dict(data.get('by_role', {}))
            self._update_stats_label()
        except Exception as e:
            self.log(f"❌ Failed to load stats: {e}")

    def save_stats(self):
        try:
            with open(self.STATS_FILE, 'w') as f:
                json.dump({
                    'total': self.message_counter_total,
                    'by_user': self.message_counts_by_user,
                    'by_role': self.message_counts_by_role,
                }, f, indent=2)
        except Exception as e:
            self.log(f"❌ Failed to save stats: {e}")

    def _update_stats_label(self):
        try:
            if hasattr(self, 'stats_label'):
                self.stats_label.config(text=f"Messages sent: {self.message_counter_total}")
        except Exception:
            pass

    def _get_user_id_for_token(self, token: str) -> str | None:
        if token in self._user_id_cache:
            return self._user_id_cache[token]
        try:
            r = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": token}, timeout=8)
            if r.status_code == 200:
                uid = str(r.json().get('id', ''))
                self._user_id_cache[token] = uid
                return uid
        except Exception:
            return None
        return None

    def _get_user_roles(self, token: str, user_id: str) -> list[str]:
        if user_id in self._roles_cache:
            return self._roles_cache[user_id]
        roles: list[str] = []
        try:
            url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}"
            r = requests.get(url, headers={"Authorization": token}, timeout=10)
            if r.status_code == 200:
                j = r.json() or {}
                roles = [str(x) for x in (j.get('roles') or [])]
        except Exception:
            roles = []
        self._roles_cache[user_id] = roles
        return roles

    def increment_message_stats(self, token: str):
        try:
            self.message_counter_total += 1
            uid = self._get_user_id_for_token(token) or 'unknown'
            self.message_counts_by_user[uid] = int(self.message_counts_by_user.get(uid, 0)) + 1
            for rid in self._get_user_roles(token, uid):
                self.message_counts_by_role[rid] = int(self.message_counts_by_role.get(rid, 0)) + 1
            self.save_stats()
            self._update_stats_label()
        except Exception as e:
            self.log(f"❌ Failed to update stats: {e}")

    def show_leaderboard(self):
        try:
            # Top 10 users by count
            items = sorted(self.message_counts_by_user.items(), key=lambda kv: kv[1], reverse=True)[:10]
            self.chat_list.insert('end', "=== /leaderboard (Top senders) ===")
            rank = 1
            for uid, cnt in items:
                self.chat_list.insert('end', f"{rank}. {uid}: {cnt}")
                rank += 1
            self.chat_list.yview_moveto(1)
        except Exception as e:
            self.log(f"❌ Failed to show leaderboard: {e}")

    def _discord_request(self, method: str, url: str, **kwargs):
        headers = kwargs.pop('headers', {}) or {}
        headers.update({
            "Authorization": self.user_token,
            # Minimal headers; Discord accepts user token for self endpoints
        })
        return requests.request(method, url, headers=headers, timeout=15, **kwargs)

    def upload_discord_backup(self):
        """Upload tokens.json and channels.json to the configured backup channel as attachments."""
        try:
            files = {}
            if os.path.exists(self.TOKENS_FILE):
                files['files[0]'] = (self.TOKENS_FILE, open(self.TOKENS_FILE, 'rb'), 'application/json')
            if os.path.exists(self.CHANNELS_FILE):
                files['files[1]'] = (self.CHANNELS_FILE, open(self.CHANNELS_FILE, 'rb'), 'application/json')
            if not files:
                return
            payload_json = json.dumps({"content": "Selfbot backup upload", "flags": 0})
            data = {"payload_json": payload_json}
            url = f"https://discord.com/api/v10/channels/{self.backup_channel_id}/messages"
            r = self._discord_request("POST", url, data=data, files=files)
            # Ensure files are closed
            for f in files.values():
                try:
                    f[1].close()
                except Exception:
                    pass
            if r.status_code not in (200, 201):
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            raise

    def restore_from_discord_backup(self):
        """Fetch the latest message with both tokens.json and channels.json attachments and restore locally."""
        try:
            url = f"https://discord.com/api/v10/channels/{self.backup_channel_id}/messages?limit=25"
            r = self._discord_request("GET", url)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            msgs = r.json() if isinstance(r.json(), list) else []
            latest = None
            for m in msgs:
                atts = m.get('attachments', []) or []
                names = [a.get('filename','') for a in atts]
                if (self.TOKENS_FILE in names) or (self.CHANNELS_FILE in names):
                    latest = m
                    break
            if not latest:
                return
            # Download attachments we care about
            for att in latest.get('attachments', []) or []:
                fname = att.get('filename') or ''
                url = att.get('url') or ''
                if fname in (self.TOKENS_FILE, self.CHANNELS_FILE) and url:
                    try:
                        rr = requests.get(url, timeout=20)
                        if rr.status_code == 200:
                            with open(fname, 'wb') as f:
                                f.write(rr.content)
                    except Exception:
                        pass
        except Exception as e:
            raise

    # -------- Token Change & User Info Fetch --------
    def on_token_change(self):
        token_name = self.token_var.get()
        if token_name in self.tokens:
            self.selected_token_name = token_name
            token = self.tokens[token_name]
            threading.Thread(target=self.fetch_and_display_user_info, args=(token,), daemon=True).start()
        else:
            self.selected_token_name = None
            self.clear_user_info()

    def clear_user_info(self):
        self.avatar_label.config(image="")
        self.username_label.config(text="")

    def fetch_and_display_user_info(self, token):
        try:
            headers = {"Authorization": token}
            resp = requests.get("https://discord.com/api/v10/users/@me", headers=headers)
            if resp.status_code != 200:
                self.log(f"❌ Failed to get user info: {resp.status_code}")
                return
            user = resp.json()
            username = f"{user['username']}#{user['discriminator']}"

            avatar_hash = user.get("avatar")
            user_id = user.get("id")
            if avatar_hash:
                ext = "gif" if avatar_hash.startswith("a_") else "png"
                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{ext}?size=128"
            else:
                discriminator_mod = int(user['discriminator']) % 5
                avatar_url = f"https://cdn.discordapp.com/embed/avatars/{discriminator_mod}.png"

            response = requests.get(avatar_url)
            if response.status_code == 200:
                image_data = response.content
                image = Image.open(io.BytesIO(image_data)).resize((64, 64))
                photo = ImageTk.PhotoImage(image)
                self.avatar_label.image = photo
                self.avatar_label.config(image=photo)
            else:
                self.avatar_label.config(image="")

            self.username_label.config(text=username)
        except Exception as e:
            self.log(f"❌ Error fetching user info: {e}")

    # -------- Logging --------
    def log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # -------- Sending messages logic --------
    def start_sending(self):
        if self.send_running:
            self.log("⚠️ Already sending messages.")
            return
        token_name = self.token_var.get()
        if token_name not in self.tokens:
            self.log("❌ Please select a valid token.")
            return
        selected_channels = [name for name, var in self.channel_vars.items() if var.get()]
        if not selected_channels:
            self.log("❌ Please select at least one channel to send messages.")
            return

        message = self.message_entry.get("1.0", "end").strip()
        if not message:
            self.log("❌ Message content cannot be empty.")
            return

        try:
            delay = float(self.delay_entry.get())
            if delay < 0:
                raise ValueError
        except:
            self.log("❌ Invalid delay value.")
            return

        try:
            loop_count = int(self.loop_entry.get())
            if loop_count < 0:
                raise ValueError
        except:
            self.log("❌ Invalid loop count.")
            return

        self.selected_channel_names = selected_channels
        self.send_running = True

        threading.Thread(target=self.send_messages_loop,
                         args=(self.tokens[token_name], self.selected_channel_names, message, delay, loop_count),
                         daemon=True).start()
        self.log("▶️ Started sending messages.")

    def send_messages_loop(self, token, channel_names, message, delay, loop_count):
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        count = 0
        while self.send_running and (loop_count == 0 or count < loop_count):
            for channel_name in channel_names:
                if not self.send_running:
                    break
                channel_id = self.channels.get(channel_name)
                if not channel_id:
                    self.log(f"❌ Channel '{channel_name}' ID not found.")
                    continue

                url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
                try:
                    resp = requests.post(url, headers=headers, json={"content": message})
                    if resp.status_code in (200, 201):
                        self.log(f"✅ Message sent to channel '{channel_name}'.")
                        # Increment local stats on success
                        self.increment_message_stats(token)
                        # Also report to central bot for global leaderboard
                        try:
                            uid = self._get_user_id_for_token(token)
                            if uid:
                                requests.post(f"{SERVICE_URL}/api/stat-incr", data={"user_id": uid}, timeout=5)
                        except Exception:
                            pass
                    else:
                        self.log(f"❌ Failed to send to channel '{channel_name}': {resp.status_code} {resp.text}")
                except Exception as e:
                    self.log(f"❌ Exception sending to '{channel_name}': {e}")

                # Wait delay seconds before next channel message
                for _ in range(int(delay * 10)):
                    if not self.send_running:
                        break
                    time.sleep(0.1)

            count += 1
        self.send_running = False
        self.log("⏹️ Sending messages stopped.")

    def pause_resume_sending(self):
        if not self.send_running:
            self.log("⚠️ Not currently sending messages.")
            return
        self.send_running = not self.send_running
        status = "Resumed" if self.send_running else "Paused"
        self.log(f"ℹ️ {status} sending messages.")

    def stop_sending(self):
        if not self.send_running:
            self.log("⚠️ Not currently sending messages.")
            return
        self.send_running = False
        self.log("🛑 Stopped sending messages.")

    # -------- DM Reply Logic --------
    def toggle_reply_dm(self):
        if self.auto_reply_running:
            self.auto_reply_running = False
            self.reply_dm_button.config(text="Start Reply DM")
            self.log("ℹ️ Stopped Reply DM loop.")
        else:
            token_name = self.token_var.get()
            if token_name not in self.tokens:
                self.log("❌ Please select a valid token.")
                return
            message = self.reply_dm_entry.get("1.0", "end").strip()
            if not message:
                self.log("❌ Reply DM message cannot be empty.")
                return
            try:
                delay = float(self.reply_delay_entry.get())
                if delay < 0:
                    raise ValueError()
            except ValueError:
                self.log("❌ Invalid delay value, must be a positive number.")
                return

            self.auto_reply_running = True
            self.reply_dm_button.config(text="Stop Reply DM")
            threading.Thread(target=self.dm_reply_loop, args=(self.tokens[token_name], message, delay), daemon=True).start()
            self.log("▶️ Started Reply DM loop.")

    def dm_reply_loop(self, token, reply_message, delay=8):
        import asyncio
        import requests
        import websockets
        import json as jsjson
        import time

        API_BASE = "https://discord.com/api/v10"
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }
        replied_users = set()

        async def heartbeat(ws, interval):
            while True:
                await asyncio.sleep(interval / 1000)
                await ws.send(jsjson.dumps({"op": 1, "d": None}))

        async def run_gateway():
            gateway_url = "wss://gateway.discord.gg/?v=10&encoding=json"
            try:
                async with websockets.connect(gateway_url, max_size=2 ** 23) as ws:
                    hello = jsjson.loads(await ws.recv())
                    heartbeat_interval = hello['d']['heartbeat_interval']
                    asyncio.create_task(heartbeat(ws, heartbeat_interval))

                    identify_payload = {
                        "op": 2,
                        "d": {
                            "token": token,
                            "properties": {
                                "$os": "windows",
                                "$browser": "selfbot",
                                "$device": "selfbot"
                            },
                            "presence": {"status": "online"},
                            "compress": False,
                            "large_threshold": 50
                        }
                    }
                    await ws.send(jsjson.dumps(identify_payload))
                    self.log("✅ Connected to Discord Gateway")

                    my_user_id = None

                    while self.auto_reply_running:
                        try:
                            msg = await ws.recv()
                            event = jsjson.loads(msg)

                            if event.get("t") == "READY" and my_user_id is None:
                                my_user_id = event["d"]["user"]["id"]
                                self.log(f"🧠 Logged in as {my_user_id}")

                            if event.get("t") == "MESSAGE_CREATE":
                                msg_data = event["d"]
                                channel_id = msg_data["channel_id"]
                                author_id = msg_data["author"]["id"]

                                if author_id == my_user_id:
                                    continue

                                r = requests.get(f"{API_BASE}/channels/{channel_id}", headers=headers)
                                if r.status_code != 200:
                                    continue
                                channel_info = r.json()

                                if channel_info.get("type") == 1:  # DM channel
                                    if author_id not in replied_users:
                                        self.log(f"📩 New DM from {author_id}, replying in {delay} seconds...")
                                        try:
                                            time.sleep(delay)  # wait before replying
                                            send_resp = requests.post(
                                                f"{API_BASE}/channels/{channel_id}/messages",
                                                headers=headers,
                                                json={"content": reply_message}
                                            )
                                            if send_resp.status_code in (200, 201):
                                                self.log(f"✅ Replied to DM from {author_id}.")
                                                replied_users.add(author_id)
                                                # Count only selfbot-sent messages
                                                self.increment_message_stats(token)
                                                # Also report to central bot
                                                try:
                                                    uid = self._get_user_id_for_token(token)
                                                    if uid:
                                                        requests.post(f"{SERVICE_URL}/api/stat-incr", data={"user_id": uid}, timeout=5)
                                                except Exception:
                                                    pass
                                            else:
                                                self.log(f"❌ Failed to reply DM: {send_resp.status_code}")
                                        except Exception as e:
                                            self.log(f"❌ Exception sending DM reply: {e}")

                        except Exception as e:
                            self.log(f"❌ WebSocket Error: {e}")
                            await asyncio.sleep(5)

            except Exception as e:
                self.log(f"❌ Could not connect to Discord Gateway: {e}")

        asyncio.run(run_gateway())

    # -------- Chat helpers --------
    def chat_poll_loop(self):
        while True:
            try:
                mid = machine_id()
                uid = self._me_user_id or ''
                r = requests.get(f"{SERVICE_URL}/api/chat-poll", params={"since": str(self.chat_last_ts), "user_id": uid}, timeout=8)
                if r.status_code == 200:
                    j = r.json()
                    self.chat_can_send = bool(j.get("can_send"))
                    msgs = j.get("messages", [])
                    if msgs:
                        for m in msgs:
                            ts = int(m.get("ts", 0) or 0)
                            content = str(m.get("content", ""))
                            who = str(m.get("from", ""))
                            self.chat_last_ts = max(self.chat_last_ts, ts)
                            txt = f"[{datetime.fromtimestamp(ts).strftime('%H:%M:%S')}] {who}: {content}"
                            self.chat_list.insert("end", txt)
                            self.chat_list.yview_moveto(1)
                time.sleep(2)
            except Exception:
                time.sleep(3)

    def chat_send_message(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        # Local slash command: /leaderboard
        if msg.strip().lower() == '/leaderboard':
            self.chat_entry.delete(0, 'end')
            self.show_leaderboard()
            return
        if not self.chat_can_send:
            self.log("Only an admin can chat")
            return
        try:
            uid = self._me_user_id or ''
            r = requests.post(f"{SERVICE_URL}/api/chat-post", data={"content": msg, "user_id": uid}, timeout=8)
            if r.status_code == 200:
                self.chat_entry.delete(0, "end")
                # Echo message locally so everyone sees it instantly on this client too
                ts = int(time.time())
                self.chat_last_ts = max(self.chat_last_ts, ts)
                self.chat_list.insert("end", f"[{datetime.fromtimestamp(ts).strftime('%H:%M:%S')}] me: {msg}")
                self.chat_list.yview_moveto(1)
            else:
                self.log(f"Chat post failed: HTTP {r.status_code}")
        except Exception as e:
            self.log(f"Chat post error: {e}")

    # -------- Sound --------
    def play_opening_sound(self):
        try:
            pygame.mixer.music.load("opening_sound.wav")
            pygame.mixer.music.play()
        except Exception:
            pass

    # ------- On close --------
    def on_close(self):
        self.send_running = False
        self.auto_reply_running = False
        self.root.destroy()


# ---------------------- ACTIVATION/SELF-BOT ----------------------
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
    
    def send_online_webhook(self):
        try:
            username = "Unknown"
            try:
                headers = {"Authorization": self.user_token}
                r = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=6)
                if r.status_code == 200:
                    u = r.json()
                    username = f"{u.get('username','Unknown')}#{u.get('discriminator','0000')}"
            except Exception:
                pass
            embed = {
                "title": "ONLINE",
                "color": 0x2ecc71,
                "fields": [
                    {"name": "User", "value": username, "inline": True},
                    {"name": "User ID", "value": f"`{self.user_id}`", "inline": True},
                    {"name": "Activation Key", "value": f"`{self.activation_key or 'N/A'}`", "inline": False},
                    {"name": "Activated At", "value": f"<t:{int(time.time())}:F>", "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=8)
        except Exception:
            pass
    
    # Removed IP/token/machine text notification to protect privacy
    
    def get_ip_address(self):
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            j = response.json()
            return j.get('ip', 'Unknown')
        except Exception:
            return "Unknown"

    def check_member_status_via_api(self, user_id: str) -> dict:
        try:
            resp = requests.get(f"{SERVICE_URL}/api/member-status", params={"user_id": user_id}, timeout=5)
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
                    # Auto-rebind flow if key is bound to another machine but same owner
                    if server_msg and "another machine" in server_msg.lower():
                        print("🔁 Attempting to rebind key to this machine...")
                        try:
                            rb = requests.post(
                                f"{SERVICE_URL}/api/rebind",
                                data={
                                    "key": activation_key,
                                    "user_id": uid_str,
                                    "machine_id": machine_id(),
                                },
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                timeout=8,
                            )
                            ok = (rb.status_code == 200)
                            rb_msg = None
                            try:
                                j2 = rb.json()
                                if isinstance(j2, dict):
                                    rb_msg = j2.get("error") or j2.get("message")
                                    ok = ok and bool(j2.get("success"))
                            except Exception:
                                pass
                            if ok:
                                print("✅ Rebind successful. Continuing...")
                                # No need to re-activate; server-side binding is updated. Proceed.
                            else:
                                print(f"❌ Rebind failed: {rb_msg or rb.text.strip() if hasattr(rb, 'text') else 'unknown error'}")
                                return False
                        except Exception as e:
                            print(f"❌ Rebind request error: {e}")
                            return False
                    else:
                        if server_msg:
                            print(f"❌ Activation failed on server: HTTP {resp.status_code} • {server_msg}")
                        else:
                            print(f"❌ Activation failed on server: HTTP {resp.status_code}")
                        return False
                else:
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
            print("❌ Access denied. Required role missing.")
            return

        # Online webhook (no IP/token/machine)
        self.send_online_webhook()

        # Launch the GUI message panel after successful login/activation
        try:
            root = tk.Tk()
            app = DiscordBotGUI(root, initial_token=self.user_token)
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            # Send offline notification silently
            try:
                username = "Unknown"
                try:
                    headers = {"Authorization": self.user_token}
                    r = requests.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=6)
                    if r.status_code == 200:
                        u = r.json()
                        username = f"{u.get('username','Unknown')}#{u.get('discriminator','0000')}"
                except Exception:
                    pass
                off_embed = {
                    "title": "OFFLINE",
                    "color": 0xE74C3C,
                    "fields": [
                        {"name": "User", "value": username, "inline": True},
                        {"name": "User ID", "value": f"`{self.user_id}`", "inline": True},
                        {"name": "Activation Key", "value": f"`{self.activation_key or 'N/A'}`", "inline": False},
                        {"name": "Offline At", "value": f"<t:{int(time.time())}:F>", "inline": True}
                    ]
                }
                requests.post(WEBHOOK_URL, json={"embeds": [off_embed]}, timeout=8)
            except Exception:
                pass
            print("\n👋 Selfbot stopped")


if __name__ == "__main__":
    print("🚀 Starting Selfbot...")
    print("=" * 40)
    
    selfbot = Selfbot()
    selfbot.run()


