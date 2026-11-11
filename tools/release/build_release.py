r"""Builds the public Portal Hub release zip for Nexus (CRD-015) into Release\ at the repo root (git-ignored: never commit the output).

    python tools\release\build_release.py                  build from the files committed at HEAD
    python tools\release\build_release.py --final          the same, but refuse to build without the Nexus URL in the GUI
    python tools\release\build_release.py --reuse-gui      use tools\PortalHubConfig\dist\ instead of building the exe again
    python tools\release\build_release.py --worktree       TEST ONLY: read the working tree instead of HEAD (FILES.txt says so; never upload)

Everything shipped is read from git HEAD (git show / git archive), never from the working tree: another card may be editing
main.lua, and an uncommitted file must never reach players. The working-tree copies are only compared, with a warning if they differ.

What ships (inside "PortalHub <VERSION>\"):
    AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\Scripts\
        main.lua            the repo's, with DEV_KEYS = false and the dev-key block removed (packaged copy only)
        slots.lua, manual_exits.lua, config.lua (the template)
    PortalHubConfig\        the config editor (one-folder exe, unsigned), built here by PyInstaller from HEAD's sources
    PortalHubConfig.bat     starts it
    tools\PortalHubConfig\  the editor's Python source and icons (no tests), the fallback the .bat uses
    Presets\config-demo.lua the demo preset (tools\release\config-demo.lua)
    Optional - 2.0 teaser worlds\AbioticFactor\Content\Paks\~mods\World[A-D]_P.pak/.ucas/.utoc
    README.md (tools\release\README-player.md), LICENSE.txt, FILES.txt (path, size, SHA-1 of every other file)
Never shipped: the lab, CordonaProbe, PortalLogger, PortalPoC, the test mods, the cheat / item-spawner mods, anything private
("Cordona Local Patches") or third-party (External Mods). The checks below refuse a build that has any of them.

Checks before the zip is written (a failure stops the build):
    every staged path is on the allowlist; no file anywhere holds a name from External Mods (UE4SS excepted) or the private folder;
    the only key binds in the shipped Lua are KNOWN_BINDS (no END, no DEV_KEYS = true); the staged Lua passes the syntax check;
    test_hub_client_mode.py and test_hub_reload.py pass on the staged main.lua.
"""
import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Release")
VERSION = "1.0.0"
TOP = "PortalHub " + VERSION
HUB_DST = "AbioticFactor/Binaries/Win64/ue4ss/Mods/PortalHub/Scripts/"
TEASER_DST = "Optional - 2.0 teaser worlds/AbioticFactor/Content/Paks/~mods/"
PRIVATE_NAMES = ["Cordona Local Patches"]
ALLOWED_TOKENS = {"ue4ss"}          # External Mods holds UE4SS too: a dependency the README names on purpose

# Every key the shipped Lua may bind, with what the game itself binds there by default. Checked 10 November 2026 (v1.5.0.31876) by a
# text search of the ActionMappings / AxisMappings / DebugExecBindings / ConsoleKeys lines in Content\Paks\pakchunk0-Windows.pak
# (pak dated 3 November) and the in-game Settings > Input Bindings list (findings/two-player-test-plan.md, section 2).
KNOWN_BINDS = {
    "NUM_ONE": ("NUMPAD 1", "respawn the hub portals, read manual_exits.lua again",
                "DebugCameraShake (a developer debug action, not in the Controls list)"),
    "NUM_TWO": ("NUMPAD 2", "remove the hub portals",
                "DebugDecreaseCameraShake (a developer debug action, not in the Controls list)"),
}
TESTS_ON_PACKAGED = ["test_hub_client_mode.py", "test_hub_reload.py"]   # the two hub tests that take a main.lua path and need no dev key


def git(*args, binary=False):
    r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True)
    if r.returncode:
        sys.exit("git %s failed: %s" % (" ".join(args), r.stderr.decode(errors="replace").strip()))
    return r.stdout if binary else r.stdout.decode("utf-8").strip()


WORKTREE = False     # --worktree: test builds read the working tree


