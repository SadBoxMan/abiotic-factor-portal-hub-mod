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
    # the shipped template is blank (CRD-031); this test starts from one portal on A-3, as the template used to have
    with open(path, encoding="utf-8", newline="") as f:
        t = f.read()
    nl = "\r\n" if "\r\n" in t else "\n"          # a Windows checkout may have CRLF
    blank = "    portals = {" + nl + "    }," + nl
    assert blank in t, "the template's empty portals list was not found"
    one = '    portals = {' + nl + '        { slot = "A-3", name = "Dunkeltaler Forest", destination = "signal_start" },' + nl + '    },' + nl
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(t.replace(blank, one, 1))
    # A fixed MHE file (not the shipped one, which has an MHE in every world, CRD-031): two worlds and the failsafe, so fog_start is unrecorded.
    with open(os.path.join(d, "manual_exits.lua"), "w", encoding="utf-8", newline="") as f:
        f.write("return {\n"
                '    ["anteverse_a_start"] = { 127627, 335370, 1930, 302 },\n'
                '    ["failsafe"] = { -11938, 8293, 257, 183 },\n'
                '    ["train_start"] = { 333394, 13460, 872, 359 },\n'
                "}\n")
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
    story = [x[1] for x in hd.DESTINATIONS if x[0] == "Story"]
    check(story[-3:] == ["wall_start", "botanical_future_01", "island_start"], "Divarication sits just above Albatross")
    check(app.mhe_problem == "" and "train_start" in app.mhe_spots and app.mhe_failsafe, "manual_exits.lua read next to config.lua")

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

    # slot off = wiped (author's ruling): turned on again it starts empty, and the old world's data is not kept
    app.select("C-2")
    app.pick_dest("train_start")
    app.pick_exit("manual")
    app.toggle_manual_buffs()
    app.pick_light("#FF2020")
    check(app.cfg.portals["C-2"].manual_buffs and app.buff_btn.cget("text") == "BUFFS ON", "manual buffs on")
    app.toggle_slot()
    q = app.cfg.portals.get("C-2")
    check(q is None or (not q.enabled and not q.destination and not q.exits and not q.manual_buffs and not q.light_hex), "slot off wipes it")
    app.toggle_slot()
    q = app.portal("C-2")
    check(q is not None and q.destination == "" and q.exits == "" and q.light_hex == "" and q.name == "", "turned on again: empty")
    root.update()
    check(not app.save_btn.enabled and "C-2" in app.status.cget("text"), "an empty slot turned on asks for a world")
    app.toggle_slot()
    root.update()
    check(app.save_btn.enabled, "turned off again: savable")

    # exit modes: per portal (1-4), manual buffs only with MANUAL, none for custom worlds
    app.select("B-1")
    check(app.exit_seg.value == "" and app.exit_seg.enabled and "Default: GAME" in app.exit_note.cget("text"), "new portal follows the default")
    check(not app.buff_btn.enabled, "buffs off limits outside MANUAL")
    app.pick_exit("manual")
    check("No MHE is recorded" in app.exit_note.cget("text"), "MANUAL without a recorded MHE warns")
    app.toggle_manual_buffs()
    app.pick_exit("hub")
    check(app.cfg.portals["B-1"].exits == "hub" and not app.cfg.portals["B-1"].manual_buffs, "leaving MANUAL drops the buffs")
    app.select("A-4")
    app.pick_dest("anteverse_a_start")
    app.pick_exit("manual")
    check("No MHE" not in app.exit_note.cget("text") and app.buff_btn.enabled, "MANUAL with a recorded MHE")
    app.toggle_manual_buffs()

    # the HUB EXITS tab: global mode and MHE switches
    app.show_tab("exits")
    root.update()
    app.pick_global_exit("dynamic")
    check(app.cfg.exit_mode == "dynamic" and app.global_seg.value == "dynamic", "global mode picked")
    rows = dict((pad, title) for title, pad in app.mhe_rows())
    check(len(rows) == len(hd.DESTINATIONS) and "failsafe" not in rows, "one row per base-game world")
    check(app.mhe_status("anteverse_a_start").startswith("used by the MANUAL portal in A-4"), "mode-4 portal uses the MHE")
    check(app.mhe_status("train_start").startswith("leads to the Failsafe Exit"), "no hub portal: Failsafe Exit")
    check(app.mhe_status("fog_start") == "no MHE recorded yet", "unrecorded world")
    app.toggle_mhe("fog_start")
    check("fog_start" not in app.cfg.mhe_off, "an unrecorded MHE can't be switched off")
    app.toggle_mhe("train_start")
    check(app.cfg.mhe_off == {"train_start"} and app.mhe_status("train_start") == "switched off", "MHE switched off")
    app.show_tab("room")

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
    check("C-2" not in c.portals and "#FF2020" not in [q.light_hex for q in c.portals.values()], "the wiped slot left nothing behind")
    check(c.portals["B-1"].exits == "hub" and not c.portals["B-1"].manual_buffs, "B-1 exit mode written")
    check(c.portals["A-4"].exits == "manual" and c.portals["A-4"].manual_buffs, "A-4 manual with buffs written")
    check(c.exit_mode == "dynamic" and c.mhe_off == {"train_start"}, "exitMode and mhe written")
    check("hubExit" not in text(path), "no old hubExits fields")
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
            check(t["portals"][1]["slot"] == "A-4" and t["portals"][1]["exits"] == "manual" and t["mhe"]["train_start"] is False,
                  "real Lua reads the saved file")
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
