# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game and checks CRD-046: the stills mode ([ -> stills)
# that shoots every portal design for the config editor's previews. SCROLL LOCK steps through the three untried calls one press each
# (camera spawned, its view, one test shot), then runs all 67 designs (32 game looks at their heights, 24 Geo rings on the engine plane
# as square C with the pad's own look hidden, 11 game ring materials on the same surface), noting each shot in stills.txt before the call; M / N, O / P, LEFT / RIGHT frame the
# camera; SCROLL LOCK stops a run; PAUSE, the end of a run and [ put everything back. Also checks the design list against the editor's
# design names and make_previews.py's file names.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)
LOOKS_MOCK = re.search(r'LOOKS = r"""(.*?)"""', open(os.path.join(S, "test_lab_looks.py"), encoding="utf-8").read(), re.S).group(1)
PADS = re.search(r'PADS = r"""(.*?)"""', open(os.path.join(S, "test_lab_scale_facing_tint.py"), encoding="utf-8").read(), re.S).group(1)
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
sys.path.insert(0, os.path.join(ROOT, "tools", "dev"))
import hubdata
import make_previews

# The stills pad: like the other lab tests' pads, plus SetAsset / Activate on its effect, turned yaw 90 (facing +Y), and a world with
# SpawnActor, a controller with SetViewTargetWithBlend, KismetSystemLibrary's ExecuteConsoleCommand and stills.txt caught in memory.
STILLS = r"""
CLOCK = 1763250000
CLOCKF = CLOCK
os.time = function() return CLOCK end
-- the clock follows the delays the lab asks for (later -> ExecuteWithDelay in this mock), so the notes' times are the run's own
function ExecuteWithDelay(ms, fn) DELAYED[#DELAYED + 1] = function() CLOCKF = CLOCKF + ms / 1000; CLOCK = math.floor(CLOCKF); fn() end end
NOTES = {}
local realOpen = io.open
io.open = function(path, mode)
    if tostring(path):find("stills.txt", 1, true) then
        if NO_NOTES then return nil end
        return { write = function(self, s) NOTES[#NOTES + 1] = (s:gsub("\n$", "")); CALLS2[#CALLS2 + 1] = "note " .. (s:gsub("\n$", "")) end,
            close = function() end }
    end
    return realOpen(path, mode)
end
local function ro(t) t.IsValid = t.IsValid or function() return true end
    return setmetatable({}, { __index = t, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end }) end
function st_pad(id, look, x, yaw)
    local cur = { look = look, vis = true }
    local fx = ro({ GetFName = function() return FName("NiagaraComponent") end, GetAddress = function() return id .. "_fx" end,
        RelativeLocation = { X = 0, Y = 0, Z = 158 }, RelativeRotation = { Pitch = 0, Yaw = 90, Roll = 0 }, RelativeScale3D = { X = 1, Y = 1, Z = 1 },
        GetAsset = function() return StaticFindObject("/Game/Particles/" .. cur.look .. "." .. cur.look) end,
        SetAsset = function(self, sys, reset) cur.look = sys:GetFName():ToString(); CALLS2[#CALLS2 + 1] = "setasset " .. cur.look end,
        Activate = function() end,
        K2_SetRelativeLocation = function(self, l) CALLS2[#CALLS2 + 1] = string.format("ownloc %.1f", l.Z) end,
        SetVisibility = function(self, v, kids) cur.vis = v; CALLS2[#CALLS2 + 1] = "ownvis " .. tostring(v) .. " " .. tostring(kids) end })
    local base = getmetatable(sft_pad(id, look, x)).__index   -- borrow AddComponentByClass (the mesh ring's component) from the CRD-042 pad
    local p = ro({ GetFName = function() return FName("BP_Teleporter_ParentBP_C") end, MyTeleporterID = FName(id), ParticleLoop = fx,
        AddComponentByClass = base.AddComponentByClass,
        K2_GetActorLocation = function() return { X = x, Y = 0, Z = 0 } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = yaw or 90, Roll = 0 } end })
    return p, cur
end
CAMS = {}
WORLD = ro({ SpawnActor = function(self, cls, loc, rot)
    if cls:GetFName():ToString() == "BP_Teleporter_ParentBP_C" then   -- the stand-in pad: settable like the lab's INSERT preview pad
        local inner = st_pad("None", "Niagara_Portal", loc.X, rot.Yaw)
        local alive = true
        local pad = setmetatable({}, {
            __index = function(_, k)
                if k == "IsValid" then return function() return alive end end
                if k == "K2_DestroyActor" then return function() alive = false; CALLS2[#CALLS2 + 1] = "standin destroy" end end
                if k == "OnRep_IsTeleporterActive" then return function() CALLS2[#CALLS2 + 1] = "standin onrep" end end
                return inner[k]
            end,
            __newindex = function(_, k, v) CALLS2[#CALLS2 + 1] = "standin set " .. k .. " " .. (type(v) == "table" and v:ToString() or tostring(v)) end })
        CALLS2[#CALLS2 + 1] = string.format("spawn pad %.0f %.0f %.0f yaw %.0f", loc.X, loc.Y, loc.Z, rot.Yaw)
        PADS[#PADS + 1] = pad
        return pad
    end
    if NO_CAMERA then return nil end
    local alive = true
    local cam = ro({ IsValid = function() return alive end, GetFName = function() return FName("CameraActor") end,
        K2_SetActorLocationAndRotation = function(self, l, r) CALLS2[#CALLS2 + 1] = string.format("cammove %.0f %.0f %.0f yaw %.0f", l.X, l.Y, l.Z, r.Yaw) end,
        K2_DestroyActor = function() alive = false; CALLS2[#CALLS2 + 1] = "camdestroy" end })
    CAMS[#CAMS + 1] = cam
    CALLS2[#CALLS2 + 1] = string.format("spawn %s %.0f %.0f %.0f yaw %.0f", cls:GetFName():ToString(), loc.X, loc.Y, loc.Z, rot.Yaw)
    return cam
end })
CONTROL_YAW = 0
LPC = ro({ Pawn = LPAWN, GetWorld = function() return WORLD end, GetControlRotation = function() return { Pitch = 0, Yaw = CONTROL_YAW, Roll = 0 } end,
    SetViewTargetWithBlend = function(self, t, bt, bf, be, lock) CALLS2[#CALLS2 + 1] = "view " .. t:GetFName():ToString() end })
local oldSFO3 = StaticFindObject
function StaticFindObject(path)
    if path == "/Script/Engine.CameraActor" then return ro({ GetFName = function() return FName("CameraActor") end }) end
    if path:find("BP_Teleporter_ParentBP_C", 1, true) then
        if NO_TELEPORTER then return nil end
        return ro({ GetFName = function() return FName("BP_Teleporter_ParentBP_C") end })
    end
    if path == "/Script/Engine.Default__KismetSystemLibrary" then
        return ro({ GetFName = function() return FName("KSL") end,
            ExecuteConsoleCommand = function(self, ctx, cmd, pc) CALLS2[#CALLS2 + 1] = "console " .. cmd end })
    end
    return oldSFO3(path)
end
"""

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
    L.execute(STILLS)
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def calls(L):
    g = L.globals()
    return [g.CALLS2[i] for i in range(1, len(g.CALLS2) + 1)]


