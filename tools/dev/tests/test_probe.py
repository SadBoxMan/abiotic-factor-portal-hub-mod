# Runs the real mod/CordonaProbe/Scripts/main.lua (CRD-020) against a small mock of the game and checks: the save identity is logged at
# load, on the survey key ] and at portal-spawn time; DELETE spawns one Button_Generic on the host only, sets ButtonAlwaysPowered / ShouldSave /
# ButtonName, and hooks the button's functions once; a press on our button steps its name and messages the presser, while other
# buttons are ignored; the survey (], was F11) lists hub pads with their roles and flags duplicate IDs,
# lists every portal-room pad with its look and hum volume, and picks the local player controller on a host; DELETE again removes the probe button.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(S, "..", "..", "..", "mod", "CordonaProbe", "Scripts", "main.lua")

MOCK = r"""
LOGS, KEYS, HOOKS, NOTIFY, QUEUE, SPAWNED, LOADED, MSGS = {}, {}, {}, {}, {}, {}, {}, {}
print = function(s) LOGS[#LOGS + 1] = (tostring(s):gsub("\n$", "")) end
local NameMT = { __index = { ToString = function(self) return self.s end }, __eq = function(a, b) return a.s == b.s end }
function FName(s) return setmetatable({ s = s }, NameMT) end
function FText(s) return setmetatable({ s = s, text = true }, NameMT) end
Key = setmetatable({}, { __index = function(_, k) return k end })
function obj(t) t.IsValid = t.IsValid or function() return true end; return t end

AUTH = true
CLASS_LOADED = false
SAVE = "CordonaCorp"
GI = obj({ GetFullName = function() return "AbioticGameInstance_C /Engine/Transient.GameEngine_0:GI_0" end })
setmetatable(GI, { __index = function(_, k) if k == "ActiveWorldSaveName" then return FName(SAVE) end end })
LIB = obj({ GetSaveSubfolderName = function() return FName("76561190000000000") end })
PAWN = obj({
    GetFName = function() return FName("Abiotic_PlayerCharacter_C_0") end,
    K2_GetActorLocation = function() return { X = -12850, Y = 8250, Z = -300 } end,
    K2_GetActorRotation = function() return { Pitch = 0, Yaw = 90, Roll = 0 } end,
    HasAuthority = function() return AUTH end,
    GetLocalRole = function() return AUTH and 3 or 2 end,
    Client_DisplayWarningMessage = function(self, t) MSGS[#MSGS + 1] = t.s end,
})
PC = obj({ Pawn = PAWN })
local nextId = 0
function make_button(name, x)
    nextId = nextId + 1
    local id = nextId
    local b = obj({ ButtonName = FText(name or "Open"), Activated = false, ButtonDisabled = true, ButtonAlwaysPowered = false, ShouldSave = true,
        ToggleSwitch = false, OneTimeUse = false, ButtonCooldown = 1.0, alive = true,
        GetFullName = function() return "Button_Generic_C /Game/Maps/Facility.Facility:PersistentLevel.Button_Generic_C_" .. id end,
        K2_GetActorLocation = function() return { X = x or -12850, Y = 8400, Z = -300 } end,
        HasAuthority = function() return AUTH end, GetLocalRole = function() return AUTH and 3 or 1 end,
        GetRemoteRole = function() return AUTH and 1 or 3 end, GetIsReplicated = function() return true end })
    b.IsValid = function(self) return self.alive end
    b.K2_DestroyActor = function(self) self.alive = false end
    return b
end
OTHER = make_button("Elevator", -12800)
WORLD = obj({ SpawnActor = function(self, cls, loc, rot)
    local b = make_button(nil, loc.X); b.at = loc; b.rot = rot; SPAWNED[#SPAWNED + 1] = b; return b end })
PADS = {}
function pad(id, role) return obj({ MyTeleporterID = FName(id), K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end,
    HasAuthority = function() return role == 3 end, GetLocalRole = function() return role end }) end
CLASS = obj({})
function FindFirstOf(n) if n == "Abiotic_PlayerController_C" then return PC end return nil end
function FindAllOf(n)
    if n == "Button_Generic_C" then local t = { OTHER }; for _, b in ipairs(SPAWNED) do if b.alive then t[#t + 1] = b end end; return t end
    if n == "BP_Teleporter_ParentBP_C" then return PADS end
    return {}
end
function StaticFindObject(p)
    if p == "/Script/AbioticFactor.Default__AbioticFunctionLibrary" then return LIB end
    if p == "/Game/Blueprints/Environment/Switches/Button_Generic.Button_Generic_C" then return CLASS_LOADED and CLASS or nil end
    return nil
end
function LoadAsset(p) LOADED[#LOADED + 1] = p; CLASS_LOADED = true end
function RegisterHook(path, cb) if not GAME_THREAD then OFF_THREAD[#OFF_THREAD + 1] = path end; HOOKS[#HOOKS + 1] = { path = path, cb = cb } end
function NotifyOnNewObject(cls, cb) NOTIFY[#NOTIFY + 1] = { cls = cls, cb = cb } end
function RegisterKeyBind(k, cb) KEYS[k] = cb end
GAME_THREAD = false
OFF_THREAD = {}
function ExecuteInGameThread(fn) local was = GAME_THREAD; GAME_THREAD = true; fn(); GAME_THREAD = was end
function ExecuteWithDelay(ms, fn) QUEUE[#QUEUE + 1] = fn end
function pump() local q = QUEUE; QUEUE = {}; for _, fn in ipairs(q) do fn() end end
function press(k) if k == "SPAWN" then KEYS["DEL"]() else KEYS[k]() end end   -- SPAWN: DELETE with no probe button out
function param(v) return { get = function() return v end } end
function hook(name) for _, h in ipairs(HOOKS) do if h.path:sub(-#name - 1) == ":" .. name then return h.cb end end end
function count_hooks(name) local n = 0; for _, h in ipairs(HOOKS) do if h.path:sub(-#name - 1) == ":" .. name then n = n + 1 end end; return n end
package.preload["UEHelpers"] = function() return { GetWorld = function() return WORLD end, GetGameInstance = function() return GI end } end
"""

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def probe():
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute(open(PROBE, encoding="utf-8").read())
    return L


