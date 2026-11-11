# Hub client mode (CRD-027): every machine with the hub runs main.lua, so a player who joins someone else's game used to run a whole second
# hub (findings/two-player-test-plan.md, 1a). Where this machine's own controller has no authority, the hub now stands down: no pads spawned
# or destroyed, no exit moves, route_return or buffs, no world loaders, zones or arrival pads, no hold or rescue teleports. It keeps the local
# parts: its own hum volume on every hub-room pad it sees (again when a host portal arrives, counting the portals really there), its own look
# on a host portal that leads where its own portal in that slot does (once per pad), and the vignette claim / lighting on its own screen.
# Also: the local player controller (IsLocalController) is the one tracked, on the host too; clientMode = false switches client mode off; no
# controller yet means looking again before acting; NUMPAD 1 / 2 on a client.
#   python test_hub_client_mode.py [path to a main.lua, default the repo's]
import sys, os, math
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HUB, "main.lua")

GAME = r'''
local Slots = require("slots")
local function obj(t) t.IsValid = function() return t.gone ~= true end; return t end
TELEPORTER = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C"
PADS, SPAWNS, LOADER_SPAWNS, DESTROY_CALLS, NEXT = {}, 0, 0, 0, 0
NOTIFY, HOOKS, KEYS = {}, {}, {}
function NotifyOnNewObject(cls, fn) NOTIFY[cls] = NOTIFY[cls] or {}; table.insert(NOTIFY[cls], fn) end
function RegisterHook(name, fn) HOOKS[#HOOKS + 1] = { name = name, fn = fn } end
function RegisterKeyBind(key, a, b) KEYS[key] = b or a end
function n_notify(cls) return NOTIFY[cls] and #NOTIFY[cls] or 0 end

-- a teleporter as it stands on this machine (replicated = the host's, seen on a client: the engine will not destroy it here)
function mkpad(id, dest, x, y, z, replicated)
    local h = obj({ v = 1.0 })
    h.SetVolumeMultiplier = function(self, m) h.v = m end
    local p = obj({ MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), IsTeleporterActive = true, PortalHumLoop = h,
        replicated = replicated, OnRep_IsTeleporterActive = function() end,
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end,
        GetActorForwardVector = function() return { X = 1, Y = 0, Z = 0 } end,
        ParticleLoop = { assets = {}, SetAsset = function(self, s) table.insert(self.assets, s.path) end, Activate = function() end,
            SetEmitterEnable = function() end },
        PointLight = obj({ Intensity = 1000, SetLightColor = function(self, c) self.color = c end, SetIntensity = function(self, i) self.Intensity = i end }) })
    NEXT = NEXT + 1
    local nm = "BP_Teleporter_ParentBP_C_" .. NEXT
    p.GetFName = function() return FName(nm) end
    p.K2_DestroyActor = function() DESTROY_CALLS = DESTROY_CALLS + 1; if not p.replicated then p.gone = true end end
    p.SetActorHiddenInGame = function() end
    PADS[#PADS + 1] = p
    return p
end
-- a teleporter the engine constructs (fires NotifyOnNewObject like the game)
function arrive(p) for _, fn in ipairs(NOTIFY[TELEPORTER] or {}) do fn(p) end; return p end
-- the host's portal in a slot, replicated to this client
function host_pad(slot, dest, id)
    local loc = Slots.pose(Slots.byId[slot])
    return arrive(mkpad(id or ("hub_" .. slot:gsub("-", "")), dest, loc.X, loc.Y, loc.Z, true))
end
function find(id) for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID:ToString() == id then return p end end end
function dest_of(id) return find(id).DestinationTeleporterID:ToString() end

-- the game's own pads
mkpad("H_Garden_Entrance", "H_Garden_Start", -13115.2, 8391.4, 900)
mkpad("H_Japan_Entrance", "H_Japan_Start", -13115.2, 8391.4, 259.8)
mkpad("H_Cabin_Entrance", "H_Cabin_Start", -13024.8, 7990.4, -416.8)
mkpad("train_start", "None", 333725.9, 12323.6, 934.2)
mkpad("train_end", "train_exit", 340408.9, -1348.7, 649.6)
mkpad("train_exit", "None", 5639.8, 34391.1, 1713.5)
mkpad("anteverse_a_start", "anteverse_early_exit", 119175.3, 330450.7, 2332.4)
mkpad("anteverse_early_exit", "None", -14756.0, 23579.4, 2406.4)
mkpad("anteverse_a_exit", "anteverse_a_return", 119000, 330000, 2300)
mkpad("anteverse_a_return", "None", -14651.4, 19826.5, 2996.4)
for _, p in ipairs(PADS) do p.replicated = true end           -- level actors: never the hub's to destroy

local padClass = obj({ kind = "pad" })
local loaderClass = obj({ kind = "loader", name = "BP_CordonaTestLoader_C" })
local extraClass = obj({ kind = "loader", name = "BP_ExtraLoader_C" })
LOADER_PRESENT, EXTRA_PRESENT = false, false
local homePad = obj({})
local baseFind, baseAll, baseFirst = StaticFindObject, FindAllOf, FindFirstOf
function StaticFindObject(p)
    if p == TELEPORTER then return padClass end
    if p == "/Game/Mods/CordonaTest/BP_CordonaTestLoader.BP_CordonaTestLoader_C" then return (not NO_LOADER_CLASS) and loaderClass or nil end
    if p == "/Game/Mods/Extra/BP_ExtraLoader.BP_ExtraLoader_C" then return extraClass end
    if p:sub(1, 15) == "/Game/Particles" then return obj({ path = p }) end
    return baseFind(p)
end
CONTROLLERS = { PC }
function FindAllOf(n)
    if n == "BP_Teleporter_ParentBP_C" then
        local out = {}
        for _, p in ipairs(PADS) do if p:IsValid() then out[#out + 1] = p end end
        return out
    end
    if n == "Abiotic_PlayerController_C" then return CONTROLLERS end
    if n == "BP_CordonaTestLoader_C" then return LOADER_PRESENT and baseAll(n) or {} end
    if n == "BP_ExtraLoader_C" then
        return EXTRA_PRESENT and { obj({ GetFName = function() return FName("Extra") end, K2_GetActorLocation = function() return { X = 2100000, Y = 2300000, Z = 0 } end }) } or {}
    end
    return baseAll(n)
end
function FindFirstOf(n)
    if n == "BP_Teleporter_HomeWorld_C" then return homePad end
    if n == "Abiotic_PlayerController_C" then return CONTROLLERS[1] end     -- the first one found: on a host it may be a client's
    return baseFirst(n)
end
WORLD.SpawnActor = function(self, cls, loc, rot)
    if cls.kind == "loader" then
        LOADER_SPAWNS = LOADER_SPAWNS + 1
        if cls.name == "BP_ExtraLoader_C" then EXTRA_PRESENT = true else LOADER_PRESENT = true end
        return obj({})
    end
    SPAWNS = SPAWNS + 1                                          -- pads only
    local p = mkpad("None", "None", loc.X, loc.Y, loc.Z, false)
    return p
end

-- this machine's player: authority decides host or client
AUTH = true
PC.HasAuthority = function() return AUTH end
PC.IsLocalController = function() return true end
TELEPORTS = 0
PAWN.K2_TeleportTo = function() TELEPORTS = TELEPORTS + 1; return true end
PAWN.CharacterMovement = { modes = {}, StopMovementImmediately = function() end,
    SetMovementMode = function(self, m) table.insert(self.modes, m) end }

-- a player character using a pad: the game moves it to the destination first, then the hooks run
function player(name)
    local c = { at = { X = 0, Y = 0, Z = 0 }, moves = 0, buffs = {} }
    c.PlayerState = obj({ GetFName = function() return FName("PlayerState_" .. name) end })
    c.K2_GetActorLocation = function() return { X = c.at.X, Y = c.at.Y, Z = c.at.Z } end
    c.GetFName = function() return FName("Char_" .. name) end
    c.K2_TeleportTo = function(self, loc) c.at = { X = loc.X, Y = loc.Y, Z = loc.Z }; c.moves = c.moves + 1; return true end
    c.CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function() end }
    c.BuffComponent = obj({ Server_ApplyBuff = function(self, row) c.buffs[#c.buffs + 1] = row.RowName:ToString(); return true end })
    return obj(c)
end
function use(char, id)
    T = T + 2
    local p = find(id)
    local d = find(p.DestinationTeleporterID:ToString())
    if d then local l = d:K2_GetActorLocation(); char.at = { X = l.X + 200, Y = l.Y, Z = l.Z } end
    for _, h in ipairs(HOOKS) do h.fn({ get = function() return p end }, { get = function() return char end }, {}) end
end
function room_hums()      -- hum volume of every hub-room pad (game entrances + pads in slots), as a sorted list
    local out = {}
    for _, p in ipairs(PADS) do
        if p:IsValid() then
            local id = p.MyTeleporterID:ToString()
            if id:match("^H_.*_Entrance$") or id:match("^hub_[ABC]%d$") or id == "None" then out[#out + 1] = string.format("%.4f", p.PortalHumLoop.v) end
        end
    end
    table.sort(out)
    return table.concat(out, " ")
end
'''

