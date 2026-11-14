# Hub Exits for base-game worlds (CRD-012): the exit modes, chosen per hub portal (exits = ...) with a default (exitMode = ...), "game" if
# neither is set (LuciDin, 9 November):
#   game     the world's exits are the game's        hub      everyone leaves to the hub portal
#   dynamic  per player (hub entrants to the hub)    manual   the hub portal leads to a placed portal that always leads back; own exits stay
# The game's pads are never changed: a player who should leave to the hub is moved on after the game's own teleport. The mock game moves the
# player before the hooks run, as seen in game (probe 1, 8 November). Also: the arrival pad as an exit, exits found by distance (not an internal
# lift), END (pretend to be Player 2), number aliases, a bad mode, manualBuffs (the game's own buff call), custom worlds ignoring the modes,
# NUMPAD 1 / 2, and pads the hub must not touch.
#   python test_hub_exits.py [path to a main.lua, default the repo's]
import sys, os, math
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HUB, "main.lua")

GAME = r'''
local function obj(t) t.IsValid = function() return t.gone ~= true end; return t end
PADS = {}
function gpad(id, dest, x, y, z, buffs)
    local p = obj({ MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), IsTeleporterActive = true,
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end, OnRep_IsTeleporterActive = function() end })
    p.BuffsToApplyOnUse = { ForEach = function(self, fn) for i, r in ipairs(buffs or {}) do fn(i, { get = function() return { RowName = FName(r) } end }) end end }
    PADS[#PADS + 1] = p
    return p
end
-- the game's own pads (positions from the teleporter dump; exits inside worlds near their arrival pads where the dump has none)
gpad("train_start", "None", 333725.9, 12323.6, 934.2)
gpad("train_entrance", "train_start", 2873.3, 30359.6, 634.3)
gpad("train_end", "train_exit", 340408.9, -1348.7, 649.6, { "Buff_TrainReward" })
gpad("train_earlyexit", "train_earlyreturn", 336000, 9000, 900)
gpad("train_exit", "None", 5639.8, 34391.1, 1713.5)
gpad("train_earlyreturn", "None", 2931.3, 29728.1, 176.5)
gpad("anteverse_a_start", "anteverse_early_exit", 119175.3, 330450.7, 2332.4)      -- Far Garden: its arrival pad is also a way out
gpad("anteverse_a_entrance", "anteverse_a_start", -15542.9, 23575.5, 2360.4)
gpad("anteverse_early_exit", "None", -14756.0, 23579.4, 2406.4)
gpad("anteverse_a_exit", "anteverse_a_return", 119000, 330000, 2300)
gpad("anteverse_a_return", "None", -14651.4, 19826.5, 2996.4)
gpad("alps_start", "None", -273160.5, 71249.8, -7889.1)                              -- Voussoir: no exit list (found by distance)
gpad("alps_entrance", "alps_start", -52808.4, -9323.5, -849.4)
gpad("alps_return", "None", -51912.3, -8811.7, -237.8)
gpad("alps_exit", "alps_return", -268000, 75000, -7000)
gpad("alps_lift_a", "alps_lift_b", -270000, 72000, -7800)
gpad("alps_lift_b", "alps_lift_a", -270000, 72000, -2000)
gpad("botanical_present_01", "botanical_future_01", -38541.6, 69076.9, 1678.0)
gpad("botanical_future_01", "botanical_present_01", -38821.0, 68771.7, 51677.9)

local padClass = obj({ kind = "pad" })
local homePad = obj({})
local baseFind, baseAll = StaticFindObject, FindAllOf
function StaticFindObject(p)
    if p == "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C" then return padClass end
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
WORLD.SpawnActor = function(self, cls, loc, rot)
    local a = obj({ K2_GetActorLocation = function() return loc end, yaw = rot.Yaw, OnRep_IsTeleporterActive = function() end,
        ParticleLoop = { SetAsset = function(self, s) end, Activate = function() end } })
    a.K2_DestroyActor = function() a.gone = true end
    a.SetActorHiddenInGame = function(self, h) a.hidden = h end
    PADS[#PADS + 1] = a
    return a
end
HOOKS, KEYS, SHOWN = {}, {}, {}
function RegisterHook(name, fn) HOOKS[#HOOKS + 1] = { name = name, fn = fn } end
function RegisterKeyBind(key, a, b) KEYS[key] = b or a end
PAWN.Client_DisplayWarningMessage = function(self, text, colour, beep) SHOWN[#SHOWN + 1] = text.s end

function player(name)
    local c = { at = { X = 0, Y = 0, Z = 0 }, moves = 0, modes = {}, buffs = {} }
    c.PlayerState = obj({ GetFName = function() return FName("PlayerState_" .. name) end })
    c.K2_GetActorLocation = function() return { X = c.at.X, Y = c.at.Y, Z = c.at.Z } end
    c.GetFName = function() return FName("Char_" .. name) end
    c.K2_TeleportTo = function(self, loc, rot) c.at = { X = loc.X, Y = loc.Y, Z = loc.Z }; c.moves = c.moves + 1; c.yaw = rot.Yaw; return true end
    c.CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function(self, m) c.modes[#c.modes + 1] = m end }
    c.BuffComponent = obj({ Server_ApplyBuff = function(self, row, override, dur, limb, linked, skip)
        assert(row.RowName and override == false and limb == 0 and skip == false, "bad Server_ApplyBuff args")
        c.buffs[#c.buffs + 1] = row.RowName:ToString(); return true end })
    return obj(c)
end
function find(id) for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID:ToString() == id then return p end end end
local function put_at(char, id)
    local t = find(id)
    if t then local l = t:K2_GetActorLocation(); char.at = { X = l.X + 200, Y = l.Y, Z = l.Z } end
end
-- the game: the player stands on the pad, is moved 2 m in front of the destination pad, then the hooks run (how = "never": no teleport)
function use(char, id, times, how)
    T = T + 2
    local p = find(id)
    local dest = p.DestinationTeleporterID:ToString()
    local l = p:K2_GetActorLocation(); char.at = { X = l.X, Y = l.Y, Z = l.Z }
    if how == nil then put_at(char, dest) end
    for _ = 1, (times or 1) do
        for _, h in ipairs(HOOKS) do h.fn({ get = function() return p end }, { get = function() return char end }, {}) end
    end
    return dest
end
function dest_of(id) return find(id).DestinationTeleporterID:ToString() end
function dist(char, x, y, z) local dx, dy, dz = char.at.X - x, char.at.Y - y, char.at.Z - z; return math.sqrt(dx * dx + dy * dy + dz * dz) end
function near_pad(char, id) local l = find(id):K2_GetActorLocation(); return dist(char, l.X, l.Y, l.Z) < 500 end
'''

