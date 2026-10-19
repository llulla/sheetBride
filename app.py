import os
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from core import INTERVALS, load_config, save_config, sync_once

BG = "#F3EEE3"
BG_ALT = "#EAE2D0"
FG = "#3E3626"
ACCENT = "#C9A96E"
ACCENT_DARK = "#B8935A"
BORDER = "#D8CFB8"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 11, "bold")


def apply_theme(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=BG, foreground=FG, font=FONT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=FG)
    style.configure("Header.TLabel", background=BG, foreground=FG, font=FONT_BOLD)
    style.configure(
        "TEntry",
        fieldbackground="#FFFDF8",
        background="#FFFDF8",
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=5,
    )
    style.configure(
        "TButton",
        background=ACCENT,
        foreground="#2A2418",
        bordercolor=ACCENT_DARK,
        padding=(12, 6),
        font=FONT,
    )
    style.map("TButton", background=[("active", ACCENT_DARK)])
    style.configure("TRadiobutton", background=BG, foreground=FG, font=FONT)
    style.map("TRadiobutton", background=[("active", BG)])


class App:
    def __init__(self, root):
        self.root = root
        root.title("SheetBride - 엑셀 → 구글시트 자동 동기화")
        root.geometry("600x440")
        apply_theme(root)

        cfg = load_config()
        self.excel_path = tk.StringVar(value=cfg.get("excel_path", ""))
        self.sheet_url = tk.StringVar(value=cfg.get("sheet_url", ""))
        self.interval_name = tk.StringVar(value=cfg.get("interval_name", "수동"))

        self.stop_event = threading.Event()
        self.worker = None

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        ttk.Label(self.root, text="SheetBride", style="Header.TLabel").pack(
            anchor="w", padx=12, pady=(12, 0)
        )

        def row(label, var, browse=None):
            f = ttk.Frame(self.root)
            f.pack(fill="x", **pad)
            ttk.Label(f, text=label, width=10, anchor="w").pack(side="left")
            ttk.Entry(f, textvariable=var).pack(side="left", fill="x", expand=True)
            if browse:
                ttk.Button(f, text="찾아보기", command=browse).pack(side="left", padx=(6, 0))

        row("엑셀 파일", self.excel_path, self.browse_excel)
        row("시트 URL", self.sheet_url)

        f = ttk.Frame(self.root)
        f.pack(fill="x", **pad)
        ttk.Label(f, text="동기화 주기", width=10, anchor="w").pack(side="left")
        for name in INTERVALS:
            ttk.Radiobutton(f, text=name, variable=self.interval_name, value=name).pack(side="left", padx=4)

        f = ttk.Frame(self.root)
        f.pack(fill="x", **pad)
        self.start_btn = ttk.Button(f, text="자동 동기화 시작", command=self.toggle_auto)
        self.start_btn.pack(side="left")
        ttk.Button(f, text="지금 동기화", command=self.sync_now).pack(side="left", padx=8)

        self.log_box = scrolledtext.ScrolledText(
            self.root,
            height=16,
            state="disabled",
            bg="#FFFDF8",
            fg=FG,
            insertbackground=FG,
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
            font=FONT,
        )
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(6, 12))

    def browse_excel(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx *.xlsm")])
        if p:
            self.excel_path.set(p)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def current_config(self):
        return {
            "excel_path": self.excel_path.get(),
            "sheet_url": self.sheet_url.get(),
            "interval_name": self.interval_name.get(),
        }

    def validate(self):
        if not self.excel_path.get() or not os.path.exists(self.excel_path.get()):
            messagebox.showerror("오류", "엑셀 파일을 선택하세요.")
            return False
        if not self.sheet_url.get():
            messagebox.showerror("오류", "구글 시트 URL을 입력하세요.")
            return False
        return True

    def sync_now(self):
        if not self.validate():
            return
        save_config(self.current_config())
        cfg = self.current_config()

        def run():
            try:
                sync_once(cfg["excel_path"], cfg["sheet_url"], self.log)
            except Exception as e:
                self.log(f"[오류] {e}")

        threading.Thread(target=run, daemon=True).start()

    def toggle_auto(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.start_btn.config(text="자동 동기화 시작")
            self.log("자동 동기화 중지")
            return
        if not self.validate():
            return
        minutes = INTERVALS[self.interval_name.get()]
        if minutes == 0:
            messagebox.showinfo("안내", "'수동'이 선택되어 있습니다. '지금 동기화' 버튼을 사용하세요.")
            return
        save_config(self.current_config())
        cfg = self.current_config()
        self.stop_event.clear()

        def loop():
            while not self.stop_event.is_set():
                try:
                    sync_once(cfg["excel_path"], cfg["sheet_url"], self.log)
                except Exception as e:
                    self.log(f"[오류] {e}")
                self.stop_event.wait(minutes * 60)

        self.worker = threading.Thread(target=loop, daemon=True)
        self.worker.start()
        self.start_btn.config(text="자동 동기화 중지")
        self.log(f"자동 동기화 시작 ({self.interval_name.get()})")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