def logs(L, since=0):
    g = L.globals()
    return [g.LOGS[i] for i in range(since + 1, len(g.LOGS) + 1)]


def has(lines, text):
    return any(text in l for l in lines)


# --- load
L = probe(); g = L.globals()
lines = logs(L)
check("load: identity logged with the save name", has(lines, "identity (mod load): ActiveWorldSaveName='CordonaCorp'"), lines)
check("load: subfolder name logged", has(lines, "GetSaveSubfolderName='76561190000000000'"), lines)
check("load: keys ] (OEM_SIX) and DEL bound; F11 (the game's fullscreen) and INSERT (the lab) left alone", g.KEYS["OEM_SIX"] is not None and g.KEYS["DEL"] is not None and g.KEYS["F11"] is None and g.KEYS["INS"] is None)
check("load: no hooks while the button class is not loaded", len(g.HOOKS) == 0)
check("load: watches the Homeworld pad", len(g.NOTIFY) == 1 and "BP_Teleporter_HomeWorld_C" in g.NOTIFY[1].cls)

# --- a Restart All Mods: the button class is already loaded, so the hooks go in at load, and must be registered on the game thread
LR2 = lupa.LuaRuntime(unpack_returned_tuples=True); LR2.execute(MOCK); LR2.execute("CLASS_LOADED = true"); LR2.execute(open(PROBE, encoding="utf-8").read())
gr2 = LR2.globals()
check("reload: hooks registered at load when the class is loaded", len(gr2.HOOKS) == 4, len(gr2.HOOKS))
check("reload: no hook registered off the game thread", len(gr2.OFF_THREAD) == 0, list(gr2.OFF_THREAD.values()))

