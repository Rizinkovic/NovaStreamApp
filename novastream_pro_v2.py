"""
NovaStream Pro - Ultimate Downloader
Author : Rizinkovic
Security : URL validation, path sanitization, no shell injection, sandboxed yt-dlp opts
"""

import customtkinter as ctk
import yt_dlp
import threading
import os
import sys
import re
import subprocess
import webbrowser
import json
import math
import time
from urllib.parse import urlparse
from tkinter import filedialog
import imageio_ffmpeg

# ── DPI awareness (Windows) ──────────────────────────────────────────────────
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# ── Constants ────────────────────────────────────────────────────────────────
CONFIG_FILE  = os.path.join(os.path.expanduser("~"), ".novastream_settings.json")
FONT_MONO    = "Courier New"
FONT_SM      = 11
FONT_MD      = 13
FONT_LG      = 15
FONT_XL      = 20

# ── Security: allowed URL schemes ────────────────────────────────────────────
ALLOWED_SCHEMES = {"http", "https"}

# ── Palettes ─────────────────────────────────────────────────────────────────
PALETTES = {
    "blueish-white": {
        "accent":       "#3B8ED0",
        "accent_dark":  "#1f538d",
        "accent_hover": "#5aaee8",
        "wave1": "#3B8ED0", "wave2": "#1f538d", "wave3": "#5aaee8",
        "canvas_bg": "#0d1b2a",
        "ctk_theme": "blue",
    },
    "greenish-white": {
        "accent":       "#27AE60",
        "accent_dark":  "#1a6b3a",
        "accent_hover": "#52c985",
        "wave1": "#27AE60", "wave2": "#1a6b3a", "wave3": "#52c985",
        "canvas_bg": "#0b1c10",
        "ctk_theme": "green",
    },
    "dark-pink": {
        "accent":       "#E91E63",
        "accent_dark":  "#880E4F",
        "accent_hover": "#f06292",
        "wave1": "#E91E63", "wave2": "#880E4F", "wave3": "#f48fb1",
        "canvas_bg": "#1a0010",
        "ctk_theme": "blue",
    },
    "dark-orange": {
        "accent":       "#F57C00",
        "accent_dark":  "#8B4500",
        "accent_hover": "#ffab40",
        "wave1": "#F57C00", "wave2": "#8B4500", "wave3": "#ffcc80",
        "canvas_bg": "#1a0d00",
        "ctk_theme": "blue",
    },
}

