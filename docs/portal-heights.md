# Portal heights per look (CRD-041)

[`portal-heights.csv`](portal-heights.csv) holds one height per portal look: how high the look's effect sits above its pad.
LuciDin edits it; the hub's per-look height build (the looks build card, "Portal Height" on the 1.0 checklist) reads it.

| Column | Meaning |
|---|---|
| look | the look's name, as in the editor (`hubdata.DESIGN_NAMES`), 32 rows |
| game default cm | where the game puts the effect: the pad Blueprint's 158 cm (the game's Stone Garden pad uses 138.3) |
| LuciDin's height cm | the height wanted for this look, in cm above the pad. Empty = not set yet |
| offset cm | height minus game default (the script fills it; the build may use either column) |
| notes | free text |

The four first picks (14 November, CRD-039): Friendly Red 108, Default 118, Botanical Red 138, Door 158.

## Measuring in game (lab, dev only)

With the lab (`mod/PortalMaterialLab`) installed, stand within 15 m of a pad (a hub pad in the portal room is easiest):

| Key | What it does |
|---|---|
| `;` | puts the next of the 32 looks on that pad (in the sheet's order, starting after the pad's own look) at that look's height |
| `O` / `P` | moves the current look up / down 10 cm; the height is kept for that look while you cycle on |

Each look starts at its height from earlier in the session, else at LuciDin's pick, else at the pad's own height. Every `;`, `O`
and `P` logs one line to UE4SS.log:

```
[MaterialLab] ---- LOOK HEIGHT: Niagara_Portal_Door | game default 158.0 cm | set 148.0 cm | offset -10.0 cm | pad hub_B4 (6/32)
```

After the 32nd look `;` starts over and logs a table of every height set so far. Nothing is saved to the game; hub NUMPAD 1 respawns
the hub pads with their configured looks. (With an overlay out from `L`, `O` / `P` move the overlay instead, as before.)

## Filling the sheet from the log

```
python tools/dev/portal_heights_from_log.py
```

reads the beta install's UE4SS.log (`--log PATH` for another) and, for each look in it, takes its last LOOK HEIGHT line:
an empty height cell is filled; a cell that already has a different height (one LuciDin typed) is never replaced without a yes:
the script asks per look (`--keep` keeps all, `--overwrite` replaces all, `--dry-run` only reports). Offsets are recomputed, notes and
extra rows kept. Run it before closing the game or before the next launch: UE4SS starts a new log each launch.

Then edit the sheet in Excel (save as CSV, keep the header) and hand it to the looks build card.
