import os
import sys
import subprocess
import queue
import webbrowser
from urllib.parse import urlsplit
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from platform_runtime import resource_path, install_instructions, open_directory, scroll_units, ffmpeg_path


BG = "#101113"
PANEL = "#191b1f"
PANEL2 = "#25282e"
TEXT = "#f4f1eb"
MUTED = "#a5a7ad"
ACCENT = "#d8bc86"
GREEN = "#53d6a0"
FONT_FAMILY = "Helvetica Neue" if sys.platform == "darwin" else "Segoe UI"


PLATFORMS = (
    ("YouTube", "Youtube", "youtube", "#ff6378"),
    ("TikTok", "TikTok", "tiktok", "#61ded8"),
    ("Facebook", "Facebook", "facebook", "#689fff"),
    ("Instagram", "Instagram", "instagram", "#e98ac5"),
    ("X / Twitter", "Twitter", "twitter", "#cbd5e1"),
    ("Reddit", "Reddit", "reddit", "#ff976f"),
    ("Vimeo", "Vimeo", "vimeo", "#70ceef"),
    ("Dailymotion", "Dailymotion", "dailymotion", "#a899ff"),
    ("Twitch", "TwitchClips", "twitch", "#bd93ff"),
    ("Bilibili", "BiliBili", "bilibili", "#78c8ee"),
    ("Pinterest", "Pinterest", "pinterest", "#ff8697"),
)


def platform_support():
    """Inspect local extractors; this is not a network availability test."""
    try:
        from yt_dlp.extractor import get_info_extractor
        from yt_dlp.version import __version__
    except ImportError:
        return "ยังไม่ได้ติดตั้ง yt-dlp", {name: "missing" for name, *_ in PLATFORMS}
    states = {}
    for name, key, *_ in PLATFORMS:
        try:
            states[name] = "supported" if get_info_extractor(key).working() else "broken"
        except (KeyError, AttributeError, ImportError):
            states[name] = "missing"
    return __version__, states


def download_error(exc):
    detail = str(exc)
    lower = detail.lower()
    if "unsupported url" in lower:
        hint = "ยังไม่รองรับลิงก์นี้ ลองใช้ลิงก์คลิปโดยตรงหรืออัปเดตผ่าน install.bat"
    elif "drm" in lower:
        hint = "คลิปนี้มี DRM โปรแกรมไม่รองรับการดาวน์โหลดเนื้อหานี้"
    elif any(word in lower for word in ("cookie", "decrypt", "dpapi")):
        hint = "อ่าน cookies ไม่สำเร็จ ลองปิดเบราว์เซอร์ หรือใช้ไฟล์ cookies.txt / Firefox"
    elif any(word in lower for word in ("login", "sign in", "private", "authentication", "403")):
        hint = "คลิปอาจต้องล็อกอิน เลือก cookies จากบัญชีที่เปิดคลิปนี้ได้"
    else:
        hint = "ลองใช้ลิงก์คลิปโดยตรง และอัปเดตผ่าน install.bat หากเว็บเปลี่ยนระบบ"
    return hint.replace("install.bat", install_instructions()) + "\n\nรายละเอียด: " + detail


class YTDLStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("YTDL Studio")
        self.root.geometry("1160x820")
        self.root.minsize(980, 700)
        self.root.configure(bg=BG)
        self.root.option_add("*Font", (FONT_FAMILY, 10))
        self.output_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.cookie_source = tk.StringVar(value="ไม่ใช้")
        self.cookie_path = tk.StringVar(value="")
        self.mode = tk.StringVar(value="video")
        self.status = tk.StringVar(value="พร้อมดาวน์โหลด")
        self.progress_text = tk.StringVar(value="วางลิงก์วิดีโอหรือเสียง เพื่อเริ่มต้น")
        self.events = queue.Queue()
        self.busy = False
        self.last_output_dir = None
        self.active_output_dir = None
        self.advanced_open = False
        self.url_value = tk.StringVar()
        self.source_text = tk.StringVar(value="รองรับลิงก์จากหลายแพลตฟอร์ม")
        self.percent_text = tk.StringVar(value="—")
        self.mode_hint = tk.StringVar(value="วิดีโอพร้อมเสียง · คุณภาพดีที่สุดที่มี")
        self._build()
        self.url_value.trace_add("write", self._url_changed)
        self.root.bind("<Return>", lambda e: self._download() if e.widget == self.url else None)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        threading.Thread(target=self._check_platforms, daemon=True).start()
        self.root.after(120, self._poll_events)

    def _build(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        for name, color in (("Primary", ACCENT), ("Selected", ACCENT), ("Subtle", PANEL2)):
            style.configure(name + ".TButton", background=color, foreground=BG if name != "Subtle" else TEXT,
                            font=(FONT_FAMILY, 10, "bold"), borderwidth=0, padding=(16, 6))
            style.map(name + ".TButton", background=[("disabled", PANEL2), ("active", "#b59c6e" if name != "Subtle" else "#34373d")],
                      foreground=[("disabled", MUTED)])
        style.configure("Studio.Horizontal.TProgressbar", troughcolor=PANEL2,
                        background=ACCENT, borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("TCombobox", fieldbackground=PANEL2, background=PANEL2,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=PANEL2, padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", TEXT)])
        self.root.option_add("*TCombobox*Listbox.background", PANEL2)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)

        # Scroll the whole workspace so controls remain reachable on small screens.
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        outer = tk.Frame(canvas, bg=BG, padx=32, pady=28)
        window = canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        self.root.bind("<MouseWheel>", lambda e: canvas.yview_scroll(scroll_units(e.delta), "units") if canvas.bbox("all") and canvas.bbox("all")[3] > canvas.winfo_height() else None)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 24))
        tk.Label(header, text="↓", bg=ACCENT, fg=BG, font=(FONT_FAMILY, 24, "bold"), width=2).pack(side="left", padx=(0, 14))
        brand = tk.Frame(header, bg=BG)
        brand.pack(side="left")
        tk.Label(brand, text="YTDL  /  STUDIO", bg=BG, fg=TEXT, font=(FONT_FAMILY, 20, "bold")).pack(anchor="w")
        tk.Label(brand, text="เก็บคลิปโปรด ให้เป็นเรื่องง่าย", bg=BG, fg=MUTED).pack(anchor="w")
        tk.Label(header, text="YOUR MEDIA, SIMPLIFIED", bg=BG, fg=ACCENT, padx=14, pady=8, font=(FONT_FAMILY, 9, "bold")).pack(side="right")

        body = tk.Frame(outer, bg=BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, minsize=300)
        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        sidebar = tk.Frame(body, bg=PANEL, padx=18, pady=18)
        sidebar.grid(row=0, column=1, sticky="new")

        card = tk.Frame(left, bg=PANEL, padx=26, pady=24, highlightthickness=1, highlightbackground="#303238")
        card.pack(fill="x")
        self._label(card, "คลิปโปรด เริ่มที่ลิงก์เดียว", 22, "bold").pack(anchor="w")
        tk.Label(card, text="วางลิงก์ เลือกรูปแบบ แล้วดาวน์โหลดได้เลย", bg=PANEL, fg=MUTED).pack(anchor="w", pady=(2, 18))
        self._label(card, "ลิงก์ของคุณ", 10, "bold").pack(anchor="w")
        urlrow = tk.Frame(card, bg=PANEL)
        urlrow.pack(fill="x", pady=(8, 6))
        self.url = self._entry(urlrow, self.url_value)
        self.url.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 8))
        self.paste_btn = self._button(urlrow, "วางลิงก์", self._paste, subtle=True)
        self.paste_btn.pack(side="right", ipady=8)

        self.source_label = tk.Label(card, textvariable=self.source_text, bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=400, font=(FONT_FAMILY, 9))
        self.source_label.pack(fill="x", pady=(0, 18))

        self._label(card, "บันทึกเป็น", 10, "bold").pack(anchor="w")
        modes = tk.Frame(card, bg=PANEL)
        modes.pack(fill="x", pady=(8, 6))
        self.video_btn = self._button(modes, "วิดีโอ  ·  MP4", lambda: self._set_mode("video"))
        self.video_btn.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 8))
        self.audio_btn = self._button(modes, "เฉพาะเสียง  ·  MP3", lambda: self._set_mode("audio"), subtle=True)
        self.audio_btn.pack(side="left", fill="x", expand=True, ipady=12)
        self._set_mode("video")

        tk.Label(card, textvariable=self.mode_hint, bg=PANEL, fg=MUTED, font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(0, 18))
        self._label(card, "บันทึกไว้ที่", 10, "bold").pack(anchor="w")
        folder = tk.Frame(card, bg=PANEL)
        folder.pack(fill="x", pady=(8, 18))
        self.folder_entry = self._entry(folder, self.output_dir)
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self.browse_btn = self._button(folder, "เปลี่ยน", self._browse, subtle=True)
        self.browse_btn.pack(side="right", ipady=6)

        self.advanced_btn = self._button(card, "＋ ตัวเลือกเพิ่มเติม", self._toggle_advanced, subtle=True)
        self.advanced_btn.pack(anchor="w", pady=(0, 14))
        self.advanced_panel = tk.Frame(card, bg=PANEL)
        auth = tk.Frame(self.advanced_panel, bg=PANEL)
        auth.pack(fill="x")
        self._label(auth, "บัญชี / Cookies", 10, "bold").pack(side="left")
        self.cookie_combo = ttk.Combobox(auth, textvariable=self.cookie_source, state="readonly", width=17,
                     values=("ไม่ใช้", "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "ไฟล์ cookies.txt"))
        self.cookie_combo.pack(side="right")
        tk.Label(self.advanced_panel, text="ใช้เฉพาะคลิปที่ต้องล็อกอิน", bg=PANEL, fg=MUTED, font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(6, 8))
        self.cookie_row = tk.Frame(self.advanced_panel, bg=PANEL)
        self.cookie_entry = self._entry(self.cookie_row, self.cookie_path)
        self.cookie_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self.cookie_btn = self._button(self.cookie_row, "เลือกไฟล์", self._choose_cookies, subtle=True)
        self.cookie_btn.pack(side="right")
        self.cookie_combo.bind("<<ComboboxSelected>>", self._toggle_cookies)
        self.download_btn = self._button(card, "ดาวน์โหลดวิดีโอ  ↓", self._download, primary=True)
        self.download_btn.pack(fill="x", ipady=12, pady=(4, 0))
        tk.Label(card, text="หรือกด Enter หลังวางลิงก์", bg=PANEL, fg=MUTED, font=(FONT_FAMILY, 9)).pack(pady=(8, 0))
        self.edit_controls = [self.url, self.paste_btn, self.video_btn, self.audio_btn,
                              self.folder_entry, self.browse_btn, self.cookie_entry, self.cookie_btn]

        progress = tk.Frame(left, bg=PANEL, padx=22, pady=18)
        progress.pack(fill="x", pady=(16, 0))
        row = tk.Frame(progress, bg=PANEL)
        row.pack(fill="x")
        self._label(row, "กิจกรรมล่าสุด", 11, "bold").pack(side="left")
        self.status_label = tk.Label(row, textvariable=self.status, bg=PANEL, fg=GREEN, font=(FONT_FAMILY, 10, "bold"))
        self.status_label.pack(side="right")
        tk.Label(progress, textvariable=self.percent_text, bg=PANEL, fg=ACCENT, font=(FONT_FAMILY, 28, "bold")).pack(anchor="w", pady=(10, 0))
        self.bar = ttk.Progressbar(progress, style="Studio.Horizontal.TProgressbar", maximum=100)
        self.bar.pack(fill="x", pady=12, ipady=2)
        self.detail_label = tk.Label(progress, textvariable=self.progress_text, bg=PANEL, fg=MUTED, anchor="w", justify="left", wraplength=480)
        self.detail_label.pack(fill="x")
        self.detail_label.bind("<Configure>", lambda e: self.detail_label.configure(wraplength=max(100, e.width)))
        self.open_btn = self._button(progress, "เปิดโฟลเดอร์ปลายทาง ↗", self._open_folder, subtle=True)
        self.open_btn.pack(anchor="w", pady=(14, 0))

        self._label(sidebar, "เชื่อมต่อโลกของคลิป", 14, "bold").pack(anchor="w")
        self.support_summary = tk.StringVar(value="กำลังตรวจสอบตัวรองรับ...")
        tk.Label(sidebar, textvariable=self.support_summary, bg=PANEL, fg=MUTED, font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(4, 16))
        self.platform_labels = {}
        self.platform_icons = {}
        icon_dir = resource_path("assets", "platforms")
        for name, key, icon_name, color in PLATFORMS:
            row = tk.Frame(sidebar, bg=PANEL)
            row.pack(fill="x", pady=6)
            try:
                icon = tk.PhotoImage(master=self.root, file=os.path.join(icon_dir, icon_name + ".png"))
                self.platform_icons[name] = icon  # Keep Tk images alive.
                tk.Label(row, image=icon, bg=PANEL, width=32, height=30).pack(side="left", padx=(0, 9))
            except tk.TclError:
                # Missing assets must not stop the downloader from opening.
                tk.Label(row, text="●", bg=PANEL, fg=color, width=3).pack(side="left", padx=(0, 9))
            self._label(row, name, 10).pack(side="left")
            label = tk.Label(row, text="ตรวจสอบ…", bg=PANEL, fg=MUTED, font=(FONT_FAMILY, 9))
            label.pack(side="right", padx=(10, 0))
            self.platform_labels[name] = label
        tk.Frame(sidebar, bg=PANEL2, height=1).pack(fill="x", pady=15)
        tk.Label(sidebar, text="สถานะจากตัวรองรับที่ติดตั้ง\nไม่ได้ยืนยันว่าดาวน์โหลดได้ทุกคลิป\nบางเว็บอาจต้องเข้าสู่ระบบ", bg=PANEL, fg=MUTED, justify="left", font=(FONT_FAMILY, 9)).pack(anchor="w")
        self._button(sidebar, "ดูเว็บทั้งหมด ↗", lambda: webbrowser.open("https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md"), subtle=True).pack(fill="x", pady=(16, 0), ipady=5)
        tk.Label(outer, text="ดาวน์โหลดเฉพาะสื่อที่คุณสร้างเองหรือได้รับอนุญาต", bg=BG, fg=MUTED, font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(18, 0))

    def _entry(self, parent, variable=None):
        return tk.Entry(parent, textvariable=variable, bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                        relief="flat", highlightthickness=1, highlightbackground=PANEL2,
                        highlightcolor=ACCENT, font=(FONT_FAMILY, 10), width=20)

    def _toggle_cookies(self, _event=None):
        if self.cookie_source.get() == "ไฟล์ cookies.txt":
            self.cookie_row.pack(fill="x", pady=(10, 0))
        else:
            self.cookie_row.pack_forget()

    def _check_platforms(self):
        version, states = platform_support()
        self.events.put(("platforms", version, states))

    def _close(self):
        if self.busy and not messagebox.askyesno("กำลังดาวน์โหลด", "ปิดโปรแกรมและหยุดงานที่กำลังทำอยู่หรือไม่?"):
            return
        self.root.destroy()

    def _label(self, parent, text, size=10, weight="normal"):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=TEXT, font=(FONT_FAMILY, size, weight))

    def _button(self, parent, text, command, primary=False, subtle=False, width=None):
        options = {"width": width} if width is not None else {}
        return ttk.Button(parent, text=text, command=command, cursor="hand2",
                          style=("Primary" if primary else "Subtle" if subtle else "Selected") + ".TButton", **options)

    def _toggle_advanced(self):
        self.advanced_open = not self.advanced_open
        if self.advanced_open:
            self.advanced_panel.pack(fill="x", before=self.download_btn, pady=(0, 14))
        else:
            self.advanced_panel.pack_forget()
        self.advanced_btn.configure(text="− ซ่อนตัวเลือกเพิ่มเติม" if self.advanced_open else "＋ ตัวเลือกเพิ่มเติม")

    def _url_changed(self, *_):
        url = self.url_value.get().strip()
        try:
            parsed = urlsplit(url)
            host = parsed.hostname if parsed.scheme.lower() in ("http", "https") else None
        except ValueError:
            host = None
        self.source_text.set(host or ("ใส่ลิงก์ที่ขึ้นต้นด้วย https://" if url else "รองรับลิงก์จากหลายแพลตฟอร์ม"))
        self.source_label.configure(fg=GREEN if host else MUTED)

    def _lock_inputs(self, locked):
        for widget in self.edit_controls:
            widget.configure(state="disabled" if locked else "normal")
        self.cookie_combo.configure(state="disabled" if locked else "readonly")

    def _set_mode(self, mode):
        self.mode.set(mode)
        self.video_btn.configure(style="Selected.TButton" if mode == "video" else "Subtle.TButton")
        self.audio_btn.configure(style="Selected.TButton" if mode == "audio" else "Subtle.TButton")
        self.mode_hint.set("วิดีโอพร้อมเสียง · คุณภาพดีที่สุดที่มี" if mode == "video" else "ไฟล์เสียง MP3 · คุณภาพ 192 kbps")
        if hasattr(self, "download_btn") and not self.busy:
            self.download_btn.configure(text="ดาวน์โหลดวิดีโอ  ↓" if mode == "video" else "ดาวน์โหลดเสียง  ↓")

    def _paste(self):
        try:
            value = self.root.clipboard_get()
            self.url.delete(0, "end")
            self.url.insert(0, value.strip())
        except tk.TclError:
            self.status.set("คลิปบอร์ดว่าง")

    def _browse(self):
        path = filedialog.askdirectory(initialdir=self.output_dir.get() or os.path.expanduser("~"))
        if path:
            self.output_dir.set(path)

    def _choose_cookies(self):
        path = filedialog.askopenfilename(title="เลือก cookies แบบ Netscape", filetypes=[("Cookies", "*.txt"), ("All files", "*.*")])
        if path:
            self.cookie_path.set(path)
            self.cookie_source.set("ไฟล์ cookies.txt")
            self._toggle_cookies()

    def _open_folder(self):
        path = self.last_output_dir or self.output_dir.get().strip()
        if os.path.isdir(path):
            try:
                open_directory(path)
            except (OSError, subprocess.SubprocessError) as exc:
                messagebox.showerror("เปิดโฟลเดอร์ไม่สำเร็จ", str(exc))
        else:
            messagebox.showerror("ไม่พบโฟลเดอร์", "กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่")

    def _download(self):
        if self.busy:
            return
        url = self.url.get().strip()
        folder = self.output_dir.get().strip()
        if not url or url == "วางลิงก์วิดีโอหรือเสียงที่นี่":
            messagebox.showinfo("ใส่ลิงก์ก่อน", "กรุณาวางลิงก์วิดีโอหรือเสียง ที่ต้องการดาวน์โหลด")
            return
        try:
            parsed = urlsplit(url)
            valid_url = parsed.scheme.lower() in ("http", "https") and bool(parsed.hostname)
        except ValueError:
            valid_url = False
        if not valid_url:
            messagebox.showerror("ลิงก์ไม่ถูกต้อง", "กรุณาใส่ลิงก์ที่ขึ้นต้นด้วย http:// หรือ https://")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("ไม่พบโฟลเดอร์", "กรุณาเลือกโฟลเดอร์บันทึกที่มีอยู่")
            return
        cookie_source = self.cookie_source.get()
        cookie_path = self.cookie_path.get().strip()
        if cookie_source == "ไฟล์ cookies.txt" and not os.path.isfile(cookie_path):
            messagebox.showerror("ไม่พบไฟล์ cookies", "กรุณาเลือกไฟล์ cookies.txt ที่มีอยู่")
            return
        self.busy = True
        self.active_output_dir = folder
        self.last_output_dir = None
        self._lock_inputs(True)
        self.percent_text.set("…")
        self.bar.configure(mode="indeterminate")
        self.bar.start(12)
        self.download_btn.configure(state="disabled", text="กำลังดาวน์โหลด…")
        self.bar.configure(value=0)
        self.status_label.configure(fg=ACCENT)
        self.status.set("กำลังเชื่อมต่อ")
        self.progress_text.set("กำลังเชื่อมต่อ...")
        threading.Thread(target=self._worker, args=(url, folder, self.mode.get(), cookie_source, cookie_path), daemon=True).start()

    def _worker(self, url, folder, mode, cookie_source="ไม่ใช้", cookie_path=""):
        try:
            import yt_dlp
            import imageio_ffmpeg
            def progress(data):
                if data["status"] == "downloading":
                    total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                    downloaded = data.get("downloaded_bytes", 0)
                    percent = min(100, downloaded * 100 / total) if total else 0
                    speed = data.get("speed")
                    eta = data.get("eta")
                    details = f"{speed / 1024 / 1024:.1f} MB/s" if speed else "กำลังรับข้อมูล"
                    if eta is not None:
                        details += f" · เหลือประมาณ {int(eta)//60}:{int(eta)%60:02d} นาที"
                    self.events.put(("progress", percent, details))
                elif data["status"] == "finished":
                    self.events.put(("processing", "กำลังรวมภาพ เสียง หรือแปลงไฟล์…"))
            opts = {
                "outtmpl": os.path.join(folder, "%(title).150B [%(extractor_key)s-%(id)s].%(ext)s"),
                "noplaylist": True,
                "progress_hooks": [progress],
                "windowsfilenames": sys.platform == "win32",
                "quiet": True,
                "ffmpeg_location": ffmpeg_path(),
            }
            if cookie_source == "ไฟล์ cookies.txt":
                # Load into memory so yt-dlp cannot rewrite the user's cookie file.
                from yt_dlp.cookies import YoutubeDLCookieJar
                jar = YoutubeDLCookieJar(cookie_path)
                jar.load(ignore_discard=True, ignore_expires=True)
                jar.filename = None
            else:
                jar = None
                if cookie_source != "ไม่ใช้":
                    opts["cookiesfrombrowser"] = (cookie_source,)
            if mode == "audio":
                opts.update({"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]})
            else:
                opts.update({"format": "bestvideo*+bestaudio/best", "merge_output_format": "mp4", "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]})
            with yt_dlp.YoutubeDL(opts) as ydl:
                if jar is not None:
                    ydl.cookiejar = jar
                result = ydl.download([url])
                if result:
                    raise RuntimeError("ดาวน์โหลดไม่สำเร็จ กรุณาลองลิงก์คลิปโดยตรง")
            self.events.put(("done",))
        except ImportError:
            self.events.put(("error", "ยังติดตั้งส่วนประกอบไม่ครบ\nเปิด " + install_instructions() + " แล้วลองใหม่อีกครั้ง"))
        except Exception as exc:
            self.events.put(("error", download_error(exc)))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "platforms":
                    count = sum(value == "supported" for value in event[2].values())
                    self.support_summary.set(f"{count}/{len(PLATFORMS)} แหล่ง · yt-dlp {event[1]}")
                    labels = {"supported": ("● มีตัวรองรับ", GREEN), "broken": ("● มีปัญหา", "#f4bd72"), "missing": ("● ไม่พบ", "#ff8697")}
                    for name, state in event[2].items():
                        text, color = labels[state]
                        self.platform_labels[name].configure(text=text, fg=color)
                elif event[0] == "processing":
                    self.bar.stop()
                    self.bar.configure(mode="indeterminate")
                    self.bar.start(12)
                    self.percent_text.set("…")
                    self.status.set("จัดเตรียมไฟล์")
                    self.progress_text.set(event[1])
                elif event[0] == "progress":
                    self.bar.stop()
                    self.bar.configure(mode="determinate")
                    self.percent_text.set(f"{event[1]:.0f}%")
                    self.bar.configure(value=event[1])
                    self.progress_text.set(event[2])
                    self.status.set("กำลังดาวน์โหลด" if event[1] < 100 else "กำลังจัดเตรียมไฟล์")
                elif event[0] == "done":
                    self.bar.stop()
                    self.bar.configure(mode="determinate", value=100)
                    self.percent_text.set("100%")
                    self.last_output_dir = self.active_output_dir
                    self.progress_text.set("บันทึกแล้ว · " + (self.last_output_dir or ""))
                    self.status.set("เสร็จแล้ว")
                    self.status_label.configure(fg=GREEN)
                    self._finish()
                elif event[0] == "error":
                    self.bar.stop()
                    self.bar.configure(mode="determinate", value=0)
                    self.percent_text.set("—")
                    self.status.set("ลองอีกครั้ง")
                    self.status_label.configure(fg="#ff8697")
                    self.progress_text.set("ดาวน์โหลดไม่สำเร็จ")
                    self._finish()
                    messagebox.showerror("ดาวน์โหลดไม่สำเร็จ", event[1])
        except queue.Empty:
            pass
        self.root.after(120, self._poll_events)

    def _finish(self):
        self.busy = False
        self._lock_inputs(False)
        self.download_btn.configure(state="normal")
        self._set_mode(self.mode.get())


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from check_macos import main as check_macos
        check_macos()
        window = tk.Tk()
        window.withdraw()
        app = YTDLStudio(window)
        window.update_idletasks()
        assert len(app.platform_icons) == len(PLATFORMS), "Missing bundled icons"
        app._set_mode("audio")
        app._set_mode("video")
        window.destroy()
        raise SystemExit(0)
    window = tk.Tk()
    YTDLStudio(window)
    window.mainloop()
