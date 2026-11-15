# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py) and checks the
# CRD-040 survey key (F9): one untried game call per press. Server_RemoveBuff first; if the sickness stays, the next press tries
# Server_RemoveSpecificBuffs. Says when there is nothing to remove, copes with no pawn, and is bound to F9 only.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

PAWN = r"""
REMOVE_CALLS, SPECIFIC_CALLS = {}, {}
REMOVE_WORKS, SPECIFIC_WORKS = true, true
function buff(row) return { get = function() return { BuffRow = { RowName = FName(row) }, BuffExpireTime = -1.0 } end } end
BUFFS = { buff("Buff_InVignette"), buff("Debuff_PortalSickness"), buff("Buff_LeyakSafetyZone") }
local function drop(row) local out = {} for _, b in ipairs(BUFFS) do if b:get().BuffRow.RowName:ToString() ~= row then out[#out + 1] = b end end BUFFS = out end
BC = { IsValid = function() return true end,
       CurrentBuffs = { ForEach = function(self, fn) for i, b in ipairs(BUFFS) do fn(i, b) end end },
       Server_RemoveBuff = function(self, row, stack, limb, expired)
           REMOVE_CALLS[#REMOVE_CALLS + 1] = row.RowName:ToString() .. "/" .. tostring(stack) .. "/" .. tostring(limb) .. "/" .. tostring(expired)
           if REMOVE_WORKS then drop(row.RowName:ToString()) end
           return REMOVE_WORKS
       end,
       Server_RemoveSpecificBuffs = function(self, rows, specific, limbs)
           SPECIFIC_CALLS[#SPECIFIC_CALLS + 1] = rows[1].RowName:ToString() .. "/" .. tostring(specific) .. "/" .. tostring(#limbs)
           if SPECIFIC_WORKS then drop(rows[1].RowName:ToString()) end
       end }
SPAWN = { IsValid = function() return true end, BuffComponent = BC, K2_GetActorLocation = function() return { X = 1, Y = 2, Z = 3 } end }
SPC = { IsValid = function() return true end, Pawn = SPAWN }
local find = FindFirstOf
function FindFirstOf(name) if name == "Abiotic_PlayerController_C" then return SPC end return find(name) end
"""

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail != "" and not cond else ""))


def lab(extra=""):
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(MOCK)
    L.execute(open(LAB, encoding="utf-8").read())
    L.execute(PAWN)
    if extra:
        L.execute(extra)
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


ev = lambda L, e: L.eval(e)
src = open(LAB, encoding="utf-8").read()

print("=== F9 is bound, and only once, by no other mod of ours; not a game key")
check("F9 bound to the remove test", re.search(r"RegisterKeyBind\(Key\.F9, function\(\) ExecuteInGameThread\(remove_sickness\)", src))
check("F9 bound once in the lab", len(re.findall(r"Key\.F9\b", src)) == 1)
check("DOWN ARROW not used (the game's walk-backward key)", "DOWN_ARROW" not in src)
others = "".join(open(os.path.join(ROOT, "mod", m, "Scripts", "main.lua"), encoding="utf-8").read()
                 for m in ("PortalHub", "CordonaProbe", "PortalLogger", "CordonaDlcSurvey") if os.path.exists(os.path.join(ROOT, "mod", m, "Scripts", "main.lua")))
check("no other mod of ours binds F9", "Key.F9" not in others)
check("listed in the lab's key lines", "test key: F9" in src and "--   F9 " in src)
check("no new top-level local (kept inside a do block)", "\ndo\n    local SICK = " in src)

print("=== first press: Server_RemoveBuff only, and it works")
L = lab()
L.execute("KEYS['F9']()")
check("Server_RemoveBuff called once: the sickness row, entire stack, limb 0 (AllBones), not expired",
      ev(L, "#REMOVE_CALLS") == 1 and ev(L, "REMOVE_CALLS[1]") == "Debuff_PortalSickness/true/0/false", ev(L, "REMOVE_CALLS[1]"))
check("named in the log before it runs", has(L, "calling Server_RemoveBuff now"))
check("before 1, after 0 logged", has(L, "Debuff_PortalSickness before: 1") and has(L, "Server_RemoveBuff: returned true; after: 0"), logs(L)[-4:])
check("no second call in the same press", ev(L, "#SPECIFIC_CALLS") == 0)
check("other buffs untouched", ev(L, "#BUFFS") == 2)
check("a 2 s look queued", ev(L, "#DELAYED") >= 1)
L.execute("pump()")
check("2 s later: 0 logged, then done", has(L, "2 s later: Debuff_PortalSickness 0") and has(L, "PORTAL SICKNESS REMOVE TEST done"))

print("=== Server_RemoveBuff leaves it: the NEXT press tries Server_RemoveSpecificBuffs (one untried call per press)")
L = lab("REMOVE_WORKS = false")
L.execute("KEYS['F9']()")
check("first press: only Server_RemoveBuff", ev(L, "#REMOVE_CALLS") == 1 and ev(L, "#SPECIFIC_CALLS") == 0)
check("says the next press tries the other call", has(L, "the next F9 press tries Server_RemoveSpecificBuffs"))
L.execute("KEYS['F9']()")
check("second press: only Server_RemoveSpecificBuffs (row, no specific limbs, no limbs)",
      ev(L, "#REMOVE_CALLS") == 1 and ev(L, "SPECIFIC_CALLS[1]") == "Debuff_PortalSickness/false/0", (ev(L, "#REMOVE_CALLS"), ev(L, "SPECIFIC_CALLS[1]")))
check("named in the log before it runs", has(L, "calling Server_RemoveSpecificBuffs now"))
check("its result logged", has(L, "Server_RemoveSpecificBuffs: returned nil; after: 0"), logs(L)[-3:])
L.execute("BUFFS[#BUFFS + 1] = buff('Debuff_PortalSickness'); KEYS['F9']()")
check("then it starts over with Server_RemoveBuff", ev(L, "#REMOVE_CALLS") == 2 and ev(L, "#SPECIFIC_CALLS") == 1)

print("=== nothing to remove / no pawn / a failing call")
L = lab("BUFFS = { buff('Buff_InVignette') }")
L.execute("KEYS['F9']()")
check("no sickness: says so, calls nothing", has(L, "nothing to remove") and ev(L, "#REMOVE_CALLS") == 0)
L = lab("SPC.Pawn = nil")
L.execute("KEYS['F9']()")
check("no pawn: logged, calls nothing", has(L, "no player pawn") and ev(L, "#REMOVE_CALLS") == 0)
L = lab("BC.Server_RemoveBuff = function() error('bad args') end")
L.execute("KEYS['F9']()")
check("a failing call is caught and logged", has(L, "Server_RemoveBuff: failed:") and ev(L, "#SPECIFIC_CALLS") == 0, logs(L)[-3:])

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
