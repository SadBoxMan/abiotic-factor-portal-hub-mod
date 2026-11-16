# Checks tools/dev/make_previews.py (CRD-046) on a made-up stills run: notes in stills.txt paired with screenshots by time (the last
# run only, the test shot and older screenshots left out, a skipped design and a missing shot reported), every picture cropped with
# the same 4:3 box and sized alike (320 x 240), file names = design keys, index.json with the licence per design, --check writes
# nothing, a design with a known-empty shot gets no picture.
import io
import json
import os
import sys
import tempfile
import contextlib

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, ".."))
import make_previews as mp  # noqa: E402
from PIL import Image  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


def shot(folder, name, when, colour=(200, 30, 30), size=(1920, 1080)):
    """A frame: blue all over, the design's colour in the centred square's middle third."""
    im = Image.new("RGB", size, (20, 20, 200))
    w, h = size
    im.paste(colour, (w // 2 - h // 6, h // 3, w // 2 + h // 6, 2 * h // 3))
    p = os.path.join(folder, name)
    im.save(p)
    os.utime(p, (when, when))
    return p


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mp.main(argv)
    return code, buf.getvalue()


print("=== names")
keys = mp.design_keys()
check("67 designs, no repeats", len(keys) == 67 and len(set(keys)) == 67, len(keys))
check("game looks first, by their DESIGN_NAMES key", keys[0] == "Niagara_Portal" and keys[31] == "Niagara_Portal_Torii", keys[:2])
check("then Geo_<Shape>_<Type>, shape by shape", keys[32:36] == ["Geo_Arch_Con", "Geo_Arch_Col", "Geo_Arch_Ren", "Geo_Arch_Pri"] and keys[55] == "Geo_Oval_Pri", keys[32:36])
check("then the game rings M_<name> (CRD-044's optional stills)", keys[56] == "M_Portal_Friendly_White" and keys[-1] == "M_Portal_Arch", keys[56:])
check("licence notes: game looks and rings are game screenshots, Geo our ring on game scenery", mp.licence_of("Geo_Door_Pri") == "own ring on game scenery"
      and mp.licence_of("Niagara_Portal_Rift") == "game screenshot" and mp.licence_of("M_Portal_Torii") == "game screenshot" and mp.kind_of("M_Portal_Torii") == "ring")
check("default crop: the centred 4:3 box of the full height (LuciDin: 4:3)", mp.crop_box(1920, 1080) == (240, 0, 1680, 1080), mp.crop_box(1920, 1080))
check("... also from a 4:3 or a narrow frame", mp.crop_box(1600, 1200) == (0, 0, 1600, 1200) and mp.crop_box(1000, 1000) == (0, 125, 1000, 875), mp.crop_box(1000, 1000))
check("pictures 320 x 240 by default", mp.out_size() == (320, 240))
check("M_Portal_Arch gets no picture (draws nothing on the flat ring)", "M_Portal_Arch" in mp.NO_PICTURE)
check("crop box as fractions", mp.crop_box(1000, 500, (0.25, 0.1, 0.5, 0.8)) == (250, 50, 750, 450), mp.crop_box(1000, 500, (0.25, 0.1, 0.5, 0.8)))

tmp = tempfile.mkdtemp(prefix="crd046-")
shots = os.path.join(tmp, "Screenshots", "Windows")
os.makedirs(shots)
out = os.path.join(tmp, "previews")
T = 1763250000
stills = os.path.join(tmp, "stills.txt")
with open(stills, "w", encoding="utf-8", newline="\n") as f:
    f.write("run\t%d\t2026-11-15 20:00:00\thub_B1\t56\n" % (T - 1000))           # an older run: left out
    f.write("shot\t1\tNiagara_Portal\tgame\t%d\n" % (T - 997))
    f.write("shot\t0\ttest\ttest\t%d\n" % (T - 20))                               # the test shot: left out
    f.write("run\t%d\t2026-11-15 20:16:40\thub_B1\t56\n" % T)
    f.write("shot\t1\tNiagara_Portal\tgame\t%d\n" % (T + 3))
    f.write("shot\t2\tNiagara_Portal_Blueverse\tgame\t%d\n" % (T + 6))
    f.write("skip\t3\tNiagara_Portal_Botanical_Green\tgame\t%d\n" % (T + 7))
    f.write("shot\t4\tGeo_Arch_Con\tgeo\t%d\n" % (T + 10))
    f.write("shot\t5\tGeo_Door_Pri\tgeo\t%d\n" % (T + 13))                       # its screenshot never came
shot(shots, "ScreenShot00000.png", T - 996)                                      # the older run's: before this run, left out
shot(shots, "ScreenShot00001.png", T - 19)                                       # the test shot's: left out
shot(shots, "ScreenShot00002.png", T + 3.4, (200, 30, 30))
shot(shots, "ScreenShot00003.png", T + 6.2, (30, 200, 30), size=(2560, 1440))   # another window size: sized alike anyway
shot(shots, "ScreenShot00004.png", T + 10.1, (230, 230, 30))

import install_check  # noqa: E402
check("the installed lab's stills.txt is under the game folder's AbioticFactor/Binaries/Win64 (as the GUI's install check)",
      mp.LAB_STILLS.startswith(os.path.join(install_check.REL_WIN64, "ue4ss", "Mods", "PortalMaterialLab")), mp.LAB_STILLS)

print("=== --check")
code, text = run(["--stills", stills, "--shots", os.path.join(tmp, "Screenshots"), "--out", out, "--check"])
check("--check writes nothing", not os.path.exists(out))
check("--check lists the pairing", "Niagara_Portal                     <- ScreenShot00002.png" in text and "Geo_Arch_Con" in text, text)
check("reports the missing shot and the skipped design (exit 1)", code == 1 and "Geo_Door_Pri: no screenshot found" in text
      and "Niagara_Portal_Botanical_Green: skipped in the game" in text, text)

print("=== making the previews")
code, text = run(["--stills", stills, "--shots", os.path.join(tmp, "Screenshots"), "--out", out])
made = sorted(n for n in os.listdir(out) if n.endswith(".png"))
check("one PNG per paired design, named by its key", made == ["Geo_Arch_Con.png", "Niagara_Portal.png", "Niagara_Portal_Blueverse.png"], made)
sizes = {n: Image.open(os.path.join(out, n)).size for n in made}
check("all 320 x 240, whatever the window size", set(sizes.values()) == {(320, 240)}, sizes)
mid = Image.open(os.path.join(out, "Niagara_Portal_Blueverse.png")).convert("RGB").getpixel((160, 120))
corner = Image.open(os.path.join(out, "Niagara_Portal_Blueverse.png")).convert("RGB").getpixel((5, 5))
check("the same centred crop: the design in the middle, background at the corner", mid[1] > 150 and corner[2] > 150, (mid, corner))
check("each design got its own frame (yellow for Geo_Arch_Con)", Image.open(os.path.join(out, "Geo_Arch_Con.png")).convert("RGB").getpixel((160, 120))[0] > 200)
idx = json.load(open(os.path.join(out, "index.json"), encoding="utf-8"))
check("index lists the pictures in the lab's order", [d["key"] for d in idx["designs"]] == ["Niagara_Portal", "Niagara_Portal_Blueverse", "Geo_Arch_Con"], idx["designs"])
check("index: kind and licence note per design", idx["designs"][0] == {"key": "Niagara_Portal", "file": "Niagara_Portal.png", "kind": "game",
      "licence": "game screenshot"} and idx["designs"][2]["licence"] == "own ring on game scenery", idx["designs"])
check("index size and version", idx["size"] == [320, 240] and idx["version"] == 1)
raw = open(os.path.join(out, "index.json"), "rb").read()
check("index.json: no BOM, LF only", not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw)
check("exit 1 while something is missing", code == 1)

print("=== a later partial reshoot keeps the earlier pictures")
with open(stills, "a", encoding="utf-8", newline="\n") as f:
    f.write("run\t%d\t2026-11-15 20:30:00\thub_B1\t56\n" % (T + 100))
    f.write("shot\t56\tGeo_Door_Pri\tgeo\t%d\n" % (T + 103))
shot(shots, "ScreenShot00005.png", T + 103.5, (250, 250, 250))
code, text = run(["--stills", stills, "--shots", os.path.join(tmp, "Screenshots"), "--out", out, "--size", "128"])
idx = json.load(open(os.path.join(out, "index.json"), encoding="utf-8"))
check("the reshoot adds Geo_Door_Pri and the index keeps the earlier ones", [d["key"] for d in idx["designs"]] ==
      ["Niagara_Portal", "Niagara_Portal_Blueverse", "Geo_Arch_Con", "Geo_Door_Pri"] and code == 0, (code, text))
check("--size 128 = 128 x 96", Image.open(os.path.join(out, "Geo_Door_Pri.png")).size == (128, 96))
with open(stills, "a", encoding="utf-8", newline="\n") as f:
    f.write("run\t%d\t2026-11-15 20:40:00\thub_B1\t56\n" % (T + 200))
    f.write("shot\t67\tM_Portal_Arch\tring\t%d\n" % (T + 203))
shot(shots, "ScreenShot00006.png", T + 203.5)
open(os.path.join(out, "M_Portal_Arch.png"), "wb").close()   # a stale one from an earlier run
code, text = run(["--stills", stills, "--shots", os.path.join(tmp, "Screenshots"), "--out", out])
check("a known-empty design: no picture, an old one removed, said why", not os.path.exists(os.path.join(out, "M_Portal_Arch.png"))
      and "M_Portal_Arch: no picture" in text and "M_Portal_Arch" not in open(os.path.join(out, "index.json"), encoding="utf-8").read(), text)
code, text = run(["--stills", stills, "--shots", os.path.join(tmp, "Screenshots"), "--out", out, "--box", "0.5,0.5,0.6,0.1"])
check("a box outside the frame is refused", code == 2 and "--box" in text, text)
code, text = run(["--stills", os.path.join(tmp, "none.txt"), "--out", out])
check("no stills.txt: said, exit 2", code == 2 and "not found" in text, text)

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
