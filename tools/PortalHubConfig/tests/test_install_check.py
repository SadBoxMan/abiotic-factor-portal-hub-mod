"""Install check (install_check.py, CRD-019) against mock game folders, plus the editor's gate on them.
Run:  python tools\\PortalHubConfig\\tests\\test_install_check.py
The mock folders are made in a temp folder; nothing outside it is read or written (the Steam libraries are passed in).
"""
import os
import shutil
import struct
import sys
import tempfile
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import install_check as ic  # noqa: E402
import PortalHubConfig as gui  # noqa: E402

TEMPLATE_DIR = os.path.join(HERE, "..", "..", "..", "mod", "PortalHub", "Scripts")
checks = fails = 0


def check(cond, what):
    global checks, fails
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", what)


def fake_dll(path, built):
    """A file with just enough of a PE header for its link time to be read."""
    head = bytearray(0x100)
    head[0:2] = b"MZ"
    struct.pack_into("<I", head, 0x3C, 0x80)
    head[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHI", head, 0x84, 0x8664, 1, built)
    with open(path, "wb") as f:
        f.write(bytes(head))


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


MODS_TXT = "PortalLogger : 1\nPortalHub : {on}\n\n; Built-in keybinds, do not move up!\nKeybinds : 1\n"


def make_install(base, name, ue4ss="new", built=ic.RECOMMENDED_BUILT, log_sha=ic.RECOMMENDED_SHA, hub=True,
                 scripts=ic.HUB_SCRIPTS, mods_txt="1", proxy=True, enabled_txt=False):
    """A mock library\\steamapps\\common\\AbioticFactor. Returns (library, game folder)."""
    lib = os.path.join(base, name)
    game = os.path.join(lib, "steamapps", "common", "AbioticFactor")
    win64 = os.path.join(game, ic.REL_WIN64)
    os.makedirs(win64)
    open(os.path.join(win64, ic.GAME_EXE), "wb").close()
    if proxy and ue4ss:
        open(os.path.join(win64, "dwmapi.dll"), "wb").close()
    ue = os.path.join(win64, "ue4ss") if ue4ss == "new" else win64
    if ue4ss:
        os.makedirs(os.path.join(ue, "Mods"), exist_ok=True)
        fake_dll(os.path.join(ue, "UE4SS.dll"), built)
        if log_sha:
            write(os.path.join(ue, "UE4SS.log"), "[2026-11-10] Console created\n"
                                                 f"[2026-11-10] UE4SS - v3.0.1 Beta #0 - Git SHA #{log_sha}\n")
            t = os.path.getmtime(os.path.join(ue, "UE4SS.dll"))
            os.utime(os.path.join(ue, "UE4SS.log"), (t + 60, t + 60))
        if mods_txt is not None:
            write(os.path.join(ue, "Mods", "mods.txt"), MODS_TXT.format(on=mods_txt) if mods_txt != "absent"
                  else "PortalLogger : 1\nKeybinds : 1\n")
        if hub:
            sd = os.path.join(ue, "Mods", "PortalHub", "Scripts")
            os.makedirs(sd)
            for s in scripts:
                src = os.path.join(TEMPLATE_DIR, s)
                if os.path.exists(src):
                    shutil.copy(src, sd)
                else:
                    write(os.path.join(sd, s), "return {}\n")
            if enabled_txt:
                open(os.path.join(ue, "Mods", "PortalHub", "enabled.txt"), "wb").close()
    return lib, game


def tree(folder):
    out = {}
    for d, _, files in os.walk(folder):
        for f in files:
            p = os.path.join(d, f)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def main():
    base = tempfile.mkdtemp(prefix="hubcheck_")
    try:
        run(base)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"{checks - fails}/{checks} checks passed")
    sys.exit(1 if fails else 0)