res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))

HUBS = []
class Hub:
    def __init__(self, portals, top="", before=""):
        HUBS.append(self)
        self.L = L = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.g = L.globals()
        L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
        L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
        L.execute("CONFIG.portals = %s" % portals)
        L.execute('package.preload["manual_exits"] = function() return MHE_T or {} end')
        if top:
            L.execute(top)
        L.execute(GAME)
        if before:
            L.execute(before)
        L.execute(open(MAIN, encoding="utf-8").read())
        self.pump()
    def ev(self, x): return self.L.eval(x)
    def ex(self, x): self.L.execute(x)
    def pump(self, n=6):
        for _ in range(n): self.L.execute("pump()")
    def logs(self, since=0): return [self.g.LOGS[i] for i in range(since + 1, len(self.g.LOGS) + 1)]
    def n(self): return len(self.g.LOGS)
    def has(self, text, since=0): return any(text in l for l in self.logs(since))

def dyn(count): return "%.4f" % max(0.15, 1.0 - count * 0.85 / 9)
def dyn3(count): return "%.3f" % max(0.15, 1.0 - count * 0.85 / 9)

TEST = '{ slot = "A-3", name = "Test World", destination = "cordonatest_start" }'
TRAIN = '{ slot = "A-4", name = "The Train", destination = "train_start", exits = "dynamic" }'
FAR = '{ slot = "B-1", name = "Far Garden", destination = "anteverse_a_start", exits = "manual", manualBuffs = true }'
FAR_MHE = 'MHE_T = { anteverse_a_start = { 119300, 330300, 2300, 0 } }'
def portals(*items): return "{ " + ", ".join(items) + " }"
INSIDE = "LOC.X, LOC.Y, LOC.Z = 1100000, 1300000, 100"
OUTSIDE = "LOC.X, LOC.Y, LOC.Z = -10000, 9000, 300"

