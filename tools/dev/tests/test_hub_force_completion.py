# Forced completion (CRD-040): forceComplete = true on a hub portal to GATE Arch Defense (wall_start) or Some Distant Shore (DistantShore)
# points that world's Vignette_Zone at a hub flag and sets it; never the game's own flag. Runs the real hub main.lua against hub_mock.lua.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
MOCK = open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read()
MAIN = open(os.path.join(HUB, "main.lua"), encoding="utf-8").read()

GAME_FLAG = "DemoNeverSet"
SHORE = "PortalHub_force_distantshore_Completed"
WALL = "PortalHub_force_wall_Completed"
SHORE_AT = (332356, -333983)      # Some Distant Shore's zone, where the lab read it in game (15 November)
WALL_AT = (-334930, 333386)       # GATE Arch Defense's zone, the same
ISLAND_AT = (600000, 600000)      # another world whose zone also names the game's flag (far from both)

EXTRAS = r'''
local function obj(t) t.IsValid = function() return true end; return t end
FLAG_ROWS = {}
local dtFlags = obj({ FindRow = function(self, n) return FLAG_ROWS[n] end, AddRow = function(self, n, r) FLAG_ROWS[n] = r end })
ZONES = {}
function zone(x, y, flag)
    local z = obj({ PortalSicknessWorldFlag = { RowName = FName(flag) } })
    z.K2_GetActorLocation = function() return { X = x, Y = y, Z = 0 } end
    ZONES[#ZONES + 1] = z
    return z
end
SET_FLAGS, SET_CALLS, SHOWN = {}, {}, {}
FLAGS_LOADED = true
FS = obj({ HasWorldFlag = function(self, ctx, h) return FLAGS_LOADED and SET_FLAGS[h.RowName.s] == true end,
           HasWorldFlagsLoaded = function(self) return FLAGS_LOADED end,
           SetWorldFlag = function(self, h, on, ctx)
               assert(h.DataTablePath == nil, "a flag handle holds the row name only")
               SET_CALLS[#SET_CALLS + 1] = h.RowName.s .. "=" .. tostring(on); SET_FLAGS[h.RowName.s] = on or nil end })
local baseFind, baseAll, baseFirst = StaticFindObject, FindAllOf, FindFirstOf
function StaticFindObject(p)
    if p == "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags" then return dtFlags end
    return baseFind(p)
end
ZONE_SCANS = 0
function FindAllOf(n)
    if n == "Vignette_Zone_C" then ZONE_SCANS = ZONE_SCANS + 1; return ZONES end
    return baseAll(n)
end
function FindFirstOf(n) if n == "WorldFlagSubsystem" then return FS end return baseFirst(n) end
PAWN.Client_DisplayWarningMessage = function(self, text, colour, beep) SHOWN[#SHOWN + 1] = text.s .. " [" .. colour .. "]" end
'''

class Hub:
    def __init__(self, portals, before=""):
        self.L = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.g = self.L.globals()
        self.L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
        self.L.execute(MOCK)
        self.L.execute(EXTRAS)
        self.L.execute("CONFIG.portals = { %s }" % portals)
        if before: self.L.execute(before)
        self.L.execute(MAIN)
    def ev(self, s): return self.L.eval(s)
    def run(self, s): self.L.execute(s)
    def tick(self, n=1):
        for _ in range(n):
            self.g.T = self.g.T + 0.5; self.L.execute("pump()")
    def logs(self): return [self.g.LOGS[i] for i in range(1, len(self.g.LOGS) + 1)]
    def has(self, s): return any(s in l for l in self.logs())
    def calls(self): return [self.ev("SET_CALLS[%d]" % i) for i in range(1, self.ev("#SET_CALLS") + 1)]
    def shown(self): return [self.ev("SHOWN[%d]" % i) for i in range(1, self.ev("#SHOWN") + 1)]
    def zflag(self, i): return self.ev("ZONES[%d].PortalSicknessWorldFlag.RowName.s" % i)

res, ALL_CALLS = [], []
def check(n, c, d=""):
    res.append(c); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d != "" and not c else ""))
def done(h):
    ALL_CALLS.extend(h.calls())
    errs = [l for l in h.logs() if "forced completion error" in l or "tracker error" in l]
    check("  (no tracker or forced completion errors)", not errs, errs)