res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))

# where the hub puts a player: in front of a slot's pad (slots.lua: anchor, cyaw, +91.5 yaw, 4.4 lift; exit 215.1 ahead, 127.5 up)
ANCHORS = {"A-4": (-12610.1, 7745.9, 255.4, 0.1), "B-1": (-12719.0, 8788.2, -394.6, -170.3), "B-2": (-13091.7, 8467.8, -394.6, -108.0)}
def front(slot):
    x, y, z, cy = ANCHORS[slot]
    yaw = cy + 91.5
    return (x + math.cos(math.radians(yaw)) * 215.1, y + math.sin(math.radians(yaw)) * 215.1, z + 4.4 + 127.5)

HUBS = []
class Hub:
    def __init__(self, portals, top="", worlds="{}"):
        HUBS.append(self)
        self.L = L = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.g = L.globals()
        L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
        L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
        if worlds != "keep":
            L.execute("CONFIG.worlds = %s" % worlds)
        L.execute("CONFIG.portals = %s" % portals)
        L.execute('package.preload["manual_exits"] = function() return {} end')   # not the shipped file (it holds recorded MHEs)
        if top:
            L.execute(top)
        L.execute(GAME)
        L.execute(open(MAIN, encoding="utf-8").read())
        self.pump()
    def ev(self, x): return self.L.eval(x)
    def ex(self, x): self.L.execute(x)
    def pump(self, n=6):
        for _ in range(n): self.L.execute("pump()")
    def use(self, who, pad, times=1, how=None):
        d = self.L.eval("use(%s, %r, %d, %s)" % (who, pad, times, "nil" if how is None else repr(how)))
        self.pump()
        return d
    def logs(self, since=0): return [self.g.LOGS[i] for i in range(since + 1, len(self.g.LOGS) + 1)]
    def n(self): return len(self.g.LOGS)
    def at_front(self, who, slot):
        f = front(slot)
        return self.ev("dist(%s, %f, %f, %f)" % (who, f[0], f[1], f[2])) < 1
    def moves(self, who): return self.ev("%s.moves" % who)

