# Portal design previews

Still pictures of every portal design, for the config editor's Portal Designer (CRD-044). One PNG per design, all cropped and sized
alike (320 x 240, 4:3), plus `index.json` (key, file, kind, licence note per design).

| Files | What |
|---|---|
| `Niagara_Portal*.png` | the game's own 32 looks |
| `Geo_<Shape>_<Type>.png` | our own 24 Geo rings (`PortalHubLooks_P`, CRD-043) at their starting sizes |
| `M_*.png` | the game's ring materials on the mesh ring (1.8 x 1.8 m); `M_Portal_Arch` has none (it draws nothing there) |

**Licence:** these are screenshots from the game: its looks, rings, scenery and cube maps (the Geo rings are ours, shown in front of the
game's scenery). They are not CC0. LuciDin OK'd committing and shipping them (15 Nov 2026). Anything new that ships game assets needs
his OK first.

A design with no picture here is normal: the editor shows a placeholder for it (or the base look's picture).

**Making them again** (when a look changes): in the game, the lab's stills mode (`[` until "stills", then SCROLL LOCK four times at a
pad: camera, its view, a test shot, the run), then `python tools\dev\make_previews.py`. Details in
[`findings/portal-stills-2026-11.md`](../../../findings/portal-stills-2026-11.md).
