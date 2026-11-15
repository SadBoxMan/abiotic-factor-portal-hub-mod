# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py) and checks the
# CRD-039 portal-look keys: / survey (read-only), SCROLL LOCK material instance (window route through User.PortalTexture, ring route
# made on its own), U puts it on the effect with SetMaterial, . colour, , picture, L overlay (attached second look with parts off, removed on the last step). Also: each key
# names its untried native call before running it, nothing is written to a game object, no pad nearby is handled, keys bound once.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

LOOKS = r"""
CALLS2 = {}
local function rec(s) CALLS2[#CALLS2 + 1] = s end
local function obj(name, extra)
    local t = extra or {}
    t.IsValid = function() return true end
    t.GetFName = function() return FName(name) end
    t.GetFullName = function() return "Class /Game/" .. name end
    t.GetClass = function() return { IsValid = function() return true end, GetFName = function() return FName(name) end } end
    return setmetatable({}, { __index = t, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end })
end
function new_mid(of)
    return obj("MID_" .. of, {
        SetVectorParameterValue = function(self, n, v) rec("vec " .. n:ToString() .. " " .. v.R) end,
        SetTextureParameterValue = function(self, n, t) rec("tex " .. n:ToString() .. " " .. t:GetFName():ToString()) end,
    })
end
function new_effect(look, mats)
    local slots = {}
    for i, m in ipairs(mats) do slots[i - 1] = obj(m) end
    return obj("NiagaraComponent", {
        RelativeLocation = { X = 0, Y = 0, Z = 127.5 }, RelativeRotation = { Pitch = 0, Yaw = 90, Roll = 0 },
        RelativeScale3D = { X = 1, Y = 1, Z = 1 },
        GetAsset = function() return obj(look) end,
        GetNumMaterials = function() return #mats end,
        GetMaterial = function(self, i) return slots[i] end,
        CreateDynamicMaterialInstance = function(self, i, src, n) rec("cdmi " .. i .. " " .. src:GetFName():ToString()); slots[i] = new_mid(src:GetFName():ToString()); return slots[i] end,
        SetVariableMaterial = function(self, n, m) rec("varmat " .. n:ToString() .. " " .. m:GetFName():ToString()) end,
        SetVariableLinearColor = function(self, n, v) rec("varcol " .. n:ToString() .. " " .. v.R) end,
        SetMaterial = function(self, i, m) rec("setmat " .. i .. " " .. m:GetFName():ToString()) end,
        K2_SetRelativeLocation = function(self, l) rec(string.format("padloc %s %.1f %.1f %.1f", look, l.X, l.Y, l.Z)) end,
    })
end
function new_pad(id, look, mats, x, tex)
    return obj("BP_Teleporter_ParentBP_C", {
        MyTeleporterID = FName(id),
        ParticleLoop = new_effect(look, mats),
        PortalTexture = tex,
        PointLight = { LightColor = { R = 255, G = 61, B = 252 } },
        K2_GetActorLocation = function() return { X = x, Y = 0, Z = 0 } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = 183, Roll = 0 } end,
    })
end
LPAWN_X = 0
LPAWN = obj("Player", { K2_GetActorLocation = function() return { X = LPAWN_X, Y = 0, Z = 0 } end,
    Client_DisplayWarningMessage = function() end })
LPC = obj("PC", { Pawn = LPAWN })
PADS = {}
function FindFirstOf(name) if name == "Abiotic_PlayerController_C" then return LPC end return nil end
function FindAllOf(name) if name == "BP_Teleporter_ParentBP_C" then return PADS end return nil end
FX = {}
KISMET = obj("KML", { CreateDynamicMaterialInstance = function(self, ctx, parent, n, flags) rec("kml " .. parent:GetFName():ToString()); return new_mid(parent:GetFName():ToString()) end })
NFL = obj("NFL", { SpawnSystemAttached = function(self, sys, comp, sock, loc, rot, lt, ad, aa, pool, cull)
    local fx = obj("FX_" .. sys:GetFName():ToString(), {
        SetEmitterEnable = function(self, n, on) rec("emit " .. sys:GetFName():ToString() .. " " .. n:ToString() .. " " .. tostring(on)) end,
        K2_DestroyComponent = function() rec("destroy " .. sys:GetFName():ToString()) end,
        K2_SetRelativeLocation = function(self, l, sweep, hit, tp) rec(string.format("loc %s %d %d %d", sys:GetFName():ToString(), l.X, l.Y, l.Z)) end,
        SetRelativeScale3D = function(self, s) rec(string.format("scale %s %.3f %.3f %.3f", sys:GetFName():ToString(), s.X, s.Y, s.Z)) end,
    })
    rec("spawn " .. sys:GetFName():ToString() .. " lt=" .. lt .. " pool=" .. pool)
    return fx
end })
function StaticFindObject(path)
    if path == "/Script/Engine.Default__KismetMaterialLibrary" then return KISMET end
    if path == "/Script/Niagara.Default__NiagaraFunctionLibrary" then return NFL end
    local n = path:match("%.([%w_]+)$")
    if n and (path:find("/Game/Particles/") == 1) then return obj(n) end
    return nil
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
    L.execute(LOOKS)
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def calls(L):
    g = L.globals()
    return [g.CALLS2[i] for i in range(1, len(g.CALLS2) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


ev = lambda L, e: L.eval(e)


def press(L, key):
    L.execute("KEYS['%s'](); pump()" % key)      # pump: O / P act after a 40 ms game-thread window (CRD-041)


src = open(LAB, encoding="utf-8").read()
print("=== keys bound once, in the lab only")
for k, fn in (("OEM_TWO", "LK.survey"), ("SCROLL_LOCK", "LK.make_mid"), ("OEM_PERIOD", "LK.next_colour"), ("OEM_COMMA", "LK.next_picture"), ("L", "LK.next_overlay"), ("U", "LK.apply")):
    check(k + " bound to " + fn, re.search(r"RegisterKeyBind\(Key\.%s, function\(\) ExecuteInGameThread\(%s\)" % (k, re.escape(fn)), src))
    check(k + " bound once", len(re.findall(r"Key\.%s\b" % k, src)) == 1)
others = "".join(open(os.path.join(S, "..", "..", "..", "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey"))
check("no other mod of ours binds them", not re.search(r"Key\.(OEM_TWO|SCROLL_LOCK|OEM_PERIOD|OEM_COMMA|L|U|O|P|M|N|I|LEFT_ARROW|RIGHT_ARROW)\b", others))
check("no bare ExecuteWithDelay added", src.count("ExecuteWithDelay(") == 1)
check("one new main-chunk local", len(re.findall(r"^local LK\b", src, re.M)) == 1)

print("=== no pad nearby")
L = lab()
L.execute("PADS = { new_pad('hub_A3', 'Niagara_Portal_Friendly_Blue', { 'M_Portal_Friendly_Blue', 'M_Spark_1' }, 5000) }")
for k in ("OEM_TWO", "SCROLL_LOCK", "L"):
    press(L, k)
check("each says no pad within 15 m", sum("no pad within 15 m" in l for l in logs(L)) == 3, logs(L)[-3:])
check("no call made", calls(L) == [], calls(L))
press(L, "OEM_PERIOD")
check("colour before an instance asks for SCROLL LOCK", has(L, "colour: press SCROLL LOCK at a pad first"))

print("=== / survey (Friendly look)")
L = lab()
L.execute("PADS = { new_pad('hub_A4', 'Niagara_Portal_Salem', { 'M_Portal_Salem' }, 1400), new_pad('hub_A3', 'Niagara_Portal_Friendly_Blue', { 'M_Spark_1', 'M_Portal_Friendly_Blue' }, 300) }")
press(L, "OEM_TWO")
check("picks the nearest pad", has(L, "pad hub_A3, 3.0 m away, look Niagara_Portal_Friendly_Blue"), logs(L)[-8:])
check("logs PortalTexture variable", has(L, "pad's PortalTexture variable: none"))
check("logs the light", has(L, "light colour: 255, 61, 252"))
check("names GetMaterial before calling it", has(L, "untried native call next: NiagaraComponent:GetMaterial"))
check("logs the effect position relative to the pad", has(L, "effect relative to its pad: at 0.0, 0.0, 127.5; turned pitch 0.0 yaw 90.0") and has(L, "pad turned pitch 0.0 yaw 183.0"), logs(L)[-6:])
check("logs both slots", has(L, "slot 0: Class /Game/M_Spark_1") and has(L, "slot 1: Class /Game/M_Portal_Friendly_Blue"))
check("survey makes no change", calls(L) == [], calls(L))

print("=== SCROLL LOCK ring route (0 material slots in game), U, then . and ,")
press(L, "SCROLL_LOCK")
check("instance made from the look's ring material", "kml M_Portal_Friendly_Blue" in calls(L), calls(L))
check("names the Kismet call first", has(L, "untried native call next: KismetMaterialLibrary:CreateDynamicMaterialInstance"))
check("component CreateDynamicMaterialInstance no longer used", not any(x.startswith("cdmi") for x in calls(L)))
check("says to press U, expected index 1", has(L, "press U to put it on the effect (expected ring index 1)"), logs(L)[-2:])
press(L, "U")
check("SetMaterial on index 1", "setmat 1 MID_M_Portal_Friendly_Blue" in calls(L), calls(L)[-1:])
check("names SetMaterial first", has(L, "untried native call next: NiagaraComponent:SetMaterial"))
press(L, "U")
check("second U tries index 2", "setmat 2 MID_M_Portal_Friendly_Blue" in calls(L), calls(L)[-1:])
press(L, "OEM_PERIOD")
c = calls(L)
check("red on PortalCenterColor and 2", "vec PortalCenterColor 1.0" in c and "vec PortalCenterColor2 1.0" in c, c)
check("all six colour parameters tried", sum(x.startswith("vec ") for x in c) == 6, c)
check("no User.Color on a non-Rift look", not any(x.startswith("varcol") for x in c))
press(L, "OEM_PERIOD")
check("second press green", "vec PortalCenterColor 0.05" in calls(L))
press(L, "OEM_COMMA")
check("picture into PortalTexture", "tex PortalTexture TC_Portal_Warehouse" in calls(L), calls(L)[-2:])
press(L, "OEM_COMMA")
check("next picture", "tex PortalTexture TC_Portal_Fog" in calls(L))
check("names SetTextureParameterValue", has(L, "untried native call next: MaterialInstanceDynamic:SetTextureParameterValue"))
L2 = lab()
L2.execute("PADS = { new_pad('hub_A4', 'Niagara_Portal_Tiny', { 'M_Lightning' }, 100) }")
press(L2, "SCROLL_LOCK")
check("a look with no ring material: logged, nothing made", has(L2, "no ring material known for this look") and calls(L2) == [], calls(L2))
press(L2, "U")
check("U without an instance asks for SCROLL LOCK", has(L2, "apply: press SCROLL LOCK at a pad first"))

print("=== SCROLL LOCK window route (Blueverse with the game's window material)")
L = lab()
L.execute("PADS = { new_pad('H_Cabin_Entrance', 'Niagara_Portal_Blueverse', { 'M_Lightning', 'M_WorldPortal_HCabin' }, 100, StaticFindObject('/Game/Particles/Materials/M_WorldPortal_HCabin.M_WorldPortal_HCabin')) }")
press(L, "SCROLL_LOCK")
c = calls(L)
check("instance made from the pad's own window material", "kml M_WorldPortal_HCabin" in c, c)
check("put in User.PortalTexture", "varmat User.PortalTexture MID_M_WorldPortal_HCabin" in c, c)
check("names the Kismet call", has(L, "untried native call next: KismetMaterialLibrary:CreateDynamicMaterialInstance"))
check("component route not used", not any(x.startswith("cdmi") for x in c))
press(L, "OEM_COMMA")
check("window picture goes into PortalImage", "tex PortalImage TC_Portal_Warehouse" in calls(L), calls(L)[-1:])
L = lab()
L.execute("PADS = { new_pad('hub_B1', 'Niagara_Portal', { 'M_WorldPortal' }, 100) }")
press(L, "SCROLL_LOCK")
check("no window material on the pad: instance of M_WorldPortal", "kml M_WorldPortal" in calls(L), calls(L))

print("=== Rift: ColorMultiplier through the instance and User.Color")
L = lab()
L.execute("PADS = { new_pad('hub_C1', 'Niagara_Portal_Rift', { 'M_Heat_Distortion', 'M_Portal_Rift', 'M_Smoke_05' }, 100) }")
press(L, "SCROLL_LOCK")
press(L, "U")
press(L, "OEM_PERIOD")
c = calls(L)
check("instance of M_Portal_Rift on index 0", "kml M_Portal_Rift" in c and "setmat 0 MID_M_Portal_Rift" in c, c)
check("ColorMultiplier set", "vec ColorMultiplier 1.0" in c)
check("User.Color boosted x6", "varcol User.Color 6.0" in c, c)

print("=== L overlay cycle")
L = lab()
L.execute("PADS = { new_pad('hub_A3', 'Niagara_Portal_Friendly_Blue', { 'M_Portal_Friendly_Blue' }, 100) }")
press(L, "L")
c = calls(L)
check("Garden attached, relative offset, no pooling", "spawn Niagara_Portal_Garden lt=0 pool=0" in c, c)
check("Garden's ring and sparks off, vines kept", "emit Niagara_Portal_Garden portal false" in c and "emit Niagara_Portal_Garden sparks false" in c
      and not any("Vine" in x for x in c), c)
check("names SpawnSystemAttached", has(L, "untried native call next: NiagaraFunctionLibrary:SpawnSystemAttached"))
press(L, "L")
c = calls(L)
check("second press removes Garden, adds SnowFlurry", "destroy Niagara_Portal_Garden" in c and "spawn Niagara_Portal_SnowFlurry lt=0 pool=0" in c, c)
check("SnowFlurry keeps Swirl and snowflakes", "emit Niagara_Portal_SnowFlurry Blackhole false" in c and not any("Swirl" in x or "snowflakes" in x for x in c))
for _ in range(4):
    press(L, "L")
check("sixth press: off, last overlay removed", has(L, "OVERLAY (L): off") and "destroy Niagara_Portal_Friendly_Red" in calls(L), calls(L)[-3:])
press(L, "L")
check("then starts over with Garden", calls(L)[-3] == "spawn Niagara_Portal_Garden lt=0 pool=0", calls(L)[-3:])

print("=== overlay fit: O / P / M / N")
for k in ("M", "N", "I", "LEFT_ARROW", "RIGHT_ARROW"):
    check(k + " bound once", len(re.findall(r"Key\.%s\b" % k, src)) == 1)
for k in ("O", "P"):
    check(k + " bound twice: plain and Shift (CRD-041)", len(re.findall(r"Key\.%s\b" % k, src)) == 2)
L = lab()
L.execute("PADS = { new_pad('hub_A3', 'Niagara_Portal_Friendly_Red', { 'M_Portal_Friendly_Red' }, 100) }")
press(L, "O"); press(L, "O"); press(L, "P"); press(L, "P"); press(L, "P")
check("no overlay: O / P move the pad's own look (127.5 -> 117.5)", calls(L)[-1] == "padloc Niagara_Portal_Friendly_Red 0.0 0.0 117.5", calls(L)[-5:])
check("logs the height", has(L, "PORTAL HEIGHT (O/P): hub_A3 (Niagara_Portal_Friendly_Red): effect at 117.5 cm above the pad (was 127.5, offset -10 cm)"), logs(L)[-1:])
L.execute("PADS[1] = new_pad('hub_A3', 'Niagara_Portal_Friendly_Red', { 'M_Portal_Friendly_Red' }, 100)")
press(L, "O")
check("a respawned pad starts from its own height again", calls(L)[-1] == "padloc Niagara_Portal_Friendly_Red 0.0 0.0 137.5", calls(L)[-1:])
L.execute("PADS = { new_pad('hub_A3', 'Niagara_Portal_Friendly_Red', { 'M_Portal_Friendly_Red' }, 100) }; CALLS2 = {}")
press(L, "L")
press(L, "O"); press(L, "O"); press(L, "P")
check("up, up, down = +10 cm", calls(L)[-1] == "loc Niagara_Portal_Garden 0 0 10", calls(L)[-3:])
check("names K2_SetRelativeLocation", has(L, "untried native call next: SceneComponent:K2_SetRelativeLocation"))
check("logs the fit", has(L, "OVERLAY FIT (O/P): Niagara_Portal_Garden: offset X +0 Y +0 Z +10 cm, scale X 1.00 Y 1.00 Z 1.00 (M/N axis: all)"), logs(L)[-1:])
press(L, "M"); press(L, "M")
check("bigger twice = x1.21", calls(L)[-1] == "scale Niagara_Portal_Garden 1.210 1.210 1.210", calls(L)[-2:])
press(L, "N")
check("smaller once = x1.10", calls(L)[-1] == "scale Niagara_Portal_Garden 1.100 1.100 1.100", calls(L)[-1:])
press(L, "RIGHT_ARROW"); press(L, "RIGHT_ARROW"); press(L, "LEFT_ARROW")
check("right, right, left = Y +10, height kept", calls(L)[-1] == "loc Niagara_Portal_Garden 0 10 10", calls(L)[-1:])
press(L, "I")
check("I: axis X", has(L, "M / N now scale X; LEFT / RIGHT move along X"))
press(L, "M")
check("M on X only", calls(L)[-1] == "scale Niagara_Portal_Garden 1.210 1.100 1.100", calls(L)[-1:])
press(L, "LEFT_ARROW")
check("arrows move along X in X mode", calls(L)[-1] == "loc Niagara_Portal_Garden -10 10 10", calls(L)[-1:])
press(L, "I")
press(L, "N")
check("I again: Y only", calls(L)[-1] == "scale Niagara_Portal_Garden 1.210 1.000 1.100", calls(L)[-1:])
press(L, "I"); press(L, "I")
check("I cycles back to all", has(L, "M / N now scale all"))
check("names SetRelativeScale3D", has(L, "untried native call next: SceneComponent:SetRelativeScale3D"))
press(L, "L")
press(L, "O")
check("next overlay starts again at 0 cm (one O = +10)", calls(L)[-1] == "loc Niagara_Portal_SnowFlurry 0 0 10", calls(L)[-1:])
press(L, "M")
check("and at x1.0 on all axes (one M = x1.10)", calls(L)[-1] == "scale Niagara_Portal_SnowFlurry 1.100 1.100 1.100", calls(L)[-1:])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