# ── Translations ──────────────────────────────────────────────────────────────
STRINGS = {
    "en": {
        "title":         "NovaStream Pro - Ultimate Downloader",
        "pro_sub":       "PRO",
        "sec_folder":    "FOLDER",
        "sec_subtitles": "SUBTITLES",
        "sec_settings":  "SETTINGS",
        "select_folder": "⊕  Select Folder",
        "saving_to":     "Saving to:\n{}",
        "open_folder":   "📂  Open Folder",
        "sub_en":        "English",
        "sub_fr":        "French",
        "theme_lbl":     "Theme",
        "theme_dark":    "dark",
        "theme_light":   "light",
        "palette_lbl":   "Color Palette",
        "mp3_lbl":       "MP3 Quality",
        "mp3_vals":      ["96 kbps (small)", "128 kbps (medium)", "192 kbps (high)", "320 kbps (best)"],
        "lang_lbl":      "Language",
        "auto_open":     "Auto-open folder",
        "show_speed":    "Show speed",
        "mode_video":    "🎬  Video",
        "mode_audio":    "🎵  Audio (MP3)",
        "dl_btn":        "▶  DOWNLOAD NOW",
        "ready":         "Ready",
        "speed_idle":    "Speed: —",
        "starting":      "Starting…",
        "downloading":   "Downloading:  {}%",
        "finalizing":    "Finalizing…",
        "done":          "Done ✔",
        "error":         "Error",
        "log_success":   "✔  Download complete!",
        "log_dl_err":    "✘  Download error: {}",
        "log_err":       "✘  Unexpected error: {}",
        "log_folder_err":"Cannot open folder: {}",
        "log_url_bad":   "✘  Invalid or unsafe URL. Only http/https links are accepted.",
        "footer":        "Made by Rizinkovic",
    },
    "fr": {
        "title":         "NovaStream Pro - Téléchargeur Ultime",
        "pro_sub":       "PRO",
        "sec_folder":    "DOSSIER",
        "sec_subtitles": "SOUS-TITRES",
        "sec_settings":  "PARAMÈTRES",
        "select_folder": "⊕  Choisir un dossier",
        "saving_to":     "Enregistrer dans :\n{}",
        "open_folder":   "📂  Ouvrir le dossier",
        "sub_en":        "Anglais",
        "sub_fr":        "Français",
        "theme_lbl":     "Thème",
        "theme_dark":    "sombre",
        "theme_light":   "clair",
        "palette_lbl":   "Palette de couleurs",
        "mp3_lbl":       "Qualité MP3",
        "mp3_vals":      ["96 kbps (léger)", "128 kbps (moyen)", "192 kbps (haute)", "320 kbps (max)"],
        "lang_lbl":      "Langue",
        "auto_open":     "Ouvrir le dossier auto.",
        "show_speed":    "Afficher la vitesse",
        "mode_video":    "🎬  Vidéo",
        "mode_audio":    "🎵  Audio (MP3)",
        "dl_btn":        "▶  TÉLÉCHARGER",
        "ready":         "Prêt",
        "speed_idle":    "Vitesse : —",
        "starting":      "Démarrage…",
        "downloading":   "Téléchargement :  {}%",
        "finalizing":    "Finalisation…",
        "done":          "Terminé ✔",
        "error":         "Erreur",
        "log_success":   "✔  Téléchargement terminé !",
        "log_dl_err":    "✘  Erreur de téléchargement : {}",
        "log_err":       "✘  Erreur inattendue : {}",
        "log_folder_err":"Impossible d'ouvrir le dossier : {}",
        "log_url_bad":   "✘  URL invalide ou dangereuse. Seuls les liens http/https sont acceptés.",
        "footer":        "Fait par Rizinkovic",
    },
}

DEFAULT_SETTINGS = {
    "theme":       "dark",
    "palette":     "blueish-white",
    "auto_open":   False,
    "show_speed":  True,
    "mp3_quality": "128",
    "language":    "en",
}

# Map every possible MP3 label (both languages) → kbps string
MP3_LABEL_TO_KBPS = {
    "96 kbps (small)":  "96",  "128 kbps (medium)": "128",
    "192 kbps (high)":  "192", "320 kbps (best)":   "320",
    "96 kbps (léger)":  "96",  "128 kbps (moyen)":  "128",
    "192 kbps (haute)": "192", "320 kbps (max)":    "320",
}


# ── Security helpers ──────────────────────────────────────────────────────────
def sanitize_url(raw: str):
    """Return cleaned URL string, or None if unsafe/invalid."""
    url = raw.strip()
    if re.search(r'[;&|`$<>\'"\\]', url):
        return None
    try:
        p = urlparse(url)
    except Exception:
        return None
    if p.scheme not in ALLOWED_SCHEMES:
        return None
    if not p.netloc:
        return None
    return url


def sanitize_path(path: str) -> str:
    """Resolve and expand path; raise ValueError on null bytes."""
    if "\x00" in path:
        raise ValueError("Null byte in path")
    return os.path.realpath(os.path.expanduser(path))


def get_resource_path(relative_path: str) -> str:
    try:
        base = sys._MEIPASS  # type: ignore[attr-defined]
    except AttributeError:
        base = os.path.abspath(".")
    return os.path.join(base, relative_path)


