# Reloading a save inside a custom world (CRD-011). The hub's Lua state outlives a map load, so after quitting to the menu and loading a save
# worldState still said "ready" and the player fell through a level that was gone (findings/game-update-2026-10.md, fault 1). Also checks that
# five worlds loading at once use one shared timer chain (fault 2). Each tick the mock player falls unless held or standing on a visible level.
#   python test_hub_reload.py [path to a main.lua, default the repo's]
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HUB, "main.lua")

L = lupa.LuaRuntime(unpack_returned_tuples=True)
g = L.globals()
L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
L.execute(r'''
local function obj(t) t.IsValid = function() return t.dead ~= true end; return t end
NAMES = { "world_a", "world_b", "world_c", "world_d", "world_e" }
CONFIG.worlds, CONFIG.portals = {}, {}
ORIGIN, CLASSES = {}, {}
for i, n in ipairs(NAMES) do
    local id = n .. "_start"
    ORIGIN[n] = i * 1000000
    CLASSES["/Game/Mods/" .. n .. "/Loader.BP_" .. n .. "_C"] = obj({ kind = "loader", name = n })
    CONFIG.worlds[id] = { loaderAsset = "/Game/Mods/" .. n .. "/Loader", loaderClass = "BP_" .. n .. "_C", level = "/Game/Mods/" .. n .. "/Map",
        origin = { ORIGIN[n], 0, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -1000 }
    CONFIG.portals[i] = { slot = i <= 4 and ("C-" .. i) or "A-3", name = n, destination = id }
end

-- the current map: its loaders, and the levels they streamed in
LOADERS, VISIBLE, SPAWNED, SHOW_LEVELS = {}, {}, {}, false
local padClass = obj({ kind = "pad" })
local function new_world()
    return obj({
        StreamingLevels = { ForEach = function(self, fn)
            for n, _ in pairs(LOADERS) do
                local path = "/Game/Mods/" .. n .. "/Map"
                local ls = obj({ PackageNameToLoad = FName(path), GetWorldAssetPackageFName = function() return FName(path) end,
                    IsLevelVisible = function() return VISIBLE[n] == true end, IsLevelLoaded = function() return VISIBLE[n] == true end })
                fn(1, { get = function() return ls end })
            end
        end },
        SpawnActor = function(self, cls, loc, rot)
            if cls.kind == "loader" then
                LOADERS[cls.name] = obj({ K2_GetActorLocation = function() return loc end, GetFName = function() return FName(cls.name) end })
                if SHOW_LEVELS then VISIBLE[cls.name] = true end
                return LOADERS[cls.name]
            end
            local a = obj({ loc = loc, K2_GetActorLocation = function() return loc end, OnRep_IsTeleporterActive = function() end,
                K2_GetActorRotation = function() return { Pitch = 0, Yaw = rot.Yaw, Roll = 0 } end,
                GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end, ParticleLoop = { SetAsset = function() end, Activate = function() end } })
            a.K2_DestroyActor = function() a.gone = true end
            SPAWNED[#SPAWNED + 1] = a
            return a
        end })
end
WORLD = new_world()
local baseFind = StaticFindObject
LEVELS_LATE = 0       -- the game's level table stays unloaded for this many more StaticFindObject calls after a map load
LEVELS_LOADABLE, LEVELS_LOADS = false, 0   -- true: the hub's LoadAsset of the table's package loads it (fresh game start, CRD-022)
function LoadAsset(p)
    if p == "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels" then   -- only the object path loads (as with the zone class in game)
        LEVELS_LOADS = LEVELS_LOADS + 1
        if LEVELS_LOADABLE then LEVELS_LATE = 0 end
    end
end
function StaticFindObject(p)
    if p == "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels" and LEVELS_LATE > 0 then LEVELS_LATE = LEVELS_LATE - 1; return nil end
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
    return CLASSES[p] or baseFind(p)
end
function FindAllOf(n)
    if n == "BP_Teleporter_ParentBP_C" then
        local out = {}
        for _, a in ipairs(SPAWNED) do if not a.gone then out[#out + 1] = a end end
        return out
    end
    local w = n:match("^BP_(.+)_C$")
    if w and LOADERS[w] then return { LOADERS[w] } end
    return {}
end
function NotifyOnNewObject(class, fn) ON_HOMEWORLD = fn end
function RegisterKeyBind(key, a, b) end

-- quit to the menu and load a save, without restarting the game
function new_map(where, z)
    WORLD.dead = true
    WORLD = new_world()
    LOADERS, VISIBLE, SPAWNED = {}, {}, {}
    PC.ActiveLevelFXName = FName("None")
    PC.ActiveLevelName = "Facility_Office1"
    LOC.X, LOC.Y, LOC.Z = where, 0, z or 80
    MODE, MIN_Z = 3, LOC.Z
end
function here()
    for _, n in ipairs(NAMES) do
        if math.abs(LOC.X - ORIGIN[n]) < 100000 then return n end
    end
end

-- the player: held (mode 0), standing on a visible level, or falling. Teleports land where they say.
MODE, MIN_Z = 3, 80
PAWN.CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function(self, m) MODE = m end }
PAWN.K2_TeleportTo = function(self, loc) LOC.X, LOC.Y, LOC.Z = loc.X, loc.Y, loc.Z; return true end
function move_player()
    if MODE == 0 then return end
    local w = here()
    if not w or (VISIBLE[w] and LOC.Z > 0) then
        if LOC.Z > 0 then LOC.Z = 80 end
    else
        LOC.Z = LOC.Z - 400
    end
    if LOC.Z < MIN_Z then MIN_Z = LOC.Z end
end
function show_all() for _, n in ipairs(NAMES) do if LOADERS[n] then VISIBLE[n] = true end end end
function count_log(s) local n = 0; for _, l in ipairs(LOGS) do if l:find(s, 1, true) then n = n + 1 end end; return n end
function portal_on(id)
    for _, a in ipairs(SPAWNED) do if not a.gone and a.MyTeleporterID and a.MyTeleporterID.s == id then return a.IsTeleporterActive end end
end
''')
L.execute(open(MAIN, encoding="utf-8").read())

