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
from tkinter import filedialog
import imageio_ffmpeg

# DPI awareness prevents blurry text on high-res monitors
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

# ─── Palette definitions ─────────────────────────────────────────────────────
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
        "ctk_theme":    "blue",   # CTK has no pink theme, we override manually
    },
}

DEFAULT_SETTINGS = {
    "theme":      "dark",
    "palette":    "blueish-white",
    "auto_open":  False,
    "show_speed": True,
    "mp3_quality": "128",
}


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

        self.title("NovaStream Pro - Ultimate Downloader")
        self.geometry("960x680")
        self.minsize(800, 580)
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

        # Animation state
        self._wave_speed   = 0.0   # 0 = idle, >0 = MB/s
        self._wave_phase   = 0.0
        self._anim_running = True

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._build_footer()

        self._start_wave_loop()

    # ── Settings persistence ──────────────────────────────────────────────────
    def _load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                # fill in any missing keys from defaults
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

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar, text="NOVA\nSTREAM",
            font=("Arial Black", 22, "bold"),
            text_color=self._pal["accent"]
        ).pack(pady=(30, 5))

        ctk.CTkLabel(
            self.sidebar, text="PRO",
            font=("Arial", 10),
            text_color="gray"
        ).pack(pady=(0, 20))

        # Folder section
        self._section_label(self.sidebar, "FOLDER")
        ctk.CTkButton(
            self.sidebar, text="⊕  Select Folder",
            fg_color=self._pal["accent"],
            hover_color=self._pal["accent_hover"],
            command=self.choose_path
        ).pack(pady=5, padx=20, fill="x")

        self.path_label = ctk.CTkLabel(
            self.sidebar, text="Saving to:\nDownloads",
            font=("Arial", 10), wraplength=190, text_color="gray"
        )
        self.path_label.pack(pady=(2, 4))

        ctk.CTkButton(
            self.sidebar, text="📂  Open Folder",
            fg_color="transparent",
            border_width=1,
            border_color=self._pal["accent"],
            text_color=self._pal["accent"],
            hover_color=self._pal["accent_dark"],
            command=self.open_folder
        ).pack(pady=5, padx=20, fill="x")

        # Subtitles section
        self._section_label(self.sidebar, "SUBTITLES")
        self.sub_en = ctk.CTkCheckBox(self.sidebar, text="English",
                                       checkmark_color=self._pal["accent"],
                                       hover_color=self._pal["accent_dark"])
        self.sub_en.pack(pady=3, padx=20, anchor="w")
        self.sub_fr = ctk.CTkCheckBox(self.sidebar, text="French",
                                       checkmark_color=self._pal["accent"],
                                       hover_color=self._pal["accent_dark"])
        self.sub_fr.pack(pady=3, padx=20, anchor="w")

        # Settings section
        self._section_label(self.sidebar, "SETTINGS")

        ctk.CTkLabel(self.sidebar, text="Theme", font=("Arial", 11)).pack(padx=20, anchor="w")
        self.theme_opt = ctk.CTkOptionMenu(
            self.sidebar, values=["dark", "light"],
            command=self._on_theme_change
        )
        self.theme_opt.set(self.settings["theme"])
        self.theme_opt.pack(pady=(2, 8), padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="Color Palette", font=("Arial", 11)).pack(padx=20, anchor="w")
        self.palette_opt = ctk.CTkOptionMenu(
            self.sidebar, values=list(PALETTES.keys()),
            command=self._on_palette_change
        )
        self.palette_opt.set(self.settings["palette"])
        self.palette_opt.pack(pady=(2, 8), padx=20, fill="x")

        ctk.CTkLabel(self.sidebar, text="MP3 Quality", font=("Arial", 11)).pack(padx=20, anchor="w")
        self.mp3_qual_opt = ctk.CTkOptionMenu(
            self.sidebar,
            values=["96 kbps (small)", "128 kbps (medium)", "192 kbps (high)", "320 kbps (best)"],
            command=self._on_mp3_quality_change
        )
        # Map stored value back to display string
        _q_map = {"96": "96 kbps (small)", "128": "128 kbps (medium)",
                   "192": "192 kbps (high)", "320": "320 kbps (best)"}
        self.mp3_qual_opt.set(_q_map.get(self.settings["mp3_quality"], "128 kbps (medium)"))
        self.mp3_qual_opt.pack(pady=(2, 8), padx=20, fill="x")

        self.auto_open_cb = ctk.CTkCheckBox(
            self.sidebar, text="Auto-open folder",
            checkmark_color=self._pal["accent"],
            hover_color=self._pal["accent_dark"],
            command=self._on_auto_open_toggle
        )
        if self.settings["auto_open"]:
            self.auto_open_cb.select()
        self.auto_open_cb.pack(pady=3, padx=20, anchor="w")

        self.show_speed_cb = ctk.CTkCheckBox(
            self.sidebar, text="Show speed label",
            checkmark_color=self._pal["accent"],
            hover_color=self._pal["accent_dark"],
            command=self._on_show_speed_toggle
        )
        if self.settings["show_speed"]:
            self.show_speed_cb.select()
        self.show_speed_cb.pack(pady=3, padx=20, anchor="w")

    def _section_label(self, parent, text):
        f = ctk.CTkFrame(parent, height=1, fg_color="gray30")
        f.pack(fill="x", padx=15, pady=(15, 4))
        ctk.CTkLabel(parent, text=text, font=("Arial", 10, "bold"), text_color="gray").pack(padx=20, anchor="w")

    # ── Main panel ────────────────────────────────────────────────────────────
    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=35, pady=20, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self.main, placeholder_text="🔗  Paste YouTube / any URL here...",
            height=50, font=("Arial", 13)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", pady=(10, 8))

        # Mode switch
        self.mode_switch = ctk.CTkSegmentedButton(
            self.main, values=["🎬  Video", "🎵  Audio (MP3)"],
            height=38,
            command=self._on_mode_change
        )
        self.mode_switch.set("🎬  Video")
        self.mode_switch.grid(row=1, column=0, sticky="ew", pady=4)

        self.quality_menu = ctk.CTkOptionMenu(
            self.main,
            values=["best", "1080p", "720p", "480p", "360p", "240p"],
            height=38
        )
        self.quality_menu.set("best")
        self.quality_menu.grid(row=2, column=0, pady=4)

        self.download_btn = ctk.CTkButton(
            self.main, text="▶  DOWNLOAD NOW",
            font=("Arial", 15, "bold"),
            height=52,
            fg_color=self._pal["accent"],
            hover_color=self._pal["accent_hover"],
            command=self.start_thread
        )
        self.download_btn.grid(row=3, column=0, sticky="ew", pady=16)

        # Progress
        self.progress_label = ctk.CTkLabel(
            self.main, text="Ready", font=("Arial", 12), anchor="w"
        )
        self.progress_label.grid(row=4, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self.main, progress_color=self._pal["accent"], height=12
        )
        self.progress_bar.grid(row=5, column=0, sticky="ew", pady=4)
        self.progress_bar.set(0)

        self.speed_label = ctk.CTkLabel(
            self.main, text="Speed: — ", font=("Arial", 10),
            text_color="gray", anchor="e"
        )
        self.speed_label.grid(row=6, column=0, sticky="e")

        # ── Visualizer canvas ─────────────────────────────────────────────
        self.canvas = ctk.CTkCanvas(
            self.main, height=90,
            bg=self._pal["canvas_bg"],
            highlightthickness=0
        )
        self.canvas.grid(row=7, column=0, sticky="ew", pady=8)

        # Log box
        self.log_box = ctk.CTkTextbox(
            self.main, height=130, font=("Consolas", 11)
        )
        self.log_box.grid(row=8, column=0, sticky="nsew", pady=(4, 0))
        self.main.grid_rowconfigure(8, weight=1)

    def _build_footer(self):
        self.footer = ctk.CTkLabel(
            self, text="Made by Rizinkovic",
            font=("Arial", 11, "underline"),
            cursor="hand2",
            text_color=self._pal["accent"]
        )
        self.footer.grid(row=1, column=0, columnspan=2, pady=8)
        self.footer.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Rizinkovic"))

    # ── Wave animation ────────────────────────────────────────────────────────
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

            speed = self._wave_speed
            # When idle: slow low-amplitude sine
            # When downloading: fast multi-wave
            t = time.monotonic()

            if speed <= 0:
                # idle – single gentle wave
                self._draw_single_wave(w, h, t, amplitude=6, freq=0.018,
                                       speed_mult=0.8, color=self._pal["wave2"], width=1)
            else:
                # active – 3 layered waves of different frequencies & phases
                amp = min(36, 6 + speed * 3.5)
                self._draw_single_wave(w, h, t, amplitude=amp * 0.55, freq=0.022,
                                       speed_mult=3.5, color=self._pal["wave2"], width=1, alpha_tag="w0")
                self._draw_single_wave(w, h, t, amplitude=amp * 0.80, freq=0.015,
                                       speed_mult=2.2, color=self._pal["wave1"], width=2, alpha_tag="w1",
                                       phase_offset=1.1)
                self._draw_single_wave(w, h, t, amplitude=amp * 0.40, freq=0.035,
                                       speed_mult=5.0, color=self._pal["wave3"], width=1, alpha_tag="w2",
                                       phase_offset=2.4)

        except Exception:
            pass

        self.after(30, self._draw_wave)

    def _draw_single_wave(self, w, h, t, amplitude, freq, speed_mult,
                          color, width, alpha_tag="w", phase_offset=0.0):
        cy = h / 2
        phase = t * speed_mult + phase_offset
        pts = []
        step = max(3, w // 120)
        for x in range(0, w + step, step):
            y = cy + amplitude * math.sin(x * freq + phase)
            pts.append(x)
            pts.append(y)
        if len(pts) >= 4:
            self.canvas.create_line(
                pts, fill=color, smooth=True,
                width=width, tags=alpha_tag
            )

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
        # Live-update accent widgets
        self.download_btn.configure(fg_color=p["accent"], hover_color=p["accent_hover"])
        self.progress_bar.configure(progress_color=p["accent"])
        self.canvas.configure(bg=p["canvas_bg"])
        self.footer.configure(text_color=p["accent"])
        # Sidebar buttons
        for child in self.sidebar.winfo_children():
            try:
                if isinstance(child, ctk.CTkButton):
                    t = child.cget("text")
                    if "Select" in t:
                        child.configure(fg_color=p["accent"], hover_color=p["accent_hover"])
                    elif "Open" in t:
                        child.configure(border_color=p["accent"], text_color=p["accent"],
                                        hover_color=p["accent_dark"])
            except:
                pass

    def _on_mp3_quality_change(self, v):
        kbps = v.split(" ")[0]
        self.settings["mp3_quality"] = kbps
        self._save_settings()

    def _on_auto_open_toggle(self):
        self.settings["auto_open"] = bool(self.auto_open_cb.get())
        self._save_settings()

    def _on_show_speed_toggle(self):
        self.settings["show_speed"] = bool(self.show_speed_cb.get())
        self._save_settings()
        self.speed_label.configure(text="Speed: — " if self.settings["show_speed"] else "")

    def _on_mode_change(self, v):
        is_audio = "Audio" in v
        if is_audio:
            self.quality_menu.configure(state="disabled")
        else:
            self.quality_menu.configure(state="normal")

    # ── File helpers ──────────────────────────────────────────────────────────
    def choose_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            display = os.path.basename(path) or path
            self.path_label.configure(text=f"Saving to:\n{display}")

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

    # ── Download logic ────────────────────────────────────────────────────────
    def start_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("1.0", "end")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Starting…")
        self._wave_speed = 0.5
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        mode = self.mode_switch.get()
        is_audio = "Audio" in mode
        q = self.quality_menu.get().replace("p", "")
        langs = [l for l, c in [("en", self.sub_en), ("fr", self.sub_fr)] if c.get()]

        opts = {
            "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
            "outtmpl": os.path.join(self.download_path, "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "writesubtitles": bool(langs),
            "subtitleslangs": langs if langs else [],
            "ignoreerrors": False,
            "quiet": True,
            "no_warnings": True,
        }

        if is_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": self.settings["mp3_quality"],
            }]
        else:
            opts["format"] = (
                f"bestvideo[height<={q}]+bestaudio/best"
                if q != "best" else "bestvideo+bestaudio/best"
            )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self._log("✔  Download complete!"))
            self.after(0, lambda: self.progress_label.configure(text="Done ✔"))
            self.after(0, lambda: self.progress_bar.set(1))
            if self.settings["auto_open"]:
                self.after(500, self.open_folder)
        except yt_dlp.utils.DownloadError as e:
            self.after(0, lambda: self._log(f"✘  Download error: {e}"))
            self.after(0, lambda: self.progress_label.configure(text="Error"))
        except Exception as e:
            self.after(0, lambda: self._log(f"✘  Unexpected error: {e}"))
            self.after(0, lambda: self.progress_label.configure(text="Error"))
        finally:
            self._wave_speed = 0.0
            self.after(0, lambda: self.download_btn.configure(state="normal"))

    def _progress_hook(self, d):
        status = d.get("status")
        if status == "downloading":
            raw_p = d.get("_percent_str", "0%").strip().rstrip("%")
            speed_str = d.get("_speed_str", "—")
            try:
                pct = float(raw_p) / 100.0
            except ValueError:
                pct = 0.0
            # Parse speed for wave animation
            try:
                if "MiB" in speed_str or "MB" in speed_str:
                    num = float(speed_str.split("M")[0].strip())
                elif "KiB" in speed_str or "KB" in speed_str:
                    num = float(speed_str.split("K")[0].strip()) / 1024.0
                else:
                    num = 0.5
                self._wave_speed = max(0.3, min(num, 15.0))
            except Exception:
                self._wave_speed = 0.5

            def _ui_update():
                self.progress_bar.set(pct)
                self.progress_label.configure(text=f"Downloading:  {raw_p}%")
                if self.settings["show_speed"]:
                    self.speed_label.configure(text=f"Speed:  {speed_str}")

            self.after(0, _ui_update)

        elif status == "finished":
            self._wave_speed = 0.2
            self.after(0, lambda: self.progress_label.configure(text="Finalizing…"))

    def _log(self, msg: str):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def on_closing(self):
        self._anim_running = False
        self.destroy()


if __name__ == "__main__":
    app = NovaStreamPro()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()