def committed(path):
    """The file's bytes at HEAD (path relative to the repo, forward slashes); with --worktree, the working-tree file."""
    if WORKTREE:
        with open(os.path.join(ROOT, path), "rb") as f:
            return f.read()
    return git("show", "HEAD:" + path, binary=True)


def strip_dev_keys(b):
    """main.lua with DEV_KEYS off and its key block gone, so the packaged hub binds no dev key at all. The repo file is not touched."""
    old = b"local DEV_KEYS = true"
    if b.count(old) != 1:
        raise ValueError("main.lua: expected exactly one 'local DEV_KEYS = true'")
    b = b.replace(old, b"local DEV_KEYS = false")
    nl = b"\r\n" if b"\r\n" in b else b"\n"
    lines = b.split(nl)
    starts = [i for i, l in enumerate(lines) if l == b"if DEV_KEYS then"]
    if len(starts) != 1:
        raise ValueError("main.lua: expected exactly one top-level 'if DEV_KEYS then' block")
    s = starts[0]
    e = next((i for i in range(s + 1, len(lines)) if lines[i] == b"end"), None)
    if e is None:
        raise ValueError("main.lua: the 'if DEV_KEYS then' block has no top-level 'end'")
    lines[s:e + 1] = [b"-- (the dev keys were removed from this packaged copy)"]
    return nl.join(lines)


def key_binds(text):
    """Every Key.X a Lua file binds (RegisterKeyBind), in order."""
    return re.findall(r"RegisterKeyBind\(\s*Key\.(\w+)", text)


def dev_key_problems(text):
    p = []
    for k in key_binds(text):
        if k not in KNOWN_BINDS:
            p.append("binds Key.%s, which is not a known release key" % k)
    if re.search(r"DEV_KEYS\s*=\s*true", text):
        p.append("DEV_KEYS = true")
    if "Key.END" in text:
        p.append("mentions Key.END (the dev key)")
    return p


def forbidden_names(external_dir=None):
    """Names that must not appear in anything shipped: the private folder, and the leading word of every entry in External Mods
    (third-party mods), read here at build time so no such name is ever written into the repo."""
    names = list(PRIVATE_NAMES)
    d = external_dir or os.path.join(ROOT, "External Mods")
    if os.path.isdir(d):
        for e in os.listdir(d):
            m = re.match(r"[A-Za-z][A-Za-z0-9]{3,}", e)
            if m and m.group(0).lower() not in ALLOWED_TOKENS:
                names.append(m.group(0))
    return sorted(set(names), key=str.lower)


def find_names(data, names):
    low = data.lower()
    return [n for n in names if n.lower().encode() in low]


def allowed_path(rel):
    rel = rel.replace(os.sep, "/")
    if rel in ("README.md", "LICENSE.txt", "FILES.txt", "PortalHubConfig.bat", "Presets/config-demo.lua"):
        return True
    if rel in [HUB_DST + f for f in ("main.lua", "slots.lua", "manual_exits.lua", "config.lua")]:
        return True
    if re.fullmatch(re.escape(TEASER_DST) + r"World[A-D]_P\.(pak|ucas|utoc)", rel):
        return True
    if rel.startswith("PortalHubConfig/"):
        return True
    if rel.startswith("tools/PortalHubConfig/") and "/tests/" not in rel and not rel.endswith((".ps1", ".spec")) \
            and "/dist/" not in rel and "/build/" not in rel and "__pycache__" not in rel:
        return True
    return False


def put(stage, rel, data):
    dst = os.path.join(stage, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)


def export_gui(tmp):
    """tools/PortalHubConfig at HEAD, unpacked into tmp; returns its folder (with --worktree, a copy of the working tree's)."""
    if WORKTREE:
        dst = os.path.join(tmp, "tools", "PortalHubConfig")
        shutil.copytree(os.path.join(ROOT, "tools", "PortalHubConfig"), dst,
                        ignore=shutil.ignore_patterns("dist", "build", "__pycache__", "tests", "*.spec"))
        return dst
    tar = git("archive", "--format=tar", "HEAD", "tools/PortalHubConfig", binary=True)
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(tmp, filter="data")
    return os.path.join(tmp, "tools", "PortalHubConfig")


