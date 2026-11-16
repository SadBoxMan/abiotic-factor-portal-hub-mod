# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game and checks CRD-043: our own cooked "Geo" portals
# (PortalHubLooks_P, World Projects/PortalHubLooks): in mesh mode Shift + SCROLL LOCK puts the next of 12 Geo rings (6 shapes x swirl /
# window) on the built shape, as the engine plane stood up as square C, at that shape's starting size (gathered with the plain SCROLL
# LOCK that fires with it); loading from our pak is named first and falls back to GetAsset by name when LoadAsset finds nothing; a
# missing pak is said, not crashed on; the tint also covers DistortionEdge where it reads; PAUSE (mesh mode) hides / shows the pad's
# own look and Shift + U shows it again; the ring faces the pad's own angle; Shift + M / N scale in fine steps.
# Also cross-checks the lab against the material's build script: same instance names and folder, chunk 120, the parameters the lab
# sets, true backside and clockwise swirl by default.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")
BUILD = os.path.join(ROOT, "World Projects", "PortalHubLooks", "Scripts", "build_ring_material.py")
GAME_INI = os.path.join(ROOT, "World Projects", "PortalHubLooks", "Config", "DefaultGame.ini")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)
LOOKS_MOCK = re.search(r'LOOKS = r"""(.*?)"""', open(os.path.join(S, "test_lab_looks.py"), encoding="utf-8").read(), re.S).group(1)
PADS = re.search(r'PADS = r"""(.*?)"""', open(os.path.join(S, "test_lab_scale_facing_tint.py"), encoding="utf-8").read(), re.S).group(1)

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def lab():
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute(open(LAB, encoding="utf-8").read())
    L.execute(LOOKS_MOCK)
    L.execute(PADS)
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def calls(L):
    g = L.globals()
    return [g.CALLS2[i] for i in range(1, len(g.CALLS2) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


def press(L, key):
    L.execute("KEYS['%s'](); pump()" % key)


def shift_sl(L):
    L.execute("KEYS['SCROLL_LOCK+SHIFT'](); KEYS['SCROLL_LOCK'](); pump()")   # UE4SS fires the plain bind with the Shift one


def mesh_built(L, steps=3):
    L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
    for _ in range(3):
        press(L, "OEM_FOUR")
    for _ in range(steps):
        press(L, "SCROLL_LOCK")


src = open(LAB, encoding="utf-8").read()
build = open(BUILD, encoding="utf-8").read()
SHAPES_SRC = re.findall(r'\{ "(\w+)", ([\d.]+), ([\d.]+) \}', re.search(r"^LK\.GEO_SHAPES = \{(.*)\}$", src, re.M).group(1))
TYPES_SRC = re.findall(r'"(\w+)"', re.search(r"^LK\.GEO_TYPES = \{(.*)\}$", src, re.M).group(1))
NAMES = ["MI_Geo%s_%s" % (s, t) for s, _, _ in SHAPES_SRC for t in TYPES_SRC]   # the lab's loop: shape by shape, each type

print("=== Geo list and keys")
shapes = ["Arch", "Gothic", "Square", "Door", "Round", "Oval"]
types = ["Con", "Col", "Ren", "Pri"]
check("6 shapes in LuciDin's order", [s for s, _, _ in SHAPES_SRC] == shapes, SHAPES_SRC)
check("4 types from opaque to clear: Conchoidal, Colloform, Reniform, Prismatic (LuciDin)", TYPES_SRC == types, TYPES_SRC)
check("the lab builds its list shape by shape, each type, as MI_Geo<Shape>_<Type> (LuciDin: Arch_Col)",
      'local name = "MI_Geo" .. s[1] .. "_" .. t' in src and "for _, s in ipairs(LK.GEO_SHAPES) do" in src and "for _, t in ipairs(LK.GEO_TYPES) do" in src)
sizes = {s: (float(w), float(h)) for s, w, h in SHAPES_SRC}
check("starting sizes: square 1 x 1 m, door 1.75 x 3 m (LuciDin)", sizes["Square"] == (1.0, 1.0) and sizes["Door"] == (1.75, 3.0), sizes)
check("the plain ring list is the game's again (no own ring in it)", "PortalHubLooks" not in re.search(r"^LK\.TINT_RINGS = \{(.*?)\}", src, re.S | re.M).group(1))
check("Shift + SCROLL LOCK bound to LK.shift_scroll", re.search(r"RegisterKeyBind\(Key\.SCROLL_LOCK, \{ ModifierKey\.SHIFT \}, function\(\) ExecuteInGameThread\(LK\.shift_scroll\)", src))
check("plain SCROLL LOCK still bound to LK.make_mid", re.search(r"RegisterKeyBind\(Key\.SCROLL_LOCK, function\(\) ExecuteInGameThread\(LK\.make_mid\)", src))
others = "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey"))
check("no other mod of ours binds SCROLL LOCK", "Key.SCROLL_LOCK" not in others)
check("no bare ExecuteWithDelay added", src.count("ExecuteWithDelay(") == 1)
block = src[src.index("-- Our own \"Geo\" portals (CRD-043"):src.index("-- Mode switch:")]
check("no main-chunk local in the CRD-043 block", not re.search(r"^local ", block, re.M))
check("square C is still a shape: engine Plane, roll +90, yaw +90",
      re.search(r'name = "square C \(roll \+90, yaw \+90\)", path = "/Engine/BasicShapes/Plane\.Plane", pitch = 0, yaw = 90, roll = 90', src))
