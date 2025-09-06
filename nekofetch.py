#!/usr/bin/env python3
import os
import sys
import time
import math
import socket
import shutil
import platform
import subprocess
from datetime import datetime
import threading

import psutil
from PIL import ImageGrab, Image

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

APP_NAME = "nekofetch"

# ---------- helpers ----------
def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
        return out.strip()
    except Exception:
        return ""

def try_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default

def seconds_to_human(s):
    days, rem = divmod(int(s), 86400)
    hrs, rem = divmod(rem, 3600)
    mins, _ = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}d")
    if hrs: parts.append(f"{hrs}h")
    if mins or not parts: parts.append(f"{mins}m")
    return " ".join(parts)

def get_os_pretty():
    # python 3.10+ has platform.freedesktop_os_release on linux
    pretty = ""
    try:
        if hasattr(platform, "freedesktop_os_release"):
            data = platform.freedesktop_os_release()
            pretty = data.get("PRETTY_NAME", "")
    except Exception:
        pass
    if not pretty and sys.platform == "darwin":
        ver, _, _ = platform.mac_ver()
        pretty = f"macOS {ver}"
    if not pretty and sys.platform.startswith("win"):
        pretty = platform.platform()
    if not pretty:
        pretty = " ".join([platform.system(), platform.release()]).strip()
    return pretty

def detect_wm_de():
    env = os.environ
    de = env.get("XDG_CURRENT_DESKTOP") or env.get("DESKTOP_SESSION") or env.get("XDG_SESSION_DESKTOP") or ""
    de = de.replace(":", " + ")
    # naive wm scan
    wm_candidates = ["i3", "sway", "bspwm", "qtile", "awesome", "openbox", "xmonad", "herbstluftwm",
                     "gnome-shell", "kwin_x11", "kwin_wayland", "mutter", "xfwm4", "Marco", "weston"]
    found = set()
    try:
        for p in psutil.process_iter(["name"]):
            n = (p.info.get("name") or "").lower()
            for c in wm_candidates:
                if c.lower() in n:
                    found.add(c)
    except Exception:
        pass
    wm = " / ".join(sorted(found)) if found else ""
    return wm, de

def detect_gpu():
    # very light heuristics
    # try nvidia-smi
    out = run_cmd(["bash", "-lc", "command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name --format=csv,noheader || true"])
    if out:
        return out.splitlines()[0]
    # try lspci
    out = run_cmd(["bash", "-lc", "command -v lspci >/dev/null && lspci -mm | grep -i 'VGA\\|3D' | head -n1 || true"])
    if out:
        return " ".join(out.split()[2:]).strip(' "')
    # mac
    if sys.platform == "darwin":
        out = run_cmd(["system_profiler", "SPDisplaysDataType"])
        for line in out.splitlines():
            if "Chipset Model:" in line:
                return line.split(":", 1)[1].strip()
    return "unknown gpu"

def detect_packages():
    # count installed packages if we can
    managers = [
        ("dpkg", "bash -lc 'command -v dpkg >/dev/null && dpkg -l | grep -E \"^ii\" | wc -l || true'"),
        ("pacman", "bash -lc 'command -v pacman >/dev/null && pacman -Q | wc -l || true'"),
        ("rpm", "bash -lc 'command -v rpm >/dev/null && rpm -qa | wc -l || true'"),
        ("apk", "bash -lc 'command -v apk >/dev/null && apk info | wc -l || true'"),
        ("brew", "bash -lc 'command -v brew >/dev/null && brew list | wc -l || true'"),
        ("winget", "bash -lc 'command -v winget >/dev/null && winget list | tail -n +3 | wc -l || true'")
    ]
    for name, cmd in managers:
        out = run_cmd(cmd.split())
        n = try_int(out, None)
        if n:
            return f"{n} via {name}"
    return "unknown"

def detect_resolution(root):
    try:
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        return f"{w}x{h}"
    except Exception:
        return "unknown"

def detect_terminal():
    # if launched from terminal we might have TERM
    return os.environ.get("TERM", "unknown")

def detect_shell():
    if sys.platform.startswith("win"):
        return os.environ.get("COMSPEC", "cmd")
    return os.environ.get("SHELL", run_cmd(["bash", "-lc", "echo \"$SHELL\""])).strip() or "unknown"

def disk_summary():
    try:
        total, used, free = shutil.disk_usage("/")
        gb = 1024**3
        return f"{used//gb}G / {total//gb}G"
    except Exception:
        return "unknown"

