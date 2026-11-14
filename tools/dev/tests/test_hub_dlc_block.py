# The hub leads into the two DLC worlds only where the session owns the DLC (CRD-033). Stone Garden (H_Garden_*, entitlement row
# HomeworldGarden) and Torii (H_Japan_*, row SupportersEdition) are gated by the game's own home pads and level streaming; a hub portal must
# not get round that. LuciDin's ruling (13 November): the mod must not let players bypass the paid DLC; close every hand-edit route; and
# (14 November) owners may have hub portals there, by the game's own check (AbioticGameState:HasServerGameEntitlement, server-wide, as the
# game's own portals use it). Four guards in main.lua, for an area that is not owned:
#   names  any destination starting with h_garden / h_japan (any case). Always, owned or not: the hub's own pad IDs (hub_..., portalroom_...)
#          and custom worlds whose ID, loader or level names a DLC area
#   spots  manual portal spots, MHEs and the Failsafe Exit inside the area (custom-world origins, arrivals and vignette exits: always)
#   pads   a destination pad that stands inside the area (a player-built portal there)
#   use    a player who lands inside the area after using a hub pad is sent straight back (the backstop; it asks again, so an owner leaving
#          the session closes it)
# Also: owners get their portals, a session's ownership is asked at the spawn (unreadable = not owned), the dev key PAUSE (pretend not
# owned), a refused entry does not take its slot, the locked slots A-1 / A-2 and the game's own pads are untouched, NUMPAD 1, the Cabin.
#   python test_hub_dlc_block.py [path to a main.lua, default the repo's]
import sys, os, math
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HUB, "main.lua")

# spots inside the two areas: a few metres from each area's own arrival pad (the game's home pads, from the teleporter dump)
GARDEN = (122890.6, 160239.8, 59350.0)
TORII = (135877.3, 125090.2, 57019.9)
def near(p, dx=500, dy=300, dz=0): return (p[0] + dx, p[1] + dy, p[2] + dz)
def lua_spot(p, yaw=0): return "{ %.1f, %.1f, %.1f, %d }" % (p[0], p[1], p[2], yaw)