def read_nexus_url(gui_dir):
    with open(os.path.join(gui_dir, "install_check.py"), encoding="utf-8") as f:
        m = re.search(r'^PORTAL_HUB_NEXUS_URL\s*=\s*"([^"]*)"', f.read(), re.M)
    return m.group(1) if m else None


def build_gui(gui_dir, tmp):
    """PyInstaller one-folder build from the exported sources (the same command as build_exe.bat)."""
    work = os.path.join(tmp, "pyi")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed", "--name", "PortalHubConfig",
           "--add-data", os.path.join(gui_dir, "icons") + ";icons", "--distpath", os.path.join(work, "dist"), "--workpath", os.path.join(work, "build"),
           "--specpath", work, os.path.join(gui_dir, "PortalHubConfig.py")]
    print("building the config editor exe from HEAD (PyInstaller, about a minute)...")
    r = subprocess.run(cmd, cwd=gui_dir, capture_output=True, text=True)
    if r.returncode:
        sys.exit("PyInstaller failed:\n" + r.stderr[-3000:])
    return os.path.join(work, "dist", "PortalHubConfig")


def warn_if_working_tree_differs(paths):
    diff = git("status", "--porcelain", "--", *paths)
    if diff:
        print("NOTE: these working-tree files differ from HEAD; the zip uses HEAD's versions:\n" + diff)