def get_info(root):
    boot = datetime.fromtimestamp(psutil.boot_time())
    uptime = time.time() - psutil.boot_time()

    wm, de = detect_wm_de()
    info = {
        "user": os.environ.get("USER") or os.environ.get("USERNAME") or "user",
        "host": socket.gethostname(),
        "os": get_os_pretty(),
        "kernel": platform.release(),
        "uptime": seconds_to_human(uptime),
        "shell": detect_shell(),
        "wm": wm or "unknown",
        "de": de or "unknown",
        "cpu": platform.processor() or platform.machine(),
        "gpu": detect_gpu(),
        "memory": f"{(psutil.virtual_memory().used // (1024**2))}MiB / {(psutil.virtual_memory().total // (1024**2))}MiB",
        "disk": disk_summary(),
        "battery": "charging" if (psutil.sensors_battery() and psutil.sensors_battery().power_plugged) else
                   (f"{psutil.sensors_battery().percent:.0f}%" if psutil.sensors_battery() else "n/a"),
        "packages": detect_packages(),
        "resolution": detect_resolution(root),
        "terminal": detect_terminal(),
        "boot": boot.strftime("%Y-%m-%d %H:%M")
    }
    return info

def info_to_text(info):
    lines = []
    uhost = f"{info['user']}@{info['host']}"
    lines.append(f"{uhost}")
    lines.append(f"os:        {info['os']}")
    lines.append(f"kernel:    {info['kernel']}")
    lines.append(f"uptime:    {info['uptime']}")
    lines.append(f"shell:     {info['shell']}")
    lines.append(f"wm:        {info['wm']}")
    lines.append(f"de:        {info['de']}")
    lines.append(f"cpu:       {info['cpu']}")
    lines.append(f"gpu:       {info['gpu']}")
    lines.append(f"memory:    {info['memory']}")
    lines.append(f"disk:      {info['disk']}")
    lines.append(f"battery:   {info['battery']}")
    lines.append(f"packages:  {info['packages']}")
    lines.append(f"resolution:{info['resolution']}")
    lines.append(f"terminal:  {info['terminal']}")
    lines.append(f"boot:      {info['boot']}")
    return "\n".join(lines)

# ---------- ui ----------
class GradientCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, highlightthickness=0, **kw)
        self.phase = 0.0
        self.running = True
        self.bind("<Configure>", lambda e: self.draw())
        self.after(30, self.animate)

    def animate(self):
        if not self.running:
            return
        self.phase += 0.008
        self.draw()
        self.after(30, self.animate)

    def draw(self):
        self.delete("grad")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 0 or h <= 0:
            return
        # simple vertical gradient that slowly shifts hues
        steps = 40
        for i in range(steps):
            t = i / (steps - 1)
            hue = (self.phase + t * 0.25) % 1.0
            r, g, b = hsl_to_rgb(hue, 0.4, 0.12)
            color = "#%02x%02x%02x" % (int(r*255), int(g*255), int(b*255))
            self.create_rectangle(0, int(t*h), w, int((t+1/steps)*h), fill=color, outline=color, tags="grad")

def hsl_to_rgb(h, s, l):
    # tiny HSL to RGB for nicer palettes
    # adapted from colorsys but inline to avoid import
    c = (1 - abs(2*l - 1)) * s
    x = c * (1 - abs(((h*6) % 2) - 1))
    m = l - c/2
    r = g = b = 0
    seg = int(h*6) % 6
    if seg == 0: r, g, b = c, x, 0
    elif seg == 1: r, g, b = x, c, 0
    elif seg == 2: r, g, b = 0, c, x
    elif seg == 3: r, g, b = 0, x, c
    elif seg == 4: r, g, b = x, 0, c
    else: r, g, b = c, 0, x
    return r+m, g+m, b+m