GAME = r'''
local function obj(t) t.IsValid = function() return t.gone ~= true end; return t end
PADS = {}
function gpad(id, dest, x, y, z, dlc)
    local p = obj({ MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), IsTeleporterActive = true, RequiredDLC = dlc,
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end, OnRep_IsTeleporterActive = function() end })
    p.BuffsToApplyOnUse = { ForEach = function() end }
    PADS[#PADS + 1] = p
    return p
end
-- the game's own home pads, all in the Facility's persistent level (always loaded), positions and rows from the teleporter dump
gpad("H_Garden_Entrance", "H_Garden_Start", -12711.6, 8761.7, 259.8, "HomeworldGarden")
gpad("H_Garden_Start", "H_Garden_Entrance", 122890.6, 160239.8, 59350.0, "HomeworldGarden")
gpad("H_Japan_Entrance", "H_Japan_Start", -13115.2, 8391.4, 259.8, "SupportersEdition")
gpad("H_Japan_Start", "H_Japan_Entrance", 135877.3, 125090.2, 57019.9, "SupportersEdition")
gpad("H_Cabin_Entrance", "H_Cabin_Start", -13024.8, 7990.4, -416.8)
gpad("H_Cabin_Start", "H_Cabin_Entrance", 125804.6, 109383.0, -2857.2)
gpad("train_start", "None", 333725.9, 12323.6, 934.2)
gpad("teleporterpad87", "teleporterpad87", 122900.0, 160300.0, 59350.0)      -- a player-built portal inside Stone Garden (as in the dump)

local padClass = obj({ kind = "pad" })
local homePad = obj({})
local baseFind, baseAll = StaticFindObject, FindAllOf
LOADER_CDO = nil       -- set to a table to give the test world's loader Blueprint settings (ArriveSpot, ...)
-- DLC ownership as the game answers it (AbioticGameState:HasServerGameEntitlement): OWNED[row] = true; NO_GAME_STATE = true: no game state
OWNED, ASKED, NO_GAME_STATE = {}, {}, false
ENT_TABLE = obj({ kind = "DT_GameEntitlements" })
local gameState = obj({ HasServerGameEntitlement = function(self, h)
    assert(h.DataTable == ENT_TABLE and h.RowName ~= nil, "bad entitlement handle")
    ASKED[#ASKED + 1] = h.RowName:ToString()
    return OWNED[h.RowName:ToString()] == true
end })
setmetatable(WORLD, { __index = function(t, k) if k == "GameState" and not NO_GAME_STATE then return gameState end end })
function StaticFindObject(p)
    if p == "/Game/Blueprints/DataTables/DT_GameEntitlements.DT_GameEntitlements" then return ENT_TABLE end
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
    if p == "/Game/Mods/CordonaTest/BP_CordonaTestLoader.Default__BP_CordonaTestLoader_C" and LOADER_CDO then return obj(LOADER_CDO) end
    return baseFind(p)
end
function FindAllOf(n)
    if n == "BP_Teleporter_ParentBP_C" then
        local out = {}
        for _, p in ipairs(PADS) do if p:IsValid() then out[#out + 1] = p end end
        return out
    end
    return baseAll(n)
end
local baseFirst = FindFirstOf
function FindFirstOf(n) if n == "BP_Teleporter_HomeWorld_C" then return homePad end return baseFirst(n) end
SPAWNED = {}
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = obj({ K2_GetActorLocation = function() return loc end, yaw = rot.Yaw, OnRep_IsTeleporterActive = function() end,
        ParticleLoop = { SetAsset = function(self, s) end, Activate = function() end } })
    a.K2_DestroyActor = function() a.gone = true end
    a.SetActorHiddenInGame = function(self, h) a.hidden = h end
    PADS[#PADS + 1] = a
    SPAWNED[#SPAWNED + 1] = a
    return a
end
HOOKS, KEYS, SHOWN = {}, {}, {}
function RegisterHook(name, fn) HOOKS[#HOOKS + 1] = { name = name, fn = fn } end
function RegisterKeyBind(key, a, b) KEYS[key] = b or a end
PAWN.Client_DisplayWarningMessage = function(self, text, colour, beep) SHOWN[#SHOWN + 1] = text.s end
function find(id) for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID and p.MyTeleporterID:ToString() == id then return p end end end
function at_of(id) local l = find(id):K2_GetActorLocation(); return l end
-- every live pad the hub spawned that leads to a DLC pad, by its destination
function dlc_leads()
    local out = {}
    for _, a in ipairs(SPAWNED) do
        if a:IsValid() and a.DestinationTeleporterID then
            local d = a.DestinationTeleporterID:ToString():lower()
            if d:match("^h_garden_") or d:match("^h_japan_") then out[#out + 1] = a.MyTeleporterID:ToString() .. "->" .. d end
        end
    end
    return table.concat(out, ",")
end
function game_pad_ok(id, dest)
    local p = find(id)
    return p ~= nil and p.DestinationTeleporterID:ToString() == dest and p.IsTeleporterActive == true
end
-- a remote player (not this machine's pawn)
function player(name)
    local c = { at = { X = 0, Y = 0, Z = 0 }, moves = 0, modes = {} }
    c.PlayerState = obj({ GetFName = function() return FName("PlayerState_" .. name) end })
    c.K2_GetActorLocation = function() return { X = c.at.X, Y = c.at.Y, Z = c.at.Z } end
    c.GetFName = function() return FName("Char_" .. name) end
    c.K2_TeleportTo = function(self, loc, rot) c.at = { X = loc.X, Y = loc.Y, Z = loc.Z }; c.moves = c.moves + 1; return true end
    c.CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function(self, m) c.modes[#c.modes + 1] = m end }
    c.BuffComponent = obj({ Server_ApplyBuff = function() return true end })
    return obj(c)
end
-- the game: the player stands on the pad, is put 2 m in front of the destination pad, then the hooks run
function use(char, id)
    T = T + 2
    local p = find(id)
    local dest = p.DestinationTeleporterID:ToString()
    local d = find(dest)
    if d then local l = d:K2_GetActorLocation(); char.at = { X = l.X + 200, Y = l.Y, Z = l.Z } end
    for _, h in ipairs(HOOKS) do h.fn({ get = function() return p end }, { get = function() return char end }, {}) end
    return dest
end
function dist(char, x, y, z) local dx, dy, dz = char.at.X - x, char.at.Y - y, char.at.Z - z; return math.sqrt(dx * dx + dy * dy + dz * dz) end
'''

res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))

# where the hub puts a player: in front of a slot's pad (slots.lua: anchor, cyaw, +91.5 yaw, 4.4 lift; exit 215.1 ahead, 127.5 up)
ANCHORS = {"A-4": (-12610.1, 7745.9, 255.4, 0.1), "B-1": (-12719.0, 8788.2, -394.6, -170.3)}
def front(slot):
    x, y, z, cy = ANCHORS[slot]
    yaw = cy + 91.5
    return (x + math.cos(math.radians(yaw)) * 215.1, y + math.sin(math.radians(yaw)) * 215.1, z + 4.4 + 127.5)

