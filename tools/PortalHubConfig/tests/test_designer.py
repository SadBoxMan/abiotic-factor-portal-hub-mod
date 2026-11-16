"""PORTAL DESIGNER (CRD-044): designs.lua edited in place, the Designer tab driven as a player would, saved designs in each slot's
PORTAL LOOK list, rename and delete reaching config.lua, the still previews (with a placeholder) and the scale preview's maths.
Run:  python tools\\PortalHubConfig\\tests\\test_designer.py
"""
import csv
import os
import shutil
import struct
import sys
import tempfile
import tkinter as tk
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import PortalHubConfig as gui  # noqa: E402
import hubdata as hd  # noqa: E402
import preview as pv  # noqa: E402
from luaconfig import Design, DesignsFile, HubConfig, Parser, plain  # noqa: E402

ROOT = os.path.join(HERE, "..", "..", "..")
SCRIPTS = os.path.join(ROOT, "mod", "PortalHub", "Scripts")
checks = fails = 0


def check(cond, what, detail=None):
    global checks, fails
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", what, "" if detail is None else "  -> " + repr(detail))


def text(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def designs_of(path):
    """designs.lua as plain Python data, through the parser (a file the hub can read must parse)."""
    return plain(Parser(text(path)).find_return_table())


def png(path, w, h):
    rows = b"".join(b"\x00" + b"\x80\x40\xff" * w for _ in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def model_tests():
    shipped = os.path.join(SCRIPTS, "designs.lua")
    f = DesignsFile(shipped)
    check(f.render() == f.text, "the shipped designs.lua: no edits gives back the same text")
    check(f.names() == ["Cordona Arch", "Big Friendly Red", "Mall Door"], "the shipped examples are read in file order")
    check(not any(d.raw for d in f.designs), "every shipped example is editable")
    raw = open(shipped, "rb").read()
    check(not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw, "the shipped designs.lua has no BOM and LF line ends")

    d = tempfile.mkdtemp()
    p = os.path.join(d, "designs.lua")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('-- my notes\nreturn {\n    -- the arch\n    ["Old Arch"] = { look = "none", ring = "Arch_Con", height = 120, params = { SwirlSpeed = 1 } },\n'
                 '    Plain = { look = "Niagara_Portal_Dark" },\n    Weird = { look = "Niagara_Portal", height = "tall" },\n    count = 3,\n}\n')
    f = DesignsFile(p)
    check(f.names() == ["Old Arch", "Plain", "Weird"], "string-keyed tables are designs; other entries are left alone")
    check(f.get("Old Arch").extras == ["params"], "an unknown field is kept as an extra")
    check(f.get("Weird").raw, "a field the editor can't read makes the design read-only")
    a = f.get("Old Arch")
    a.tint_hex = "#FF8000"
    a.size = [1.2, 2.4]
    a.height = None
    a.name = "New Arch"
    f.get("Weird").name = "Odd"
    f.remove("Plain")
    f.add(Design(name='Quote "Q"', look="Niagara_Portal_Friendly_Blue", scale=[1.5, 1.5, 1.0], hide=["sparks"]))
    f.save()
    out = text(p)
    data = designs_of(p)
    check("-- my notes" in out and "-- the arch" in out, "comments stay")
    check(set(data) == {"New Arch", "Odd", 'Quote "Q"', "count"}, "renamed, removed and added designs land in the file", sorted(data))
    check(data["New Arch"]["tint"] == [1.0, 0.502, 0.0] and data["New Arch"]["size"] == [1.2, 2.4], "edited values written (tint as 0-1 RGB)")
    check("height" not in data["New Arch"], "a height set back to the look's usual is removed")
    check(data["New Arch"]["params"] == {"SwirlSpeed": 1.0}, "an unknown field survives an edit")
    check('Odd = { look = "Niagara_Portal", height = "tall" }' in out, "a read-only design is kept exactly as written, only renamed")
    check(data['Quote "Q"'] == {"look": "Niagara_Portal_Friendly_Blue", "scale": [1.5, 1.5, 1.0], "hide": ["sparks"]}, "a new design is written whole")
    check(os.path.exists(p + ".bak") and not open(p, "rb").read().startswith(b"\xef\xbb\xbf"), "saving keeps a .bak and writes no BOM")
    check(DesignsFile(p).render() == out, "the saved file reads back with nothing left to write")

    with open(p, "wb") as fh:
        fh.write(b"\xef\xbb\xbf" + "return {\r\n    A = { look = \"none\", ring = \"Round_Pri\" },\r\n}\r\n".encode())
    f = DesignsFile(p)
    f.get("A").scene = "TC_H_Cabin"
    f.save()
    out = open(p, "rb").read()
    check(not out.startswith(b"\xef\xbb\xbf") and b"\r\n" in out and b"\n" not in out.replace(b"\r\n", b""), "a CRLF file keeps CRLF; the BOM goes")
    f = DesignsFile(os.path.join(d, "missing.lua"))
    check(f.names() == [] and not f.exists and not f.is_dirty(), "no designs.lua: an empty list, nothing to save")
    f.add(Design(name="First", look="none", ring="Gothic_Ren", size=[1.0, 2.0]))
    f.save()
    check(designs_of(f.path)["First"]["ring"] == "Gothic_Ren", "the first save creates designs.lua")
    nr = Design(name="X", look="Niagara_Portal", ring="", tint_hex="#FF0000", scene="TC_H_Cabin", size=[2, 2])
    vals = DesignsFile.field_values(nr)
    check(vals["tint"] is None and vals["scene"] is None and vals["size"] is None, "ring settings are not written without a ring")


def data_tests():
    rows = {r["look"]: float(r["LuciDin's height cm"]) for r in csv.DictReader(open(os.path.join(ROOT, "docs", "portal-heights.csv"), encoding="utf-8"))}
    check({k: float(v) for k, v in hd.LOOK_HEIGHTS.items()} == rows, "the editor's heights are LuciDin's sheet")
    check(set(hd.LOOK_HEIGHTS) == set(hd.DESIGN_NAMES), "a height for every look in the list")
    check(hd.parse_ring("Arch_Col") == ("geo", "Arch", "Col") and hd.parse_ring("M_Portal_Garden") == ("game", "M_Portal_Garden")
          and hd.parse_ring("Spiral_Big") is None and hd.parse_ring("") is None, "rings are read as Geo, game or nothing")
    check(len([1 for s in hd.GEO_SHAPES for t in hd.GEO_TYPES]) == 24, "24 Geo rings")
    check(hd.ring_takes_scene("Arch_Ren") and not hd.ring_takes_scene("Arch_Con") and not hd.ring_takes_scene("M_Portal_Salem")
          and hd.ring_takes_scene("M_Portal_Garden"), "which rings take a scene")
    check(hd.design_name_problem("") and hd.design_name_problem("/Game/x") and hd.design_name_problem("x" * 41)
          and hd.design_name_problem("ARCH", ["Arch"]) and not hd.design_name_problem("My Arch", ["Arch"]), "name rules")


def preview_tests():
    arch = Design(name="a", look="none", ring="Arch_Col", size=[1.0, 2.0], height=128)
    e = pv.extent(arch)
    check(e.exact and (e.width, e.height, e.centre) == (1.0, 2.0, 1.28), "a ring's outline is its own size at its height")
    check(abs(e.bottom - 0.28) < 1e-9 and abs(e.top - 2.28) < 1e-9, "bottom and top from the centre")
    lay = pv.layout(e, 176, 274, 248, margin=14, top_room=26)
    feet, top, ph = lay.person
    check(abs(ph - lay.scale * 1.76) < 1e-6 and abs(top - (lay.floor - ph)) < 1e-6, "the scientist stands 1.76 m tall at the preview's scale")
    x0, y0, x1, y1 = lay.portal
    check(abs((x1 - x0) - lay.scale * 1.0) < 1e-6 and abs((y1 - y0) - lay.scale * 2.0) < 1e-6, "the portal outline is 1 x 2 m at the same scale")
    check(abs(y1 - (lay.floor - lay.scale * 0.28)) < 1e-6, "the outline starts 0.28 m above the floor")
    check(x0 > feet and y0 >= 26 and lay.floor <= 248, "player left of the portal, both inside the box")
    big = Design(name="b", look="none", ring="Door_Pri", size=[3.5, 6.0], height=350)
    lay2 = pv.layout(pv.extent(big), 176, 274, 248, margin=14, top_room=26)
    check(lay2.scale < lay.scale and lay2.portal[1] >= 26 - 1e-6, "a bigger portal: the scale shrinks so it still fits")
    check(abs(lay2.person[2] / (lay2.portal[3] - lay2.portal[1]) - 1.76 / 6.0) < 1e-6, "player and portal keep their real ratio at any scale")
    auto = Design(name="c", look="none", ring="Door_Pri", size=[1.75, 3.0])
    check(pv.design_height(auto) == 178, "a ring with no look and no height: bottom 28 cm above the pad (as the hub)")
    plain_look = Design(name="d", look="Niagara_Portal_Friendly_Red")
    e = pv.extent(plain_look)
    check(not e.exact and e.centre == 1.08, "a game look: an estimate, at its sheet height")
    scaled = Design(name="e", look="Niagara_Portal_Friendly_Red", scale=[1.0, 2.0, 1.5])
    e2 = pv.extent(scaled)
    check(abs(e2.width - e.width * 2.0) < 1e-9 and abs(e2.height - e.height * 1.5) < 1e-9, "a Friendly look's scale: Y = width, Z = height")
    door = Design(name="f", look="Niagara_Portal_Door", scale=[2, 2, 2])
    check(pv.extent(door).width == hd.look_size("Niagara_Portal_Door")[0], "a look that doesn't scale ignores the scale")
    check("0.97 x" in pv.ratio_text(pv.extent(Design(name="g", look="none", ring="Square_Pri", size=[1, 1.7])), 176), "ratio to the player in words")


def gui_tests():
    d = tempfile.mkdtemp()
    cfg = os.path.join(d, "config.lua")
    with open(cfg, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('return {\n    portals = {\n        { slot = "A-3", name = "Far Garden", destination = "anteverse_a_start", design = "Cordona Arch" },\n'
                 '        { slot = "A-4", name = "The Train", destination = "train_start", exits = "game" },\n    },\n}\n')
    shutil.copy(os.path.join(SCRIPTS, "designs.lua"), os.path.join(d, "designs.lua"))
    shutil.copy(os.path.join(SCRIPTS, "manual_exits.lua"), os.path.join(d, "manual_exits.lua"))
    prev = os.path.join(d, "previews")
    os.makedirs(prev)
    png(os.path.join(prev, "Geo_Arch_Col.png"), 600, 300)
    gui.PREVIEW_DIRS = [prev]
    root = tk.Tk()
    root.withdraw()
    answers, texts = [], []
    gui.ask = lambda *a, **k: answers.pop(0)
    gui.ask_text = lambda parent, title, msg, initial, chk: (lambda t: t if t is not None and not chk(t) else None)(texts.pop(0))   # a refused name = cancelled
    gui.remember_config = lambda p: None
    app = gui.App(root, cfg)
    root.update()
    designs_file = os.path.join(d, "designs.lua")
    before = text(designs_file)

    check(not app.is_dirty(), "starts clean")
    app.show_tab("designer")
    root.update()
    check(app.design_sel == "Cordona Arch" and app.d_title.cget("text") == "Cordona Arch", "the designer opens on the first design")
    check("A-3" in app.d_used.cget("text"), "it says which slots use the design")
    check(app.tab_btns["designer"].cget("text") == "PORTAL DESIGNER  3", "the tab shows how many designs there are")

    # the slot's look list offers the saved designs
    app.show_tab("room")
    app.select("A-4")
    items = app.look_items()
    vals = [v for _, _, v in items if v is not None]
    check(all(n in vals for n in ("Cordona Arch", "Big Friendly Red", "Mall Door")), "each saved design is in the PORTAL LOOK list")
    check(hd.DEFAULT_DESIGN in vals and vals.index(hd.DEFAULT_DESIGN) < vals.index("Cordona Arch"), "the game's looks stay, listed first")
    app.pick_look("Mall Door")
    check(app.cfg.portals["A-4"].design == "Mall Door" and "your design" in app.look.label.cget("text"), "a slot takes a design by name")
    app.select("A-3")
    check(app.look.label.cget("text").startswith("Cordona Arch"), "a slot that uses a design shows its name")
    check(app.fx.cget("text") == "IN DESIGNER", "EFFECTS points to the designer for a design")

    # build a new design
    app.show_tab("designer")
    app.d_new()
    check(app.design_sel == "New design" and app.designs.get("New design") is not None, "NEW makes 'New design'")
    app.d_new()
    check(app.design_sel == "New design 2", "a second NEW gets a free name")
    app.d_pick_ring("Gothic_Ren")
    dsg = app.design()
    check(dsg.ring == "Gothic_Ren" and dsg.size == [1.0, 2.0], "picking a Geo ring sets its shape's size")
    app.d_pick_look("none")
    app.d_size_set(1, 2.6)
    app.d_pick_tint("#2EE65C")
    app.d_pick_scene("TC_Portal_Alps")
    app.d_height_set(160)
    app.d_mhe_toggle()
    app.d_mhe_set(140)
    check(dsg.size == [1.0, 2.6] and dsg.tint_hex == "#2EE65C" and dsg.scene == "TC_Portal_Alps" and dsg.height == 160 and dsg.mhe_height == 140,
          "size, colour, scene, height and MHE height are set")
    app.d_pick_ring("Gothic_Con")
    check(dsg.scene == "", "a ring with no scene clears the scene")
    check(dsg.size == [1.0, 2.6], "another type of the same shape keeps the size")
    app.d_pick_ring("Round_Con")
    check(dsg.size == [1.8, 1.8], "another shape starts at its own size")
    app.d_pick_ring("Gothic_Con")
    app.d_size_set(1, 2.6)
    check(app.d_scene.enabled is False, "... and the scene list is off for it")
    app.d_pick_look("Niagara_Portal_Friendly_Lime")
    app.d_scale_set(1, 1.4)
    check(dsg.scale == [1.0, 1.4, 1.0], "a Friendly look takes a scale")
    app.d_pick_look("Niagara_Portal_Door")
    check(dsg.scale is None and app.d_scale[0].field.entry.cget("state") == "disabled", "a look that doesn't scale drops the scale; its boxes are off")

    # duplicate, rename (portals follow), delete (with a confirm; users fall back to its look)
    app.d_pick("Cordona Arch")
    app.d_duplicate()
    check(app.design_sel == "Cordona Arch copy" and app.design().ring == "Arch_Col", "DUPLICATE copies the design under a new name")
    app.d_pick("Cordona Arch")
    texts.append("Big Friendly Red")
    app.d_rename()
    check(app.design_sel == "Cordona Arch", "renaming to a taken name is refused")
    texts.append("Purple Arch")
    app.d_rename()
    check(app.designs.get("Purple Arch") is not None and app.designs.get("Cordona Arch") is None, "RENAME renames the design")
    check(app.cfg.portals["A-3"].design == "Purple Arch", "the portal that used the old name follows the new one")
    answers.append(0)
    app.d_pick("Mall Door")
    app.d_delete()
    check(app.designs.get("Mall Door") is not None, "DELETE asks first; cancel keeps it")
    answers.append(1)
    app.d_delete()
    check(app.designs.get("Mall Door") is None, "DELETE removes the design after the confirm")
    check(app.cfg.portals["A-4"].design == hd.DEFAULT_DESIGN, "a portal that used it falls back to its look (none here: the default look)")

    # preview panel
    app.d_pick("Purple Arch")
    root.update()
    check(app.preview_file(app.design()).endswith("Geo_Arch_Col.png"), "the still is the ring's picture from the previews folder")
    check(any(app.d_still.type(i) == "image" for i in app.d_still.find_all()), "the still is drawn")
    img = next(iter(app.d_images.values()))
    check(img.width() <= gui.px(274) and img.height() <= gui.px(132), "the still is shrunk to fit its box, keeping its shape")
    app.d_pick("Big Friendly Red")
    root.update()
    check(not any(app.d_still.type(i) == "image" for i in app.d_still.find_all()) and "Niagara_Portal_Friendly_Red.png" in app.d_still_note.cget("text"),
          "a missing still: a placeholder naming the file it looked for")
    app.d_pick("Purple Arch")
    root.update()
    n_before = len(app.d_scale_cv.find_all())
    app.d_size_set(1, 3.0)
    root.update()
    lay = pv.layout(pv.extent(app.design()), hd.PLAYER_HEIGHT_CM, gui.px(274), gui.px(248), margin=gui.px(14), top_room=gui.px(26))
    check("1.00 x 3.00 m" in app.d_scale_txt.cget("text") and len(app.d_scale_cv.find_all()) > 10 and n_before > 10,
          "the scale preview redraws with the new size")
    check("player 1.76 m" in [app.d_scale_cv.itemcget(i, "text") for i in app.d_scale_cv.find_all() if app.d_scale_cv.type(i) == "text"],
          "the scale preview names the player's height")

    # save writes both files; the hub's format
    check(app.is_dirty(), "edits make the editor dirty")
    app.save()
    data = designs_of(designs_file)
    check(set(data) == {"Purple Arch", "Big Friendly Red", "New design", "New design 2", "Cordona Arch copy"}, "designs.lua saved", sorted(data))
    nd2 = data["New design 2"]
    check(nd2 == {"look": "Niagara_Portal_Door", "ring": "Gothic_Con", "size": [1.0, 2.6], "tint": [0.18, 0.902, 0.361], "height": 160.0, "mheHeight": 140.0},
          "a new design is written in the hub's format", nd2)
    check(data["Purple Arch"]["size"] == [1.0, 3.0], "an edited design is written")
    conf = text(cfg)
    check('design = "Purple Arch"' in conf and "Mall Door" not in conf, "config.lua follows the rename and the delete")
    check("-- Portal Hub: saved portal designs." in text(designs_file), "the file's comments stay")
    check(not app.is_dirty(), "after saving, nothing is left to save")
    check(before != text(designs_file) and os.path.exists(designs_file + ".bak"), "the old designs.lua is kept as .bak")

    # a designs.lua that can't be read is never written
    with open(designs_file, "w", encoding="utf-8") as fh:
        fh.write("return { broken = ")
    app.do_reload()
    check(app.designs_problem and not app.d_new_btn.enabled, "an unreadable designs.lua: a warning, and the designer is read-only")
    app.save()
    check(text(designs_file) == "return { broken = ", "... and saving leaves it exactly as it was")
    root.destroy()


def main():
    model_tests()
    data_tests()
    preview_tests()
    gui_tests()
    print(f"{checks} checks, {fails} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