TRAIN = '{ slot = "A-4", name = "The Train", destination = "train_start"%s }'
FAR = '{ slot = "B-1", name = "Far Garden", destination = "anteverse_a_start"%s }'
ALPS = '{ slot = "B-2", name = "Voussoir", destination = "alps_start"%s }'
def portals(*items): return "{ " + ", ".join(items) + " }"

print("=== default: no exitMode, no exits -> game")
h = Hub(portals(TRAIN % "", FAR % ""))
check("A-4 says exits: game", any("A-4: exits: game" in l for l in h.logs()), h.logs()[-6:])
h.ex("A, B = player('A'), player('B')")
h.use("B", "hub_A4")
check("the Train's arrival pad is not rewritten (route_return is for custom worlds only)", h.ev("dest_of('train_start')") == "None")
h.use("B", "train_end")
check("hub entrant B: train_end leaves B at train_exit, no move", h.ev("near_pad(B, 'train_exit')") and h.moves("B") == 0)
h.use("B", "hub_B1")
check("Far Garden's arrival pad is not rewritten either", h.ev("dest_of('anteverse_a_start')") == "anteverse_early_exit")
h.use("B", "anteverse_a_start")
check("hub entrant B: Far Garden's arrival pad leaves B at anteverse_early_exit, no move", h.ev("near_pad(B, 'anteverse_early_exit')") and h.moves("B") == 0)
check("END is bound (dev key)", h.ev("KEYS.END ~= nil"))
check("the hook is registered once, on AttemptTeleport", len(list(h.g.HOOKS.values())) == 1 and h.g.HOOKS[1].name.endswith(":AttemptTeleport"))

