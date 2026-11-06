# World settings on the loader Blueprint: the Blueprint wins over config.lua, which wins over the defaults. Runs the real hub main.lua
# against hub_mock.lua plus a fake class defaults object (LOADER_VARS) for the world's loader, once per scenario.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mod", "PortalHub", "Scripts")
ORIGIN = (1100000, 1300000, 0)

EXTRAS = r'''
local function obj(t) t.IsValid = function() return true end; return t end
CDO_PATH = "/Game/Mods/CordonaTest/BP_CordonaTestLoader.Default__BP_CordonaTestLoader_C"
FLAG_ROWS, SPAWNED, TELEPORTS = {}, {}, {}
local dtFlags = obj({ FindRow = function(self, n) return FLAG_ROWS[n] end, AddRow = function(self, n, r) FLAG_ROWS[n] = r end })
local classes = {
    ["/Game/Blueprints/Environment/Volumes/Vignette_Zone.Vignette_Zone_C"] = obj({ kind = "Vignette_Zone_C" }),
    ["/Game/Blueprints/Environment/Volumes/LeyakSafetyZone.LeyakSafetyZone_C"] = obj({ kind = "LeyakSafetyZone_C" }),
    ["/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C"] = obj({ kind = "BP_Teleporter_ParentBP_C" }),
}
local homePad = obj({ RequiredWorldFlag = { DataTablePath = FName("/Game/Blueprints/DataTables/DT_WorldFlags") } })
local baseFind, baseAll = StaticFindObject, FindAllOf
function StaticFindObject(p)
    if p == CDO_PATH then
        if not LOADER_VARS then return nil end
        local cdo = obj({})
        for k, v in pairs(LOADER_VARS) do cdo[k] = v end
        return cdo
    end
    if p == "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags" then return dtFlags end
    if classes[p] then return classes[p] end
    return baseFind(p)
end
function FindAllOf(n)
    if n == "BP_Teleporter_HomeWorld_C" then return { homePad } end
    local out = {}
    for _, a in ipairs(SPAWNED) do if a.kind == n then out[#out + 1] = a end end
    if #out > 0 then return out end
    return baseAll(n)
end
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = obj({ kind = cls.kind, loc = loc, yaw = rot.Yaw, K2_GetActorLocation = function() return loc end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = rot.Yaw, Roll = 0 } end,
        GetActorForwardVector = function() return { X = math.cos(math.rad(rot.Yaw)), Y = math.sin(math.rad(rot.Yaw)), Z = 0 } end,
        OnRep_IsTeleporterActive = function() end, ParticleLoop = { SetAsset = function() end, Activate = function() end },
        BuffVolume = obj({ SetBoxExtent = function() end }), PortalSicknessWorldFlag = { RowName = FName("None") } })
    SPAWNED[#SPAWNED + 1] = a
    return a
end
FS = obj({ HasWorldFlag = function() return false end, HasWorldFlagsLoaded = function() return true end })
local baseFirst = FindFirstOf
function FindFirstOf(n) if n == "WorldFlagSubsystem" then return FS end return baseFirst(n) end
PAWN.Client_DisplayWarningMessage = function() end
PAWN.K2_TeleportTo = function(self, loc) TELEPORTS[#TELEPORTS + 1] = loc; return true end
function vec(x, y, z) return { X = x, Y = y, Z = z } end
function pad(id) for _, a in ipairs(SPAWNED) do if a.MyTeleporterID and a.MyTeleporterID.s == id then return a end end end
function count(kind) local n = 0; for _, a in ipairs(SPAWNED) do if a.kind == kind then n = n + 1 end end; return n end
'''

results = []


def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def run(title, setup):
    """Fresh hub in a fresh Lua; `setup` (Lua) changes CONFIG / LOADER_VARS before main.lua loads. Returns (eval, tick, logs)."""
    print("\n-- " + title)
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    g = L.globals()
    L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
    L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
    L.execute("CONFIG.worlds.cordonatest_start.lighting = nil")     # the lighting block is not part of this test
    L.execute(EXTRAS)
    L.execute(setup)
    L.execute(open(os.path.join(HUB, "main.lua"), encoding="utf-8").read())

    def tick(n=1):
        for _ in range(n):
            g.T = g.T + 0.5
            L.execute("pump()")

    def logs():
        return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

    return L.eval, L.execute, tick, logs


