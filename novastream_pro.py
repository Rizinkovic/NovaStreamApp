import customtkinter as ctk
import yt_dlp
import threading
import os
import sys
import subprocess
import webbrowser
import json
import math
import time
import re
from tkinter import filedialog
import imageio_ffmpeg

# DPI awareness
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".novastream_settings.json")

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ─── Platform detection ───────────────────────────────────────────────────────
PLATFORM_PATTERNS = {
    "youtube":   r"(youtube\.com|youtu\.be)",
    "facebook":  r"(facebook\.com|fb\.watch|fb\.com)",
    "instagram": r"(instagram\.com|instagr\.am)",
    "tiktok":    r"(tiktok\.com|vm\.tiktok\.com)",
    "twitter":   r"(twitter\.com|x\.com|t\.co)",
}

PLATFORM_DISPLAY = {
    "youtube":   "▶  YouTube",
    "facebook":  "f  Facebook",
    "instagram": "📷 Instagram",
    "tiktok":    "🎵 TikTok",
    "twitter":   "𝕏  X / Twitter",
    "unknown":   "🌐 Auto-detect",
}

def detect_platform(url: str) -> str:
    for name, pattern in PLATFORM_PATTERNS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return name
    return "unknown"

# ─── Palettes ─────────────────────────────────────────────────────────────────
PALETTES = {
    "blueish-white": {
        "accent":       "#3B8ED0",
        "accent_dark":  "#1f538d",
        "accent_hover": "#5aaee8",
        "wave1":        "#3B8ED0",
        "wave2":        "#1f538d",
        "wave3":        "#5aaee8",
        "canvas_bg":    "#0d1b2a",
        "ctk_theme":    "blue",
    },
    "greenish-white": {
        "accent":       "#2ECC71",
        "accent_dark":  "#1a7a43",
        "accent_hover": "#58d68d",
        "wave1":        "#2ECC71",
        "wave2":        "#1a7a43",
        "wave3":        "#58d68d",
        "canvas_bg":    "#0d1f16",
        "ctk_theme":    "green",
    },
    "dark-pink": {
        "accent":       "#E91E63",
        "accent_dark":  "#880E4F",
        "accent_hover": "#f06292",
        "wave1":        "#E91E63",
        "wave2":        "#880E4F",
        "wave3":        "#f48fb1",
        "canvas_bg":    "#1a0010",
        "ctk_theme":    "blue",
    },
}

DEFAULT_SETTINGS = {
    "theme":       "dark",
    "palette":     "blueish-white",
    "auto_open":   False,
    "show_speed":  True,
    "mp3_quality": "128",
}

F       = 13   # base font
F_SM    = 11   # small
F_BTN   = 14   # buttons
F_TITLE = 21   # sidebar title


class NovaStreamPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = self._load_settings()
        self._apply_appearance()

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass

        self.title("NovaStream Pro")
        self.geometry("1000x720")
        self.minsize(820, 580)
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

        self._wave_speed   = 0.0
        self._anim_running = True
        self._dl_total     = 0
        self._dl_done      = 0

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._build_footer()
        self._start_wave_loop()

    # ── Settings ──────────────────────────────────────────────────────────────
    def _load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    data.setdefault(k, v)
                return data
            except:
                pass
        return dict(DEFAULT_SETTINGS)

    def _save_settings(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.settings, f, indent=2)
        except:
            pass

    def _apply_appearance(self):
        ctk.set_appearance_mode(self.settings["theme"])
        p = PALETTES.get(self.settings["palette"], PALETTES["blueish-white"])
        ctk.set_default_color_theme(p["ctk_theme"])
        self._pal = p

    # ── Sidebar (scrollable) ──────────────────────────────────────────────────
    def _build_sidebar(self):
        # Outer fixed-width container — no scrollbar on it
        self.sidebar_outer = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_outer.grid(row=0, column=0, sticky="nsew")
        self.sidebar_outer.grid_propagate(False)
        self.sidebar_outer.grid_rowconfigure(0, weight=1)
        self.sidebar_outer.grid_columnconfigure(0, weight=1)

        # Scrollable inner frame
        self.sidebar = ctk.CTkScrollableFrame(
            self.sidebar_outer,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color="gray30",
            scrollbar_button_hover_color="gray50",
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        sb = self.sidebar  # shorthand

        # Title
        ctk.CTkLabel(
            sb, text="NOVA STREAM",
            font=("Arial Black", F_TITLE, "bold"),
            text_color=self._pal["accent"]
        ).pack(pady=(28, 2), padx=10)
        ctk.CTkLabel(
            sb, text="PRO  ·  Ultimate Downloader",
            font=("Arial", F_SM), text_color="gray"
        ).pack(pady=(0, 18), padx=10)

        # Platforms badges
        self._sep(sb, "PLATFORMS")
        ctk.CTkLabel(
            sb,
            text="▶ YouTube    📷 Instagram\nf  Facebook   🎵 TikTok\n𝕏  X / Twitter",
            font=("Arial", F_SM), text_color="gray", justify="left"
        ).pack(padx=22, anchor="w", pady=(4, 10))

        # Folder
        self._sep(sb, "FOLDER")
        self._btn(sb, "⊕  Select Folder", self.choose_path, solid=True).pack(
            pady=(6, 3), padx=18, fill="x")
        self.path_label = ctk.CTkLabel(
            sb, text="Saving to:  Downloads",
            font=("Arial", F_SM), text_color="gray", wraplength=210
        )
        self.path_label.pack(padx=18, anchor="w", pady=(2, 4))
        self._btn(sb, "📂  Open Folder", self.open_folder, solid=False).pack(
            pady=(3, 6), padx=18, fill="x")

        # Subtitles
        self._sep(sb, "SUBTITLES  (YouTube only)")
        self.sub_en = self._checkbox(sb, "English")
        self.sub_en.pack(pady=(4, 2), padx=22, anchor="w")
        self.sub_fr = self._checkbox(sb, "French")
        self.sub_fr.pack(pady=(2, 8), padx=22, anchor="w")

        # Settings
        self._sep(sb, "SETTINGS")

        self._lbl(sb, "Theme")
        self.theme_opt = ctk.CTkOptionMenu(
            sb, values=["dark", "light"],
            font=("Arial", F_SM), height=34,
            command=self._on_theme_change
        )
        self.theme_opt.set(self.settings["theme"])
        self.theme_opt.pack(pady=(2, 10), padx=18, fill="x")

        self._lbl(sb, "Color Palette")
        self.palette_opt = ctk.CTkOptionMenu(
            sb, values=list(PALETTES.keys()),
            font=("Arial", F_SM), height=34,
            command=self._on_palette_change
        )
        self.palette_opt.set(self.settings["palette"])
        self.palette_opt.pack(pady=(2, 10), padx=18, fill="x")

        self._lbl(sb, "MP3 Quality")
        self.mp3_qual_opt = ctk.CTkOptionMenu(
            sb,
            values=["96 kbps (small)", "128 kbps (medium)",
                    "192 kbps (high)", "320 kbps (best)"],
            font=("Arial", F_SM), height=34,
            command=self._on_mp3_quality_change
        )
        _qmap = {"96": "96 kbps (small)", "128": "128 kbps (medium)",
                 "192": "192 kbps (high)", "320": "320 kbps (best)"}
        self.mp3_qual_opt.set(_qmap.get(self.settings["mp3_quality"], "128 kbps (medium)"))
        self.mp3_qual_opt.pack(pady=(2, 10), padx=18, fill="x")

        self.auto_open_cb = self._checkbox(sb, "Auto-open folder after download",
                                           command=self._on_auto_open_toggle)
        if self.settings["auto_open"]:
            self.auto_open_cb.select()
        self.auto_open_cb.pack(pady=(4, 4), padx=22, anchor="w")

        self.show_speed_cb = self._checkbox(sb, "Show download speed",
                                            command=self._on_show_speed_toggle)
        if self.settings["show_speed"]:
            self.show_speed_cb.select()
        self.show_speed_cb.pack(pady=(4, 20), padx=22, anchor="w")

    # ── Sidebar helpers ───────────────────────────────────────────────────────
    def _sep(self, parent, text):
        ctk.CTkFrame(parent, height=1, fg_color="gray25").pack(
            fill="x", padx=14, pady=(14, 3))
        ctk.CTkLabel(parent, text=text, font=("Arial", 10, "bold"),
                     text_color="gray50").pack(padx=22, anchor="w", pady=(0, 2))

    def _lbl(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Arial", F_SM)).pack(
            padx=22, anchor="w", pady=(4, 1))

    def _btn(self, parent, text, cmd, solid=True):
        if solid:
            return ctk.CTkButton(
                parent, text=text,
                font=("Arial", F_SM), height=34,
                fg_color=self._pal["accent"],
                hover_color=self._pal["accent_hover"],
                corner_radius=8,
                command=cmd
            )
        else:
            return ctk.CTkButton(
                parent, text=text,
                font=("Arial", F_SM), height=34,
                fg_color="transparent",
                border_width=1,
                border_color=self._pal["accent"],
                text_color=self._pal["accent"],
                hover_color=self._pal["accent_dark"],
                corner_radius=8,
                command=cmd
            )

    def _checkbox(self, parent, text, command=None):
        kw = {"command": command} if command else {}
        return ctk.CTkCheckBox(
            parent, text=text,
            font=("Arial", F_SM),
            checkmark_color=self._pal["accent"],
            hover_color=self._pal["accent_dark"],
            corner_radius=4,
            **kw
        )

    # ── Main panel ────────────────────────────────────────────────────────────
    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=32, pady=22, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(9, weight=1)

        # URL
        self.url_entry = ctk.CTkEntry(
            self.main,
            placeholder_text="🔗  Paste URL  (YouTube, TikTok, Instagram, Facebook, X…)",
            height=50, font=("Arial", F), corner_radius=10
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", pady=(8, 4))
        self.url_entry.bind("<KeyRelease>", self._on_url_type)

        # Platform badge
        self.platform_label = ctk.CTkLabel(
            self.main, text="🌐  Paste a URL — platform will be detected automatically",
            font=("Arial", F_SM), text_color="gray", anchor="w"
        )
        self.platform_label.grid(row=1, column=0, sticky="w", pady=(0, 8))

        # Mode
        self.mode_switch = ctk.CTkSegmentedButton(
            self.main, values=["🎬  Video", "🎵  Audio (MP3)"],
            font=("Arial", F), height=38,
            command=self._on_mode_change
        )
        self.mode_switch.set("🎬  Video")
        self.mode_switch.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        # Quality
        self.quality_menu = ctk.CTkOptionMenu(
            self.main,
            values=["Best available", "1080p", "720p", "480p", "360p", "240p"],
            font=("Arial", F), height=36, corner_radius=8
        )
        self.quality_menu.set("Best available")
        self.quality_menu.grid(row=3, column=0, pady=(0, 6))

        # Download button
        self.download_btn = ctk.CTkButton(
            self.main, text="▶   DOWNLOAD NOW",
            font=("Arial", F_BTN, "bold"),
            height=50, corner_radius=10,
            fg_color=self._pal["accent"],
            hover_color=self._pal["accent_hover"],
            command=self.start_thread
        )
        self.download_btn.grid(row=4, column=0, sticky="ew", pady=(8, 14))

        # ── Progress section ──────────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        prog_frame.grid(row=5, column=0, sticky="ew", pady=(0, 2))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(
            prog_frame, text="Ready to download",
            font=("Arial", F), anchor="w"
        )
        self.progress_label.grid(row=0, column=0, sticky="w")

        self.pct_label = ctk.CTkLabel(
            prog_frame, text="",
            font=("Arial", F, "bold"),
            text_color=self._pal["accent"], anchor="e"
        )
        self.pct_label.grid(row=0, column=1, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(
            self.main,
            progress_color=self._pal["accent"],
            height=12, corner_radius=6
        )
        self.progress_bar.grid(row=6, column=0, sticky="ew", pady=(2, 2))
        self.progress_bar.set(0)

        # Speed + ETA row
        info_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        info_frame.grid(row=7, column=0, sticky="ew", pady=(0, 4))
        info_frame.grid_columnconfigure(0, weight=1)

        self.speed_label = ctk.CTkLabel(
            info_frame, text="",
            font=("Arial", F_SM), text_color="gray", anchor="w"
        )
        self.speed_label.grid(row=0, column=0, sticky="w")

        self.eta_label = ctk.CTkLabel(
            info_frame, text="",
            font=("Arial", F_SM), text_color="gray", anchor="e"
        )
        self.eta_label.grid(row=0, column=1, sticky="e")

        # Visualizer
        self.canvas = ctk.CTkCanvas(
            self.main, height=88,
            bg=self._pal["canvas_bg"],
            highlightthickness=0
        )
        self.canvas.grid(row=8, column=0, sticky="ew", pady=(4, 6))

        # Log
        self.log_box = ctk.CTkTextbox(
            self.main, height=110, font=("Consolas", F)
        )
        self.log_box.grid(row=9, column=0, sticky="nsew")

    def _build_footer(self):
        self.footer = ctk.CTkLabel(
            self, text="Made by Rizinkovic",
            font=("Arial", F_SM, "underline"),
            cursor="hand2",
            text_color=self._pal["accent"]
        )
        self.footer.grid(row=1, column=0, columnspan=2, pady=6)
        self.footer.bind("<Button-1>",
                         lambda e: webbrowser.open("https://github.com/Rizinkovic"))

    # ── URL typing ────────────────────────────────────────────────────────────
    def _on_url_type(self, _=None):
        url = self.url_entry.get().strip()
        if not url:
            self.platform_label.configure(
                text="🌐  Paste a URL — platform will be detected automatically",
                text_color="gray")
            return
        p = detect_platform(url)
        self.platform_label.configure(
            text=f"Detected:  {PLATFORM_DISPLAY.get(p, '🌐 Unknown')}",
            text_color=self._pal["accent"])
        # Subtitles only on YouTube
        state = "normal" if p == "youtube" else "disabled"
        self.sub_en.configure(state=state)
        self.sub_fr.configure(state=state)

    # ── Wave ──────────────────────────────────────────────────────────────────
    def _start_wave_loop(self):
        self._draw_wave()

    def _draw_wave(self):
        if not self._anim_running:
            return
        try:
            self.canvas.delete("all")
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            if w < 10 or h < 10:
                self.after(50, self._draw_wave)
                return
            t = time.monotonic()
            s = self._wave_speed
            if s <= 0:
                self._wave(w, h, t, amp=5,       freq=0.018, spd=0.7,  col=self._pal["wave2"], lw=1)
            else:
                a = min(34, 5 + s * 3.2)
                self._wave(w, h, t, amp=a*.55,   freq=0.022, spd=3.2,  col=self._pal["wave2"], lw=1)
                self._wave(w, h, t, amp=a*.85,   freq=0.014, spd=2.0,  col=self._pal["wave1"], lw=2, ph=1.1)
                self._wave(w, h, t, amp=a*.38,   freq=0.034, spd=4.8,  col=self._pal["wave3"], lw=1, ph=2.5)
        except Exception:
            pass
        self.after(30, self._draw_wave)

    def _wave(self, w, h, t, amp, freq, spd, col, lw, ph=0.0):
        cy = h / 2
        phase = t * spd + ph
        pts = []
        step = max(3, w // 130)
        for x in range(0, w + step, step):
            pts.extend([x, cy + amp * math.sin(x * freq + phase)])
        if len(pts) >= 4:
            self.canvas.create_line(pts, fill=col, smooth=True, width=lw)

    # ── Settings callbacks ────────────────────────────────────────────────────
    def _on_theme_change(self, v):
        self.settings["theme"] = v
        self._save_settings()
        ctk.set_appearance_mode(v)

    def _on_palette_change(self, v):
        self.settings["palette"] = v
        self._save_settings()
        p = PALETTES.get(v, PALETTES["blueish-white"])
        self._pal = p
        # Update all accent-coloured widgets live
        self.download_btn.configure(fg_color=p["accent"], hover_color=p["accent_hover"])
        self.progress_bar.configure(progress_color=p["accent"])
        self.pct_label.configure(text_color=p["accent"])
        self.canvas.configure(bg=p["canvas_bg"])
        self.footer.configure(text_color=p["accent"])
        self.platform_label.configure(text_color=p["accent"])
        # Sidebar buttons
        for w in self.sidebar.winfo_children():
            try:
                if isinstance(w, ctk.CTkButton):
                    txt = w.cget("text")
                    if "Select" in txt:
                        w.configure(fg_color=p["accent"], hover_color=p["accent_hover"])
                    elif "Open" in txt:
                        w.configure(border_color=p["accent"],
                                    text_color=p["accent"],
                                    hover_color=p["accent_dark"])
            except:
                pass

    def _on_mp3_quality_change(self, v):
        self.settings["mp3_quality"] = v.split(" ")[0]
        self._save_settings()

    def _on_auto_open_toggle(self):
        self.settings["auto_open"] = bool(self.auto_open_cb.get())
        self._save_settings()

    def _on_show_speed_toggle(self):
        self.settings["show_speed"] = bool(self.show_speed_cb.get())
        self._save_settings()
        if not self.settings["show_speed"]:
            self.speed_label.configure(text="")
            self.eta_label.configure(text="")

    def _on_mode_change(self, v):
        self.quality_menu.configure(
            state="disabled" if "Audio" in v else "normal")

    # ── Folder helpers ────────────────────────────────────────────────────────
    def choose_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            name = os.path.basename(path) or path
            self.path_label.configure(text=f"Saving to:  {name}")

    def open_folder(self):
        try:
            if os.name == "nt":
                os.startfile(self.download_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", self.download_path])
            else:
                subprocess.call(["xdg-open", self.download_path])
        except Exception as e:
            self._log(f"Cannot open folder: {e}")

    # ── Download ──────────────────────────────────────────────────────────────
    def start_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("1.0", "end")
        self.progress_bar.set(0)
        self.pct_label.configure(text="")
        self.speed_label.configure(text="")
        self.eta_label.configure(text="")
        self.progress_label.configure(text="Starting download…")
        self._wave_speed = 0.4
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _build_opts(self, url, is_audio, quality, langs):
        platform = detect_platform(url)
        ffmpeg   = imageio_ffmpeg.get_ffmpeg_exe()
        q        = quality.replace("p", "").replace("Best available", "best").replace(" ", "")

        opts = {
            "ffmpeg_location":              ffmpeg,
            "outtmpl":                      os.path.join(self.download_path, "%(title)s.%(ext)s"),
            "progress_hooks":               [self._progress_hook],
            "ignoreerrors":                 False,
            "quiet":                        True,
            "no_warnings":                  True,
            # ── Robustness for slow/3G connections ──
            "retries":                      15,
            "fragment_retries":             15,
            "file_access_retries":          5,
            "socket_timeout":               60,
            "http_chunk_size":              1_048_576,   # 1 MB
            "buffersize":                   1024,
            "concurrent_fragment_downloads": 1,
            "retry_sleep_functions":        {"http": lambda n: min(4 ** n, 60)},
        }

        if is_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": self.settings["mp3_quality"],
            }]
            return opts

        # ── Video — always output MP4 ─────────────────────────────────────────
        if q == "best":
            if platform in ("instagram", "tiktok", "facebook", "twitter"):
                fmt = "best[ext=mp4]/best"
            else:
                fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        else:
            if platform in ("instagram", "tiktok", "facebook", "twitter"):
                # Try height-filtered mp4, fall back to any matching height, fall back to best
                fmt = (
                    f"best[ext=mp4][height<={q}]"
                    f"/best[height<={q}]"
                    f"/best[ext=mp4]"
                    f"/best"
                )
            else:
                fmt = (
                    f"bestvideo[ext=mp4][height<={q}]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={q}]+bestaudio"
                    f"/best[height<={q}]"
                    f"/best"
                )

        opts["format"] = fmt
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [{
            "key":            "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }]

        # Subtitles — only meaningful on YouTube
        if langs and platform == "youtube":
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = langs
        else:
            opts["writesubtitles"] = False

        # Platform headers to avoid 403s
        if platform == "instagram":
            opts["http_headers"] = {
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                    "Mobile/15E148 Safari/604.1"
                )
            }
        elif platform in ("twitter", "facebook"):
            opts["http_headers"] = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            }

        return opts

    def _download(self, url):
        mode     = self.mode_switch.get()
        is_audio = "Audio" in mode
        quality  = self.quality_menu.get()
        langs    = [l for l, c in [("en", self.sub_en), ("fr", self.sub_fr)] if c.get()]
        platform = detect_platform(url)

        self.after(0, lambda: self._log(
            f"⏳ Fetching  [ {PLATFORM_DISPLAY.get(platform, '🌐 Auto')} ]"
        ))

        opts = self._build_opts(url, is_audio, quality, langs)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, self._on_success)

        except yt_dlp.utils.DownloadError as e:
            hints = {
                "instagram": "ℹ  Instagram: private accounts or Stories cannot be downloaded.",
                "tiktok":    "ℹ  TikTok: private videos cannot be downloaded.",
                "facebook":  "ℹ  Facebook: private/group videos may need login cookies.",
                "twitter":   "ℹ  X/Twitter: some tweets may be restricted or private.",
            }
            self.after(0, lambda: self._log(f"✘  {e}"))
            hint = hints.get(platform, "")
            if hint:
                self.after(0, lambda: self._log(hint))
            self.after(0, lambda: self._set_status("Download failed", error=True))

        except Exception as e:
            self.after(0, lambda: self._log(f"✘  Unexpected error: {e}"))
            self.after(0, lambda: self._set_status("Download failed", error=True))

        finally:
            self._wave_speed = 0.0
            self.after(0, lambda: self.download_btn.configure(state="normal"))

    def _on_success(self):
        self.progress_bar.set(1)
        self.pct_label.configure(text="100%")
        self.progress_label.configure(text="✔  Download complete!")
        self.speed_label.configure(text="")
        self.eta_label.configure(text="")
        self._log("✔  Saved to:  " + self.download_path)
        if self.settings["auto_open"]:
            self.after(600, self.open_folder)

    def _set_status(self, msg, error=False):
        self.progress_label.configure(text=msg)
        if error:
            self.pct_label.configure(text="")

    def _progress_hook(self, d):
        status = d.get("status")

        if status == "downloading":
            raw_p     = d.get("_percent_str", "0%").strip().rstrip("% \x1b[0m").replace("\x1b[0;94m", "")
            speed_str = d.get("_speed_str", "—").strip()
            eta_str   = d.get("_eta_str", "").strip()
            downloaded = d.get("downloaded_bytes", 0)
            total      = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

            # Clean up any ANSI codes yt-dlp might inject
            raw_p = re.sub(r'\x1b\[[0-9;]*m', '', raw_p).strip().rstrip('%').strip()

            try:
                pct = float(raw_p) / 100.0
            except ValueError:
                pct = (downloaded / total) if total > 0 else 0.0

            # Wave speed
            try:
                clean_spd = re.sub(r'\x1b\[[0-9;]*m', '', speed_str)
                if "MiB" in clean_spd or "MB" in clean_spd:
                    num = float(re.findall(r"[\d.]+", clean_spd)[0])
                elif "KiB" in clean_spd or "KB" in clean_spd:
                    num = float(re.findall(r"[\d.]+", clean_spd)[0]) / 1024.0
                else:
                    num = 0.3
                self._wave_speed = max(0.3, min(num, 15.0))
            except Exception:
                self._wave_speed = 0.5

            def _ui():
                self.progress_bar.set(max(0.0, min(pct, 1.0)))
                pct_display = f"{pct*100:.1f}%"
                self.pct_label.configure(text=pct_display)
                self.progress_label.configure(text="Downloading…")
                if self.settings["show_speed"] and speed_str and speed_str != "—":
                    self.speed_label.configure(text=f"⬇  {speed_str}")
                if eta_str and eta_str not in ("Unknown", "--:--", ""):
                    self.eta_label.configure(text=f"ETA  {eta_str}")

            self.after(0, _ui)

        elif status == "finished":
            self._wave_speed = 0.15
            self.after(0, lambda: self.progress_label.configure(text="Finalizing…"))
            self.after(0, lambda: self.pct_label.configure(text=""))

    def _log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def on_closing(self):
        self._anim_running = False
        self.destroy()


if __name__ == "__main__":
    app = NovaStreamPro()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