print("=== host (authority, the local controller): unchanged")
h = Hub(portals(TEST, TRAIN, FAR), top=FAR_MHE)
check("the hub logs that client mode is on", h.has("client mode: on"))
check("host: the configured portals, the manual portal and the MHE-less setup are spawned (3 hub pads + manual portal)",
      h.ev("find('hub_A3') ~= nil and find('hub_A4') ~= nil and find('hub_B1') ~= nil and find('hub_B1_manual') ~= nil"), h.logs()[-12:])
check("host: the hum is set by the host path (apply_hum), as before", h.has("hum volume (dynamic) x" + dyn3(3)) and h.has("(3 added)"), [l for l in h.logs() if "hum" in l])
check("host: the custom world's loader is spawned", h.ev("LOADER_SPAWNS") == 1)
check("host: no teleporter watch is registered (that is for clients only)", h.ev("n_notify(TELEPORTER)") == 0)
check("host: the AttemptTeleport hook is registered once", h.ev("#HOOKS") == 1)
h.ex("B = player('B')")
h.use = lambda who, pad: (h.ex("use(%s, %r)" % (who, pad)), h.pump())
h.ex("other = mkpad('hub_B4', 'cordonatest_start', -12610.1, 7745.9, -390)")
h.use("B", "hub_B4")
check("host: route_return points the custom world's arrival pad at the portal used", h.ev("dest_of('cordonatest_start')") == "hub_B4")
h.use("B", "hub_A4"); h.ex("B.moves = 0"); h.use("B", "train_end")
check("host: a dynamic exit moves the hub entrant on to the hub portal", h.ev("B.moves") == 1)
h.use("B", "hub_B1_manual")
check("host: manualBuffs gives the true exit's buff", list(h.ev("B.buffs").values()) == ["Buff_Hygroscopic"], list(h.ev("B.buffs").values()))
n = h.n(); h.ex("KEYS.NUM_TWO()")
check("host: NUMPAD 2 removes the hub's pads", h.ev("find('hub_A3') == nil and find('hub_A4') == nil") and h.has("removed", n))
h.ex("KEYS.NUM_ONE()"); h.pump()
check("host: NUMPAD 1 spawns them again", h.ev("find('hub_A3') ~= nil and find('hub_A4') ~= nil"))
check("host: no client-mode lines after load", not any(l.startswith("[PortalHub] client mode:") and "client mode: on" not in l for l in h.logs()),
      [l for l in h.logs() if "client mode" in l])