HUBS = []
class Hub:
    def __init__(self, portals, top="", worlds="{}", mhe=None):
        HUBS.append(self)
        self.L = L = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.g = L.globals()
        L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
        L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
        if worlds != "keep":
            L.execute("CONFIG.worlds = %s" % worlds)
        L.execute("CONFIG.portals = %s" % portals)
        L.execute('MHE_T = %s; package.preload["manual_exits"] = function() return MHE_T end' % (mhe or "{}"))   # never the shipped file
        L.execute(GAME)
        if top:
            L.execute(top)
        L.execute(open(MAIN, encoding="utf-8").read())
        self.pump()
    def ev(self, x): return self.L.eval(x)
    def ex(self, x): self.L.execute(x)
    def pump(self, n=8):
        for _ in range(n): self.L.execute("pump()")
    def logs(self, since=0): return [self.g.LOGS[i] for i in range(since + 1, len(self.g.LOGS) + 1)]
    def n(self): return len(self.g.LOGS)
    def has(self, id): return self.ev("find(%r) ~= nil" % id)
    def dest(self, id): return self.ev("find(%r).DestinationTeleporterID:ToString()" % id)
    def said(self, text, since=0): return any(text in l for l in self.logs(since))
    def refused(self, dest, since=0): return self.said(dest + " is a DLC area and cannot be a destination, skipped", since)
    def use(self, who, pad):
        d = self.L.eval("use(%s, %r)" % (who, pad))
        self.pump()
        return d
    def at_front(self, who, slot):
        f = front(slot)
        return self.ev("dist(%s, %f, %f, %f)" % (who, f[0], f[1], f[2])) < 1
    def moves(self, who): return self.ev("%s.moves" % who)

def portals(*items): return "{ " + ", ".join(items) + " }"
def entry(slot, dest, extra=""): return '{ slot = "%s", name = "X", destination = "%s"%s }' % (slot, dest, extra)
GAME_PADS = (("H_Garden_Entrance", "H_Garden_Start"), ("H_Garden_Start", "H_Garden_Entrance"),
             ("H_Japan_Entrance", "H_Japan_Start"), ("H_Japan_Start", "H_Japan_Entrance"))
def game_pads_untouched(h): return all(h.ev("game_pad_ok(%r, %r)" % p) for p in GAME_PADS)
TEST_LOADER = 'loaderAsset = "/Game/Mods/CordonaTest/BP_CordonaTestLoader", loaderClass = "BP_CordonaTestLoader_C"'
def world(id, level="/Game/Mods/CordonaTest/Maps/CordonaTest_L0", origin=(1100000, 1300000, 0), extra="", loader=TEST_LOADER):
    return '{ %s = { %s, level = "%s", origin = { %.1f, %.1f, %.1f }%s } }' % (id, loader, level, origin[0], origin[1], origin[2], extra)

print("=== control: a plain world and the Cabin (story-gated by SnowglobeComplete, not DLC) get their hub portals")
h = Hub(portals(entry("A-4", "train_start"), entry("B-1", "H_Cabin_Start")))
check("the Train on A-4 gets hub_A4", h.has("hub_A4"))
check("the Cabin on B-1 is not a DLC world: hub_B1 is spawned and leads to H_Cabin_Start", h.has("hub_B1") and h.dest("hub_B1") == "H_Cabin_Start")
check("no DLC refusal logged", not h.said("cannot be a destination") and not h.said("inside a DLC area"), [l for l in h.logs() if "DLC" in l])

print("=== names: each DLC pad id and any other h_garden / h_japan name, in any letter case: refused, no pad")
for dest in ("H_Garden_Start", "H_Garden_Entrance", "H_Japan_Start", "H_Japan_Entrance",
             "h_garden_start", "H_GARDEN_START", "h_JaPaN_sTaRt", "H_Garden_Pond", "h_japan_bridge"):
    h = Hub(portals(entry("A-4", dest)))
    check("%s: refused with a log line, no hub portal on A-4" % dest, h.refused(dest) and not h.has("hub_A4"), h.logs())
    check("%s: nothing leads into a DLC world, the game's own DLC pads untouched" % dest, h.ev("dlc_leads()") == "" and game_pads_untouched(h))

print("=== names: the hub's own pads are never a destination (an MHE stands inside its world)")
for dest in ("hub_mhe_train_start", "HUB_A4", "Hub_failsafe", "hub_B1_manual", "portalroom_1"):
    h = Hub(portals(entry("B-1", dest), entry("A-4", "train_start")), mhe="{ train_start = { 336500, 8000, 880, 45 } }")
    check("%s: refused (one of the hub's own pads), no hub_B1" % dest,
          h.said(dest + " is one of the hub's own pads and cannot be a destination, skipped") and not h.has("hub_B1"), h.logs())

