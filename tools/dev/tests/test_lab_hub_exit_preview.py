# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py) and checks the
# CRD-012 Hub Exit preview (INSERT): a pad at the last F2 spot (feet, saved yaw) that leads to the last hub-room portal used; a new F2 spot
# moves it, the same spot removes it; without an F2 spot nothing is spawned.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

GAME = r"""
SAID = {}
WHERE = { X = 1000, Y = 2000, Z = 388 }      -- capsule centre; feet are 88 lower
YAW = 90.4
PPAWN = { IsValid = function() return true end, GetFName = function() return FName("Player_C_0") end,
    K2_GetActorLocation = function() return { X = WHERE.X, Y = WHERE.Y, Z = WHERE.Z } end,
    CapsuleComponent = { IsValid = function() return true end, GetScaledCapsuleHalfHeight = function() return 88 end },
    Client_DisplayWarningMessage = function(self, t) SAID[#SAID + 1] = t:ToString() end }
PPC = { IsValid = function() return true end, Pawn = PPAWN, GetControlRotation = function() return { Pitch = 0, Yaw = YAW, Roll = 0 } end }
PADS = {}
local padClass = { IsValid = function() return true end, kind = "pad" }
local look = { IsValid = function() return true end }
PWORLD = { IsValid = function() return true end, SpawnActor = function(self, cls, loc, rot)
    local a = { loc = loc, yaw = rot.Yaw, active = false }
    a.IsValid = function() return not a.gone end
    a.K2_DestroyActor = function() a.gone = true end
    a.OnRep_IsTeleporterActive = function() end
    a.ParticleLoop = { SetAsset = function(self, s) a.look = s end, Activate = function() end }
    PADS[#PADS + 1] = a
    return a end }
PPC.GetWorld = function() return PWORLD end
package.preload["UEHelpers"] = function() return { GetWorld = function() return PWORLD end } end
local ff, fa, sf = FindFirstOf, FindAllOf, StaticFindObject
function FindFirstOf(n) if n == "Abiotic_PlayerController_C" then return PPC end return ff(n) end
function FindAllOf(n)
    if n == "BP_Teleporter_ParentBP_C" then local o = {}; for _, p in ipairs(PADS) do if not p.gone then o[#o + 1] = p end end; return o end
    return fa(n)
end
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
    if p == "/Game/Particles/Niagara_Portal.Niagara_Portal" then return look end
    return sf(p)
end
io.open = function() return nil end           -- saved_positions.txt is not written in the test
function live() local o = {}; for _, p in ipairs(PADS) do if not p.gone then o[#o + 1] = p end end; return o end
function use_pad(id, dest)                     -- the lab's passive pad-use hook sees a pad being used
    local p = { IsValid = function() return true end, MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), IsTeleporterActive = true,
        WorldFlagToTriggerOnUse = { RowName = FName("None") } }
    for name, fn in pairs(HOOKS) do if name:find("AttemptTeleport") then fn({ get = function() return p end }) end end
end
"""

results = []
def check(name, cond, detail=""):
    results.append(bool(cond)); print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))

L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute(MOCK)
L.execute(open(LAB, encoding="utf-8").read())
L.execute(GAME)
g = L.globals()
ev = L.eval
def logs(): return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

check("INSERT is bound under the name this UE4SS build uses (Key.INS; Key.INSERT does not exist)", ev("KEYS.INS ~= nil") and ev("KEYS.INSERT == nil"))
L.execute("KEYS.INS()")
check("no F2 spot yet: nothing spawned, and the screen says to press F2", ev("#live()") == 0 and "F2" in ev("SAID[#SAID]"))

# the pad-use hook must be in place before pads are used (the lab hooks a few seconds after the portal room appears)
L.execute("for _, fn in ipairs(DELAYED) do pcall(fn) end; DELAYED = {}")
L.execute("for _, fn in pairs(NOTIFY) do pcall(fn) end; for _, fn in ipairs(DELAYED) do pcall(fn) end; DELAYED = {}")
check("the pad-use hook is registered", ev("(function() for n in pairs(HOOKS) do if n:find('AttemptTeleport') then return true end end return false end)()"))

