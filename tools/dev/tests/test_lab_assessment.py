# Runs the real mod/PortalMaterialLab/Scripts/main.lua against a small mock of the game and checks the CRD-006 additions: flags that come
# back wrapped are still read (they looked missing before), PAGE UP reports the tables and the row registry, PAGE DOWN falls back to
# RowName only when the hub's table is refused, the pad hook logs which pad was used, and nothing writes to the game.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")

MOCK = r"""
T = 0
os.clock = function() return T end
LOGS, KEYS, HOOKS, NOTIFY, DELAYED, CALLS = {}, {}, {}, {}, {}, {}
print = function(s) LOGS[#LOGS + 1] = (tostring(s):gsub("\n$", "")) end

local NameMT = { __index = { ToString = function(self) return self.s end }, __eq = function(a, b) return a.s == b.s end }
function FName(s) return setmetatable({ s = s }, NameMT) end
function FText(s) return setmetatable({ s = s }, NameMT) end
Key = setmetatable({}, { __index = function(_, k) return k end })
function RegisterKeyBind(k, fn) KEYS[k] = fn end
function RegisterHook(name, fn) HOOKS[name] = fn end
function NotifyOnNewObject(name, fn) NOTIFY[name] = fn end
function ExecuteInGameThread(fn) fn() end
function ExecuteWithDelay(ms, fn) DELAYED[#DELAYED + 1] = fn end
function LoadAsset() end
function pump() local d = DELAYED; DELAYED = {}; for _, f in ipairs(d) do f() end end

-- every mock game object refuses writes, so a write anywhere fails the test
local function ro(t)
    t.IsValid = function() return true end
    return setmetatable({}, { __index = t, __newindex = function(_, k) error("the lab wrote " .. tostring(k)) end })
end
local function wrapped(s) return { get = function() return FName(s) end } end   -- like UE4SS's out-parameter items: ToString needs :get() first
local function list(items)
    return { ForEach = function(self, fn) for i, v in ipairs(items) do fn(i, { get = function() return v end }) end end }
end
local function dtable(rows)
    return ro({
        GetFName = function() return FName("table") end,
        FindRow = function(self, n) for _, r in ipairs(rows) do if r == n then return {} end end return nil end,
        GetRowNames = function() local o = {}; for i, r in ipairs(rows) do o[i] = FName(r) end; return o end,
        AddRow = function() error("the lab added a row") end,
    })
end

FLAGS = { "TrainCompletedOnce", "PortalHub_world_b_start_Completed" }
REFUSE_TABLE = false
local function handle(row) return { RowName = FName(row) } end
SUBSYSTEM = ro({
    HasWorldFlagsLoaded = function() return true end,
    GetWorldFlags = function(self, out) for i, f in ipairs(FLAGS) do out[i] = wrapped(f) end; return true end,
    SetWorldFlag = function() error("the lab set a flag") end,
    HasWorldFlag = function(self, pc, h)
        if rawget(h, "DataTablePath") ~= nil and REFUSE_TABLE then error("no property DataTablePath") end
        CALLS[#CALLS + 1] = (rawget(h, "DataTablePath") ~= nil) and "table" or "other"
        return true
    end,
})
local FLAG_ROWS = dtable({ "TrainCompletedOnce", "PortalHub_world_b_start_Completed" })
local LEVEL_ROWS = dtable({ "office1", "PortalHub_world_b_start" })
local BUFF_ROWS = dtable({ "Debuff_PortalSickness", "Buff_InVignette" })
local function named(t, n) t.GetFName = function() return FName(n) end; return ro(t) end
REGISTRY = ro({
    BaseTables = list({ named({}, "DT_WorldFlags"), named({}, "DT_LevelFX"), named({}, "DT_Items") }),
    RootedModObjects = list({}),
    IsSessionLoadOrderActive = function() return false end,
    K2_GetResolvedLoadOrder = function() return {} end,
})
LIBRARY = ro({
    DoesWorldFlagRowExist = function() return true end,
    GetAllWorldFlagRowNames = function(self, out) out[1] = wrapped("TrainCompletedOnce"); out[2] = wrapped("PortalHub_world_b_start_Completed") end,
    Conv_NameToWorldFlag = function(self, n) return handle(n.s) end,
})
local ZONE = ro({
    GetFullName = function() return "Vignette_Zone_C /Temp/Zone" end,
    K2_GetActorLocation = function() return { X = 1, Y = 2, Z = 3 } end,
    PortalSicknessWorldFlag = handle("PortalHub_world_b_start_Completed"),
    BuffVolume = ro({ IsOverlappingActor = function() return true end, GetScaledBoxExtent = function() return { X = 1, Y = 1, Z = 1 } end }),
    BuffToApply = handle("Buff_InVignette"), BuffBlockingTags = {},
})
GAMEPAD = ro({ RequiredWorldFlag = handle("Residence_Entered") })    -- no DataTablePath, as since v1.5.0
EXITPAD = ro({
    MyTeleporterID = FName("world_b_start_exit"), DestinationTeleporterID = FName("hub_C2"), IsTeleporterActive = true,
    WorldFlagToTriggerOnUse = handle("PortalHub_world_b_start_Completed"),
    K2_GetActorLocation = function() return { X = 4, Y = 5, Z = 6 } end,
})
ARRIVAL = ro({
    MyTeleporterID = FName("world_b_start"), DestinationTeleporterID = FName("hub_C2"), IsTeleporterActive = true,
    WorldFlagToTriggerOnUse = handle("None"),
    K2_GetActorLocation = function() return { X = 7, Y = 8, Z = 9 } end,
})
PAWN = ro({
    K2_GetActorLocation = function() return { X = 1100000, Y = 1600000, Z = 0 } end,
    K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end,
    BuffComponent = ro({ CurrentBuffs = list({}), BuffTagContainer = {} }),
})
PC = ro({ Pawn = PAWN, ActiveLevelName = FName("x"), ActiveWeatherFXName = FName("None") })

function FindFirstOf(name)
    if name == "WorldFlagSubsystem" then return SUBSYSTEM end
    if name == "ABFRowRegistrySubsystem" then return REGISTRY end
    if name == "Abiotic_PlayerController_C" then return PC end
    if name == "BP_Teleporter_HomeWorld_C" then return GAMEPAD end
    return nil
end
function FindAllOf(name)
    if name == "Vignette_Zone_C" then return { ZONE } end
    if name == "BP_Teleporter_HomeWorld_C" then return { GAMEPAD } end
    if name == "BP_Teleporter_ParentBP_C" then return { ARRIVAL, EXITPAD } end
    return nil
end
function StaticFindObject(path)
    if path:find("DT_WorldFlags") then return FLAG_ROWS end
    if path:find("DT_Levels") then return LEVEL_ROWS end
    if path:find("DT_BuffsDebuffs") then return BUFF_ROWS end
    if path:find("WorldFlagHandleFunctionLibrary") then return LIBRARY end
    return nil
end
"""

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def lab(refuse=False):
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute("REFUSE_TABLE = " + ("true" if refuse else "false"))
    L.execute(open(LAB, encoding="utf-8").read())
    L.execute("pump()")     # the portal room is loaded: the pad hook goes in
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