class Meter(ttk.Frame):
    def __init__(self, master, label, getter, **kw):
        super().__init__(master, **kw)
        self.getter = getter
        self.var = tk.DoubleVar(value=0.0)
        self.text = tk.StringVar(value=f"{label}: 0%")
        self.label = ttk.Label(self, textvariable=self.text)
        self.label.pack(anchor="w")
        self.canvas = tk.Canvas(self, height=14, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=0, pady=(2, 8))
        self.after(300, self.tick)
        self.bind("<Configure>", lambda e: self.draw())

    def draw(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.delete("all")
        pct = max(0.0, min(1.0, self.var.get() / 100.0))
        self.canvas.create_rectangle(0, 0, w, h, outline="", fill="#1f1f1f")
        self.canvas.create_rectangle(0, 0, int(w*pct), h, outline="", fill="#5fb3b3")

    def tick(self):
        try:
            val = float(self.getter())
        except Exception:
            val = 0.0
        # ease the number a little
        current = self.var.get()
        eased = current + (val - current) * 0.2
        self.var.set(eased)
        label = self.label.cget("text").split(":")[0]
        self.text.set(f"{label}: {int(self.var.get()):d}%")
        self.draw()
        self.after(500, self.tick)

class nekofetch(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("760x520")
        self.minsize(640, 460)

        # layered gradient background
        self.bg = GradientCanvas(self)
        self.bg.pack(fill="both", expand=True)

        # content frame on top
        self.content = ttk.Frame(self.bg, padding=16)
        self.content.place(relx=0.5, rely=0.5, anchor="center")

        # title
        self.title_var = tk.StringVar(value="nekofetch")
        ttk.Label(self.content, textvariable=self.title_var, font=("JetBrains Mono", 18, "bold")).pack(anchor="w")

        # info box
        self.info_text = tk.Text(self.content, height=14, width=80, wrap="none", bd=0, relief="flat")
        self.info_text.configure(state="disabled")
        self.info_text.pack(fill="both", expand=False, pady=(10, 8))

        # meters
        meters = ttk.Frame(self.content)
        meters.pack(fill="x")
        self.cpu_meter = Meter(meters, "cpu", lambda: psutil.cpu_percent(interval=None))
        self.mem_meter = Meter(meters, "memory", lambda: psutil.virtual_memory().percent)
        self.cpu_meter.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.mem_meter.pack(side="left", fill="x", expand=True)

        # controls
        controls = ttk.Frame(self.content)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Button(controls, text="refresh", command=self.refresh).pack(side="left")
        ttk.Button(controls, text="copy", command=self.copy_text).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="export png", command=self.export_png).pack(side="left", padx=(8, 0))
        self.theme = tk.StringVar(value="dark")
        ttk.Button(controls, text="toggle theme", command=self.toggle_theme).pack(side="right")

        # initial fill and periodic refresh
        self._stop = False
        self.refresh()
        self.after(3000, self.periodic_refresh)

        # apply dark theme defaults
        self.style = ttk.Style(self)
        self.apply_theme()

        # close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self._stop = True
        self.bg.running = False
        self.destroy()

    def periodic_refresh(self):
        if self._stop:
            return
        self.refresh()
        self.after(5000, self.periodic_refresh)

    def refresh(self):
        info = get_info(self)
        self.title_var.set(f"{info['user']}@{info['host']}")
        text = info_to_text(info)
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", text)
        self.info_text.configure(state="disabled")

    def copy_text(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.info_text.get("1.0", "end-1c"))
        except Exception as e:
            messagebox.showerror(APP_NAME, f"copy failed: {e}")

    def export_png(self):
        # capture the app window to PNG using Pillow ImageGrab
        try:
            self.update_idletasks()
            x = self.winfo_rootx()
            y = self.winfo_rooty()
            w = self.winfo_width()
            h = self.winfo_height()
            bbox = (x, y, x + w, y + h)
            img = ImageGrab.grab(bbox=bbox)
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")], initialfile="nekofetch.png")
            if path:
                img.save(path, "PNG")
        except Exception as e:
            messagebox.showerror(APP_NAME, f"export failed: {e}\ntry running under X11 or install scrot then retry")

    def toggle_theme(self):
        self.theme.set("light" if self.theme.get() == "dark" else "dark")
        self.apply_theme()

    def apply_theme(self):
        dark = self.theme.get() == "dark"
        fg = "#e6e6e6" if dark else "#1a1a1a"
        bg = "#121212" if dark else "#fafafa"
        accent = "#5fb3b3" if dark else "#006a6a"

        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TButton", background=bg, foreground=fg)
        self.style.map("TButton", foreground=[("active", fg)], background=[("active", bg)])
        self.info_text.configure(bg="#1b1b1b" if dark else "#ffffff", fg=fg, insertbackground=fg)

        # move content over gradient for readable contrast
        self.content.configure(style="TFrame")

if __name__ == "__main__":
    app = nekofetch()
    app.mainloop()