print("=== dynamic: per player")
h = Hub(portals(TRAIN % ', exits = "dynamic"', FAR % ', exits = "dynamic"', ALPS % ', exits = "dynamic"'))
h.ex("A, B = player('A'), player('B')")
h.use("B", "hub_A4", 3)
h.use("A", "train_entrance")
n = h.n()
h.use("A", "train_end", 3)
check("A (game's way): train_end -> train_exit, no move", h.ev("near_pad(A, 'train_exit')") and h.moves("A") == 0)
h.use("B", "train_end", 2)
check("B (hub): moved on to the front of hub_A4, once", h.at_front("B", "A-4") and h.moves("B") == 1)
check("B held still, then let fall (MOVE_None, then MOVE_Falling)", list(h.ev("B.modes").values())[-2:] == [0, 3])
h.use("A", "train_earlyexit")
h.use("B", "train_earlyexit")
check("interleaved: A to train_earlyreturn, B to hub_A4", h.ev("near_pad(A, 'train_earlyreturn')") and h.at_front("B", "A-4") and h.moves("B") == 2)
new = h.logs(n)
check("one log line per pad use though the overlap fired several times", len([l for l in new if " used train_" in l]) == 4, new)
check("checks after the move say: at the hub portal", [l for l in new if "check after" in l] and all("(at the hub portal)" in l for l in new if "check after" in l))
check("the game's pads are never changed", h.ev("dest_of('train_end')") == "train_exit" and h.ev("dest_of('train_start')") == "None")
# the arrival pad as an exit
h.use("B", "hub_B1"); h.use("A", "anteverse_a_entrance")
h.ex("A.moves, B.moves = 0, 0")
h.use("B", "anteverse_a_start")
check("B (hub): Far Garden's arrival pad, then the front of hub_B1", h.at_front("B", "B-1") and h.moves("B") == 1)
h.use("A", "anteverse_a_start")
check("A (game's way): Far Garden's arrival pad leaves A at anteverse_early_exit", h.ev("near_pad(A, 'anteverse_early_exit')") and h.moves("A") == 0)
check("Far Garden's arrival pad still leads where the game made it", h.ev("dest_of('anteverse_a_start')") == "anteverse_early_exit")
h.use("B", "hub_B1")
h.use("B", "anteverse_a_exit")
check("B (hub): anteverse_a_exit (on the list), then the front of hub_B1", h.at_front("B", "B-1") and h.moves("B") == 2)
# found by distance
h.use("B", "hub_B2")
h.ex("B.moves = 0")
n = h.n()
h.use("B", "alps_lift_a")
check("an internal lift (58 m) is not an exit: no move", h.moves("B") == 0 and h.ev("near_pad(B, 'alps_lift_b')"))
h.use("B", "alps_exit")
check("alps_exit (found by distance) moves B on to the front of hub_B2", h.at_front("B", "B-2") and h.moves("B") == 1)
check("the log names it as found by distance", any("alps_exit, an exit of alps_start (distance)" in l for l in h.logs(n)), h.logs(n))
# the game never moves the player
h.use("B", "hub_A4"); h.ex("B.moves = 0")
n = h.n()
h.use("B", "train_end", 1, "never")
check("no teleport by the game: no move, and the log says so", h.moves("B") == 0 and any("had not moved the player after 1.5 s" in l for l in h.logs(n)))
# END
h.ex("ME = player('Me')")
h.use("ME", "hub_A4")
h.ex("KEYS.END()")
h.ex("ME.moves = 0")
h.use("ME", "train_end")
check("END: as Player 2 (never came in through the hub) train_end leaves you at train_exit", h.ev("near_pad(ME, 'train_exit')") and h.moves("ME") == 0)
h.ex("KEYS.END()")
h.use("ME", "train_end")
check("END again: as yourself, the front of hub_A4", h.at_front("ME", "A-4") and h.moves("ME") == 1)
# NUMPAD 1 keeps the trips
h.use("A", "hub_A4")
h.ex("KEYS.NUM_ONE()"); h.pump()
h.ex("A.moves = 0")
h.use("A", "train_end")
check("after NUMPAD 1 A's exit still moves A to hub_A4", h.at_front("A", "A-4") and h.moves("A") == 1)

print("=== hub: everyone")
h = Hub(portals(TRAIN % ', exits = "hub"'))
h.ex("A, B, C = player('A'), player('B'), player('C')")
h.use("A", "train_entrance"); h.use("B", "hub_A4")
h.use("A", "train_end"); h.use("B", "train_earlyexit"); h.use("C", "train_end")
check("A (game's way), B (hub) and C (never seen coming in) all end at the front of hub_A4",
      h.at_front("A", "A-4") and h.at_front("B", "A-4") and h.at_front("C", "A-4"))
check("the game's pads are never changed", h.ev("dest_of('train_end')") == "train_exit")

print("=== default exitMode, per-portal override, numbers, a bad mode")
h = Hub(portals(TRAIN % "", FAR % ', exits = "game"', ALPS % ", exits = 3"), top='CONFIG.exitMode = "hub"')
check("exitMode = \"hub\" covers A-4", any("A-4: exits: hub" in l for l in h.logs()), h.logs()[-12:])
check("B-1 overrides it with game", any("B-1: exits: game" in l for l in h.logs()))
check("exits = 3 is dynamic", any("B-2: exits: dynamic" in l for l in h.logs()))
h.ex("A = player('A')")
h.use("A", "hub_B1"); h.use("A", "anteverse_a_exit")
check("game on B-1: A stays at anteverse_a_return", h.ev("near_pad(A, 'anteverse_a_return')") and h.moves("A") == 0)
h.use("A", "train_end")
check("hub on A-4 (from exitMode): A to the front of hub_A4", h.at_front("A", "A-4"))
h = Hub(portals(TRAIN % ', exits = "sometimes"'), top="CONFIG.exitMode = 7")
check("a bad exits value is logged, and the default used", any("unknown exits 'sometimes'" in l for l in h.logs()) and any("A-4: exits: game" in l for l in h.logs()), h.logs()[-8:])
check("a bad exitMode is logged", any("unknown exitMode '7'" in l for l in h.logs()))

