# The one-off DLC survey mod (mod/CordonaDlcSurvey, CRD-033): read-only, runs on the game thread, finds the volumes that carry a DLC
# entitlement, boxes each DLC area from their bounds, and survives unreadable objects (a failed bounds call, a stale actor).
#   python test_dlc_survey.py [path to the survey's main.lua]
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))
import lupa

S = os.path.dirname(os.path.abspath(__file__))
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S, "..", "..", "..", "mod", "CordonaDlcSurvey", "Scripts", "main.lua")
OUT = os.path.join(tempfile.mkdtemp(prefix="crd033-survey-"), "survey.txt").replace("\\", "/")

MOCK = r'''
LOGS, KEYS, GAME_THREAD, IN_GAME_THREAD, WRITES = {}, {}, 0, false, 0
print = function(s) LOGS[#LOGS + 1] = (tostring(s):gsub("\n$", "")) end
Key = setmetatable({}, { __index = function(_, k) return k end })
function RegisterKeyBind(k, fn) KEYS[k] = fn end
function ExecuteInGameThread(fn) IN_GAME_THREAD = true; fn(); IN_GAME_THREAD = false end
local NameMT = { __index = { ToString = function(self) return self.s end } }
local function FName(s) return setmetatable({ s = s }, NameMT) end
CALLS_OFF_THREAD = 0
local function obj(t)
    t.IsValid = function() return t.gone ~= true end
    return setmetatable(t, { __index = function(_, k) return nil end })
end
local function guard(f) return function(...) if not IN_GAME_THREAD then CALLS_OFF_THREAD = CALLS_OFF_THREAD + 1 end; return f(...) end end
local function vol(name, row, flag, o, e, failBounds, gone)
    local v = obj({ RequiredEntitlement = { RowName = FName(row) }, RequiredWorldFlag = { RowName = FName(flag) }, X = 1, Y = 2, Z = 3, gone = gone })
    v.GetFName = guard(function() return FName(name) end)
    v.K2_GetActorLocation = guard(function() return { X = o[1], Y = o[2], Z = o[3] } end)
    v.GetActorBounds = guard(function(self, only, oo, ee, child)
        assert(only == false and child == false, "bad GetActorBounds flags")
        if failBounds then error("bounds boom") end
        oo.X, oo.Y, oo.Z = o[1], o[2], o[3]; ee.X, ee.Y, ee.Z = e[1], e[2], e[3]
    end)
    return v
end
local function pad(id, x, y, z, dlc, flag)
    local p = obj({ MyTeleporterID = FName(id), RequiredDLC = { RowName = FName(dlc) }, RequiredWorldFlag = { RowName = FName(flag) } })
    p.K2_GetActorLocation = guard(function() return { X = x, Y = y, Z = z } end)
    return p
end
VOLS = {
    vol("V_Garden_A", "HomeworldGarden", "None", { 122900, 160200, 59400 }, { 8000, 9000, 3000 }),
    vol("V_Garden_B", "HomeworldGarden", "None", { 125000, 161000, 59000 }, { 4000, 4000, 2000 }),
    vol("V_Torii", "SupportersEdition", "None", { 135900, 125100, 57000 }, { 7000, 7000, 2500 }),
    vol("V_Cabin", "None", "SnowglobeComplete", { 125800, 109400, -2800 }, { 6000, 6000, 2000 }),
    vol("V_Plain", "None", "None", { 0, 0, 0 }, { 100, 100, 100 }),
    vol("V_Broken", "HomeworldGarden", "None", { 1, 1, 1 }, { 1, 1, 1 }, true),
    vol("V_Gone", "SupportersEdition", "None", { 0, 0, 0 }, { 1, 1, 1 }, false, true),
}
PADS = { pad("H_Garden_Start", 122890.6, 160239.8, 59350.0, "HomeworldGarden", "None"), pad("H_Garden_Entrance", -12711.6, 8761.7, 259.8, "HomeworldGarden", "None"),
         pad("H_Japan_Start", 135877.3, 125090.2, 57019.9, "SupportersEdition", "None"), pad("H_Cabin_Start", 125804.6, 109383.0, -2857.2, "None", "SnowglobeComplete") }
local mgr = obj({ RequiredEntitlement = { RowName = FName("HomeworldGarden") }, RequiredWorldFlag = { RowName = FName("None") }, LevelStreamingVolumes = { 1, 2 } })
mgr.LevelStreaming = obj({ GetFullName = function() return "LevelStreamingDynamic /Game/Maps/H_Garden" end })
function FindAllOf(n)
    if not IN_GAME_THREAD then CALLS_OFF_THREAD = CALLS_OFF_THREAD + 1 end
    if n == "AbioticLevelStreamingVolume" then return VOLS end
    if n == "LevelManagerInstance" then return { mgr } end
    if n == "BP_Teleporter_HomeWorld_C" then return PADS end
    return {}
end
function FindFirstOf(n) return nil end
'''