print("=== host with a client connected: the tracker follows the host's own player")
h = Hub(portals(TEST), before='''
CPAWN = { at = { X = 1100000, Y = 1300000, Z = 100 } }
CPAWN.IsValid = function() return true end
CPAWN.K2_GetActorLocation = function() return CPAWN.at end
CPAWN.GetFName = function() return FName("Pawn_Client") end
CPAWN.CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function() end }
CPC = { ActiveLevelFXName = FName("office1"), ActiveLevelName = FName("Facility_Office1"), Pawn = CPAWN, DisableAutomaticFX = false,
    ActiveWeatherFXName = FName("None"), Day_FX_Row = { RowName = FName("office1") }, Night_FX_Row = { RowName = FName("Office1_Night") } }
CPC.IsValid = function() return true end
CPC.HasAuthority = function() return true end                  -- on the host every controller has authority
CPC.IsLocalController = function() return false end
CPC.TransitionToNewEnvironmentFX = function() CPC.lit = true end
CPC.UpdateToNewEnvironmentFX = function() end
CONTROLLERS = { CPC, PC }                                       -- the client's is found first
LOADER_PRESENT = true
''')
h.pump(4)
check("the client standing in the custom world is not tracked as the host's player: its controller is untouched",
      h.ev("CPC.ActiveLevelFXName:ToString()") == "office1" and h.ev("CPC.lit") is None and not h.has("vignette: inside"), h.logs()[-6:])
check("... and the host's own controller is not claimed either (the host is outside)", h.ev("PC.ActiveLevelFXName:ToString()") == "office1")
h.ex(INSIDE); h.pump(3)
check("the host walks in: the host's own controller is claimed", h.ev("PC.ActiveLevelFXName:ToString()") == "PortalHub_cordonatest_start", h.logs()[-6:])