print("=== manual: the hub portal leads to a placed portal, which always leads back")
h = Hub(portals(TRAIN % ', exits = "manual"'), top='MHE_T = { train_start = { 336500, 8000, 880, 45 } }; package.preload["manual_exits"] = function() return MHE_T end')
check("A-4 says exits: manual", any("A-4: exits: manual" in l for l in h.logs()))
check("hub_A4 leads to its manual portal", h.ev("dest_of('hub_A4')") == "hub_A4_manual")
check("the manual portal stands at its spot, facing its yaw, leading back to hub_A4",
      h.ev("find('hub_A4_manual') ~= nil") and h.ev("find('hub_A4_manual'):K2_GetActorLocation().X") == 336500
      and h.ev("find('hub_A4_manual').yaw") == 45 and h.ev("dest_of('hub_A4_manual')") == "hub_A4")
h.ex("A, B = player('A'), player('B')")
h.use("B", "hub_A4")
check("B arrives in front of the manual portal", h.ev("near_pad(B, 'hub_A4_manual')"))
h.ex("B.moves = 0")
h.use("B", "train_end")
check("the world's own exits stay the game's: B at train_exit, no move", h.ev("near_pad(B, 'train_exit')") and h.moves("B") == 0)
h.use("B", "hub_A4")
n = h.n()
h.use("B", "hub_A4_manual")
check("the manual portal takes B back to hub_A4 (the game's teleport; no buffs by default)", h.ev("near_pad(B, 'hub_A4')") and h.ev("#B.buffs") == 0)
check("... logged", any("used the manual portal of train_start, back to hub_A4" in l for l in h.logs(n)), h.logs(n))
h.use("A", "train_entrance"); h.use("A", "hub_A4_manual")
check("a player who came the game's way also goes back to the hub by it", h.ev("near_pad(A, 'hub_A4')"))
check("the manual portal still leads to hub_A4 after both", h.ev("dest_of('hub_A4_manual')") == "hub_A4")
h.ex("KEYS.NUM_TWO()")
check("NUMPAD 2 removes the manual portal with the hub portals", h.ev("find('hub_A4_manual') == nil and find('hub_A4') == nil"))
h.ex("KEYS.NUM_ONE()"); h.pump()
check("NUMPAD 1 brings both back", h.ev("find('hub_A4_manual') ~= nil and dest_of('hub_A4') == 'hub_A4_manual'"))
h = Hub(portals(TRAIN % ', exits = "manual"'))
check("manual with no MHE for its world: logged, and the portal falls back to game",
      any("train_start has no manual portal yet (manual_exits.lua)" in l for l in h.logs()) and any("A-4: exits: game" in l for l in h.logs())
      and h.ev("dest_of('hub_A4')") == "train_start", h.logs()[-8:])
DEFAULTS = 'package.preload["manual_exits"] = function() return { train_start = { 337000, 7000, 870, 90 } } end'
h = Hub(portals(TRAIN % ', exits = 4'), top=DEFAULTS)
check("manual (exits = 4) uses the world's MHE from manual_exits.lua",
      h.ev("dest_of('hub_A4')") == "hub_A4_manual" and h.ev("find('hub_A4_manual'):K2_GetActorLocation().X") == 337000 and h.ev("find('hub_A4_manual').yaw") == 90)
h = Hub(portals(TRAIN % ', exits = "manual", manual = { 336500, 8000, 880, 45 }'), top=DEFAULTS)
check("a portal's own manual spot is ignored (the hub portals are final): the world's MHE is used, with a log line",
      h.ev("find('hub_A4_manual'):K2_GetActorLocation().X") == 337000 and any("manual is ignored" in l for l in h.logs()), h.logs()[-8:])
h = Hub(portals(TRAIN % ""), top=DEFAULTS + '; CONFIG.exitMode = "manual"')
check("exitMode = \"manual\" is refused (the global choice is modes 1-3): logged, game used",
      any("exitMode is for modes 1-3" in l for l in h.logs()) and any("A-4: exits: game" in l for l in h.logs()) and h.ev("dest_of('hub_A4')") == "train_start")

