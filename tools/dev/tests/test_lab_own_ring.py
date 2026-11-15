# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game and checks CRD-043: our own cooked ring material
# M_PortalHubLooks_Arch (PortalHubLooks_P, World Projects/PortalHubLooks) is one more ring in LK.TINT_RINGS, right after the game's
# arch; in mesh mode Shift + SCROLL LOCK swaps the ring on the built shape between the game's arch and ours (gathered with the plain
# SCROLL LOCK that fires with it); the first load is named in the log first; a missing pak is said, not crashed on; PAUSE (mesh
# mode) hides / shows the pad's own look, and Shift + U shows it again.
# Also cross-checks the lab against the material's build script: same asset path, chunk 120 label, and every parameter the lab sets
# (tint colours, PortalTexture, Radius (S)) exists in the material with the radius the lab starts from.
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


def ring_list(src):   # LK is a main-chunk local, so the list is read from the source
    body = re.search(r"^LK\.TINT_RINGS = \{(.*?)\}", src, re.S | re.M).group(1)
    return re.findall(r'"([\w]+)"', body)


def mesh_built(L, steps=4):
    L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
    for _ in range(3):
        press(L, "OEM_FOUR")
    for _ in range(steps):
        press(L, "SCROLL_LOCK")


src = open(LAB, encoding="utf-8").read()
build = open(BUILD, encoding="utf-8").read()

print("=== ring list and keys")
L = lab()
rings = ring_list(src)
check("own arch is in LK.TINT_RINGS, right after the game's arch", rings.index("M_PortalHubLooks_Arch") == rings.index("M_Portal_Arch") + 1, rings)
check("the plain window is still last (mesh mode skips it)", rings[-1] == "M_WorldPortal", rings)
check("12 mesh rings + the plain window", len(rings) == 13, len(rings))
check("Shift + SCROLL LOCK bound to LK.shift_scroll", re.search(r"RegisterKeyBind\(Key\.SCROLL_LOCK, \{ ModifierKey\.SHIFT \}, function\(\) ExecuteInGameThread\(LK\.shift_scroll\)", src))
check("plain SCROLL LOCK still bound to LK.make_mid", re.search(r"RegisterKeyBind\(Key\.SCROLL_LOCK, function\(\) ExecuteInGameThread\(LK\.make_mid\)", src))
others = "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey"))
check("no other mod of ours binds SCROLL LOCK", "Key.SCROLL_LOCK" not in others)
check("no bare ExecuteWithDelay added", src.count("ExecuteWithDelay(") == 1)
block = src[src.index("-- Our own ring material (CRD-043)"):src.index("-- Mode switch:")]
check("no main-chunk local in the CRD-043 block", not re.search(r"^local ", block, re.M))
check("square C is still a shape: engine Plane, roll +90, yaw +90",
      re.search(r'name = "square C \(roll \+90, yaw \+90\)", path = "/Engine/BasicShapes/Plane\.Plane", pitch = 0, yaw = 90, roll = 90', src))

print("=== lab and material build script agree")
m = re.search(r'BASE = "([^"]+)"\nMAT_DIR = BASE \+ "([^"]+)"\nMAT_NAME = "([^"]+)"', build)
path = m.group(1) + m.group(2) + "/" + m.group(3)
lab_path = re.search(r'LK\.RING_PATHS = \{ M_PortalHubLooks_Arch = "([^"]+)" \}', src).group(1)
check("lab path = the build script's asset (" + path + ")", lab_path == path + "." + m.group(3), lab_path)
check("label chunk 120 in the build script", re.search(r"^CHUNK = 120$", build, re.M))
check("the project cooks its own folder", '+DirectoriesToAlwaysCook=(Path="%s")' % m.group(1) in open(GAME_INI, encoding="utf-8").read())
params = re.findall(r'\("\w+",\s*"([^"]+)",\s*([-\d.(][^)]*\)?)\)', build)
names = {p for p, _ in params}
for p in ("PortalCenterColor", "PortalCenterColor2", "PortalEdge", "Radius (S)"):
    check("material has " + p + " (the lab sets it)", p in names, sorted(names))