print("=== client (no authority): the hub stands down")
h = Hub(portals(TEST, TRAIN, FAR, '{ slot = "C-2", name = "Flathill", destination = "flathill_start" }',
                '{ slot = "C-4", name = "Torii look", destination = "train_start" }'),
        top=FAR_MHE, before='''
AUTH = false
CONFIG.worlds.extra_start = { loaderAsset = "/Game/Mods/Extra/BP_ExtraLoader", loaderClass = "BP_ExtraLoader_C", level = "/Game/Mods/Extra/Maps/Extra",
    origin = { 2100000, 2300000, 0 } }
table.insert(CONFIG.portals, { slot = "C-1", name = "Extra", destination = "extra_start" })
CONFIG.portals[1].design = "/Game/Particles/Niagara_Portal_Torii.Niagara_Portal_Torii"
CONFIG.portals[1].lightColor = { 0.2, 0.9, 0.4 }
CONFIG.portals[1].lightBrightness = 2
-- the host's portals, already replicated when the client's hub looks: A-3 to the same world, C-2 elsewhere, C-4 with no ID or destination
-- (not replicated), the host's manual portal of B-1 (in Far Garden)
host_pad("A-3", "cordonatest_start")
host_pad("C-2", "world_x_start")
host_pad("C-4", "None", "None")
HMAN = mkpad("hub_B1_manual", "hub_B1", 119300, 330300, 2300, true)
host_pad("B-1", "hub_B1_manual")
ARRIVAL = mkpad("cordonatest_start", "hub_A3", 1100000, 1300000, 0, true)    -- the host's arrival pad of the custom world
''')
check("client: the hub says it stands down", h.has("client mode: this player joined someone else's game"), h.logs()[-10:])
check("client: no pads spawned (no hub portals, manual portal, MHEs or failsafe)", h.ev("SPAWNS") == 0)
check("client: nothing destroyed (not even tried)", h.ev("DESTROY_CALLS") == 0)
check("client: the host has a portal in A-3, where its own config puts the custom world: loaded here ahead of time (one loader, logged)",
      h.ev("LOADER_SPAWNS") == 1 and h.has("the host has a portal in A-3, where your config puts cordonatest_start; loading it on this machine ahead of time"),
      [l for l in h.logs() if "worlds" in l or "loading" in l])
check("... ready with no arrival pad, zones or portal switching of its own", h.has("cordonatest_start is ready after") and h.has("loaded on this machine only")
      and not h.has("worlds: arrival pad") and not h.has("zone spawned") and not h.has("zone class"), [l for l in h.logs() if "worlds" in l or "zone" in l])
check("client: extra_start (C-1 in its config, no host portal there yet) is not loaded", not h.has("puts extra_start") and h.ev("EXTRA_PRESENT") is False)
check("client: the hum (its own dynamic) counts the 4 host portals really there, by ID or by place, and covers the 3 game entrances too",
      h.ev("room_hums()") == " ".join([dyn(4)] * 7), h.ev("room_hums()"))
check("client: the host's manual portal (not in the room) keeps its volume", h.ev("HMAN.PortalHumLoop.v") == 1.0)
check("client: the hum line is logged", h.has("client mode: hum volume (dynamic) x%s on 7 hub pad(s) (4 portal(s) from the host)" % dyn3(4)),
      [l for l in h.logs() if "hum" in l])
check("client: the teleporter watch is registered once", h.ev("n_notify(TELEPORTER)") == 1)
check("client: the hook is registered (inert)", h.ev("#HOOKS") == 1)
a3 = "find('hub_A3')"
check("client: its own look goes on the host's A-3 portal, which leads to the same world", h.ev(a3 + ".ParticleLoop.assets[1]") == "/Game/Particles/Niagara_Portal_Torii.Niagara_Portal_Torii")
check("client: ... with its own light colour and brightness", h.ev(a3 + ".PointLight.Intensity") == 2000 and abs(h.ev(a3 + ".PointLight.color.G") - 0.9) < 1e-9)
check("client: no look on C-2, where the host's portal leads elsewhere (logged)",
      h.ev("#find('hub_C2').ParticleLoop.assets") == 0 and h.has("the host's portal in C-2 leads to world_x_start (yours: flathill_start)"))
check("client: no look on C-4, whose destination did not come through (logged)", h.has("the host's portal in C-4 shows no destination here"))
check("client: B-1 (manual on both) leads to the same manual portal: look applied",
      h.ev("#find('hub_B1').ParticleLoop.assets") == 1 and h.has("your look for B-1"))

