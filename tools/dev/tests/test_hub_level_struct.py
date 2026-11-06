# Runs the real mod/PortalHub/Scripts/main.lua against hub_mock.lua with each layout of the game's level row struct: native since game
# update v1.5.0 (found through DT_Levels.RowStruct, or by its /Script path when RowStruct cannot be read), the old Blueprint struct, and
# none at all. Checks that the vignette level entry is added, that the soft-object field Level is never written, and that leaving puts
# the level name back.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(S, "..", "..", "..", "mod", "PortalHub", "Scripts")

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def run(title, setup, after_mock=""):
    print("=== " + title)
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    g = L.globals()
    L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
    L.execute(setup)
    L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
    L.execute(after_mock)
    L.execute("LOADER_TITLE = 'Struct Test'")
    L.execute(open(os.path.join(HUB, "main.lua"), encoding="utf-8").read())

    def tick(n=1):
        for _ in range(n):
            g.T = g.T + 0.5
            L.execute("pump()")

    def logs():
        return [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]

    tick(2)
    L.execute("LOC.X, LOC.Y, LOC.Z = 1100500, 1300000, 80")
    tick(1)
    return L, g, tick, logs


def leave_and_leftover(L, tick, prefix):
    L.execute("LOC.X, LOC.Y = -10000, 9000")
    tick(1)
    check(prefix + ": left, entry back to office1", L.eval("PC.ActiveLevelFXName.s") == "office1", L.eval("PC.ActiveLevelFXName.s"))
    check(prefix + ": left, level name back", L.eval("PC.ActiveLevelName.s") == "Facility_Office1", L.eval("PC.ActiveLevelName.s"))
    # mods restarted: a leftover entry of ours outside, previous level unknown
    L.execute("PC.ActiveLevelFXName = FName('PortalHub_cordonatest_start'); PC.ActiveLevelName = 'PortalHub_cordonatest_start'")
    tick(1)
    check(prefix + ": leftover released to office1", L.eval("PC.ActiveLevelFXName.s") == "office1")
    check(prefix + ": leftover level name Facility_Office1", L.eval("PC.ActiveLevelName.s") == "Facility_Office1", L.eval("PC.ActiveLevelName.s"))


ROW = "LEVEL_ROWS.PortalHub_cordonatest_start"

# 1. native struct through DT_Levels.RowStruct (the game since v1.5.0)
L, g, tick, logs = run("native, through RowStruct", "")
lg = logs()
check("native: struct logged from RowStruct", any("row struct is ScriptStruct /Script/AbioticFactor.LevelMetadata (from DT_Levels.RowStruct)" in l for l in lg),
      [l for l in lg if "row struct" in l])
check("native: row added", L.eval("#ADDED") == 1, [l for l in lg if "vignette" in l])
check("native: row is a vignette", L.eval(ROW + " ~= nil and " + ROW + ".IsVignette == true"))
check("native: no value for the soft-object Level", L.eval(ROW + " ~= nil and " + ROW + ".Level == nil"))
check("native: bIsSublevel false", L.eval(ROW + " ~= nil and " + ROW + ".bIsSublevel == false"))
check("native: entrance = world id", L.eval(ROW + ".EntranceTeleporter.s") == "cordonatest_start")
check("native: title", L.eval(ROW + ".SectorName.s") == "Struct Test")
check("native: claimed", L.eval("PC.ActiveLevelFXName.s") == "PortalHub_cordonatest_start")
check("native: struct logged once", sum(1 for l in lg if "row struct is" in l) == 1, sum(1 for l in lg if "row struct is" in l))
leave_and_leftover(L, tick, "native")

# 1b. a world with no lighting block of its own (like Worlds A and C): the controller's Day_FX_Row is a row handle struct; reading it must not
# look like the game changing the lighting (6 November 2026: "changed the lighting to nil" every 3 s)
L, g, tick, logs = run("native, world without a lighting block", "", "CONFIG.worlds.cordonatest_start.lighting = nil")
n = L.eval("#TRANSITIONS")
tick(10)
lg = logs()
check("handle: Day_FX_Row read, lighting left alone", not any("the game changed the lighting" in l for l in lg) and L.eval("#TRANSITIONS") == n,
      [l for l in lg if "the game changed" in l])

# 2. native struct, RowStruct unreadable: found by its /Script path
L, g, tick, logs = run("native, RowStruct unreadable", "NO_ROW_STRUCT = true")
lg = logs()
check("path: struct logged from /Script path", any("(from /Script/AbioticFactor.LevelMetadata)" in l for l in lg), [l for l in lg if "row struct" in l])
check("path: row added without Level", L.eval("#ADDED") == 1 and L.eval(ROW + ".Level == nil"))
leave_and_leftover(L, tick, "path")

# 3. the old Blueprint struct (before v1.5.0)
L, g, tick, logs = run("old Blueprint struct", "LEGACY_LEVEL_STRUCT = true")
lg = logs()
check("legacy: struct logged from the Blueprint path", any("LevelMetadata_Struct.LevelMetadata_Struct)" in l for l in lg), [l for l in lg if "row struct" in l])
check("legacy: row added", L.eval("#ADDED") == 1)
check("legacy: LevelFileName = row name", L.eval(ROW + "[F('LevelFileName')].s") == "PortalHub_cordonatest_start")
check("legacy: vignette", L.eval(ROW + "[F('IsVignette')] == true"))
leave_and_leftover(L, tick, "legacy")

# 4. no struct anywhere: the world stays a Facility area, nothing breaks
L, g, tick, logs = run("no struct at all", "NO_ROW_STRUCT = true", "LEVEL_STRUCT_PATH = 'nowhere'")
lg = logs()
check("none: struct logged as none", any("row struct is none" in l for l in lg), [l for l in lg if "row struct" in l])
check("none: entry refused with the game-update message", any("has no field ReleaseGroup (game update?)" in l for l in lg))
check("none: no row added", L.eval("#ADDED") == 0)
check("none: level entry untouched", L.eval("PC.ActiveLevelFXName.s") == "office1")

allLogs = lg
check("no tracker errors (last run)", not any("tracker error" in l for l in allLogs), [l for l in allLogs if "tracker error" in l])
failed = [n for n, ok in results if not ok]
print("\n%d checks, %d passed, %d failed" % (len(results), len(results) - len(failed), len(failed)))
sys.exit(1 if failed else 0)