def at(h, xy): h.run("LOC.X, LOC.Y, LOC.Z = %d, %d, 500" % (xy[0] + 2000, xy[1] + 2000))
ZONES3 = "zone(%d, %d, 'DemoNeverSet'); zone(%d, %d, 'DemoNeverSet'); zone(%d, %d, 'DemoNeverSet')" % (SHORE_AT + WALL_AT + ISLAND_AT)
SHORE_P = '{ slot = "A-4", name = "Shore", destination = "DistantShore"%s }'
WALL_P = '{ slot = "B-1", name = "Wall", destination = "wall_start"%s }'

# ---- off by default: a portal to the world without the key changes nothing
h = Hub(SHORE_P % "" + ", " + WALL_P % "", ZONES3)
h.tick(12)
check("off by default: no zone re-pointed", [h.zflag(i) for i in (1, 2, 3)] == [GAME_FLAG] * 3, [h.zflag(i) for i in (1, 2, 3)])
check("off by default: SetWorldFlag never called", h.calls() == [], h.calls())
check("off by default: no 'on for' line", not h.has("forced completion: on for"))
done(h)

# ---- forceComplete = false is off too
h = Hub(SHORE_P % ", forceComplete = false", ZONES3)
h.tick(12)
check("forceComplete = false: off", h.zflag(1) == GAME_FLAG and h.calls() == [], (h.zflag(1), h.calls()))
done(h)

# ---- on for Distant Shore: its zone points at the hub flag, the flag is set once
h = Hub(SHORE_P % ", forceComplete = true" + ", " + WALL_P % "", ZONES3)
h.tick(6)
check("on, player in the Facility: flag set, but no zone scan", h.calls() == [SHORE + "=true"] and h.ev("ZONE_SCANS") == 0 and h.zflag(1) == GAME_FLAG,
      (h.calls(), h.ev("ZONE_SCANS")))
at(h, SHORE_AT)
h.tick(6)
check("on: config line names the world", h.has("forced completion: on for Some Distant Shore"))
check("on: hub flag row added to DT_WorldFlags", h.ev("FLAG_ROWS['%s'] ~= nil" % SHORE))
check("on: Distant Shore's zone waits for the hub flag", h.zflag(1) == SHORE, h.zflag(1))
check("on: the zone handle holds the row name only", h.ev("ZONES[1].PortalSicknessWorldFlag.DataTablePath") is None)
check("on: Arch Defense's zone untouched (not forced)", h.zflag(2) == GAME_FLAG, h.zflag(2))
check("on: a far zone on the game's flag untouched", h.zflag(3) == GAME_FLAG, h.zflag(3))
check("on: the hub flag set once", h.calls() == [SHORE + "=true"], h.calls())
h.tick(20)
check("on: still set only once after more ticks", h.calls() == [SHORE + "=true"], h.calls())
check("on: logged the set", h.has(SHORE + " set: portal sickness lifted in Some Distant Shore"))
check("on: the zone is kept: one scan in 16 ticks inside", h.ev("ZONE_SCANS") == 1, h.ev("ZONE_SCANS"))
# the zone streams out and back in: the new zone object holds the game's flag again and is re-pointed; the flag is not set again
h.run("GONE = ZONES[1]; ZONES[1] = nil; ZONES[1] = ZONES[2]; ZONES[2] = ZONES[3]; ZONES[3] = nil")
h.run("zone(%d, %d, 'DemoNeverSet')" % SHORE_AT)
h.tick(6)
check("zone reload, kept zone still valid: no rescan, not re-pointed yet", h.zflag(3) == GAME_FLAG and h.ev("ZONE_SCANS") == 1, (h.zflag(3), h.ev("ZONE_SCANS")))
# the kept zone object goes invalid (streamed out): one rescan finds the new one
h.run("GONE.IsValid = function() return false end")
h.tick(6)
check("zone reload: the new zone re-pointed", h.zflag(3) == SHORE, h.zflag(3))
check("zone reload: flag not set again", h.calls() == [SHORE + "=true"], h.calls())
check("zone reload: the invalid kept zone means one rescan", h.ev("ZONE_SCANS") == 2, h.ev("ZONE_SCANS"))
n_repoint = sum(1 for l in h.logs() if "Some Distant Shore's zone now waits for " + SHORE in l)
check("zone reload: one re-point line per zone load (2)", n_repoint == 2, n_repoint)
# a new load (a new controller): set again if the save does not have it (here cleared by hand, as lab NUMPAD 3 does)
h.run("SET_FLAGS['%s'] = nil; PC = setmetatable({}, { __index = PC })" % SHORE)
h.tick(6)
check("new load: flag set again once", h.calls() == [SHORE + "=true", SHORE + "=true"], h.calls())
done(h)