def enter(ex, tick, dx=500, dy=0, dz=80):
    ex("LOC.X, LOC.Y, LOC.Z = %d, %d, %d" % (ORIGIN[0] + dx, ORIGIN[1] + dy, ORIGIN[2] + dz))
    tick(2)


# 1) Everything on the Blueprint; config.lua has other values, which must lose.
lua, ex, tick, logs = run("Blueprint has every setting", r'''
local w = CONFIG.worlds.cordonatest_start
w.title = "Config Title"; w.type = "home"; w.leyakSafe = true; w.lightingFrom = "HGarden"; w.killZ = -3000; w.radius = 90000
w.arrive = { 0, 0, 0, 0 }; w.exit = { 1, 1, 1, 1 }
LOADER_VARS = { WorldTitle = FText("Blueprint Title"), WorldType = FName("Vignette"), NoWeather = true, LeyakSafeZone = false,
    LightingDay = FName("SouthIsland"), KillZ = -500.0, Radius = 5000.0,
    ArriveSpot = vec(100, 200, 30), ArriveYaw = 90.0, ExitSpot = vec(600, 0, 0), ExitYaw = 180.0 }
''')
enter(ex, tick)
for l in logs():
    if "settings" in l: print("    " + l)
check("arrival pad at origin + ArriveSpot", lua("pad('cordonatest_start').loc.X") == ORIGIN[0] + 100 and lua("pad('cordonatest_start').loc.Y") == ORIGIN[1] + 200
      and lua("pad('cordonatest_start').loc.Z") == ORIGIN[2] + 30, lua("pad('cordonatest_start') and pad('cordonatest_start').loc.X"))
check("arrival pad faces ArriveYaw", lua("pad('cordonatest_start').yaw") == 90)
check("WorldType Vignette (any case): exit pad at origin + ExitSpot", lua("pad('cordonatest_start_exit') ~= nil and pad('cordonatest_start_exit').loc.X") == ORIGIN[0] + 600)
check("exit pad faces ExitYaw", lua("pad('cordonatest_start_exit').yaw") == 180)
check("LeyakSafeZone false: no Leyak zone", lua("count('LeyakSafetyZone_C')") == 0, lua("count('LeyakSafetyZone_C')"))
check("NoWeather true: vignette zone spawned", lua("count('Vignette_Zone_C')") == 1)
check("LightingDay alone lights day and night", lua("TRANSITIONS[1]") == "SouthIsland / SouthIsland / 'Blueprint Title'", lua("TRANSITIONS[1]"))
check("Blueprint title in the level entry", lua("LEVEL_ROWS.PortalHub_cordonatest_start[F('SectorName')].s") == "Blueprint Title")
ex("TELEPORTS = {}; LOC.Z = -400"); tick(1)
check("above KillZ (-500): no rescue (config's -3000 lost too)", lua("#TELEPORTS") == 0)
ex("LOC.Z = -600"); tick(1)
check("below KillZ: rescued to the arrival pad", lua("#TELEPORTS") == 1 and abs(lua("TELEPORTS[1].Y") - (ORIGIN[1] + 200 + 215.1)) < 0.01, lua("#TELEPORTS"))
ex("LOC.X, LOC.Y, LOC.Z = %d, %d, 80" % (ORIGIN[0] + 6000, ORIGIN[1])); tick(2)
check("Radius 5000: 6000 away is outside (level entry given back)", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))
check("one settings line, read once", sum(1 for l in logs() if "settings from its loader Blueprint" in l) == 1)
check("no tracker errors", not any("tracker error" in l for l in logs()), [l for l in logs() if "error" in l])