# --- portal-spawn time
n = len(g.LOGS)
g.NOTIFY[1].cb(None); g.NOTIFY[1].cb(None)          # two pads appear at once: one pair of lines only
L.execute("pump()")
lines = logs(L, n)
check("homeworld: identity logged at once", has(lines, "identity (a Homeworld pad appeared)"), lines)
check("homeworld: identity logged at portal-spawn time", has(lines, "identity (portal-spawn time, 4000 ms"), lines)
check("homeworld: a second pad in the same load adds no second pair", sum("a Homeworld pad appeared" in l for l in lines) == 1, lines)

# --- DELETE on a client
g.AUTH = False
n = len(g.LOGS)
L.execute("press('SPAWN')")
check("client spawn: nothing spawned", len(g.SPAWNED) == 0)
check("client spawn: says host only", has(logs(L, n), "client"), logs(L, n))
g.AUTH = True

# --- DELETE on the host
n = len(g.LOGS)
L.execute("press('SPAWN')")
lines = logs(L, n)
check("host spawn: the class was loaded by LoadAsset", list(g.LOADED.values()) == ["/Game/Blueprints/Environment/Switches/Button_Generic"], list(g.LOADED.values()))
check("host spawn: one button spawned", len(g.SPAWNED) == 1)
b = g.SPAWNED[1]
check("host spawn: spawned in front of the player (yaw 90 -> +Y)", abs(b.at.X - (-12850)) < 1 and abs(b.at.Y - (8250 + 150)) < 1, (b.at.X, b.at.Y))
check("host spawn: faces the player", abs(b.rot.Yaw - 270) < 0.01, b.rot.Yaw)
check("host spawn: ButtonAlwaysPowered = true", b.ButtonAlwaysPowered is True)
check("host spawn: ShouldSave = false", b.ShouldSave is False)
check("host spawn: ButtonDisabled = false", b.ButtonDisabled is False)
check("host spawn: ButtonName is an FText with the probe name", b.ButtonName.text and b.ButtonName.s == "Cordona console: press 0", b.ButtonName.s)
check("host spawn: four hooks registered", len(g.HOOKS) == 4, len(g.HOOKS))
check("host spawn: InteractWith_A hooked on Button_Generic_C", g.count_hooks("InteractWith_A") == 1)
check("host spawn: player told", any("spawned" in m for m in g.MSGS.values()))

# --- presses
n = len(g.LOGS)
L.execute("hook('InteractWith_A')(param(SPAWNED[1]), param(PAWN), param(nil))")
L.execute("hook('InteractWith_A')(param(SPAWNED[1]), param(PAWN), param(nil))")
lines = logs(L, n)
check("press: name stepped to press 2", b.ButtonName.s == "Cordona console: press 2", b.ButtonName.s)
check("press: logged with the presser", has(lines, "hook InteractWith_A fired on our button") and has(lines, "arg1=Abiotic_PlayerCharacter_C_0"), lines)
check("press: presser messaged", any("pressed (2)" in m for m in g.MSGS.values()))
n = len(g.LOGS)
L.execute("hook('InteractWith_A')(param(OTHER), param(PAWN), param(nil))")
check("press: another button is ignored", len(logs(L, n)) == 0 and g.OTHER.ButtonName.s == "Elevator", logs(L, n))
n = len(g.LOGS)
L.execute("hook('OnRep_Activated')(param(SPAWNED[1]))")
check("OnRep_Activated on our button is logged, name unchanged", has(logs(L, n), "hook OnRep_Activated fired") and b.ButtonName.s == "Cordona console: press 2", logs(L, n))

# --- DELETE again removes it; DELETE once more spawns a fresh one (hooks not doubled, counter reset)
L.execute("press('DEL')")
check("DELETE with a button out: removes it, spawns nothing", b.alive is False and len(g.SPAWNED) == 1)
L.execute("press('DEL')")
check("spawn again: a new button", len(g.SPAWNED) == 2 and g.SPAWNED[2].alive)
check("spawn again: hooks not registered twice", len(g.HOOKS) == 4, len(g.HOOKS))
check("spawn again: the name starts at press 0", g.SPAWNED[2].ButtonName.s == "Cordona console: press 0")