# ---- both worlds: any enabled portal to the world with the key counts
h = Hub(SHORE_P % "" + ", " + WALL_P % ", forceComplete = true" + ", " + '{ slot = "B-2", name = "Shore 2", destination = "DistantShore", forceComplete = true }', ZONES3)
at(h, SHORE_AT); h.tick(6); at(h, WALL_AT); h.tick(6)
check("both: Distant Shore forced by its second portal", h.zflag(1) == SHORE, h.zflag(1))
check("both: Arch Defense forced", h.zflag(2) == WALL, h.zflag(2))
check("both: each flag set once", sorted(h.calls()) == sorted([SHORE + "=true", WALL + "=true"]), h.calls())
check("both: far zone untouched", h.zflag(3) == GAME_FLAG)
done(h)

# ---- the save's flags not loaded yet: nothing is set until they are (the CRD-001 early-ask bug)
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + "; FLAGS_LOADED = false")
h.tick(12)
check("flags not loaded: not set yet", h.calls() == [], h.calls())
h.run("FLAGS_LOADED = true"); h.tick(6)
check("flags loaded: set once", h.calls() == [SHORE + "=true"], h.calls())
done(h)

# ---- already set in this save: not set again
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + "; SET_FLAGS['%s'] = true" % SHORE)
at(h, SHORE_AT); h.tick(12)
check("already set: SetWorldFlag not called", h.calls() == [], h.calls())
check("already set: zone still re-pointed", h.zflag(1) == SHORE, h.zflag(1))
done(h)

# ---- the undo: no portal has the key any more, the save still has the hub flag: cleared once, with a gray message
h = Hub(SHORE_P % "", ZONES3 + "; SET_FLAGS['%s'] = true" % SHORE)
h.tick(12)
check("undo: hub flag cleared once", h.calls() == [SHORE + "=false"], h.calls())
check("undo: gray message", any("Some Distant Shore: forced completion switched off" in m and m.endswith("[1]") for m in h.shown()), h.shown())
check("undo: zone left on the game's flag", h.zflag(1) == GAME_FLAG, h.zflag(1))
h.tick(20)
check("undo: not cleared again", h.calls() == [SHORE + "=false"], h.calls())
done(h)
# ---- no portal to the world at all: also cleared (a slot switched off is wiped, key and all)
h = Hub('{ slot = "A-3", name = "Test World", destination = "cordonatest_start" }', ZONES3 + "; SET_FLAGS['%s'] = true" % WALL)
h.tick(12)
check("undo, no portal at all: Arch Defense's flag cleared", h.calls() == [WALL + "=false"], h.calls())
done(h)
# ---- nothing set and nothing forced: no SetWorldFlag at all, no message
h = Hub(SHORE_P % "", ZONES3)
h.tick(12)
check("nothing set: no clear, no message", h.calls() == [] and not any("forced completion" in m for m in h.shown()), (h.calls(), h.shown()))
done(h)

# ---- client mode: a joining player's hub does nothing (the host's hub does it for everyone)
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + "; SET_FLAGS['%s'] = true; PC.HasAuthority = function() return false end; PC.IsLocalController = function() return true end" % WALL)
at(h, SHORE_AT); h.tick(30)
check("client: no zone scan", h.ev("ZONE_SCANS") == 0, h.ev("ZONE_SCANS"))
check("client: no zone re-pointed", h.zflag(1) == GAME_FLAG, h.zflag(1))
check("client: SetWorldFlag never called (no set, no clear)", h.calls() == [], h.calls())
done(h)
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + "; SET_FLAGS['%s'] = true; PC.HasAuthority = function() return true end; PC.IsLocalController = function() return true end" % WALL)
at(h, SHORE_AT); h.tick(30)
check("client control: the same run with authority (host) does act", h.zflag(1) == SHORE and sorted(h.calls()) == sorted([SHORE + "=true", WALL + "=false"]), (h.zflag(1), h.calls()))
done(h)

