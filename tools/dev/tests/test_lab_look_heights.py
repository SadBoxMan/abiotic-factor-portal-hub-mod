# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game and checks the CRD-041 look-height key:
# ; steps the nearest pad through all 32 looks (SetAsset, in DESIGN_NAMES order, starting after the pad's own look), keeps a height
# per look (LuciDin's picks first, else the pad's own height), O / P change the current look's height, one LOOK HEIGHT line per change
# (the line tools/dev/portal_heights_from_log.py reads), a table of heights when the cycle wraps, and the old O / P without ;.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)
LOOKS_MOCK = re.search(r'LOOKS = r"""(.*?)"""', open(os.path.join(S, "test_lab_looks.py"), encoding="utf-8").read(), re.S).group(1)
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
import hubdata

PADS = r"""
-- A pad whose effect remembers the look SetAsset gave it and where it was moved.
function cyc_pad(id, look, x, z)
    local cur = { look = look, z = z or 158 }
    local t = { IsValid = function() return true end, GetFName = function() return FName("NiagaraComponent") end,
        GetAddress = function() return id .. "_fx_" .. tostring(cur) end }
    t.GetAsset = function() return StaticFindObject("/Game/Particles/" .. cur.look .. "." .. cur.look) end
    t.SetAsset = function(self, sys, reset) cur.look = sys:GetFName():ToString(); CALLS2[#CALLS2 + 1] = "asset " .. cur.look .. " " .. tostring(reset) end
    t.Activate = function(self, r) CALLS2[#CALLS2 + 1] = "activate" end
    t.K2_SetRelativeLocation = function(self, l) cur.z = l.Z; CALLS2[#CALLS2 + 1] = string.format("z %s %.1f", cur.look, l.Z) end
    local fx = setmetatable({}, { __index = function(_, k)
        if k == "RelativeLocation" then return { X = 0, Y = 0, Z = cur.z } end
        return t[k] end, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end })
    local p = { IsValid = function() return true end, GetFName = function() return FName("BP_Teleporter_ParentBP_C") end,
        MyTeleporterID = FName(id), ParticleLoop = fx,
        K2_GetActorLocation = function() return { X = x, Y = 0, Z = 0 } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end }
    return setmetatable({}, { __index = p, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end }), cur
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


def heights(L):
    return [l[l.index("---- LOOK HEIGHT:"):].strip() for l in logs(L) if "---- LOOK HEIGHT:" in l]


def press(L, key):
    L.execute("KEYS['%s']()" % key)


src = open(LAB, encoding="utf-8").read()
print("=== key")
check("; bound to LK.next_look", re.search(r"RegisterKeyBind\(Key\.OEM_ONE, function\(\) ExecuteInGameThread\(LK\.next_look\)", src))
check("; bound once", len(re.findall(r"Key\.OEM_ONE\b", src)) == 1)
others = "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey"))
check("no other mod of ours binds ;", "Key.OEM_ONE" not in others)
check("no bare ExecuteWithDelay added", src.count("ExecuteWithDelay(") == 1)
L = lab()
lab_looks = re.findall(r'"(Niagara_Portal\w*)"', re.search(r"LK\.LOOKS = \{(.*?)\}", src, re.S).group(1))
check("the lab's 32 looks are the editor's DESIGN_NAMES, same order", lab_looks == hubdata.DESIGN_NAMES, lab_looks)

print("=== no pad nearby")
L.execute("PADS = { (cyc_pad('hub_B1', 'Niagara_Portal', 5000)) }")
press(L, "OEM_ONE")
check("says no pad within 15 m, no call", any("look heights: no pad within 15 m" in l for l in logs(L)) and calls(L) == [], calls(L))

print("=== cycle from the pad's own look")
L = lab()
L.execute("PADS = { (cyc_pad('hub_B1', 'Niagara_Portal_Dark', 100)) }")
press(L, "OEM_ONE")
c = calls(L)
check("first ; = the look after the pad's own (Dark -> Door)", c[:3] == ["asset Niagara_Portal_Door true", "activate", "z Niagara_Portal_Door 158.0"], c)
check("start line names the pad's own look and height", any("LOOK HEIGHTS (;): pad hub_B1, its own look Niagara_Portal_Dark, game default height 158.0 cm" in l for l in logs(L)))
check("Door starts at LuciDin's pick (158)", heights(L)[-1] == "---- LOOK HEIGHT: Niagara_Portal_Door | game default 158.0 cm | set 158.0 cm | offset +0.0 cm | pad hub_B1 (6/32)", heights(L))
press(L, "O"); press(L, "O"); press(L, "P")
check("O, O, P: Door +10 = 168", calls(L)[-1] == "z Niagara_Portal_Door 168.0", calls(L)[-3:])
check("each O / P logs a line", len(heights(L)) == 4 and heights(L)[-1].startswith("---- LOOK HEIGHT: Niagara_Portal_Door | game default 158.0 cm | set 168.0 cm | offset +10.0 cm"), heights(L))
check("O / P with ; on do not use the old PORTAL HEIGHT path", not any("PORTAL HEIGHT (O/P)" in l for l in logs(L)))
press(L, "OEM_ONE")
check("next: Fog at the pad's own height (no pick)", calls(L)[-3:] == ["asset Niagara_Portal_Fog true", "activate", "z Niagara_Portal_Fog 158.0"], calls(L)[-3:])
press(L, "P"); press(L, "P"); press(L, "P")
check("Fog -30 = 128", calls(L)[-1] == "z Niagara_Portal_Fog 128.0")
for _ in range(31):
    press(L, "OEM_ONE")
check("31 more ; come back to Door at its kept 168", calls(L)[-1] == "z Niagara_Portal_Door 168.0", calls(L)[-3:])
check("wrap logged a heights table", any("LOOK HEIGHTS so far (hub_B1)" in l for l in logs(L)) and any("  Niagara_Portal_Fog = 128.0 cm" in l for l in logs(L)))
order = [x.split()[1] for x in calls(L) if x.startswith("asset ")]
check("cycle order: DESIGN_NAMES from Door, wrapping", order[:33] == (hubdata.DESIGN_NAMES[5:] + hubdata.DESIGN_NAMES[:6])[:33], order[:8])
seen = {}
for l in heights(L):
    m = re.match(r"---- LOOK HEIGHT: (\S+) \| game default ([\d.]+) cm \| set ([\d.]+) cm", l)
    seen[m.group(1)] = float(m.group(3))
check("all 32 looks logged", len(seen) == 32, len(seen))
check("picks used: Friendly Red 108, Default 118, Botanical Red 138",
      seen["Niagara_Portal_Friendly_Red"] == 108 and seen["Niagara_Portal"] == 118 and seen["Niagara_Portal_Botanical_Red"] == 138, seen)
check("Fog kept at 128 through the wrap", seen["Niagara_Portal_Fog"] == 128)
L2 = lab()
L2.execute("PADS = { (cyc_pad('H_Garden_Entrance', 'Niagara_Portal_Garden', 100, 138.3)) }")
press(L2, "OEM_ONE")
check("a fresh session on Stone Garden: unpicked look starts at the pad's own 138.3", calls(L2)[-1] == "z Niagara_Portal_Greenverse 138.3", calls(L2)[-3:])

print("=== another pad: heights kept per look, its own default")
L.execute("PADS = { (cyc_pad('H_Garden_Entrance', 'Niagara_Portal_Garden', 100, 138.3)) }")
press(L, "OEM_ONE")
check("Stone Garden: starts after Garden (Greenverse), at its height kept from hub_B1 (158)", calls(L)[-1] == "z Niagara_Portal_Greenverse 158.0", calls(L)[-3:])
check("line shows this pad's game default 138.3", heights(L)[-1].startswith("---- LOOK HEIGHT: Niagara_Portal_Greenverse | game default 138.3 cm | set 158.0 cm | offset +19.7 cm | pad H_Garden_Entrance (23/32)"), heights(L)[-1])
L.execute("for i = 1, 16 do KEYS['OEM_ONE']() end")
check("Fog's kept height follows the look to this pad (128, offset -10.3)", calls(L)[-1] == "z Niagara_Portal_Fog 128.0" and "offset -10.3 cm" in heights(L)[-1], (calls(L)[-1], heights(L)[-1]))

print("=== without ;: old O / P path unchanged")
L = lab()
L.execute("PADS = { (cyc_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100, 127.5)) }")
press(L, "P")
check("O / P before any ; move the pad's look as before", calls(L)[-1] == "z Niagara_Portal_Friendly_Red 117.5" and any("PORTAL HEIGHT (O/P): hub_A3" in l for l in logs(L)), calls(L))
check("no LOOK HEIGHT line", heights(L) == [])
L.execute("PADS = { (cyc_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100, 127.5)) }")
press(L, "OEM_ONE")
L.execute("PADS = { (cyc_pad('hub_A3', 'Niagara_Portal_Friendly_Red', 100, 158)) }")
press(L, "O")
check("a respawned pad (new effect) drops back to the old O / P", any("PORTAL HEIGHT (O/P)" in l for l in logs(L)[-2:]), logs(L)[-2:])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