# --- a client sees a replicated probe button (not in its own list): the hook logs it but never writes
L2 = probe(); g2 = L2.globals()
g2.AUTH = False
L2.execute("CLASS_LOADED = true; REP = make_button('Cordona console: press 3', -12850); SPAWNED[1] = REP")
L2.execute("press('OEM_SIX')")
n = len(g2.LOGS)
L2.execute("hook('InteractWith_A_LocalFX')(param(REP), param(PAWN))")
L2.execute("hook('InteractWith_A')(param(REP), param(PAWN), param(nil))")
lines = logs(L2, n)
check("client: hooks installed by the survey once the class is loaded", len(g2.HOOKS) == 4, len(g2.HOOKS))
check("client: a replicated probe button's hooks are logged", has(lines, "a replicated probe button") and has(lines, "InteractWith_A_LocalFX"), lines)
check("client: a replicated probe button is never renamed", g2.REP.ButtonName.s == "Cordona console: press 3")

# --- survey (])
L.execute("PADS = { pad('hub_A-3', 3), pad('hub_A-3', 1), pad('hub_C-1', 1), pad('H_Cabin_Entrance', 3) }")
n = len(g.LOGS)
L.execute("press('OEM_SIX')")
lines = logs(L, n)
check("survey: identity in the survey", has(lines, "identity (survey key ]): ActiveWorldSaveName='CordonaCorp'"), lines)
check("survey: the probe button listed with its name and role", has(lines, "button 'Cordona console: press 0'") and has(lines, "role=Authority(3)"), lines)
check("survey: the nearby game button listed too", has(lines, "button 'Elevator'"), lines)
check("survey: three hub pads, the base pad skipped", has(lines, "3 hub pad(s)") and not has(lines, "H_Cabin_Entrance"), lines)
check("survey: duplicate hub IDs flagged", has(lines, "more than one with the same ID: hub_A-3 x2"), lines)
check("survey: a pad's role shown", has(lines, "hub pad hub_C-1") and has(lines, "role=SimulatedProxy(1)"), lines)

# --- survey (]) on a client whose pads arrived without our IDs: every pad in the portal room is listed, with its look and hum volume
L.execute("""
local function roompad(id, x, look, hum)
    local p = pad(id, 1)
    p.K2_GetActorLocation = function() return { X = x, Y = 8250, Z = -400 } end
    p.DestinationTeleporterID = FName('train_start'); p.IsTeleporterActive = true; p.bHidden = false
    p.ParticleLoop = obj({ Asset = look and obj({ GetFName = function() return FName(look) end }) or nil })
    p.PortalHumLoop = obj({ VolumeMultiplier = hum })
    return p
end
PADS = { roompad('None', -12000, 'NS_Portal_Purple', 0.575), roompad('H_Garden_Entrance', -12900, nil, 1.0), pad('far_away', 1) }
""")
n = len(g.LOGS)
L.execute("press('OEM_SIX')")
lines = logs(L, n)
check("survey: a room pad with no hub ID is listed with destination, look and hum",
      has(lines, "pad 'None' -> 'train_start'") and has(lines, "look=NS_Portal_Purple hum=0.575"), lines)
check("survey: a room pad with no particle asset says look=none", has(lines, "pad 'H_Garden_Entrance'") and has(lines, "look=none hum=1.000"), lines)
check("survey: a pad far from the portal room is not listed", not has(lines, "far_away"), lines)
check("survey: room pad count", has(lines, "2 pad(s) listed with look and hum"), lines)
check("survey: player controller count logged", has(lines, "1 player controller(s) on this machine"), lines)

# --- on a host the first controller found may be a client's: the survey and DELETE use the local one
L4 = probe(); g4 = L4.globals()
L4.execute("""
REMOTE_PAWN = obj({ GetFName = function() return FName('Client_Character') end, K2_GetActorLocation = function() return { X = 0, Y = 0, Z = 0 } end,
    K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end, HasAuthority = function() return true end })
REMOTE_PC = obj({ Pawn = REMOTE_PAWN, IsLocalController = function() return false end })
PC.IsLocalController = function() return true end
local ff = FindAllOf
FindAllOf = function(n) if n == 'Abiotic_PlayerController_C' then return { REMOTE_PC, PC } end return ff(n) end
""")
n = len(g4.LOGS)
L4.execute("press('OEM_SIX')")
lines = logs(L4, n)
check("host with two controllers: the survey reports the local player", has(lines, "player Abiotic_PlayerCharacter_C_0") and not has(lines, "player Client_Character"), lines)
check("host with two controllers: both counted", has(lines, "2 player controller(s) on this machine"), lines)
L4.execute("press('SPAWN')")
check("host with two controllers: the button spawns in front of the local player", len(g4.SPAWNED) == 1 and abs(g4.SPAWNED[1].at.Y - (8250 + 150)) < 1)

