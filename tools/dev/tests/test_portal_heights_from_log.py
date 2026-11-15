# Checks tools/dev/portal_heights_from_log.py (CRD-041) on temp copies: the last LOOK HEIGHT line per look counts, empty cells are
# filled, equal ones left alone, typed ones never replaced without a yes (ask / --keep / --overwrite / no terminal), offsets recomputed,
# notes and extra rows kept, ASCII with no BOM and the sheet's own line endings; and the shipped sheet itself (32 looks, the 4 picks).
import os, sys, shutil, tempfile

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(S, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "dev"))
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
import portal_heights_from_log as ph
import hubdata

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("PASS  " if cond else "FAIL  ") + name + (("   -> " + str(detail)) if detail and not cond else ""))


SHEET = os.path.join(ROOT, "docs", "portal-heights.csv")
LOG = """[12:00:01] [Lua] [MaterialLab] ---- LOOK HEIGHTS (;): pad hub_B1, its own look Niagara_Portal_Dark, game default height 158.0 cm
[12:00:02] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Door | game default 158.0 cm | set 158.0 cm | offset +0.0 cm | pad hub_B1 (6/32)
[12:00:03] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Fog | game default 158.0 cm | set 158.0 cm | offset +0.0 cm | pad hub_B1 (7/32)
[12:00:04] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Fog | game default 158.0 cm | set 128.0 cm | offset -30.0 cm | pad hub_B1 (7/32)
[12:00:05] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Friendly_Red | game default 158.0 cm | set 98.0 cm | offset -60.0 cm | pad hub_B1 (19/32)
[12:00:06] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Garden | game default 138.3 cm | set 128.3 cm | offset -10.0 cm | pad H_Garden_Entrance (22/32)
[12:00:07] [Lua] [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Unknown | game default 158.0 cm | set 100.0 cm | offset -58.0 cm | pad hub_B1 (1/32)
[12:00:08] [Lua] [MaterialLab] ---- PORTAL HEIGHT (O/P): hub_A3 (Niagara_Portal_Tiny): effect at 117.5 cm above the pad (was 127.5, offset -10 cm)
"""

print("=== the shipped sheet")
raw = open(SHEET, "rb").read()
check("ASCII, no BOM", not raw.startswith(b"\xef\xbb\xbf") and all(b < 128 for b in raw))
rows, nl = ph.read_sheet(SHEET)
check("header", rows[0] == ph.HEADER, rows[0])
check("32 looks, DESIGN_NAMES order", [r[0] for r in rows[1:]] == hubdata.DESIGN_NAMES)
byname = {r[0]: r for r in rows[1:]}
check("game default 158 on every row", all(r[1] == "158" for r in rows[1:]))
check("LuciDin's 4 picks", [byname[n][2] for n in ("Niagara_Portal_Friendly_Red", "Niagara_Portal", "Niagara_Portal_Botanical_Red", "Niagara_Portal_Door")] == ["108", "118", "138", "158"])
check("pick offsets", [byname[n][3] for n in ("Niagara_Portal_Friendly_Red", "Niagara_Portal", "Niagara_Portal_Botanical_Red", "Niagara_Portal_Door")] == ["-50", "-40", "-20", "0"])
check("only the picks have heights", sum(1 for r in rows[1:] if r[2]) == 4)
# git stores the sheet with LF (core.autocrlf, no .gitattributes): a Windows checkout has CRLF, a zip or Linux checkout LF. Either is
# fine for Excel; the checks below run on a CRLF fixture built here, and on an LF one, so they pass on any checkout.
check("one line ending throughout", (b"\r\n" in raw) == (raw.count(b"\n") == raw.count(b"\r\n")))
raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")      # the CRLF fixture (what Excel writes)