check("material has a PortalTexture texture parameter", '"parameter_name", "PortalTexture"' in build)
rad = [v for p, v in params if p == "Radius (S)"]
lab_rad = float(re.search(r"M_PortalHubLooks_Arch = ([\d.]+) \}", src).group(1))
check("lab's starting ring size = the material's Radius (S) default (0.30)", rad and abs(float(rad[0]) - lab_rad) < 1e-9, (rad, lab_rad))
check("material: two-sided, masked, unlit, Niagara sprite usage", all(x in build for x in ('"two_sided", True', "BLEND_MASKED", "MSM_UNLIT", '"used_with_niagara_sprites", True')))
check("no game texture paths in the graph except the dummy's own path", re.findall(r'"/Game/Particles/[^"]*"', build) == ['"/Game/Particles/RenderTargets"'], re.findall(r'"/Game/Particles/[^"]*"', build))

print("=== mesh mode: Shift + SCROLL LOCK, own arch / game's arch")
L = lab()
mesh_built(L, steps=2)
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("before the shape is on (step 2): asks for the build, no call", has(L, "own ring A / B: build the shape first") and calls(L)[-1] == "collision 0", calls(L)[-2:])
press(L, "SCROLL_LOCK")   # step 3: SM_Portal
n = len(calls(L))
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); KEYS['SCROLL_LOCK'](); pump()")   # UE4SS fires plain SCROLL LOCK with Shift + SCROLL LOCK
c = calls(L)[n:]
check("step 3 + Shift + SCROLL LOCK: our own arch straight on (step 4), the plain press gathered", c == ["kml M_PortalHubLooks_Arch", "mmat 0 MID_M_PortalHubLooks_Arch"], c)
check("first load named before it runs", has(L, "first load of our own cooked ring material next: /Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Arch.M_PortalHubLooks_Arch"))
i_name = next(i for i, l in enumerate(logs(L)) if "first load of our own" in l)
i_put = next(i for i, l in enumerate(logs(L)) if "MESH RING step 4/4 (Shift + SCROLL LOCK, own arch): M_PortalHubLooks_Arch" in l)
check("... and before the ring line", i_name < i_put, (i_name, i_put))
check("SetMaterial on a StaticMeshComponent still named once (first time)", sum("untried native call next: PrimitiveComponent:SetMaterial" in l for l in logs(L)) == 1)
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("again: the game's arch for comparison", calls(L)[-2:] == ["kml M_Portal_Arch", "mmat 0 MID_M_Portal_Arch"], calls(L)[-2:])
check("logged as the game's arch", has(L, "MESH RING next ring (Shift + SCROLL LOCK, game's arch): M_Portal_Arch"))
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("again: ours", calls(L)[-1] == "mmat 0 MID_M_PortalHubLooks_Arch", calls(L)[-1])
check("first-load line only once", sum("first load of our own" in l for l in logs(L)) == 1)
press(L, "OEM_PERIOD"); press(L, "OEM_PERIOD")
check(". tints our arch (red, grey x RGB on PortalCenterColor / 2 / PortalEdge)", calls(L)[-3:] == ["vec PortalCenterColor 0.109 0.005 0.005", "vec PortalCenterColor2 1.000 0.050 0.050", "vec PortalEdge 4.836 0.242 0.242"], calls(L)[-3:])
press(L, "OEM_COMMA")
check(", puts a scene in our arch's PortalTexture", calls(L)[-1].startswith("tex PortalTexture TC_"), calls(L)[-1])
press(L, "SCROLL_LOCK")
check("plain SCROLL LOCK after ours: wraps to Friendly White (ours is the 12th mesh ring)", calls(L)[-1] == "mmat 0 MID_M_Portal_Friendly_White", calls(L)[-1])
L.execute("for i = 1, 10 do KEYS['SCROLL_LOCK'](); pump() end")
check("10 more: the game's arch (11th)", calls(L)[-1] == "mmat 0 MID_M_Portal_Arch", calls(L)[-1])
press(L, "SCROLL_LOCK")
check("next: ours (12th)", calls(L)[-1] == "mmat 0 MID_M_PortalHubLooks_Arch", calls(L)[-1])
for _ in range(3):
    press(L, "L")