def press(L, key):
    L.execute("KEYS['%s']()" % key)


print("=== NUMPAD 7: flags that come back wrapped")
L = lab()
press(L, "NUM_SEVEN")
check("the hub's flag is listed (it looked missing before)", has(L, "Portal Hub ones: PortalHub_world_b_start_Completed"), logs(L)[-12:])

print("=== PAGE UP")
press(L, "PAGE_UP")
check("save flags counted", has(L, "set in this save: 2 (2 readable)"))
check("hub row in DT_WorldFlags", has(L, "DT_WorldFlags: 2 rows, matching ^PortalHub_: PortalHub_world_b_start_Completed"))
check("hub row in DT_Levels", has(L, "DT_Levels: 2 rows, matching ^PortalHub_: PortalHub_world_b_start"))
check("flag row and save state", has(L, "PortalHub_world_b_start_Completed: row in DT_WorldFlags true, set in this save true"))
check("sickness row checked", has(L, "Debuff_PortalSickness row in DT_BuffsDebuffs: true"))
check("registry tables listed", has(L, "3 table(s): DT_Items, DT_LevelFX, DT_WorldFlags"))
check("which tables the registry manages", has(L, "DT_WorldFlags in BaseTables: true, DT_LevelFX: true, DT_Levels: false"))
check("zone with its flag", has(L, "flag PortalHub_world_b_start_Completed, set in this save true, player inside true"))
check("a handle's missing DataTablePath does not stop the survey", has(L, "its DataTablePath: not readable"), logs(L)[-8:])
check("only the pad that sets a flag is listed", has(L, "pad world_b_start_exit -> hub_C2") and has(L, "pads that set a flag: 1"))
check("survey ran to the end", has(L, "FLAG AND REGISTRY SURVEY done"))