check("DistortionEdge (the arch's fringe) is one of the tint colours", re.search(r'LK\.TINT_PARAMS = \{ "PortalCenterColor", "PortalCenterColor2", "PortalEdge", "DistortionEdge" \}', src))

print("=== lab and material build script agree")
geo_dir = re.search(r'^GEO_DIR = BASE \+ "([^"]+)"', build, re.M).group(1)
base = re.search(r'^BASE = "([^"]+)"', build, re.M).group(1)
lab_dir = re.search(r'LK\.RING_PATHS\[name\] = "([^"]+)" \.\. name', src).group(1)
check("lab folder = the script's instance folder (" + base + geo_dir + ")", lab_dir == base + geo_dir + "/", lab_dir)
sh = re.findall(r'\("(\w+)", ([\d.]+)\)', re.search(r"^SHAPES = \[(.*?)\]$", build, re.M).group(1))
st = re.findall(r'"(\w+)": \{', re.search(r"^STYLES = \{(.*?)^\}", build, re.M | re.S).group(1))
script_names = ["MI_Geo%s_%s" % (a, b) for a, _ in sh for b in st]   # the script's loop: name = "MI_Geo" + shape + "_" + style
check("the script names its instances MI_Geo<Shape>_<Type>", 'name = "MI_Geo" + shape + "_" + style' in build)
check("the script makes exactly the lab's 24 instances", script_names == NAMES and len(NAMES) == 24, script_names)
check("the script clears the whole Geo folder first (the first 12 names go)", "eal.list_assets(GEO_DIR, recursive=True, include_folder=False)" in build)
shape_val = {a: float(v) for a, v in sh}
check("shape values: arch 0, gothic 1, square = door = 2 (rectangle), round 3, oval 4",
      shape_val == {"Arch": 0.0, "Gothic": 1.0, "Square": 2.0, "Door": 2.0, "Round": 3.0, "Oval": 4.0}, shape_val)
