# Runs the real mod/PortalMaterialLab/Scripts/main.lua against the lab's mock game (borrowed from test_lab_assessment.py) and checks the
# CRD-016 no-clip (F5): the capsule's blocking channels go to overlap and come back, the actor's collision is never switched off
# (that hid the Facility's sublevels), the old whole-actor switch is only the fallback, and flying is switched on and off.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(S, "..", "..", "..", "mod", "PortalMaterialLab", "Scripts", "main.lua")
MOCK = re.search(r'MOCK = r"""(.*?)"""', open(os.path.join(S, "test_lab_assessment.py"), encoding="utf-8").read(), re.S).group(1)

# A writable pawn for F5: capsule with 32 channels (0, 1, 2 and 30 block, 3 overlaps, the rest ignore), a movement component.
PAWN = r"""
COLL = {}            -- SetActorEnableCollision calls
RESP = {}            -- channel -> response
for ch = 0, 31 do RESP[ch] = 0 end
RESP[0], RESP[1], RESP[2], RESP[30], RESP[3] = 2, 2, 2, 2, 1
CAP_OK = true
MODES = {}
local cap = {
    IsValid = function() return true end,
    GetCollisionResponseToChannel = function(self, ch) return RESP[ch] end,
    SetCollisionResponseToChannel = function(self, ch, r) RESP[ch] = r end,
}
MV = { IsValid = function() return true end, MaxFlySpeed = 600.0, bCheatFlying = false,
       SetMovementMode = function(self, m) MODES[#MODES + 1] = m end }
NPAWN = setmetatable({
    IsValid = function() return true end,
    GetFName = function() return FName("Player_C_0") end,
    K2_GetActorLocation = function() return { X = 10, Y = 20, Z = 30 } end,
    SetActorEnableCollision = function(self, on) COLL[#COLL + 1] = on end,
    Client_DisplayWarningMessage = function() end,
    CharacterMovement = MV,
}, { __index = function(_, k) if k == "CapsuleComponent" then return CAP_OK and cap or nil end end })
NPC = { IsValid = function() return true end, Pawn = NPAWN }
local find = FindFirstOf
function FindFirstOf(name) if name == "Abiotic_PlayerController_C" then return NPC end return find(name) end
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
    return L


def logs(L):
    g = L.globals()
    return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]


def has(L, text):
    return any(text in line for line in logs(L))


def ev(L, expr):
    return L.eval(expr)


print("=== F5 on: capsule passes through, overlaps kept")
L = lab()
L.execute("KEYS['F5']()")
check("actor collision never switched off", ev(L, "#COLL") == 0)
check("blocking channels now overlap", all(ev(L, "RESP[%d]" % c) == 1 for c in (0, 1, 2, 30)))
check("the overlapping channel is untouched", ev(L, "RESP[3]") == 1)
check("ignored channels stay ignored", all(ev(L, "RESP[%d]" % c) == 0 for c in (4, 17, 31)))
check("flying on", ev(L, "MV.bCheatFlying") is True and ev(L, "MODES[#MODES]") == 5 and ev(L, "MV.MaxFlySpeed") == 2000.0)
check("the log names the switched channels", has(L, "4 blocking channel(s) set to overlap: 0 1 2 30"), logs(L)[-3:])

print("=== F5 off: everything back")
L.execute("KEYS['F5']()")
check("blocking channels block again", all(ev(L, "RESP[%d]" % c) == 2 for c in (0, 1, 2, 30)))
check("the overlapping channel still overlaps", ev(L, "RESP[3]") == 1)
check("ignored channels still ignored", all(ev(L, "RESP[%d]" % c) == 0 for c in (4, 17, 31)))
check("actor collision still never touched", ev(L, "#COLL") == 0)
check("flying off, falling, fly speed back", ev(L, "MV.bCheatFlying") is False and ev(L, "MODES[#MODES]") == 3 and ev(L, "MV.MaxFlySpeed") == 600.0)
check("restore logged", has(L, "4 of 4 channel(s) back to block") and has(L, "no-clip OFF at 10, 20, 30"))

print("=== F5 again: a second round works the same")
L.execute("KEYS['F5']()")
check("second on switches the same channels", all(ev(L, "RESP[%d]" % c) == 1 for c in (0, 1, 2, 30)))
L.execute("KEYS['F5']()")
check("second off restores them", all(ev(L, "RESP[%d]" % c) == 2 for c in (0, 1, 2, 30)))

print("=== no capsule: the old switch as fallback")
L = lab()
L.execute("CAP_OK = false")
L.execute("KEYS['F5']()")
check("fallback switches actor collision off", ev(L, "COLL[1]") is False)
check("fallback is logged", has(L, "FALLBACK (no capsule)"), logs(L)[-3:])
L.execute("KEYS['F5']()")
check("fallback off switches it back on", ev(L, "COLL[2]") is True)

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
