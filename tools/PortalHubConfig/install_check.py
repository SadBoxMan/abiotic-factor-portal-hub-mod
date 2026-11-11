"""Checks that the Portal Hub is installed: the game, UE4SS (and how new it is), the PortalHub mod's files, and mods.txt.

Read only: it never writes, moves, installs or downloads anything, and never touches UE4SS's files.
No Tkinter here, so the tests can drive it with mock install folders.

    report = check_install(find_game())      # find_game() looks through the Steam libraries
    report.state                              # "ok", "warn" (outdated / disabled / unknown version), "missing", "nogame"
"""
from __future__ import annotations

import os
import re
import struct

GAME_EXE = "AbioticFactor-Win64-Shipping.exe"
REL_WIN64 = os.path.join("AbioticFactor", "Binaries", "Win64")          # under the game folder (steamapps\common\AbioticFactor)
HUB = "PortalHub"
HUB_SCRIPTS = ("main.lua", "config.lua", "manual_exits.lua", "slots.lua")
NEXUS_UE4SS = "UE4SS for Abiotic Factor (Nexus Mods), 1.25.0 or later"
UE4SS_NEXUS_URL = "https://www.nexusmods.com/abioticfactor/mods/35"
# TODO(CRD-015, LuciDin): paste the Portal Hub's own Nexus page here once it exists, e.g.
#   PORTAL_HUB_NEXUS_URL = "https://www.nexusmods.com/abioticfactor/mods/123"
# then rebuild the exe (build_exe.bat, or tools/release/build_release.py builds it). Empty = the steps say "search Nexus Mods".
PORTAL_HUB_NEXUS_URL = ""
# UE4SS loads through a proxy DLL beside the game's exe; the Abiotic Factor build uses dwmapi.dll.
PROXIES = ("dwmapi.dll", "xinput1_3.dll", "dxgi.dll", "d3d11.dll", "version.dll", "winmm.dll")

# What we know of UE4SS builds (CRD-026). Both call themselves v3.0.1, so the git hash and the build time tell them apart.
RECOMMENDED_SHA = "d4aebbf0"                     # v3.0.1-1212-gd4aebbf0 = Nexus 1.25.0, our mods pass on it
RECOMMENDED_BUILT = 1793882343                   # its UE4SS.dll link time (5 November 2026, UTC)
OLD_SHAS = {"c838a8ac": "the July 2026 build"}  # the build before; "Ref was not function" was seen on it
RECOMMENDED_TEXT = "v3.0.1-1212 (Nexus 1.25.0)"
def portal_hub_page():
    """Where to get the Portal Hub, for the install steps: its Nexus page, or a search hint while the URL is not set."""
    return "its Nexus Mods page: " + PORTAL_HUB_NEXUS_URL if PORTAL_HUB_NEXUS_URL else "Nexus Mods (search for \"Portal Hub\" under Abiotic Factor)"


LOG_RX = re.compile(r"UE4SS - v(\d+)\.(\d+)\.(\d+)([^\r\n]*?) - Git SHA #([0-9a-fA-F]+)")


# ------------------------------------------------------------------ finding the game
def steam_roots():
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            roots.append(winreg.QueryValueEx(k, "SteamPath")[0].replace("/", "\\"))
    except (OSError, ImportError):
        pass
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        if os.environ.get(env):
            roots.append(os.path.join(os.environ[env], "Steam"))
    return roots


def steam_libraries(roots=None):
    """Every Steam library folder: the Steam folders themselves plus the paths in their libraryfolders.vdf."""
    libs = []
    for steam in steam_roots() if roots is None else roots:
        if not os.path.isdir(steam):
            continue
        libs.append(steam)
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        if os.path.exists(vdf):
            try:
                with open(vdf, encoding="utf-8", errors="replace") as f:
                    libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', f.read())]
            except OSError:
                pass
    seen = {}
    for p in libs:
        seen.setdefault(os.path.normcase(os.path.normpath(p)), os.path.normpath(p))
    return list(seen.values())


