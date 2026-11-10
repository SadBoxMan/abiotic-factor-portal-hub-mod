"""Tests for luaconfig.py. Run:  python tools\\PortalHubConfig\\tests\\test_luaconfig.py [path to a live config.lua]

Every edit is also loaded by real Lua when lupa is available (pip install --target %TEMP%\\pylib lupa), so the writer is
checked against the language and not only against this project's own parser.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
from hubdata import DEFAULT_DESIGN, design_path  # noqa: E402
from luaconfig import HubConfig, LuaError, Parser, World, Portal, read_manual_exits  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TEMPLATE = os.path.join(REPO, "mod", "PortalHub", "Scripts", "config.lua")
try:
    import lupa
    LUA = lupa.LuaRuntime()
except Exception:
    LUA = None

checks = 0
fails = 0


def check(cond, what):
    global checks, fails
    checks += 1
    if not cond:
        fails += 1
        print("FAIL:", what)


def lua(text):
    """The config as Lua itself reads it, as nested Python data."""
    if LUA is None:
        return None

    def conv(v):
        if type(v).__name__ == "_LuaTable":
            keys = list(v.keys())
            if keys and all(isinstance(k, int) for k in keys):
                return [conv(v[k]) for k in sorted(keys)]
            return {k: conv(v[k]) for k in keys}
        return v
    return conv(LUA.execute(text))


SAMPLE = '''-- header comment
local unused = "return { not this one }"

return {
    humMode = "manual",   -- mode comment
    humFloor = 0.15,    -- dynamic
    humManual = 0.5,
    tracker = false,      -- a key the editor has never heard of

    hideEmitters = {
        -- a note
        ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "smoke", "Swirl" },
    },

    worlds = {
        plain_start = {
            loaderAsset = "/Game/Mods/P/BP_P",
            loaderClass = "BP_P_C",
            level       = "/Game/Mods/P/Maps/P_L0",
            origin      = { 1000000, 1200000, 0 },
        },
        -- note about tuned
        tuned_start = { loaderAsset = "/Game/Mods/T/BP_T", loaderClass = "BP_T_C",
            level = "/Game/Mods/T/Maps/T_L0", origin = { 1400000, 1300000, 0 }, arrive = { 1, 2, 3 }, killZ = -3000 },  -- trailing
        odd_start = { loaderAsset = "/x", loaderClass = "x_C", level = "/x", origin = { 1000 * 2, 0, 0 } },
    },

    portals = {
        { slot = "A-3", name = "One", destination = "signal_start", title = "keep me" },  -- keep this note
        { slot = "A-4", name = "Two", destination = "train_start", design = "/Game/Particles/Niagara_Portal_Fog.Niagara_Portal_Fog", lightColor = { 0.2, 0.9, 0.4 }, lightBrightness = 2 },
        { slot = "C-1", name = 'single "quoted"', destination = "x" },
    },
}
'''


def round_trip_same(text, label):
    c = HubConfig(text=text)
    check(c.render() == text, f"{label}: no edits gives the same text")
    check(not c.is_dirty(), f"{label}: not dirty")


def edited(fn, text=SAMPLE):
    c = HubConfig(text=text)
    fn(c)
    out = c.render()
    Parser(out).find_return_table()
    if LUA is not None:
        lua(out)
    return c, out


def test_reading():
    c = HubConfig(text=SAMPLE)
    check(c.hum_mode == "manual" and c.hum_floor == 15 and c.hum_manual == 50, "hum values")
    check(list(c.hide.values()) == [["smoke", "Swirl"]], "hide map")
    w = {x.id: x for x in c.worlds}
    check(w["plain_start"].arrive is None and not w["plain_start"].raw, "arrive is optional")
    check(w["tuned_start"].arrive == [1, 2, 3, 0] and w["tuned_start"].extras == ["killZ"], "extras are seen, 3-value arrive padded")
    check(w["odd_start"].raw, "an expression in a known field makes the entry read-only")
    check(c.portals["A-3"].extras == ["title"], "unknown portal field noticed")
    check(c.portals["A-4"].light_hex == "#33E666" and c.portals["A-4"].brightness == 2, "light")
    check(c.portals["C-1"].name == 'single "quoted"' and c.portals["C-1"].design == DEFAULT_DESIGN, "single-quoted strings")


def test_edits():
    def hum(c):
        c.hum_mode = "dynamic"
        c.hum_manual = 33
    c, out = edited(hum)
    check('humMode = "dynamic",   -- mode comment' in out and "humManual = 0.33," in out, "hum edited in place")
    check(out.count("\n") == SAMPLE.count("\n"), "hum edit changes no lines")

    def name(c):
        c.portals["A-3"].name = 'New "name"'
    c, out = edited(name)
    check('title = "keep me" },  -- keep this note' in out and 'name = "New \\"name\\""' in out, "unknown field and note survive a rename")

    def light(c):
        p = c.portals["A-4"]
        p.light_hex = ""
        p.brightness = 1.0
        p.design = DEFAULT_DESIGN
    c, out = edited(light)
    check("lightColor" not in out and "lightBrightness" not in out and "design" not in out.split("portals = {")[1], "removing fields")
    check('destination = "train_start" },' in out, "no stray comma after removing the tail fields")

    def add_light(c):
        c.portals["A-3"].light_hex = "#FF2020"
        c.portals["A-3"].brightness = 2.5
    c, out = edited(add_light)
    check('title = "keep me", lightColor = { 1, 0.125, 0.125 }, lightBrightness = 2.5 },' in out, "adding fields to one-line entry")

    def off(c):
        c.portals["A-4"].enabled = False
    c, out = edited(off)
    check('"A-4"' not in out and "keep this note" in out, "removing a portal takes its line only")

    def add(c):
        c.portals["B-1"] = Portal(slot="B-1", name="Fog", destination="fog_start", design=design_path("Niagara_Portal_Fog"))
        c.portals["C-4"] = Portal(slot="C-4", name="Last", destination="z")
    c, out = edited(add)
    check(out.index('"A-4"') < out.index('"B-1"') < out.index('"C-1"') < out.index('"C-4"'), "new portals go in slot order")

    def world(c):
        w = {x.id: x for x in c.worlds}
        w["tuned_start"].origin = [5, 6, 7]
        w["tuned_start"].arrive = None
        w["tuned_start"].id = "renamed_start"
        w["plain_start"].arrive = [1, 2, 3, 4]
    c, out = edited(world)
    check("killZ = -3000 },  -- trailing" in out and "renamed_start = {" in out and "origin = { 5, 6, 7 }" in out, "world edited, its extras kept")
    check("arrive = { 1, 2, 3 }" not in out and "arrive = { 1, 2, 3, 4 }," in out, "arrive removed and added")
    check("-- note about tuned" in out, "comment in worlds kept")
    if LUA is not None:
        t = lua(out)
        check(t["worlds"]["renamed_start"]["killZ"] == -3000 and "arrive" not in t["worlds"]["renamed_start"], "real Lua agrees")

    def newworld(c):
        c.worlds.append(World(id="new_start", asset="/Game/N/BP_N", cls="BP_N_C", level="/Game/N/L", origin=[1, 2, 3]))
        c.worlds = [w for w in c.worlds if w.id != "plain_start"]
    c, out = edited(newworld)
    check("plain_start" not in out and "new_start = {" in out and "arrive" not in out.split("new_start = {")[1].split("}")[0], "world added without arrive, another removed")

    def hide(c):
        c.hide.clear()
        c.hide[design_path("Niagara_Portal_Rift")] = ["smoke"]
    c, out = edited(hide)
    check("-- a note" in out and "SnowFlurry" not in out.split("hideEmitters = {")[1].split("worlds = {")[0], "hide block keeps its comment")
    check('["/Game/Particles/Niagara_Portal_Rift.Niagara_Portal_Rift"] = { "smoke" },' in out, "hide entry added")


EXITS = '''return {
    exitMode = 3,    -- a number works too
    mhe = { train_start = false, ["anteverse_a_start"] = true },
    hubExits = { train_start = { { 1, 2, 3, 4 } } },    -- the old CRD-013 field: no longer edited, kept as written
    portals = {
        { slot = "A-3", name = "One", destination = "signal_start", exits = 4, manualBuffs = true, title = "keep me" },
        { slot = "A-4", name = "Two", destination = "train_start", exits = "HUB" },
        { slot = "B-1", name = "Odd", destination = "fog_start", exits = "sideways" },
    },
}
'''


def template():
    with open(TEMPLATE, encoding="utf-8", newline="") as f:
        return f.read()


def test_exit_modes():
    c = HubConfig(text=EXITS)
    check(c.exit_mode == "dynamic", "exitMode as a number")
    check(c.portals["A-3"].exits == "manual" and c.portals["A-3"].manual_buffs is True, "exits 4 and manualBuffs read")
    check(c.portals["A-4"].exits == "hub", "exits in capitals read")
    check(c.portals["B-1"].exits == "" and c.portals["B-1"].extras == ["exits"], "an unknown exits value is kept as written")
    check(c.portals["A-3"].extras == ["title"], "exits and manualBuffs are known fields")
    round_trip_same(EXITS, "exits")
    check(HubConfig(text='return { exitMode = "manual" }').exit_mode == "game", "manual is refused as the global mode")

    def edit(c):
        c.exit_mode = "hub"
        c.portals["A-3"].exits = ""
        c.portals["A-3"].manual_buffs = False
        c.portals["A-4"].exits = "manual"
        c.portals["A-4"].manual_buffs = True
        c.portals["C-1"] = Portal(slot="C-1", name="New", destination="alps_start", exits="dynamic")
    c, out = edited(edit, EXITS)
    check('exitMode = "hub",    -- a number works too' in out, "exitMode edited in place, comment kept")
    check('{ slot = "A-3", name = "One", destination = "signal_start", title = "keep me" },' in out, "exits and manualBuffs removed")
    check('exits = "manual", manualBuffs = true }' in out.split('"A-4"')[1].split("\n")[0], "exits set and manualBuffs added")
    check('{ slot = "C-1", name = "New", destination = "alps_start", exits = "dynamic" },' in out, "new portal with its exit mode")
    check("hubExits = { train_start = { { 1, 2, 3, 4 } } }," in out, "the old hubExits field is left alone")
    if LUA is not None:
        t = lua(out)
        check(t["exitMode"] == "hub" and t["portals"][1]["exits"] == "manual" and t["portals"][1]["manualBuffs"] is True, "real Lua agrees")
    c2 = HubConfig(text=out)
    check(c2.portals["A-4"].exits == "manual" and c2.render() == out, "exit modes read back and round trip")

    # the shipped template has  -- exitMode = "game",  commented out: the real line takes its place
    def on(c):
        c.exit_mode = "dynamic"
    c, out = edited(on, template())
    check('    exitMode = "dynamic",\n' in out and '-- exitMode' not in out, "exitMode written over its commented-out line")
    check(out.count("\n") == template().count("\n"), "no lines added")
    c, out = edited(lambda c: setattr(c, "exit_mode", "game"), template())
    check(out == template(), "the default mode on a file without exitMode writes nothing")
    c, out = edited(on, SAMPLE)
    check(out.index('exitMode = "dynamic",') < out.index("portals = {"), "exitMode added above portals when there is no commented line")


def test_mhe():
    # the template has  -- mhe = {},  commented out
    def off(c):
        c.mhe_off.update({"train_start", "anteverse_a_start"})
    c, out = edited(off, template())
    check('    mhe = { anteverse_a_start = false, train_start = false },\n' in out and "-- mhe = {}" not in out, "mhe written over its commented-out line")
    if LUA is not None:
        check(lua(out)["mhe"] == {"anteverse_a_start": False, "train_start": False}, "real Lua reads mhe")
    c2 = HubConfig(text=out)
    check(c2.mhe_off == {"train_start", "anteverse_a_start"} and c2.render() == out, "mhe read back")
    c2.mhe_off.discard("train_start")
    out2 = c2.render()
    check("mhe = { anteverse_a_start = false }," in out2, "an MHE switched back on leaves the list")
    c3 = HubConfig(text=out2)
    c3.mhe_off.clear()
    out3 = c3.render()
    Parser(out3).find_return_table()
    check("anteverse_a_start" not in out3 and HubConfig(text=out3).mhe_off == set(), "all on: nothing left switched off")
    c, out = edited(lambda c: None, template())
    check(out == template(), "no MHE change writes nothing")

    # an existing block: = true flips, a new key is added, a false one removed
    def edit(c):
        c.mhe_off.discard("train_start")
        c.mhe_off.update({"anteverse_a_start", "fog_start"})
    c, out = edited(edit, EXITS)
    check('mhe = { ["anteverse_a_start"] = false, fog_start = false },' in out, "mhe block edited: " + out.split("\n")[2])
    check(HubConfig(text=out).mhe_off == {"anteverse_a_start", "fog_start"}, "mhe edits read back")


def test_wipe():
    c = HubConfig(text=EXITS)
    c.wipe_portal("A-3")
    p = c.portals["A-3"]
    check(not p.enabled and p.destination == "" and p.exits == "" and not p.manual_buffs and p.extras == [], "wiped slot holds nothing")
    out = c.render()
    check('"A-3"' not in out and "keep me" not in out, "a wiped slot left off is removed from the file")
    p.enabled = True                       # turned on again, a new world picked
    p.destination, p.name = "train_start", "The Train"
    out = c.render()
    check('{ slot = "A-3", name = "The Train", destination = "train_start" },' in out, "turned on again: written anew, no leftovers")
    check("signal_start" not in out and "manualBuffs" not in out.split('"A-3"')[1].split("\n")[0], "nothing of the old world kept")
    if LUA is not None:
        t = lua(out)
        check(t["portals"][0] == {"slot": "A-3", "name": "The Train", "destination": "train_start"}, "real Lua sees only the new entry")
    c.portals["C-4"] = Portal(slot="C-4", destination="x")
    c.wipe_portal("C-4")
    check("C-4" not in c.portals, "a portal never saved is simply dropped")
    c.wipe_portal("C-3")                   # an empty slot: nothing to do
    check("C-3" not in c.portals, "wiping an empty slot is harmless")


def test_manual_exits_file():
    real = os.path.join(REPO, "mod", "PortalHub", "Scripts", "manual_exits.lua")
    spots, failsafe, problem = read_manual_exits(real)
    check(problem == "" and "train_start" in spots and "failsafe" not in spots and failsafe is not None and len(failsafe) == 4,
          "the repo's manual_exits.lua is read")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "manual_exits.lua")
        with open(p, "w", encoding="utf-8") as f:
            f.write('return {\n    a_start = { 1, 2, 3 },\n    bad = { 1, "x", 3, 4 },\n    expr = { 1 * 2, 0, 0, 0 },\n    H_Cabin_Start = { 4, 5, 6, 90 },\n}\n')
        spots, failsafe, problem = read_manual_exits(p)
        check(spots == {"a_start": [1, 2, 3, 0], "H_Cabin_Start": [4, 5, 6, 90]} and failsafe is None and problem == "",
              "bad spots skipped, a 3-value spot padded")
        with open(p, "w", encoding="utf-8") as f:
            f.write("return {")
        check(read_manual_exits(p)[2].startswith("manual_exits.lua can't be read"), "an unreadable file is reported")
        check(read_manual_exits(os.path.join(d, "none.lua"))[2] != "", "a missing file is reported")


def test_bad_input():
    for bad in ("", "x = 1", "return 5", "return {", 'return { a = "unfinished }'):
        try:
            HubConfig(text=bad)
            check(False, f"should refuse {bad!r}")
        except LuaError:
            check(True, "refused")
    c = HubConfig(text="return {}\n")
    c.portals["A-3"] = Portal(slot="A-3", name="x", destination="y", exits="hub")
    c.exit_mode = "dynamic"
    c.mhe_off.add("y")
    out = c.render()
    if LUA is not None:
        t = lua(out)
        check(t["portals"][0]["slot"] == "A-3" and t["portals"][0]["exits"] == "hub" and t["exitMode"] == "dynamic"
              and t["mhe"]["y"] is False, "blocks added to an empty table")
    check(HubConfig(text=out).portals["A-3"].destination == "y", "reads back")
    # hand-written layouts the editor can't model stay as written
    odd = 'return {\n    hideEmitters = { [k] = 1 },\n    mhe = { "b" },\n    worlds = { 1, 2 },\n    portals = {},\n}\n'
    c = HubConfig(text=odd)
    check(not c.worlds_editable and not c.mhe_editable, "odd blocks are read-only")
    c.mhe_off.add("x")
    check(c.render() == odd, "a read-only mhe is never written")
    c.mhe_off.clear()
    round_trip_same(odd, "odd")


def test_crlf_and_bom():
    text = SAMPLE.replace("\n", "\r\n")
    round_trip_same(text, "crlf")
    def add(c):
        c.portals["B-1"] = Portal(slot="B-1", name="Fog", destination="fog_start", exits="manual", manual_buffs=True)
        c.exit_mode = "hub"
        c.mhe_off.add("fog_start")
    c, out = edited(add, text)
    check(out.count("\n") == out.count("\r\n"), "new lines follow the file's CRLF")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.lua")
        with open(p, "wb") as f:
            f.write(b"\xef\xbb\xbf" + "return {\n    humMode = \"manual\",\n}\n".encode("utf-8"))
        c = HubConfig(p)
        c.hum_mode = "default"
        check(not c.changed_on_disk(), "the BOM alone is not an outside change")
        c.save()
        with open(p, "rb") as f:
            raw = f.read()
        check(not raw.startswith(b"\xef\xbb\xbf") and b'"default"' in raw, "saved with no BOM")
        check(os.path.exists(p + ".bak"), "backup kept")
        check(not os.path.exists(p + ".tmp"), "no temp file left")
        with open(p, "ab") as f:
            f.write(b"-- edited by hand\n")
        check(c.changed_on_disk(), "notices an outside edit")


def test_live(path):
    with open(path, "rb") as f:
        raw = f.read()
    check(not raw.startswith(b"\xef\xbb\xbf"), "live config has no BOM")
    text = raw.decode("utf-8")
    round_trip_same(text, "live")
    c = HubConfig(text=text)
    print(f"live: {len(c.portals)} portals, {len(c.worlds)} worlds, editable worlds: {sum(not w.raw for w in c.worlds)}")
    if LUA is not None:
        c.hum_mode = "dynamic" if c.hum_mode != "dynamic" else "manual"
        before, after = lua(text), lua(c.render())
        before.pop("humMode"), after.pop("humMode")
        check(before == after, "live: a hum edit changes nothing else, by real Lua")


if __name__ == "__main__":
    test_reading()
    test_edits()
    test_exit_modes()
    test_mhe()
    test_wipe()
    test_manual_exits_file()
    test_bad_input()
    test_crlf_and_bom()
    round_trip_same(SAMPLE, "sample")
    round_trip_same(open(TEMPLATE, encoding="utf-8", newline="").read(), "template")
    if len(sys.argv) > 1:
        test_live(sys.argv[1])
    print(f"{checks} checks, {fails} failed" + ("" if LUA else " (no lupa: real-Lua checks skipped)"))
    sys.exit(1 if fails else 0)