print("=== a mixed hand-edited config: only the DLC entries are dropped")
h = Hub(portals(entry("A-4", "train_start"), entry("B-1", "H_Garden_Start"), entry("B-2", "H_Japan_Start", ', exits = "dynamic"'),
                entry("C-1", "H_Garden_Entrance", ', design = "/Game/Particles/Niagara_Portal_Garden.Niagara_Portal_Garden"')))
check("the Train still gets hub_A4; B-1, B-2 and C-1 get no pad", h.has("hub_A4") and not h.has("hub_B1") and not h.has("hub_B2") and not h.has("hub_C1"))
check("three refusals logged", h.refused("H_Garden_Start") and h.refused("H_Japan_Start") and h.refused("H_Garden_Entrance"))
check("nothing the hub spawned leads into a DLC world, the game's own DLC pads untouched", h.ev("dlc_leads()") == "" and game_pads_untouched(h))

print("=== a refused entry does not take its slot: a later valid entry on the same slot is used")
h = Hub(portals(entry("B-1", "H_Japan_Start"), entry("B-1", "train_start")))
check("refused, then B-1 goes to the Train", h.refused("H_Japan_Start") and h.has("hub_B1") and h.dest("hub_B1") == "train_start")
check("no 'already used' line for B-1", not h.said("B-1 is already used"))

print("=== the locked slots A-1 (Stone Garden) and A-2 (Torii) stay the game's, whatever config.lua puts there")
h = Hub(portals(entry("A-1", "H_Garden_Start"), entry("A-2", "train_start"), entry("A-4", "train_start")))
check("A-1 and A-2 are skipped as game portals, no hub_A1 or hub_A2",
      h.said("slot A-1 holds a game portal, skipped") and h.said("slot A-2 holds a game portal, skipped") and not h.has("hub_A1") and not h.has("hub_A2"), h.logs())
check("the game's own A-1 / A-2 pads still lead into their worlds, active (the game gates them); A-4 works", game_pads_untouched(h) and h.has("hub_A4"))

print("=== exit mode \"manual\" to a DLC world: refused before any manual portal is placed")
h = Hub(portals(entry("A-4", "H_Garden_Start", ', exits = "manual"')), mhe="{ H_Garden_Start = %s }" % lua_spot(near(GARDEN)))
check("refused with the DLC line; no hub_A4, no hub_A4_manual", h.refused("H_Garden_Start") and not h.has("hub_A4") and not h.has("hub_A4_manual"))

print("=== spots: MHEs in a DLC area are not placed, the DLC homes' own included")
h = Hub(portals(entry("A-4", "train_start")),
        mhe="{ H_Garden_Start = %s, H_Japan_Start = %s, train_start = { 336500, 8000, 880, 45 } }" % (lua_spot(near(GARDEN)), lua_spot(near(TORII))))
check("Stone Garden's and Torii's MHEs are not spawned", not h.has("hub_mhe_H_Garden_Start") and not h.has("hub_mhe_H_Japan_Start"))
check("... each with a log line", h.said("MHE: H_Garden_Start") and h.said("MHE: H_Japan_Start"), h.logs())
check("the Train's own MHE (in the Train) is still spawned", h.has("hub_mhe_train_start"))
h = Hub(portals(entry("A-4", "H_Cabin_Start")), mhe="{ train_start = %s }" % lua_spot(near(TORII)))
check("an MHE hand-moved into Torii (the Train's key) is not spawned, with a line naming Torii",
      not h.has("hub_mhe_train_start") and h.said("MHE: train_start stands inside a DLC area (Torii)"), h.logs())

print("=== spots: exit mode \"manual\" whose MHE spot was hand-moved into a DLC area falls back to \"game\"")
h = Hub(portals(entry("A-4", "train_start", ', exits = "manual"')), mhe="{ train_start = %s }" % lua_spot(near(GARDEN)))
check("logged: the manual portal spot is inside Stone Garden, using game", h.said("is inside a DLC area (Stone Garden); the hub never leads there; using \"game\""), h.logs())
check("hub_A4 leads to train_start itself, no manual portal", h.has("hub_A4") and h.dest("hub_A4") == "train_start" and not h.has("hub_A4_manual"))
check("no pad the hub spawned stands inside Stone Garden",
      h.ev("(function() for _, a in ipairs(SPAWNED) do local l = a:K2_GetActorLocation(); if a:IsValid() and math.abs(l.X - %f) < 30000 and math.abs(l.Y - %f) < 30000 then return false end end return true end)()" % GARDEN[:2]))