def is_game_folder(path):
    return bool(path) and os.path.isdir(os.path.join(path, REL_WIN64))


def game_folder_from(path):
    """The game folder (...\\steamapps\\common\\AbioticFactor) for a folder a player picked anywhere near it:
    the game folder itself, any folder inside it (Binaries, Win64, ue4ss, Mods, Scripts...), a Steam library or steamapps.
    None if it isn't one."""
    if not path:
        return None
    p = os.path.normpath(os.path.abspath(path))
    if os.path.isfile(p):
        p = os.path.dirname(p)
    for below in ("", os.path.join("common", "AbioticFactor"), os.path.join("steamapps", "common", "AbioticFactor")):
        cand = os.path.join(p, below) if below else p
        if is_game_folder(cand):
            return os.path.normpath(cand)
    d = p
    for _ in range(9):                               # up from ...\Mods\PortalHub\Scripts at most
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
        if is_game_folder(d):
            return d
    return None


def find_game(libraries=None, hints=()):
    """The first game folder among hints (paths tried first: a remembered folder, the config being edited, this program's
    folder) and then the Steam libraries. None if there is none."""
    for h in hints:
        g = game_folder_from(h)
        if g:
            return g
    for lib in steam_libraries() if libraries is None else libraries:
        cand = os.path.join(lib, "steamapps", "common", "AbioticFactor")
        if is_game_folder(cand):
            return os.path.normpath(cand)
    return None


# ------------------------------------------------------------------ UE4SS version
def pe_build_time(path):
    """The link time stamp in a DLL's PE header (seconds since 1970), or None."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        if head[:2] != b"MZ":
            return None
        off = struct.unpack_from("<I", head, 0x3C)[0]
        if head[off:off + 4] != b"PE\0\0":
            return None
        return struct.unpack_from("<I", head, off + 8)[0]
    except (OSError, struct.error):
        return None


def dll_product_version(path):
    """The ProductVersion string of a DLL's version resource (UE4SS puts its git hash there), or None. Windows only."""
    try:
        import ctypes
        from ctypes import wintypes
        ver = ctypes.WinDLL("version")
        size = ver.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not ver.GetFileVersionInfoW(path, 0, size, buf):
            return None
        ptr, n = ctypes.c_void_p(), wintypes.UINT()
        if not ver.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(n)) or n.value < 4:
            return None
        lang, cp = struct.unpack("<HH", ctypes.string_at(ptr.value, 4))
        key = f"\\StringFileInfo\\{lang:04x}{cp:04x}\\ProductVersion"
        if not ver.VerQueryValueW(buf, key, ctypes.byref(ptr), ctypes.byref(n)) or not n.value:
            return None
        return ctypes.wstring_at(ptr.value, n.value).rstrip("\0").strip() or None
    except (OSError, AttributeError, ValueError):
        return None


def log_version(ue4ss_dir, dll):
    """(version tuple, extra text, git hash) from the last UE4SS.log, if the log was written after the DLL was installed."""
    log = os.path.join(ue4ss_dir, "UE4SS.log")
    try:
        if os.path.getmtime(log) < os.path.getmtime(dll):
            return None                              # the log is from before this UE4SS.dll was put in: it may name the old one
        with open(log, encoding="utf-8", errors="replace") as f:
            head = f.read(4000)
    except OSError:
        return None
    m = LOG_RX.search(head)
    if not m:
        return None
    return (int(m[1]), int(m[2]), int(m[3])), m[4].strip(), m[5].lower()[:8]