def run(base):
    # ---- complete install
    lib, game = make_install(base, "complete")
    before = tree(game)
    r = ic.check_install(game)
    check(r.state == "ok" and r.hub_installed, f"complete: ok ({r.state}: {r.text()})")
    check(r.ue4ss["state"] == "ok" and r.ue4ss["sha"] == ic.RECOMMENDED_SHA and "3.0.1" in r.ue4ss["text"], "complete: UE4SS version read from the log")
    check(r.enabled == "on" and r.enabled_by == "mods.txt" and r.proxy == "dwmapi.dll", "complete: switched on, loader found")
    check(r.config_path and r.config_path.endswith(os.path.join("PortalHub", "Scripts", "config.lua")), "complete: config path")
    check("installed and switched on" in r.headline and not r.todo, "complete: headline, nothing to do")
    check(tree(game) == before, "the check writes nothing")

    # ---- finding the game
    other, _ = make_install(base, "nogame_lib", ue4ss=None, hub=False)
    shutil.rmtree(os.path.join(other, "steamapps"))
    check(ic.find_game(libraries=[other, lib]) == os.path.normpath(game), "found in the second Steam library")
    check(ic.find_game(libraries=[other]) is None, "no game in any library: None")
    win64 = os.path.join(game, ic.REL_WIN64)
    for picked, what in ((game, "the game folder"), (os.path.join(game, "AbioticFactor"), "the inner AbioticFactor"),
                         (win64, "Win64"), (os.path.join(win64, "ue4ss", "Mods", "PortalHub", "Scripts"), "the hub's Scripts"),
                         (os.path.join(win64, "ue4ss", "Mods", "PortalHub", "Scripts", "config.lua"), "config.lua itself"),
                         (lib, "the Steam library"), (os.path.join(lib, "steamapps"), "steamapps")):
        check(ic.game_folder_from(picked) == os.path.normpath(game), f"picked {what}: the game folder")
    check(ic.game_folder_from(other) is None and ic.game_folder_from(None) is None, "picked a folder that isn't the game: None")
    check(ic.find_game(libraries=[], hints=[None, other, win64]) == os.path.normpath(game), "hints come before the libraries")
    vdf = os.path.join(base, "steam", "steamapps", "libraryfolders.vdf")
    write(vdf, '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n'
          % (os.path.join(base, "steam").replace("\\", "\\\\"), lib.replace("\\", "\\\\")))
    libs = ic.steam_libraries(roots=[os.path.join(base, "steam"), os.path.join(base, "steam").upper()])
    check(len(libs) == 2 and os.path.normpath(lib) in libs, f"libraryfolders.vdf read, duplicates dropped ({libs})")

    # ---- no game found
    r = ic.check_install(None)
    check(r.state == "nogame" and not r.hub_installed and r.config_path is None, "no game: nogame")
    check("PICK GAME FOLDER" in r.text(), "no game: says to pick the folder")
    check(ic.check_install(other).state == "nogame", "a folder that isn't the game: nogame")

    # ---- missing mod
    _, g = make_install(base, "nomod", hub=False)
    r = ic.check_install(g)
    check(r.state == "missing" and not r.hub_installed and r.config_path is None, "missing mod: missing")
    check("the PortalHub mod" in r.headline and any("Nexus" in t for t in r.todo), "missing mod: says to install it from Nexus")
    check("Nothing is saved" in r.text(), "missing mod: says nothing is saved")

    # ---- a script missing
    _, g = make_install(base, "nomhe", scripts=("main.lua", "config.lua", "slots.lua"))
    r = ic.check_install(g)
    check(r.state == "missing" and r.scripts_missing == ["manual_exits.lua"] and "manual_exits.lua" in r.headline, "missing manual_exits.lua named")
    _, g = make_install(base, "nomain", scripts=("config.lua", "manual_exits.lua", "slots.lua"))
    check(ic.check_install(g).scripts_missing == ["main.lua"], "missing main.lua named")

    # ---- no UE4SS
    _, g = make_install(base, "noue4ss", ue4ss=None, hub=False)
    r = ic.check_install(g)
    check(r.state == "missing" and r.ue4ss is None and "UE4SS" in r.headline, "no UE4SS: missing")
    check(any("UE4SS for Abiotic Factor" in t and "1.25.0" in t for t in r.todo), "no UE4SS: says which UE4SS to install")
    _, g = make_install(base, "noproxy", proxy=False)
    r = ic.check_install(g)
    check(r.state == "missing" and "dwmapi.dll" in r.headline, "UE4SS without its loader DLL: missing")

    # ---- disabled in mods.txt
    _, g = make_install(base, "disabled", mods_txt="0")
    r = ic.check_install(g)
    check(r.state == "warn" and r.hub_installed and r.enabled == "off", "disabled: warn, still installed")
    check("switched off in mods.txt" in r.headline and any("PortalHub : 1" in t for t in r.todo), "disabled: says to set PortalHub : 1")
    _, g = make_install(base, "unlisted", mods_txt="absent")
    r = ic.check_install(g)
    check(r.state == "warn" and r.enabled == "absent" and "not listed" in r.headline, "not in mods.txt: warn")
    _, g = make_install(base, "nomodstxt", mods_txt=None)
    r = ic.check_install(g)
    check(r.state == "warn" and r.enabled is None and "no mods.txt" in r.headline, "no mods.txt: warn")
    _, g = make_install(base, "enabledtxt", mods_txt="0", enabled_txt=True)
    r = ic.check_install(g)
    check(r.state == "ok" and r.enabled_by == "enabled.txt", "enabled.txt switches it on")
    _, g = make_install(base, "comment", mods_txt="1")
    p = os.path.join(g, ic.REL_WIN64, "ue4ss", "Mods", "mods.txt")
    write(p, "; PortalHub : 1\nportalhub : 0 ; off for now\nKeybinds : 1\n")
    check(ic.check_install(g).enabled == "off", "mods.txt comments ignored, names any case")

    # ---- old UE4SS
    _, g = make_install(base, "oldsha", built=1784168482, log_sha="c838a8ac")
    r = ic.check_install(g)
    check(r.state == "warn" and r.hub_installed and r.ue4ss["state"] == "outdated", "old UE4SS (July hash): outdated, still installed")
    check("July" in r.headline and any("Update UE4SS" in t for t in r.todo), "old UE4SS: says to update")
    _, g = make_install(base, "oldbuild", built=ic.RECOMMENDED_BUILT - 86400 * 30, log_sha=None)
    r = ic.check_install(g)
    check(r.ue4ss["state"] == "outdated" and "built before" in r.ue4ss["why"], "unknown hash, older build time: outdated")
    _, g = make_install(base, "newbuild", built=ic.RECOMMENDED_BUILT + 86400 * 30, log_sha="0123abcd")
    check(ic.check_install(g).state == "ok", "unknown hash, newer build time: ok")
    _, g = make_install(base, "v2", ue4ss="old")
    r = ic.check_install(g)
    check(r.ue4ss["state"] == "outdated" and "v2.x" in r.ue4ss["text"] and r.state == "warn", "UE4SS 2.x layout: outdated")
    _, g = make_install(base, "v4", log_sha=None)
    write(os.path.join(g, ic.REL_WIN64, "ue4ss", "UE4SS.log"), "UE4SS - v3.1.0 Beta #0 - Git SHA #feedbeef\n")
    check(ic.check_install(g).ue4ss["state"] == "ok", "newer version number: ok")
    _, g = make_install(base, "stalelog", built=ic.RECOMMENDED_BUILT, log_sha="c838a8ac")
    ue = os.path.join(g, ic.REL_WIN64, "ue4ss")
    t = os.path.getmtime(os.path.join(ue, "UE4SS.dll"))
    os.utime(os.path.join(ue, "UE4SS.log"), (t - 3600, t - 3600))
    check(ic.check_install(g).ue4ss["state"] == "ok", "a log older than the DLL is ignored (the build time decides)")
    _, g = make_install(base, "nover", built=0, log_sha=None)
    with open(os.path.join(g, ic.REL_WIN64, "ue4ss", "UE4SS.dll"), "wb") as f:
        f.write(b"not a dll")
    r = ic.check_install(g)
    check(r.ue4ss["state"] == "unknown" and r.state == "warn" and "Couldn't tell" in r.headline, "unreadable version: warn, unknown")

    # ---- the editor's gate
    gui_checks(base)