print("=== spots: a Failsafe Exit hand-moved into a DLC area is replaced by the fallback spot")
h = Hub(portals(entry("A-4", "train_start")), mhe="{ fog_start = { 120000, -30000, 500, 0 }, failsafe = %s }" % lua_spot(near(GARDEN)))
check("logged: the recorded Failsafe Exit is inside Stone Garden", h.said("the recorded Failsafe Exit is inside a DLC area (Stone Garden)"), h.logs())
fs = h.ev("at_of('hub_failsafe')") if h.has("hub_failsafe") else None
check("the failsafe pad stands in the portal room, not in Stone Garden", fs is not None and abs(fs.X - (-12700)) < 3000 and abs(fs.Y - 8300) < 3000, fs and (fs.X, fs.Y))
check("fog's MHE leads to the failsafe", h.has("hub_mhe_fog_start") and h.dest("hub_mhe_fog_start") == "hub_failsafe")

print("=== names and spots: custom worlds that name or stand in a DLC area are refused, and so are their portals")
for wid, w, why in (("H_Garden_Copy", world("H_Garden_Copy"), "is named after a DLC area"),
                    ("my_world", world("my_world", level="/Game/Maps/Homeworlds/H_Japan"), "names a DLC area in its loader or level"),
                    ("my_world", world("my_world", loader='loaderAsset = "/Game/Mods/X/H_Garden_Loader", loaderClass = "H_Garden_Loader_C"'), "names a DLC area in its loader or level"),
                    ("my_world", world("my_world", origin=near(GARDEN)), "has its origin inside a DLC area (Stone Garden)"),
                    ("my_world", world("my_world", extra=", arrive = { %.1f, %.1f, %.1f, 0 }" % (TORII[0] - 1100000, TORII[1] - 1300000, TORII[2])), "arrives inside a DLC area (Torii)")):
    h = Hub(portals(entry("A-3", wid)), worlds=w)
    check("%s (%s): the world is refused" % (wid, why), h.said("worlds: '%s' %s; refused" % (wid, why)), h.logs())
    check("%s (%s): no hub portal, the world is never loaded" % (wid, why), not h.has("hub_A3") and not h.said("worlds: checking " + wid))
h = Hub(portals(entry("A-3", "my_world")), worlds=world("my_world", level="/Game/Mods/Th_Gardens/Maps/Th_Gardens_L0"))
check("Th_Gardens is not a DLC name: that world and its portal are kept", not h.said("refused") and h.has("hub_A3"), h.logs())

print("=== spots: the loader Blueprint's ArriveSpot inside a DLC area keeps the world's portals off")
h = Hub(portals(entry("A-3", "cordonatest_start")), worlds="keep")
check("control: the test world loads, its arrival pad is placed and hub_A3 is on",
      h.has("cordonatest_start") and h.ev("find('hub_A3').IsTeleporterActive") == True, h.logs())
h = Hub(portals(entry("A-3", "cordonatest_start")), worlds="keep",
        top="LOADER_CDO = { ArriveSpot = { X = %f, Y = %f, Z = %f } }" % (GARDEN[0] - 1100000, GARDEN[1] - 1300000, GARDEN[2]))
check("logged: it arrives inside Stone Garden, no arrival pad, portals off",
      h.said("worlds: cordonatest_start arrives inside a DLC area (Stone Garden); no arrival pad, its hub portals stay off"), h.logs())
check("no arrival pad, and hub_A3 stays off", not h.has("cordonatest_start") and h.has("hub_A3") and h.ev("find('hub_A3').IsTeleporterActive") == False)
h.ex("KEYS.NUM_ONE()"); h.pump()
check("after NUMPAD 1: hub_A3 is still off, still no arrival pad", h.ev("find('hub_A3').IsTeleporterActive") == False and not h.has("cordonatest_start"))

print("=== spots: a vignette's exit pad hand-moved into a DLC area is not placed")
FLAG_TABLE = ("FLAG_ROWS = {}; local dtFlags = { IsValid = function() return true end, FindRow = function(self, n) return FLAG_ROWS[n] end, "
              "AddRow = function(self, n, r) FLAG_ROWS[n] = r end }; local sf = StaticFindObject; "
              "function StaticFindObject(p) if p == '/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags' then return dtFlags end return sf(p) end; ")
h = Hub(portals(entry("A-3", "cordonatest_start")), worlds="keep",
        top=FLAG_TABLE + "CONFIG.worlds.cordonatest_start.exit = { %f, %f, %f, 0 }; CONFIG.worlds.cordonatest_start.type = 'vignette'" % (TORII[0] - 1100000, TORII[1] - 1300000, TORII[2]))