check("Con: no scene (opaque swirl)", re.search(r'"Con": \{"SceneMix": 0\.0\}', build))
check("Col: the master's defaults (swirl over a faint scene)", re.search(r'"Col": \{\}', build))
check("Ren: scene, the swirl only ripples it", re.search(r'"Ren": \{"SceneMix": 1\.0, "SwirlOverScene": 0\.0, "DistortMultiply": 0\.03', build))
check("Pri: scene, no ripple at all (clearest)", re.search(r'"Pri": \{"SceneMix": 1\.0, "SwirlOverScene": 0\.0, "DistortMultiply": 0\.0, "DistortDistance": 0\.0\}', build))
check("label chunk 120 in the build script", re.search(r"^CHUNK = 120$", build, re.M))
check("the project cooks its own folder", '+DirectoriesToAlwaysCook=(Path="%s")' % base in open(GAME_INI, encoding="utf-8").read())
params = {p for p in re.findall(r'\(\s*"\w+",\s*"([^"]+)",', build)}
for p in ("PortalCenterColor", "PortalCenterColor2", "PortalEdge", "DistortionEdge", "Shape", "Pointed", "TrueBack"):
    check("material has " + p, p in params, sorted(params))
check("material has a PortalTexture texture parameter", '"parameter_name", "PortalTexture"' in build)
check("true backside by default (TrueBack 1.0)", re.search(r'\("TrueBack",\s*"TrueBack",\s*1\.0\)', build))
check("front = the side facing out from the pad on square C (FlipFront 1.0: the plane's back side; LuciDin at Dunkel Forest's MHE)",
      re.search(r'\("FlipFront",\s*"FlipFront",\s*1\.0\)', build) and "(FlipFront > 0.5 ? -1.0 : 1.0)" in build)
check("swirl turns clockwise from the front (angle minus time x speed, y down)", "atan2(pn.y, pn.x) - t * SwirlSpeed" in build)
check("scene as a window into a sphere by default (SceneParallax 1.0, SphereDepth / SphereRadius; LuciDin: like the Door look)",
      re.search(r'\("Parallax",\s*"SceneParallax",\s*1\.0\)', build) and "SphereDepth" in params and "SphereRadius" in params
      and "hit - ctr" in build)
check("the eye comes from the surface's own axes, not a tangent-space convention", "float3 e = -P;" in build and "dot(e, Tu) * fx" in build)
check("from the back the scene's other half shows (eye and sphere flip with the side; LuciDin: as the Door does)",
      "float sg = (TrueBack > 0.5 && frontSide < 0.0) ? -1.0 : 1.0;" in build and "SphereDepth * sg" in build)
check("material: two-sided, masked, unlit, Niagara sprite usage", all(x in build for x in ('"two_sided", True', "BLEND_MASKED", "MSM_UNLIT", '"used_with_niagara_sprites", True')))
check("shape size read from the surface (pixel derivatives of the camera-relative position)", "ddx(P)" in build and "WPT_CAMERA_RELATIVE" in build)
check("no game texture paths in the graph except the dummy's own path", re.findall(r'"/Game/Particles/[^"]*"', build) == ['"/Game/Particles/RenderTargets"'], re.findall(r'"/Game/Particles/[^"]*"', build))

print("=== mesh mode: Shift + SCROLL LOCK steps through the Geo rings")
L = lab()
mesh_built(L, steps=2)
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("before the shape is on (step 2): asks for the build, no call", has(L, "Geo ring: build the shape first") and calls(L)[-1] == "collision 0", calls(L)[-2:])
press(L, "SCROLL_LOCK")   # step 3: SM_Portal
n = len(calls(L))
shift_sl(L)
c = calls(L)[n:]
check("first Geo: Conchoidal arched door, on the plane (square C), the plain press gathered",
      c[:3] == ["kml MI_GeoArch_Con", "mesh Plane", "mmat 0 MID_MI_GeoArch_Con"], c)
