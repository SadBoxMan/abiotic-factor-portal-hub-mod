"""Drives the real editor (hidden window) through what a player does and checks config.lua afterwards.
Run:  python tools\\PortalHubConfig\\tests\\test_gui.py
"""
import os
import shutil
import sys
import tempfile
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
import PortalHubConfig as gui  # noqa: E402
import hubdata as hd  # noqa: E402
from luaconfig import HubConfig  # noqa: E402

TEMPLATE = os.path.join(HERE, "..", "..", "..", "mod", "PortalHub", "Scripts", "config.lua")
checks = fails = 0


def check(cond, what):
    global checks, fails
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", what)


def text(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def main():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "config.lua")
    shutil.copy(TEMPLATE, path)
    original = text(path)
    root = tk.Tk()
    root.withdraw()
    answers = []
    gui.ask = lambda *a, **k: answers.pop(0)
    gui.remember_config = lambda p: None
    app = gui.App(root, path)
    root.update()

    # nothing touched
    check(app.save_btn.enabled and not app.cfg.is_dirty(), "starts clean")
    app.save()
    check(text(path) == original, "saving with no edits leaves the file as it was")

    # every destination offered, both halves of the Botanical Wing among them, DLC not
    ids = [v for _, _, v in app.dest_items() if v]
    check("botanical_future_01" in ids and "botanical_present_01" in ids, "Botanical Wing offered")
    check(not any(hd.is_dlc(v) for v in ids), "no DLC in the list")
    check(len(hd.DESTINATIONS) == 22 and len(hd.DESIGNS) == 32 and all(hd.design_name(p) in hd.DESIGN_PARTS for _, p in hd.DESIGNS), "lists complete")
    check(all(os.path.exists(os.path.join(gui.ICON_DIR, x[3] + ".png")) for x in hd.DESTINATIONS if not x[1].startswith("botanical_")), "icons present")

    # picking a world on an empty slot turns it on, with the world's name and look
    app.select("B-1")
    app.pick_dest("botanical_future_01")
    p = app.cfg.portals["B-1"]
    check(p.enabled and p.name == "Botanical Wing (Future)" and p.design.endswith("Botanical_Red"), "pick fills name and look")
    app.update_state()
    check(app.save_btn.enabled, "savable")

    # custom destination: blocked while empty, and DLC refused
    app.select("B-2")
    app.pick_dest("__custom__")
    root.update()
    check(not app.save_btn.enabled and "B-2" in app.status.cget("text"), "empty custom destination blocks saving")
    app.pad_var.set("h_garden_START")
    root.update()
    check(not app.save_btn.enabled and "DLC" in app.status.cget("text"), "DLC refused, any case")
    app.pad_var.set("my_own_pad")
    root.update()
    check(app.save_btn.enabled and app.cfg.portals["B-2"].destination == "my_own_pad", "typed pad accepted")

    # light, brightness, effects
    app.select("B-1")
    app.pick_light("#2EE65C")
    app.bright.set(2.5)
    app.bright_set(2.5)
    app.cfg.hide[hd.design_path("Niagara_Portal_Botanical_Green")] = ["Ivy"]

    # slot off drops the portal; a locked slot can't be turned on
    app.select("A-3")
    app.toggle_slot()
    check(app.portal("A-3") is None, "A-3 off")
    app.select("A-1")
    app.toggle_slot()
    check("A-1" not in app.cfg.portals, "locked slot refused")

    # hub exits on a destination
    app.select("B-1")
    app.add_exit()
    root.update()
    fields = app.exit_rows[0]
    for f, v in zip(fields, ("-100.5", "2", "3", "90")):
        f.var.set(v)
    root.update()
    fields[1].var.set("abc")
    root.update()
    check(not app.save_btn.enabled, "bad hub exit number blocks saving")
    fields[1].var.set("2")
    root.update()
    check(app.save_btn.enabled, "fixed")
    app.toggle_buff()

    # a world with no arrival pad
    app.show_tab("worlds")
    app.add_world()
    root.update()
    check(not app.save_btn.enabled, "unfinished world blocks saving")
    app.w_vars["id"].set("plain_start")
    app.w_vars["asset"].set("/Game/Mods/Plain/BP_PlainLoader")
    root.update()
    check(app.w_vars["cls"].get() == "BP_PlainLoader_C", "class fills itself in")
    app.w_vars["level"].set("/Game/Mods/Plain/Maps/Plain_L0")
    for n in app.w_nums[3:]:
        n.var.set("")
    root.update()
    check(app.save_btn.enabled and app.cfg.worlds[0].arrive is None, "world valid without arrive")
    app.show_tab("room")
    app.set_hum_mode("manual")
    app.hum_step.set(40)
    app.hum_changed(40)
    app.save()
    root.update()
    check("Restart All Mods" in app.status.cget("text"), "save message: " + app.status.cget("text"))

    c = HubConfig(path)
    check(c.portals["B-1"].destination == "botanical_future_01" and c.portals["B-1"].brightness == 2.5 and c.portals["B-1"].light_hex == "#2EE65C", "B-1 written")
    check("A-3" not in c.portals and c.portals["B-2"].destination == "my_own_pad", "other slots written")
    check(c.hub_exits == {"botanical_future_01": [[-100.5, 2.0, 3.0, 90.0]]} and c.hub_exit_buff is True, "hub exits written")
    check(c.worlds[0].id == "plain_start" and c.worlds[0].arrive is None, "world written without arrive")
    check(c.hum_mode == "manual" and c.hum_manual == 40, "hum written")
    check(list(c.hide) == [hd.design_path("Niagara_Portal_Botanical_Green")], "effects written")
    out = text(path)
    check("Each entry in `portals`" in out and "docs/world-settings.md" in out, "comments kept")
    check(not out.startswith("﻿") and os.path.exists(path + ".bak"), "no BOM, backup kept")
    check(text(path + ".bak") == original, "backup holds the old file")
    if gui.__dict__.get("lupa") is None:
        try:
            import lupa
            t = lupa.LuaRuntime().execute(out)
            check(t["portals"][1]["slot"] == "B-1", "real Lua reads the saved file")
        except ImportError:
            pass

    # saved cleanly: nothing left to save, and a second save changes nothing
    check(not app.cfg.is_dirty(), "clean after save")
    app.save()
    check(text(path) == out, "second save is a no-op")

    # outside edit: refused until answered
    with open(path, "a", encoding="utf-8") as f:
        f.write("-- by hand\n")
    app.name_var.set("Renamed")
    answers.append(None)
    app.save()
    check("-- by hand" in text(path) and "Renamed" not in text(path), "cancel leaves an outside edit alone")
    answers.append("reload")
    app.save()
    check(not app.cfg.is_dirty(), "reload after outside edit")

    # the remove-world prompt warns and removes
    app.select("C-1")
    app.pick_dest("plain_start")
    app.show_tab("worlds")
    app.world_i = 0
    answers.append(1)
    app.remove_world()
    check(not app.cfg.worlds, "world removed")
    root.destroy()
    shutil.rmtree(d)
    print(f"{checks} checks, {fails} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
