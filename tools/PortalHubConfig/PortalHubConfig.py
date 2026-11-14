"""Portal Hub Config: pick a world and a look for each open slot of the portal room, then Save.

Run it with PortalHubConfig.bat, with the packaged PortalHubConfig.exe, or with  python PortalHubConfig.py .
Python standard library only (Tkinter). Optional switches for testing:
  --config <file>      edit this file instead of looking for the installed mod (the install check is shown, not enforced)
  --game <folder>      check this game folder instead of looking through the Steam libraries
  --roundtrip <out>    read the config, write it to <out> unchanged, and exit
  --screenshot <png>   save pictures of each screen and exit (needs Pillow)
"""
from __future__ import annotations

import argparse
import ctypes
import math
import os
import re
import struct
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
import zlib
from tkinter import colorchooser, filedialog

import hubdata as hd
import install_check as ic
from luaconfig import HubConfig, LuaError, Portal, World, fmt_num, read_manual_exits

APP = "Cordona Corporations Portal Hub Assistant Tool"
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
TOOL_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR
ICON_DIR = os.path.join(BASE_DIR, "icons")
SETTINGS_FILE = os.path.join(os.environ.get("APPDATA", ""), "PortalHubConfig", "config-path.txt")
GAME_FILE = os.path.join(os.environ.get("APPDATA", ""), "PortalHubConfig", "game-path.txt")
PAD_ID_RX = re.compile(r"^[A-Za-z0-9_\-]+$")

MONO = "Consolas"
CARD_W = 176
# Dark mode: a night-shift control room in purple. Black glass, CRT panels, amber hazard tape.
T = dict(bg="#0d0a13", chassis="#141020", panel="#1a1529", line="#3b2f58", fg="#e2d6ff", dim="#9181bd",
         accent="#b583ff", on_accent="#140c20", hover="#2a2140", bad="#ff8a80", warn="#ffc266", good="#7df0b0",
         status_good="#7df0b0", status_bad="#ff8a80", head="#0d0a13", head_fg="#b583ff", head_dim="#9181bd",
         crt="#0b0812", crt_hi="#1a1329", crt_line="#1f1830", card="#1a1428", crt_fg="#e2d6ff", crt_dim="#9181bd",
         crt_good="#7df0b0", crt_bad="#ff8a80", crt_edge="#3b2f58", slot_off="#100c19", stripe="#ffc247", stripe_bg="#0d0a13")
S = 1.0            # screen scale: 1.0 at 96 DPI


def px(n):
    return int(round(n * S))


def font(size=10, bold=False):
    return (MONO, size, "bold") if bold else (MONO, size)


def text_width(widget, text, size=10, bold=False):
    return tkfont.Font(root=widget, family=MONO, size=size, weight="bold" if bold else "normal").measure(text)


def fit_text(widget, text, room, size, bold, smallest=7):
    """The largest font size from size down at which text fits in room pixels; the text is shortened only past smallest."""
    for sz in range(size, smallest - 1, -1):
        if text_width(widget, text, sz, bold) <= room:
            return text, sz
    while text and text_width(widget, text + "...", smallest, bold) > room:
        text = text[:-1]
    return text + "...", smallest


# ------------------------------------------------------------------ finding config.lua
# 1. the path remembered from last time, 2. the mod folder around this program, 3. the installed mod in a Steam library,
# 4. the copy of the mod in the repo, 5. a file picker.
REL_CONFIG = os.path.join("steamapps", "common", "AbioticFactor", "AbioticFactor", "Binaries", "Win64", "ue4ss", "Mods",
                          "PortalHub", "Scripts", "config.lua")


steam_libraries = ic.steam_libraries


def find_config():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8-sig") as f:
            saved = f.read().strip()
        if saved and os.path.exists(saved):
            return saved
    d = TOOL_DIR
    for _ in range(4):
        for sub in (("PortalHub", "Scripts"), ("Mods", "PortalHub", "Scripts")):
            cand = os.path.join(d, *sub, "config.lua")
            if os.path.exists(cand):
                return cand
        d = os.path.dirname(d)
    for lib in steam_libraries():
        cand = os.path.join(lib, REL_CONFIG)
        if os.path.exists(cand):
            return cand
    repo = os.path.abspath(os.path.join(TOOL_DIR, "..", "..", "mod", "PortalHub", "Scripts", "config.lua"))
    return repo if os.path.exists(repo) else None


def remember_config(path):
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            f.write(path)
    except OSError:
        pass


# ------------------------------------------------------------------ the install check (install_check.py; read only)
def remembered(path_file):
    try:
        with open(path_file, encoding="utf-8-sig") as f:
            return f.read().strip() or None
    except OSError:
        return None


def remember_game(folder):
    try:
        os.makedirs(os.path.dirname(GAME_FILE), exist_ok=True)
        with open(GAME_FILE, "w", encoding="utf-8") as f:
            f.write(folder)
    except OSError:
        pass


def check_game(*first):
    """Find the game (the folders given first, then a remembered one, the remembered config, this program's folder,
    the Steam libraries) and check the hub's install there."""
    hints = [h for h in (*first, remembered(GAME_FILE), remembered(SETTINGS_FILE), TOOL_DIR) if h]
    return ic.check_install(ic.find_game(hints=hints))


def pick_game_folder(parent):
    """Ask for the game's folder. Returns the game folder, or None (with a message if the pick wasn't the game)."""
    picked = filedialog.askdirectory(parent=parent, mustexist=True,
                                     title="Pick Abiotic Factor's folder (Steam library\\steamapps\\common\\AbioticFactor)")
    if not picked:
        return None
    game = ic.game_folder_from(picked)
    if not game:
        ask(parent, APP, f"That folder isn't Abiotic Factor's:\n\n{os.path.normpath(picked)}\n\n"
                         "Pick the AbioticFactor folder in your Steam library (steamapps\\common\\AbioticFactor).", [("OK", 1)])
        return None
    remember_game(game)
    return game


INSTALL_COLOURS = {"ok": "status_good", "warn": "warn", "missing": "status_bad", "nogame": "status_bad"}
INSTALL_MARKS = {"ok": "INSTALLED", "warn": "CHECK", "missing": "MISSING", "nogame": "NO GAME"}


class InstallBar(tk.Frame):
    """The install check's status line: a mark, what was found and what to do, RE-CHECK and PICK GAME FOLDER."""

    def __init__(self, parent, on_recheck, on_pick):
        super().__init__(parent, bg=T["panel"], padx=px(12), pady=px(6), highlightthickness=1, highlightbackground=T["line"])
        self.mark = tk.Label(self, bg=T["panel"], font=font(9, True), width=10, anchor="w")
        self.mark.pack(side="left", anchor="n")
        Btn(self, "RE-CHECK", on_recheck, small=True).pack(side="right", anchor="n")
        self.pick = Btn(self, "PICK GAME FOLDER", on_pick, small=True)
        self.pick.pack(side="right", anchor="n", padx=px(6))
        self.text = tk.Label(self, bg=T["panel"], fg=T["fg"], font=font(9), anchor="w", justify="left")
        self.text.pack(side="left", fill="x", expand=True, padx=(px(6), px(8)))
        self.tip = Tip(self.mark, "")
        self.bind("<Configure>", lambda e: self.text.configure(wraplength=max(px(200), e.width - px(360))))

    def show(self, report):
        if report is None:
            self.mark.configure(text="NOT CHECKED", fg=T["dim"])
            self.text.configure(text="Install check skipped.")
            return
        colour = T[INSTALL_COLOURS[report.state]]
        self.mark.configure(text=INSTALL_MARKS[report.state], fg=colour)
        self.text.configure(text=report.text(), fg=T["fg"] if report.state == "ok" else colour)
        self.tip.text = ("Game: " + report.game) if report.game else "No game folder found."


# ------------------------------------------------------------------ small widgets
class Btn(tk.Label):
    def __init__(self, parent, text, command=None, primary=False, small=False, width=None):
        self.command, self.primary, self.enabled = command, primary, True
        super().__init__(parent, text=text, font=font(9 if small else 10, True), cursor="hand2", width=width,
                         padx=px(8 if small else 14), pady=px(3 if small else 7), highlightthickness=1)
        self.paint()
        self.bind("<Button-1>", lambda e: self.enabled and self.command and self.command())
        self.bind("<Enter>", lambda e: self.paint(True))
        self.bind("<Leave>", lambda e: self.paint())

    def paint(self, hot=False):
        if not self.enabled:
            self.configure(bg=T["panel"], fg=T["line"], highlightbackground=T["line"], cursor="arrow")
        elif self.primary:
            self.configure(bg=T["accent"], fg=T["on_accent"], highlightbackground=T["accent"], cursor="hand2")
        else:
            self.configure(bg=T["hover"] if hot else T["panel"], fg=T["fg"], highlightbackground=T["line"], cursor="hand2")

    def set_enabled(self, on):
        self.enabled = on
        self.paint()


class Segmented(tk.Frame):
    def __init__(self, parent, options, command, bg):
        super().__init__(parent, bg=bg)
        self.command, self.value, self.labels, self.enabled = command, None, {}, True
        for i, (label, value) in enumerate(options):
            w = tk.Label(self, text=label, font=font(9, True), padx=px(9), pady=px(5), cursor="hand2")
            w.pack(side="left", padx=(0 if i == 0 else 1, 0))
            w.bind("<Button-1>", lambda e, v=value: self.enabled and self.command(v))
            self.labels[value] = w

    def set(self, value):
        self.value = value
        for v, w in self.labels.items():
            on = v == value
            if not self.enabled:
                w.configure(bg=T["hover"] if on else T["panel"], fg=T["dim"] if on else T["line"], cursor="arrow")
            else:
                w.configure(bg=T["accent"] if on else T["panel"], fg=T["on_accent"] if on else T["fg"], cursor="hand2")

    def set_enabled(self, on):
        self.enabled = on
        self.set(self.value)


class Tip:
    """Hover help."""

    def __init__(self, widget, text):
        self.widget, self.text, self.win, self.job = widget, text, None, None
        widget.bind("<Enter>", self.arm, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<Button-1>", self.hide, add="+")

    def arm(self, _):
        self.job = self.widget.after(350, self.show)

    def show(self):
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + px(4)
        self.win = tk.Toplevel(self.widget)
        self.win.overrideredirect(True)
        self.win.geometry(f"+{x}+{y}")
        tk.Label(self.win, text=self.text, bg=T["crt"], fg=T["crt_fg"], font=font(9), justify="left", wraplength=px(430),
                 padx=px(8), pady=px(5), highlightthickness=1, highlightbackground=T["crt_edge"]).pack()

    def hide(self, _=None):
        if self.job:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.win:
            self.win.destroy()
            self.win = None


class Field(tk.Frame):
    """A text box set into a CRT panel."""

    def __init__(self, parent, var=None, width=10, justify="left", on_change=None):
        super().__init__(parent, bg=T["crt"], highlightthickness=1, highlightbackground=T["crt_edge"], highlightcolor=T["accent"])
        self.var = var or tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, width=width, justify=justify, bd=0, font=font(10), bg=T["crt"],
                              fg=T["crt_fg"], insertbackground=T["crt_fg"], disabledbackground=T["crt"],
                              disabledforeground=T["crt_dim"], readonlybackground=T["crt"], selectbackground=T["accent"],
                              selectforeground=T["on_accent"], highlightthickness=0)
        self.entry.pack(fill="x", expand=True, padx=px(7), pady=px(5))
        if on_change:
            self.var.trace_add("write", lambda *_: on_change())

    def set_enabled(self, on):
        self.entry.configure(state="normal" if on else "disabled")

    def set_bad(self, bad):
        self.configure(highlightbackground=T["crt_bad"] if bad else T["crt_edge"])