# ---- the key on another destination is ignored, with a log line
h = Hub('{ slot = "A-3", name = "Train", destination = "train_start", forceComplete = true }, '
        '{ slot = "A-4", name = "Test World", destination = "cordonatest_start", forceComplete = true }', ZONES3)
h.tick(12)
check("other destination: ignored with a log line (base-game world)", h.has("config entry 1: forceComplete is only for") and h.has("ignored for train_start"))
check("other destination: ignored with a log line (custom world)", h.has("config entry 2: forceComplete is only for") and h.has("ignored for cordonatest_start"))
check("other destination: nothing set or re-pointed", h.calls() == [] and h.zflag(1) == GAME_FLAG and h.zflag(2) == GAME_FLAG, h.calls())
done(h)

# ---- a zone a little off the recorded spot (300 m) still matches; one 2 km away does not
h = Hub(SHORE_P % ", forceComplete = true", "zone(%d, %d, 'DemoNeverSet'); zone(%d, %d, 'DemoNeverSet')" % (SHORE_AT[0] + 30000, SHORE_AT[1], SHORE_AT[0] + 200000, SHORE_AT[1]))
at(h, SHORE_AT); h.tick(12)
check("zone 300 m off the spot: re-pointed", h.zflag(1) == SHORE, h.zflag(1))
check("zone 2 km off the spot: untouched", h.zflag(2) == GAME_FLAG, h.zflag(2))
done(h)

# ---- a zone near the world that waits on another flag (a real ending) is never touched
h = Hub(SHORE_P % ", forceComplete = true", "zone(%d, %d, 'SomeRealEnding')" % SHORE_AT)
at(h, SHORE_AT); h.tick(20)
check("no zone found: rescans every 2 s for the first 5 tries", h.ev("ZONE_SCANS") == 5, h.ev("ZONE_SCANS"))
h.tick(20)
check("no zone found: one more rescan per 10 s", h.ev("ZONE_SCANS") == 6, h.ev("ZONE_SCANS"))
check("a zone on another flag is never re-pointed", h.zflag(1) == "SomeRealEnding", h.zflag(1))
done(h)

# ---- another player goes into the forced world (the host stays in the Facility): the AttemptTeleport hook wakes the zone search
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + """
function RegisterHook(name, fn) HOOK_FN = fn; return 1, 1 end
NOTIFY = {}
function NotifyOnNewObject(cls, fn) NOTIFY[cls] = fn end
local sfo = StaticFindObject
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return { IsValid = function() return true end } end
    return sfo(p)
end
function pad_obj(dest) return { IsValid = function() return true end, DestinationTeleporterID = FName(dest), MyTeleporterID = FName('toilet'),
    K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end } end
OTHER = { IsValid = function() return true end, K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end }
""")
h.run("NOTIFY['/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C']()")
h.tick(12)
check("other player: no scan before anyone goes in", h.ev("ZONE_SCANS") == 0 and h.zflag(1) == GAME_FLAG, h.ev("ZONE_SCANS"))
if h.ev("HOOK_FN") is not None:
    h.run("HOOK_FN({ get = function() return pad_obj('DistantShore') end }, { get = function() return OTHER end })")
    h.tick(4)
    check("other player: their pad use into Distant Shore wakes the search; zone re-pointed", h.zflag(1) == SHORE and h.ev("ZONE_SCANS") >= 1, (h.zflag(1), h.ev("ZONE_SCANS")))
    h.tick(140)
    n = h.ev("ZONE_SCANS")
    h.run("ZONES[1].IsValid = function() return false end"); h.tick(10)
    check("other player: after a minute with the host away, an invalid zone is not searched for again", h.ev("ZONE_SCANS") == n, (n, h.ev("ZONE_SCANS")))
else:
    check("other player: the hook was registered", False, "no hook")
done(h)

