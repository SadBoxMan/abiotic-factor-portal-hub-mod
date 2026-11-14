# Game-thread delays (CRD-032): ExecuteWithDelay runs its callback on UE4SS's async thread, in the mod's own Lua state, with no lock against
# the game thread's callbacks, and two threads in one Lua state can damage it ("Ref was not function", a crash when the state is closed).
# The hub, the lab and the probe send every delay through one helper that uses ExecuteInGameThreadWithDelay (UE4SS 1.25.0) when UE4SS has
# it, and the old ExecuteWithDelay + ExecuteInGameThread pair only on an older UE4SS.
import sys, os, re
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(S, "..", "..", "..", "mod")
FILES = {
    "hub": (os.path.join(MOD, "PortalHub", "Scripts", "main.lua"), "function state.later(ms, fn)"),
    "lab": (os.path.join(MOD, "PortalMaterialLab", "Scripts", "main.lua"), "local function later(ms, fn)"),
    "probe": (os.path.join(MOD, "CordonaProbe", "Scripts", "main.lua"), "local function later(ms, fn)"),
}

results = []
def check(name, cond, detail=""):
    results.append(bool(cond))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))

def code_lines(src):
    # each line with its comment cut off (none of these files puts "--" inside a string on a line that calls a delay)
    return [l.split("--", 1)[0] for l in src.splitlines()]

for name, (path, head) in FILES.items():
    src = open(path, encoding="utf-8").read()
    lines = code_lines(src)
    calls = [i for i, l in enumerate(lines) if "ExecuteWithDelay(" in l]
    check(f"{name}: ExecuteWithDelay is called in one place only (the helper's fallback)", len(calls) == 1, [i + 1 for i in calls])
    check(f"{name}: no LoopAsync or ExecuteAsync", not any(("LoopAsync(" in l or "ExecuteAsync(" in l) for l in lines))
    start = src.find(head)
    check(f"{name}: the helper exists", start >= 0)
    if start < 0:
        continue
    block = src[start:src.find("\nend", start) + 4]
    check(f"{name}: the helper prefers ExecuteInGameThreadWithDelay", "if ExecuteInGameThreadWithDelay then ExecuteInGameThreadWithDelay(ms, fn)" in block)
    check(f"{name}: the fallback is inside the helper", calls and src.find("ExecuteWithDelay(", start) < start + len(block))

    # run the helper on its own, with and without the game-thread call
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute("local state = {}\n" + block.replace("local function later", "function later").replace("function state.later", "function later"))
    L.execute(r'''
    CALLS = {}
    function ExecuteInGameThread(fn) CALLS[#CALLS + 1] = "game"; fn() end
    function ExecuteWithDelay(ms, fn) CALLS[#CALLS + 1] = "async " .. math.type(ms); fn() end
    function ExecuteInGameThreadWithDelay(ms, fn) CALLS[#CALLS + 1] = "gamedelay " .. math.type(ms) .. " " .. ms; fn() end
    RAN = 0
    later(1500.0, function() RAN = RAN + 1 end)
    ''')
    check(f"{name}: with UE4SS 1.25.0 the delay runs on the game thread only, with an integer delay",
          L.eval("#CALLS == 1 and CALLS[1] == 'gamedelay integer 1500' and RAN == 1"), list(L.eval("CALLS").values()))
    L.execute("CALLS = {}; ExecuteInGameThreadWithDelay = nil; later(250, function() RAN = RAN + 1 end)")
    check(f"{name}: an older UE4SS gets ExecuteWithDelay, then the game thread",
          L.eval("#CALLS == 2 and CALLS[1] == 'async integer' and CALLS[2] == 'game' and RAN == 2"), list(L.eval("CALLS").values()))

# the hub as a whole: loading it, spawning the portals and running its timers asks for no async delay at all
HUB_DIR = os.path.dirname(FILES["hub"][0])
def load_hub(old_ue4ss):
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB_DIR)
    L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
    L.execute("KEYS = {}; function RegisterKeyBind(key, a, b) KEYS[key] = b or a end")
    if old_ue4ss:
        L.execute("ExecuteInGameThreadWithDelay = nil")
    L.execute(open(FILES["hub"][0], encoding="utf-8").read())
    for _ in range(6):
        L.execute("T = (T or 0) + 0.5; pump()")
    return L

L = load_hub(False)
check("hub: its timers use the game-thread delay", L.eval("GAME_DELAYS") > 0, L.eval("GAME_DELAYS"))
check("hub: no ExecuteWithDelay at all with UE4SS 1.25.0", L.eval("ASYNC_DELAYS") == 0, L.eval("ASYNC_DELAYS"))
L = load_hub(True)
check("hub on an older UE4SS: the timers still run (through ExecuteWithDelay)", L.eval("ASYNC_DELAYS") > 0 and L.eval("GAME_DELAYS") == 0,
      (L.eval("ASYNC_DELAYS"), L.eval("GAME_DELAYS")))

print(f"{len(results)} checks, {results.count(False)} failed")
sys.exit(0 if all(results) else 1)