tmp = tempfile.mkdtemp()
try:
    logp = os.path.join(tmp, "UE4SS.log")
    open(logp, "w", encoding="utf-8").write(LOG)

    print("=== log reading")
    found = ph.read_log(logp)
    check("last line per look counts (Fog 128)", found["Niagara_Portal_Fog"] == (158.0, 128.0), found)
    check("PORTAL HEIGHT lines ignored", "Niagara_Portal_Tiny" not in found)
    check("five looks found", len(found) == 5, found)

    def copy():
        p = os.path.join(tmp, "sheet.csv")
        open(p, "wb").write(raw)
        return p

    check("the CRLF fixture reads as CRLF", ph.read_sheet(copy())[1] == "\r\n")

    print("=== --keep (and no terminal): typed values stay")
    p = copy()
    rc = ph.main(["--log", logp, "--csv", p, "--keep"])
    rows, _ = ph.read_sheet(p)
    b = {r[0]: r for r in rows[1:]}
    check("exit 0", rc == 0)
    check("Fog filled 128, offset -30", b["Niagara_Portal_Fog"][2:4] == ["128", "-30"], b["Niagara_Portal_Fog"])
    check("Garden filled 128.3 against the sheet's 158: offset -29.7", b["Niagara_Portal_Garden"][2:4] == ["128.3", "-29.7"], b["Niagara_Portal_Garden"])
    check("Friendly Red kept at LuciDin's 108", b["Niagara_Portal_Friendly_Red"][2] == "108")
    check("Door the same, untouched", b["Niagara_Portal_Door"][2:4] == ["158", "0"])
    check("notes kept", b["Niagara_Portal_Door"][4] == "LuciDin's pick 14 Nov (CRD-039); oversized look")
    out = open(p, "rb").read()
    check("written ASCII, no BOM, CRLF kept", not out.startswith(b"\xef\xbb\xbf") and b"\r\n" in out and b"\r\r" not in out)
    before = open(p, "rb").read()
    ph.main(["--log", logp, "--csv", p, "--keep"])
    check("a second run changes nothing", open(p, "rb").read() == before)

    print("=== ask")
    p = copy()
    rows, nl = ph.read_sheet(p)
    asked = []
    ph.fill(rows, found, "ask", ask=lambda look, typed, logged: asked.append((look, typed, logged)) or False)
    check("asks only for the differing typed value", asked == [("Niagara_Portal_Friendly_Red", 108.0, 98.0)], asked)
    check("a no keeps it", {r[0]: r for r in rows[1:]}["Niagara_Portal_Friendly_Red"][2] == "108")
    rows, nl = ph.read_sheet(p)
    ph.fill(rows, found, "ask", ask=lambda *a: True)
    check("a yes replaces it, offset -60", {r[0]: r for r in rows[1:]}["Niagara_Portal_Friendly_Red"][2:4] == ["98", "-60"])
    p = copy()
    sys.stdin = open(os.devnull)                   # nobody answers: ask keeps
    ph.main(["--log", logp, "--csv", p])
    check("no answer: ask keeps typed values", {r[0]: r for r in ph.read_sheet(p)[0][1:]}["Niagara_Portal_Friendly_Red"][2] == "108")

    print("=== --overwrite, --dry-run, LuciDin's own edits")
    p = copy()
    ph.main(["--log", logp, "--csv", p, "--overwrite"])
    check("--overwrite replaces 108 with 98", {r[0]: r for r in ph.read_sheet(p)[0][1:]}["Niagara_Portal_Friendly_Red"][2] == "98")
    p = copy()
    ph.main(["--log", logp, "--csv", p, "--dry-run"])
    check("--dry-run writes nothing", open(p, "rb").read() == raw)
    p = os.path.join(tmp, "edited.csv")
    text = raw.decode("ascii").replace("Niagara_Portal_Fog,158,,,", "Niagara_Portal_Fog,158,140,,too low otherwise") + "my row,1,2,3,mine\r\n"
    open(p, "wb").write(b"\xef\xbb\xbf" + text.encode("ascii"))       # Excel "CSV UTF-8" save adds a BOM
    ph.main(["--log", logp, "--csv", p, "--keep"])
    out = open(p, "rb").read()
    b = {r[0]: r for r in ph.read_sheet(p)[0][1:]}
    check("his typed Fog 140 kept, offset filled -18, his note kept", b["Niagara_Portal_Fog"][2:] == ["140", "-18", "too low otherwise"], b["Niagara_Portal_Fog"])
    check("his extra row kept (its offset recomputed: 2 - 1)", b.get("my row") == ["my row", "1", "2", "1", "mine"], b.get("my row"))
    check("BOM dropped on write", not out.startswith(b"\xef\xbb\xbf"))
    p = os.path.join(tmp, "lf.csv")
    open(p, "wb").write(raw.replace(b"\r\n", b"\n"))
    ph.main(["--log", logp, "--csv", p, "--keep"])
    check("an LF sheet stays LF", b"\r" not in open(p, "rb").read())
    empty = os.path.join(tmp, "empty.log")
    open(empty, "w").write("nothing here\n")
    check("a log with no lines: exit 1, sheet untouched", ph.main(["--log", empty, "--csv", copy()]) == 1)
finally:
    shutil.rmtree(tmp)

failed = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(failed)))
sys.exit(1 if failed else 0)