def gui_checks(base):
    gui.ask = lambda *a, **k: 0
    gui.remember_config = lambda p: None
    gui.remember_game = lambda p: None
    root = tk.Tk()
    root.withdraw()

    _, game = make_install(base, "gui_ok")
    rep = ic.check_install(game)
    app = gui.App(root, rep.config_path, install=rep, gate=True)
    root.update()
    check(app.save_btn.enabled and not app.save_blocked(), "editor: installed hub saves")
    check(app.install_bar.mark.cget("text") == "INSTALLED", "editor: install line says INSTALLED")

    _, game = make_install(base, "gui_off", mods_txt="0")
    rep = ic.check_install(game)
    app.recheck(game)
    root.update()
    check(os.path.normcase(app.path) == os.path.normcase(rep.config_path), "editor: re-check on another game folder opens its config")
    check(app.install_bar.mark.cget("text") == "CHECK" and "PortalHub : 1" in app.install_bar.text.cget("text"), "editor: disabled shows the fix")
    check(app.save_btn.enabled, "editor: disabled in mods.txt still saves")

    # the hub's main.lua goes missing under a running editor: re-check refuses to save
    os.remove(os.path.join(os.path.dirname(rep.config_path), "main.lua"))
    cfg_before = tree(os.path.dirname(rep.config_path))
    app.recheck()
    root.update()
    check(app.install.state == "missing" and not app.save_btn.enabled and app.save_blocked(), "editor: hub gone, save refused")
    check(app.install_bar.mark.cget("text") == "MISSING" and "Can't save" in app.status.cget("text"), "editor: says why it can't save")
    app.select("A-1")
    app.save()
    check(tree(os.path.dirname(rep.config_path)) == cfg_before, "editor: nothing written while the hub is missing")

    # --config (gate off): the check is shown but not enforced
    app2 = gui.App(root, rep.config_path, install=app.install, gate=False)
    check(app2.save_btn.enabled and not app2.save_blocked(), "--config: not gated")
    app3 = gui.App(root, rep.config_path)
    check(app3.install_bar.mark.cget("text") == "NOT CHECKED", "no check: says so")

    # the gate screen: missing, then the player installs the mod and clicks RE-CHECK
    _, game = make_install(base, "gui_gate", hub=False)
    ready = []
    real_check = gui.check_game
    gui.check_game = lambda *hints: ic.check_install(game)
    try:
        top = tk.Toplevel(root)
        g = gui.Gate(top, ic.check_install(game), ready.append)
        root.update()
        check(g.mark.cget("text") == "MISSING" and "PortalHub" in g.headline.cget("text"), "gate: says the mod is missing")
        check("Nexus" in g.steps.cget("text") and "1." in g.steps.cget("text"), "gate: numbered steps")
        g.recheck()
        check(not ready and g.frame.winfo_exists(), "gate: still missing, stays")
        sd = os.path.join(game, ic.REL_WIN64, "ue4ss", "Mods", "PortalHub", "Scripts")
        os.makedirs(sd)
        for s in ic.HUB_SCRIPTS:
            shutil.copy(os.path.join(TEMPLATE_DIR, s), sd)
        g.recheck()
        check(len(ready) == 1 and ready[0].hub_installed, "gate: installed, hands over to the editor")
        top.destroy()
        top = tk.Toplevel(root)
        g = gui.Gate(top, ic.check_install(None), ready.append)
        root.update()
        check(g.mark.cget("text") == "NO GAME" and "not found" in g.where.cget("text"), "gate: no game found")
    finally:
        gui.check_game = real_check
    root.destroy()


if __name__ == "__main__":
    main()