n = h.n()
h.ex("host_pad('B-2', 'alps_start')"); h.pump()
check("a host portal arrives (B-2): a moment later the hum is set on it and recounted (5)", h.ev("room_hums()") == " ".join([dyn(5)] * 8), h.ev("room_hums()"))
h.ex("host_pad('B-4', 'a'); host_pad('C-1', 'b'); host_pad('C-3', 'c')")
check("a burst of three: one look queued, not three", h.ev("#QUEUE") <= 2, h.ev("#QUEUE"))      # the tracker's own tick may be queued too
h.pump()
check("... then all counted (8)", h.ev("room_hums()") == " ".join([dyn(8)] * 11), h.ev("room_hums()"))
check("a host portal arrived in C-1: the world the client's config puts there is loaded then", h.has("the host has a portal in C-1, where your config puts extra_start")
      and h.ev("LOADER_SPAWNS") == 2)
h.ex("KEYS.NUM_ONE()"); h.pump(); h.ex("KEYS.NUM_ONE()"); h.pump()
check("NUMPAD 1 on a client: nothing spawned or destroyed", h.ev("SPAWNS") == 0 and h.ev("DESTROY_CALLS") == 0)
check("... and a pad's look and light are applied once only (brightness does not multiply again)",
      h.ev(a3 + ".PointLight.Intensity") == 2000 and h.ev("#" + a3 + ".ParticleLoop.assets") == 1)
n = h.n(); h.ex("KEYS.NUM_TWO()")
check("NUMPAD 2 on a client: nothing destroyed, and the log says why", h.ev("DESTROY_CALLS") == 0 and h.has("NUMPAD 2 does nothing here", n))

h.ex("C = player('C')")
def use(who, pad): h.ex("use(%s, %r)" % (who, pad)); h.pump()
h.ex("hb4 = mkpad('hub_X9', 'cordonatest_start', 0, 0, 0, true)")
use("C", "hub_X9")
check("client: no route_return (the host's arrival pad keeps the host's destination)", h.ev("dest_of('cordonatest_start')") == "hub_A3")
check("client: the hook says it ran here and did nothing", h.has("client mode: AttemptTeleport ran on this client (pad hub_X9)"))
h.ex("host_pad('A-4', 'train_start')")
use("C", "hub_A4"); h.ex("C.moves = 0"); use("C", "train_end")
check("client: no exit move (dynamic on its own config)", h.ev("C.moves") == 0)
use("C", "hub_B1_manual")
check("client: no buffs from the manual portal (manualBuffs on its own config)", h.ev("#C.buffs") == 0)
check("client: no hub-exit lines at all", not any("hub exits:" in l for l in h.logs()))

print("=== client in a custom world it had not loaded: loaded on arrival; no hold or rescue; the claim stays local")
h = Hub(portals(TEST), before="AUTH = false")
check("no host portal in A-3, so no guess: nothing loaded yet", h.ev("LOADER_SPAWNS") == 0)
h.ex(INSIDE + "; PAWN.CharacterMovement.modes = {}; TELEPORTS = 0")
n = h.n(); h.pump(4)
check("the host's teleport put the player in its area: the world is loaded on this machine (logged)", h.ev("LOADER_SPAWNS") == 1
      and h.has("the host's teleport brought this player into cordonatest_start's area; loading it on this machine", n), h.logs(n))
check("... with no hold, no teleport and no pads", h.ev("#PAWN.CharacterMovement.modes") == 0 and h.ev("TELEPORTS") == 0 and h.ev("SPAWNS") == 0, h.logs(n))
check("... no arrival pad or zones of its own", not h.has("worlds: arrival pad") and not h.has("zone spawned") and not h.has("zone class"), h.logs(n))
check("... and no hub portals spawned for it once it is ready (CRD-028 is the host's)", h.ev("PC.ActiveLevelFXName:ToString()") == "PortalHub_cordonatest_start"
      and not h.has("spawning the hub portals now") and h.ev("SPAWNS") == 0, h.logs(n))
