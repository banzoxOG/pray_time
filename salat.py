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


def get_next_prayer():
    """Return (name, datetime) of the next upcoming prayer (today or tomorrow)."""
    now = datetime.datetime.now()
    today = now.date()
    current_minutes = now.hour * 60 + now.minute

    for name in PRAYER_ORDER:
        h, m = PRAYER_TIMES[name]
        if h * 60 + m > current_minutes:
            return name, datetime.datetime.combine(today, datetime.time(h, m))

    # Past all prayers today → wait for Fajr tomorrow
    tomorrow = today + datetime.timedelta(days=1)
    h, m = PRAYER_TIMES["Fajr"]
    return "Fajr", datetime.datetime.combine(tomorrow, datetime.time(h, m))


def seconds_until(dt):
    """Seconds from now until a future datetime (floor at 0)."""
    return max(0, (dt - datetime.datetime.now()).total_seconds())


def kill_app():
    """Permanently kill the script."""
    try:
        os.kill(os.getpid(), 9)
    except Exception:
        sys.exit(0)


# ── Main App ──────────────────────────────────────────────────────────────────

class SalatApp:
    STARTUP_DELAY = 240   # 4 min grace period on first launch

    def __init__(self):
        self.root = tk.Tk()
        self._focus_job   = None
        self._wait_thread = None
        self._confirmed_prayer = None   # name of prayer already confirmed this session
        self.root.withdraw()
        self._build_ui()
        self._start_startup_delay()
        self.root.mainloop()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        root.protocol("WM_DELETE_WINDOW", lambda: None)
        root.attributes("-topmost", True)
        root.attributes("-fullscreen", True)

        root.bind("<Alt-F4>",    lambda e: "break")
        root.bind("<Control-w>", lambda e: "break")
        root.bind("<Control-q>", lambda e: "break")
        root.bind("<Escape>",    lambda e: "break")

        W = root.winfo_screenwidth()
        H = root.winfo_screenheight()
        root.geometry(f"{W}x{H}+0+0")

        # Fonts
        try:
            f_title  = tkfont.Font(family="Amiri",          size=46, weight="bold")
            f_arabic = tkfont.Font(family="Amiri",          size=26)
            f_times  = tkfont.Font(family="Courier New",    size=18, weight="bold")
            f_label  = tkfont.Font(family="Helvetica Neue", size=20)
            f_prompt = tkfont.Font(family="Helvetica Neue", size=16)
            f_entry  = tkfont.Font(family="Courier New",    size=18)
            f_exit   = tkfont.Font(family="Helvetica Neue", size=22, weight="bold")
            f_count  = tkfont.Font(family="Helvetica Neue", size=14)
        except Exception:
            f_title  = tkfont.Font(size=46, weight="bold")
            f_arabic = tkfont.Font(size=26)
            f_times  = tkfont.Font(family="Courier New", size=18, weight="bold")
            f_label  = tkfont.Font(size=20)
            f_prompt = tkfont.Font(size=16)
            f_entry  = tkfont.Font(family="Courier New", size=18)
            f_exit   = tkfont.Font(size=22, weight="bold")
            f_count  = tkfont.Font(size=14)

        # Colors
        BG       = "#0a0f1e"
        GOLD     = "#c9a84c"
        GOLD_DK  = "#8a6a1e"
        GREEN    = "#1a5e3a"
        GREEN_LT = "#2eb87b"
        WHITE    = "#f0ece0"
        MUTED    = "#7a8099"
        RED_BTN  = "#c0392b"
        RED_HOV  = "#e74c3c"

        root.configure(bg=BG)

        # Decorative arcs
        canvas = tk.Canvas(root, bg=BG, highlightthickness=0, width=W, height=H)
        canvas.place(x=0, y=0)
        for r in [320, 280, 240]:
            canvas.create_arc(W//2 - r, 80 - r, W//2 + r, 80 + r,
                              start=180, extent=180,
                              outline=GOLD, width=1, style="arc")

        # Title
        tk.Label(root, text="🕌  Salat Reminder", font=f_title,
                 fg=GOLD, bg=BG).place(relx=0.5, y=60, anchor="center")
        tk.Label(root, text="الصَّلاةُ خَيْرٌ مِنَ النَّوْمِ",
                 font=f_arabic, fg=GOLD_DK, bg=BG).place(
                 relx=0.5, y=120, anchor="center")

        # Prayer times table (built once; highlighting is static at build time)
        table_frame = tk.Frame(root, bg=BG)
        table_frame.place(relx=0.5, y=200, anchor="n")
        self._table_frame = table_frame
        self._build_table(table_frame, GREEN, GREEN_LT, WHITE, GOLD, MUTED, f_times)

        # "Wach slity X?" label
        self.current_prayer_var = tk.StringVar()
        prompt_top = tk.Label(root, textvariable=self.current_prayer_var,
                              font=f_label, fg=GREEN_LT, bg=BG)
        prompt_top.place(relx=0.5, rely=0.72, anchor="center")

        # Instruction
        tk.Label(root, text='Kteb: "wlh hta slit [ssm salat]" bash t7el',
                 font=f_prompt, fg=MUTED, bg=BG).place(
                 relx=0.5, rely=0.77, anchor="center")

        # Entry
        entry_frame = tk.Frame(root, bg=GOLD, padx=2, pady=2)
        entry_frame.place(relx=0.5, rely=0.83, anchor="center")
        self.entry_var = tk.StringVar()
        entry = tk.Entry(entry_frame, textvariable=self.entry_var,
                         font=f_entry, bg="#12192e", fg=WHITE,
                         insertbackground=GOLD, relief="flat", width=40)
        entry.pack(ipady=10, ipadx=10)
        entry.bind("<Return>", self._check_input)
        self.entry_widget = entry

        # Feedback
        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = tk.Label(root, textvariable=self.feedback_var,
                                       font=f_prompt, fg="#e74c3c", bg=BG)
        self.feedback_label.place(relx=0.5, rely=0.88, anchor="center")

        # EXIT button
        exit_btn = tk.Button(root, text="🚪  EXIT", font=f_exit,
                             bg=RED_BTN, fg=WHITE,
                             activebackground=RED_HOV, activeforeground=WHITE,
                             relief="flat", padx=30, pady=12,
                             cursor="hand2", command=kill_app)
        exit_btn.place(relx=0.5, rely=0.94, anchor="center")
        exit_btn.bind("<Enter>", lambda e: exit_btn.config(bg=RED_HOV))
        exit_btn.bind("<Leave>", lambda e: exit_btn.config(bg=RED_BTN))

        # Status / countdown label
        self.countdown_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.countdown_var,
                 font=f_count, fg=MUTED, bg=BG).place(
                 relx=0.5, rely=0.98, anchor="center")

        # Live clock
        self.clock_var = tk.StringVar()
        tk.Label(root, textvariable=self.clock_var,
                 font=f_count, fg=MUTED, bg=BG).place(
                 relx=0.98, rely=0.01, anchor="ne")
        self._tick_clock()

        # Store colors for table rebuild
        self._colors = (BG, GREEN, GREEN_LT, WHITE, GOLD, MUTED, f_times)

    def _build_table(self, frame, GREEN, GREEN_LT, WHITE, GOLD, MUTED, f_times):
        """Draw prayer rows; highlight the current prayer."""
        for widget in frame.winfo_children():
            widget.destroy()

        BG = self._colors[0] if hasattr(self, "_colors") else "#0a0f1e"
        current = get_current_prayer()

        for i, name in enumerate(PRAYER_ORDER):
            h, m = PRAYER_TIMES[name]
            time_str   = f"{h:02d}:{m:02d}"
            is_current = (name == current)
            row_bg = GREEN   if is_current else BG
            row_fg = GREEN_LT if is_current else WHITE
            marker = "▶  "   if is_current else "   "

            row = tk.Frame(frame, bg=row_bg, padx=20, pady=6,
                           highlightthickness=1 if is_current else 0,
                           highlightbackground=GREEN_LT)
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=40)

            tk.Label(row, text=f"{marker}{name:<8}", font=f_times,
                     fg=row_fg, bg=row_bg, width=12, anchor="w").pack(side="left")
            tk.Label(row, text=time_str, font=f_times,
                     fg=GOLD if is_current else MUTED,
                     bg=row_bg).pack(side="right", padx=20)

    # ── Clock ─────────────────────────────────────────────────────────────────

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%H:%M:%S  |  %A %d %b %Y")
        self.clock_var.set(now)
        self.root.after(1000, self._tick_clock)

    # ── Scheduling logic ──────────────────────────────────────────────────────

    def _start_startup_delay(self):
        """On first launch: wait 4 min, then show for current prayer."""
        def run():
            for remaining in range(self.STARTUP_DELAY, 0, -1):
                mins, secs = divmod(remaining, 60)
                self.root.after(0, self.countdown_var.set,
                                f"Starting in {mins:02d}:{secs:02d} …")
                time.sleep(1)
            self.root.after(0, self._show_window)
        threading.Thread(target=run, daemon=True).start()

    def _wait_for_next_prayer(self):
        """
        After confirming a prayer, sleep until the NEXT prayer time,
        then show the window again.
        """
        def run():
            next_name, next_dt = get_next_prayer()
            secs = seconds_until(next_dt)

            # Show a live countdown in the status label while hidden
            while secs > 1:
                secs = seconds_until(next_dt)
                h = int(secs // 3600)
                m = int((secs % 3600) // 60)
                s = int(secs % 60)
                label = f"Next: {next_name} — {h:02d}:{m:02d}:{s:02d}"
                self.root.after(0, self.countdown_var.set, label)
                time.sleep(1)

            self.root.after(0, self._show_window)

        self._wait_thread = threading.Thread(target=run, daemon=True)
        self._wait_thread.start()

    # ── Window show / hide ────────────────────────────────────────────────────

    def _show_window(self):
        # Rebuild table so the correct prayer is highlighted
        BG, GREEN, GREEN_LT, WHITE, GOLD, MUTED, f_times = self._colors
        self._build_table(self._table_frame, GREEN, GREEN_LT, WHITE, GOLD, MUTED, f_times)

        self.current_prayer_var.set(f"Wach slity {get_current_prayer()}? ✦")
        self.countdown_var.set("")
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.root.after(100, self._grab_entry_focus)

    def _grab_entry_focus(self):
        self.entry_widget.focus_force()
        self.entry_widget.focus_set()
        self._focus_job = self.root.after(500, self._keep_focus)

    def _keep_focus(self):
        try:
            self.entry_widget.focus_force()
        except Exception:
            pass
        self._focus_job = self.root.after(500, self._keep_focus)

    # ── Input check ───────────────────────────────────────────────────────────

    def _check_input(self, event=None):
        text    = self.entry_var.get().strip().lower()
        current = get_current_prayer()
        expected = f"wlh hta slit {current.lower()}"

        if text == expected:
            self.feedback_var.set("✅  Barakallahu fik! Salat maqbula insha'Allah.")
            self.feedback_label.config(fg="#2eb87b")
            self._confirmed_prayer = current
            self.root.after(1500, self._hide_window)
        else:
            self.feedback_var.set(
                f'❌  Kteb bssah: "wlh hta slit {current}"')
            self.entry_var.set("")

    # ── Hide ──────────────────────────────────────────────────────────────────

    def _hide_window(self):
        self.entry_var.set("")
        self.feedback_var.set("")
        if self._focus_job is not None:
            self.root.after_cancel(self._focus_job)
            self._focus_job = None
        self.root.withdraw()
        # Now wait until the NEXT prayer — not 4 minutes
        self._wait_for_next_prayer()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    SalatApp()
