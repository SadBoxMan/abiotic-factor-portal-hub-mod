"""Fill docs/portal-heights.csv from the lab's LOOK HEIGHT lines in UE4SS.log (CRD-041).

The lab's ; key logs one line per height change, for example
  [MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Door | game default 158.0 cm | set 148.0 cm | offset -10.0 cm | pad hub_B4 (6/32)
The LAST line per look counts. For each look in the log:
  - an empty "LuciDin's height cm" cell is filled;
  - a cell that already holds the same height is left alone;
  - a cell that holds a different height (one LuciDin typed, or an earlier run) is NEVER overwritten without a yes:
    the script asks per look, or keeps them all with --keep (the default when it cannot ask), or replaces them with --overwrite.
The offset column is recomputed for every row with a height (height - game default). Empty game default cells are filled from the
log. Other columns and rows (notes, extra rows) are kept. Writes ASCII, no BOM, the sheet's own line endings.

  python tools/dev/portal_heights_from_log.py                 (default log: the beta install's UE4SS.log)
  python tools/dev/portal_heights_from_log.py --log PATH --csv PATH [--keep | --overwrite] [--dry-run]
"""
import argparse, csv, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "portal-heights.csv"))
DEFAULT_LOG = os.path.join(os.environ.get("USERPROFILE", ""), "Games", "Steam Library", "steamapps", "common", "AbioticFactor",
                           "AbioticFactor", "Binaries", "Win64", "ue4ss", "UE4SS.log")
LINE = re.compile(r"---- LOOK HEIGHT: (\w+) \| game default (-?[\d.]+) cm \| set (-?[\d.]+) cm")
HEADER = ["look", "game default cm", "LuciDin's height cm", "offset cm", "notes"]


def num(text):
    """'158', '158.0', ' 138.3 ' -> float; '' -> None; anything else raises ValueError."""
    text = (text or "").strip()
    return float(text) if text else None


def fmt(v):
    return ("%.1f" % v).rstrip("0").rstrip(".") if v is not None else ""


def read_log(path):
    found = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = LINE.search(line)
            if m:
                found[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return found


def read_sheet(path):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8-sig")                 # Excel may save with a BOM; we never write one
    newline = "\r\n" if "\r\n" in text else "\n"
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or [c.strip() for c in rows[0][:4]] != HEADER[:4]:
        raise SystemExit("%s: first row is not the sheet's header (%s)" % (path, ", ".join(HEADER)))
    return rows, newline


def write_sheet(path, rows, newline):
    out = io.StringIO()
    csv.writer(out, lineterminator=newline).writerows(rows)
    data = out.getvalue()
    data.encode("ascii")                           # the sheet stays ASCII; a non-ASCII note stops the write here
    if open(path, "rb").read() == data.encode("ascii"):
        return False
    with open(path, "w", encoding="ascii", newline="") as f:
        f.write(data)
    return True


def ask_default(look, typed, logged):
    if not sys.stdin.isatty():
        return False
    try:
        a = input("%s: the sheet has %s cm, the log says %s cm. Replace? [y/N] " % (look, fmt(typed), fmt(logged)))
    except EOFError:                               # no one to answer (Windows reports NUL as a terminal): keep
        print()
        return False
    return a.strip().lower() in ("y", "yes")


def fill(rows, found, mode="ask", ask=ask_default):
    """Change rows in place. Returns (filled, same, kept, replaced, not_in_sheet) lists of look names."""
    filled, same, kept, replaced = [], [], [], []
    index = {}
    for i, r in enumerate(rows[1:], 1):
        while len(r) < len(HEADER):
            r.append("")
        if r[0].strip():
            index[r[0].strip()] = i
    for look, (default, height) in found.items():
        if look not in index:
            continue
        r = rows[index[look]]
        typed = num(r[2])
        if num(r[1]) is None:
            r[1] = fmt(default)
        if typed is None:
            r[2] = fmt(height); filled.append(look)
        elif abs(typed - height) < 0.05:
            same.append(look)
        elif mode == "overwrite" or (mode == "ask" and ask(look, typed, height)):
            r[2] = fmt(height); replaced.append(look)
        else:
            kept.append(look)
    for r in rows[1:]:
        h, d = num(r[2]), num(r[1])
        if h is not None and d is not None:
            r[3] = fmt(h - d)
    return filled, same, kept, replaced, sorted(set(found) - set(index))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--log", default=DEFAULT_LOG)
    p.add_argument("--csv", default=DEFAULT_CSV)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--keep", action="store_true", help="never replace a height already in the sheet")
    g.add_argument("--overwrite", action="store_true", help="replace every differing height without asking")
    p.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    a = p.parse_args(argv)
    found = read_log(a.log)
    if not found:
        print("no LOOK HEIGHT lines in %s (press ; at a pad with the lab installed first)" % a.log)
        return 1
    rows, newline = read_sheet(a.csv)
    mode = "keep" if a.keep else "overwrite" if a.overwrite else "ask"
    filled, same, kept, replaced, missing = fill(rows, found, mode)
    print("%d look(s) in the log: %d filled, %d already the same, %d replaced, %d kept as typed"
          % (len(found), len(filled), len(same), len(replaced), len(kept)))
    for name, lst in (("filled", filled), ("replaced", replaced), ("kept (sheet differs from log)", kept), ("not in the sheet", missing)):
        if lst:
            print("  %s: %s" % (name, ", ".join(lst)))
    if a.dry_run:
        print("dry run: nothing written")
    elif write_sheet(a.csv, rows, newline):
        print("written: " + a.csv)
    else:
        print("no change: " + a.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