check("L x3: square C (engine Plane, roll +90, yaw +90) with our arch put back", "mesh Plane" in calls(L)[-6:] and "mmat 0 MID_M_PortalHubLooks_Arch" in calls(L)[-6:]
      and "mrot 0 180 90" in calls(L)[-3:], calls(L)[-6:])
n = len(calls(L))
L.execute("KEYS['SCROLL_LOCK'](); KEYS['SCROLL_LOCK'](); pump()")
check("two plain presses inside 40 ms count once (gathered)", calls(L)[n:] == ["kml M_Portal_Friendly_White", "mmat 0 MID_M_Portal_Friendly_White"], calls(L)[n:])

print("=== missing pak")
L = lab()
L.execute("OWN_PAK = false")
mesh_built(L)
n = len(calls(L))
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("not installed: said in the log and on screen, no call", has(L, "M_PortalHubLooks_Arch not found: is PortalHubLooks_P (.pak / .ucas / .utoc) in Content\\Paks\\~mods?")
      and calls(L)[n:] == [], calls(L)[n:])
press(L, "SCROLL_LOCK")
check("the ring index was kept: plain SCROLL LOCK goes on to Friendly (2nd), not past ours", calls(L)[-1] == "mmat 0 MID_M_Portal_Friendly", calls(L)[-1])
L.execute("OWN_PAK = nil")
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("installed later: the next Shift + SCROLL LOCK finds it", calls(L)[-1] == "mmat 0 MID_M_PortalHubLooks_Arch", calls(L)[-1])

print("=== other modes")
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
check("overlay mode: Shift + SCROLL LOCK says mesh mode only, no call", has(L, "Shift + SCROLL LOCK: mesh mode only") and calls(L) == [], calls(L))
press(L, "OEM_FOUR"); press(L, "OEM_FOUR")
L.execute("for i = 1, 12 do KEYS['SCROLL_LOCK']() end")
check("tint mode: the 12th grey ring is ours, in the window", calls(L)[-1] == "varmat User.PortalTexture MID_M_PortalHubLooks_Arch", calls(L)[-1])
press(L, "M")
check("tint-mode M: our Radius (S) from 0.30 (x1.1 = 0.330)", calls(L)[-1] == "scalar Radius (S) 0.330" and has(L, "M_PortalHubLooks_Arch Radius (S) 0.330 (cooked 0.300, x1.10)"), calls(L)[-1])

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
L.execute("KEYS['SCROLL_LOCK+SHIFT'](); pump()")
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)), (sft_pad('hub_B2', 'Niagara_Portal', 50)) }")
n = len(calls(L))
press(L, "PAUSE")
check("with a ring built: hides the ring's pad, not a nearer one", calls(L)[n:] == ["ownvis false false"] and has(L, "OWN LOOK HIDDEN (PAUSE in mesh mode): hub_B1"), calls(L)[n:])
check("SetVisibility named only once", sum("SetVisibility(false)" in l for l in logs(L)) == 1)
L.execute("KEYS['U+SHIFT'](); KEYS['U'](); pump()")
check("Shift + U: ring removed and the own look shown again", calls(L)[-2:] == ["mdestroy", "ownvis true false"] and has(L, "OWN LOOK SHOWN (Shift + U)"), calls(L)[-3:])
press(L, "PAUSE")
check("next PAUSE hides again (state cleared by Shift + U)", calls(L)[-1] == "ownvis false false", calls(L)[-1])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