results = []
def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail != "" and not cond else ""))
def tick(n=1):
    for _ in range(n):
        g.T = g.T + 0.25
        L.execute("pump(); move_player()")
lua = L.eval
count = lambda s: lua("count_log([[%s]])" % s)

# ---- first load: five worlds, one timer chain each for the checks and the tracker
L.execute("ON_HOMEWORLD()")
tick()
check("first load: five worlds are checked", count("world(s) start over") == 0 and count("waiting for the level to stream in") == 5, count("waiting for the level to stream in"))
most = 0
for _ in range(6):
    tick(); most = max(most, lua("#QUEUE"))
check("five loading worlds use one shared chain (plus the tracker's)", most == 2, most)
check("the portals wait for their worlds", lua("portal_on('hub_C1')") is False)
L.execute("show_all()"); tick(2)
check("all five worlds are ready", count("is ready after") == 5, count("is ready after"))
check("the shared chain has ended, the tracker goes on", lua("#QUEUE") == 1, lua("#QUEUE"))
check("the portals are on", lua("portal_on('hub_C1')") is True)

# ---- walking in
L.execute("LOC.X = ORIGIN.world_b"); tick(2)
check("walked into World B: claimed", count("vignette: inside world_b_start") == 1)

# ---- ten quit-to-menu reloads inside World B, the level taking a moment each time
for i in range(10):
    L.execute("new_map(ORIGIN.world_b)")
    tick(3)
    held = count("hold: the player is inside a world that is still loading") == i + 1
    still = lua("LOC.Z") == 80 and lua("MODE") == 0
    claimedEarly = count("vignette: inside world_b_start") != i + 1
    L.execute("show_all()"); tick(2)
    landed = count("hold: the world is ready; the player is back on the ground") == i + 1 and lua("LOC.Z") == 80 and lua("MODE") == 3
    claimed = count("vignette: inside world_b_start") == i + 2
    entry = lua("PC.ActiveLevelFXName.s") == "PortalHub_world_b_start"
    L.execute("ON_HOMEWORLD()"); tick(3); L.execute("show_all()"); tick(2)
    if not (held and still and not claimedEarly and landed and claimed and entry):
        check("reload %d" % (i + 1), False, (held, still, claimedEarly, landed, claimed, entry, lua("MIN_Z")))
        break
else:
    check("ten reloads inside World B: held, landed, claimed once each", True)
check("nobody fell during the reloads", lua("MIN_Z") == 80, lua("MIN_Z"))
check("no rescue ran", count("rescue:") == 0, count("rescue:"))
check("each reload was noticed once", count("a new map was loaded") == 10, count("a new map was loaded"))
check("every world is ready after them", count("is ready after") == 5 + 50, count("is ready after"))
check("a portal is on after them", lua("portal_on('hub_C2')") is True)
check("the tracker runs alone again", lua("#QUEUE") == 1, lua("#QUEUE"))
check("no tracker errors", count("tracker error") == 0)