L.execute("KEYS.F2()")
L.execute("KEYS.INS()")
check("F2 then INSERT before any hub-room portal: a pad that leads nowhere", ev("#live()") == 1 and ev("live()[1].DestinationTeleporterID:ToString()") == "None")
check("... and the log says why", any("no hub-room portal found" in l for l in logs()), logs()[-3:])

L.execute("use_pad('H_Cabin_Entrance', 'H_Cabin_Start')")
L.execute("WHERE = { X = 5000, Y = 6000, Z = 188 }; YAW = 181.2")
L.execute("KEYS.F2()")
L.execute("KEYS.INS()")
check("a new F2 spot moves the preview (still one pad)", ev("#live()") == 1)
check("the preview stands at the spot's feet, facing the saved yaw", ev("live()[1].loc.X") == 5000 and ev("live()[1].loc.Y") == 6000 and ev("live()[1].loc.Z") == 100 and ev("live()[1].yaw") == 181)
check("it leads to the last hub-room portal used (the Cabin's)", ev("live()[1].DestinationTeleporterID:ToString()") == "H_Cabin_Entrance")
check("its id is hub_exit_preview, active, with the plain portal look", ev("live()[1].MyTeleporterID:ToString()") == "hub_exit_preview" and ev("live()[1].IsTeleporterActive") is True and ev("live()[1].look ~= nil"))
check("the screen says where it leads", ev("(function() for _, t in ipairs(SAID) do if t:find('leads to H_Cabin_Entrance') then return true end end return false end)()"), list(ev("SAID").values())[-3:])

L.execute("use_pad('hub_A4', 'anteverse_a_start')")
L.execute("use_pad('hub_exit_preview', 'hub_A4')")        # using the preview itself is not a hub-room portal
L.execute("use_pad('anteverse_a_start', 'hub_A4')")       # nor is a world's pad
L.execute("WHERE = { X = 7000, Y = 8000, Z = 288 }")
L.execute("KEYS.F2()")
L.execute("KEYS.INS()")
check("after hub_A4, the preview leads to hub_A4", ev("#live()") == 1 and ev("live()[1].DestinationTeleporterID:ToString()") == "hub_A4")

L.execute("KEYS.INS()")
check("INSERT again with no new F2 spot removes it", ev("#live()") == 0 and "removed" in ev("SAID[#SAID]"))
L.execute("KEYS.INS()")
check("and INSERT once more puts it back at the same spot", ev("#live()") == 1 and ev("live()[1].loc.X") == 7000)

# After a Restart All Mods the lab no longer knows which hub-room portal was used: the preview leads to the hub-room portal whose
# destination is nearest to the player (positions from the teleporter dump).
L2 = lupa.LuaRuntime(unpack_returned_tuples=True)
L2.execute(MOCK)
L2.execute(open(LAB, encoding="utf-8").read())
L2.execute(GAME)
L2.execute("for _, fn in pairs(NOTIFY) do pcall(fn) end; for _, fn in ipairs(DELAYED) do pcall(fn) end; DELAYED = {}")   # the pad-use hook
L2.execute("""
local function gpad(id, dest, x, y, z)
    PADS[#PADS + 1] = { IsValid = function() return true end, MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest),
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end }
end
gpad("H_Cabin_Entrance", "H_Cabin_Start", -13024.8, 7990.4, -416.8)
gpad("H_Cabin_Start", "H_Cabin_Entrance", 125804.6, 109383.0, -2857.2)
gpad("hub_A4", "anteverse_a_start", -12610.1, 7745.9, 259.8)
gpad("anteverse_a_start", "hub_A4", 119175.3, 330450.7, 2332.4)
gpad("anteverse_a_exit", "anteverse_a_return", 119000, 330000, 2300)
gpad("anteverse_a_return", "None", -14651.4, 19826.5, 2996.4)
WHERE = { X = 129897, Y = 113224, Z = -2762 }    -- in the Cabin (9 November, spot 1)
""")
L2.execute("KEYS.F2(); KEYS.INS()")
g2 = L2.globals()
logs2 = [g2.LOGS[i] for i in range(1, len(g2.LOGS) + 1)]
prev2 = lambda: L2.eval("(function() for _, p in ipairs(live()) do if p.MyTeleporterID:ToString() == 'hub_exit_preview' then return p end end end)()")
pdest = lambda: prev2().DestinationTeleporterID.ToString(prev2().DestinationTeleporterID)
check("in the Cabin (a game home, no hub portal in the config): the preview leads to its own hub-room portal H_Cabin_Entrance, as its MHE will",
      prev2() is not None and pdest() == "H_Cabin_Entrance", logs2[-2:])