h = Hub(portals(FAR % ', exits = "manual"'), top='MHE_T = {}; package.preload["manual_exits"] = function() return MHE_T end')
check("no MHE yet: B-1 works as game", h.ev("dest_of('hub_B1')") == "anteverse_a_start")
h.ex("MHE_T = { anteverse_a_start = { 128612, 334772, 1927, 180 } }; KEYS.NUM_ONE()"); h.pump()
check("an MHE recorded since: NUMPAD 1 reads manual_exits.lua again and B-1 leads to its manual portal at the MHE",
      h.ev("dest_of('hub_B1')") == "hub_B1_manual" and h.ev("find('hub_B1_manual'):K2_GetActorLocation().X") == 128612
      and h.ev("dest_of('hub_B1_manual')") == "hub_B1", h.logs()[-8:])
check("... and the log says the file changed", any("manual_exits.lua changed (1 MHE(s))" in l for l in h.logs()))
n = h.n(); h.ex("KEYS.NUM_ONE()"); h.pump()
check("an unchanged file is not read as a change", not any("manual_exits.lua changed" in l for l in h.logs(n)))

print("=== MHEs on their own (opt-out per world) and the Failsafe Exit")
MHES = 'MHE_T = { anteverse_a_start = { 128612, 334772, 1927, 180 }, alps_start = { -272000, 72000, -7800, 90 } }; package.preload["manual_exits"] = function() return MHE_T end'
h = Hub(portals(FAR % ""), top=MHES)
check("Far Garden's MHE is spawned (on by default) and leads to its hub portal hub_B1",
      h.ev("find('hub_mhe_anteverse_a_start') ~= nil and dest_of('hub_mhe_anteverse_a_start') == 'hub_B1'"))
check("... at its spot, facing its yaw, active", h.ev("find('hub_mhe_anteverse_a_start'):K2_GetActorLocation().X") == 128612
      and h.ev("find('hub_mhe_anteverse_a_start').yaw") == 180 and h.ev("find('hub_mhe_anteverse_a_start').IsTeleporterActive") is True)
check("Voussoir has an MHE but no hub portal: its MHE leads to the Failsafe Exit", h.ev("dest_of('hub_mhe_alps_start')") == "hub_failsafe")
f = front("B-1")
fx, fy = f[0], f[1]
check("the Failsafe Exit (not recorded yet) is hidden, off, and placed so an arrival stands in front of the first hub portal",
      h.ev("find('hub_failsafe').hidden") is True and h.ev("find('hub_failsafe').IsTeleporterActive") is False
      and abs(h.ev("find('hub_failsafe'):K2_GetActorLocation().X + math.cos(math.rad(find('hub_failsafe').yaw)) * 215.1") - fx) < 1
      and abs(h.ev("find('hub_failsafe'):K2_GetActorLocation().Y + math.sin(math.rad(find('hub_failsafe').yaw)) * 215.1") - fy) < 1, h.logs()[-6:])
check("... and the log says it is not recorded yet", any("Failsafe Exit (not recorded yet" in l for l in h.logs()))
h.ex("B = player('B')"); n = h.n()
h.use("B", "hub_mhe_alps_start")
check("using Voussoir's MHE: the game takes B to the Failsafe Exit; logged", h.ev("near_pad(B, 'hub_failsafe')") and any("used the MHE of alps_start, to hub_failsafe" in l for l in h.logs(n)))
check("the MHEs and the failsafe are never rewritten", h.ev("dest_of('hub_mhe_alps_start')") == "hub_failsafe" and h.ev("dest_of('hub_mhe_anteverse_a_start')") == "hub_B1")
h.ex("KEYS.NUM_TWO()")
check("NUMPAD 2 removes the MHEs and the Failsafe Exit", h.ev("find('hub_mhe_alps_start') == nil and find('hub_failsafe') == nil and find('hub_mhe_anteverse_a_start') == nil"))
h = Hub(portals(FAR % ""), top=MHES + "; MHE_T.failsafe = { -12850, 8270, -1040, 90 }")
check("a recorded Failsafe Exit: the arrival point is the recorded spot",
      abs(h.ev("find('hub_failsafe'):K2_GetActorLocation().X + math.cos(math.rad(90)) * 215.1") - (-12850)) < 1
      and abs(h.ev("find('hub_failsafe'):K2_GetActorLocation().Y + 215.1") - 8270) < 1)