check("logged: the exit is inside Torii, not spawned; no cordonatest_start_exit pad",
      h.said("vignette: the exit of cordonatest_start is inside a DLC area (Torii)") and not h.has("cordonatest_start_exit"), [l for l in h.logs() if "vignette" in l])
check("the world itself (outside the areas) still works: arrival pad placed, hub_A3 on",
      h.has("cordonatest_start") and h.ev("find('hub_A3').IsTeleporterActive") == True)

print("=== pads: a destination pad standing inside a DLC area (a player-built portal there) gets no hub portal")
h = Hub(portals(entry("B-1", "teleporterpad87"), entry("A-4", "train_start")))
check("teleporterpad87 (in Stone Garden): not spawned, with a line naming the area",
      not h.has("hub_B1") and h.said("teleporterpad87: that pad stands inside a DLC area (Stone Garden)"), h.logs())
h = Hub(portals(entry("B-1", "TELEPORTERPAD87")))
check("the same pad in another letter case: not spawned either", not h.has("hub_B1"))
check("the Train still gets hub_A4 in the first run", HUBS[-2].has("hub_A4"))

print("=== use: the backstop sends a player who lands inside a DLC area straight back")
h = Hub(portals(entry("B-1", "teleporterpad99"), entry("A-4", "train_start")))
check("teleporterpad99 is not there when the portals spawn, so hub_B1 is spawned (it can't be checked yet)", h.has("hub_B1"))
h.ex('gpad("teleporterpad99", "teleporterpad99", %f, %f, %f); B = player("B")' % near(GARDEN, 800, -600))
n0 = h.n()
h.use("B", "hub_B1")
check("B is sent back to the front of hub_B1 (one move)", h.at_front("B", "B-1") and h.moves("B") == 1, h.ev("B.at.X"))
check("logged: landed inside Stone Garden after using hub_B1, sent back", h.said("landed inside Stone Garden", n0) and h.said("after using hub_B1; sent back", n0), h.logs(n0))
check("held still, then falling (MOVE_None, MOVE_Falling)", list(h.ev("B.modes").values()) == [0, 3], list(h.ev("B.modes").values()))
check("no on-screen line for a remote player", len(h.ev("SHOWN")) == 0)
h.ex("B.moves = 0")
h.use("B", "hub_A4")
check("B uses hub_A4 to the Train (outside the areas): left where the game put them", h.moves("B") == 0 and h.ev("dist(B, 333925.9, 12323.6, 934.2)") < 1)
h.use("B", "H_Garden_Entrance")
check("B uses the game's own Stone Garden portal: the game's business, not moved", h.moves("B") == 0)
print("=== use: this machine's own player gets the on-screen line")
h = Hub(portals(entry("B-1", "teleporterpad99")))
h.ex('LOC.X, LOC.Y, LOC.Z = %f, %f, %f' % near(TORII))
h.ex("for _, k in ipairs(HOOKS) do k.fn({ get = function() return find('hub_B1') end }, { get = function() return PAWN end }, {}) end")
h.pump()
shown = list(h.ev("SHOWN").values())
check("the local player standing in Torii after hub_B1 sees why", any("Torii is DLC: the Portal Hub doesn't lead there" in s for s in shown), shown)

print("=== owners (LuciDin, 14 November): where the session owns a DLC, the hub may lead there; the game's own check decides")
OWN_BOTH = "OWNED.HomeworldGarden = true; OWNED.SupportersEdition = true"
h = Hub(portals(entry("A-4", "H_Garden_Start"), entry("B-1", "h_japan_start", ', exits = "dynamic"')), top=OWN_BOTH)
check("at load nothing can be asked yet: the DLC entries wait for the spawn", h.said("ownership is checked when the portals spawn"), h.logs())
check("at the spawn: both owned, logged", h.said("DLC: Stone Garden is owned in this session") and h.said("DLC: Torii is owned in this session"))
check("hub_A4 leads into Stone Garden, hub_B1 into Torii", h.has("hub_A4") and h.dest("hub_A4") == "H_Garden_Start" and h.has("hub_B1") and h.dest("hub_B1") == "h_japan_start")
check("the game was asked with its own rows and table (HomeworldGarden, SupportersEdition)",
      set(h.ev("ASKED").values()) == {"HomeworldGarden", "SupportersEdition"})