# ── App ───────────────────────────────────────────────────────────────────────
class NovaStreamPro(ctk.CTk):

    def __init__(self):
        super().__init__()

        # Load settings & active translation
        self.settings   = self._load_settings()
        self._pal       = PALETTES[self.settings["palette"]]
        self._lang      = self.settings["language"]
        self._t         = STRINGS[self._lang]

        # Apply CTK global appearance BEFORE any widget is created
        ctk.set_appearance_mode(self.settings["theme"])
        ctk.set_default_color_theme(self._pal["ctk_theme"])

        # Icon
        icon = get_resource_path("icon.ico")
        if os.path.exists(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass

        self.title(self._t["title"])
        self.geometry("980x710")
        self.minsize(820, 600)

        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self._wave_speed   = 0.0
        self._anim_running = True

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._build_footer()
        self._start_wave_loop()

    # ── Translate shortcut ────────────────────────────────────────────────────
    def _(self, key: str, *args) -> str:
        val = self._t.get(key, key)
        return val.format(*args) if args else val

    # ── Settings I/O ─────────────────────────────────────────────────────────
    def _load_settings(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("corrupt")
                for k, v in DEFAULT_SETTINGS.items():
                    data.setdefault(k, v)
                # Guard unknowns
                if data["palette"]  not in PALETTES: data["palette"]  = DEFAULT_SETTINGS["palette"]
                if data["language"] not in STRINGS:  data["language"] = DEFAULT_SETTINGS["language"]
                return data
            except Exception:
                pass
        return dict(DEFAULT_SETTINGS)

    def _save_settings(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── Widget style helpers ──────────────────────────────────────────────────
    def _accent(self) -> dict:
        return {"fg_color": self._pal["accent"],
                "hover_color": self._pal["accent_hover"],
                "text_color": "#ffffff"}

    def _outline(self) -> dict:
        return {"fg_color": "transparent",
                "border_width": 1,
                "border_color": self._pal["accent"],
                "text_color": self._pal["accent"],
                "hover_color": self._pal["accent_dark"]}

    def _chk(self) -> dict:
        return {"checkmark_color": self._pal["accent"],
                "hover_color": self._pal["accent_dark"],
                "border_color": self._pal["accent"]}

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=242, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo — always blueish at startup (default palette), colour updated by _apply_palette
        self.logo_lbl = ctk.CTkLabel(
            self.sidebar, text="NOVA\nSTREAM",
            font=(FONT_MONO, FONT_XL, "bold"),
            text_color=self._pal["accent"],
        )
        self.logo_lbl.pack(pady=(26, 2))

        self.pro_lbl = ctk.CTkLabel(
            self.sidebar, text=self._("pro_sub"),
            font=(FONT_MONO, FONT_SM), text_color="gray",
        )
        self.pro_lbl.pack(pady=(0, 14))

        # ── Folder ────────────────────────────────────────────────────────────
        self._sb_section_labels = []
        self._sec_folder = self._sb_divider("sec_folder")

        self.sel_btn = ctk.CTkButton(
            self.sidebar, text=self._("select_folder"),
            font=(FONT_MONO, FONT_SM), **self._accent(),
            command=self.choose_path,
        )
        self.sel_btn.pack(pady=5, padx=18, fill="x")

        self.path_label = ctk.CTkLabel(
            self.sidebar, text=self._("saving_to", "Downloads"),
            font=(FONT_MONO, FONT_SM - 1), wraplength=205, text_color="gray",
        )
        self.path_label.pack(pady=(2, 4))

        self.open_btn = ctk.CTkButton(
            self.sidebar, text=self._("open_folder"),
            font=(FONT_MONO, FONT_SM), **self._outline(),
            command=self.open_folder,
        )
        self.open_btn.pack(pady=5, padx=18, fill="x")

        # ── Subtitles ─────────────────────────────────────────────────────────
        self._sec_subs = self._sb_divider("sec_subtitles")

        self.sub_en = ctk.CTkCheckBox(
            self.sidebar, text=self._("sub_en"),
            font=(FONT_MONO, FONT_SM), **self._chk(),
        )
        self.sub_en.pack(pady=3, padx=18, anchor="w")

        self.sub_fr_cb = ctk.CTkCheckBox(
            self.sidebar, text=self._("sub_fr"),
            font=(FONT_MONO, FONT_SM), **self._chk(),
        )
        self.sub_fr_cb.pack(pady=3, padx=18, anchor="w")

        # ── Settings ──────────────────────────────────────────────────────────
        self._sec_cfg = self._sb_divider("sec_settings")

        # Theme
        self.theme_lbl_w = self._sb_label("theme_lbl")
        self.theme_opt = ctk.CTkOptionMenu(
            self.sidebar,
            values=[self._("theme_dark"), self._("theme_light")],
            font=(FONT_MONO, FONT_SM),
            command=self._on_theme_change,
        )
        self.theme_opt.set(
            self._("theme_dark") if self.settings["theme"] == "dark"
            else self._("theme_light")
        )
        self.theme_opt.pack(pady=(2, 8), padx=18, fill="x")

        # Palette
        self.palette_lbl_w = self._sb_label("palette_lbl")
        self.palette_opt = ctk.CTkOptionMenu(
            self.sidebar, values=list(PALETTES.keys()),
            font=(FONT_MONO, FONT_SM),
            command=self._on_palette_change,
        )
        self.palette_opt.set(self.settings["palette"])
        self.palette_opt.pack(pady=(2, 8), padx=18, fill="x")

        # MP3 quality
        self.mp3_lbl_w = self._sb_label("mp3_lbl")
        mp3_vals = self._("mp3_vals")
        kbps_rev = {v: k for k, v in MP3_LABEL_TO_KBPS.items() if k in mp3_vals}
        self.mp3_opt = ctk.CTkOptionMenu(
            self.sidebar, values=mp3_vals,
            font=(FONT_MONO, FONT_SM),
            command=self._on_mp3_quality_change,
        )
        self.mp3_opt.set(kbps_rev.get(self.settings["mp3_quality"], mp3_vals[1]))
        self.mp3_opt.pack(pady=(2, 8), padx=18, fill="x")

        # Language
        self.lang_lbl_w = self._sb_label("lang_lbl")
        self.lang_opt = ctk.CTkOptionMenu(
            self.sidebar, values=["English", "Français"],
            font=(FONT_MONO, FONT_SM),
            command=self._on_language_change,
        )
        self.lang_opt.set("English" if self.settings["language"] == "en" else "Français")
        self.lang_opt.pack(pady=(2, 8), padx=18, fill="x")

        # Toggles
        self.auto_open_cb = ctk.CTkCheckBox(
            self.sidebar, text=self._("auto_open"),
            font=(FONT_MONO, FONT_SM), **self._chk(),
            command=self._on_auto_open_toggle,
        )
        if self.settings["auto_open"]:
            self.auto_open_cb.select()
        self.auto_open_cb.pack(pady=3, padx=18, anchor="w")

        self.show_speed_cb = ctk.CTkCheckBox(
            self.sidebar, text=self._("show_speed"),
            font=(FONT_MONO, FONT_SM), **self._chk(),
            command=self._on_show_speed_toggle,
        )
        if self.settings["show_speed"]:
            self.show_speed_cb.select()
        self.show_speed_cb.pack(pady=3, padx=18, anchor="w")

        # Collect refs for full palette refresh
        self._accent_btns  = [self.sel_btn]
        self._outline_btns = [self.open_btn]
        self._checkboxes   = [self.sub_en, self.sub_fr_cb, self.auto_open_cb, self.show_speed_cb]
        self._optionmenus  = [self.theme_opt, self.palette_opt, self.mp3_opt,
                               self.lang_opt]

    def _sb_divider(self, key: str) -> ctk.CTkLabel:
        ctk.CTkFrame(self.sidebar, height=1, fg_color="gray30").pack(
            fill="x", padx=14, pady=(14, 3)
        )
        lbl = ctk.CTkLabel(
            self.sidebar, text=self._(key),
            font=(FONT_MONO, FONT_SM - 1, "bold"), text_color="gray",
        )
        lbl.pack(padx=18, anchor="w")
        self._sb_section_labels.append((lbl, key))
        return lbl

    def _sb_label(self, key: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            self.sidebar, text=self._(key),
            font=(FONT_MONO, FONT_SM), anchor="w",
        )
        lbl.pack(padx=18, anchor="w")
        return lbl

    # ── Main panel ────────────────────────────────────────────────────────────
    def _build_main(self):
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=36, pady=20, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self.main,
            placeholder_text="🔗  https://youtube.com/watch?v=...",
            height=52, font=(FONT_MONO, FONT_MD),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", pady=(6, 8))

        self.mode_switch = ctk.CTkSegmentedButton(
            self.main,
            values=[self._("mode_video"), self._("mode_audio")],
            height=42, font=(FONT_MONO, FONT_MD),
            command=self._on_mode_change,
        )
        self.mode_switch.set(self._("mode_video"))
        self.mode_switch.grid(row=1, column=0, sticky="ew", pady=4)

        self.quality_menu = ctk.CTkOptionMenu(
            self.main,
            values=["best", "1080p", "720p", "480p", "360p", "240p"],
            height=40, font=(FONT_MONO, FONT_MD),
        )
        self.quality_menu.set("best")
        self.quality_menu.grid(row=2, column=0, pady=4)

        self.download_btn = ctk.CTkButton(
            self.main, text=self._("dl_btn"),
            font=(FONT_MONO, FONT_LG, "bold"),
            height=56, **self._accent(),
            command=self.start_thread,
        )
        self.download_btn.grid(row=3, column=0, sticky="ew", pady=14)

        self.progress_label = ctk.CTkLabel(
            self.main, text=self._("ready"),
            font=(FONT_MONO, FONT_MD), anchor="w",
        )
        self.progress_label.grid(row=4, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(
            self.main, progress_color=self._pal["accent"], height=14,
        )
        self.progress_bar.grid(row=5, column=0, sticky="ew", pady=4)
        self.progress_bar.set(0)

        self.speed_label = ctk.CTkLabel(
            self.main, text=self._("speed_idle"),
            font=(FONT_MONO, FONT_SM), text_color="gray", anchor="e",
        )
        self.speed_label.grid(row=6, column=0, sticky="e")

        self.canvas = ctk.CTkCanvas(
            self.main, height=92,
            bg=self._pal["canvas_bg"],
            highlightthickness=0,
        )
        self.canvas.grid(row=7, column=0, sticky="ew", pady=8)

        self.log_box = ctk.CTkTextbox(
            self.main, height=130, font=(FONT_MONO, FONT_SM),
        )
        self.log_box.grid(row=8, column=0, sticky="nsew", pady=(4, 0))
        self.main.grid_rowconfigure(8, weight=1)

    def _build_footer(self):
        self.footer = ctk.CTkLabel(
            self, text=self._("footer"),
            font=(FONT_MONO, FONT_SM, "underline"),
            cursor="hand2", text_color=self._pal["accent"],
        )
        self.footer.grid(row=1, column=0, columnspan=2, pady=8)
        self.footer.bind("<Button-1>",
                         lambda e: webbrowser.open("https://github.com/Rizinkovic"))

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
            t = time.monotonic()
            s = self._wave_speed
            if s <= 0:
                self._wave_line(w, h, t, amp=5,        freq=0.018, sp=0.8,
                                color=self._pal["wave2"], lw=1)
            else:
                amp = min(36, 6 + s * 3.2)
                self._wave_line(w, h, t, amp * 0.50, 0.022, 3.5,
                                self._pal["wave2"], lw=1)
                self._wave_line(w, h, t, amp * 0.85, 0.015, 2.2,
                                self._pal["wave1"], lw=2, phase=1.1)
                self._wave_line(w, h, t, amp * 0.40, 0.036, 5.0,
                                self._pal["wave3"], lw=1, phase=2.5)
        except Exception:
            pass
        self.after(30, self._draw_wave)

    def _wave_line(self, w, h, t, amp, freq, sp, color, lw, phase=0.0):
        cy   = h / 2
        step = max(3, w // 130)
        pts  = []
        for x in range(0, w + step, step):
            pts.extend((x, cy + amp * math.sin(x * freq + t * sp + phase)))
        if len(pts) >= 4:
            self.canvas.create_line(pts, fill=color, smooth=True, width=lw)

    # ── Full palette repaint ──────────────────────────────────────────────────
    def _apply_palette(self):
        p = self._pal
        self.canvas.configure(bg=p["canvas_bg"])
        self.progress_bar.configure(progress_color=p["accent"])
        self.download_btn.configure(fg_color=p["accent"],
                                    hover_color=p["accent_hover"],
                                    text_color="#ffffff")
        self.footer.configure(text_color=p["accent"])
        self.logo_lbl.configure(text_color=p["accent"])

        for btn in self._accent_btns:
            btn.configure(fg_color=p["accent"], hover_color=p["accent_hover"],
                          text_color="#ffffff")
        for btn in self._outline_btns:
            btn.configure(border_color=p["accent"], text_color=p["accent"],
                          hover_color=p["accent_dark"])
        for cb in self._checkboxes:
            cb.configure(checkmark_color=p["accent"],
                         hover_color=p["accent_dark"],
                         border_color=p["accent"])
        for om in self._optionmenus + [self.quality_menu]:
            try:
                om.configure(button_color=p["accent"],
                             button_hover_color=p["accent_hover"])
            except Exception:
                pass

    # ── Full language repaint ─────────────────────────────────────────────────
    def _apply_language(self):
        t = self._t
        self.title(t["title"])
        self.pro_lbl.configure(text=t["pro_sub"])
        display = os.path.basename(self.download_path) or self.download_path
        self.path_label.configure(text=t["saving_to"].format(display))
        self.sel_btn.configure(text=t["select_folder"])
        self.open_btn.configure(text=t["open_folder"])
        self.sub_en.configure(text=t["sub_en"])
        self.sub_fr_cb.configure(text=t["sub_fr"])
        self.theme_lbl_w.configure(text=t["theme_lbl"])
        self.palette_lbl_w.configure(text=t["palette_lbl"])
        self.mp3_lbl_w.configure(text=t["mp3_lbl"])
        self.lang_lbl_w.configure(text=t["lang_lbl"])
        self.auto_open_cb.configure(text=t["auto_open"])
        self.show_speed_cb.configure(text=t["show_speed"])

        # Section divider labels
        for lbl, key in self._sb_section_labels:
            lbl.configure(text=t[key])

        # Theme dropdown — keep current selection
        self.theme_opt.configure(values=[t["theme_dark"], t["theme_light"]])
        self.theme_opt.set(
            t["theme_dark"] if self.settings["theme"] == "dark" else t["theme_light"]
        )

        # MP3 dropdown
        mp3_vals = t["mp3_vals"]
        self.mp3_opt.configure(values=mp3_vals)
        kbps_rev = {v: k for k, v in MP3_LABEL_TO_KBPS.items() if k in mp3_vals}
        self.mp3_opt.set(kbps_rev.get(self.settings["mp3_quality"], mp3_vals[1]))

        # Mode switch — keep current mode
        cur_audio = self._("mode_audio") in self.mode_switch.get() or "MP3" in self.mode_switch.get()
        self.mode_switch.configure(values=[t["mode_video"], t["mode_audio"]])
        self.mode_switch.set(t["mode_audio"] if cur_audio else t["mode_video"])

        self.download_btn.configure(text=t["dl_btn"])
        self.progress_label.configure(text=t["ready"])
        self.speed_label.configure(text=t["speed_idle"])
        self.footer.configure(text=t["footer"])

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_theme_change(self, v: str):
        is_dark = (v == self._("theme_dark"))
        internal = "dark" if is_dark else "light"
        self.settings["theme"] = internal
        self._save_settings()
        ctk.set_appearance_mode(internal)

    def _on_palette_change(self, v: str):
        if v not in PALETTES:
            return
        self.settings["palette"] = v
        self._save_settings()
        self._pal = PALETTES[v]
        self._apply_palette()

    def _on_mp3_quality_change(self, v: str):
        self.settings["mp3_quality"] = MP3_LABEL_TO_KBPS.get(v, "128")
        self._save_settings()

    def _on_language_change(self, v: str):
        lang = "en" if v == "English" else "fr"
        self.settings["language"] = lang
        self._save_settings()
        self._lang = lang
        self._t    = STRINGS[lang]
        self._apply_language()

    def _on_auto_open_toggle(self):
        self.settings["auto_open"] = bool(self.auto_open_cb.get())
        self._save_settings()

    def _on_show_speed_toggle(self):
        self.settings["show_speed"] = bool(self.show_speed_cb.get())
        self._save_settings()
        self.speed_label.configure(
            text=self._("speed_idle") if self.settings["show_speed"] else ""
        )

    def _on_mode_change(self, v: str):
        is_audio = "MP3" in v or self._("mode_audio") in v
        self.quality_menu.configure(state="disabled" if is_audio else "normal")

    # ── File helpers ──────────────────────────────────────────────────────────
    def choose_path(self):
        path = filedialog.askdirectory()
        if path:
            try:
                self.download_path = sanitize_path(path)
            except ValueError:
                return
            display = os.path.basename(self.download_path) or self.download_path
            self.path_label.configure(text=self._("saving_to", display))

    def open_folder(self):
        try:
            safe = sanitize_path(self.download_path)
            if os.name == "nt":
                os.startfile(safe)
            elif sys.platform == "darwin":
                subprocess.call(["open", safe])
            else:
                subprocess.call(["xdg-open", safe])
        except Exception as e:
            self._log(self._("log_folder_err", e))

    # ── Download ──────────────────────────────────────────────────────────────
    def start_thread(self):
        url = sanitize_url(self.url_entry.get())
        if not url:
            self._log(self._("log_url_bad"))
            return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("1.0", "end")
        self.progress_bar.set(0)
        self.progress_label.configure(text=self._("starting"))
        self._wave_speed = 0.5
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url: str):
        is_audio = "MP3" in self.mode_switch.get() or self._("mode_audio") in self.mode_switch.get()
        q        = self.quality_menu.get().replace("p", "")
        langs    = [lc for lc, cb in [("en", self.sub_en), ("fr", self.sub_fr_cb)] if cb.get()]

        try:
            safe_out = sanitize_path(self.download_path)
        except ValueError as e:
            msg = str(e)
            self.after(0, lambda: self._log(self._("log_err", msg)))
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            return

        opts = {
            "ffmpeg_location":    imageio_ffmpeg.get_ffmpeg_exe(),
            "outtmpl":            os.path.join(safe_out, "%(title)s.%(ext)s"),
            "progress_hooks":     [self._progress_hook],
            "writesubtitles":     bool(langs),
            "subtitleslangs":     langs or [],
            "ignoreerrors":       False,
            "quiet":              True,
            "no_warnings":        True,
            "postprocessor_args": [],        # prevent injection via args
            "nocheckcertificate": False,     # keep TLS verification ON
        }

        if is_audio:
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": self.settings["mp3_quality"],
            }]
        else:
            # Force mp4: prefer h264+aac; fall back gracefully
            if q == "best":
                fmt = (
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                    "/bestvideo[ext=mp4]+bestaudio"
                    "/bestvideo+bestaudio/best"
                )
            else:
                fmt = (
                    f"bestvideo[height<={q}][ext=mp4]+bestaudio[ext=m4a]"
                    f"/bestvideo[height<={q}][ext=mp4]+bestaudio"
                    f"/bestvideo[height<={q}]+bestaudio/best"
                )
            opts["format"]               = fmt
            opts["merge_output_format"]  = "mp4"

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self._log(self._("log_success")))
            self.after(0, lambda: self.progress_label.configure(text=self._("done")))
            self.after(0, lambda: self.progress_bar.set(1))
            if self.settings["auto_open"]:
                self.after(600, self.open_folder)
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            self.after(0, lambda: self._log(self._("log_dl_err", msg)))
            self.after(0, lambda: self.progress_label.configure(text=self._("error")))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._log(self._("log_err", msg)))
            self.after(0, lambda: self.progress_label.configure(text=self._("error")))
        finally:
            self._wave_speed = 0.0
            self.after(0, lambda: self.download_btn.configure(state="normal"))

    def _progress_hook(self, d: dict):
        status = d.get("status")
        if status == "downloading":
            raw_p     = d.get("_percent_str", "0%").strip().rstrip("%")
            speed_str = d.get("_speed_str") or "—"
            try:
                pct = max(0.0, min(float(raw_p) / 100.0, 1.0))
            except ValueError:
                pct = 0.0
            # Parse speed for wave amplitude
            try:
                if "MiB" in speed_str or "MB" in speed_str:
                    num = float(re.sub(r"[^\d.]", "", speed_str.split("M")[0]))
                elif "KiB" in speed_str or "KB" in speed_str:
                    num = float(re.sub(r"[^\d.]", "", speed_str.split("K")[0])) / 1024
                else:
                    num = 0.5
                self._wave_speed = max(0.3, min(num, 15.0))
            except Exception:
                self._wave_speed = 0.5

            dl_text  = self._("downloading", raw_p)
            show_spd = self.settings["show_speed"]
            spd_text = speed_str

            def _ui():
                self.progress_bar.set(pct)
                self.progress_label.configure(text=dl_text)
                if show_spd:
                    self.speed_label.configure(text=f"  {spd_text}")

            self.after(0, _ui)

        elif status == "finished":
            self._wave_speed = 0.2
            self.after(0, lambda: self.progress_label.configure(text=self._("finalizing")))

    def _log(self, msg: str):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    def on_closing(self):
        self._anim_running = False
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = NovaStreamPro()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()