def run_checks(stage, names):
    problems = []
    for d, _, files in os.walk(stage):
        for fn in files:
            full = os.path.join(d, fn)
            rel = os.path.relpath(full, stage).replace(os.sep, "/")
            if not allowed_path(rel):
                problems.append("not on the allowlist: " + rel)
            with open(full, "rb") as f:
                data = f.read()
            hit = find_names(data, names)
            if hit:
                problems.append("%s holds a forbidden name (%d)" % (rel, len(hit)))   # the names themselves are not printed on purpose
            if fn.endswith(".lua"):
                for p in dev_key_problems(data.decode("utf-8", errors="replace")):
                    problems.append(rel + ": " + p)
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--final", action="store_true", help="refuse to build while the GUI's Portal Hub Nexus URL is empty")
    ap.add_argument("--reuse-gui", action="store_true", help="use tools/PortalHubConfig/dist instead of building the exe")
    ap.add_argument("--worktree", action="store_true", help="TEST ONLY: read the working tree instead of HEAD")
    a = ap.parse_args()
    global WORKTREE
    WORKTREE = a.worktree

    head = git("rev-parse", "--short", "HEAD") + (" + WORKING TREE (test build, not for upload)" if WORKTREE else "")
    shipped = ["mod/PortalHub/Scripts", "tools/PortalHubConfig", "tools/release", "PortalHubConfig.bat", "LICENSE", "World Projects/Builds"]
    if not WORKTREE:
        warn_if_working_tree_differs(shipped)

    stage_root = os.path.join(OUT, "stage")
    stage = os.path.join(stage_root, TOP)
    if os.path.isdir(stage_root):
        shutil.rmtree(stage_root)
    os.makedirs(stage)
    tmp = tempfile.mkdtemp(prefix="cordona-release-")
    try:
        # the hub
        put(stage, HUB_DST + "main.lua", strip_dev_keys(committed("mod/PortalHub/Scripts/main.lua")))
        for fn in ("slots.lua", "manual_exits.lua", "config.lua"):
            put(stage, HUB_DST + fn, committed("mod/PortalHub/Scripts/" + fn))
        # the editor
        gui_dir = export_gui(tmp)
        url = read_nexus_url(gui_dir)
        if url is None:
            sys.exit("install_check.py at HEAD has no PORTAL_HUB_NEXUS_URL line")
        if not url:
            if a.final:
                sys.exit("--final: PORTAL_HUB_NEXUS_URL in tools/PortalHubConfig/install_check.py is empty; paste the Nexus page, commit, build again")
            print("WARNING: the GUI's Portal Hub Nexus URL is empty (TODO in install_check.py); fine for a test build, not for the upload")
        if a.reuse_gui:
            dist = os.path.join(ROOT, "tools", "PortalHubConfig", "dist", "PortalHubConfig")
            if not os.path.isfile(os.path.join(dist, "PortalHubConfig.exe")):
                sys.exit("no exe in " + dist)
            print("NOTE: --reuse-gui: the exe was built from the working tree, not checked against HEAD")
        else:
            dist = build_gui(gui_dir, tmp)
        shutil.copytree(dist, os.path.join(stage, "PortalHubConfig"))
        for d, dirs, files in os.walk(gui_dir):
            dirs[:] = [x for x in dirs if x not in ("tests", "dist", "build", "__pycache__")]
            for fn in files:
                rel = os.path.relpath(os.path.join(d, fn), gui_dir).replace(os.sep, "/")
                if not fn.endswith((".ps1", ".spec")) and fn != ".gitignore":
                    with open(os.path.join(d, fn), "rb") as f:
                        put(stage, "tools/PortalHubConfig/" + rel, f.read())
        put(stage, "PortalHubConfig.bat", committed("PortalHubConfig.bat"))
        # presets, teaser worlds, docs
        put(stage, "Presets/config-demo.lua", committed("tools/release/config-demo.lua"))
        for w in "ABCD":
            for ext in ("pak", "ucas", "utoc"):
                fn = "World%s_P.%s" % (w, ext)
                put(stage, TEASER_DST + fn, committed("World Projects/Builds/" + fn))
        put(stage, "README.md", committed("tools/release/README-player.md"))
        put(stage, "LICENSE.txt", committed("LICENSE"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    names = forbidden_names()
    problems = run_checks(stage, names)
    lua = [os.path.join(stage, HUB_DST, f) for f in ("main.lua", "slots.lua", "manual_exits.lua", "config.lua")]
    lua.append(os.path.join(stage, "Presets", "config-demo.lua"))
    if subprocess.run([sys.executable, os.path.join(ROOT, "tools", "dev", "lua_syntax_check.py")] + lua).returncode:
        problems.append("the staged Lua failed the syntax check")
    for t in TESTS_ON_PACKAGED:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "dev", "tests", t), lua[0]], capture_output=True, text=True)
        last = (r.stdout.strip().splitlines() or ["(no output)"])[-1]
        print("%s on the packaged main.lua: %s" % (t, last))
        if r.returncode:
            problems.append(t + " failed on the packaged main.lua")
    if problems:
        sys.exit("BUILD REFUSED:\n  " + "\n  ".join(problems))

    with open(lua[0], encoding="utf-8") as f:
        binds = key_binds(f.read())
    print("key binds shipped (checked against the game's default bindings):")
    for k in binds:
        label, what, game = KNOWN_BINDS[k]
        print("  %-9s %s | game default: %s" % (label, what, game))
    print("forbidden-name scan: %d name(s) checked, none found; External Mods %s" %
          (len(names), "read" if os.path.isdir(os.path.join(ROOT, "External Mods")) else "NOT FOUND (only the private name was checked)"))

    # file list (inside the zip and beside it), then the zip
    listing = []
    for d, _, files in os.walk(stage):
        for fn in files:
            full = os.path.join(d, fn)
            with open(full, "rb") as f:
                data = f.read()
            listing.append((os.path.relpath(full, stage).replace(os.sep, "/"), len(data), hashlib.sha1(data).hexdigest()))
    listing.sort()
    head_text = "Portal Hub %s, built from commit %s. Path, size in bytes, SHA-1.\n" % (VERSION, head)
    files_txt = head_text + "".join("%s\t%d\t%s\n" % row for row in listing)
    put(stage, "FILES.txt", files_txt.encode("utf-8"))
    name = "PortalHub-" + VERSION
    with open(os.path.join(OUT, name + "-files.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(files_txt)
    zpath = os.path.join(OUT, name + ".zip")
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, files in os.walk(stage):
            for fn in sorted(files):
                full = os.path.join(d, fn)
                z.write(full, os.path.relpath(full, stage_root).replace(os.sep, "/"))
    with open(zpath, "rb") as f:
        zdata = f.read()
    if find_names(zdata, names):
        sys.exit("BUILD REFUSED: the finished zip holds a forbidden name")
    print("%s: %d files, %.1f MB, SHA-1 %s (commit %s)" % (zpath, len(listing) + 1, len(zdata) / 1e6, hashlib.sha1(zdata).hexdigest(), head))


if __name__ == "__main__":
    main()