check("the game's own DLC pads are untouched", game_pads_untouched(h))
h.ex("B = player('B')"); h.use("B", "hub_A4")
check("an owner's player who takes hub_A4 into Stone Garden stays there (no backstop move)", h.moves("B") == 0 and h.ev("dist(B, %f, %f, %f)" % (GARDEN[0] + 200, GARDEN[1], GARDEN[2])) < 1)
h = Hub(portals(entry("A-4", "H_Garden_Start"), entry("B-1", "H_Japan_Start")), top="OWNED.HomeworldGarden = true")
check("only Stone Garden owned: hub_A4 into Stone Garden, Torii refused", h.has("hub_A4") and not h.has("hub_B1")
      and h.refused("H_Japan_Start") and h.said("Torii is not owned in this session"), h.logs())
h = Hub(portals(entry("A-4", "hub_mhe_train_start"), entry("B-1", "H_Garden_Copy")), top=OWN_BOTH, worlds=world("H_Garden_Copy"),
        mhe="{ train_start = { 336500, 8000, 880, 45 } }")
check("owned or not, a hub pad ID is still refused", not h.has("hub_A4") and h.said("is one of the hub's own pads"))
check("owned or not, a custom world named after a DLC area is still refused", not h.has("hub_B1") and h.said("worlds: 'H_Garden_Copy' is named after a DLC area; refused"))
h = Hub(portals(entry("A-4", "train_start", ', exits = "manual"')), top=OWN_BOTH,
        mhe="{ train_start = %s, H_Garden_Start = %s, failsafe = %s, fog_start = { 120000, -30000, 500, 0 } }" % (lua_spot(near(GARDEN)), lua_spot(near(GARDEN, 900)), lua_spot(near(TORII))))
check("owned: a manual portal spot in Stone Garden is used (hub_A4_manual placed)", h.has("hub_A4_manual") and h.dest("hub_A4") == "hub_A4_manual")
check("owned: Stone Garden's own MHE is placed and leads to H_Garden_Entrance", h.has("hub_mhe_H_Garden_Start") and h.dest("hub_mhe_H_Garden_Start") == "H_Garden_Entrance")
fs = h.ev("at_of('hub_failsafe')") if h.has("hub_failsafe") else None
check("owned: a Failsafe Exit in Torii is used as recorded", fs is not None and abs(fs.X - TORII[0]) < 3000 and not h.said("recorded Failsafe Exit is inside"))
h = Hub(portals(entry("B-1", "teleporterpad87")), top=OWN_BOTH)
check("owned: a player-built portal inside Stone Garden may be a destination", h.has("hub_B1") and h.dest("hub_B1") == "teleporterpad87")

print("=== the owner leaves: the backstop asks again and sends players back")
h = Hub(portals(entry("A-4", "H_Garden_Start")), top=OWN_BOTH)
check("owned at the spawn: hub_A4 leads into Stone Garden", h.has("hub_A4"))
h.ex("OWNED = {}; B = player('B')")
n0 = h.n()
h.use("B", "hub_A4")
check("not owned any more: B is sent back to the front of hub_A4", h.at_front("B", "A-4") and h.moves("B") == 1, h.logs(n0))
check("logged: Stone Garden not owned (a player landed in it)", h.said("Stone Garden is not owned in this session: the hub never leads there (a player landed in Stone Garden)", n0), h.logs(n0))
h.ex("KEYS.NUM_ONE()"); h.pump()
check("NUMPAD 1 after that: hub_A4 is refused now", not h.has("hub_A4") and h.refused("H_Garden_Start"))
h.ex("OWNED.HomeworldGarden = true; KEYS.NUM_ONE()"); h.pump()
check("an owner joins, NUMPAD 1: hub_A4 is back", h.has("hub_A4") and h.dest("hub_A4") == "H_Garden_Start")

print("=== ownership that can't be read counts as not owned")
h = Hub(portals(entry("A-4", "H_Garden_Start")), top=OWN_BOTH + "; NO_GAME_STATE = true")
check("no game state: not readable, refused", not h.has("hub_A4") and h.said("Stone Garden is not readable, so treated as not owned"), h.logs())

print("=== dev key PAUSE (DEV_KEYS only, cut from the packaged hub): the DLC guard test for LuciDin's own run, as an owner of both DLCs")
h = Hub(portals(entry("A-4", "train_start"), entry("B-1", "H_Garden_Start")),
        top="PAWN.GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end; OWNED.HomeworldGarden = true; OWNED.SupportersEdition = true")
check("PAUSE is bound (dev key); as an owner, the config's Stone Garden portal is spawned", h.ev("KEYS.PAUSE ~= nil") and h.has("hub_B1"))
n0 = h.n()
h.ex("KEYS.PAUSE()"); h.pump()
check("1st press: pretend not owned ON, the portals respawn, the config's Stone Garden portal is gone",
      h.said("DLC test: pretend not owned ON", n0) and not h.has("hub_B1") and h.has("hub_A4"))