# ---- a mode-4 (manual) hub portal leads to its manual portal inside the world: that counts as going in too
HOOK_EXTRAS = """
function RegisterHook(name, fn) HOOK_FN = fn; return 1, 1 end
NOTIFY = {}
function NotifyOnNewObject(cls, fn) NOTIFY[cls] = fn end
local sfo = StaticFindObject
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return { IsValid = function() return true end } end
    return sfo(p)
end
function pad_obj(dest) return { IsValid = function() return true end, DestinationTeleporterID = FName(dest), MyTeleporterID = FName('toilet'),
    K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end } end
OTHER = { IsValid = function() return true end, K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end }
"""
h = Hub(SHORE_P % ', exits = "manual", forceComplete = true', ZONES3 + HOOK_EXTRAS)
h.run("NOTIFY['/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C']()")
h.tick(12)
if h.ev("HOOK_FN") is not None:
    h.run("HOOK_FN({ get = function() return pad_obj('hub_A4_manual') end }, { get = function() return OTHER end })")
    h.tick(4)
    check("manual hub portal (to hub_A4_manual) wakes the search too", h.zflag(1) == SHORE, h.zflag(1))
else:
    check("manual: the hook was registered", False, "no hook")
done(h)

# ---- stream-in watch: a forced world's zone is re-pointed as it is created, before it can give the sickness (the 2 s tick lost that race
# in game, 15 November). The zone is created with no flag read in yet; the hub looks again until the flag is there.
WATCH = """
NOTIFY, NOTIFY_COUNT = {}, 0
function NotifyOnNewObject(cls, fn) NOTIFY[cls] = fn; if cls:find("Vignette_Zone", 1, true) then NOTIFY_COUNT = NOTIFY_COUNT + 1 end end
local sfo2 = StaticFindObject
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Volumes/Vignette_Zone.Vignette_Zone_C" then return { IsValid = function() return true end } end
    return sfo2(p)
end
ZC = "/Game/Blueprints/Environment/Volumes/Vignette_Zone.Vignette_Zone_C"
"""
h = Hub(SHORE_P % ", forceComplete = true", WATCH)
h.tick(6)
check("watch: registered once for the vignette zone class", h.ev("NOTIFY_COUNT") == 1 and h.ev("NOTIFY[ZC]") is not None and h.has("watching for vignette zones"), h.ev("NOTIFY_COUNT"))
h.tick(10)
check("watch: not registered again", h.ev("NOTIFY_COUNT") == 1)
h.run("NEWZ = zone(%d, %d, 'None'); RET = NOTIFY[ZC](NEWZ)" % SHORE_AT)
check("watch: the callback returns nothing (a true would remove it)", h.ev("RET") is None)
h.run("pump()")
check("watch: flag not read in yet: left alone", h.ev("NEWZ.PortalSicknessWorldFlag.RowName.s") == "None")
h.run("NEWZ.PortalSicknessWorldFlag = { RowName = FName('DemoNeverSet') }; pump()")
check("watch: re-pointed as soon as the flag is there, without a tick", h.ev("NEWZ.PortalSicknessWorldFlag.RowName.s") == SHORE, h.ev("NEWZ.PortalSicknessWorldFlag.RowName.s"))
check("watch: logged as caught at stream-in", h.has("Some Distant Shore's zone caught as it streamed in (2 look(s))"), [l for l in h.logs() if "caught" in l])
check("watch: no zone scan for it (the player was never inside)", h.ev("ZONE_SCANS") == 0, h.ev("ZONE_SCANS"))
h.run("OTHERZ = zone(%d, %d, 'DemoNeverSet'); NOTIFY[ZC](OTHERZ); pump(); pump()" % ISLAND_AT)
# as in game: a new zone's position still reads 0, 0, 0, but its full name already names its map
h.run("WZ = zone(0, 0, 'None'); WZ.GetFullName = function() return 'Vignette_Zone_C /Game/Maps/V_TheWall.V_TheWall:PersistentLevel.Vignette_Zone_C_0' end; NOTIFY[ZC](WZ); pump()")
h.run("WZ.PortalSicknessWorldFlag = { RowName = FName('DemoNeverSet') }; pump()")
h.run("SZ = zone(0, 0, 'None'); SZ.GetFullName = function() return 'Vignette_Zone_C /Game/Maps/V_DistantShore.V_DistantShore:PersistentLevel.Vignette_Zone_C_0' end; NOTIFY[ZC](SZ); pump(); SZ.PortalSicknessWorldFlag = { RowName = FName('DemoNeverSet') }; pump()")
check("watch: Distant Shore's zone at 0, 0, 0 caught by its map name", h.ev("SZ.PortalSicknessWorldFlag.RowName.s") == SHORE, h.ev("SZ.PortalSicknessWorldFlag.RowName.s"))
check("watch: Arch Defense's zone (not forced in this run) left on the game's flag", h.ev("WZ.PortalSicknessWorldFlag.RowName.s") == GAME_FLAG, h.ev("WZ.PortalSicknessWorldFlag.RowName.s"))
h.run("NZ = zone(0, 0, 'None'); NZ.GetFullName = function() return 'Vignette_Zone_C /Game/Maps/V_TheWall.V_TheWall:PersistentLevel.Vignette_Zone_C_0' end; NOTIFY[ZC](NZ); for i = 1, 12 do pump() end")
check("watch: a forced-or-game world's zone that never reads its flag is logged as not caught", h.has("a vignette zone streamed in (Vignette_Zone_C /Game/Maps/V_TheWall"), [l for l in h.logs() if "not caught" in l])
check("watch: another world's zone on the game's flag untouched", h.ev("OTHERZ.PortalSicknessWorldFlag.RowName.s") == GAME_FLAG)
h.run("LOOKS = 0; SLOWZ = zone(%d, %d, 'None'); local mt = { __index = function(t, k) if k == 'PortalSicknessWorldFlag' then LOOKS = LOOKS + 1; return { RowName = FName('None') } end end }; SLOWZ.PortalSicknessWorldFlag = nil; setmetatable(SLOWZ, mt); NOTIFY[ZC](SLOWZ); for i = 1, 20 do pump() end" % WALL_AT)
check("watch: a zone whose flag never reads in is looked at 10 times, then left", h.ev("LOOKS") == 10, h.ev("LOOKS"))
done(h)
h = Hub(SHORE_P % "", WATCH)
h.tick(12)
check("watch: nothing forced, no watch", h.ev("NOTIFY[ZC]") is None)
done(h)
h = Hub(SHORE_P % ", forceComplete = true", WATCH + "PC.HasAuthority = function() return false end; PC.IsLocalController = function() return true end")
h.tick(12)
check("watch: client, no watch", h.ev("NOTIFY[ZC]") is None)
done(h)

