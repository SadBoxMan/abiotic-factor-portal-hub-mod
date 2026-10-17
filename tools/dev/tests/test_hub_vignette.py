# Runs the real mod/PortalHub/Scripts/main.lua against hub_mock.lua (a fake of the UE4SS API) and walks the vignette scenarios.
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa may be installed there (pip install --target %TEMP%\pylib lupa)
import lupa

S = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mod", "PortalHub", "Scripts")

L = lupa.LuaRuntime(unpack_returned_tuples=True)
g = L.globals()
L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
L.execute("LOADER_TITLE = 'Made By The Map Maker'")
L.execute(open(os.path.join(HUB, "main.lua"), encoding="utf-8").read())

results = []
seen = [0]


def new_logs():
    logs = g.LOGS
    out = [logs[i] for i in range(seen[0] + 1, len(logs) + 1)]
    seen[0] = len(logs)
    return out


def tick(n=1, dt=0.5):
    for _ in range(n):
        g.T = g.T + dt
        L.execute("pump()")


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def lua(expr):
    return L.eval(expr)


def show(title):
    print("--- " + title)
    for line in new_logs():
        print("    " + line)


show("load")
tick(2)
show("outside, two ticks")
check("no tracker errors so far", not any("tracker error" in l for l in [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]))
check("outside: level entry untouched", lua("PC.ActiveLevelFXName.s") == "office1")

# arrive in the Test World
L.execute("LOC.X, LOC.Y, LOC.Z = 1100500, 1300000, 80")
tick(1)
show("arrived")
check("row added once", lua("#ADDED") == 1 and lua("ADDED[1]") == "PortalHub_cordonatest_start", lua("#ADDED"))
row_ok = lua("LEVEL_ROWS.PortalHub_cordonatest_start ~= nil and LEVEL_ROWS.PortalHub_cordonatest_start[F('IsVignette')] == true")
check("row is a vignette", row_ok)
check("row entrance = world id", lua("LEVEL_ROWS.PortalHub_cordonatest_start[F('EntranceTeleporter')].s") == "cordonatest_start")
check("row title = WorldTitle from the loader Blueprint", lua("LEVEL_ROWS.PortalHub_cordonatest_start[F('SectorName')].s") == "Made By The Map Maker")
check("claimed: ActiveLevelFXName", lua("PC.ActiveLevelFXName.s") == "PortalHub_cordonatest_start")
check("claimed: level name", lua("PC.ActiveLevelName.s") == "PortalHub_cordonatest_start", lua("PC.ActiveLevelName.s"))
check("lighting switched to HGarden with title", lua("TRANSITIONS[1]") == "HGarden / HGarden / 'Made By The Map Maker'", lua("TRANSITIONS[1]"))
check("automatic lighting on for the switch", lua("PC.DisableAutomaticFX") is False)

tick(2)   # 1 s: manual lighting not yet
check("custom lighting waits for the switch", lua("PC.DisableAutomaticFX") is False)
tick(3)   # 2.5 s total
show("2.5 s later")
check("custom lighting applied after the switch", lua("PC.DisableAutomaticFX") is True)

# the game changes the level entry while inside (e.g. a respawn)
L.execute("PC.ActiveLevelFXName = FName('office1')")
tick(8)
show("game changed the entry while inside")
check("entry put back while inside", lua("PC.ActiveLevelFXName.s") == "PortalHub_cordonatest_start")

# dead: no pawn
L.execute("PC.Pawn = nil")
L.execute("LOC.X, LOC.Y = -10000, 9000")
tick(3)
show("dead (no pawn), body moved away")
check("nothing changed while dead", lua("PC.ActiveLevelFXName.s") == "PortalHub_cordonatest_start")
L.execute("PC.Pawn = PAWN")

# leave (back to the portal room, fog still on)
tick(1)
show("left the world")
check("entry back to office1", lua("PC.ActiveLevelFXName.s") == "office1", lua("PC.ActiveLevelFXName.s"))
check("level name back to Facility_Office1", lua("PC.ActiveLevelName.s") == "Facility_Office1", lua("PC.ActiveLevelName.s"))
check("lighting back to the weather rows with the sector title", lua("TRANSITIONS[#TRANSITIONS]") == "Weather_Fog / Weather_Fog_Night / 'The Office Sector'", lua("TRANSITIONS[#TRANSITIONS]"))
check("automatic lighting back on", lua("PC.DisableAutomaticFX") is False)
check("no extra update when the entry switch handles it", lua("UPDATES") == 0, lua("UPDATES"))

# re-enter: row not added again
tick(1)
L.execute("LOC.X, LOC.Y = 1100500, 1300000")
tick(1)
show("re-entered")
check("row not added twice", lua("#ADDED") == 1)
check("claimed again", lua("PC.ActiveLevelFXName.s") == "PortalHub_cordonatest_start")

# the game moves the player to another level by itself (respawn at a bed elsewhere), then the player is outside
L.execute("PC.ActiveLevelFXName = FName('Labs')")
L.execute("LOC.X, LOC.Y = -20000, 5000")
tick(1)
show("respawned at a bed in another sector")
check("game's own entry kept", lua("PC.ActiveLevelFXName.s") == "Labs")

# weather over: back to the level's own rows
tick(1)
L.execute("PC.ActiveWeatherFXName = FName('None')")
L.execute("LOC.X, LOC.Y = 1100500, 1300000")
tick(1)
L.execute("LOC.X, LOC.Y = -10000, 9000")
tick(1)
show("in and out again without weather")
check("previous entry (Labs) put back", lua("PC.ActiveLevelFXName.s") == "Labs")

# mods restarted: a leftover entry of ours while outside
L.execute("PC.ActiveLevelFXName = FName('PortalHub_cordonatest_start'); PC.ActiveLevelName = 'PortalHub_cordonatest_start'")
tick(1)
show("leftover entry found outside")
check("leftover released to the fallback", lua("PC.ActiveLevelFXName.s") == "office1")
check("leftover level name from the office1 row", lua("PC.ActiveLevelName.s") == "Facility_Office1", lua("PC.ActiveLevelName.s"))

allLogs = [g.LOGS[i] for i in range(1, len(g.LOGS) + 1)]
check("no tracker errors at all", not any("tracker error" in l for l in allLogs), [l for l in allLogs if "tracker error" in l])
failed = [n for n, ok in results if not ok]
print("\n%d checks, %d passed, %d failed" % (len(results), len(results) - len(failed), len(failed)))