# 2) No Blueprint variables at all: config.lua decides.
lua, ex, tick, logs = run("no Blueprint variables: config.lua", r'''
local w = CONFIG.worlds.cordonatest_start
w.arrive = { 50, 0, 10, 45 }; w.lightingFrom = { day = "office1", night = "Office1_Night" }; w.type = "vignette"; w.exit = { 0, 700, 0, 0 }
LOADER_VARS = {}
''')
enter(ex, tick)
check("arrival pad from config arrive", lua("pad('cordonatest_start').loc.X") == ORIGIN[0] + 50 and lua("pad('cordonatest_start').yaw") == 45)
check("exit pad from config exit", lua("pad('cordonatest_start_exit') ~= nil and pad('cordonatest_start_exit').loc.Y") == ORIGIN[1] + 700)
check("lighting rows from config", lua("TRANSITIONS[1]") == "office1 / Office1_Night / 'Test World'", lua("TRANSITIONS[1]"))
check("Leyak zone on by default", lua("count('LeyakSafetyZone_C')") == 1)
check("settings line says none", any("settings from its loader Blueprint: none" in l for l in logs()))
ex("TELEPORTS = {}; LOC.Z = -3100"); tick(1)
check("config killZ (-3000) still rescues", lua("#TELEPORTS") == 1)

# 3) A mix: the Blueprint sets some, config.lua the rest; KillZ 0 switches the rescue off; NoWeather false opts out of vignette status.
lua, ex, tick, logs = run("mixed: Blueprint partly, KillZ 0, NoWeather false", r'''
local w = CONFIG.worlds.cordonatest_start
w.title = "Config Title"; w.arrive = { 0, 0, 0, 30 }
LOADER_VARS = { KillZ = 0.0, NoWeather = false, ArriveSpot = vec(300, 0, 0) }
''')
enter(ex, tick)
check("ArriveSpot from Blueprint, yaw kept from config", lua("pad('cordonatest_start').loc.X") == ORIGIN[0] + 300 and lua("pad('cordonatest_start').yaw") == 30)
check("NoWeather false: no vignette zone", lua("count('Vignette_Zone_C')") == 0)
check("NoWeather false: game's level entry left alone", lua("PC.ActiveLevelFXName.s") == "office1" and lua("#TRANSITIONS") == 0)
ex("TELEPORTS = {}; LOC.Z = -5000"); tick(1)
check("KillZ 0 on the Blueprint: no rescue even though config has -3000", lua("#TELEPORTS") == 0, lua("#TELEPORTS"))
check("no tracker errors", not any("tracker error" in l for l in logs()))

# 4) Nothing anywhere: no arrive in config, no Blueprint loaded yet. The world is still accepted; the pad goes to origin.
lua, ex, tick, logs = run("no arrive anywhere", r'''
CONFIG.worlds.cordonatest_start.arrive = nil
''')
check("world without arrive is not refused", not any("incomplete" in l for l in logs()), [l for l in logs() if "incomplete" in l])
enter(ex, tick)
check("pad at origin by default", lua("pad('cordonatest_start').loc.X") == ORIGIN[0] and lua("pad('cordonatest_start').loc.Y") == ORIGIN[1])
check("no lighting set: lit with Intro, title = the portal name", lua("TRANSITIONS[1]") == "Intro / Intro / 'Test World'", lua("TRANSITIONS[1]"))
check("no lighting set is logged", any("has no lighting set" in l for l in logs()))
ex("PC.Day_FX_Row = { RowName = FName('office1') }"); n = lua("#TRANSITIONS"); tick(8)
check("no lighting set: Intro is put back if the game changes it", lua("PC.Day_FX_Row.RowName.s") == "Intro", lua("PC.Day_FX_Row.RowName.s"))

# 5) A lighting row that does not exist falls back to Intro.
lua, ex, tick, logs = run("unknown lighting row", r'''
LOADER_VARS = { LightingDay = FName("NoSuchRow") }
''')
enter(ex, tick)
check("unknown row: reported", any("'NoSuchRow'" in l and "using Intro" in l for l in logs()))
check("unknown row: lit with Intro", lua("TRANSITIONS[1]") == "Intro / Intro / 'Test World'", lua("TRANSITIONS[1]"))

print("\n%d checks, %d passed, %d failed" % (len(results), sum(results), len(results) - sum(results)))
sys.exit(0 if all(results) else 1)
