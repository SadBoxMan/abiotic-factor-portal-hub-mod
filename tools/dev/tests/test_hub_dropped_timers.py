# Dropped timers: UE4SS can lose queued ExecuteWithDelay callbacks when mods are restarted ("Hook threw exception: Ref was not function").
# A world's loading check and the presence tracker must then be restarted by NUMPAD 1 (spawn_all), without ever running twice.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mod", "PortalHub", "Scripts")

L = lupa.LuaRuntime(unpack_returned_tuples=True)
g = L.globals()
L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
L.execute(r'''
CONFIG.worlds.cordonatest_start.lighting = nil
local function obj(t) t.IsValid = function() return true end; return t end
KEYS, SPAWNED = {}, {}
function RegisterKeyBind(key, a, b) KEYS[key] = b or a end
local padClass = obj({ kind = "BP_Teleporter_ParentBP_C" })
local baseFind, baseAll = StaticFindObject, FindAllOf
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
    return baseFind(p)
end
function FindAllOf(n)
    if n == "BP_Teleporter_ParentBP_C" then
        local out = {}
        for _, a in ipairs(SPAWNED) do if not a.gone then out[#out + 1] = a end end
        return out
    end
    return baseAll(n)
end
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = obj({ kind = cls.kind, loc = loc, K2_GetActorLocation = function() return loc end, OnRep_IsTeleporterActive = function() end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = rot.Yaw, Roll = 0 } end,
        GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end, ParticleLoop = { SetAsset = function() end, Activate = function() end } })
    a.K2_DestroyActor = function() a.gone = true end
    SPAWNED[#SPAWNED + 1] = a
    return a
end
function count_log(s) local n = 0; for _, l in ipairs(LOGS) do if l:find(s, 1, true) then n = n + 1 end end; return n end
''')
L.execute(open(os.path.join(HUB, "main.lua"), encoding="utf-8").read())

results = []
def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))
def tick(n=1):
    for _ in range(n):
        g.T = g.T + 0.5; L.execute("pump()")
lua = L.eval

# the portal room loads: hub portals spawn, the world's loading check is queued ... and every queued timer is lost
L.execute("KEYS.NUM_ONE()")
L.execute("QUEUE = {}")
g.T = g.T + 30
tick(4)
check("timers lost: the world is not ready", lua("count_log('is ready after')") == 0)
check("timers lost: the hub portal is still off", lua("SPAWNED[1].IsTeleporterActive") is False, lua("SPAWNED[1].IsTeleporterActive"))
L.execute("LOC.X, LOC.Y, LOC.Z = 1100500, 1300000, 80"); tick(4)
check("timers lost: the tracker does nothing either", lua("count_log('vignette: inside')") == 0)
L.execute("LOC.X, LOC.Y = -10000, 9000")

# NUMPAD 1: both are found stale and started again
L.execute("KEYS.NUM_ONE()")
check("NUMPAD 1 restarts the loading check", lua("count_log('stopped running; starting it again')") == 1)
check("NUMPAD 1 restarts the tracker", lua("count_log('tracker: it stopped running')") == 1)
tick(2)
check("the world is ready afterwards", lua("count_log('is ready after')") == 1)
portal = "(function() for _, a in ipairs(SPAWNED) do if not a.gone and a.MyTeleporterID.s == 'hub_A3' then return a.IsTeleporterActive end end end)()"
check("its hub portal is on", lua(portal) is True, lua(portal))
L.execute("LOC.X, LOC.Y, LOC.Z = 1100500, 1300000, 80"); tick(2)
check("the tracker works again", lua("count_log('vignette: inside')") == 1)

# NUMPAD 1 while everything is running: nothing is restarted, and the tracker never runs twice per tick
L.execute("KEYS.NUM_ONE()")
check("no restart when nothing is stale", lua("count_log('stopped running; starting it again')") == 1 and lua("count_log('tracker: it stopped running')") == 1)
before = lua("#QUEUE")
tick(1)
check("one tracker loop only", lua("#QUEUE") == before, (before, lua("#QUEUE")))
allLogs = [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
check("no tracker errors", not any("tracker error" in l for l in allLogs), [l for l in allLogs if "tracker error" in l])
print("\n%d checks, %d passed, %d failed" % (len(results), sum(results), len(results) - sum(results)))
sys.exit(0 if all(results) else 1)
