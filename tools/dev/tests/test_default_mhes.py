# CRD-031: the default Manual Hub Exits (MHEs) that ship in mod/PortalHub/Scripts/manual_exits.lua.
# Fails if any base-game portal world in the config GUI's destination list (hubdata.DESTINATIONS) has no MHE, or if the file is not what
# the hub and the GUI expect: real Lua that returns a table, no BOM, one line per key (no duplicates), only known keys, four numbers per
# spot with sane coordinates and yaw, a failsafe spot, the same spots read by the GUI's reader as by Lua, and the lab's world list in step
# with the GUI's. Homes (H_*_Start) and custom worlds (World A-D) are not required (LuciDin, 10 November 2026).
#   python tools\dev\tests\test_default_mhes.py [path\to\manual_exits.lua]     (default: the repo copy)
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(S, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
import hubdata
from luaconfig import read_manual_exits

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mod", "PortalHub", "Scripts", "manual_exits.lua")
LAB = os.path.join(ROOT, "mod", "PortalMaterialLab", "Scripts", "main.lua")

REQUIRED = [d[1] for d in hubdata.DESTINATIONS]                 # every base-game portal world the GUI offers
OPTIONAL = {"H_Cabin_Start", "H_Garden_Start", "H_Japan_Start"}  # homes: allowed, not required
MAX_XY = 2_000_000      # 20 km from the map origin (the widest spots seen are ~3.4 km)
MAX_Z = 300_000         # 3 km up or down
PORTAL_ROOM_CM = 3000   # an MHE this close to the failsafe was recorded in the portal room by mistake
TWIN_CM = 500           # two worlds' MHEs this close: one of them was probably given to the wrong world

fails = 0
checks = 0


def check(ok, what):
    global fails, checks
    checks += 1
    if not ok:
        fails += 1
        print("FAIL", what)


raw = open(PATH, "rb").read()
check(not raw.startswith(b"\xef\xbb\xbf"), "no BOM")
text = raw.decode("utf-8")

# real Lua, as the hub loads it
L = lupa.LuaRuntime(unpack_returned_tuples=True)
try:
    t = L.execute(text)
    lua_ok = lupa.lua_type(t) == "table"
except lupa.LuaError as err:
    t, lua_ok = None, False
    print("Lua error:", err)
check(lua_ok, "the file is Lua that returns a table")
spots = {}
if lua_ok:
    for k, v in t.items():
        if lupa.lua_type(v) == "table":
            spots[str(k)] = [v[i] for i in range(1, len(v) + 1)]
        else:
            check(False, f"{k}: is a table")

# one line per key; the lab's own writer keeps the return { ... } shape it needs
keys = re.findall(r'^\s*\[?"?([A-Za-z0-9_]+)"?\]?\s*=\s*{', text, re.M)
dups = sorted({k for k in keys if keys.count(k) > 1})
check(not dups, f"no duplicate keys (found {dups})")
check(re.search(r"^\s*return\s*{\s*$", text, re.M) and re.search(r"^\s*}\s*$", text, re.M), "return { ... } on lines of their own (the lab writes into it)")
check(set(keys) == set(spots), "every key line is read by Lua")

# the GUI reads the same spots (it never writes this file: read-only round trip)
gspots, gfail, problem = read_manual_exits(PATH)
check(problem == "", f"the GUI reads the file ({problem})")
gall = dict(gspots)
if gfail is not None:
    gall["failsafe"] = gfail
check(set(gall) == set(spots), f"the GUI and Lua see the same keys (GUI only: {sorted(set(gall) - set(spots))}, Lua only: {sorted(set(spots) - set(gall))})")
for k, v in spots.items():
    if k in gall:
        check([float(x) for x in (list(v) + [0])[:4]] == gall[k], f"{k}: the GUI reads the same numbers")

# known keys only, every world present
known = set(REQUIRED) | OPTIONAL | {"failsafe"}
orphans = sorted(set(spots) - known)
check(not orphans, f"only known keys (unknown: {orphans})")
missing = [d for d in hubdata.DESTINATIONS if d[1] not in spots]
check(not missing, "every world has an MHE; missing: " + ", ".join(f"{d[2]} ({d[1]})" for d in missing))
check("failsafe" in spots, "the Failsafe Exit is recorded")

# sane spots
for k, v in spots.items():
    check(len(v) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v), f"{k}: four numbers {{ x, y, z, yaw }}")
    if len(v) != 4:
        continue
    x, y, z, yaw = v
    check(abs(x) <= MAX_XY and abs(y) <= MAX_XY and abs(z) <= MAX_Z, f"{k}: coordinates in range ({x}, {y}, {z})")
    check(0 <= yaw <= 360, f"{k}: yaw 0-360 ({yaw})")
    check((x, y, z) != (0, 0, 0), f"{k}: not the map origin")
fs = spots.get("failsafe")
names = sorted(k for k in spots if k != "failsafe")
for k in names:
    v = spots[k]
    if fs and len(v) == 4:
        d = sum((a - b) ** 2 for a, b in zip(v[:3], fs[:3])) ** 0.5
        check(d > PORTAL_ROOM_CM, f"{k}: not in the portal room ({d / 100:.0f} m from the failsafe)")
for i, a in enumerate(names):
    for b in names[i + 1:]:
        d = sum((p - q) ** 2 for p, q in zip(spots[a][:3], spots[b][:3])) ** 0.5
        check(d > TWIN_CM, f"{a} and {b}: not the same spot ({d / 100:.1f} m apart)")

# the lab records MHEs for the same worlds the GUI lists (plus the Cabin)
lab = open(LAB, encoding="utf-8").read()
m = re.search(r"local MHE_WORLDS = {(.*?)}", lab, re.S)
labw = re.findall(r'"([^"]+)"', m.group(1)) if m else []
check(set(labw) - OPTIONAL == set(REQUIRED), f"the lab's MHE_WORLDS match hubdata.DESTINATIONS ({sorted(set(labw) ^ set(REQUIRED))})")

print(f"{len(names)} MHE(s) + {'failsafe' if fs else 'no failsafe'} in {PATH}")
print(f"{checks} checks, {fails} failed")
sys.exit(1 if fails else 0)
