# Vignette world type: completion flag row, zone pointed at it, proper exit pad. Runs the real hub main.lua against hub_mock.lua plus extras.
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
CONFIG.worlds.cordonatest_start.type = "vignette"
CONFIG.worlds.cordonatest_start.exit = { 600, 0, 0, 180 }
local function obj(t) t.IsValid = function() return true end; return t end
FLAG_ROWS, SPAWNED_ZONES, SPAWNED_PADS = {}, {}, {}
local dtFlags = obj({ FindRow = function(self, n) return FLAG_ROWS[n] end, AddRow = function(self, n, r) FLAG_ROWS[n] = r end })
local zoneClass, padClass = obj({ kind = "zone" }), obj({ kind = "pad" })
local homePad = obj({ RequiredWorldFlag = { DataTablePath = FName("/Game/Blueprints/DataTables/DT_WorldFlags") } })
local baseFind, baseAll = StaticFindObject, FindAllOf
function StaticFindObject(p)
    if p == "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags" then return dtFlags end
    if p == "/Game/Blueprints/Environment/Volumes/Vignette_Zone.Vignette_Zone_C" then return zoneClass end
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
    return baseFind(p)
end
function FindAllOf(n)
    if n == "Vignette_Zone_C" then return SPAWNED_ZONES end
    if n == "BP_Teleporter_ParentBP_C" then return SPAWNED_PADS end
    if n == "BP_Teleporter_HomeWorld_C" then return { homePad } end
    if n == "WorldFlagSubsystem" then return FS end
    return baseAll(n)
end
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = obj({ loc = loc, K2_GetActorLocation = function() return loc end, OnRep_IsTeleporterActive = function() end,
        ParticleLoop = { SetAsset = function() end, Activate = function() end },
        BuffVolume = obj({ SetBoxExtent = function() end }), PortalSicknessWorldFlag = { RowName = FName("None") } })
    if cls.kind == "zone" then SPAWNED_ZONES[#SPAWNED_ZONES + 1] = a else SPAWNED_PADS[#SPAWNED_PADS + 1] = a end
    return a
end
SET_FLAGS, SHOWN = {}, {}
FS = obj({ HasWorldFlag = function(self, ctx, h) return SET_FLAGS[h.RowName.s] == true end })
local baseFirst = FindFirstOf
function FindFirstOf(n) if n == 'WorldFlagSubsystem' then return FS end return baseFirst(n) end
PAWN.Client_DisplayWarningMessage = function(self, text, colour, beep) SHOWN[#SHOWN + 1] = text.s .. ' [' .. colour .. ']' end
''')
L.execute(open(os.path.join(HUB, "main.lua"), encoding="utf-8").read())

res = []
def check(n, c, d=""):
    res.append(c); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))
def tick(n=1):
    for _ in range(n):
        g.T = g.T + 0.5; L.execute("pump()")
lua = L.eval

L.execute("LOC.X, LOC.Y, LOC.Z = 1100500, 1300000, 80")
tick(2)
logs = [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
for l in logs:
    if "vignette" in l or "zone" in l or "exit" in l: print("    " + l)
flag = "PortalHub_cordonatest_start_Completed"
check("flag row added", lua("FLAG_ROWS['%s'] ~= nil" % flag))
check("flag row fields", lua("FLAG_ROWS['%s'].ReleaseGroup == 0 and type(FLAG_ROWS['%s'].DebugText) == 'string'" % (flag, flag)))
check("one zone spawned", lua("#SPAWNED_ZONES") == 1, lua("#SPAWNED_ZONES"))
check("zone waits for the flag", lua("SPAWNED_ZONES[1].PortalSicknessWorldFlag.RowName.s") == flag, lua("SPAWNED_ZONES[1].PortalSicknessWorldFlag.RowName.s"))
check("zone handle has the game's table path", lua("SPAWNED_ZONES[1].PortalSicknessWorldFlag.DataTablePath") == "/Game/Blueprints/DataTables/DT_WorldFlags")
pads = [lua("SPAWNED_PADS[%d].MyTeleporterID.s" % i) for i in range(1, lua("#SPAWNED_PADS") + 1)]
check("arrival pad and exit pad spawned", "cordonatest_start" in pads and "cordonatest_start_exit" in pads, pads)
ex = pads.index("cordonatest_start_exit") + 1
check("exit pad position = origin + exit", lua("SPAWNED_PADS[%d].loc.X" % ex) == 1100600 and lua("SPAWNED_PADS[%d].loc.Y" % ex) == 1300000)
check("exit pad returns to the hub portal", lua("SPAWNED_PADS[%d].DestinationTeleporterID.s" % ex) == "hub_A3", lua("SPAWNED_PADS[%d].DestinationTeleporterID.s" % ex))
check("exit pad sets the flag", lua("SPAWNED_PADS[%d].WorldFlagToTriggerOnUse.RowName.s" % ex) == flag)
# leave and come back: nothing doubled
L.execute("LOC.X, LOC.Y = -10000, 9000"); tick(1)
L.execute("LOC.X, LOC.Y = 1100500, 1300000"); tick(2)
check("still one zone after re-entry", lua("#SPAWNED_ZONES") == 1)
check("still one exit pad after re-entry", sum(1 for i in range(1, lua("#SPAWNED_PADS") + 1) if lua("SPAWNED_PADS[%d].MyTeleporterID.s" % i) == "cordonatest_start_exit") == 1)
shown = [lua('SHOWN[%d]' % i) for i in range(1, lua('#SHOWN') + 1)]
print('    shown so far:', shown)
check('sickness message on first entry', any('Portal sickness' in m for m in shown), shown)
L.execute("SET_FLAGS['%s'] = true" % flag); tick(5)
shown = [lua('SHOWN[%d]' % i) for i in range(1, lua('#SHOWN') + 1)]
check('completed message when the flag is set', any('completed' in m for m in shown), shown)
L.execute("SET_FLAGS['%s'] = nil" % flag); tick(5)
shown = [lua('SHOWN[%d]' % i) for i in range(1, lua('#SHOWN') + 1)]
check('cleared message when the flag is cleared', any('cleared' in m for m in shown), shown)
print('    all shown:', shown)
allLogs = [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
check("no tracker errors", not any("tracker error" in l for l in allLogs), [l for l in allLogs if "tracker error" in l])
print("\n%d checks, %d passed, %d failed" % (len(res), sum(res), len(res) - sum(res)))
