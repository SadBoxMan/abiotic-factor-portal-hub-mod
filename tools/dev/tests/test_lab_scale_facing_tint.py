# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game and checks the CRD-042 keys: [ switches the look keys
# between overlay (CRD-039, unchanged), own (scale and turn the nearest pad's OWN effect per axis, reset, renderer survey, ring facing
# edit with ReinitializeSystem) and tint (a grey ring material in a window look's User.PortalTexture, tinted by RGB, picture in it).
# Also: each untried call is named before it runs, nothing is written to a game object except the renderer's FacingMode in U, keys
# bound once, no other mod binds [, no new main-chunk local, no bare ExecuteWithDelay.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)
LOOKS_MOCK = re.search(r'LOOKS = r"""(.*?)"""', open(os.path.join(S, "test_lab_looks.py"), encoding="utf-8").read(), re.S).group(1)

PADS = r"""
-- A pad whose effect keeps its scale, turn and look, and records the calls.
function sft_pad(id, look, x)
    local cur = { look = look, s = { X = 1, Y = 1, Z = 1 }, r = { Pitch = 0, Yaw = 90, Roll = 0 } }
    local t = { IsValid = function() return true end, GetFName = function() return FName("NiagaraComponent") end,
        GetAddress = function() return id .. "_fx_" .. tostring(cur) end }
    t.GetAsset = function() return StaticFindObject("/Game/Particles/" .. cur.look .. "." .. cur.look) end
    t.SetRelativeScale3D = function(self, s) cur.s = { X = s.X, Y = s.Y, Z = s.Z }; CALLS2[#CALLS2 + 1] = string.format("ownscale %.3f %.3f %.3f", s.X, s.Y, s.Z) end
    t.K2_SetRelativeRotation = function(self, r) cur.r = { Pitch = r.Pitch, Yaw = r.Yaw, Roll = r.Roll }; CALLS2[#CALLS2 + 1] = string.format("ownrot %d %d %d", r.Pitch, r.Yaw, r.Roll) end
    t.K2_SetRelativeLocation = function(self, l) CALLS2[#CALLS2 + 1] = string.format("ownloc %.1f", l.Z) end
    t.SetVariableMaterial = function(self, n, m) CALLS2[#CALLS2 + 1] = "varmat " .. n:ToString() .. " " .. m:GetFName():ToString() end
    t.ReinitializeSystem = function() CALLS2[#CALLS2 + 1] = "reinit" end
    local fx = setmetatable({}, { __index = function(_, k)
        if k == "RelativeLocation" then return { X = 0, Y = 0, Z = 158 } end
        if k == "RelativeScale3D" then return cur.s end
        if k == "RelativeRotation" then return cur.r end
        return t[k] end, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end })
    local p = { IsValid = function() return true end, GetFName = function() return FName("BP_Teleporter_ParentBP_C") end,
        MyTeleporterID = FName(id), ParticleLoop = fx,
        K2_GetActorLocation = function() return { X = x, Y = 0, Z = 0 } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end }
    return setmetatable({}, { __index = p, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end }), cur
end
-- Renderer objects: only FacingMode may be written.
function renderer(look, part, mesh, facing, align)
    local st = { FacingMode = facing, Alignment = align }
    local cls = mesh and "NiagaraMeshRendererProperties" or "NiagaraSpriteRendererProperties"
    return setmetatable({}, {
        __index = function(_, k)
            if k == "IsValid" then return function() return true end end
            if k == "GetFullName" then return function() return cls .. " /Game/Particles/" .. look .. "." .. look .. ":" .. part .. "." .. cls .. "_0" end end
            if k == "FacingMode" then return st.FacingMode end
            if k == "Alignment" and not mesh then return st.Alignment end
            return nil
        end,
        __newindex = function(_, k, v)
            if k ~= "FacingMode" then error("the lab wrote renderer " .. tostring(k)) end
            st.FacingMode = v; CALLS2[#CALLS2 + 1] = "facing " .. look .. " " .. part .. " " .. tostring(v)
        end }), st
end
RENDERERS = { NiagaraSpriteRendererProperties = {}, NiagaraMeshRendererProperties = {} }
local oldFind = FindAllOf
function FindAllOf(name) if RENDERERS[name] then return RENDERERS[name] end return oldFind(name) end
-- MIDs that answer K2_GetVectorParameterValue with Friendly White's cooked values.
GREYS = { PortalCenterColor = { R = 0.109, G = 0.109, B = 0.109 }, PortalCenterColor2 = { R = 1, G = 1, B = 1 }, PortalEdge = { R = 5, G = 4.816, B = 4.557 } }
local oldMid = new_mid
function new_mid(of)
    local m = { IsValid = function() return true end, GetFName = function() return FName("MID_" .. of) end,
        SetVectorParameterValue = function(self, n, v) CALLS2[#CALLS2 + 1] = string.format("vec %s %.3f %.3f %.3f", n:ToString(), v.R, v.G, v.B) end,
        SetTextureParameterValue = function(self, n, t) CALLS2[#CALLS2 + 1] = "tex " .. n:ToString() .. " " .. t:GetFName():ToString() end,
        K2_GetVectorParameterValue = function(self, n) local c = GREYS[n:ToString()]; if not c then error("no such parameter") end return c end }
    return setmetatable({}, { __index = m, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end })
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
    L.execute("KEYS['%s'](); pump()" % key)   # pump: O / P act after CRD-041's 40 ms game-thread window


src = open(LAB, encoding="utf-8").read()
print("=== key")
check("[ bound to LK.next_mode", re.search(r"RegisterKeyBind\(Key\.OEM_FOUR, function\(\) ExecuteInGameThread\(LK\.next_mode\)", src))
check("[ bound once", len(re.findall(r"Key\.OEM_FOUR\b", src)) == 1)
others = "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey"))
check("no other mod of ours binds [", "Key.OEM_FOUR" not in others)
check("no bare ExecuteWithDelay added", src.count("ExecuteWithDelay(") == 1)
block = src[src.index("-- Look scale, facing and grey tint (CRD-042"):src.index('RegisterKeyBind(Key.O, ')]
check("no new main-chunk local in the CRD-042 block", not re.search(r"^local ", block, re.M))

print("=== mode cycle")
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "OEM_FOUR")
check("[ -> own, logged", has(L, "LOOK KEYS MODE ([): own"))
press(L, "OEM_FOUR")
check("[ -> tint", has(L, "LOOK KEYS MODE ([): tint"))
press(L, "OEM_FOUR")
check("[ -> back to overlay", logs(L)[-1].find("LOOK KEYS MODE ([): overlay") >= 0 or any("LOOK KEYS MODE ([): overlay" in l for l in logs(L)[-2:]), logs(L)[-2:])
check("mode switch alone makes no call", calls(L) == [], calls(L))

print("=== overlay mode unchanged: M without an overlay still asks for L")
press(L, "M")
check("M in overlay mode: press L first", has(L, "overlay scale: no overlay (press L first)") and calls(L) == [], calls(L))

print("=== own mode: scale per axis")
L = lab()
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100)) }")
press(L, "OEM_FOUR")
press(L, "M")
check("M scales the pad's own effect on all axes x1.1", calls(L)[-1] == "ownscale 1.100 1.100 1.100", calls(L))
check("names SetRelativeScale3D on the own effect first", has(L, "untried native call next: SceneComponent:SetRelativeScale3D on the pad's own effect"))
check("logs the start scale and turn", has(L, "pad hub_A3 starts at scale 1.00, 1.00, 1.00, turned pitch 0.0 yaw 90.0 roll 0.0"))
check("logs the new values", has(L, "OWN LOOK SCALE (M/N): hub_A3 (Niagara_Portal_Friendly_Red): scale X 1.10 Y 1.10 Z 1.10"), logs(L)[-2:])
press(L, "I"); press(L, "M"); press(L, "M")
check("I -> X: M M on X only (1.331 / 1.1 / 1.1)", calls(L)[-1] == "ownscale 1.331 1.100 1.100", calls(L)[-1])
press(L, "I"); press(L, "N")
check("I -> Y: N on Y only", calls(L)[-1] == "ownscale 1.331 1.000 1.100", calls(L)[-1])
press(L, "I"); press(L, "N")
check("I -> Z: N on Z only (up/down)", calls(L)[-1] == "ownscale 1.331 1.000 1.000", calls(L)[-1])

print("=== own mode: turn")
press(L, "LEFT_ARROW")
check("axis Z: LEFT turns yaw -15 from 90", calls(L)[-1] == "ownrot 0 75 0", calls(L)[-1])
check("names K2_SetRelativeRotation first", has(L, "untried native call next: SceneComponent:K2_SetRelativeRotation on the pad's own effect"))
press(L, "I")   # all
press(L, "RIGHT_ARROW"); press(L, "RIGHT_ARROW")
check("axis all: RIGHT RIGHT = yaw +15 net 105", calls(L)[-1] == "ownrot 0 105 0", calls(L)[-1])
press(L, "I")   # X
press(L, "RIGHT_ARROW")
check("axis X: roll +15", calls(L)[-1] == "ownrot 0 105 15", calls(L)[-1])
press(L, "I")   # Y
press(L, "LEFT_ARROW")
check("axis Y: pitch -15", calls(L)[-1] == "ownrot -15 105 15", calls(L)[-1])
check("overlay offset untouched (no overlay calls)", not any(x.startswith("loc ") for x in calls(L)))

print("=== own mode: O / P height, SCROLL LOCK reset")
press(L, "O")
check("O moves the own look up 10 cm", calls(L)[-1] == "ownloc 168.0", calls(L)[-1])
L.execute("KEYS['O+SHIFT'](); KEYS['O'](); pump()")
check("Shift + O in own mode: 1 cm (finest step wins)", calls(L)[-1] == "ownloc 169.0", calls(L)[-1])
press(L, "SCROLL_LOCK")
c = calls(L)
check("SCROLL LOCK puts scale and turn back", c[-2] == "ownscale 1.000 1.000 1.000" and c[-1] == "ownrot 0 90 0", c[-2:])
press(L, "SCROLL_LOCK")
check("a second reset with nothing changed makes no call", calls(L) == c and has(L, "scale back not scaled, turn back not turned"), calls(L)[-2:])
check("reset logged", has(L, "OWN LOOK RESET (SCROLL LOCK): hub_A3"))
check("no material instance made in own mode", not any(x.startswith("kml") for x in c))
press(L, "M")
check("after reset M starts from x1.0 again", calls(L)[-1] == "ownscale 1.000 1.100 1.000" or calls(L)[-1] == "ownscale 1.100 1.100 1.100", calls(L)[-1])
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100)) }")
press(L, "I"); press(L, "I")
press(L, "M")
check("a respawned pad starts from its own scale again", calls(L)[-1] == "ownscale 1.100 1.100 1.100", calls(L)[-1])

print("=== own mode: no pad")
L = lab()
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal', 5000)) }")
press(L, "OEM_FOUR")
for k in ("M", "LEFT_ARROW", "SCROLL_LOCK", "OEM_TWO", "U"):
    press(L, k)
check("every own-mode key says no pad within 15 m, no call", sum("no pad within 15 m" in l for l in logs(L)) == 5 and calls(L) == [], calls(L))

print("=== own mode: renderer survey and ring facing (Friendly mesh, Default sprite)")
L = lab()
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal_Friendly_White', 100)) }")
L.execute("""
RING, RINGST = renderer('Niagara_Portal_Friendly_White', 'portal_0', true, 2)
RENDERERS.NiagaraMeshRendererProperties = { RING, (renderer('Niagara_Portal_Garden', 'Vine1_0', true, 0)) }
RENDERERS.NiagaraSpriteRendererProperties = { (renderer('Niagara_Portal_Friendly_White', 'sparks_0', false, 2, 0)), (renderer('Niagara_Portal', 'portalmap_1', false, 2, 2)) }
""")
press(L, "OEM_FOUR")
press(L, "U")
check("U before / asks for / first, no call", has(L, "ring facing: press / (own mode) first") and calls(L) == [], calls(L))
press(L, "OEM_TWO")
check("/ in own mode: renderer survey of this look only (2)", has(L, "RENDERER SURVEY (/ in own mode): Niagara_Portal_Friendly_White on hub_A3: 2 renderer(s)"), logs(L)[-4:])
check("ring marked, mesh, CameraPosition", has(L, "RING portal: MESH, facing CameraPosition"), logs(L)[-3:])
check("sparks sprite with alignment", has(L, "sparks: SPRITE, facing CustomFacingVector, alignment Unaligned"))
check("survey writes nothing", calls(L) == [], calls(L))
check("names the renderer read first", has(L, "untried native call next: FindAllOf on Niagara renderer properties, reading FacingMode / Alignment"))
press(L, "U")
c = calls(L)
check("first U: only the write (CameraPosition -> CameraPlane), no restart", c == ["facing Niagara_Portal_Friendly_White portal_0 3"], c)
check("write read back and logged", has(L, "written; reads back CameraPlane"))
check("warns it is a run-time edit of the look's asset (every pad)", has(L, "run-time edit of the look's asset: EVERY pad with this look changes until the game restarts"))
check("names the write first (enum byte)", has(L, "untried native call next: writing FacingMode (enum byte) on a renderer properties object"))
check("ReinitializeSystem not named on the write press", not has(L, "untried native call next: NiagaraComponent:ReinitializeSystem"))
press(L, "U")
c = calls(L)
check("second U: only ReinitializeSystem", c[-1] == "reinit" and len(c) == 2, c)
check("names ReinitializeSystem first", has(L, "untried native call next: NiagaraComponent:ReinitializeSystem"))
check("restart line repeats the every-pad warning", has(L, "RING FACING RESTART (U in own mode, second press)") and has(L, "stays changed on EVERY pad"))
for _ in range(6):
    press(L, "U")
check("eight U (4 writes + 4 restarts) = round to the start (mesh has 4 modes)", L.eval("RINGST.FacingMode") == 2 and calls(L).count("reinit") == 4, (L.eval("RINGST.FacingMode"), calls(L)))
check("start remembered in the log", has(L, "(look's own start: CameraPosition)"))
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "U")
check("Default: portalmap is the ring, sprite CustomFacingVector -> FaceCameraPosition", calls(L)[-1] == "facing Niagara_Portal portalmap_1 3", calls(L)[-2:])
L.execute("PADS = { (sft_pad('hub_C1', 'Niagara_Portal_Tiny', 100)) }")
press(L, "U")
check("another pad's effect: no restart of it, a fresh write try instead (Tiny: no ring, logged)", has(L, "ring facing: no ring renderer found for Niagara_Portal_Tiny") and calls(L).count("reinit") == 4 and not any("Tiny" in x for x in calls(L)), calls(L)[-2:])

print("=== tint mode: grey ring in a window look")
L = lab()
L.execute("PADS = { (sft_pad('hub_B1', 'Niagara_Portal', 100)) }")
press(L, "OEM_FOUR"); press(L, "OEM_FOUR")
press(L, "SCROLL_LOCK")
c = calls(L)
check("instance of Friendly White made", "kml M_Portal_Friendly_White" in c, c)
check("put in User.PortalTexture", "varmat User.PortalTexture MID_M_Portal_Friendly_White" in c, c)
check("names K2_GetVectorParameterValue first", has(L, "untried native call next: MaterialInstanceDynamic:K2_GetVectorParameterValue"))
check("grey levels read from the instance", has(L, "Grey levels: centre 0.109, centre 2 1.000, edge 4.836"), [l for l in logs(L) if "Grey" in l])
press(L, "OEM_PERIOD")
check("first tint white: values as they are", "vec PortalCenterColor2 1.000 1.000 1.000" in calls(L), calls(L)[-3:])
press(L, "OEM_PERIOD")
c = calls(L)[-3:]
check("red: grey x RGB on all three", c == ["vec PortalCenterColor 0.109 0.005 0.005", "vec PortalCenterColor2 1.000 0.050 0.050", "vec PortalEdge 4.836 0.242 0.242"], c)
check("tint logged", has(L, "TINT (. in tint mode): red = RGB 1.00, 0.05, 0.05 on hub_B1 (M_Portal_Friendly_White)"))
press(L, "OEM_COMMA")
check(", puts a picture in the ring's PortalTexture", calls(L)[-1] == "tex PortalTexture TC_Portal_Warehouse", calls(L)[-1])
press(L, "SCROLL_LOCK")
check("next ring: Friendly (parent)", "kml M_Portal_Friendly" in calls(L) and calls(L)[-1] == "varmat User.PortalTexture MID_M_Portal_Friendly", calls(L)[-2:])
L.execute("for i = 1, 10 do KEYS['SCROLL_LOCK']() end")
check("12th ring: plain M_WorldPortal (window back)", calls(L)[-1] == "varmat User.PortalTexture MID_M_WorldPortal", calls(L)[-1])
press(L, "OEM_COMMA")
check("picture on the plain window goes into PortalImage", calls(L)[-1].startswith("tex PortalImage "), calls(L)[-1])
L.execute("GREYS = {}")
press(L, "SCROLL_LOCK")
check("unreadable instance: falls back to Friendly White's grey", has(L, "Grey levels: centre 0.109, centre 2 1.000, edge 4.840"), [l for l in logs(L) if "Grey" in l][-1:])

print("=== tint mode: not a window look, no instance yet")
L = lab()
L.execute("PADS = { (sft_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100)) }")
press(L, "OEM_FOUR"); press(L, "OEM_FOUR")
press(L, "OEM_PERIOD")
check(". before SCROLL LOCK asks for it", has(L, "tint: press SCROLL LOCK (tint mode) at a window-look pad first") and calls(L) == [], calls(L))
press(L, "SCROLL_LOCK")
check("Friendly pad: window looks only, nothing made", has(L, "is not a window look") and calls(L) == [], calls(L))
press(L, "U")
check("U in tint mode does nothing to the effect", calls(L) == [], calls(L))

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