def notes(L):
    g = L.globals()
    return [g.NOTES[i] for i in range(1, len(g.NOTES) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


def press(L, key):
    L.execute("KEYS['%s'](); pump()" % key)


def drain(L, ticks=500):
    """Runs the delayed steps until none are left (the mock clock moves by each delay)."""
    for _ in range(ticks):
        if L.eval("#DELAYED") == 0:
            return
        L.execute("pump()")


def stills_mode(L, pad="PADS = { (st_pad('hub_B1', 'Niagara_Portal', 100)) }"):
    L.execute(pad)
    for _ in range(4):
        press(L, "OEM_FOUR")


src = open(LAB, encoding="utf-8").read()
block = src[src.index("-- Stills for the config editor's previews (CRD-046"):src.index('RegisterKeyBind(Key.O, ')]

print("=== code rules")
check("a fifth look-keys mode, stills", re.search(r'^LK\.MODES = \{ "overlay", "own", "tint", "mesh", "stills" \}', src, re.M))
check("no new key bind in the stills block (existing lab keys through the mode)", "RegisterKeyBind" not in block)
check("no main-chunk local in the stills block", not re.search(r"^local ", block, re.M))
check("no bare ExecuteWithDelay added (delays through the game-thread helper)", src.count("ExecuteWithDelay(") == 1)
check("the game's screenshot without UI ('shot', not 'shot showui')", re.search(r'^LK\.SHOT_CMD = "shot"', src, re.M))
settle = int(re.search(r"^LK\.ST_SETTLE_MS = (\d+)", src, re.M).group(1))
after = int(re.search(r"^LK\.ST_AFTER_MS = (\d+)", src, re.M).group(1))
check("shots at least 3 s apart, so make_previews.py can pair them by time (%d + %d ms)" % (settle, after), settle + after >= 3000)
check("stills.txt next to the lab", 'LK.STILLS_FILE = "ue4ss/Mods/PortalMaterialLab/stills.txt"' in src)
check("each untried call named in the block", all(("LK.untried(\"" + c) in block for c in
      ("World:SpawnActor(CameraActor)", "PlayerController:SetViewTargetWithBlend", "KismetSystemLibrary:ExecuteConsoleCommand", "Actor:K2_SetActorLocationAndRotation")))

print("=== the design list and the preview file names")
looks_src = re.findall(r'"(Niagara_Portal[\w]*)"', re.search(r"^LK\.LOOKS = \{(.*?)\}", src, re.S | re.M).group(1))
check("the 32 game looks are the editor's DESIGN_NAMES, in order", looks_src == hubdata.DESIGN_NAMES, looks_src)
rings_src = re.findall(r'"(M_\w+)"', re.search(r"^LK\.TINT_RINGS = \{(.*?)\}", src, re.S | re.M).group(1))
check("the ring stills: every TINT_RINGS material but the plain window (as the mesh ring)", rings_src[-1] == "M_WorldPortal" and len(rings_src) == 12, rings_src)
check("make_previews.py knows the same 67 names (32 game + 24 Geo + 11 rings)", make_previews.design_keys() == hubdata.DESIGN_NAMES +
      ["Geo_%s_%s" % (s, t) for s in ("Arch", "Gothic", "Square", "Door", "Round", "Oval") for t in ("Con", "Col", "Ren", "Pri")] + rings_src[:-1],
      make_previews.design_keys()[30:36])

print("=== stills mode: not at a pad, keys before the camera")
L = lab()
stills_mode(L, "PADS = {}")
check("[ x4 = stills mode, logged", has(L, "LOOK KEYS MODE ([): stills"))
L.execute("NO_TELEPORTER = true")
press(L, "SCROLL_LOCK")
check("no pad and no teleporter class: said, no call", has(L, "stills: the world or the teleporter class was not found") and calls(L) == [], calls(L))
L.execute("NO_TELEPORTER = false; PADS = { (st_pad('hub_B1', 'Niagara_Portal', 100)) }")
L.execute("KEYS['M'](); pump()")
check("M before the camera: asks for SCROLL LOCK, no call", has(L, "stills distance: press SCROLL LOCK at a pad first") and calls(L) == [], calls(L))
press(L, "PAUSE")
check("PAUSE with nothing on: nothing to end, no call", has(L, "stills (PAUSE): nothing to end") and calls(L) == [], calls(L))

print("=== the three untried calls, one press each")
press(L, "SCROLL_LOCK")
check("1st press: a camera 3 m in front of the pad (facing +Y), at the look's height, looking back", calls(L) == ["spawn CameraActor 100 300 158 yaw 270"], calls(L))
i_un = next((i for i, l in enumerate(logs(L)) if "untried native call next: World:SpawnActor(CameraActor)" in l), 99999)
i_head = next((i for i, l in enumerate(logs(L)) if "STILLS step 1/3" in l), -1)
check("heading, then the untried line, before the spawn", 0 <= i_head < i_un)
press(L, "SCROLL_LOCK")
check("2nd press: view from the camera", calls(L)[-1] == "view CameraActor", calls(L))
check("SetViewTargetWithBlend named first", has(L, "untried native call next: PlayerController:SetViewTargetWithBlend"))
L.execute("KEYS['M'](); pump()")
check("M: camera 3.3 m away (x1.1)", calls(L)[-1] == "cammove 100 330 158 yaw 270", calls(L)[-1])
check("the move named on its first use", has(L, "untried native call next: Actor:K2_SetActorLocationAndRotation on the camera"))
L.execute("KEYS['N+SHIFT'](); KEYS['N'](); pump()")
check("Shift + N (plain N fired too) = /1.01 only", calls(L)[-1] == "cammove 100 327 158 yaw 270", calls(L)[-1])
L.execute("KEYS['O'](); pump()")
check("O: camera 10 cm higher", calls(L)[-1] == "cammove 100 327 168 yaw 270", calls(L)[-1])
L.execute("KEYS['P+SHIFT'](); KEYS['P'](); pump()")
check("Shift + P: 1 cm lower", calls(L)[-1] == "cammove 100 327 167 yaw 270", calls(L)[-1])
press(L, "RIGHT_ARROW")
check("RIGHT: the other side of the pad, looking the other way", calls(L)[-1] == "cammove 100 -327 167 yaw 90", calls(L)[-1])
press(L, "LEFT_ARROW")
check("LEFT: back in front", calls(L)[-1] == "cammove 100 327 167 yaw 270", calls(L)[-1])
check("the move named only once", sum("K2_SetActorLocationAndRotation" in l for l in logs(L)) == 1)
n = len(calls(L))
press(L, "SCROLL_LOCK")
c = calls(L)[n:]
check("3rd press: stills.txt line first, then one 'shot' console command", c == ["note shot\t0\ttest\ttest\t1763250000", "console shot"], c)
check("ExecuteConsoleCommand named first", has(L, "untried native call next: KismetSystemLibrary:ExecuteConsoleCommand('shot')"))
check("says where the picture lands", has(L, "AbioticFactor\\Saved\\Screenshots"))

print("=== the run: 67 designs")
n = len(calls(L))
press(L, "SCROLL_LOCK")
drain(L)
c = calls(L)[n:]
shots = [x for x in c if x == "console shot"]
check("67 shots", len(shots) == 67, len(shots))
run_notes = [x for x in notes(L) if x.startswith("shot\t") and not x.split("\t")[2] == "test"]
names = [x.split("\t")[2] for x in run_notes]
check("stills.txt names each shot in order: the 32 game looks, then the 24 Geo rings", names == make_previews.design_keys(), names[:3] + names[-3:])
check("a run line before the shots (time, date, pad, count)", any(x.startswith("run\t1763250") and x.endswith("\thub_B1\t67") for x in notes(L)), notes(L)[:3])
times = [int(x.split("\t")[4]) for x in run_notes]
check("shots at least 3 s apart in the notes", all(b - a >= 3 for a, b in zip(times, times[1:])), times[:5])
order_ok = all(c[c.index("console shot", i) - 1].startswith("note shot") for i in range(len(c)) if c[i] == "console shot")
check("every shot noted just before its call", order_ok)
looks = [x[len("setasset "):] for x in c if x.startswith("setasset ")]
check("each game look put on in turn, then the pad's own look back at the end", looks == hubdata.DESIGN_NAMES + ["Niagara_Portal"], looks[-3:])
check("game looks at their heights (Friendly Red 108 from the sheet or picks)", "ownloc 108.0" in c, [x for x in c if x.startswith("ownloc")][:5])
geo_start = c.index("setasset Niagara_Portal_Torii")
g = c[geo_start:]
check("Geo surface built once, collision off before the mesh, square C at the effect's place",
      [x for x in g if x.startswith(("addcomp", "collision", "mesh ", "mloc", "mrot"))][:5] ==
      ["addcomp StaticMeshComponent false false W=1", "collision 0", "mesh Plane", "mloc 0.0 0.0 158.0", "mrot 0 90 90"], g[:12])
check("Geo surface added only once", sum(x.startswith("addcomp") for x in c) == 1)
check("the pad's own look hidden once for the Geo rings", [x for x in c if x.startswith("ownvis")][:1] == ["ownvis false false"] and
      sum(x == "ownvis false false" for x in c) == 1)
geo_mats = [x[len("mmat 0 MID_"):] for x in c if x.startswith("mmat 0 MID_MI_Geo")]
check("each Geo instance on the surface, shape by shape, Con / Col / Ren / Pri", geo_mats == ["MI_Geo%s_%s" % (s, t) for s in
      ("Arch", "Gothic", "Square", "Door", "Round", "Oval") for t in ("Con", "Col", "Ren", "Pri")], geo_mats[:4])
ring_mats = [x[len("mmat 0 MID_"):] for x in c if x.startswith("mmat 0 MID_M_")]
check("then the 11 game rings on the same surface, untinted, at 1.8 x 1.8 m", ring_mats == rings_src[:-1] and not any(x.startswith("vec ") for x in c), ring_mats)
check("each at its starting size (door 1.75 x 3 m)", "mscale 1.750 3.000 1.000" in c and "mscale 1.800 1.800 1.000" in c)
tail = c[-6:]
check("at the end: surface removed, own look shown, own look and height back, own view back, camera removed",
      tail == ["mdestroy", "ownvis true false", "setasset Niagara_Portal", "ownloc 158.0", "view Player", "camdestroy"], tail)
check("end logged with the next step", has(L, "STILLS END (run finished: 67 designs; next: python tools\\dev\\make_previews.py)"))
check("each shot logged with its design", has(L, "---- STILL 1/67: Niagara_Portal (game,") and has(L, "---- STILL 56/67: Geo_Oval_Pri (geo, 1.40 x 2.00 m)")
      and has(L, "---- STILL 67/67: M_Portal_Arch (ring, 1.80 x 1.80 m)"))
n = len(calls(L))
press(L, "SCROLL_LOCK")
check("after the end, SCROLL LOCK starts over with a new camera", calls(L)[n:] == ["spawn CameraActor 100 300 158 yaw 270"], calls(L)[n:])

print("=== stand-in pad on a map with no portal (LuciDin, 15 Nov)")
src_standin = src[src.index("LK.st_standin = function()"):src.index("LK.st_drop_standin = function(pad)")]
check("stand-in: no untried call (INSERT's spawn and settings), nothing written to manual_exits.lua",
      "LK.untried(" not in src_standin and "mhe_save" not in src_standin and "io.open" not in src_standin)
L = lab()
stills_mode(L, "PADS = {}; LPAWN_X = 0; CONTROL_YAW = 0")
press(L, "SCROLL_LOCK")
c = calls(L)
check("1st press with no pad: a stand-in 4.5 m ahead on the floor, facing the player (yaw 180)", c[:1] == ["spawn pad 450 0 0 yaw 180"], c)
check("... named cordona_stills, leading nowhere, active (as INSERT's preview)",
      c[1:5] == ["standin set MyTeleporterID cordona_stills", "standin set DestinationTeleporterID None", "standin set IsTeleporterActive true", "standin onrep"], c)
check("... then the camera 3 m in front of it, between the pad and the player, looking at it", c[5:] == ["spawn CameraActor 150 0 158 yaw 0"], c)
check("logged with its place", has(L, "STILLS STAND-IN PAD (SCROLL LOCK, no pad within 15 m): at 450, 0, 0 facing yaw 180, 450 cm ahead of you"))
for _ in range(3):
    press(L, "SCROLL_LOCK")
drain(L)
check("the run uses the stand-in: the test shot + 67", calls(L).count("console shot") == 68, calls(L).count("console shot"))
check("at the end the stand-in is removed after the camera", calls(L)[-2:] == ["camdestroy", "standin destroy"], calls(L)[-4:])
check("end logged with it", has(L, "stand-in pad removed: true"))
L = lab()
stills_mode(L, "PADS = {}")
press(L, "SCROLL_LOCK")
press(L, "PAUSE")
check("PAUSE before the run: camera and stand-in removed", calls(L)[-2:] == ["camdestroy", "standin destroy"], calls(L))
L = lab()
L.execute("NO_CAMERA = true")
stills_mode(L, "PADS = {}")
press(L, "SCROLL_LOCK")
check("camera fails: the stand-in goes again (nothing left behind)", calls(L)[-1] == "standin destroy" and has(L, "no camera"), calls(L))
L = lab()
stills_mode(L, "PADS = { (st_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "SCROLL_LOCK")
check("a pad within 15 m: no stand-in", not any(x.startswith("spawn pad") for x in calls(L)), calls(L))

print("=== stopping, [ and a missing pak")
L = lab()
stills_mode(L)
for _ in range(4):
    press(L, "SCROLL_LOCK")
L.execute("pump(); pump(); pump()")
press(L, "SCROLL_LOCK")
n_shots = calls(L).count("console shot")
drain(L)
check("SCROLL LOCK during the run stops it: no shot afterwards", calls(L).count("console shot") == n_shots, n_shots)
check("stop logged and everything put back", has(L, "STILLS END (SCROLL LOCK during the run: stopped at") and calls(L)[-2:] == ["view Player", "camdestroy"], calls(L)[-3:])
L = lab()
stills_mode(L)
press(L, "SCROLL_LOCK"); press(L, "SCROLL_LOCK")
press(L, "OEM_FOUR")
check("[ out of stills mode ends it (own view back, camera removed)", calls(L)[-2:] == ["view Player", "camdestroy"] and has(L, "STILLS END ([)"), calls(L))
check("... and the mode is overlay again", has(L, "LOOK KEYS MODE ([): overlay"))
L = lab()
L.execute("OWN_PAK = false")
stills_mode(L)
for _ in range(4):
    press(L, "SCROLL_LOCK")
drain(L)
check("pak missing: the 32 game looks and 11 game rings shot, the 24 Geo rings skipped and noted", calls(L).count("console shot") == 44
      and sum(x.startswith("skip\t") for x in notes(L)) == 24, calls(L).count("console shot"))
check("... and the run still ends cleanly", has(L, "STILLS END (run finished"))
L = lab()
L.execute("NO_CAMERA = true")
stills_mode(L)
press(L, "SCROLL_LOCK")
check("no camera spawned: said, state kept clear", has(L, "no camera") and not any(x.startswith("spawn") for x in calls(L)))
L.execute("NO_CAMERA = false")
press(L, "SCROLL_LOCK")
check("... the next press tries step 1 again", calls(L)[-1].startswith("spawn CameraActor"), calls(L))
L = lab()
L.execute("NO_NOTES = true")
stills_mode(L)
press(L, "SCROLL_LOCK"); press(L, "SCROLL_LOCK"); press(L, "SCROLL_LOCK")
check("stills.txt unwritable: warned once, the shot still taken", has(L, "can't write ue4ss/Mods/PortalMaterialLab/stills.txt") and calls(L)[-1] == "console shot", calls(L)[-2:])

print("=== other modes unchanged")
L = lab()
L.execute("PADS = { (st_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "PAUSE")
check("overlay mode: PAUSE still says mesh mode only", has(L, "PAUSE: mesh mode only"))
for _ in range(3):
    press(L, "OEM_FOUR")
press(L, "PAUSE")
check("mesh mode: PAUSE still hides the pad's own look", calls(L)[-1] == "ownvis false false", calls(L))

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
