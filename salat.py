import tkinter as tk
from tkinter import font as tkfont
import datetime
import threading
import time
import sys
import os

# ── Prayer times ──────────────────────────────────────────────────────────────
PRAYER_TIMES = {
    "Fajr":   (4,  50),
    "Dohr":   (13, 40),
    "3asr":   (17,  20),
    "Magrib": (20, 50),
    "3icha":  (22, 30),
}

PRAYER_ORDER = ["Fajr", "Dohr", "3asr", "Magrib", "3icha"]

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_current_prayer():
    """Return the name of the most recently due prayer."""
    now = datetime.datetime.now()
    current_minutes = now.hour * 60 + now.minute
    last_prayer = PRAYER_ORDER[0]
    for name in PRAYER_ORDER:
        h, m = PRAYER_TIMES[name]
        if current_minutes >= h * 60 + m:
            last_prayer = name
    return last_prayer


def kill_app():
    """Permanently kill the script (works even if window is destroyed)."""
    try:
        os.kill(os.getpid(), 9)
    except Exception:
        sys.exit(0)


# ── Main App ──────────────────────────────────────────────────────────────────

class SalatApp:
    WAIT_SECONDS = 240   # 4 minutes

    def __init__(self):
        self.root = tk.Tk()
        self._focus_job = None
        self.root.withdraw()          # hide during countdown
        self._build_ui()
        self._start_countdown()
        self.root.mainloop()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # Block close button and Alt+F4
        root.protocol("WM_DELETE_WINDOW", lambda: None)
        root.attributes("-topmost", True)
        root.attributes("-fullscreen", True)

        # Block keyboard shortcuts that could escape the window
        root.bind("<Alt-F4>",    lambda e: "break")
        root.bind("<Control-w>", lambda e: "break")
        root.bind("<Control-q>", lambda e: "break")
        root.bind("<Escape>",    lambda e: "break")

        W = root.winfo_screenwidth()
        H = root.winfo_screenheight()
        root.geometry(f"{W}x{H}+0+0")

        # ── Fonts ──────────────────────────────────────────────────────────
        try:
            f_title   = tkfont.Font(family="Amiri",         size=46, weight="bold")
            f_arabic  = tkfont.Font(family="Amiri",         size=26)
            f_times   = tkfont.Font(family="Courier New",   size=18, weight="bold")
            f_label   = tkfont.Font(family="Helvetica Neue",size=20)
            f_prompt  = tkfont.Font(family="Helvetica Neue",size=16)
            f_entry   = tkfont.Font(family="Courier New",   size=18)
            f_exit    = tkfont.Font(family="Helvetica Neue",size=22, weight="bold")
            f_count   = tkfont.Font(family="Helvetica Neue",size=14)
        except Exception:
            f_title   = tkfont.Font(size=46, weight="bold")
            f_arabic  = tkfont.Font(size=26)
            f_times   = tkfont.Font(family="Courier New", size=18, weight="bold")
            f_label   = tkfont.Font(size=20)
            f_prompt  = tkfont.Font(size=16)
            f_entry   = tkfont.Font(family="Courier New", size=18)
            f_exit    = tkfont.Font(size=22, weight="bold")
            f_count   = tkfont.Font(size=14)

        # ── Colors ─────────────────────────────────────────────────────────
        BG        = "#0a0f1e"
        GOLD      = "#c9a84c"
        GOLD_DARK = "#8a6a1e"
        GREEN     = "#1a5e3a"
        GREEN_LT  = "#2eb87b"
        WHITE     = "#f0ece0"
        MUTED     = "#7a8099"
        RED_BTN   = "#c0392b"
        RED_HOV   = "#e74c3c"

        root.configure(bg=BG)

        # ── Master canvas for crescent decoration ──────────────────────────
        canvas = tk.Canvas(root, bg=BG, highlightthickness=0,
                           width=W, height=H)
        canvas.place(x=0, y=0)

        # Subtle geometric arcs
        for i, r in enumerate([320, 280, 240]):
            alpha = 40 - i * 10
            canvas.create_arc(W//2 - r, 80 - r, W//2 + r, 80 + r,
                              start=180, extent=180,
                              outline=GOLD, width=1, style="arc")

        # ── Title ──────────────────────────────────────────────────────────
        tk.Label(root, text="🕌  Salat Reminder", font=f_title,
                 fg=GOLD, bg=BG).place(relx=0.5, y=60, anchor="center")

        tk.Label(root, text="الصَّلاةُ خَيْرٌ مِنَ النَّوْمِ",
                 font=f_arabic, fg=GOLD_DARK, bg=BG).place(
                 relx=0.5, y=120, anchor="center")

        # ── Prayer times table ─────────────────────────────────────────────
        table_frame = tk.Frame(root, bg=BG)
        table_frame.place(relx=0.5, y=200, anchor="n")

        current = get_current_prayer()

        for i, name in enumerate(PRAYER_ORDER):
            h, m = PRAYER_TIMES[name]
            time_str = f"{h:02d}:{m:02d}"
            is_current = (name == current)

            row_bg  = GREEN      if is_current else BG
            row_fg  = GREEN_LT   if is_current else WHITE
            marker  = "▶  "      if is_current else "   "

            row = tk.Frame(table_frame, bg=row_bg,
                           padx=20, pady=6,
                           highlightthickness=1 if is_current else 0,
                           highlightbackground=GREEN_LT)
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=40)

            tk.Label(row, text=f"{marker}{name:<8}",
                     font=f_times, fg=row_fg, bg=row_bg,
                     width=12, anchor="w").pack(side="left")
            tk.Label(row, text=time_str,
                     font=f_times, fg=GOLD if is_current else MUTED,
                     bg=row_bg).pack(side="right", padx=20)

        # ── "Wach slity?" label (above entry) ─────────────────────────────
        self.current_prayer_var = tk.StringVar()
        self.current_prayer_var.set(current)

        prompt_top = tk.Label(
            root,
            textvariable=self.current_prayer_var,
            font=f_label,
            fg=GREEN_LT,
            bg=BG
        )
        # We'll use a StringVar that shows the full phrase
        self._update_top_label()
        prompt_top.place(relx=0.5, rely=0.72, anchor="center")
        self._prompt_top_widget = prompt_top   # keep ref to update

        # ── Entry instruction ──────────────────────────────────────────────
        tk.Label(root,
                 text='Kteb: "wlh hta slit [ssm salat]" bash t7el',
                 font=f_prompt, fg=MUTED, bg=BG).place(
                 relx=0.5, rely=0.77, anchor="center")

        # ── Text entry ─────────────────────────────────────────────────────
        entry_frame = tk.Frame(root, bg=GOLD, padx=2, pady=2)
        entry_frame.place(relx=0.5, rely=0.83, anchor="center")

        self.entry_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self.entry_var,
                         font=f_entry, bg="#12192e", fg=WHITE,
                         insertbackground=GOLD,
                         relief="flat", width=40)
        entry.pack(ipady=10, ipadx=10)
        entry.focus()
        entry.bind("<Return>", self._check_input)
        self.entry_widget = entry

        # ── Feedback label ─────────────────────────────────────────────────
        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = tk.Label(root, textvariable=self.feedback_var,
                                       font=f_prompt, fg="#e74c3c", bg=BG)
        self.feedback_label.place(relx=0.5, rely=0.88, anchor="center")

        # ── EXIT button ────────────────────────────────────────────────────
        exit_btn = tk.Button(
            root, text="🚪  EXIT",
            font=f_exit,
            bg=RED_BTN, fg=WHITE,
            activebackground=RED_HOV, activeforeground=WHITE,
            relief="flat", padx=30, pady=12,
            cursor="hand2",
            command=kill_app
        )
        exit_btn.place(relx=0.5, rely=0.94, anchor="center")

        # hover effect
        exit_btn.bind("<Enter>", lambda e: exit_btn.config(bg=RED_HOV))
        exit_btn.bind("<Leave>", lambda e: exit_btn.config(bg=RED_BTN))

        # ── Countdown label (shown while hidden) ──────────────────────────
        self.countdown_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.countdown_var,
                 font=f_count, fg=MUTED, bg=BG).place(
                 relx=0.5, rely=0.98, anchor="center")

        # ── Live clock ────────────────────────────────────────────────────
        self.clock_var = tk.StringVar()
        tk.Label(root, textvariable=self.clock_var,
                 font=f_count, fg=MUTED, bg=BG).place(
                 relx=0.98, rely=0.01, anchor="ne")
        self._tick_clock()

        self._W = W
        self._H = H

    # ── Top label updater ─────────────────────────────────────────────────────

    def _update_top_label(self):
        p = get_current_prayer()
        self.current_prayer_var.set(f"Wach slity {p}? ✦")

    # ── Clock ─────────────────────────────────────────────────────────────────

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S  |  %A %d %b %Y")
        self.clock_var.set(now)
        self.root.after(1000, self._tick_clock)

    # ── Countdown / reveal ────────────────────────────────────────────────────

    def _start_countdown(self):
        def run():
            for remaining in range(self.WAIT_SECONDS, 0, -1):
                mins, secs = divmod(remaining, 60)
                self.root.after(0, self.countdown_var.set,
                                f"Launching in {mins:02d}:{secs:02d} …")
                time.sleep(1)
            self.root.after(0, self._show_window)
        threading.Thread(target=run, daemon=True).start()

    def _show_window(self):
        self._update_top_label()
        self.countdown_var.set("")
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        # Give tkinter a moment to render, then focus the entry
        self.root.after(100, self._grab_entry_focus)

    def _grab_entry_focus(self):
        self.entry_widget.focus_force()
        self.entry_widget.focus_set()
        # Keep re-stealing focus every 500ms so nothing else grabs it
        self._focus_job = self.root.after(500, self._keep_focus)

    def _keep_focus(self):
        """Re-steal focus to entry while window is visible."""
        try:
            self.entry_widget.focus_force()
        except Exception:
            pass
        self._focus_job = self.root.after(500, self._keep_focus)

    # ── Input check ───────────────────────────────────────────────────────────

    def _check_input(self, event=None):
        text = self.entry_var.get().strip().lower()
        current = get_current_prayer().lower()

        # Accept: "wlh hta slit <prayer>" (flexible spacing / case)
        expected = f"wlh hta slit {current}"
        if text == expected:
            self.feedback_var.set("✅  Barakallahu fik! Salat maqbula insha'Allah.")
            self.feedback_label.config(fg="#2eb87b")
            self.root.after(1500, self._hide_window)
        else:
            self.feedback_var.set(
                f'❌  Kteb bssah: "wlh hta slit {get_current_prayer()}"')
            self.entry_var.set("")

    # ── Hide until next session ────────────────────────────────────────────────

    def _hide_window(self):
        self.entry_var.set("")
        self.feedback_var.set("")
        # Stop the focus-stealing loop before hiding
        if self._focus_job is not None:
            self.root.after_cancel(self._focus_job)
            self._focus_job = None
        self.root.withdraw()
        self._start_countdown()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SalatApp()