class Stepper(tk.Frame):
    """A number with - and + beside it. Steps with the buttons, the arrow keys or the mouse wheel; can also be typed."""

    def __init__(self, parent, lo, hi, step, decimals, on_change, bg):
        super().__init__(parent, bg=bg)
        self.lo, self.hi, self.step, self.decimals, self.on_change = lo, hi, step, decimals, on_change
        self.guard = False
        self.minus = Btn(self, "-", lambda: self.nudge(-1), small=True)
        self.minus.pack(side="left")
        self.field = Field(self, width=5, justify="center", on_change=self.typed)
        self.field.pack(side="left", padx=px(3))
        self.plus = Btn(self, "+", lambda: self.nudge(1), small=True)
        self.plus.pack(side="left")
        self.field.entry.bind("<Up>", lambda e: self.nudge(1))
        self.field.entry.bind("<Down>", lambda e: self.nudge(-1))
        self.field.entry.bind("<MouseWheel>", lambda e: self.nudge(1 if e.delta > 0 else -1))
        self.field.entry.bind("<FocusOut>", lambda e: self.set(self.get()))

    def get(self):
        try:
            v = float(self.field.var.get())
            return min(self.hi, max(self.lo, v))
        except ValueError:
            return self.lo

    def set(self, v):
        self.guard = True
        self.field.var.set(f"{v:.{self.decimals}f}")
        self.guard = False

    def nudge(self, sign):
        self.set(min(self.hi, max(self.lo, round(self.get() + sign * self.step, 3))))
        self.on_change(self.get())

    def typed(self):
        if not self.guard:
            self.on_change(self.get())

    def set_enabled(self, on):
        self.field.set_enabled(on)
        self.minus.set_enabled(on)
        self.plus.set_enabled(on)


class Bar(tk.Canvas):
    """A thin scrollbar that takes the theme (Windows draws tk.Scrollbar itself)."""

    def __init__(self, parent, command, bg):
        super().__init__(parent, width=px(10), bg=bg, highlightthickness=0)
        self.command, self.first, self.last = command, 0.0, 1.0
        self.bind("<Configure>", lambda e: self.paint())
        self.bind("<Button-1>", self.drag)
        self.bind("<B1-Motion>", self.drag)

    def set(self, first, last):
        self.first, self.last = float(first), float(last)
        self.paint()

    def paint(self):
        self.delete("all")
        if self.last - self.first >= 0.999:
            return
        h = self.winfo_height()
        self.create_rectangle(px(2), self.first * h, px(8), self.last * h, fill=T["crt_dim"], outline="")

    def drag(self, e):
        self.command("moveto", e.y / max(1, self.winfo_height()) - (self.last - self.first) / 2)


class Scrolled(tk.Frame):
    """A frame that scrolls: put the content in .inner."""

    def __init__(self, parent, bg):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, width=px(10), height=px(10))
        self.bar = Bar(self, self.canvas.yview, bg)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.bind_wheel(self.canvas)

    def bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self.wheel, add="+")

    def wheel(self, e):
        if self.bar.last - self.bar.first < 0.999:
            self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        return "break"