L2.execute("WHERE = { X = 119500, Y = 330200, Z = 2420 }; KEYS.F2(); KEYS.INS()")
check("in Far Garden with no hub portal to it: the preview leads nowhere yet (the MHE will lead to the Failsafe Exit after NUMPAD 1)", pdest() == "None")
L2.execute("WHERE = { X = -40000, Y = 0, Z = 88 }; KEYS.F2(); KEYS.INS()")
check("a spot in no world, after a restart: a hub-room portal picked by its destination's distance", pdest() in ("H_Cabin_Entrance", "hub_A4"))
L2.execute("use_pad('H_Cabin_Entrance', 'H_Cabin_Start'); WHERE = { X = -41000, Y = 0, Z = 88 }; KEYS.F2(); KEYS.INS()")
check("a spot in no world: a hub-room portal used since the restart wins over distance", pdest() == "H_Cabin_Entrance")
L2.execute("use_pad('hub_B1_manual', 'hub_B1'); WHERE = { X = -42000, Y = 0, Z = 88 }; KEYS.F2(); KEYS.INS()")
check("a manual portal (hub_B1_manual, in a world) is not a hub-room portal: the preview still leads to H_Cabin_Entrance", pdest() == "H_Cabin_Entrance")

# MHE (Manual Hub Exit): INSERT also saves the spot as the MHE of the world it is in, in the hub's manual_exits.lua (installed copy).
MHE_PATH = "ue4ss/Mods/PortalHub/Scripts/manual_exits.lua"
REPO_MHE = open(os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts", "manual_exits.lua"), encoding="utf-8").read()
L3 = lupa.LuaRuntime(unpack_returned_tuples=True)
L3.execute(MOCK)
L3.execute(open(LAB, encoding="utf-8").read())
L3.execute(GAME)
L3.execute("for _, fn in pairs(NOTIFY) do pcall(fn) end; for _, fn in ipairs(DELAYED) do pcall(fn) end; DELAYED = {}")
L3.globals().REPO_MHE = REPO_MHE.replace("\n", "\r\n")          # as git checks it out on Windows: CRLF
L3.execute("""
FS = { [%r] = REPO_MHE }
io.open = function(path, mode)
    mode = mode or "r"
    if mode:find("w") or mode:find("a") then
        local buf = { mode:find("a") and (FS[path] or "") or "" }
        return { write = function(self, t) buf[#buf + 1] = t end, close = function() FS[path] = table.concat(buf) end }
    end
    local c = FS[path]
    if not c then return nil end
    return { read = function() return c end, close = function() end }
end
local function gpad(id, dest, x, y, z)
    PADS[#PADS + 1] = { IsValid = function() return true end, MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest),
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end }
end
gpad("H_Cabin_Entrance", "H_Cabin_Start", -13024.8, 7990.4, -416.8)
gpad("H_Cabin_Start", "H_Cabin_Entrance", 125804.6, 109383.0, -2857.2)
gpad("hub_A4", "anteverse_a_start", -12610.1, 7745.9, 259.8)
gpad("anteverse_a_start", "anteverse_early_exit", 119175.3, 330450.7, 2332.4)
function mhe() return FS[%r] end
function mhe_table() local f = load(mhe()); return f and f() end
""" % (MHE_PATH, MHE_PATH))
ev3 = L3.eval
L3.execute("WHERE = { X = 129897, Y = 113224, Z = -2762 }; YAW = 300; KEYS.F2(); KEYS.INS()")
check("MHE: INSERT in the Cabin saves H_Cabin_Start's MHE (feet, yaw) in the hub's manual_exits.lua",
      ev3("mhe_table() and mhe_table().H_Cabin_Start and table.concat(mhe_table().H_Cabin_Start, ',')") == "129897,113224,-2850,300", ev3("mhe()"))
check("MHE: the file keeps its comments, its CRLF line endings and no BOM",
      ev3("mhe():find('Portal Hub: Manual Hub Exits (MHEs)', 1, true) ~= nil") and "\n" not in ev3("mhe()").replace("\r\n", "") and not ev3("mhe()").startswith("\ufeff"))
check("MHE: the screen says it was saved", ev3("(function() for _, t in ipairs(SAID) do if t:find('MHE for H_Cabin_Start saved') then return true end end return false end)()"))
L3.execute("WHERE = { X = 129000, Y = 112000, Z = -2762 }; YAW = 10; KEYS.F2(); KEYS.INS()")
t = ev3("mhe_table()")
check("MHE: a new spot in the same world replaces its MHE (still one line)", ev3("table.concat(mhe_table().H_Cabin_Start, ',')") == "129000,112000,-2850,10"
      and ev3("select(2, mhe():gsub('H_Cabin_Start', ''))") == 1, ev3("mhe()"))
L3.execute("WHERE = { X = 119500, Y = 330200, Z = 2420 }; YAW = 180; KEYS.F2(); KEYS.INS()")
check("MHE: a spot in Far Garden adds anteverse_a_start's, the Cabin's stays",
      ev3("mhe_table().anteverse_a_start ~= nil and mhe_table().H_Cabin_Start ~= nil"), ev3("mhe()"))
before = ev3("mhe()")
L3.execute("WHERE = { X = -40000, Y = 0, Z = 88 }; KEYS.F2(); KEYS.INS()")   # the Facility: ~1986 m from the Cabin's arrival pad
check("MHE: a spot far from every world's arrival pad saves nothing, and says so", ev3("mhe()") == before and ev3("SAID[#SAID]").startswith("No MHE saved"))
L3.execute("FS[%r] = '-- broken' ; WHERE = { X = 129897, Y = 113224, Z = -2762 }; KEYS.F2(); KEYS.INS()" % MHE_PATH)
check("MHE: a file without its return { ... } shape is left alone, and the screen says why", ev3("mhe()") == "-- broken" and "MHE not saved" in ev3("SAID[#SAID]"))
# the hub portal in manual mode for that world and the preview are linked at once, both ways (the config says which slot)
L3.execute("""
gpad = gpad or nil
PADS[#PADS + 1] = { IsValid = function() return true end, MyTeleporterID = FName("hub_B1"), DestinationTeleporterID = FName("anteverse_a_start"),
    K2_GetActorLocation = function() return { X = -12719, Y = 8788, Z = -390 } end }
PADS[#PADS + 1] = { IsValid = function() return true end, MyTeleporterID = FName("hub_B2"), DestinationTeleporterID = FName("anteverse_a_start"),
    K2_GetActorLocation = function() return { X = -13091, Y = 8467, Z = -390 } end }
local realDofile = dofile
HUBCFG = { worlds = {}, portals = { { slot = "A-4", destination = "anteverse_a_start", exits = "dynamic" },
    { slot = "B-2", destination = "anteverse_a_start", exits = 4, manual = { 1, 2, 3, 0 } }, { slot = "B-1", destination = "anteverse_a_start", exits = "manual" } } }
function dofile(path) if path:find("PortalHub/Scripts/config.lua", 1, true) then return HUBCFG end return realDofile(path) end
function dest(id) for _, p in ipairs(PADS) do if p.IsValid() and p.MyTeleporterID:ToString() == id then return p.DestinationTeleporterID:ToString() end end end
""")
L3.execute("""
function hubpad(id, dest, x, y, z)
    local p = { MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end }
    p.IsValid = function() return not p.gone end
    p.K2_DestroyActor = function() p.gone = true end
    PADS[#PADS + 1] = p
end
hubpad("hub_B1_manual", "hub_B1", 127329, 334595, 1933)
hubpad("hub_B2_manual", "hub_B2", 1, 2, 3)
""")
n3 = len(L3.globals().LOGS)
L3.execute("FS[%r] = REPO_MHE; WHERE = { X = 119500, Y = 330200, Z = 2420 }; YAW = 180; KEYS.F2(); KEYS.INS()" % MHE_PATH)
logs3 = [L3.globals().LOGS[i] for i in range(n3 + 1, len(L3.globals().LOGS) + 1)]
check("MHE linked at once: the first manual hub portal (B-2) now leads to the preview, and the preview to it",
      ev3("dest('hub_B2')") == "hub_exit_preview" and ev3("dest('hub_exit_preview')") == "hub_B2", logs3)
check("... the dynamic portal (A-4) is not touched; one preview links with one hub portal (the first manual one, B-2)",
      ev3("dest('hub_A4')") != "hub_exit_preview", logs3)
check("... the screen says so", "hub_B2 now leads here" in ev3("SAID[#SAID]"), ev3("SAID[#SAID]"))
alive = lambda pid: ev3("(function() for _, p in ipairs(PADS) do if p.MyTeleporterID:ToString() == %r and not p.gone then return true end end return false end)()" % pid)
check("one MHE per world: the old manual portal of hub_B1 (at the old MHE) is removed at once", not alive("hub_B1_manual"), logs3)
check("... B-2's manual portal (also at the old MHE) is removed too: one MHE per world", not alive("hub_B2_manual"))
check("... and the log says so", any("removed the old portal(s) of anteverse_a_start: hub_B1_manual" in l for l in logs3), logs3)
# the Train with no hub portal: the preview never leads to a pad in another world (9 November: it led to Far Garden's manual portal)
L3.execute("""
hubpad("train_start", "None", 333725.9, 12323.6, 934.2)
use_pad("hub_B1_manual", "hub_B1")
FS[%r] = REPO_MHE; WHERE = { X = 333394, Y = 13460, Z = 960 }; YAW = 359; KEYS.F2(); KEYS.INS()
""" % MHE_PATH)
check("an MHE for the Train (no hub portal to it) after using Far Garden's manual portal: the preview leads nowhere, not to hub_B1_manual",
      ev3("dest('hub_exit_preview')") == "None", ev3("dest('hub_exit_preview')"))
check("... and the screen says the Failsafe Exit comes after NUMPAD 1", "Failsafe Exit" in ev3("SAID[#SAID]"), ev3("SAID[#SAID]"))
L3.execute("hubpad('hub_failsafe', 'None', -12850, 8270, -1040); KEYS.F2(); KEYS.INS()")
check("with the hub's Failsafe Exit in place, the Train's preview leads to it", ev3("dest('hub_exit_preview')") == "hub_failsafe")
L3.execute("HUBCFG.portals = {}")
# INSERT in the portal room records the Failsafe Exit (near the game's own Cabin portal; first floor, in front of the door)
L3.execute("FS[%r] = REPO_MHE; WHERE = { X = -12850, Y = 8270, Z = -952 }; YAW = 90; KEYS.F2(); KEYS.INS()" % MHE_PATH)
check("INSERT in the portal room saves the Failsafe Exit, not an MHE", ev3("mhe_table().failsafe and table.concat(mhe_table().failsafe, ',')") == "-12850,8270,-1040,90", ev3("mhe()"))
check("... the screen says so", "Failsafe Exit saved" in ev3("SAID[#SAID]"), ev3("SAID[#SAID]"))
check("... and no preview portal is placed there (the Failsafe Exit is invisible)", not ev3("(function() for _, p in ipairs(PADS) do if p.MyTeleporterID:ToString() == 'hub_exit_preview' and p.IsValid() then return true end end return false end)()"))

# the hub reads what the lab wrote: exits = "manual" with no spot of its own uses the recorded MHE
L3.execute("FS[%r] = REPO_MHE; WHERE = { X = 129897, Y = 113224, Z = -2762 }; YAW = 300; KEYS.F2(); KEYS.INS()" % MHE_PATH)
recorded = ev3("mhe()")
H = lupa.LuaRuntime(unpack_returned_tuples=True)
HUBDIR = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
H.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUBDIR)
H.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
H.globals().RECORDED = recorded
H.execute("""
CONFIG.worlds = {}
CONFIG.portals = { { slot = "B-1", name = "Cabin", destination = "H_Cabin_Start", exits = "manual" } }
package.preload["manual_exits"] = function() return load(RECORDED)() end
SPAWNED = {}
local padClass = { IsValid = function() return true end }
local sf = StaticFindObject
function StaticFindObject(p) if p:find("BP_Teleporter_ParentBP", 1, true) then return padClass end return sf(p) end
local ff = FindFirstOf
function FindFirstOf(n) if n == "BP_Teleporter_HomeWorld_C" then return { IsValid = function() return true end } end return ff(n) end
function FindAllOf(n) if n == "BP_Teleporter_ParentBP_C" then return SPAWNED end return {} end
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = { IsValid = function() return true end, loc = loc, yaw = rot.Yaw, OnRep_IsTeleporterActive = function() end,
        ParticleLoop = { SetAsset = function() end, Activate = function() end }, K2_GetActorLocation = function() return loc end }
    SPAWNED[#SPAWNED + 1] = a
    return a
end
function RegisterHook() end
""")
H.execute(open(os.path.join(HUBDIR, "main.lua"), encoding="utf-8").read())
H.execute("pump(); pump()")
check("the hub reads the recorded MHE: B-1's manual portal stands at the Cabin spot the lab saved",
      H.eval("(function() for _, a in ipairs(SPAWNED) do if a.MyTeleporterID and a.MyTeleporterID:ToString() == 'hub_B1_manual' then return a.loc.X == 129897 and a.loc.Z == -2850 and a.yaw == 300 end end return false end)()"),
      [H.globals().LOGS[i] for i in range(1, len(H.globals().LOGS) + 1)][-6:])