def ue4ss_version(ue4ss_dir, dll):
    """{text, sha, built, state, why}: state "ok", "outdated" or "unknown"."""
    sha = None
    pv = dll_product_version(dll)
    if pv and re.fullmatch(r"[0-9a-fA-F]{7,40}", pv):
        sha = pv.lower()[:8]
    lv = log_version(ue4ss_dir, dll)
    if lv and not sha:
        sha = lv[2]
    built = pe_build_time(dll)
    text = ("v" + ".".join(map(str, lv[0])) if lv else "v3.x") + (f" ({sha})" if sha else "")
    out = dict(text=text, sha=sha, built=built, state="unknown", why="")
    if lv and lv[0] < (3, 0, 1):
        out.update(state="outdated", why=f"UE4SS {text} is older than {RECOMMENDED_TEXT}.")
    elif sha == RECOMMENDED_SHA or (lv and lv[0] > (3, 0, 1)):
        out.update(state="ok")
    elif sha in OLD_SHAS:
        out.update(state="outdated", why=f"UE4SS {text} is {OLD_SHAS[sha]}, older than {RECOMMENDED_TEXT}.")
    elif built:
        if built >= RECOMMENDED_BUILT:
            out.update(state="ok")
        else:
            out.update(state="outdated", why=f"UE4SS {text} was built before {RECOMMENDED_TEXT}.")
    else:
        out.update(why="Couldn't tell which UE4SS this is (no version in UE4SS.dll and no fresh UE4SS.log).")
    return out


# ------------------------------------------------------------------ mods.txt
def read_mods_txt(path):
    """{lower-case mod name: (name as written, on)} from a UE4SS mods.txt; None if it can't be read."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return None
    out = {}
    for line in lines:
        line = line.split(";", 1)[0].strip()
        if ":" not in line:
            continue
        name, val = (s.strip() for s in line.rsplit(":", 1))
        if name:
            out[name.lower()] = (name, val == "1")
    return out


def read_mods_json(path):
    """{lower-case mod name: on} from UE4SS's mods.json, or {} (it is optional)."""
    import json
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        return {str(d.get("mod_name", "")).lower(): bool(d.get("mod_enabled")) for d in data if isinstance(d, dict)}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


# ------------------------------------------------------------------ the check
class Report:
    """What check_install found. state: "ok", "warn", "missing" or "nogame". headline: one line; todo: what to do, in order."""

    def __init__(self, game):
        self.game = game
        self.win64 = os.path.join(game, REL_WIN64) if game else None
        self.ue4ss_dir = None
        self.ue4ss = None                 # the version dict, or None if UE4SS is missing
        self.proxy = None
        self.hub_dir = None
        self.scripts_missing = list(HUB_SCRIPTS)
        self.mods_txt = None
        self.enabled = None               # "on", "off", "absent" (not in mods.txt), or None (mods.txt missing)
        self.enabled_by = ""
        self.state = "nogame"
        self.headline = ""
        self.todo = []

    @property
    def config_path(self):
        if self.hub_dir and "config.lua" not in self.scripts_missing:
            return os.path.join(self.hub_dir, "Scripts", "config.lua")
        return None

    @property
    def hub_installed(self):
        """The hub's files are all there, so its config may be edited (it may still be switched off or on an old UE4SS)."""
        return self.state in ("ok", "warn")

    def text(self):
        return "  ".join([self.headline] + self.todo)


