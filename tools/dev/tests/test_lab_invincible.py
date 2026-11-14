# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py) and checks the
# CRD-031 infinite health key (F7): it sets the player's Invincible flag and clears it again, sets it again on a new character while on,
# stops its 2 s check chain when switched off, copes with no character or a flag that can't be written, and is bound to F7 only.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

PAWN = r"""
SAID = {}
function new_pawn(locked)
    local p = { Invincible = false }
    return setmetatable({}, {
        __index = function(_, k)
            if k == "IsValid" then return function() return true end end
            if k == "GetFName" then return function() return FName("Player_C_0") end end
            if k == "GetTotalHealth" then return function() return 600 end end
            if k == "Client_DisplayWarningMessage" then return function(self, t) SAID[#SAID + 1] = t:ToString() end end
            return p[k]
        end,
        __newindex = function(_, k, v) if locked then error("cannot write " .. k) end p[k] = v end,
    })
end
IPAWN = new_pawn()
PC_OK = true
PC_FINDS = 0
IPC = { IsValid = function() return PC_OK end }
setmetatable(IPC, { __index = function(_, k) if k == "Pawn" then return IPAWN end end })
local find = FindFirstOf
function FindFirstOf(name) if name == "Abiotic_PlayerController_C" then PC_FINDS = PC_FINDS + 1; return IPC end return find(name) end
function run_delayed()
    local list = DELAYED
    DELAYED = {}
    for _, fn in ipairs(list) do fn() end
    return #list
end
"""

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def lab():
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute(open(LAB, encoding="utf-8").read())
    L.execute(PAWN)
    L.execute("DELAYED = {}")
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


ev = lambda L, e: L.eval(e)

print("=== F7 is bound, and only once")
src = open(LAB, encoding="utf-8").read()
check("F7 bound to the infinite health toggle", re.search(r"RegisterKeyBind\(Key\.F7, function\(\) ExecuteInGameThread\(toggle_invincible\)", src))
check("F7 bound once in the lab", len(re.findall(r"Key\.F7\b", src)) == 1)
others = "".join(open(os.path.join(S, "..", "..", "..", "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger"))
check("no other mod of ours binds F7", "Key.F7" not in others)
check("no hook and no async loop for it", "LoopAsync" not in src and "RegisterHook(\"/Script/AbioticFactor.Abiotic_PlayerCharacter" not in src)

print("=== F7 on")
L = lab()
L.execute("KEYS['F7']()")
check("Invincible set", ev(L, "IPAWN.Invincible") is True)
check("logged ON", has(L, "infinite health ON (Invincible = true, health 600)"), logs(L)[-2:])
check("said on screen", ev(L, "SAID[#SAID]") == "Infinite health ON")
check("a 2 s check queued", ev(L, "#DELAYED") == 1)

print("=== while on: a new character gets it too")
L.execute("IPAWN = new_pawn()")
L.execute("run_delayed()")
check("set again on the new character", ev(L, "IPAWN.Invincible") is True)
check("logged the re-set", has(L, "infinite health: set again on the current character (true)"))
check("the check keeps going", ev(L, "#DELAYED") == 1)
n = len(logs(L))
L.execute("run_delayed()")
check("no log line when nothing changed", len(logs(L)) == n)

print("=== the controller is found once and kept (no object walk every 2 s, CRD-032)")
L.execute("PC_FINDS = 0")
L.execute("run_delayed(); run_delayed(); run_delayed()")
check("no controller search while it stays valid", ev(L, "PC_FINDS") == 0, ev(L, "PC_FINDS"))
L.execute("PC_OK = false")
L.execute("run_delayed()")
check("searched again when it went invalid", ev(L, "PC_FINDS") >= 1, ev(L, "PC_FINDS"))
L.execute("PC_OK = true; PC_FINDS = 0")
L.execute("run_delayed(); run_delayed(); run_delayed()")
check("found once when back, then kept", ev(L, "PC_FINDS") == 1, ev(L, "PC_FINDS"))

print("=== F7 off")
L.execute("KEYS['F7']()")
check("Invincible cleared", ev(L, "IPAWN.Invincible") is False)
check("logged OFF", has(L, "infinite health OFF (Invincible = false"))
L.execute("run_delayed()")
check("the old check chain stops", ev(L, "#DELAYED") == 0 and ev(L, "IPAWN.Invincible") is False)

print("=== on, off, on quickly: only one chain runs")
L.execute("KEYS['F7']()")
L.execute("KEYS['F7']()")
L.execute("KEYS['F7']()")
L.execute("run_delayed()")
check("one chain left after the stale ones end", ev(L, "#DELAYED") == 1)
check("still on", ev(L, "IPAWN.Invincible") is True)

print("=== no character, or a flag that can't be written")
L = lab()
L.execute("IPAWN = nil")
L.execute("KEYS['F7']()")
check("no character: logged, nothing queued", has(L, "infinite health: no player character") and ev(L, "#DELAYED") == 0)
L = lab()
L.execute("IPAWN = new_pawn(true)")
L.execute("KEYS['F7']()")
check("unwritable flag: logged, stays off", has(L, "infinite health: could not set Invincible") and ev(L, "#DELAYED") == 0)
L.execute("IPAWN = new_pawn()")
L.execute("KEYS['F7']()")
check("then works on the next press", ev(L, "IPAWN.Invincible") is True)

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