print("=== PAGE DOWN, the hub's table accepted")
L = lab()
press(L, "PAGE_DOWN")
check("library rows", has(L, "2 names, Portal Hub ones: PortalHub_world_b_start_Completed"))
check("the game's own handle is tried", has(L, "calling: HasWorldFlag with the game's own handle"))
check("RowName only is not tried when the table works", not has(L, "HasWorldFlag with RowName only"))
check("probe ran to the end", has(L, "FLAG NATIVE PROBE done"))

print("=== PAGE DOWN, the hub's table refused")
L = lab(refuse=True)
press(L, "PAGE_DOWN")
check("the refusal is logged", has(L, "failed: no property DataTablePath") or has(L, "failed:"), logs(L)[-8:])
check("RowName only is tried next", has(L, "calling: HasWorldFlag with RowName only"))

print("=== pad use")
L = lab()
g = L.globals()
hook = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C:AttemptTeleport"
check("the hook is in", g.HOOKS[hook] is not None)
L.execute("HOOKS['%s']({ get = function() return EXITPAD end })" % hook)
L.execute("HOOKS['%s']({ get = function() return EXITPAD end })" % hook)
check("the pad, its way out and its flag are logged", has(L, "pad use: world_b_start_exit -> hub_C2, active true, sets flag PortalHub_world_b_start_Completed"))
check("one crossing logs once", sum("pad use: world_b_start_exit" in l for l in logs(L)) == 1)
L.execute("pump()")
check("the flag is checked after the pad", has(L, "1.5 s after world_b_start_exit, flag PortalHub_world_b_start_Completed set in this save: true"))
L.execute("T = 5; HOOKS['%s']({ get = function() return ARRIVAL end })" % hook)
check("a pad with no flag logs the use only", has(L, "pad use: world_b_start -> hub_C2, active true, sets flag None"))

print("=== NUMPAD 3: completion flags cleared with RowName-only handles (CRD-016)")
L = lab()
L.execute(r"""
HANDLES = {}
local set = { PortalHub_world_b_start_Completed = true }
local fs = { IsValid = function() return true end,
    GetWorldFlags = function(self, out) out[1] = { get = function() return FName("PortalHub_world_b_start_Completed") end } end,
    HasWorldFlag = function(self, pc, h) HANDLES[#HANDLES + 1] = h; return set[h.RowName.s] == true end,
    SetWorldFlag = function(self, h, on, pc) HANDLES[#HANDLES + 1] = h; set[h.RowName.s] = on end }
local find = FindFirstOf
function FindFirstOf(name) if name == "WorldFlagSubsystem" then return fs end return find(name) end
""")
press(L, "NUM_THREE")
g = L.globals()
n = len(g.HANDLES)
check("NUMPAD 3 used flag handles", n > 0)
check("no handle carries DataTablePath", n > 0 and all(L.eval("HANDLES[%d].DataTablePath" % i) is None for i in range(1, n + 1)))
check("the hub's flag is cleared and confirmed", has(L, "clear flags: PortalHub_world_b_start_Completed -> call true, still set afterwards: false"), logs(L)[-4:])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