# ---- the sickness the zone gave in the same moment is taken off (lab F9 proved the call, 15 November): once the zone waits for the hub's
# flag and the flag is set, every player in that world (this machine's player, and players whose pad use led there) loses it
SICKMOCK = """
function buffcomp(sick)
    local bc = { IsValid = function() return true end, removes = {} }
    bc.list = sick and { "Buff_InVignette", "Debuff_PortalSickness" } or { "Buff_InVignette" }
    bc.CurrentBuffs = { ForEach = function(self, fn) for i, r in ipairs(bc.list) do fn(i, { get = function() return { BuffRow = { RowName = FName(r) } } end }) end end }
    bc.Server_RemoveBuff = function(self, row, stack, limb, expired)
        bc.removes[#bc.removes + 1] = row.RowName.s .. "/" .. tostring(stack) .. "/" .. tostring(limb) .. "/" .. tostring(expired)
        local out = {} for _, r in ipairs(bc.list) do if r ~= row.RowName.s then out[#out + 1] = r end end
        bc.list = out
        return true
    end
    return bc
end
PAWN.BuffComponent = buffcomp(true)
PAWN.GetFName = function() return FName("Player_Host") end
"""
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + SICKMOCK)
h.tick(6)
check("sickness: player outside the world: not touched", h.ev("#PAWN.BuffComponent.removes") == 0)
at(h, SHORE_AT); h.tick(6)
check("sickness: taken off this machine's player in the forced world, once (row, entire stack, AllBones, not expired)",
      h.ev("#PAWN.BuffComponent.removes") == 1 and h.ev("PAWN.BuffComponent.removes[1]") == "Debuff_PortalSickness/true/0/false",
      (h.ev("#PAWN.BuffComponent.removes"), h.ev("PAWN.BuffComponent.removes[1]")))
