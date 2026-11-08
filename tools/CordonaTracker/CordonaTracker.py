"""Cordona Tracker: a read-only view of the Portal Hub project's progress.

Reads the task queue in docs/handoff.md ("Queue at a glance" table), the plan in docs/roadmap.html and git log.
Writes nothing. Start it with CordonaTracker.bat, or  python CordonaTracker.py .
Python standard library only (Tkinter). Optional switches:
  --repo <folder>      read this repo instead of the one around this program
  --screenshot <png>   save a picture of the window and exit (needs Pillow)
Keys: F5 or R re-reads the files; 1-7 pick a state filter (1 = all).
"""
from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
import tkinter as tk
from tkinter import ttk

import trackerdata as td

APP = "Cordona Corporations Project Tracker"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONO = "Consolas"
# Theme copied from tools/PortalHubConfig/PortalHubConfig.py (T), so the two programs look alike. That file is not imported.
T = dict(bg="#0d0a13", chassis="#141020", panel="#1a1529", line="#3b2f58", fg="#e2d6ff", dim="#9181bd",
         accent="#b583ff", on_accent="#140c20", hover="#2a2140", bad="#ff8a80", warn="#ffc266", good="#7df0b0",
         head="#0d0a13", head_fg="#b583ff", head_dim="#9181bd", crt="#0b0812", stripe="#ffc247", stripe_bg="#0d0a13")
STATE_COLOUR = {"running": T["accent"], "waiting": T["warn"], "queued": T["fg"], "on hold": T["bad"],
                "done": T["good"], "retired": T["dim"], "unknown": T["bad"]}
BADGE_COLOUR = {"done": T["good"], "in progress": T["accent"], "next": T["warn"], "planned": T["dim"]}
ITEM_MARK = {"done": ("✓", T["good"]), "partial": ("◐", T["warn"]), "open": ("·", T["dim"])}
FILTERS = ("all",) + td.STATES
S = 1.0


def px(n):
    return int(round(n * S))


def font(size=10, bold=False):
    return (MONO, size, "bold") if bold else (MONO, size)


def dark_title_bar(win):
    try:
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4)
        rgb = int(T["head"][1:], 16)
        bgr = ctypes.c_int(((rgb & 0xff) << 16) | (rgb & 0xff00) | (rgb >> 16))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(bgr), 4)
    except (AttributeError, OSError):
        pass


def window_icon(root):
    n = 32
    img = tk.PhotoImage(width=n, height=n)
    rows = []
    for y in range(n):
        row = []
        for x in range(n):
            d = ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** 0.5
            row.append("#c08bff" if 10 <= d <= 14.5 else "#7df0b0" if d <= 5 else "#150f22")
        rows.append("{" + " ".join(row) + "}")
    img.put(" ".join(rows))
    root.iconphoto(True, img)
    root.window_icon = img