check("1st press: the self-check passes on the game's pads and the name rules, nothing fails",
      h.said("DLC test: self-check: 14 PASS, 0 FAIL", n0) and not h.said("DLC test: FAIL", n0), [l for l in h.logs(n0) if "DLC test" in l])
check("... it checked H_Garden_Start inside Stone Garden, H_Japan_Start inside Torii, the Cabin outside",
      h.said("PASS pad H_Garden_Start", n0) and h.said("PASS pad H_Japan_Start", n0) and h.said("PASS pad H_Cabin_Start", n0))
check("... and logged the game's real answer next to the pretend one",
      h.said("the game says Stone Garden (HomeworldGarden) is owned; the hub treats it as not owned", n0), [l for l in h.logs(n0) if "the game says" in l])
check("1st press: a test pad hub_dlctest leads into Stone Garden, 3 m in front of the player",
      h.has("hub_dlctest") and h.dest("hub_dlctest") == "H_Garden_Start" and abs(h.ev("at_of('hub_dlctest').X") - (-10000 + 300)) < 1)
h.ex("B = player('B')")
h.use("B", "hub_dlctest")
check("walking into it (pretend): the backstop sends B to the portal room (the front of the first hub portal)", h.at_front("B", "A-4") and h.moves("B") == 1)
h.ex("KEYS.PAUSE()"); h.pump()
check("2nd press: one test pad, now into Torii", h.dest("hub_dlctest") == "H_Japan_Start"
      and h.ev("(function() local n = 0; for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID and p.MyTeleporterID:ToString() == 'hub_dlctest' then n = n + 1 end end; return n end)()") == 1)
h.ex("B.moves = 0"); h.use("B", "hub_dlctest")
check("walking into it (pretend): back from Torii too", h.at_front("B", "A-4") and h.moves("B") == 1)
n1 = h.n()
h.ex("KEYS.PAUSE()"); h.pump()
check("3rd press: pretend OFF, the portals respawn and the config's Stone Garden portal is back", h.said("pretend not owned OFF", n1) and h.has("hub_B1"))
check("3rd press: the test pad leads into Stone Garden, owned", h.dest("hub_dlctest") == "H_Garden_Start" and h.said("owned: walk in and you should stay", n1))
h.ex("B.moves = 0"); h.use("B", "hub_dlctest")
check("walking into it as an owner: B stays in Stone Garden", h.moves("B") == 0 and h.ev("dist(B, %f, %f, %f)" % (GARDEN[0] + 200, GARDEN[1], GARDEN[2])) < 1)
h.ex("KEYS.PAUSE()"); h.pump()
check("4th press: the test pad is gone, pretend stays off", not h.has("hub_dlctest") and h.has("hub_B1"))
h = Hub(portals(entry("A-4", "train_start")), top="PAWN.GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end")
h.ex("B = player('B')"); h.ex("for i = 1, 3 do KEYS.PAUSE() end"); h.pump()
h.use("B", "hub_dlctest")
check("without the DLC, 3rd press: the test pad into Stone Garden still sends B back", h.at_front("B", "A-4") and h.moves("B") == 1)

print("=== the surveyed DLC boxes leave every shipped MHE and the failsafe alone (manual_exits.lua as committed, CRD-031)")
SHIPPED_MHE = os.path.join(HUB, "manual_exits.lua").replace("\\", "/")
h = Hub(portals(entry("A-4", "train_start")), top="MHE_T = dofile(%r)" % SHIPPED_MHE)
n_mhe = h.ev("(function() local n = 0; for k, v in pairs(MHE_T) do if k ~= 'failsafe' and type(v) == 'table' then n = n + 1 end end; return n end)()")
check("none of the %d shipped MHEs or the failsafe is refused as inside a DLC area" % n_mhe,
      n_mhe >= 20 and not h.said("inside a DLC area") and not h.said("is a DLC area"), [l for l in h.logs() if "DLC" in l])

print("=== NUMPAD 1 (respawn everything from the config read at load) brings no DLC portal back")
h = Hub(portals(entry("A-4", "train_start"), entry("B-1", "h_garden_start")))
check("at load: refused with the DLC line", h.refused("h_garden_start"))
h.ex("KEYS.NUM_ONE()"); h.pump()
check("after NUMPAD 1: hub_A4 is back, B-1 still empty, nothing leads into a DLC world",
      h.has("hub_A4") and not h.has("hub_B1") and h.ev("dlc_leads()") == "")

errs = [l for hb in HUBS for l in hb.logs() if "failed" in l]
check("no 'failed' lines in any run's log", not errs, errs)
print("\n%d/%d passed" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
