"""Turns the lab's stills run (CRD-046) into the config editor's preview pictures.

The lab's stills mode ([ -> stills, SCROLL LOCK x4) shoots every portal design with the game's own screenshot command and notes each
shot (design, time) in stills.txt next to the lab. This script pairs the game's screenshots with those notes by time, crops every
shot with the same 4:3 box, sizes it alike and writes one PNG per design into tools/PortalHubConfig/previews/, plus index.json.

    python tools/dev/make_previews.py                       # the last run, found in the installed lab; game screenshots folder
    python tools/dev/make_previews.py --check               # only list the pairing, write nothing
    python tools/dev/make_previews.py --box 0.25,0.05,0.5,0.9 --size 400    # own box (fractions), 400 x 300

Game assets (LuciDin, 15 Nov): the pictures show the game's own looks, rings, scenery and cube maps; he OK'd committing and shipping
all of them ("Commit all the shots ... 4:3"). Anything new that ships game assets needs his OK first.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
import hubdata  # noqa: E402

OUT_DIR = os.path.join(ROOT, "tools", "PortalHubConfig", "previews")
LAB_STILLS = os.path.join("AbioticFactor", "Binaries", "Win64", "ue4ss", "Mods", "PortalMaterialLab", "stills.txt")   # under the game folder, as install_check.REL_WIN64
SHOTS_DIR = os.path.join(os.environ.get("LOCALAPPDATA", ""), "AbioticFactor", "Saved", "Screenshots")
GAME_FILE = os.path.join(os.environ.get("APPDATA", ""), "PortalHubConfig", "game-path.txt")
GEO_SHAPES = ("Arch", "Gothic", "Square", "Door", "Round", "Oval")     # the lab's LK.GEO_SHAPES / LK.GEO_TYPES order
GEO_TYPES = ("Con", "Col", "Ren", "Pri")
# the game's ring materials on the mesh ring (the lab's LK.TINT_RINGS without the plain window; CRD-044's optional ring stills)
RINGS = ("M_Portal_Friendly_White", "M_Portal_Friendly", "M_Portal_Garden", "M_Portal_Torii", "M_Portal_Salem", "M_Portal_Shadowgate2",
         "M_Portal_Shadowgate_Blue", "M_Portal_Botanical_Green", "M_Portal_Botanical_Red", "M_WorldPortal_Warehouse", "M_Portal_Arch")
SIZE = 320      # picture width in pixels; the height follows the 4:3 shape (LuciDin, 15 Nov: "a 4:3 perspective")
ASPECT = (4, 3)
# designs whose shot shows nothing: no picture (the editor falls back to the base look's, CRD-044)
NO_PICTURE = {"M_Portal_Arch": "the Night Realm arch's ring material draws nothing on the flat mesh ring (first run, 15 Nov)"}
SKEW = 1.0      # seconds: the lab's os.time() is whole seconds; a file may carry a time a little before the note's


def design_keys():
    """Every design in the lab's run order: the game's 32 looks (the editor's DESIGN_NAMES), the 24 Geo rings, the 11 game rings."""
    return list(hubdata.DESIGN_NAMES) + ["Geo_%s_%s" % (s, t) for s in GEO_SHAPES for t in GEO_TYPES] + list(RINGS)


def kind_of(key):
    if key.startswith("Geo_"):
        return "geo"
    return "ring" if key.startswith("M_") else "game"


def licence_of(key):
    return "own ring on game scenery" if kind_of(key) == "geo" else "game screenshot"


def find_stills():
    """stills.txt in the installed lab: the GUI's remembered game folder, else the Steam libraries."""
    hints = []
    try:
        with open(GAME_FILE, encoding="utf-8") as f:
            hints.append(f.read().strip())
    except OSError:
        pass
    try:
        import install_check
        game = install_check.find_game(hints=hints)
    except Exception:
        game = hints[0] if hints else None
    return os.path.join(game, LAB_STILLS) if game else None


def read_run(path, run=-1):
    """The shot and skip notes of one run in stills.txt (the last by default): a list of dicts (i, key, kind, t, skip), plus the run's
    start time. The test shot (kind 'test') is left out."""
    runs = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            parts = raw.rstrip("\r\n").split("\t")
            if parts[0] == "run" and len(parts) >= 2:
                runs.append({"t": int(parts[1]), "entries": []})
            elif parts[0] in ("shot", "skip") and len(parts) >= 5 and runs:
                if parts[3] == "test":
                    continue
                runs[-1]["entries"].append({"i": int(parts[1]), "key": parts[2], "kind": parts[3], "t": int(parts[4]),
                                            "skip": parts[0] == "skip"})
    if not runs:
        raise SystemExit("no run in %s (the lab writes one on the 4th SCROLL LOCK in stills mode)" % path)
    return runs[run]["entries"], runs[run]["t"]


def list_shots(folder, since):
    """PNG screenshots under folder made at or after since (seconds), oldest first: [(mtime, path)]."""
    found = []
    for p in glob.glob(os.path.join(folder, "**", "*.png"), recursive=True):
        m = os.path.getmtime(p)
        if m >= since - SKEW:
            found.append((m, p))
    return sorted(found)


def pair(entries, shots):
    """Gives each shot to the last note made at or before its time (notes are >= 3 s apart). Returns ({key: path}, problems)."""
    taken = [e for e in entries if not e["skip"]]
    got, problems = {}, []
    for m, p in shots:
        owner = None
        for e in taken:
            if e["t"] <= m + SKEW:
                owner = e
        if owner is None:
            continue
        if owner["key"] in got:
            problems.append("%s: more than one screenshot (kept %s, not %s)" % (owner["key"], os.path.basename(got[owner["key"]]), os.path.basename(p)))
            continue
        got[owner["key"]] = p
    for e in taken:
        if e["key"] not in got:
            problems.append("%s: no screenshot found" % e["key"])
    for e in entries:
        if e["skip"]:
            problems.append("%s: skipped in the game (could not be put on)" % e["key"])
    return got, problems


def crop_box(width, height, box=None):
    """Pixel box (left, top, right, bottom): the given fractions of the frame, or by default the centred 4:3 box of the full height
    (a 16:9 shot loses a little at each side; nothing is cut off the top or bottom, so tall portals stay whole)."""
    if box:
        x, y, w, h = box
        return (round(x * width), round(y * height), round((x + w) * width), round((y + h) * height))
    aw, ah = ASPECT
    w, h = min(width, height * aw // ah), min(height, width * ah // aw)
    left, top = (width - w) // 2, (height - h) // 2
    return (left, top, left + w, top + h)


def out_size(size=SIZE):
    return (size, size * ASPECT[1] // ASPECT[0])


def make_picture(src, dst, size=SIZE, box=None):
    from PIL import Image
    with Image.open(src) as im:
        im = im.convert("RGB")
        out = im.crop(crop_box(im.width, im.height, box)).resize(out_size(size), Image.LANCZOS)
        out.save(dst, "PNG", optimize=True)


def write_index(out_dir, size=SIZE):
    """index.json: every design that has a picture in out_dir, in the lab's order."""
    designs = []
    for key in design_keys():
        name = key + ".png"
        if os.path.isfile(os.path.join(out_dir, name)):
            designs.append({"key": key, "file": name, "kind": kind_of(key), "licence": licence_of(key)})
    index = {"version": 1, "size": list(out_size(size)), "designs": designs,
             "note": "Screenshots from the game (its looks, rings, scenery and cube maps; Geo = our own ring on that scenery), "
                     "committed and shipped with LuciDin's OK (15 Nov 2026). Made by tools/dev/make_previews.py from the lab's stills run (CRD-046)."}
    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, indent=1)
        f.write("\n")
    return designs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stills", help="stills.txt (default: the installed lab's)")
    ap.add_argument("--shots", default=SHOTS_DIR, help="the game's screenshot folder (default: %(default)s)")
    ap.add_argument("--out", default=OUT_DIR, help="where the previews go (default: tools/PortalHubConfig/previews)")
    ap.add_argument("--size", type=int, default=SIZE, help="picture width in pixels, 4:3 (default: %(default)s)")
    ap.add_argument("--box", help="crop box as fractions of the frame: left,top,width,height (default: the centred 4:3 box)")
    ap.add_argument("--run", type=int, default=-1, help="which run in stills.txt (default: -1, the last)")
    ap.add_argument("--check", action="store_true", help="list the pairing only, write nothing")
    a = ap.parse_args(argv)
    stills = a.stills or find_stills()
    if not stills or not os.path.isfile(stills):
        print("stills.txt not found (%s); give it with --stills" % stills)
        return 2
    box = tuple(float(v) for v in a.box.split(",")) if a.box else None
    if box and (len(box) != 4 or min(box) < 0 or box[0] + box[2] > 1 or box[1] + box[3] > 1):
        print("--box needs four fractions left,top,width,height inside the frame")
        return 2
    entries, started = read_run(stills, a.run)
    shots = list_shots(a.shots, started)
    got, problems = pair(entries, shots)
    unknown = sorted(set(got) - set(design_keys()))
    print("run with %d notes, %d screenshots since it started, %d paired" % (len(entries), len(shots), len(got)))
    for key in design_keys():
        if key in got:
            print("  %-34s <- %s" % (key, os.path.basename(got[key])))
    for p in problems:
        print("  ! " + p)
    for k in unknown:
        print("  ! %s: not a known design (left out)" % k)
    if a.check:
        return 0 if not problems else 1
    os.makedirs(a.out, exist_ok=True)
    written = 0
    for key, path in got.items():
        if key in unknown:
            continue
        if key in NO_PICTURE:
            print("  - %s: no picture (%s)" % (key, NO_PICTURE[key]))
            stale = os.path.join(a.out, key + ".png")
            if os.path.isfile(stale):
                os.remove(stale)
            continue
        make_picture(path, os.path.join(a.out, key + ".png"), a.size, box)
        written += 1
    designs = write_index(a.out, a.size)
    print("wrote %d picture(s) and index.json (%d designs listed) in %s" % (written, len(designs), a.out))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