# ---- the portal room's load comes first: the world portals must start off
L.execute("new_map(ORIGIN.world_b)"); before = count("vignette: inside world_b_start")
L.execute("ON_HOMEWORLD()"); tick()
check("spawn_all first: the portals start off", lua("portal_on('hub_C1')") is False, lua("portal_on('hub_C1')"))
tick(2)
check("spawn_all first: the player is held, no fall", lua("LOC.Z") == 80 and lua("MODE") == 0, (lua("LOC.Z"), lua("MODE")))
L.execute("show_all()"); tick(2)
check("spawn_all first: claimed once", count("vignette: inside world_b_start") == before + 1)

# ---- a reload while the worlds are still loading
L.execute("new_map(ORIGIN.world_b)"); L.execute("ON_HOMEWORLD()"); tick(3)
L.execute("new_map(ORIGIN.world_b)"); tick(3)
check("reload while loading: not treated as failed", count("the game world changed while loading") >= 1 and count("rescue:") == 0, count("rescue:"))
check("reload while loading: the player is held", lua("LOC.Z") == 80 and lua("MODE") == 0, (lua("LOC.Z"), lua("MODE")))
L.execute("ON_HOMEWORLD()"); tick(3); L.execute("show_all()"); tick(3)
check("reload while loading: on the ground, one chain left", lua("LOC.Z") == 80 and lua("MODE") == 3 and lua("#QUEUE") == 1, (lua("LOC.Z"), lua("MODE"), lua("#QUEUE")))

# ---- a save made inside another world, then one in the Facility
before = count("vignette: inside world_d_start")
L.execute("new_map(ORIGIN.world_d)"); tick(3); L.execute("show_all()"); tick(2)
check("reload into World D: claimed there", count("vignette: inside world_d_start") == before + 1 and lua("PC.ActiveLevelFXName.s") == "PortalHub_world_d_start")
L.execute("ON_HOMEWORLD()"); tick(3); L.execute("show_all()"); tick(2)
L.execute("new_map(-10000)")
L.execute("PC.ActiveLevelFXName = FName('office1')")
L.execute("ON_HOMEWORLD()"); tick(3); L.execute("show_all()"); tick(2)
check("reload in the Facility: the game's level entry is left alone", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))
before = count("vignette: inside world_b_start")
L.execute("LOC.X = ORIGIN.world_b"); tick(2)
check("then walking into World B claims it", count("vignette: inside world_b_start") == before + 1)
tick(8)
check("and only once", count("vignette: inside world_b_start") == before + 1)

# ---- the game's level table loads a moment after the world is ready (seen in game, 7 November): the claim is tried again
L.execute("LOC.X = -10000"); tick(2)
before = count("vignette: inside world_b_start")
L.execute("new_map(ORIGIN.world_b); LEVELS_LATE = 1000"); tick(3); L.execute("show_all()"); tick(2)
check("level table late: not claimed yet", count("vignette: inside world_b_start") == before and count("level table is not loaded yet") >= 1)
L.execute("LEVELS_LATE = 0"); tick(3)
check("level table late: claimed once it is there", count("vignette: inside world_b_start") == before + 1 and lua("PC.ActiveLevelFXName.s") == "PortalHub_world_b_start", lua("PC.ActiveLevelFXName.s"))
tick(8)
check("level table late: and only once", count("vignette: inside world_b_start") == before + 1)
L.execute("LOC.X = -10000"); tick(2)
# fresh game start (CRD-022, in game 10 November): the table took over 10 s; the claim keeps trying while the player is inside, quietly
before, notLoaded = count("vignette: inside world_b_start"), count("level table is not loaded yet")
L.execute("new_map(ORIGIN.world_b); LEVELS_LATE = 100000"); tick(3); L.execute("show_all()"); tick(140)
check("level table very late: still trying after 30 tries, a line every 10",
      count("could not be marked as a vignette after 10 tries; trying again") == 1 and count("after 30 tries; trying again") == 1
      and count("vignette: inside world_b_start") == before, (count("after 10 tries"), count("after 30 tries")))
check("level table very late: only the first 10 tries say why", count("level table is not loaded yet") - notLoaded == 10,
      count("level table is not loaded yet") - notLoaded)
check("level table very late: no longer gives up", count("it stays a Facility area until the player comes back in") == 0)
L.execute("LEVELS_LATE = 0"); tick(6)
check("level table very late: claimed once it loads", count("vignette: inside world_b_start") == before + 1
      and count("world_b_start was marked as a vignette on try") == 1 and lua("PC.ActiveLevelFXName.s") == "PortalHub_world_b_start",
      lua("PC.ActiveLevelFXName.s"))