# Every key the hub and the lab bind must be a name this UE4SS build knows: the mocks accept any name, which is how Key.INSERT (not a
# UE4SS key; it is Key.INS) got through the tests on 9 November. The list is the key table in UE4SS.dll (v3.0.1 Beta, July build).
UE4SS_KEYS = set("""BACKSPACE TAB CLEAR RETURN PAUSE CAPS_LOCK ESCAPE SPACE PAGE_UP PAGE_DOWN END HOME LEFT_ARROW UP_ARROW RIGHT_ARROW DOWN_ARROW
SELECT PRINT EXECUTE PRINT_SCREEN INS DEL HELP ZERO ONE TWO THREE FOUR FIVE SIX SEVEN EIGHT NINE A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
LEFT_WIN RIGHT_WIN APPS SLEEP NUM_ZERO NUM_ONE NUM_TWO NUM_THREE NUM_FOUR NUM_FIVE NUM_SIX NUM_SEVEN NUM_EIGHT NUM_NINE MULTIPLY ADD SEPARATOR
SUBTRACT DECIMAL DIVIDE F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19 F20 F21 F22 F23 F24 NUM_LOCK SCROLL_LOCK""".split())
MODS = os.path.join(S, "..", "..", "..", "mod")
for mod in ("PortalHub", "PortalMaterialLab"):
    src = open(os.path.join(MODS, mod, "Scripts", "main.lua"), encoding="utf-8").read()
    used = sorted(set(re.findall(r"(?<![A-Za-z0-9_])Key\.([A-Z0-9_]+)", src)))
    bad = [k for k in used if k not in UE4SS_KEYS]
    check("%s binds only real UE4SS key names (%s)" % (mod, " ".join(used)), not bad, bad)
    taken = [k for k in used if k in ("DEL", "F11")]     # CRD-020's probe mod (mod/CordonaProbe) uses DELETE and F11
    check("%s stays off DELETE and F11 (the probe mod's keys)" % mod, not taken, taken)

check("no 'failed' lines in the log", not [l for l in logs() if "failed" in l], [l for l in logs() if "failed" in l])
print("\n%d checks, %d failed" % (len(results), results.count(False)))
sys.exit(0 if all(results) else 1)