check("... and the claim and lighting are made on this player's screen", h.ev("PC.ActiveLevelFXName:ToString()") == "PortalHub_cordonatest_start"
      and h.ev("#TRANSITIONS") >= 1, h.logs(n))
h.ex("LOC.Z = -5000"); h.pump(3)
check("falling below the world's killZ: no rescue teleport on a client", h.ev("TELEPORTS") == 0)
h.ex(OUTSIDE); h.pump(2)
check("leaving: the level entry is put back", h.ev("PC.ActiveLevelFXName:ToString()") == "office1")
h = Hub(portals(TEST), before="AUTH = false; NO_LOADER_CLASS = true")
h.ex(INSIDE + "; TELEPORTS = 0; T = 100"); n = h.n(); h.pump(4)
check("the world's pak is missing on this machine: logged, and no portal-room rescue (a teleport the server would undo)",
      h.has("cannot be loaded on this machine (is its pak installed?)", n) and h.ev("TELEPORTS") == 0, h.logs(n))

print("=== host in the same spot, for comparison: hold and loader")
h = Hub(portals(TEST), before="LOADER_PRESENT = false; " + INSIDE + "; AUTH = true")
check("host inside a world not loaded yet: loads it and holds the player", h.ev("LOADER_SPAWNS") == 1 and 0 in list(h.ev("PAWN.CharacterMovement.modes").values()))

print("=== the role read another way, and not known yet")
h = Hub(portals(TEST), before="PC.HasAuthority = nil; PC.GetLocalRole = function() return 2 end")
check("no HasAuthority, local role 2 (autonomous proxy): client", h.ev("SPAWNS") == 0 and h.has("client mode: this player joined"))
h = Hub(portals(TEST), before="PC.HasAuthority = nil; PC.GetLocalRole = function() return 3 end")
check("local role 3 (authority): host", h.ev("find('hub_A3') ~= nil"))
h = Hub(portals(TEST), before="PC.HasAuthority = nil")
check("authority unreadable: host (as before client mode)", h.ev("find('hub_A3') ~= nil") and not h.has("joined someone else's game"))
h = Hub(portals(TEST), before="CONTROLLERS = {}; AUTH = false")
check("no controller yet: the portals wait, and the log says why", h.ev("SPAWNS") == 0 and h.has("no player controller yet"), h.logs()[-4:])
h.ex("CONTROLLERS = { PC }"); h.pump(4)
check("the controller arrives (a client): client mode, still nothing spawned", h.ev("SPAWNS") == 0 and h.has("client mode: this player joined"))
h = Hub(portals(TEST), before="CONTROLLERS = {}")
h.pump(30)
check("still no controller after 10 tries: acts as host (spawns)", h.has("still no player controller; acting as host") and h.ev("find('hub_A3') ~= nil"),
      h.logs()[-4:])

print("=== clientMode = false: the old behaviour on a client, for comparison runs")
h = Hub(portals(TEST, TRAIN), top="CONFIG.clientMode = false", before='''
AUTH = false
host_pad("A-3", "cordonatest_start")
ARRIVAL = mkpad("cordonatest_start", "hub_A3", 1100000, 1300000, 0, true)
''')
check("logged as OFF", h.has("client mode: OFF"))
check("its own portals are spawned beside the host's (a second hub)", h.ev("SPAWNS") >= 2 and h.ev("DESTROY_CALLS") >= 1)
check("no teleporter watch", h.ev("n_notify(TELEPORTER)") == 0)
h.ex("C = player('C'); hx = mkpad('hub_X9', 'cordonatest_start', 0, 0, 0, true)")
h.ex("use(C, 'hub_X9')"); h.pump()
check("route_return runs as before", h.ev("dest_of('cordonatest_start')") == "hub_X9")

errs = [l for hb in HUBS for l in hb.logs() if "failed" in l or "error" in l]
check("no 'failed' or 'error' lines in any run's log", not errs, errs)
print("\n%d/%d passed" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
