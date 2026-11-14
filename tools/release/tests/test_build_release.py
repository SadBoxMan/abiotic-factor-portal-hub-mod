# Release builder checks (CRD-015): the dev-key removal, the key-bind check, the forbidden-name scan, the path allowlist, and the repo's
# own main.lua going through the removal cleanly (exactly one key left out: END). No zip is built here.
#   python tools\release\tests\test_build_release.py
import os
import re
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
check(set(br.key_binds(repo.decode("utf-8"))) - set(br.key_binds(pk)) == {"END", "PAUSE"},
      "only the dev keys were removed (END: Player 2 pretend; PAUSE: the DLC guard test, CRD-033)")
_rl = repo.decode("utf-8").splitlines()
_s = _rl.index("if DEV_KEYS then")
_block = next(i for i in range(_s + 1, len(_rl)) if _rl[i] == "end") - _s + 1
check(len(pk.splitlines()) == len(_rl) - (_block - 1) and "hub_dlctest" not in pk, "exactly the dev-key block became one line (the DLC test pad with it)")

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
ok_paths = ["README.md", "LICENSE.txt", "FILES.txt", "PortalHubConfig.bat",
            br.HUB_DST + "main.lua", br.HUB_DST + "manual_exits.lua",
            "PortalHubConfig/PortalHubConfig.exe", "PortalHubConfig/_internal/icons/rise.png",
            "tools/PortalHubConfig/PortalHubConfig.py", "tools/PortalHubConfig/icons/rise.png"]
bad_paths = ["AbioticFactor/Binaries/Win64/ue4ss/Mods/PortalMaterialLab/Scripts/main.lua",
             "AbioticFactor/Binaries/Win64/ue4ss/Mods/CordonaProbe/Scripts/main.lua",
             "AbioticFactor/Binaries/Win64/ue4ss/Mods/PortalHub/Scripts/config.lua.bak",
             br.TEASER_DST + "Test_P.pak", "tools/PortalHubConfig/tests/test_gui.py", "tools/PortalHubConfig/PortalHubConfig.ps1",
             "tools/PortalHubConfig/__pycache__/x.pyc", "mods.txt", "Mods/PortalLogger/Scripts/main.lua",
             # the main download is blank (CRD-031): presets and teaser worlds are optional downloads of their own
             "Presets/config-demo.lua", "Presets/pack1-demo.lua", br.TEASER_DST + "WorldC_P.utoc",
             "Optional - 2.0 teaser worlds/AbioticFactor/Content/Paks/~mods/WorldA_P.pak"]
for p in ok_paths:
    check(br.allowed_path(p), "allowed: " + p)
for p in bad_paths:
    check(not br.allowed_path(p), "refused: " + p)

# --- preset packs (CRD-031): one optional download per committed pack, pack 1 required, Pack 4 carries the teaser worlds
check(br.order_presets(["pack3-builder-worlds.lua", "pack1-demo.lua"]) == (["pack1-demo.lua", "pack3-builder-worlds.lua"], []),
      "presets in pack order, missing packs skipped")
check(br.order_presets(list(br.PRESET_NAMES)[::-1]) == (list(br.PRESET_NAMES), []), "all four packs")
check(br.order_presets(["pack1-demo.lua", "notes.txt"]) == (["pack1-demo.lua"], ["notes.txt"]), "an unknown file is reported, not shipped")
check(br.REQUIRED_PRESET == "pack1-demo.lua" and br.TEASER_PACK == "pack4-custom-worlds.lua", "pack 1 required, pack 4 has the teaser worlds")
check(len({p[1] for p in br.PACKS}) == 4 and all(p[1].startswith("Pack%d-" % (i + 1)) for i, p in enumerate(br.PACKS)), "four distinct zip names")
for preset in br.PRESET_NAMES:
    check(br.allowed_pack_path("Presets/" + preset, preset) and br.allowed_pack_path("README.md", preset), "pack allows its preset: " + preset)
    others = [n for n in br.PRESET_NAMES if n != preset]
    check(not any(br.allowed_pack_path("Presets/" + n, preset) for n in others), "pack refuses the other presets: " + preset)
    check(not br.allowed_pack_path(br.HUB_DST + "main.lua", preset), "pack refuses the hub: " + preset)
check(br.allowed_pack_path(br.TEASER_DST + "WorldB_P.ucas", br.TEASER_PACK), "Pack 4 allows the teaser worlds")
check(not br.allowed_pack_path(br.TEASER_DST + "WorldB_P.ucas", br.REQUIRED_PRESET), "Pack 1 refuses the teaser worlds")
check(not br.allowed_pack_path(br.TEASER_DST + "Test_P.pak", br.TEASER_PACK), "Pack 4 refuses other paks")
pdir = os.path.join(br.ROOT, "tools", "release", "presets")
check(os.path.isfile(os.path.join(pdir, "pack1-demo.lua")), "pack1-demo.lua exists")
check(os.path.isfile(os.path.join(br.ROOT, "tools", "release", "README-presets.md")), "the packs' README exists")
for n in sorted(os.listdir(pdir)):
    check(n in br.PRESET_NAMES, "presets folder holds only preset names: " + n)
    t = open(os.path.join(pdir, n), "rb").read()
    check(not t.startswith(b"\xef\xbb\xbf") and t.startswith(b"-- Portal Hub preset: Pack "), n + ": no BOM, starts with its header")
    check(b"made by the author" in t.lower(), n + ": the header says the author made it")
tmpl = open(os.path.join(br.ROOT, "mod", "PortalHub", "Scripts", "config.lua"), encoding="utf-8").read()
check(not re.search(r'^\s*\{\s*slot\s*=', tmpl, re.M), "the main download's template config has no portals (blank)")

print("%d checks, %d passed, %d failed" % (passed + failed, passed, failed))
sys.exit(1 if failed else 0)