res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))

L = lupa.LuaRuntime(unpack_returned_tuples=True)
L.execute(MOCK)
src = open(MAIN, encoding="utf-8").read()
check("the survey writes only its own file (one io.open, mode w, OUT_PATH)", src.count("io.open(") == 1 and 'io.open(OUT_PATH, "w")' in src)
for bad in ("K2_TeleportTo", "SpawnActor", "K2_DestroyActor", "RegisterHook", "NotifyOnNewObject", "SetActorHiddenInGame", "LoadAsset", "ExecuteWithDelay"):
    check("read-only: no %s" % bad, bad not in src)
check("one key, the apostrophe (Key.OEM_SEVEN), no modifier", src.count("RegisterKeyBind(") == 1 and "RegisterKeyBind(Key.OEM_SEVEN, function()" in src)
src = src.replace('local OUT_PATH = "ue4ss/Mods/CordonaDlcSurvey/survey.txt"', 'local OUT_PATH = "%s"' % OUT)
L.execute(src)
g = L.globals()
logs = lambda: [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
check("loads quietly: one 'loaded' line", any("loaded; press '" in l for l in logs()))
check("nothing searched at load", g.CALLS_OFF_THREAD == 0)
L.execute("KEYS.OEM_SEVEN()")
out = logs()
text = "\n".join(out)
check("every game call ran on the game thread", g.CALLS_OFF_THREAD == 0, g.CALLS_OFF_THREAD)
check("no 'survey failed' line", "survey failed" not in text, text)
check("lists the gated volumes, not the plain one", "volume V_Garden_A" in text and "volume V_Cabin" in text and "volume V_Plain" not in text)
check("a stale volume is skipped", "V_Gone" not in text)
check("a volume whose bounds call fails says so and is left out of the box", "volume V_Broken" in text and "unreadable (" in text)
check("7 streaming volumes found, 5 gated and valid (the stale one is not counted)", "streaming volumes: 7" in text and "with an entitlement or world flag: 5" in text, text)
check("the level manager is listed with its level and volume count", "manager | entitlement HomeworldGarden" in text and "/Game/Maps/H_Garden | volumes 2" in text)
check("Stone Garden's box joins both volumes", "AREA Stone Garden | 2 volume(s) | min 114900.0, 151200.0, 56400.0 | max 130900.0, 169200.0, 62400.0" in text, text)
check("Stone Garden's box holds H_Garden_Start, not the Cabin", "home pads inside: H_Garden_Start" in text and
      [l for l in out if l.startswith("[CordonaDlcSurvey] AREA Stone Garden")][0].endswith("H_Garden_Start"))
check("Torii's box from its one valid volume, with H_Japan_Start", "AREA Torii | 1 volume(s) | min 128900.0, 118100.0, 54500.0 | max 142900.0, 132100.0, 59500.0 | home pads inside: H_Japan_Start" in text, text)
check("home pads listed with their rows; a missing one says not found",
      "home pad H_Garden_Start | at 122890.6, 160239.8, 59350.0 | RequiredDLC HomeworldGarden" in text and "home pad H_Japan_Entrance | at not found" in text)
check("the file holds the same lines", os.path.exists(OUT) and "AREA Torii" in open(OUT, encoding="utf-8").read())
print("\n%d/%d passed" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