check("placed at 1.0 x 2.0 m, stood up as square C (roll +90, yaw +90 from the pad)", c[3:] == ["mloc 0.0 0.0 158.0", "mrot 0 90 90", "mscale 1.000 2.000 1.000"], c)
check("first load named before it runs", has(L, "first load of our own cooked ring material next: /Game/Mods/PortalHubLooks/Geo/MI_GeoArch_Con.MI_GeoArch_Con"))
check("logged with its starting size", has(L, "GEO RING (Shift + SCROLL LOCK): 1/24 MI_GeoArch_Con, starting size 1.00 m wide x 2.00 m tall"))
check("SetMaterial on a StaticMeshComponent named once (first time)", sum("untried native call next: PrimitiveComponent:SetMaterial" in l for l in logs(L)) == 1)
n = len(calls(L))
shift_sl(L)
c = calls(L)[n:]
check("second: Colloform arch; shape already square C (no SetStaticMesh)", c[:2] == ["kml MI_GeoArch_Col", "mmat 0 MID_MI_GeoArch_Col"] and not any(x.startswith("mesh ") for x in c), c)
shift_sl(L); shift_sl(L)
check("3rd and 4th: Reniform, then Prismatic arch", "mmat 0 MID_MI_GeoArch_Pri" in calls(L)[-4:] and "kml MI_GeoArch_Ren" in calls(L), calls(L)[-4:])
for _ in range(9):
    shift_sl(L)
check("13th: Conchoidal door at 1.75 x 3.0 m", calls(L)[-1] == "mscale 1.750 3.000 1.000" and "mmat 0 MID_MI_GeoDoor_Con" in calls(L)[-4:], calls(L)[-4:])
for _ in range(11):
    shift_sl(L)
check("24th: Prismatic oval", "mmat 0 MID_MI_GeoOval_Pri" in calls(L)[-4:], calls(L)[-4:])
shift_sl(L)
check("then round again to the Conchoidal arch", "mmat 0 MID_MI_GeoArch_Con" in calls(L)[-4:], calls(L)[-4:])
check("first-load line only once", sum("first load of our own" in l for l in logs(L)) == 1)
press(L, "OEM_PERIOD"); press(L, "OEM_PERIOD")
check(". tints the Geo ring (red, grey x RGB; DistortionEdge unreadable in this mock, left alone)",
      calls(L)[-3:] == ["vec PortalCenterColor 0.109 0.005 0.005", "vec PortalCenterColor2 1.000 0.050 0.050", "vec PortalEdge 4.836 0.242 0.242"], calls(L)[-3:])
check("tint log names the Geo ring", has(L, "MESH RING TINT (.): red = RGB 1.00, 0.05, 0.05 (MI_GeoArch_Con)"))
press(L, "OEM_COMMA")
check(", puts a scene in its PortalTexture", calls(L)[-1].startswith("tex PortalTexture TC_"), calls(L)[-1])
press(L, "M")
check("M scales it from its starting size (x1.1 = 1.1 x 2.2 m)", calls(L)[-1] == "mscale 1.100 2.200 1.100", calls(L)[-1])
press(L, "OEM_TWO")
check("/ names the Geo ring", has(L, "ring MI_GeoArch_Con"))
press(L, "SCROLL_LOCK")
check("plain SCROLL LOCK after a Geo ring: the game's rings again (Friendly White)", calls(L)[-1] == "mmat 0 MID_M_Portal_Friendly_White", calls(L)[-1])
shift_sl(L)
check("Shift + SCROLL LOCK goes on with the next Geo (Colloform arch)", "mmat 0 MID_MI_GeoArch_Col" in calls(L)[-4:], calls(L)[-4:])
L.execute("KEYS['SCROLL_LOCK'](); KEYS['SCROLL_LOCK'](); pump()")
check("two plain presses inside 40 ms count once (gathered)", calls(L)[-1] == "mmat 0 MID_M_Portal_Friendly", calls(L)[-2:])

print("=== tint: DistortionEdge where it reads")
L = lab()
L.execute("GREYS.DistortionEdge = { R = 10, G = 0.924, B = 0 }")
mesh_built(L)
shift_sl(L)
press(L, "OEM_PERIOD"); press(L, "OEM_PERIOD")
c = calls(L)[-4:]
check("readable DistortionEdge is tinted too (grey 2.78 x red)", c[3].startswith("vec DistortionEdge 2.78") and c[0].startswith("vec PortalCenterColor "), c)

