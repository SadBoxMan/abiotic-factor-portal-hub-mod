# CRD-032: the lab's pad-use hook (AttemptTeleport) keeps the ids RegisterHook returns, and ModRef.OnUnload takes it off before Restart All
# Mods closes the lab's Lua state (UE4SS v3.0.1-1212 drops a Blueprint function's hooks only with the mod that hooked it first, usually the
# hub). Also: the object search at load waits for the game thread, and the Homeworld callback returns nothing (true would cancel it).
# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py).
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

# RegisterHook hands out ids as UE4SS does (a Blueprint function's pre and post id are the same); UnregisterHook records its arguments;
# GAME_THREAD counts game-thread callbacks so a search made outside one can be told apart.
EXTRA = r"""
NEXT_ID, IDS, UNHOOKED, ModRef, OFF_THREAD, LOADING, GAME_THREAD = 400, {}, {}, {}, {}, true, 0
local reg = RegisterHook
function RegisterHook(name, fn) reg(name, fn); NEXT_ID = NEXT_ID + 1; IDS[name] = NEXT_ID; return NEXT_ID, NEXT_ID end
function UnregisterHook(name, pre, post) UNHOOKED[#UNHOOKED + 1] = { name = name, pre = pre, post = post } end
function ExecuteInGameThread(fn) GAME_THREAD = GAME_THREAD + 1; fn(); GAME_THREAD = GAME_THREAD - 1 end
local first = FindFirstOf
function FindFirstOf(n, ...) if LOADING and GAME_THREAD == 0 then OFF_THREAD[#OFF_THREAD + 1] = tostring(n) end return first(n, ...) end
"""

TELEPORT_FN = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C:AttemptTeleport"
HOMEWORLD = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def lab(extra=""):
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute(EXTRA + extra)
    L.execute(open(LAB, encoding="utf-8").read())
    L.execute("LOADING = false")
    return L


def logs(L, since=0):
    g = L.globals()
    return [g.LOGS[i] for i in range(since + 1, len(g.LOGS) + 1)]


L = lab(); g = L.globals()
check("load: no object search outside the game thread", len(g.OFF_THREAD) == 0, [g.OFF_THREAD[i] for i in range(1, len(g.OFF_THREAD) + 1)])
check("load: the unload callback is set", L.eval("type(ModRef.OnUnload)") == "function")
check("the Homeworld callback returns nothing (true would cancel it)", L.eval("select('#', NOTIFY['%s']())" % HOMEWORLD) == 0)
L.execute("pump()")
hid = L.eval("IDS['%s']" % TELEPORT_FN)
check("the pad-use hook is registered once the portal room is there", hid is not None and any("pad use: logging every pad use" in l for l in logs(L)), logs(L)[-5:])
n = len(g.LOGS)
L.execute("ModRef.OnUnload()")
un = [(g.UNHOOKED[i].name, g.UNHOOKED[i].pre, g.UNHOOKED[i].post) for i in range(1, len(g.UNHOOKED) + 1)]
check("unload unregisters the pad-use hook with its own ids", un == [(TELEPORT_FN, hid, hid)], un)
check("unload is logged", any("unloading: pad-use hook %s unregistered" % hid in l for l in logs(L, n)), logs(L, n))
L.execute("ModRef.OnUnload()")
check("a second unload does nothing", len(g.UNHOOKED) == 1, len(g.UNHOOKED))

L2 = lab(); g2 = L2.globals()
n = len(g2.LOGS); L2.execute("ModRef.OnUnload()")
check("unload before the hook exists: nothing to unregister, no error", len(g2.UNHOOKED) == 0 and not any("could not" in l for l in logs(L2, n)), logs(L2, n))

L3 = lab("function UnregisterHook() error('no hook with that id') end"); g3 = L3.globals()
L3.execute("pump()")
n = len(g3.LOGS)
try:
    L3.execute("ModRef.OnUnload()"); escaped = False
except Exception:
    escaped = True
check("a throwing UnregisterHook is logged, not raised", not escaped and any("pad-use hook could not be unregistered" in l for l in logs(L3, n)), logs(L3, n))

L4 = lab("ModRef = nil"); g4 = L4.globals()
check("no ModRef (an older UE4SS): logged, the lab still loads", any("unload callback not available" in l for l in logs(L4))
      and any("player keys:" in l for l in logs(L4)), logs(L4)[-3:])

bad = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(bad)))
sys.exit(1 if bad else 0)