tick(8)
check("level table very late: and only once", count("vignette: inside world_b_start") == before + 1)
L.execute("LOC.X = -10000"); tick(2)
check("level table very late: leaving puts the Facility row back", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))
# fresh game start as seen in game (10 November): the game never loads the table by itself, so the hub loads it
before = count("vignette: inside world_b_start")
L.execute("new_map(ORIGIN.world_b); LEVELS_LATE = 100000; LEVELS_LOADABLE = true; LEVELS_LOADS = 0"); tick(3); L.execute("show_all()"); tick(2)
check("table never loaded by the game: the hub loads it and claims on the first try",
      count("vignette: inside world_b_start") == before + 1 and count("level table was not loaded yet; loaded it") == 1
      and lua("LEVELS_LOADS") == 1 and lua("PC.ActiveLevelFXName.s") == "PortalHub_world_b_start", (lua("LEVELS_LOADS"), lua("PC.ActiveLevelFXName.s")))
L.execute("LOC.X = -10000; LEVELS_LOADABLE = false"); tick(2)
check("table never loaded by the game: leaving puts the Facility row back", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))
# leaving while still trying stops the tries; coming back starts over
L.execute("new_map(ORIGIN.world_b); LEVELS_LATE = 100000"); tick(3); L.execute("show_all()"); tick(20)
L.execute("LOC.X = -10000"); tick(2); n0 = count("tries; trying again"); tick(80)
check("left while trying: no more tries outside", count("tries; trying again") == n0, count("tries; trying again") - n0)
L.execute("LEVELS_LATE = 0")

# ---- CRD-022: after a reload the fresh controller holds "None" as its level entry; leaving must not put "None" back
L.execute("LOC.X = -10000"); tick(2)
L.execute("new_map(ORIGIN.world_b); PC.ActiveLevelName = 'V_ISLAND'"); tick(3); L.execute("show_all()"); tick(2)
check("reload, None row: claimed, previous row logged as unknown",
      count("level entry PortalHub_world_b_start, was unknown (None), will fall back to office1") >= 1, lua("PC.ActiveLevelFXName.s"))
L.execute("LOC.X = -10000"); tick(2)
check("reload, None row: leaving puts the Facility row back, not None",
      lua("PC.ActiveLevelFXName.s") == "office1" and count("level entry back to office1 (previous one unknown)") >= 1, lua("PC.ActiveLevelFXName.s"))
check("reload, None row: the stale level name is not put back", lua("PC.ActiveLevelName:ToString()") == "Facility_Office1", lua("PC.ActiveLevelName:ToString()"))

# a real previous row is still put back, with its level name
L.execute("LEVEL_ROWS.v_island = LEVEL_ROWS.office1; PC.ActiveLevelFXName = FName('v_island'); PC.ActiveLevelName = 'V_ISLAND'")
L.execute("LOC.X = ORIGIN.world_b"); tick(2)
check("known row: logged as the previous row", count("level entry PortalHub_world_b_start, was v_island)") >= 1)
L.execute("LOC.X = -10000"); tick(2)
check("known row: put back with its level name", lua("PC.ActiveLevelFXName.s") == "v_island" and lua("PC.ActiveLevelName:ToString()") == "V_ISLAND",
      (lua("PC.ActiveLevelFXName.s"), lua("PC.ActiveLevelName:ToString()")))

# empty, or a row of ours left from before a mod restart: unknown too
for raw in ("", "PortalHub_world_c_start"):
    L.execute("PC.ActiveLevelFXName = FName([[%s]]); PC.ActiveLevelName = 'Elsewhere'" % raw)
    L.execute("LOC.X = ORIGIN.world_b"); tick(2); L.execute("LOC.X = -10000"); tick(2)
    check("row '%s': falls back to the Facility row" % raw, lua("PC.ActiveLevelFXName.s") == "office1" and lua("PC.ActiveLevelName:ToString()") == "Facility_Office1",
          (lua("PC.ActiveLevelFXName.s"), lua("PC.ActiveLevelName:ToString()")))

# the retry path (level table late after a reload): the late claim also treats None as unknown
before = count("vignette: inside world_b_start")
L.execute("new_map(ORIGIN.world_b); LEVELS_LATE = 1000"); tick(3); L.execute("show_all()"); tick(2)
L.execute("LEVELS_LATE = 0"); tick(3)
check("retry path: claimed late, once", count("vignette: inside world_b_start") == before + 1 and lua("PC.ActiveLevelFXName.s") == "PortalHub_world_b_start")
L.execute("LOC.X = -10000"); tick(2)
check("retry path: leaving puts the Facility row back", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))

check("never put None back in the whole run", count("level entry back to None") == 0, count("level entry back to None"))
check("no rescue in the whole run", count("rescue:") == 0, count("rescue:"))
print("\n%d checks, %d passed, %d failed" % (len(results), sum(results), len(results) - sum(results)))
sys.exit(0 if all(results) else 1)