# --- empty save name and missing game instance do not break
L.execute("SAVE = ''")
n = len(g.LOGS); L.execute("press('OEM_SIX')")
check("empty save name logged as ''", has(logs(L, n), "ActiveWorldSaveName=''"), logs(L, n))
L3 = probe(); g3 = L3.globals()
L3.execute("package.loaded['UEHelpers'].GetGameInstance = function() return nil end; LIB = nil")
n = len(g3.LOGS); L3.execute("press('OEM_SIX')")
check("no game instance / library: logged, no error", has(logs(L3, n), "no game instance") and has(logs(L3, n), "library not found"), logs(L3, n))

# --- DELETE
n = len(g.LOGS)
L.execute("press('DEL')")
check("DELETE: removes the probe button", g.SPAWNED[2].alive is False and has(logs(L, n), "removed 1 probe button"), logs(L, n))
check("DELETE: the game's own button is untouched", g.OTHER.alive is True)

# --- CRD-032: the ids RegisterHook returns are kept, and ModRef.OnUnload takes every hook off before Restart All Mods closes the state
def probe_unload(extra):
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute("CLASS_LOADED = true; NEXT_ID, UNHOOKED, ModRef = 300, {}, {}\n"
              "local reg = RegisterHook\n"
              "function RegisterHook(path, cb) reg(path, cb); NEXT_ID = NEXT_ID + 1; HOOKS[#HOOKS].id = NEXT_ID; return NEXT_ID, NEXT_ID end\n"
              "function UnregisterHook(path, pre, post) UNHOOKED[#UNHOOKED + 1] = { path = path, pre = pre, post = post } end\n" + extra)
    L.execute(open(PROBE, encoding="utf-8").read())
    return L
L5 = probe_unload(""); g5 = L5.globals()
reg = sorted((g5.HOOKS[i].path, g5.HOOKS[i].id) for i in range(1, len(g5.HOOKS) + 1))
check("CRD-032: four hooks registered at load", len(reg) == 4, reg)
check("CRD-032: the unload callback is set", L5.eval("type(ModRef.OnUnload)") == "function")
n = len(g5.LOGS); L5.execute("ModRef.OnUnload()")
un = sorted((g5.UNHOOKED[i].path, g5.UNHOOKED[i].pre) for i in range(1, len(g5.UNHOOKED) + 1))
check("CRD-032: unload unregisters each hook with its own ids", un == reg and all(g5.UNHOOKED[i].pre == g5.UNHOOKED[i].post for i in range(1, len(g5.UNHOOKED) + 1)), (reg, un))
check("CRD-032: unload is logged", has(logs(L5, n), "unloading: 4 hook(s) unregistered"), logs(L5, n))
L5.execute("ModRef.OnUnload()")
check("CRD-032: a second unload does nothing", len(g5.UNHOOKED) == 4, len(g5.UNHOOKED))
check("CRD-032: the Homeworld callback returns nothing (true would cancel it)", L5.eval("select('#', NOTIFY[1].cb())") == 0)
L6 = probe_unload("function UnregisterHook() error('no hook with that id') end"); g6 = L6.globals()
n = len(g6.LOGS)
try:
    L6.execute("ModRef.OnUnload()"); escaped = False
except Exception:
    escaped = True
check("CRD-032: a throwing UnregisterHook is logged, not raised", not escaped and has(logs(L6, n), "hook could not be unregistered"), logs(L6, n))

bad = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(bad)))
sys.exit(1 if bad else 0)