check("... with its hidden pad 0.1 m (10 units) above the recorded floor, so an arrival never ends up in the floor", h.ev("find('hub_failsafe'):K2_GetActorLocation().Z") == -1030)
check("the failsafe line in manual_exits.lua is not an MHE", h.ev("find('hub_mhe_failsafe') == nil"))
h = Hub(portals(FAR % ""), top=MHES + "; CONFIG.mhe = { alps_start = false }")
check("mhe = { alps_start = false }: no MHE for Voussoir, so no Failsafe Exit either, and a log line",
      h.ev("find('hub_mhe_alps_start') == nil and find('hub_failsafe') == nil") and any("alps_start is switched off in config.lua" in l for l in h.logs()))
check("... Far Garden's MHE is still there", h.ev("find('hub_mhe_anteverse_a_start') ~= nil"))
h = Hub(portals(FAR % ', exits = "manual"'), top=MHES)
check("a world whose hub portal uses mode 4 gets no extra MHE (its manual portal is the MHE)",
      h.ev("find('hub_mhe_anteverse_a_start') == nil and find('hub_B1_manual') ~= nil"))
h = Hub(portals(FAR % ""), top='MHE_T = { H_Cabin_Start = { 129000, 112000, -2850, 10 } }; package.preload["manual_exits"] = function() return MHE_T end')
check("the Cabin's MHE (a game home, no Portal Hub portal) leads to its own hub-room portal, not the Failsafe Exit",
      h.ev("dest_of('hub_mhe_H_Cabin_Start')") == "H_Cabin_Entrance" and h.ev("find('hub_failsafe') == nil"))
h = Hub(portals(TRAIN % ""), top='MHE_T = { cordonatest_start = { 1, 2, 3, 0 } }; package.preload["manual_exits"] = function() return MHE_T end', worlds="keep")
check("a custom world never gets an MHE", h.ev("find('hub_mhe_cordonatest_start') == nil"))

print("=== NUMPAD 1 reads the file itself, not require (UE4SS keeps a required module, 9 November)")
import tempfile
tmp = os.path.join(tempfile.mkdtemp(), "manual_exits.lua")
def write_mhe(x):
    text = 'return {\n    ["anteverse_a_start"] = { %d, 334595, 1933, 6 },\n}\n' % x
    open(tmp, "w", encoding="utf-8", newline="\n").write(text)
write_mhe(127329)
h = Hub(portals(FAR % ', exits = "manual"'),
        top='PORTALHUB_MHE_PATH = [[%s]]; package.preload["manual_exits"] = function() return { anteverse_a_start = { 1, 1, 1, 0 } } end' % tmp)
check("the hub reads the MHE from the file (require would give a stale spot)", h.ev("find('hub_B1_manual'):K2_GetActorLocation().X") == 127329)
write_mhe(128359)
h.ex("KEYS.NUM_ONE()"); h.pump()
check("after a new MHE is written, NUMPAD 1 puts the manual portal at the new spot", h.ev("find('hub_B1_manual'):K2_GetActorLocation().X") == 128359, h.logs()[-8:])
check("... once (one manual portal)", h.ev("(function() local n = 0; for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID:ToString() == 'hub_B1_manual' then n = n + 1 end end; return n end)()") == 1)

print("=== manualBuffs: the true exit's buffs, by the game's own call")
h = Hub(portals(TRAIN % ', exits = "manual", manualBuffs = true'), top='MHE_T = { train_start = { 336500, 8000, 880, 45 } }; package.preload["manual_exits"] = function() return MHE_T end')
h.ex("B = player('B')")
h.use("B", "hub_A4")
n = h.n()
h.use("B", "hub_A4_manual", 2)
check("B gets train_end's buff once (read from the loaded true exit)", list(h.ev("B.buffs").values()) == ["Buff_TrainReward"], list(h.ev("B.buffs").values()))
check("... logged", any("true-exit buff Buff_TrainReward given" in l for l in h.logs(n)), h.logs(n))
h = Hub(portals(FAR % ', exits = "manual", manualBuffs = true'), top='MHE_T = { anteverse_a_start = { 119300, 330300, 2300, 0 } }; package.preload["manual_exits"] = function() return MHE_T end')
h.ex("B = player('B')")
h.use("B", "hub_B1"); n = h.n(); h.use("B", "hub_B1_manual")
check("Far Garden: its true exit's buff (Buff_Hygroscopic, from the hub's own list; the exit pad gives none here) is given",
      list(h.ev("B.buffs").values()) == ["Buff_Hygroscopic"], h.logs(n))