class App:
    def __init__(self, root, repo):
        self.root, self.repo = root, repo
        self.filter = "all"
        self.data = None
        self.build()
        self.reload()

    # ------------- building
    def build(self):
        r = self.root
        r.configure(bg=T["bg"])
        self.stripe(r).pack(fill="x")
        head = tk.Frame(r, bg=T["head"], padx=px(18), pady=px(10))
        head.pack(fill="x")
        tk.Label(head, text="PROJECT TRACKER", bg=T["head"], fg=T["head_fg"], font=font(20, True)).pack(side="left")
        tk.Label(head, text="   CORDONA CORPORATIONS  //  portal hub progress", bg=T["head"], fg=T["head_dim"],
                 font=font(10)).pack(side="left", pady=(px(8), 0))
        self.updated_label = tk.Label(head, bg=T["head"], fg=T["head_dim"], font=font(9))
        self.updated_label.pack(side="right", pady=(px(8), 0))

        style = ttk.Style(r)
        style.theme_use("clam")
        style.configure("T.Treeview", background=T["crt"], fieldbackground=T["crt"], foreground=T["fg"],
                        bordercolor=T["line"], lightcolor=T["line"], darkcolor=T["line"], rowheight=px(24), font=font(10))
        style.map("T.Treeview", background=[("selected", T["hover"])], foreground=[("selected", T["fg"])])
        style.configure("T.Treeview.Heading", background=T["panel"], foreground=T["dim"], bordercolor=T["line"],
                        lightcolor=T["panel"], darkcolor=T["panel"], relief="flat", font=font(9, True))
        style.map("T.Treeview.Heading", background=[("active", T["hover"])])
        style.configure("T.Vertical.TScrollbar", background=T["panel"], troughcolor=T["crt"], bordercolor=T["line"],
                        arrowcolor=T["dim"], lightcolor=T["panel"], darkcolor=T["panel"])

        body = tk.Frame(r, bg=T["chassis"], padx=px(14), pady=px(12))
        body.pack(fill="both", expand=True, padx=px(16))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # left: tasks
        left = tk.Frame(body, bg=T["chassis"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, px(12)))
        self.heading(left, "TASK QUEUE").pack(fill="x")
        bar = tk.Frame(left, bg=T["chassis"])
        bar.pack(fill="x", pady=(px(4), px(6)))
        self.filter_btns = {}
        for i, key in enumerate(FILTERS):
            w = tk.Label(bar, font=font(9, True), padx=px(8), pady=px(3), cursor="hand2")
            w.pack(side="left", padx=(0, px(4)))
            w.bind("<Button-1>", lambda e, k=key: self.set_filter(k))
            self.filter_btns[key] = w
        tree_box = tk.Frame(left, bg=T["chassis"])
        tree_box.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_box, style="T.Treeview", columns=("id", "task", "state", "commit"),
                                 show="headings", selectmode="browse")
        for col, text, w, stretch in (("id", "ID", 86, False), ("task", "TASK", 360, True),
                                      ("state", "STATE", 96, False), ("commit", "COMMIT", 90, False)):
            self.tree.heading(col, text=text, anchor="w")
            self.tree.column(col, width=px(w), stretch=stretch, anchor="w")
        for st, colour in STATE_COLOUR.items():
            self.tree.tag_configure(st, foreground=colour)
        sb = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview, style="T.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_detail())

        self.heading(left, "DETAIL FROM THE HANDOFF NOTE").pack(fill="x", pady=(px(10), px(4)))
        self.detail = tk.Text(left, height=8, wrap="word", bg=T["crt"], fg=T["fg"], insertbackground=T["fg"],
                              relief="flat", highlightthickness=1, highlightbackground=T["line"], font=font(9),
                              padx=px(8), pady=px(6))
        self.detail.pack(fill="both")
        self.detail.configure(state="disabled")

        # right: release path
        right = tk.Frame(body, bg=T["panel"], padx=px(14), pady=px(10), highlightthickness=1,
                         highlightbackground=T["line"])
        right.grid(row=0, column=1, sticky="nsew")
        self.right = right

        # footer
        foot = tk.Frame(r, bg=T["bg"], padx=px(16), pady=px(8))
        foot.pack(fill="x")
        self.refresh_btn = tk.Label(foot, text="REFRESH  (F5)", bg=T["accent"], fg=T["on_accent"], font=font(10, True),
                                    padx=px(14), pady=px(5), cursor="hand2")
        self.refresh_btn.pack(side="right")
        self.refresh_btn.bind("<Button-1>", lambda e: self.reload())
        self.status = tk.Label(foot, bg=T["bg"], fg=T["dim"], font=font(9), anchor="w", justify="left")
        self.status.pack(side="left", fill="x", expand=True)
        for key in ("<F5>", "r", "R"):
            r.bind(key, lambda e: self.reload())
        for i, key in enumerate(FILTERS):
            r.bind(str(i + 1), lambda e, k=key: self.set_filter(k))

    def stripe(self, parent):
        h = px(7)
        c = tk.Canvas(parent, height=h, highlightthickness=0, bg=T["stripe_bg"])
        for x in range(-px(20), 4000, px(22)):
            c.create_polygon(x, h, x + h, 0, x + h + px(11), 0, x + px(11), h, fill=T["stripe"], outline="")
        return c

    def heading(self, parent, text, bg=None):
        return tk.Label(parent, text=text, bg=bg or T["chassis"], fg=T["dim"], font=font(9, True), anchor="w")

    # ------------- data
    def reload(self):
        sel = self.tree.selection()
        keep = sel[0] if sel else None
        self.data = td.load(self.repo)
        d = self.data
        self.updated_label.configure(text=f"handoff last updated: {d.updated or '?'}")
        self.fill_tree(keep)
        self.fill_right()
        counts = {s: sum(t.state == s for t in d.tasks) for s in td.STATES}
        msg = f"Read {time.strftime('%H:%M:%S')} from {self.repo}  //  {len(d.tasks)} tasks, " + \
              ", ".join(f"{counts[s]} {s}" for s in td.STATES if counts[s])
        if d.warnings:
            msg += "\n! " + "\n! ".join(d.warnings[:3]) + (f"\n! ...and {len(d.warnings) - 3} more" if len(d.warnings) > 3 else "")
        self.status.configure(text=msg, fg=T["warn"] if d.warnings else T["dim"])

    def set_filter(self, key):
        self.filter = key
        self.fill_tree(None)

    def fill_tree(self, keep):
        d = self.data
        for key, w in self.filter_btns.items():
            n = len(d.tasks) if key == "all" else sum(t.state == key for t in d.tasks)
            on = key == self.filter
            w.configure(text=f"{key.upper()} {n}", bg=T["accent"] if on else T["panel"],
                        fg=T["on_accent"] if on else (STATE_COLOUR.get(key, T["fg"]) if n else T["line"]))
        self.tree.delete(*self.tree.get_children())
        order = {s: i for i, s in enumerate(td.STATES)}
        shown = [t for t in d.tasks if self.filter == "all" or t.state == self.filter]
        shown.sort(key=lambda t: (order.get(t.state, -1), t.id) if self.filter == "all" else t.id)
        for t in shown:
            commit = t.commit + (" *" if t.commit_from_git else "")
            self.tree.insert("", "end", iid=t.id, values=(t.id, t.title, t.state, commit), tags=(t.state,))
        if keep and self.tree.exists(keep):
            self.tree.selection_set(keep)
        elif shown:
            self.tree.selection_set(shown[0].id)
        self.show_detail()

    def show_detail(self):
        sel = self.tree.selection()
        t = next((x for x in self.data.tasks if sel and x.id == sel[0]), None)
        if t is None:
            text = "No task selected."
        else:
            text = t.detail or "(no bullet for this task in section 1 of the handoff note yet)"
            if t.commit_from_git:
                text = f"Commit {t.commit} found in git log (not in the table).\n\n" + text
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def fill_right(self):
        for w in self.right.winfo_children():
            w.destroy()
        d, p = self.data, self.right
        wrap = px(430)
        self.heading(p, "ROADMAP ORDER", T["panel"]).pack(fill="x")
        for s in d.steps:
            row = tk.Frame(p, bg=T["panel"])
            row.pack(fill="x", pady=px(2))
            colour = BADGE_COLOUR.get(s.badge.lower(), T["dim"])
            tk.Label(row, text=s.num, bg=colour, fg=T["on_accent"], font=font(10, True), width=2).pack(side="left")
            tk.Label(row, text=" " + s.title, bg=T["panel"], fg=T["fg"], font=font(10), anchor="w").pack(side="left")
            tk.Label(row, text=s.badge.upper(), bg=T["panel"], fg=colour, font=font(8, True)).pack(side="right")
        if not d.steps:
            tk.Label(p, text="(no steps read from docs/roadmap.html)", bg=T["panel"], fg=T["bad"], font=font(9)).pack(anchor="w")

        one = next((s for s in d.steps if "1.0" in s.title), None)
        if one and one.items:
            done = sum(st == "done" for _, st in one.items)
            self.heading(p, f"PORTAL HUB 1.0  ({done} of {len(one.items)} pieces done)", T["panel"]).pack(fill="x", pady=(px(12), px(2)))
            self.meter(p, [st for _, st in one.items])
            for text, st in one.items:
                self.item(p, text.split(":")[0], st, wrap)

        if d.understanding:
            done = sum(st == "done" for _, st in d.understanding)
            part = sum(st == "partial" for _, st in d.understanding)
            self.heading(p, f"2.0: FULL UNDERSTANDING  ({done} done, {part} started, of {len(d.understanding)})",
                         T["panel"]).pack(fill="x", pady=(px(12), px(2)))
            if d.gate:
                self.item(p, "Stability gate first: " + d.gate.split(".")[0] + " (hard gate)", "open", wrap, bad=True)
            self.meter(p, [st for _, st in d.understanding])
            grid = tk.Frame(p, bg=T["panel"])
            grid.pack(fill="x")
            for i, (text, st) in enumerate(d.understanding):
                short = text.split(" (")[0]
                cell = tk.Frame(grid, bg=T["panel"])
                cell.grid(row=i % 6, column=i // 6, sticky="w", padx=(0, px(10)))
                mark, colour = ITEM_MARK[st]
                tk.Label(cell, text=f"{mark} {i + 1:>2}", bg=T["panel"], fg=colour, font=font(9, True)).pack(side="left")
                tk.Label(cell, text=" " + (short if len(short) <= 26 else short[:25] + "…"), bg=T["panel"], fg=T["fg"] if st != "open" else T["dim"],
                         font=font(9)).pack(side="left")
            tk.Label(p, text="✓ done   ◐ started (first form or findings)   · open", bg=T["panel"],
                     fg=T["dim"], font=font(8)).pack(anchor="w", pady=(px(4), 0))

    def item(self, parent, text, st, wrap, bad=False):
        mark, colour = ITEM_MARK[st]
        row = tk.Frame(parent, bg=T["panel"])
        row.pack(fill="x")
        tk.Label(row, text="!" if bad else mark, bg=T["panel"], fg=T["bad"] if bad else colour, font=font(10, True), width=2).pack(side="left", anchor="n")
        tk.Label(row, text=text, bg=T["panel"], fg=T["fg"], font=font(9), anchor="w", justify="left",
                 wraplength=wrap).pack(side="left", fill="x")

    def meter(self, parent, states):
        h = px(8)
        c = tk.Canvas(parent, height=h, highlightthickness=0, bg=T["crt"])
        c.pack(fill="x", pady=(px(2), px(4)))

        def draw(e=None):
            c.delete("all")
            w = c.winfo_width()
            n = max(len(states), 1)
            for i, st in enumerate(states):
                colour = {"done": T["good"], "partial": T["warn"]}.get(st, T["line"])
                c.create_rectangle(i * w / n + 1, 0, (i + 1) * w / n - 1, h, fill=colour, outline="")
        c.bind("<Configure>", draw)


def main():
    global S
    ap = argparse.ArgumentParser(description=APP)
    ap.add_argument("--repo")
    ap.add_argument("--screenshot")
    args = ap.parse_args()
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.withdraw()
    root.title(APP)
    S = root.winfo_fpixels("1i") / 96.0
    repo = args.repo or td.find_repo(BASE_DIR)
    if not repo:
        root.deiconify()
        tk.Label(root, text="docs/handoff.md not found above " + BASE_DIR, bg=T["bg"], fg=T["bad"], font=font(11),
                 padx=20, pady=20).pack()
        root.mainloop()
        return
    App(root, repo)
    window_icon(root)
    root.geometry(f"{px(1240)}x{px(720)}")
    root.minsize(px(1000), px(600))
    root.deiconify()
    dark_title_bar(root)
    root.update()
    if args.screenshot:
        root.lift()
        root.attributes("-topmost", True)
        root.update()
        time.sleep(0.4)
        from PIL import ImageGrab
        x, y = root.winfo_rootx(), root.winfo_rooty()
        ImageGrab.grab((x, y, x + root.winfo_width(), y + root.winfo_height()), all_screens=True).save(args.screenshot)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
