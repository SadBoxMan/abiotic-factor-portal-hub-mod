r"""Builds the select beta zips (CRD-024) into Beta\ at the repo root (git-ignored: never commit the output).

    python tools\\beta\\build_beta.py run1          probe, worlds A-D, config editor, README (no Portal Hub)
    python tools\\beta\\build_beta.py full          the same plus the Portal Hub (DEV_KEYS = false in the packaged copy only)

Sources (the repo, except where noted):
    mod/CordonaProbe/Scripts/main.lua
    World Projects/Builds/World[A-D]_P.pak/.ucas/.utoc
    tools/PortalHubConfig/dist/PortalHubConfig/   (build it first with tools/PortalHubConfig/build_exe.bat)
    PortalHubConfig.bat
    mod/PortalHub/Scripts/main.lua, slots.lua, manual_exits.lua   (full only; copy the installed manual_exits.lua back first)
    tools/beta/config-beta.lua -> Mods/PortalHub/Scripts/config.lua   (full only; the tester starting config)
    tools/beta/README-tester.md -> README.md, LICENSE -> LICENSE.txt
Left out on purpose: the lab, PortalLogger, PortalPoC, the old PortalHubConfig.ps1, any third-party or private file.
"""
import hashlib
import os
import shutil
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "Beta")
VERSION = "2026-11-10"


def src(*parts):
    p = os.path.join(ROOT, *parts)
    if not os.path.exists(p):
        sys.exit("missing: " + p)
    return p


def copy(a, stage, rel):
    dst = os.path.join(stage, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(a, dst)


def packaged_hub_main(stage):
    """The repo's main.lua with DEV_KEYS switched off, in the staged copy only (the repo file is not touched)."""
    with open(src("mod", "PortalHub", "Scripts", "main.lua"), "rb") as f:
        b = f.read()
    old = b"local DEV_KEYS = true"
    if b.count(old) != 1:
        sys.exit("main.lua: expected exactly one 'local DEV_KEYS = true'")
    b = b.replace(old, b"local DEV_KEYS = false")
    dst = os.path.join(stage, "Mods", "PortalHub", "Scripts", "main.lua")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(b)


def build(kind):
    name = "CordonaBeta-%s-%s" % (kind, VERSION)
    stage = os.path.join(OUT, name)
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    os.makedirs(stage)

    copy(src("mod", "CordonaProbe", "Scripts", "main.lua"), stage, os.path.join("Mods", "CordonaProbe", "Scripts", "main.lua"))
    for w in "ABCD":
        for ext in ("pak", "ucas", "utoc"):
            fn = "World%s_P.%s" % (w, ext)
            copy(src("World Projects", "Builds", fn), stage, os.path.join("Paks", fn))
    gui = src("tools", "PortalHubConfig", "dist", "PortalHubConfig")
    shutil.copytree(gui, os.path.join(stage, "PortalHubConfig"))
    copy(src("PortalHubConfig.bat"), stage, "PortalHubConfig.bat")
    copy(src("tools", "beta", "README-tester.md"), stage, "README.md")
    copy(src("LICENSE"), stage, "LICENSE.txt")

    if kind == "full":
        packaged_hub_main(stage)
        for fn in ("slots.lua", "manual_exits.lua"):
            copy(src("mod", "PortalHub", "Scripts", fn), stage, os.path.join("Mods", "PortalHub", "Scripts", fn))
        copy(src("tools", "beta", "config-beta.lua"), stage, os.path.join("Mods", "PortalHub", "Scripts", "config.lua"))

    zpath = os.path.join(OUT, name + ".zip")
    if os.path.exists(zpath):
        os.remove(zpath)
    listing = []
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, files in os.walk(stage):
            for fn in sorted(files):
                full = os.path.join(d, fn)
                rel = os.path.relpath(full, OUT)
                z.write(full, rel)
                with open(full, "rb") as f:
                    listing.append((rel, os.path.getsize(full), hashlib.sha1(f.read()).hexdigest()[:12]))
    with open(os.path.join(OUT, name + "-files.txt"), "w", encoding="utf-8", newline="\n") as f:
        for rel, size, h in sorted(listing):
            f.write("%s\t%d\t%s\n" % (rel.replace(os.sep, "/"), size, h))
    print("%s: %d files, %.1f MB" % (zpath, len(listing), os.path.getsize(zpath) / 1e6))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("run1", "full"):
        sys.exit(__doc__)
    build(sys.argv[1])