h = Hub(portals(ALPS % ', exits = "manual", manualBuffs = true'), top='MHE_T = { alps_start = { -272000, 72000, -7800, 0 } }; package.preload["manual_exits"] = function() return MHE_T end')
h.ex("B = player('B')")
h.use("B", "hub_B2"); n = h.n(); h.use("B", "hub_B2_manual")
check("no buffs known (Voussoir): none given, and the log says so", h.ev("#B.buffs") == 0 and any("no true-exit buffs known for alps_start" in l for l in h.logs(n)), h.logs(n))

print("=== custom worlds have no mode")
h = Hub('{ { slot = "A-3", name = "Test World", destination = "cordonatest_start", exits = "hub" } }', worlds="keep")
check("exits on a custom world is ignored, with a log line", any("is a custom world, which always returns to the hub; exits ignored" in l for l in h.logs()), h.logs()[-10:])

print("=== pads the hub must not touch")
h = Hub(portals(TRAIN % ', exits = "dynamic"', FAR % ', exits = "hub"'))
h.ex("B = player('B')")
h.use("B", "hub_A4"); h.use("B", "botanical_present_01"); h.use("B", "botanical_future_01")
check("using the Botanical pair moves no one", h.moves("B") == 0)
for pid, d in (("botanical_present_01", "botanical_future_01"), ("botanical_future_01", "botanical_present_01"), ("train_entrance", "train_start"),
               ("train_end", "train_exit"), ("anteverse_a_start", "anteverse_early_exit"), ("train_exit", "None")):
    check("%s still leads to %s" % (pid, d), h.ev("dest_of(%r)" % pid) == d)

print("=== the Cabin in dynamic mode: Torii's pad (~630 m away) and the hub room (~1.7 km) are not its exits")
CABIN = '{ slot = "B-1", name = "Cabin", destination = "H_Cabin_Start", exits = "dynamic" }'
h = Hub(portals(CABIN))
h.ex("""
gpad("H_Cabin_Start", "H_Cabin_Entrance", 125804.6, 109383.0, -2857.2)
gpad("H_Cabin_Entrance", "H_Cabin_Start", -13024.8, 7990.4, -416.8)
gpad("H_Japan_Start", "H_Japan_Entrance", 135877.3, 125090.2, 57019.9)
gpad("H_Japan_Entrance", "H_Japan_Start", -13115.2, 8391.4, 259.8)
gpad("hubroom_pad", "train_start", -12000, 8000, 300)
gpad("cabin_far_pad", "train_exit", 125804.6 + 120000, 109383.0, -2857.2)
B = player('B')
""")
h.use("B", "hub_B1")
h.ex("B.moves = 0")
h.use("B", "H_Japan_Start")
check("Torii's own pad (630 m from the Cabin's arrival pad) is not a Cabin exit: no move", h.moves("B") == 0)
h.use("B", "hubroom_pad")
check("a pad in the hub room (1.7 km away) is not a Cabin exit: no move", h.moves("B") == 0)
h.use("B", "cabin_far_pad")
check("a pad 1.2 km from the Cabin's arrival pad is not found by distance (limit 1 km): no move", h.moves("B") == 0)
h.use("B", "H_Cabin_Start")
check("the Cabin's own way out (its arrival pad) moves B on to the front of hub_B1", h.at_front("B", "B-1") and h.moves("B") == 1)

errs = [l for hb in HUBS for l in hb.logs() if "failed" in l]
check("no 'failed' lines in any run's log", not errs, errs)
print("\n%d/%d passed" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