def check_install(game):
    r = Report(game)
    if not is_game_folder(game):
        r.game = r.win64 = None
        r.headline = "Abiotic Factor not found."
        r.todo = ["Click PICK GAME FOLDER and choose the game's folder (in your Steam library: steamapps\\common\\AbioticFactor)."]
        return r

    missing, warn = [], []
    # UE4SS: 3.x keeps its files in Win64\ue4ss; 2.x put UE4SS.dll and Mods straight into Win64.
    new_dir, old_dll = os.path.join(r.win64, "ue4ss"), os.path.join(r.win64, "UE4SS.dll")
    if os.path.exists(os.path.join(new_dir, "UE4SS.dll")):
        r.ue4ss_dir = new_dir
        r.ue4ss = ue4ss_version(new_dir, os.path.join(new_dir, "UE4SS.dll"))
    elif os.path.exists(old_dll):
        r.ue4ss_dir = r.win64
        r.ue4ss = dict(text="v2.x or older", sha=None, built=pe_build_time(old_dll), state="outdated",
                       why=f"UE4SS is an old version (its files sit straight in Win64); {RECOMMENDED_TEXT} is needed.")
    else:
        r.ue4ss_dir = new_dir if os.path.isdir(new_dir) else None
        missing.append("UE4SS")
    if r.ue4ss:
        r.proxy = next((p for p in PROXIES if os.path.exists(os.path.join(r.win64, p))), None)
        if not r.proxy:
            missing.append("UE4SS's loader (dwmapi.dll beside the game's exe)")
        if r.ue4ss["state"] != "ok":
            warn.append(r.ue4ss["why"])

    # the hub
    mods = os.path.join(r.ue4ss_dir, "Mods") if r.ue4ss_dir else None
    if mods and os.path.isdir(os.path.join(mods, HUB)):
        r.hub_dir = os.path.join(mods, HUB)
        scripts = os.path.join(r.hub_dir, "Scripts")
        r.scripts_missing = [s for s in HUB_SCRIPTS if not os.path.isfile(os.path.join(scripts, s))]
        if r.scripts_missing:
            missing.append("PortalHub's " + ", ".join(r.scripts_missing))
    else:
        missing.append("the PortalHub mod")

    # mods.txt (an enabled.txt in the mod's folder switches it on too)
    if mods:
        r.mods_txt = os.path.join(mods, "mods.txt")
        listed = read_mods_txt(r.mods_txt)
        via_json = read_mods_json(os.path.join(mods, "mods.json")).get(HUB.lower())
        has_enabled_txt = bool(r.hub_dir) and os.path.isfile(os.path.join(r.hub_dir, "enabled.txt"))
        if listed is None:
            r.enabled = None
        elif HUB.lower() in listed:
            r.enabled = "on" if listed[HUB.lower()][1] else "off"
        else:
            r.enabled = "absent"
        if r.enabled != "on" and (has_enabled_txt or via_json):
            r.enabled, r.enabled_by = "on", ("enabled.txt" if has_enabled_txt else "mods.json")
        elif r.enabled == "on":
            r.enabled_by = "mods.txt"

    # verdict
    if missing:
        r.state = "missing"
        r.headline = "Portal Hub is not fully installed: missing " + "; ".join(missing) + "."
        if "UE4SS" in missing or any(m.startswith("UE4SS's loader") for m in missing):
            r.todo.append(f"Install {NEXUS_UE4SS} into the game's Binaries\\Win64 folder: {UE4SS_NEXUS_URL}")
        if any("PortalHub" in m for m in missing):
            r.todo.append("Install the Portal Hub mod from " + portal_hub_page() + " (its PortalHub folder goes in Win64\\ue4ss\\Mods).")
        r.todo.append("Then click RE-CHECK. Nothing is saved until the hub is installed.")
        return r

    if r.enabled != "on":
        where = "mods.txt" if r.enabled is not None else "mods.txt (it is missing)"
        warn.append({"off": "PortalHub is switched off in mods.txt.",
                     "absent": "PortalHub is not listed in mods.txt.",
                     None: "UE4SS has no mods.txt."}[r.enabled])
        r.todo.append(f"Open Win64\\ue4ss\\Mods\\{where} and set the line  PortalHub : 1  (above the Keybinds line).")
    if r.ue4ss["state"] == "outdated":
        r.todo.append(f"Update UE4SS: install {NEXUS_UE4SS}: {UE4SS_NEXUS_URL}")
    elif r.ue4ss["state"] == "unknown":
        r.todo.append(f"If the hub misbehaves, install {NEXUS_UE4SS}.")
    if warn:
        r.state = "warn"
        r.headline = "Portal Hub is installed, but: " + " ".join(warn)
    else:
        r.state = "ok"
        r.headline = f"Portal Hub is installed and switched on. UE4SS {r.ue4ss['text']}."
    return r