class Popup:
    """A dark, scrolling pop-up list with group headings. items: (heading, None, None) or (text, right text, value)."""
    ROW = 26
    VISIBLE = 13

    def __init__(self, anchor, items, on_pick, width, current=None):
        self.items, self.on_pick = items, on_pick
        self.win = tk.Toplevel(anchor)
        self.win.overrideredirect(True)
        self.win.configure(bg=T["crt_edge"])
        rows = min(len(items), self.VISIBLE)
        h = px(self.ROW) * rows + 2
        x, y = anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height() + px(2)
        if y + h > anchor.winfo_screenheight():
            y = anchor.winfo_rooty() - h - px(2)
        self.win.geometry(f"{width}x{h}+{x}+{y}")
        self.canvas = tk.Canvas(self.win, bg=T["crt"], highlightthickness=0, bd=0)
        self.bar = Bar(self.win, self.canvas.yview, T["crt"])
        self.canvas.configure(yscrollcommand=self.bar.set, scrollregion=(0, 0, width, px(self.ROW) * len(items)),
                              yscrollincrement=px(self.ROW))
        self.bar.pack(side="right", fill="y", pady=1, padx=(0, 1))
        self.canvas.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
        self.width = width
        self.hot = next((i for i, it in enumerate(items) if it[2] is not None and it[2] == current), None)
        self.paint()
        if self.hot is not None:
            self.canvas.yview_moveto(max(0, self.hot - 4) / max(1, len(items)))
        self.canvas.bind("<Motion>", self.motion)
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-2 if e.delta > 0 else 2, "units"))
        self.win.bind("<Escape>", lambda e: self.close())
        self.win.bind("<Up>", lambda e: self.step(-1))
        self.win.bind("<Down>", lambda e: self.step(1))
        self.win.bind("<Return>", lambda e: self.pick(self.hot))
        self.win.bind("<FocusOut>", lambda e: self.close())
        self.win.focus_force()

    def paint(self):
        c = self.canvas
        c.delete("all")
        row = px(self.ROW)
        for i, (text, right, value) in enumerate(self.items):
            y = i * row
            if value is None:
                c.create_rectangle(0, y, self.width, y + row, fill=T["crt_hi"], outline="")
                c.create_text(px(8), y + row / 2, text=text.upper(), anchor="w", fill=T["crt_dim"], font=font(9, True))
                continue
            hot = i == self.hot
            if hot:
                c.create_rectangle(0, y, self.width, y + row, fill=T["accent"], outline="")
            fg = T["on_accent"] if hot else T["crt_fg"]
            c.create_text(px(14), y + row / 2, text=text, anchor="w", fill=fg, font=font(10))
            if right:
                c.create_text(self.width - px(24), y + row / 2, text=right, anchor="e", fill=fg if hot else T["crt_dim"], font=font(9))

    def row_at(self, e):
        i = int(self.canvas.canvasy(e.y) // px(self.ROW))
        return i if 0 <= i < len(self.items) and self.items[i][2] is not None else None

    def motion(self, e):
        i = self.row_at(e)
        if i is not None and i != self.hot:
            self.hot = i
            self.paint()

    def click(self, e):
        self.pick(self.row_at(e))

    def step(self, d):
        i = 0 if self.hot is None else self.hot
        for _ in range(len(self.items)):
            i = (i + d) % len(self.items)
            if self.items[i][2] is not None:
                self.hot = i
                self.paint()
                self.canvas.yview_moveto(max(0, i - 4) / len(self.items))
                return

    def pick(self, i):
        if i is None:
            return
        value = self.items[i][2]
        self.close()
        self.on_pick(value)

    def close(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class Drop(tk.Frame):
    """A CRT-panel box that opens a Popup. items_fn gives the list when it opens."""

    def __init__(self, parent, items_fn, on_pick):
        super().__init__(parent, bg=T["crt"], highlightthickness=1, highlightbackground=T["crt_edge"], cursor="hand2")
        self.items_fn, self.on_pick, self.value, self.enabled = items_fn, on_pick, None, True
        self.label = tk.Label(self, bg=T["crt"], fg=T["crt_fg"], font=font(10), anchor="w", padx=px(7), pady=px(5))
        self.label.pack(side="left", fill="x", expand=True)
        self.arrow = tk.Label(self, text="▾", bg=T["crt"], fg=T["crt_fg"], font=font(10), padx=px(7))
        self.arrow.pack(side="right")
        for w in (self, self.label, self.arrow):
            w.bind("<Button-1>", lambda e: self.open())

    def open(self):
        if self.enabled:
            items = self.items_fn()
            rows = [text_width(self, t) + text_width(self, r or "", 9) + px(70) for t, r, v in items if v is not None]
            self.popup = Popup(self, items, self.on_pick, max([self.winfo_width()] + rows), self.value)

    def show(self, text, value=None):
        self.value = value
        self.label.configure(text=text)

    def set_enabled(self, on):
        self.enabled = on
        self.label.configure(fg=T["crt_fg"] if on else T["crt_dim"])
        self.arrow.configure(fg=T["crt_fg"] if on else T["crt_dim"])

    def set_bad(self, bad):
        self.configure(highlightbackground=T["crt_bad"] if bad else T["crt_edge"])


def scaled_image(root, path, size, background):
    """A PNG resized to size x size with a box filter, flattened onto background. (Tk itself only skips pixels.)"""
    src = tk.PhotoImage(master=root, file=path)
    w, h = src.width(), src.height()
    if w == size and h == size:
        return src
    rows = [r.split() for r in root.tk.splitlist(src.tk.call(src, "data", "-background", background))]
    px_rgb = [[(int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)) for c in r] for r in rows]
    out = []
    for y in range(size):
        y0, y1 = y * h // size, max(y * h // size + 1, (y + 1) * h // size)
        line = []
        for x in range(size):
            x0, x1 = x * w // size, max(x * w // size + 1, (x + 1) * w // size)
            cells = [px_rgb[j][i] for j in range(y0, y1) for i in range(x0, x1)]
            n = len(cells)
            line.append("#{:02x}{:02x}{:02x}".format(*(sum(c[k] for c in cells) // n for k in range(3))))
        out.append("{" + " ".join(line) + "}")
    img = tk.PhotoImage(master=root, width=size, height=size)
    img.put(" ".join(out))
    return img


def no_symbol_image(root, size):
    """The red no-entry ring for the barred slots, drawn here: Tk can't read SVG, and this stays sharp at any screen scale."""
    samples = 4
    rows = bytearray()
    for y in range(size):
        rows.append(0)                                    # PNG filter byte
        for x in range(size):
            red = white = 0
            for sy in range(samples):
                for sx in range(samples):
                    dx = ((x + (sx + 0.5) / samples) / size - 0.5) * 265
                    dy = ((y + (sy + 0.5) / samples) / size - 0.5) * 265
                    r = math.hypot(dx, dy)
                    if r > 132.5:
                        continue
                    if r >= 105.87 or abs(dx - dy) / math.sqrt(2) <= 10.65:
                        red += 1
                    else:
                        white += 1
            n = red + white
            if n == 0:
                rows += bytes(4)
            else:
                mix = [(0xb7 * red + 0xff * white) // n, (0x1f * red + 0xff * white) // n, (0x2e * red + 0xff * white) // n]
                rows += bytes(mix + [255 * n // samples ** 2])

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    png = (bytes.fromhex("89504e470d0a1a0a") + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))
    return tk.PhotoImage(master=root, data=png, format="png")


def window_icon(root):
    """A small portal ring, drawn here so no image file is needed."""
    n = 32
    img = tk.PhotoImage(master=root, width=n, height=n)
    rows = []
    for y in range(n):
        row = []
        for x in range(n):
            d = math.hypot(x - 15.5, y - 15.5)
            row.append("#c08bff" if 10 <= d <= 14.5 else "#ffc247" if d <= 5 else "#150f22")
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    root.iconphoto(True, img)
    root.window_icon = img


def dark_title_bar(win):
    """Windows only, and harmless where it isn't supported."""
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        rgb = int(T["head"][1:], 16)
        bgr = ctypes.c_int(((rgb & 0xff) << 16) | (rgb & 0xff00) | (rgb >> 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(bgr), 4)
    except (AttributeError, OSError):
        pass


class Dialog(tk.Toplevel):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(bg=T["chassis"])
        self.transient(parent)
        self.resizable(False, False)
        self.result = None
        self.bind("<Escape>", lambda e: self.close(None))
        self.protocol("WM_DELETE_WINDOW", lambda: self.close(None))
        self.body = tk.Frame(self, bg=T["chassis"], padx=px(18), pady=px(14))
        self.body.pack(fill="both", expand=True)

    def present(self, wait=True):
        self.update_idletasks()
        p = self.master
        x = p.winfo_rootx() + (p.winfo_width() - self.winfo_reqwidth()) // 2
        y = p.winfo_rooty() + (p.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry(f"+{x}+{y}")
        self.deiconify()
        dark_title_bar(self)
        if wait:
            self.grab_set()
            self.wait_window()
        return self.result

    def close(self, result):
        self.result = result
        self.grab_release()
        self.destroy()


def ask(parent, title, text, buttons):
    """A themed message box. buttons: list of (label, value), the first is the main one."""
    d = Dialog(parent, title)
    tk.Label(d.body, text=text, bg=T["chassis"], fg=T["fg"], font=font(10), justify="left", wraplength=px(440)).pack(anchor="w")
    row = tk.Frame(d.body, bg=T["chassis"])
    row.pack(anchor="e", pady=(px(14), 0))
    for i, (label, value) in enumerate(buttons):
        Btn(row, label, lambda v=value: d.close(v), primary=i == 0).pack(side="left", padx=(px(6), 0))
    return d.present()


class EffectsDialog(Dialog):
    """One box per named part of a look (on = shown). OK saves the choice for that look."""

    def __init__(self, parent, app, path, label):
        super().__init__(parent, "Effects - " + label)
        self.app, self.path = app, path
        name = hd.design_name(path)
        self.parts = hd.DESIGN_PARTS.get(name, [])
        hidden = app.cfg.hide.get(path, [])
        self.state = {p: p not in hidden for p in self.parts}
        self.boxes = {}
        tk.Label(self.body, text="Tick the parts of this look you want ON. Unticked parts are switched off\n"
                                 "for every portal that uses it.", bg=T["chassis"], fg=T["dim"], font=font(10),
                 justify="left").pack(anchor="w", pady=(0, px(10)))
        panel = tk.Frame(self.body, bg=T["crt"], padx=px(10), pady=px(8), highlightthickness=1, highlightbackground=T["crt_edge"])
        panel.pack(fill="x")
        notes = hd.PART_NOTES.get(name, {})
        for p in self.parts:
            locked = p in hd.PROTECTED_PARTS
            suffix = "  (always on)" if locked else f"  ({notes[p]})" if p in notes else ""
            row = tk.Label(panel, bg=T["crt"], fg=T["crt_dim"] if locked else T["crt_fg"], font=font(10), anchor="w",
                           cursor="arrow" if locked else "hand2")
            row.suffix = suffix
            row.pack(fill="x", pady=px(1))
            self.boxes[p] = row
            if not locked:
                row.bind("<Button-1>", lambda e, q=p: self.flip(q))
        self.paint()
        tk.Label(self.body, text="Part names come from the game's effect file. Untested: the game may\n"
                                 "ignore switching a part off.", bg=T["chassis"], fg=T["dim"], font=font(9),
                 justify="left").pack(anchor="w", pady=(px(10), 0))
        row = tk.Frame(self.body, bg=T["chassis"])
        row.pack(fill="x", pady=(px(12), 0))
        Btn(row, "ALL ON", self.all_on).pack(side="left")
        Btn(row, "CANCEL", lambda: self.close(None)).pack(side="right")
        Btn(row, "OK", self.ok, primary=True).pack(side="right", padx=px(6))

    def paint(self):
        for p, row in self.boxes.items():
            on = p in hd.PROTECTED_PARTS or self.state[p]
            row.configure(text=("[x] " if on else "[ ] ") + p + row.suffix)

    def flip(self, p):
        self.state[p] = not self.state[p]
        self.paint()

    def all_on(self):
        for p in self.state:
            self.state[p] = True
        self.paint()

    def ok(self):
        off = [p for p in self.parts if not self.state[p] and p not in hd.PROTECTED_PARTS]
        if off:
            self.app.cfg.hide[self.path] = off
        else:
            self.app.cfg.hide.pop(self.path, None)
        self.close(True)


# ------------------------------------------------------------------ custom worlds: checks
def world_problems(worlds):
    """(errors, warnings) for each world. Errors block saving; warnings (origins that may overlap) are shown but allowed."""
    out = []
    path_rx = re.compile(r"^/[A-Za-z0-9_/\-]+[A-Za-z0-9_\-]$")
    for i, w in enumerate(worlds):
        err, warn = [], []
        if w.raw:
            out.append((err, warn))
            continue
        if not w.id:
            err.append("Enter a world ID.")
        elif not PAD_ID_RX.match(w.id):
            err.append("The world ID can use letters, numbers, _ and - only.")
        elif hd.is_reserved(w.id):
            err.append("IDs starting with hub_ are reserved for the hub's own portals.")
        elif hd.is_dlc(w.id):
            err.append("IDs starting with H_Garden or H_Japan are the game's DLC areas; pick your own.")
        elif w.id in hd.KNOWN_BY_ID:
            err.append("That ID is one of the game's own pads; pick your own.")
        elif any(k != i and o.id.lower() == w.id.lower() for k, o in enumerate(worlds)):
            err.append("Another world already uses this ID.")
        if not path_rx.match(w.asset):
            err.append("Loader Blueprint: enter its package path, like /Game/Mods/MyWorld/BP_MyWorldLoader (no dots, no spaces).")
        if not re.match(r"^[A-Za-z0-9_]+_C$", w.cls):
            err.append("Loader class should end in _C, like BP_MyWorldLoader_C.")
        if not path_rx.match(w.level):
            err.append("Level: enter the map's package path, like /Game/Mods/MyWorld/Maps/MyWorld_L0.")
        if any(hd.names_dlc_map(p) for p in (w.asset, w.cls, w.level)):
            err.append("The loader or level names a DLC area (H_Garden or H_Japan), which the hub refuses.")
        if w.bad:
            err.append(w.bad)
        else:
            if max(abs(w.origin[0]), abs(w.origin[1])) < 500000:
                warn.append("This origin is close to the Facility's own levels. Use a far one (1,000,000 or more).")
            for k, o in enumerate(worlds):
                if k == i or o.raw:
                    continue
                d = math.dist(w.origin, o.origin)
                other = o.id or "another world"
                if d < 1:
                    err.append(f"Same origin as '{other}': the two worlds would load on top of each other.")
                elif d < 100000:
                    warn.append(f"Only {d:,.0f} units from '{other}'. Worlds bigger than that would overlap.")
        out.append((err, warn))
    return out


def next_origin(worlds, skip=None):
    best = None
    for w in worlds:
        if w.raw or w is skip:
            continue
        if best is None or w.origin[0] > best[0]:
            best = w.origin
    return [1000000.0, 1200000.0, 0.0] if best is None else [best[0] + 200000.0, best[1], 0.0]


# ------------------------------------------------------------------ the app
class App:
    def __init__(self, root, path, install=None, gate=False):
        """install: the install check's report (None = not checked). gate: refuse to save while the hub isn't installed
        (off when the config was named with --config)."""
        self.root = root
        self.path = path
        self.install = install
        self.gate = gate
        self.images = {}
        self.guard = False
        self.sel = "A-3"
        self.tab = "room"
        self.world_i = -1
        self.cards = {}
        self.status_kind = "info"
        self.saved_note = ""
        self.load()
        self.build()
        self.refresh_all()

    def load(self):
        self.cfg = HubConfig(self.path)
        self.mhe_path = os.path.join(os.path.dirname(os.path.abspath(self.path)), "manual_exits.lua")
        self.mhe_spots, self.mhe_failsafe, self.mhe_problem = read_manual_exits(self.mhe_path)
        self.hum_vals = {"dynamic": self.cfg.hum_floor, "manual": self.cfg.hum_manual}
        self.world_i = 0 if self.cfg.worlds else -1

    # ------------- building
    def build(self):
        r = self.root
        r.configure(bg=T["bg"])
        self.stripe(r).pack(fill="x")
        head = tk.Frame(r, bg=T["head"], padx=px(18), pady=px(10))
        head.pack(fill="x")
        tk.Label(head, text="PORTAL HUB", bg=T["head"], fg=T["head_fg"], font=font(20, True)).pack(side="left")
        tk.Label(head, text="   CORDONA CORPORATIONS  //  portal room assignments", bg=T["head"], fg=T["head_dim"], font=font(10)).pack(side="left", pady=(px(8), 0))
        self.path_label = tk.Label(head, bg=T["head"], fg=T["head_dim"], font=font(9), cursor="hand2")
        self.path_label.pack(side="right", pady=(px(8), 0))
        self.path_label.bind("<Button-1>", lambda e: self.choose_file())
        Tip(self.path_label, "The config.lua being edited. Click to pick a different one.")
        self.install_bar = InstallBar(r, self.recheck, self.pick_game)
        self.install_bar.pack(fill="x", padx=px(16), pady=(px(2), 0))

        tabs = tk.Frame(r, bg=T["bg"], padx=px(16))
        tabs.pack(fill="x", pady=(px(8), 0))
        self.tab_btns = {}
        for key, text in (("room", "PORTAL ROOM"), ("exits", "HUB EXITS"), ("worlds", "CUSTOM WORLDS")):
            w = tk.Label(tabs, text=text, font=font(10, True), padx=px(14), pady=px(6), cursor="hand2")
            w.pack(side="left")
            w.bind("<Button-1>", lambda e, k=key: self.show_tab(k))
            self.tab_btns[key] = w

        self.page_host = tk.Frame(r, bg=T["chassis"])
        self.page_host.pack(fill="both", expand=True, padx=px(16))
        self.room = tk.Frame(self.page_host, bg=T["chassis"], padx=px(14), pady=px(12))
        self.worlds_page = tk.Frame(self.page_host, bg=T["chassis"], padx=px(14), pady=px(12))
        self.exits_page = tk.Frame(self.page_host, bg=T["chassis"], padx=px(14), pady=px(12))
        self.build_board()
        self.build_inspector()
        self.build_hub_exits()
        self.build_worlds()
        self.build_footer()
        self.show_tab("room")

    def stripe(self, parent):
        h = px(7)
        c = tk.Canvas(parent, height=h, highlightthickness=0, bg=T["stripe_bg"])
        for x in range(-px(20), 4000, px(22)):
            c.create_polygon(x, h, x + h, 0, x + h + px(11), 0, x + px(11), h, fill=T["stripe"], outline="")
        return c

    def build_board(self):
        board = tk.Frame(self.room, bg=T["chassis"])
        board.pack(side="left", anchor="n")
        for r, row in enumerate(hd.ROWS):
            lab = tk.Label(board, text=row, bg=T["chassis"], fg=T["dim"], font=font(16, True), width=2)
            lab.grid(row=r, column=0)
            Tip(lab, {"A": "Top level of the portal room.", "B": "Middle level.", "C": "Bottom level."}[row])
            for col in range(4):
                slot = f"{row}-{col + 1}"
                c = tk.Canvas(board, width=px(CARD_W), height=px(148), highlightthickness=0, bg=T["chassis"], cursor="hand2")
                c.grid(row=r, column=col + 1, padx=px(4), pady=px(4))
                c.bind("<Button-1>", lambda e, s=slot: self.select(s))
                self.cards[slot] = c

    def section(self, parent, text, tip=None):
        w = tk.Label(parent, text=text, bg=T["panel"], fg=T["dim"], font=font(8, True), anchor="w")
        w.pack(fill="x", pady=(px(9), px(2)))
        if tip:
            Tip(w, tip)
        return w

    def build_inspector(self):
        side = tk.Frame(self.room, bg=T["panel"], padx=px(14), pady=px(12), highlightthickness=1, highlightbackground=T["line"], width=px(470))
        side.pack(side="left", fill="both", expand=True, padx=(px(12), 0))
        side.pack_propagate(False)
        self.side = side
        top = tk.Frame(side, bg=T["panel"])
        top.pack(fill="x")
        self.slot_title = tk.Label(top, bg=T["panel"], fg=T["fg"], font=font(15, True))
        self.slot_title.pack(side="left")
        self.on_btn = tk.Label(top, font=font(9, True), padx=px(8), pady=px(2), cursor="hand2")
        self.on_btn.pack(side="right")
        self.on_btn.bind("<Button-1>", lambda e: self.toggle_slot())
        Tip(self.on_btn, "Turn on to put a portal in this slot. Slots turned off stay empty.")

        self.locked_note = tk.Label(side, bg=T["panel"], fg=T["dim"], font=font(10), justify="left", anchor="w", wraplength=px(430))
        self.form = tk.Frame(side, bg=T["panel"])
        f = self.form
        self.section(f, "DESTINATION", "The arrival pad the portal sends players to (its MyTeleporterID). Must match exactly. "
                                       "Pick a world from the list, or choose Custom Destination at the bottom to type any pad ID (not the two DLC areas).")
        self.dest = Drop(f, self.dest_items, self.pick_dest)
        self.dest.pack(fill="x")
        self.pad_row = tk.Frame(f, bg=T["panel"])
        tk.Label(self.pad_row, text="PAD ID ", bg=T["panel"], fg=T["dim"], font=font(8, True)).pack(side="left")
        self.pad_var = tk.StringVar()
        self.pad = Field(self.pad_row, self.pad_var, on_change=self.pad_typed)
        self.pad.pack(side="left", fill="x", expand=True)
        self.section(f, "NAME", "Optional label. Only shown in the mod's log; it does not need to match anything in the game.")
        self.name_var = tk.StringVar()
        self.name = Field(f, self.name_var, on_change=self.name_typed)
        self.name.pack(fill="x")
        self.section(f, "PORTAL LOOK", "The base look of the portal (its particle effect). Purely visual.")
        row = tk.Frame(f, bg=T["panel"])
        row.pack(fill="x")
        self.look = Drop(row, self.look_items, self.pick_look)
        self.look.pack(side="left", fill="x", expand=True)
        self.fx = Btn(row, "EFFECTS", self.open_effects)
        self.fx.pack(side="left", padx=(px(6), 0))
        Tip(self.fx, "Switch parts of this look on or off (for example the accretion disk of SnowFlurry). Applies to every portal that uses the look.")
        self.section(f, "PAD LIGHT", "The colour of the pad's own light: a rainbow preset, or ... for any colour. It tints the surroundings and works "
                                     "with every look. The first box leaves it alone. The number is its brightness: 1.0 = the game's normal brightness, 2.0 = twice as bright, 0.5 = half.")
        sw = tk.Frame(f, bg=T["panel"])
        sw.pack(fill="x")
        self.swatches = {}
        for label, hexv in [("Default", "")] + hd.LIGHT_PRESETS:
            w = tk.Label(sw, text="-" if not hexv else "", bg=hexv or T["crt"], fg=T["crt_fg"], width=2, font=font(9), highlightthickness=2, cursor="hand2")
            w.pack(side="left", padx=(0, px(3)))
            w.bind("<Button-1>", lambda e, h=hexv: self.pick_light(h))
            Tip(w, label)
            self.swatches[hexv] = w
        self.custom_sw = tk.Label(sw, text="...", bg=T["panel"], fg=T["fg"], width=3, font=font(9, True), highlightthickness=2, cursor="hand2")
        self.custom_sw.pack(side="left")
        self.custom_sw.bind("<Button-1>", lambda e: self.pick_custom_light())
        Tip(self.custom_sw, "Any colour")
        self.bright = Stepper(sw, 0.1, 20, 0.1, 1, self.bright_set, T["panel"])
        self.bright.pack(side="right")

        head = tk.Frame(f, bg=T["panel"])
        head.pack(fill="x", pady=(px(9), px(2)))
        lab = tk.Label(head, text="EXIT MODE", bg=T["panel"], fg=T["dim"], font=font(8, True))
        lab.pack(side="left")
        Tip(lab, "What the world's own exits do for players of this portal (exits in config.lua). Picking a world sets M.H.E.; "
                 "a portal with no mode in config.lua shows GAME. Custom worlds always lead back to the hub, so they have no mode.")
        self.buff_btn = Btn(head, "", self.toggle_manual_buffs, small=True)
        self.buff_btn.pack(side="right")
        Tip(self.buff_btn, "manualBuffs, M.H.E. only: the Manual Hub Exit also gives the buffs of the world's true exit. "
                           "Off by default: it makes the game much easier.")
        self.exit_seg = Segmented(f, hd.EXIT_PICKER, self.pick_exit, T["panel"])
        self.exit_seg.pack(anchor="w")
        for m, w in self.exit_seg.labels.items():
            Tip(w, hd.EXIT_MODE_HELP[m])
        self.exit_note = tk.Label(f, bg=T["panel"], fg=T["dim"], font=font(9), anchor="w", justify="left", wraplength=px(430))
        self.exit_note.pack(fill="x", pady=(px(4), 0))

    def build_hub_exits(self):
        p = self.exits_page
        box = tk.Frame(p, bg=T["panel"], padx=px(14), pady=px(10), highlightthickness=1, highlightbackground=T["line"])
        box.pack(fill="both", expand=True)
        lab = tk.Label(box, text="MANUAL HUB EXITS (MHE)", bg=T["panel"], fg=T["dim"], font=font(8, True), anchor="w")
        lab.pack(fill="x")
        Tip(lab, "Spots are recorded in manual_exits.lua next to config.lua (read only here). Switching one off writes mhe = { [pad] = false } into config.lua.")
        tk.Label(box, text="An MHE is an exit portal placed inside a base-game world that leads back to the hub: to the first hub portal to that "
                           "world, or with none, to the Failsafe Exit in the portal room. Every recorded MHE is on unless you switch it off here, "
                           "with or without a hub portal to its world.", bg=T["panel"], fg=T["fg"], font=font(9), anchor="w", justify="left",
                 wraplength=px(1100)).pack(fill="x", pady=(px(2), px(6)))
        self.mhe_note = tk.Label(box, bg=T["panel"], fg=T["warn"], font=font(9, True), anchor="w", justify="left", wraplength=px(1100))
        host = tk.Frame(box, bg=T["crt"], highlightthickness=1, highlightbackground=T["crt_edge"])
        host.pack(fill="both", expand=True)
        self.mhe_list = Scrolled(host, T["crt"])
        self.mhe_list.pack(fill="both", expand=True)
        self.failsafe_note = tk.Label(box, bg=T["panel"], fg=T["dim"], font=font(9), anchor="w", justify="left")
        self.failsafe_note.pack(fill="x", pady=(px(6), 0))

    def build_worlds(self):
        p = self.worlds_page
        tk.Label(p, text="Connect a world that ships its own pak. Each world gets an ID; a hub portal uses that ID as its destination.",
                 bg=T["chassis"], fg=T["dim"], font=font(10), anchor="w").pack(fill="x", pady=(0, px(8)))
        self.worlds_locked = tk.Label(p, text="The worlds section of config.lua uses a layout this editor can't read, so it is left exactly as written. Edit it in config.lua.",
                                      bg=T["chassis"], fg=T["fg"], font=font(10), anchor="w", justify="left", wraplength=px(900))
        self.worlds_main = tk.Frame(p, bg=T["chassis"])
        self.worlds_main.pack(fill="both", expand=True)
        left = tk.Frame(self.worlds_main, bg=T["chassis"], width=px(250))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        host = tk.Frame(left, bg=T["crt"], highlightthickness=1, highlightbackground=T["crt_edge"])
        host.pack(fill="both", expand=True)
        self.world_list = Scrolled(host, T["crt"])
        self.world_list.pack(fill="both", expand=True)
        row = tk.Frame(left, bg=T["chassis"])
        row.pack(fill="x", pady=(px(8), 0))
        Btn(row, "ADD WORLD", self.add_world, primary=True).pack(side="left", fill="x", expand=True)
        self.del_btn = Btn(row, "REMOVE", self.remove_world)
        self.del_btn.pack(side="left", fill="x", expand=True, padx=(px(6), 0))

        right = tk.Frame(self.worlds_main, bg=T["panel"], padx=px(14), pady=px(10), highlightthickness=1, highlightbackground=T["line"])
        right.pack(side="left", fill="both", expand=True, padx=(px(12), 0))
        self.world_form = right

        def cap(text, hint=None):
            w = tk.Label(right, text=text, bg=T["panel"], fg=T["dim"], font=font(8, True), anchor="w")
            w.pack(fill="x", pady=(px(8), px(2)))
            if hint:
                Tip(w, hint)

        self.w_vars = {k: tk.StringVar() for k in ("id", "asset", "cls", "level")}
        cap("WORLD ID", "You choose this. A hub portal's destination must be exactly this text. Letters, numbers, _ and - only.")
        self.w_id = Field(right, self.w_vars["id"], on_change=self.world_edited)
        self.w_id.pack(fill="x")
        cap("LOADER BLUEPRINT (PACKAGE PATH)", "The Blueprint in your pak that streams your map in, e.g. /Game/Mods/MyWorld/BP_MyWorldLoader")
        self.w_asset = Field(right, self.w_vars["asset"], on_change=self.asset_edited)
        self.w_asset.pack(fill="x")
        cap("LOADER CLASS", "Filled in for you: the Blueprint's name plus _C.")
        self.w_cls = Field(right, self.w_vars["cls"], on_change=self.class_edited)
        self.w_cls.pack(fill="x")
        cap("LEVEL (MAP PACKAGE PATH)", "Your map, e.g. /Game/Mods/MyWorld/Maps/MyWorld_L0. Used to tell when the level has finished loading.")
        self.w_level = Field(right, self.w_vars["level"], on_change=self.world_edited)
        self.w_level.pack(fill="x")
        cap("ORIGIN  (X, Y, Z)", "Where the world is loaded. Keep it far from the Facility, and different for every world.")
        row = tk.Frame(right, bg=T["panel"])
        row.pack(fill="x")
        self.w_nums = []
        for _ in range(3):
            n = Field(row, width=11, justify="center", on_change=self.world_edited)
            n.pack(side="left", padx=(0, px(6)))
            self.w_nums.append(n)
        self.suggest = Btn(row, "SUGGEST", self.suggest_origin, small=True)
        self.suggest.pack(side="left")
        cap("ARRIVAL PAD  (X, Y, FLOOR Z, YAW)  OPTIONAL", "The pad players arrive at and return through, relative to the origin. Leave all four blank "
                                                           "to leave it out: the loader Blueprint's ArriveSpot is used if it has one, else 0, 0, 0, 0.")
        row = tk.Frame(right, bg=T["panel"])
        row.pack(fill="x")
        for _ in range(4):
            n = Field(row, width=11, justify="center", on_change=self.world_edited)
            n.pack(side="left", padx=(0, px(6)))
            self.w_nums.append(n)
        self.w_inputs = [self.w_id, self.w_asset, self.w_cls, self.w_level] + self.w_nums
        self.w_extras = tk.Label(right, bg=T["panel"], fg=T["dim"], font=font(9), anchor="w", justify="left", wraplength=px(640))
        self.w_extras.pack(fill="x", pady=(px(8), 0))
        self.w_msg = tk.Label(right, bg=T["panel"], fg=T["dim"], font=font(10, True), anchor="w", justify="left", wraplength=px(640))
        self.w_msg.pack(fill="x", pady=(px(4), 0))
        self.w_empty = tk.Label(self.worlds_main, text="No custom worlds yet.\n\nClick ADD WORLD to connect a world from your own pak.\n"
                                                       "The test-world walkthrough shows how to build one: docs/test-world-walkthrough.html",
                                bg=T["panel"], fg=T["dim"], font=font(10), justify="left", padx=px(20), pady=px(20),
                                highlightthickness=1, highlightbackground=T["line"], anchor="nw")

    def build_footer(self):
        foot = tk.Frame(self.root, bg=T["bg"], padx=px(16), pady=px(8))
        foot.pack(fill="x")
        row = tk.Frame(foot, bg=T["bg"])
        row.pack(fill="x")
        lab = tk.Label(row, text="PORTAL HUM", bg=T["bg"], fg=T["fg"], font=font(9, True))
        lab.pack(side="left", padx=(0, px(6)))
        Tip(lab, "The looping hum of the portals in the portal room.")
        self.hum_seg = Segmented(row, (("DYNAMIC", "dynamic"), ("MANUAL", "manual"), ("GAME DEFAULT", "default")), self.set_hum_mode, T["bg"])
        self.hum_seg.pack(side="left")
        self.hum_step = Stepper(row, 0, 100, 1, 0, self.hum_changed, T["bg"])
        self.hum_step.pack(side="left", padx=(px(10), 0))
        self.hum_unit = tk.Label(row, text="%", bg=T["bg"], fg=T["fg"], font=font(10, True))
        self.hum_unit.pack(side="left", padx=(px(4), 0))
        self.hum_hint = tk.Label(row, bg=T["bg"], fg=T["fg"], font=font(8), anchor="w", justify="left")
        self.hum_hint.pack(side="left", padx=(px(10), 0))
        self.save_btn = Btn(row, "SAVE TO CONFIG", self.save, primary=True)
        self.save_btn.pack(side="right")
        b = Btn(row, "OPEN FOLDER", self.open_folder)
        b.pack(side="right", padx=px(6))
        Btn(row, "RELOAD", self.reload).pack(side="right")
        self.status = tk.Label(foot, bg=T["bg"], fg=T["fg"], font=font(9, True), anchor="w", justify="left")
        self.status.pack(fill="x", pady=(px(5), 0))
        foot.bind("<Configure>", lambda e: self.status.configure(wraplength=e.width - px(30)))

    # ------------- slot cards
    def icon_for(self, dest):
        known = hd.KNOWN_BY_ID.get(dest)
        if not known:
            return None
        slug = known[3]
        if slug not in self.images:
            img = None
            path = os.path.join(ICON_DIR, slug + ".png")
            if os.path.exists(path):
                try:
                    img = scaled_image(self.root, path, px(64), T["card"])
                except tk.TclError:
                    img = None
            self.images[slug] = img
        return self.images[slug]

    def portal(self, slot):
        p = self.cfg.portals.get(slot)
        return p if p is not None and p.enabled else None

    def world_title(self, dest):
        known = hd.KNOWN_BY_ID.get(dest)
        return known[2] if known else dest

    def draw_card(self, slot):
        c = self.cards[slot]
        c.delete("all")
        W, H = px(CARD_W), px(148)
        selected = slot == self.sel and self.tab == "room"
        if slot in hd.LOCKED_SLOTS:
            c.create_rectangle(0, 0, W - 1, H - 1, fill=T["slot_off"], outline=T["accent"] if selected else T["line"], width=3 if selected else 1)
            for x in range(-H, W, px(14)):
                c.create_line(x, H, x + H, 0, fill=T["line"])
            c.create_rectangle(px(10), px(8), px(62), px(30), fill=T["slot_off"], outline="")
            c.create_text(px(14), px(19), text=slot, anchor="w", fill=T["dim"], font=font(13, True))
            if slot in hd.NO_ENTRY_SLOTS:
                if "no-symbol" not in self.images:
                    self.images["no-symbol"] = no_symbol_image(self.root, px(64))
                c.create_image(W / 2, px(66), image=self.images["no-symbol"])
            c.create_rectangle(px(10), px(104), W - px(10), px(138), fill=T["slot_off"], outline="")
            c.create_text(W / 2, px(113), text=hd.LOCKED_SLOTS[slot][0], fill=T["dim"], font=font(10, True))
            c.create_text(W / 2, px(128), text="GAME PORTAL", fill=T["dim"], font=font(8))
            return
        p = self.portal(slot)
        if p is None:
            c.create_rectangle(1, 1, W - 2, H - 2, fill=T["slot_off"], outline=T["accent"] if selected else T["line"], dash=() if selected else (4, 4), width=3 if selected else 1)
            c.create_text(px(14), px(19), text=slot, anchor="w", fill=T["dim"], font=font(13, True))
            c.create_text(W / 2, px(84), text="+ assign", fill=T["dim"], font=font(10))
            return
        c.create_rectangle(0, 0, W - 1, H - 1, fill=T["card"], outline="")
        for y in range(px(3), H - 1, px(3)):               # CRT scan lines
            c.create_line(1, y, W - 1, y, fill=T["crt_line"])
        bad = self.dest_problem(p)
        c.create_rectangle(1, 1, W - 2, H - 2, outline=T["crt_bad"] if bad else T["accent"] if selected else T["crt_edge"], width=3 if selected or bad else 1)
        c.create_text(px(14), px(19), text=slot, anchor="w", fill=T["crt_fg"], font=font(13, True))
        c.create_oval(W - px(22), px(13), W - px(12), px(23), fill=T["crt_bad"] if bad else T["crt_good"], outline="")
        img = self.icon_for(p.destination)
        if img is not None:
            c.create_image(W / 2, px(66), image=img)
        else:
            tint = hd.LOOK_TINTS.get(hd.design_name(p.design), T["crt_fg"])
            r = px(29)
            x, y = W / 2, px(66)
            c.create_oval(x - r, y - r, x + r, y + r, outline=tint, width=3)
            c.create_oval(x - r + px(6), y - r + px(6), x + r - px(6), y + r - px(6), outline=tint, dash=(3, 3))
            words = re.sub(r"^The ", "", p.name or self.world_title(p.destination) or "?").split()
            code = (words[0][0] + words[1][0] if len(words) > 1 else words[0][:2]).upper() if words else "?"
            c.create_text(x, y, text=code, fill=tint, font=font(13, True))
        name = p.name or self.world_title(p.destination) or "no destination"
        room = W - px(12)
        shown, size = fit_text(c, name, room, 10, True)
        c.create_text(W / 2, px(116), text=shown, fill=T["crt_fg"], font=font(size, True))
        shown, size = fit_text(c, p.destination or "pick a world", room, 8, False)
        c.create_text(W / 2, px(132), text=shown, fill=T["crt_dim"], font=font(size))

    def dest_problem(self, p):
        d = p.destination.strip()
        if not PAD_ID_RX.match(d):
            return "no valid destination pad ID (letters, numbers, _ and - only)"
        if hd.is_dlc(d):
            return "a DLC area (Stone Garden or Torii) as its destination, which isn't allowed"
        if hd.is_reserved(d):
            return "one of the hub's own pads (hub_...) as its destination, which isn't allowed"
        return ""

    # ------------- selection and the side panel
    def select(self, slot):
        self.commit_focus()
        old, self.sel = self.sel, slot
        self.draw_card(old)
        self.draw_card(slot)
        self.refresh_inspector()

    def commit_focus(self):
        self.root.focus_set()

    def refresh_inspector(self):
        self.guard = True
        slot = self.sel
        self.slot_title.configure(text="SLOT " + slot)
        locked = hd.LOCKED_SLOTS.get(slot)
        self.locked_note.pack_forget()
        self.form.pack_forget()
        if locked:
            self.on_btn.configure(text=" LOCKED ", bg=T["panel"], fg=T["dim"])
            self.locked_note.configure(text=f"Game portal: {locked[0]}\nDestination: {locked[1]}\n\nFixed by the game, so this slot can't be changed.")
            self.locked_note.pack(fill="x", pady=(px(14), 0))
            self.guard = False
            return
        p = self.portal(slot)
        on = p is not None
        self.on_btn.configure(text=" ON " if on else " OFF ", bg=T["accent"] if on else T["crt"], fg=T["on_accent"] if on else T["crt_dim"])
        self.form.pack(fill="both", expand=True)
        p = p or self.cfg.portals.get(slot) or Portal(slot=slot, enabled=False)
        self.dest.set_enabled(True)
        self.show_dest(p)
        self.name_var.set(p.name)
        self.name.set_enabled(on)
        self.show_look(p)
        self.look.set_enabled(on)
        self.fx.set_enabled(on)
        self.bright.set(p.brightness)
        self.bright.set_enabled(on)
        self.show_light(p)
        self.guard = False
        self.show_exits(p if on else None)

    def show_dest(self, p):
        d = p.destination
        known = hd.KNOWN_BY_ID.get(d)
        custom_world = any(w.id == d for w in self.cfg.worlds)
        self.pad_row.pack_forget()
        if known:
            self.dest.show(f"{known[2]}   {d}", d)
        elif custom_world:
            self.dest.show(f"{d}   custom world", d)
        elif d or getattr(p, "typing", False):
            self.dest.show("Custom Destination", "__custom__")
            self.pad_var.set(d)
            self.pad_row.pack(fill="x", pady=(px(4), 0), after=self.dest)
        else:
            self.dest.show("Pick a world", None)
        bad = self.portal(p.slot) is not None and bool(self.dest_problem(p))
        self.dest.set_bad(bad)
        self.pad.set_bad(bad)

    def show_look(self, p):
        label = next((l for l, path in hd.DESIGNS if path == p.design), "Custom: " + p.design)
        self.look.show(label, p.design)
        n = len(self.cfg.hide.get(p.design, []))
        self.fx.configure(text=f"EFFECTS ({n} OFF)" if n else "EFFECTS")

    def show_light(self, p):
        hexv = p.light_hex.upper()
        preset = hexv in self.swatches
        for h, w in self.swatches.items():
            w.configure(highlightbackground=T["accent"] if h == hexv else T["line"], highlightcolor=T["accent"])
        if preset:
            self.custom_sw.configure(bg=T["panel"], fg=T["fg"], highlightbackground=T["line"])
        else:
            self.custom_sw.configure(bg=hexv, fg=T["on_accent"], highlightbackground=T["accent"])

    def active(self):
        return self.portal(self.sel)

    def toggle_slot(self):
        slot = self.sel
        if slot in hd.LOCKED_SLOTS:
            return
        p = self.cfg.portals.get(slot)
        if p is None:
            self.cfg.portals[slot] = Portal(slot=slot)
        elif p.enabled:
            self.cfg.wipe_portal(slot)          # off = wiped: world, exit mode, look and light all go (author's ruling)
        else:
            p.enabled = True
        self.changed(slot, inspector=True)

    def ensure_on(self):
        p = self.cfg.portals.get(self.sel)
        if p is None:
            p = self.cfg.portals[self.sel] = Portal(slot=self.sel)
        p.enabled = True
        return p

    def dest_items(self):
        items, group = [], None
        for g, pid, world, _icon, _look in hd.DESTINATIONS:
            if g != group:
                items.append((g, None, None))
                group = g
            items.append((world, pid, pid))
        mine = [w.id for w in self.cfg.worlds if w.id]
        if mine:
            items.append(("Your worlds", None, None))
            items += [(w, "custom world", w) for w in mine]
        items.append(("Custom", None, None))
        items.append(("Custom Destination", "type the pad ID of your own world", "__custom__"))
        return items

    def pick_dest(self, value):
        p = self.ensure_on()
        if value == "__custom__":
            p.destination = ""
            p.name = ""
            p.typing = True
            self.changed(p.slot, inspector=True)
            self.pad.entry.focus_set()
            return
        p.destination = value
        p.typing = False
        if any(w.id == value for w in self.cfg.worlds):     # custom worlds always return to the hub: no exit mode
            p.exits, p.manual_buffs = "", False
        else:                                               # every base-game world pick starts at M.H.E. (CRD-034)
            p.exits = hd.PICK_EXIT_MODE
        known = hd.KNOWN_BY_ID.get(value)
        if known:                       # a world brings its name and the look the game uses for it
            p.name = known[2]
            p.design = hd.design_path(known[4])
        else:
            p.name = value
        self.changed(p.slot, inspector=True)

    def pad_typed(self):
        if self.guard or not self.active():
            return
        self.active().destination = self.pad_var.get().strip()
        self.active().typing = True
        p = self.active()
        if self.is_custom_world(p.destination):
            p.exits, p.manual_buffs = "", False
        elif p.destination and not p.exits:                 # a typed pad with no mode yet: GAME, as a portal with no exits
            p.exits = hd.DEFAULT_EXIT_MODE
        bad = bool(self.dest_problem(p))
        self.dest.set_bad(bad)
        self.pad.set_bad(bad)
        self.show_exits(p)
        self.changed(p.slot)

    def name_typed(self):
        if not self.guard and self.active():
            self.active().name = self.name_var.get()
            self.changed(self.sel)

    def look_items(self):
        items = [(label, None, path) for label, path in hd.DESIGNS]
        p = self.active()
        if p and not any(path == p.design for _, path in hd.DESIGNS):
            items.append(("Custom: " + p.design, None, p.design))       # a path from a hand-edited config: keep it
        return items

    def pick_look(self, path):
        p = self.active()
        p.design = path
        self.changed(p.slot, inspector=True)

    def open_effects(self):
        p = self.active()
        if not p:
            return
        label = next((l for l, path in hd.DESIGNS if path == p.design), p.design)
        if not hd.DESIGN_PARTS.get(hd.design_name(p.design)):
            ask(self.root, "Effects", "No named parts were found for this look.", [("OK", 1)])
            return
        if EffectsDialog(self.root, self, p.design, label).present():
            self.changed(p.slot, inspector=True)

    def pick_light(self, hexv):
        p = self.active()
        if p:
            p.light_hex = hexv
            self.show_light(p)
            self.changed(p.slot)

    def pick_custom_light(self):
        p = self.active()
        if not p:
            return
        _, hexv = colorchooser.askcolor(color=p.light_hex or None, parent=self.root, title="Pad light colour")
        if hexv:
            self.pick_light(hexv.upper())

    def bright_set(self, v):
        if not self.guard and self.active():
            self.active().brightness = v
            self.changed(self.sel)

    # ------------- exit modes (side panel)
    def is_custom_world(self, dest):
        return any(w.id == dest for w in self.cfg.worlds)

    def show_exits(self, p):
        dest = p.destination.strip() if p else ""
        custom = bool(p) and self.is_custom_world(dest)
        self.exit_seg.set_enabled(bool(p) and bool(dest) and not custom)
        self.exit_seg.set(p.exits if p and dest and not custom else "")
        manual = bool(p) and p.exits == "manual" and not custom
        self.buff_btn.configure(text="BUFFS ON" if p and p.manual_buffs else "BUFFS OFF")
        self.buff_btn.set_enabled(manual)
        warn = False
        if not p:
            text = "Turn the slot on first."
        elif custom:
            text = "A custom world always leads back to the hub through its arrival pad, so it has no exit mode."
        elif not dest:
            text = "Pick a world first."
        elif not p.exits:
            text = hd.EXIT_MODE_HELP[hd.DEFAULT_EXIT_MODE]
        else:
            text = hd.EXIT_MODE_HELP[p.exits]
            if manual and dest and dest not in self.mhe_spots:
                text += f"\nNo MHE is recorded for {self.world_title(dest)} yet (manual_exits.lua), so the hub uses GAME for this portal."
                warn = True
        self.exit_note.configure(text=text, fg=T["warn"] if warn else T["dim"])

    def pick_exit(self, mode):
        p = self.active()
        if not p:
            return
        p.exits = mode
        if mode != "manual":
            p.manual_buffs = False              # only read with M.H.E.: no leftover in the file
        self.show_exits(p)
        self.changed(p.slot)

    def toggle_manual_buffs(self):
        p = self.active()
        if p and p.exits == "manual":
            p.manual_buffs = not p.manual_buffs
            self.show_exits(p)
            self.changed(p.slot)

    # ------------- hub exits tab
    def mhe_rows(self):
        """(title, pad id) for every base-game world in the list, then any other world manual_exits.lua or mhe names."""
        rows = [(d[2], d[1]) for d in hd.DESTINATIONS]
        seen = {pad for _, pad in rows}
        for pad in sorted(set(self.mhe_spots) | self.cfg.mhe_off):
            if pad not in seen and not self.is_custom_world(pad):
                rows.append((hd.home_title(pad) or pad, pad))
                seen.add(pad)
        return rows

    def mhe_status(self, pad):
        """What the MHE of a world does now, in words."""
        if pad not in self.mhe_spots:
            return "no MHE recorded yet"
        if pad in self.cfg.mhe_off:
            return "switched off"
        portals = [self.portal(s) for s in hd.SLOT_IDS if self.portal(s) and self.portal(s).destination.strip() == pad]
        manual = [q.slot for q in portals if q.exits == "manual"]
        others = [q.slot for q in portals if q.exits != "manual"]
        if manual:
            return f"used by the M.H.E. portal in {manual[0]}"
        if others:
            return f"leads to hub portal {others[0]}"
        if hd.home_title(pad):
            return "leads to its home's own portal"
        return "leads to the Failsafe Exit (no hub portal to this world)"

    def toggle_mhe(self, pad):
        if not self.cfg.mhe_editable:
            return
        if pad in self.cfg.mhe_off:
            self.cfg.mhe_off.discard(pad)
        elif pad in self.mhe_spots:
            self.cfg.mhe_off.add(pad)
        self.refresh_hub_exits()
        self.update_state()

    def refresh_hub_exits(self):
        notes = []
        if self.mhe_problem:
            notes.append(self.mhe_problem + ".")
        if not self.cfg.mhe_editable:
            notes.append("The mhe section of config.lua uses a layout this editor can't read, so it is left exactly as written. Edit it in config.lua.")
        self.mhe_note.pack_forget()
        if notes:
            self.mhe_note.configure(text="  ".join(notes))
            self.mhe_note.pack(fill="x", pady=(0, px(6)), before=self.mhe_list.master)
        host = self.mhe_list.inner
        for child in host.winfo_children():
            child.destroy()
        for title, pad in self.mhe_rows():
            recorded = pad in self.mhe_spots
            off = pad in self.cfg.mhe_off
            row = tk.Frame(host, bg=T["crt"], padx=px(8), pady=px(3))
            row.pack(fill="x")
            if recorded or off:
                on = recorded and not off
                sw = tk.Label(row, text=" ON " if on else " OFF ", width=5, font=font(9, True),
                              bg=T["accent"] if on else T["crt_hi"], fg=T["on_accent"] if on else T["crt_dim"],
                              cursor="hand2" if self.cfg.mhe_editable else "arrow")
                sw.bind("<Button-1>", lambda e, k=pad: self.toggle_mhe(k))
            else:
                sw = tk.Label(row, text=" -- ", width=5, font=font(9, True), bg=T["crt"], fg=T["line"])
            sw.pack(side="left", padx=(0, px(10)))
            name = tk.Label(row, text=title, bg=T["crt"], fg=T["crt_fg"] if recorded else T["crt_dim"], font=font(10), anchor="w", width=28)
            name.pack(side="left")
            tk.Label(row, text=pad, bg=T["crt"], fg=T["crt_dim"], font=font(9), anchor="w", width=24).pack(side="left")
            status = self.mhe_status(pad)
            col = T["crt_good"] if recorded and not off else T["crt_dim"]
            tk.Label(row, text=status, bg=T["crt"], fg=col, font=font(9), anchor="w").pack(side="left", fill="x", expand=True)
            for w in [row] + list(row.winfo_children()):
                self.mhe_list.bind_wheel(w)
        if self.mhe_failsafe:
            x, y, z, yaw = self.mhe_failsafe
            self.failsafe_note.configure(text=f"Failsafe Exit: recorded at {fmt_num(x)}, {fmt_num(y)}, {fmt_num(z)} facing {fmt_num(yaw)} (manual_exits.lua).")
        else:
            self.failsafe_note.configure(text="Failsafe Exit: not recorded in manual_exits.lua.")

    # ------------- custom worlds tab
    def world_rows(self):
        host = self.world_list.inner
        for child in host.winfo_children():
            child.destroy()
        problems = world_problems(self.cfg.worlds)
        for i, w in enumerate(self.cfg.worlds):
            hot = i == self.world_i
            bg = T["accent"] if hot else T["crt"]
            row = tk.Frame(host, bg=bg, cursor="hand2", padx=px(8), pady=px(4))
            row.pack(fill="x")
            err, warn = problems[i]
            col = T["crt_dim"] if w.raw else T["crt_bad"] if err else T["warn"] if warn else T["crt_good"]
            dot = tk.Label(row, text="●", bg=bg, fg=col, font=font(9))
            dot.pack(side="left", padx=(0, px(6)))
            txt = tk.Frame(row, bg=bg)
            txt.pack(side="left", fill="x", expand=True)
            sub = "kept as written" if w.raw else w.level.rsplit("/", 1)[-1] if w.level else "not finished"
            a = tk.Label(txt, text=w.id or "(new world)", bg=bg, fg=T["on_accent"] if hot else T["crt_fg"], font=font(10), anchor="w")
            b = tk.Label(txt, text=sub, bg=bg, fg=T["on_accent"] if hot else T["crt_dim"], font=font(8), anchor="w")
            a.pack(fill="x")
            b.pack(fill="x")
            for widget in (row, dot, txt, a, b):
                widget.bind("<Button-1>", lambda e, k=i: self.pick_world(k))
                self.world_list.bind_wheel(widget)

    def pick_world(self, i):
        self.commit_focus()
        self.world_i = i
        self.refresh_worlds()

    def current_world(self):
        return self.cfg.worlds[self.world_i] if 0 <= self.world_i < len(self.cfg.worlds) else None

    def refresh_worlds(self):
        n = len(self.cfg.worlds)
        self.tab_btns["worlds"].configure(text=f"CUSTOM WORLDS  {n}" if self.cfg.worlds_editable else "CUSTOM WORLDS  (view)")
        if not self.cfg.worlds_editable:
            self.worlds_main.pack_forget()
            self.worlds_locked.pack(fill="x")
            return
        self.world_rows()
        w = self.current_world()
        self.del_btn.set_enabled(w is not None)
        if w is None:
            self.world_form.pack_forget()
            self.w_empty.pack(side="left", fill="both", expand=True, padx=(px(12), 0))
            return
        self.w_empty.pack_forget()
        self.world_form.pack(side="left", fill="both", expand=True, padx=(px(12), 0))
        self.guard = True
        self.w_vars["id"].set(w.id)
        self.w_vars["asset"].set(w.asset)
        self.w_vars["cls"].set(w.cls)
        self.w_vars["level"].set(w.level)
        for k in range(3):
            self.w_nums[k].var.set(fmt_num(w.origin[k]))
        for k in range(4):
            self.w_nums[3 + k].var.set("" if w.arrive is None else fmt_num(w.arrive[k]))
        for c in self.w_inputs:
            c.set_enabled(not w.raw)
        self.suggest.set_enabled(not w.raw)
        self.guard = False
        self.w_extras.configure(text=("Also set in config.lua, kept as written: " + ", ".join(w.extras)) if w.extras else "")
        self.world_message()

    def world_message(self):
        w = self.current_world()
        if w is None:
            return
        err, warn = world_problems(self.cfg.worlds)[self.world_i]
        if w.raw:
            self.w_msg.configure(fg=T["dim"], text="This entry uses a layout the editor can't read. It is kept exactly as written; edit it in config.lua.")
        elif err:
            self.w_msg.configure(fg=T["bad"], text=err[0])
        elif warn:
            self.w_msg.configure(fg=T["warn"], text=warn[0])
        else:
            self.w_msg.configure(fg=T["good"], text="Looks good.")

    def read_world_form(self):
        w = self.current_world()
        if w is None or w.raw:
            return
        w.id = self.w_vars["id"].get().strip()
        w.asset = self.w_vars["asset"].get().strip()
        w.cls = self.w_vars["cls"].get().strip()
        w.level = self.w_vars["level"].get().strip()
        w.bad = ""
        texts = [n.var.get().strip() for n in self.w_nums]
        try:
            origin = [float(t) for t in texts[:3]]
            if any(texts[3:]):
                arrive = [float(t or 0) for t in texts[3:]]
            else:
                arrive = None
            w.origin, w.arrive = origin, arrive
        except ValueError:
            w.bad = "Origin and arrival values must be numbers."

    def world_edited(self):
        if self.guard:
            return
        self.read_world_form()
        self.world_rows()
        self.world_message()
        self.update_state()

    def class_edited(self):
        if not self.guard and self.current_world():
            self.current_world().class_auto = False
        self.world_edited()

    def asset_edited(self):
        """Typing the Blueprint's path fills in its class (name + _C) until the class is edited by hand."""
        w = self.current_world()
        if self.guard or w is None:
            return
        self.world_edited()
        if not w.cls or w.class_auto:
            seg = w.asset.rsplit("/", 1)[-1]
            self.guard = True
            self.w_vars["cls"].set(seg + "_C" if seg else "")
            self.guard = False
            w.class_auto = bool(seg)
            self.world_edited()

    def suggest_origin(self):
        w = self.current_world()
        if w is None:
            return
        o = next_origin(self.cfg.worlds, w)
        self.guard = True
        for k in range(3):
            self.w_nums[k].var.set(fmt_num(o[k]))
        self.guard = False
        self.world_edited()

    def add_world(self):
        n, new = 1, "myworld_start"
        ids = {w.id.lower() for w in self.cfg.worlds}
        while new in ids:
            n += 1
            new = f"myworld{n}_start"
        self.cfg.worlds.append(World(id=new, origin=next_origin(self.cfg.worlds), class_auto=True))
        self.world_i = len(self.cfg.worlds) - 1
        self.refresh_worlds()
        self.update_state()
        self.w_id.entry.focus_set()
        self.w_id.entry.selection_range(0, "end")

    def remove_world(self):
        w = self.current_world()
        if w is None:
            return
        users = [p.slot for p in self.cfg.portals.values() if p.enabled and p.destination == w.id]
        q = f"Remove the world '{w.id}'?"
        if users:
            q += f"\n\nPortal {', '.join(users)} still leads to it. That portal will have nothing to load until you pick another destination."
        if ask(self.root, "Remove world", q, [("REMOVE", 1), ("CANCEL", 0)]):
            self.cfg.worlds.pop(self.world_i)
            self.world_i = min(self.world_i, len(self.cfg.worlds) - 1)
            self.refresh_worlds()
            self.update_state()

    # ------------- volume
    def set_hum_mode(self, mode):
        self.cfg.hum_mode = mode
        self.hum_seg.set(mode)
        numeric = mode in self.hum_vals
        self.hum_step.pack_forget()
        self.hum_unit.pack_forget()
        if numeric:
            self.hum_step.pack(side="left", padx=(px(10), 0), after=self.hum_seg)
            self.hum_unit.pack(side="left", padx=(px(4), 0), after=self.hum_step)
            self.hum_step.set(self.hum_vals[mode])
        self.hum_hint.configure(text={"dynamic": "Each added portal lowers the hum,\ndown to this lowest volume.",
                                      "manual": "Every hub portal uses this volume.",
                                      "default": "Portal volume is left exactly\nas the game sets it."}[mode])
        self.update_state()

    def hum_changed(self, v):
        mode = self.cfg.hum_mode
        if mode in self.hum_vals:
            self.hum_vals[mode] = int(round(v))
            self.cfg.hum_floor, self.cfg.hum_manual = self.hum_vals["dynamic"], self.hum_vals["manual"]
            self.update_state()

    # ------------- state
    def changed(self, slot, inspector=False):
        self.draw_card(slot)
        if inspector:
            self.refresh_inspector()
        self.update_state()

    def problems(self):
        out = []
        by_kind = {}
        for slot in hd.SLOT_IDS:
            p = self.portal(slot)
            if p and self.dest_problem(p):
                by_kind.setdefault(self.dest_problem(p), []).append(slot)
        for why, slots in by_kind.items():
            verb = ("is enabled but has " if len(slots) == 1 else "are enabled but have ") if why.startswith("no") else ("uses " if len(slots) == 1 else "use ")
            hint = " Enter one, or turn the portal off." if why.startswith("no") else " Pick another destination."
            out.append(f"{', '.join(slots)} {verb}{why}.{hint}")
        problems = world_problems(self.cfg.worlds)
        bad = [w.id or "(new world)" for w, (err, _) in zip(self.cfg.worlds, problems) if err]
        if bad:
            out.append(f"Custom worlds need fixing: {', '.join(bad)}.")
        return out

    def save_blocked(self):
        """Why saving is refused by the install check, or ''. Only when the hub's files are missing; a hub switched off in
        mods.txt or an old UE4SS is a warning only (the config can be edited while the player fixes that)."""
        if self.gate and self.install is not None and not self.install.hub_installed:
            return "Portal Hub isn't installed in the game, so nothing is written. See the install line at the top."
        return ""

    def update_state(self):
        probs = self.problems()
        blocked = self.save_blocked()
        self.save_btn.set_enabled(not probs and not blocked)
        dirty = self.cfg.is_dirty() if not probs else True
        if blocked:
            self.status.configure(fg=T["status_bad"], text="Can't save: " + blocked)
        elif probs:
            self.status.configure(fg=T["status_bad"], text="Can't save yet: " + "  ".join(probs))
        elif dirty:
            self.saved_note = ""
            self.status.configure(fg=T["fg"], text="Unsaved changes.")
        elif self.saved_note:
            self.status.configure(fg=T["status_good"], text=self.saved_note)
        else:
            self.status.configure(fg=T["fg"], text="No changes.")

    def refresh_all(self):
        self.path_label.configure(text=self.short_path())
        self.install_bar.show(self.install)
        for slot in hd.SLOT_IDS:
            self.draw_card(slot)
        self.refresh_inspector()
        self.refresh_hub_exits()
        self.refresh_worlds()
        self.set_hum_mode(self.cfg.hum_mode)

    def short_path(self):
        p = self.path
        return p if len(p) < 60 else "..." + p[-57:]

    def show_tab(self, key):
        self.commit_focus()
        self.tab = key
        for k, w in self.tab_btns.items():
            on = k == key
            w.configure(bg=T["chassis"] if on else T["bg"], fg=T["fg"] if on else T["dim"])
        self.room.pack_forget()
        self.exits_page.pack_forget()
        self.worlds_page.pack_forget()
        {"room": self.room, "exits": self.exits_page, "worlds": self.worlds_page}[key].pack(fill="both", expand=True)
        if key == "room":
            self.refresh_inspector()
        elif key == "exits":
            self.refresh_hub_exits()

    # ------------- file actions
    # ------------- install check
    def recheck(self, game=None):
        """Check the install again: the given game folder, else the one checked last, then the usual places."""
        self.install = check_game(game, self.install.game if self.install else None, None if self.gate else self.path)
        new = self.install.config_path
        if self.gate and new and os.path.normcase(os.path.abspath(new)) != os.path.normcase(os.path.abspath(self.path)):
            # the installed hub's config is another file than the one open (another game folder was picked): edit that one
            if not self.cfg.is_dirty() or ask(self.root, APP, f"Switch to the Portal Hub config in that game folder?\n\n{new}\n\n"
                                                              "Your unsaved changes here are dropped.", [("SWITCH", 1), ("STAY", 0)]):
                self.path = new
                self.do_reload()
                return
        self.install_bar.show(self.install)
        self.update_state()

    def pick_game(self):
        game = pick_game_folder(self.root)
        if game:
            self.recheck(game)

    def save(self):
        if not self.save_btn.enabled or self.save_blocked():
            return
        self.commit_focus()
        if self.cfg.changed_on_disk():
            choice = ask(self.root, "config.lua changed", "config.lua was changed by something else since it was loaded.\n\n"
                                                          "Reload shows the file as it is now and drops your edits here. Overwrite keeps your edits; "
                                                          "only the values you changed are written, onto the file as it was loaded.",
                         [("RELOAD", "reload"), ("OVERWRITE", "write"), ("CANCEL", None)])
            if choice is None:
                return
            if choice == "reload":
                self.do_reload()
                return
        for p in self.cfg.portals.values():
            if p.enabled and not p.name.strip():
                p.name = self.world_title(p.destination.strip())
            if p.enabled:
                p.destination = p.destination.strip()
        n = sum(p.enabled for p in self.cfg.portals.values())
        w = len(self.cfg.worlds)
        try:
            self.cfg.save()
            self.do_reload()
            self.saved_note = f"Saved {n} portal(s)" + (f" and {w} custom world(s)" if w else "") + ". Restart the game to apply (for a quick try: Ctrl+O, Restart All Mods)."
            self.update_state()
        except (OSError, LuaError) as err:
            self.status.configure(fg=T["status_bad"], text=f"Could not save: {err}")

    def do_reload(self):
        sel, world = self.sel, self.world_i
        self.load()
        self.sel = sel
        if 0 <= world < len(self.cfg.worlds):
            self.world_i = world
        self.saved_note = ""
        self.refresh_all()
        self.update_state()

    def reload(self):
        if self.cfg.is_dirty() and not ask(self.root, "Reload", "Drop your unsaved changes and read config.lua again?", [("RELOAD", 1), ("CANCEL", 0)]):
            return
        self.do_reload()

    def open_folder(self):
        subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(self.path)])

    def choose_file(self):
        picked = pick_config(self.root)
        if picked:
            try:
                HubConfig(picked)
            except (LuaError, UnicodeDecodeError) as err:
                ask(self.root, APP, f"That file can't be read as a Portal Hub config:\n\n{err}", [("OK", 1)])
                return
            self.path = picked
            remember_config(picked)
            self.do_reload()

    def on_close(self):
        if self.cfg.is_dirty():
            choice = ask(self.root, APP, "Save your changes to config.lua?", [("SAVE", "save"), ("DON'T SAVE", "drop"), ("CANCEL", None)])
            if choice is None:
                return
            if choice == "save":
                if not self.save_btn.enabled:
                    return
                self.save()
        self.root.destroy()


class Gate:
    """Shown instead of the editor while the hub isn't installed: what is missing, what to do, RE-CHECK, PICK GAME FOLDER.
    Nothing is read or written here; once a check finds the hub, on_ready(report) builds the editor."""

    def __init__(self, root, report, on_ready):
        self.root, self.report, self.on_ready = root, report, on_ready
        self.frame = tk.Frame(root, bg=T["bg"])
        self.frame.pack(fill="both", expand=True)
        App.stripe(None, self.frame).pack(fill="x")
        head = tk.Frame(self.frame, bg=T["head"], padx=px(18), pady=px(10))
        head.pack(fill="x")
        tk.Label(head, text="PORTAL HUB", bg=T["head"], fg=T["head_fg"], font=font(20, True)).pack(side="left")
        tk.Label(head, text="   CORDONA CORPORATIONS  //  install check", bg=T["head"], fg=T["head_dim"], font=font(10)).pack(side="left", pady=(px(8), 0))
        body = tk.Frame(self.frame, bg=T["chassis"], padx=px(24), pady=px(20))
        body.pack(fill="both", expand=True, padx=px(16), pady=(px(8), px(16)))
        self.mark = tk.Label(body, bg=T["chassis"], font=font(16, True), anchor="w")
        self.mark.pack(fill="x")
        self.headline = tk.Label(body, bg=T["chassis"], font=font(11, True), anchor="w", justify="left")
        self.headline.pack(fill="x", pady=(px(8), 0))
        self.steps = tk.Label(body, bg=T["chassis"], fg=T["fg"], font=font(10), anchor="w", justify="left")
        self.steps.pack(fill="x", pady=(px(10), 0))
        self.where = tk.Label(body, bg=T["chassis"], fg=T["dim"], font=font(9), anchor="w", justify="left")
        self.where.pack(fill="x", pady=(px(14), 0))
        tk.Label(body, text="This tool only reads the game folder; it never installs, downloads or changes UE4SS or mod files.",
                 bg=T["chassis"], fg=T["dim"], font=font(9), anchor="w").pack(fill="x", pady=(px(4), 0))
        row = tk.Frame(body, bg=T["chassis"])
        row.pack(fill="x", pady=(px(18), 0))
        Btn(row, "RE-CHECK", self.recheck, primary=True).pack(side="left")
        Btn(row, "PICK GAME FOLDER", self.pick).pack(side="left", padx=px(8))
        Btn(row, "QUIT", root.destroy).pack(side="right")
        # the download pages open in the player's browser only on a click; the tool itself never downloads anything
        if ic.PORTAL_HUB_NEXUS_URL:
            Btn(row, "PORTAL HUB PAGE", lambda: open_page(ic.PORTAL_HUB_NEXUS_URL)).pack(side="right", padx=px(8))
        Btn(row, "UE4SS PAGE", lambda: open_page(ic.UE4SS_NEXUS_URL)).pack(side="right", padx=(px(8), 0))
        body.bind("<Configure>", lambda e: [w.configure(wraplength=e.width - px(50)) for w in (self.headline, self.steps, self.where)])
        self.show()

    def show(self):
        r = self.report
        colour = T[INSTALL_COLOURS[r.state]]
        self.mark.configure(text=INSTALL_MARKS[r.state], fg=colour)
        self.headline.configure(text=r.headline, fg=colour)
        self.steps.configure(text="\n".join(f"{i}. {t}" for i, t in enumerate(r.todo, 1)))
        lines = [f"Game folder: {r.game}" if r.game else "Game folder: not found (looked in the Steam libraries)."]
        if r.ue4ss:
            lines.append(f"UE4SS: {r.ue4ss['text']} in {r.ue4ss_dir}")
        if r.hub_dir:
            lines.append(f"PortalHub: {r.hub_dir}")
        self.where.configure(text="\n".join(lines))

    def recheck(self, game=None):
        self.report = check_game(game, self.report.game)
        if self.report.hub_installed:
            self.frame.destroy()
            self.on_ready(self.report)
        else:
            self.show()

    def pick(self):
        game = pick_game_folder(self.root)
        if game:
            self.recheck(game)


def open_page(url):
    import webbrowser
    webbrowser.open(url)


def pick_config(parent):
    return filedialog.askopenfilename(parent=parent, title="Find the Portal Hub mod's config.lua (Mods\\PortalHub\\Scripts\\config.lua)",
                                      filetypes=[("config.lua", "config.lua"), ("Lua files", "*.lua")]) or None


def screenshots(root, app, base):
    from PIL import ImageGrab
    stem = base[:-4] if base.endswith(".png") else base

    def grab(win, name):
        win.update()
        root.after(300, root.quit)
        root.mainloop()
        win.update()
        x, y, w, h = win.winfo_rootx(), win.winfo_rooty(), win.winfo_width(), win.winfo_height()
        ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(stem + name)

    root.attributes("-topmost", True)
    app.select("A-4")
    app.pick_dest("train_start")
    app.pick_exit("manual")
    app.refresh_inspector()
    app.update_state()
    grab(root, ".png")
    app.dest.open()
    root.update()
    app.dest.popup.canvas.yview_moveto(1)
    pop = app.dest.popup.win
    pop.attributes("-topmost", True)
    grab(pop, "_dropdown.png")
    pop.destroy()
    d = EffectsDialog(root, app, hd.design_path("Niagara_Portal_SnowFlurry"), "SnowFlurry")
    d.present(wait=False)
    d.attributes("-topmost", True)
    grab(d, "_effects.png")
    d.destroy()
    app.show_tab("exits")
    grab(root, "_exits.png")
    app.show_tab("worlds")
    grab(root, "_worlds.png")
    root.destroy()


def main():
    global S
    ap = argparse.ArgumentParser(description=APP)
    ap.add_argument("--config")
    ap.add_argument("--game")
    ap.add_argument("--roundtrip")
    ap.add_argument("--screenshot")
    args = ap.parse_args()

    if args.roundtrip:
        path = args.config or find_config()
        HubConfig(path).save(args.roundtrip)
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.withdraw()
    root.title(APP)
    S = root.winfo_fpixels("1i") / 96.0
    # The install check comes first. Without --config the editor opens only on an installed hub's own config.lua;
    # with --config (testing) the check is shown but doesn't stop saving.
    report = check_game(args.game, args.config)

    def open_editor(rep):
        path = args.config or rep.config_path
        if not args.config and not args.screenshot:
            remember_config(path)
        try:
            app = App(root, path, install=rep, gate=not args.config)
        except (LuaError, UnicodeDecodeError) as err:
            root.deiconify()
            ask(root, APP, f"config.lua can't be read, so nothing was changed:\n\n{path}\n\n{err}", [("OK", 1)])
            root.destroy()
            return None
        root.minsize(px(1260), px(700))
        root.geometry(f"{px(1320)}x{px(780)}")
        root.protocol("WM_DELETE_WINDOW", app.on_close)
        return app

    window_icon(root)
    if args.config or report.hub_installed:
        app = open_editor(report)
        if app is None:
            return
    else:
        app = None
        root.geometry(f"{px(900)}x{px(520)}")
        Gate(root, report, open_editor)
    root.deiconify()
    dark_title_bar(root)
    root.update()
    if args.screenshot:
        if app:
            screenshots(root, app, args.screenshot)
        else:
            from PIL import ImageGrab
            root.attributes("-topmost", True)
            root.after(300, root.quit)
            root.mainloop()
            x, y, w, h = root.winfo_rootx(), root.winfo_rooty(), root.winfo_width(), root.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(args.screenshot)
            root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