print("=== own pak: LoadAsset finds nothing (in game, 15 Nov), GetAsset by name loads it")
L = lab()
L.execute("""
OWN_VIA_GETASSET, OWN_LOADED = true, false
local oldSFO2 = StaticFindObject
function StaticFindObject(path)
    if path == "/Script/AssetRegistry.Default__AssetRegistryHelpers" then
        return { IsValid = function() return true end, GetFName = function() return FName("Default__AssetRegistryHelpers") end,
            GetAsset = function(self, d) CALLS2[#CALLS2 + 1] = "getasset " .. d.PackageName:ToString() .. " " .. d.AssetName:ToString(); OWN_LOADED = true end }
    end
    if path:find("^/Game/Mods/PortalHubLooks/") and OWN_VIA_GETASSET and not OWN_LOADED then return nil end
    return oldSFO2(path)
end
function LoadAsset(p) if p:find("PortalHubLooks") then error("asset not found in the asset registry") end end
""")
mesh_built(L)
n = len(calls(L))
shift_sl(L)
c = calls(L)[n:]
check("GetAsset by package and asset name, then the Geo ring goes on",
      c[:2] == ["getasset /Game/Mods/PortalHubLooks/Geo/MI_GeoArch_Con MI_GeoArch_Con", "kml MI_GeoArch_Con"] and "mmat 0 MID_MI_GeoArch_Con" in c, c)
check("LoadAsset's error is logged, not swallowed", has(L, "LoadAsset did not load it (") and has(L, "asset not found in the asset registry"))
check("GetAsset named as untried before it runs", has(L, "untried native call next: AssetRegistryHelpers:GetAsset({ PackageName, AssetName }) for our own pak's material"))
check("logged how it loaded", has(L, "loaded with GetAsset"))

print("=== missing pak")
L = lab()
L.execute("OWN_PAK = false")
mesh_built(L)
n = len(calls(L))
shift_sl(L)
check("not installed: said in the log, no call, shape not changed", has(L, "MI_GeoArch_Con not found: is PortalHubLooks_P (.pak / .ucas / .utoc) in Content\\Paks\\~mods?")
      and calls(L)[n:] == [], calls(L)[n:])
L.execute("OWN_PAK = nil")
shift_sl(L)
check("installed later: the next press tries the same (first) Geo ring and finds it", "mmat 0 MID_MI_GeoArch_Con" in calls(L)[-4:], calls(L)[-4:])

print("=== other modes")
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("overlay mode: Shift + SCROLL LOCK says mesh mode only, no call", has(L, "Shift + SCROLL LOCK: mesh mode only") and calls(L) == [], calls(L))

print("=== PAUSE: hide the pad's own look (mesh mode)")
check("PAUSE bound once in the lab, to LK.hide_own", re.search(r"RegisterKeyBind\(Key\.PAUSE, function\(\) ExecuteInGameThread\(LK\.hide_own\)", src) and len(re.findall(r"Key\.PAUSE\b", src)) == 1)
hub = open(os.path.join(ROOT, "mod", "PortalHub", "Scripts", "main.lua"), encoding="utf-8").read()
check("the hub binds PAUSE only inside its DEV_KEYS block (off in the install, cut from the package)",
      hub.count("Key.PAUSE") == 1 and hub.rfind("if DEV_KEYS then", 0, hub.index("Key.PAUSE")) > hub.rfind("\nend", 0, hub.index("Key.PAUSE")))
check("no other mod of ours binds PAUSE", "Key.PAUSE" not in "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                                                                     for m in ("CordonaProbe", "PortalLogger", "CordonaDlcSurvey")))
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "PAUSE")
check("overlay mode: PAUSE says mesh mode only, no call", has(L, "PAUSE: mesh mode only") and calls(L) == [], calls(L))
for _ in range(3):
    press(L, "OEM_FOUR")
