# Release builder checks (CRD-015): the dev-key removal, the key-bind check, the forbidden-name scan, the path allowlist, and the repo's
# own main.lua going through the removal cleanly (exactly one key left out: END). No zip is built here.
#   python tools\release\tests\test_build_release.py
import os
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, ".."))
import build_release as br

passed = failed = 0


def check(ok, what):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1
        print("FAIL: " + what)


def raises(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


# --- strip_dev_keys on a small file, both line endings
src = ("local DEV_KEYS = true       -- comment\n"
       "RegisterKeyBind(Key.NUM_ONE, function() end)\n"
       "if DEV_KEYS then\n"
       "    RegisterKeyBind(Key.END, function()\n"
       "        x()\n"
       "    end)\n"
       "end\n"
       "log('done')\n")
for nl in ("\n", "\r\n"):
    out = br.strip_dev_keys(src.replace("\n", nl).encode()).decode()
    check("local DEV_KEYS = false" in out and "DEV_KEYS = true" not in out, "DEV_KEYS switched off (%r)" % nl)
    check("Key.END" not in out and "if DEV_KEYS then" not in out, "dev-key block removed (%r)" % nl)
    check("log('done')" in out and "Key.NUM_ONE" in out, "the rest kept (%r)" % nl)
    check(("\r\n" in out) == (nl == "\r\n") and ("\n" not in out.replace("\r\n", "") if nl == "\r\n" else True), "line endings kept (%r)" % nl)
check(raises(lambda: br.strip_dev_keys(b"local DEV_KEYS = false\n")), "no 'DEV_KEYS = true': refused")
check(raises(lambda: br.strip_dev_keys(b"local DEV_KEYS = true\nlocal DEV_KEYS = true\n")), "two of them: refused")
check(raises(lambda: br.strip_dev_keys(b"local DEV_KEYS = true\nx()\n")), "no block: refused")
check(raises(lambda: br.strip_dev_keys(b"local DEV_KEYS = true\nif DEV_KEYS then\n  y()\n")), "block without end: refused")

# --- key binds and dev-key problems
check(br.key_binds("RegisterKeyBind(Key.NUM_ONE, f)\nRegisterKeyBind( Key.END, g)") == ["NUM_ONE", "END"], "key_binds finds both")
check(br.dev_key_problems("RegisterKeyBind(Key.NUM_ONE, f) RegisterKeyBind(Key.NUM_TWO, g)") == [], "NUMPAD 1/2 only: fine")
check(any("END" in p for p in br.dev_key_problems("RegisterKeyBind(Key.END, f)")), "END bound: flagged")
check(any("F5" in p for p in br.dev_key_problems("RegisterKeyBind(Key.F5, f)")), "unknown key: flagged")
check(br.dev_key_problems("local DEV_KEYS = true") != [], "DEV_KEYS = true: flagged")

# --- the repo's own main.lua
with open(os.path.join(br.ROOT, "mod", "PortalHub", "Scripts", "main.lua"), "rb") as f:
    repo = f.read()
pk = br.strip_dev_keys(repo).decode("utf-8")
check(br.dev_key_problems(pk) == [], "packaged repo main.lua: no dev-key problem")
check(br.key_binds(pk) == ["NUM_ONE", "NUM_TWO"], "packaged repo main.lua binds NUMPAD 1 and 2 only")
check(set(br.key_binds(repo.decode("utf-8"))) - set(br.key_binds(pk)) == {"END"}, "only END was removed")
check(len(pk.splitlines()) == len(repo.decode("utf-8").splitlines()) - 7, "exactly the 8-line block became one line")

# --- forbidden names, read from a mock External Mods folder (the real names are never written here)
with tempfile.TemporaryDirectory() as d:
    for n in ("SomeOtherMod 321 0.9.1 2026.zip", "SomeOtherMod-0.10.0", "UE4SS v3.0.1 35 1.25.0.zip", "Cheaty 28 1.zip", "x"):
        open(os.path.join(d, n), "w").close()
    names = br.forbidden_names(d)
    check("SomeOtherMod" in names and "Cheaty" in names, "External Mods entries become forbidden names")
    check(not any(n.lower() == "ue4ss" for n in names), "UE4SS is allowed (a named dependency)")
    check("Cordona Local Patches" in names, "the private folder's name is always forbidden")
    check(br.find_names(b"... someothermod ...", names) == ["SomeOtherMod"], "scan is case-insensitive")
    check(br.find_names(b"PortalHub UE4SS", names) == [], "clean data passes")
check(br.forbidden_names(os.path.join(tempfile.gettempdir(), "no-such-folder-crd015")) == ["Cordona Local Patches"], "no External Mods: private name only")

# --- allowlist
ok_paths = ["README.md", "LICENSE.txt", "FILES.txt", "PortalHubConfig.bat", "Presets/config-demo.lua",
            br.HUB_DST + "main.lua", br.HUB_DST + "manual_exits.lua", br.TEASER_DST + "WorldC_P.utoc",
            "PortalHubConfig/PortalHubConfig.exe", "PortalHubConfig/_internal/icons/rise.png",
            "tools/PortalHubConfig/PortalHubConfig.py", "tools/PortalHubConfig/icons/rise.png"]
bad_paths = ["AbioticFactor/Binaries/Win64/ue4ss/Mods/PortalMaterialLab/Scripts/main.lua",
             "AbioticFactor/Binaries/Win64/ue4ss/Mods/CordonaProbe/Scripts/main.lua",
             "AbioticFactor/Binaries/Win64/ue4ss/Mods/PortalHub/Scripts/config.lua.bak",
             br.TEASER_DST + "Test_P.pak", "tools/PortalHubConfig/tests/test_gui.py", "tools/PortalHubConfig/PortalHubConfig.ps1",
             "tools/PortalHubConfig/__pycache__/x.pyc", "mods.txt", "Mods/PortalLogger/Scripts/main.lua"]
for p in ok_paths:
    check(br.allowed_path(p), "allowed: " + p)
for p in bad_paths:
    check(not br.allowed_path(p), "refused: " + p)

print("%d checks, %d passed, %d failed" % (passed + failed, passed, failed))
sys.exit(1 if failed else 0)
