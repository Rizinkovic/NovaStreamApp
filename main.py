import customtkinter as ctk
import yt_dlp
import threading
import os
import sys
import subprocess
import webbrowser
from tkinter import filedialog
import imageio_ffmpeg

# DPI awareness prevents blurry text on high-res monitors
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class NovaStreamPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Safe Icon Loading
        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass # Fail silently if OS rejects icon format

        self.title("NovaStream Pro - Ultimate Downloader")
        self.geometry("900x650")
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")

        # Grid config
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="NOVA STREAM", font=("Arial", 22, "bold")).pack(pady=30)
        
        ctk.CTkButton(self.sidebar, text="Select Folder", command=self.choose_path).pack(pady=10, padx=20)
        self.path_label = ctk.CTkLabel(self.sidebar, text="Saving to:\nDownloads", font=("Arial", 11), wraplength=180)
        self.path_label.pack(pady=5)

        ctk.CTkButton(self.sidebar, text="Open Folder", command=self.open_folder).pack(pady=10, padx=20)

        ctk.CTkLabel(self.sidebar, text="Subtitles", font=("Arial", 14, "bold")).pack(pady=(30, 10))
        self.sub_en = ctk.CTkCheckBox(self.sidebar, text="English")
        self.sub_en.pack(pady=5)
        self.sub_fr = ctk.CTkCheckBox(self.sidebar, text="French")
        self.sub_fr.pack(pady=5)

        # --- Main UI ---
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, padx=40, pady=20, sticky="nsew")

        self.url_entry = ctk.CTkEntry(self.main, placeholder_text="Paste URL here...", height=50)
        self.url_entry.pack(fill="x", pady=20)

        self.quality_menu = ctk.CTkOptionMenu(self.main, values=["best", "1080p", "720p", "480p", "360p", "240p"], height=40)
        self.quality_menu.pack(pady=10)
        self.quality_menu.set("best")

        self.download_btn = ctk.CTkButton(self.main, text="DOWNLOAD NOW", font=("Arial", 16, "bold"), height=50, command=self.start_thread)
        self.download_btn.pack(fill="x", pady=20)

        self.progress_label = ctk.CTkLabel(self.main, text="Ready", font=("Arial", 13))
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(self.main)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)

        self.speed_label = ctk.CTkLabel(self.main, text="Speed: 0 MB/s", font=("Arial", 11), text_color="gray")
        self.speed_label.pack(anchor="e")

        self.log_box = ctk.CTkTextbox(self.main, height=150)
        self.log_box.pack(fill="both", expand=True, pady=20)

        # --- Footer ---
        self.footer = ctk.CTkLabel(self, text="Made By Rizinkovic", font=("Arial", 12, "underline"), cursor="hand2", text_color="#1f538d")
        self.footer.grid(row=1, column=0, columnspan=2, pady=10)
        self.footer.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/Rizinkovic"))

    def choose_path(self):
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            self.path_label.configure(text=f"Saving to:\n{os.path.basename(path)}")

    def open_folder(self):
        os.startfile(self.download_path) if os.name == 'nt' else subprocess.call(['open', self.download_path])

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').strip('% ')
            speed = d.get('_speed_str', '0 MB/s')
            try:
                self.after(0, lambda: self._update_progress(float(p)/100, p, speed))
            except: pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.progress_label.configure(text="Finalizing..."))

    def _update_progress(self, val, p, speed):
        self.progress_bar.set(val)
        self.progress_label.configure(text=f"Downloading: {p}%")
        self.speed_label.configure(text=f"Speed: {speed}")

    def start_thread(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.download_btn.configure(state="disabled")
        self.log_box.delete("1.0", "end")
        threading.Thread(target=self.download_video, args=(url,), daemon=True).start()

    def download_video(self, url):
        q = self.quality_menu.get().replace("p", "")
        langs = [l for l, c in [('en', self.sub_en), ('fr', self.sub_fr)] if c.get()]
        
        opts = {
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
            'format': f'bestvideo[height<={q}]+bestaudio/best' if q != "best" else "best",
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'progress_hooks': [self.progress_hook],
            'writesubtitles': bool(langs),
            'subtitleslangs': langs,
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.after(0, lambda: self.log_box.insert("end", "SUCCESS: Saved!"))
        except Exception as e:
            self.after(0, lambda: self.log_box.insert("end", f"ERROR: {str(e)}"))
        finally:
            self.after(0, lambda: self.download_btn.configure(state="normal"))

if __name__ == "__main__":
    app = NovaStreamPro()
    app.mainloop()