press(L, "PAUSE")
check("mesh mode, no ring yet: hides the nearest pad's own look", calls(L) == ["ownvis false false"], calls(L))
check("names SetVisibility first", has(L, "untried native call next: SceneComponent:SetVisibility(false) on the pad's own effect"))
i_head = next(i for i, l in enumerate(logs(L)) if "OWN LOOK HIDDEN (PAUSE in mesh mode): hub_B1's own look (Niagara_Portal)" in l)
i_un = next(i for i, l in enumerate(logs(L)) if "SetVisibility(false)" in l)
check("heading, then the untried line, then the call", i_head < i_un)
press(L, "PAUSE")
check("PAUSE again: shown", calls(L)[-1] == "ownvis true false" and has(L, "OWN LOOK SHOWN (PAUSE in mesh mode): hub_B1's own look visible again"), calls(L))
for _ in range(3):
    press(L, "SCROLL_LOCK")
shift_sl(L)
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)), (sft_pad('hub_B2', 'Niagara_Portal', 50)) }")
n = len(calls(L))
press(L, "PAUSE")
check("with a ring built: hides the ring's pad, not a nearer one", calls(L)[n:] == ["ownvis false false"] and has(L, "OWN LOOK HIDDEN (PAUSE in mesh mode): hub_B1"), calls(L)[n:])
check("SetVisibility named only once", sum("SetVisibility(false)" in l for l in logs(L)) == 1)
L.execute("KEYS['U+SHIFT'](); KEYS['U'](); pump()")
check("Shift + U: ring removed and the own look shown again", calls(L)[-2:] == ["mdestroy", "ownvis true false"] and has(L, "OWN LOOK SHOWN (Shift + U)"), calls(L)[-3:])
press(L, "PAUSE")
check("next PAUSE hides again (state cleared by Shift + U)", calls(L)[-1] == "ownvis false false", calls(L)[-1])

print("=== facing: the ring faces the pad's own angle, not the effect's turn")
L = lab()
mesh_built(L, steps=1)
check("the effect's turn (yaw 90 in the mock) is logged and ignored: ring yaw 0", "mrot 0 0 0" in calls(L) and has(L, "the pad's effect is turned pitch 0.0 yaw 90.0 roll 0.0; the ring ignores that"), calls(L))

print("=== fine scale: Shift + M / N (x1.01), every mode")
check("Shift + M and Shift + N bound to fine steps", re.search(r"RegisterKeyBind\(Key\.M, \{ ModifierKey\.SHIFT \}, function\(\) ExecuteInGameThread\(function\(\) LK\.scale_press\(1\.01\)", src)
      and re.search(r"RegisterKeyBind\(Key\.N, \{ ModifierKey\.SHIFT \}, function\(\) ExecuteInGameThread\(function\(\) LK\.scale_press\(1 / 1\.01\)", src))
L = lab()
mesh_built(L, steps=1)
L.execute("KEYS['M+SHIFT'](); KEYS['M'](); pump()")
check("mesh: Shift + M (plain M fired too) = x1.01 only", calls(L)[-1] == "mscale 1.010 1.010 1.010", calls(L)[-1])
L.execute("KEYS['N+SHIFT'](); KEYS['N'](); pump()")
check("mesh: Shift + N = /1.01 (back to 1.000)", calls(L)[-1] == "mscale 1.000 1.000 1.000", calls(L)[-1])
press(L, "M")
check("plain M still x1.1", calls(L)[-1] == "mscale 1.100 1.100 1.100", calls(L)[-1])
L.execute("KEYS['M'](); KEYS['M'](); pump()")
check("two plain M inside 40 ms count once", calls(L)[-1] == "mscale 1.210 1.210 1.210", calls(L)[-1])
L = lab()
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100)) }")
press(L, "OEM_FOUR")
L.execute("KEYS['M+SHIFT'](); KEYS['M'](); pump()")
check("own mode: Shift + M scales the pad's own look x1.01", calls(L)[-1] == "ownscale 1.010 1.010 1.010", calls(L)[-1])
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "OEM_FOUR"); press(L, "OEM_FOUR"); press(L, "SCROLL_LOCK")
L.execute("KEYS['N+SHIFT'](); KEYS['N'](); pump()")
check("tint mode: Shift + N ring size /1.01 (0.346 -> 0.343)", calls(L)[-1] == "scalar Radius (S) 0.343", calls(L)[-1])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