check("sickness: logged", h.has("portal sickness taken off Player_Host in Some Distant Shore (returned true; 0 left)"), [l for l in h.logs() if "taken off" in l])
check("sickness: other buffs kept", h.ev("#PAWN.BuffComponent.list") == 1)
h.tick(10)
check("sickness: no further calls while it is gone", h.ev("#PAWN.BuffComponent.removes") == 1)
h.run("PAWN.BuffComponent.list[#PAWN.BuffComponent.list + 1] = 'Debuff_PortalSickness'"); h.tick(6)
check("sickness: given again (e.g. a re-entry race): taken off again", h.ev("#PAWN.BuffComponent.removes") == 2 and h.ev("#PAWN.BuffComponent.list") == 1)
done(h)

# not before the hub's flag is set (the zone would only give it back)
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + SICKMOCK + "FLAGS_LOADED = false")
at(h, SHORE_AT); h.tick(12)
check("sickness: flags not loaded / flag not set: not touched", h.ev("#PAWN.BuffComponent.removes") == 0)
h.run("FLAGS_LOADED = true"); h.tick(6)
check("sickness: once the flag is set: taken off", h.ev("#PAWN.BuffComponent.removes") == 1)
done(h)

# not forced: never touched; client: never touched
h = Hub(SHORE_P % "", ZONES3 + SICKMOCK)
at(h, SHORE_AT); h.tick(12)
check("sickness: world not forced: not touched", h.ev("#PAWN.BuffComponent.removes") == 0)
done(h)
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + SICKMOCK + "PC.HasAuthority = function() return false end; PC.IsLocalController = function() return true end")
at(h, SHORE_AT); h.tick(12)
check("sickness: client: not touched", h.ev("#PAWN.BuffComponent.removes") == 0)
done(h)

# another player whose pad use led into the world (the host stays in the Facility) loses it too; one standing elsewhere does not
h = Hub(SHORE_P % ", forceComplete = true", ZONES3 + SICKMOCK + HOOK_EXTRAS + """
FRIEND = { IsValid = function() return true end, BuffComponent = buffcomp(true), GetFName = function() return FName("Player_Friend") end,
           K2_GetActorLocation = function() return { X = %d, Y = %d, Z = 500 } end }
FAR = { IsValid = function() return true end, BuffComponent = buffcomp(true), GetFName = function() return FName("Player_Far") end,
        K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end }
""" % (SHORE_AT[0] + 1000, SHORE_AT[1]))
h.run("NOTIFY['/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C']()")
h.tick(6)
if h.ev("HOOK_FN") is not None:
    h.run("HOOK_FN({ get = function() return pad_obj('DistantShore') end }, { get = function() return FRIEND end })")
    h.run("HOOK_FN({ get = function() return pad_obj('fog_start') end }, { get = function() return FAR end })")
    h.tick(6)
    check("sickness: the friend who went in loses it", h.ev("#FRIEND.BuffComponent.removes") == 1 and h.ev("#FRIEND.BuffComponent.list") == 1,
          h.ev("#FRIEND.BuffComponent.removes"))
    check("sickness: a player who went elsewhere keeps theirs", h.ev("#FAR.BuffComponent.removes") == 0)
    check("sickness: the host (in the Facility) not touched", h.ev("#PAWN.BuffComponent.removes") == 0)
else:
    check("sickness: the hook was registered", False, "no hook")
done(h)

# the stream-in catch sweeps 0.3 s later, without waiting for the 2 s tick
h = Hub(SHORE_P % ", forceComplete = true", WATCH + SICKMOCK)
h.tick(6)                                         # flag set, watch on
at(h, SHORE_AT)
h.run("CZ = zone(%d, %d, 'DemoNeverSet'); NOTIFY[ZC](CZ); pump(); pump()" % SHORE_AT)
check("sickness: the stream-in catch takes it off right away", h.ev("#PAWN.BuffComponent.removes") == 1, h.ev("#PAWN.BuffComponent.removes"))
done(h)

check("the game's flag is never passed to SetWorldFlag (every run above)", not any(c.startswith(GAME_FLAG) for c in ALL_CALLS), ALL_CALLS)
check("only hub flags are ever passed to SetWorldFlag", all(c.startswith("PortalHub_force_") for c in ALL_CALLS), ALL_CALLS)

print("\n%d checks, %d passed, %d failed" % (len(res), sum(res), len(res) - sum(res)))
sys.exit(0 if all(res) else 1)
