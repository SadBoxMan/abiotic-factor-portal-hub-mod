# Still pictures of every portal design (CRD-046, 15 November 2026)

Serves LuciDin's requests "a lab-key to get still first, and once we have stills of EVERY portal type (base game and the new custom
portals) we can try to get some animated clips (gifs) of each type (5 seconds each I reckon)" and "This will need to include some
screenshot previews of the portal designs" (15 Nov). This card made the stills only. The config editor's Portal Designer (CRD-044)
reads them from `tools/PortalHubConfig/previews/`.

## 1. Short answers

| Question | Answer |
|---|---|
| Can the lab shoot every design by itself? | **Yes.** The lab's stills mode (`[` until "stills", SCROLL LOCK x4) put all 67 designs on one pad and shot each with the game's own `shot` command: 67 of 67 in 3 min 41 s, no crash, everything put back. |
| HUD in the pictures? | **No.** `shot` (without `showui`) captures the scene only. |
| Where do the shots land? | `%LOCALAPPDATA%\AbioticFactor\Saved\Screenshots\Windows\ScreenShotNNNNN.png` at the window size (1920 x 1080 here). The game makes the folder on the first shot. |
| A map with no portal? | **Yes.** With no pad within 15 m, the first SCROLL LOCK places a stand-in pad 4.5 m ahead of the player, facing them, removed again at the end (LuciDin ran it in the tutorial). |
| Picture format? | PNG, **4:3, 320 x 240** (LuciDin: "trimmed a bit so that it's a 4:3 perspective"): the centred 4:3 box of the full frame height, so tall portals stay whole. Names agreed with CRD-044: `<DESIGN_NAMES key>.png`, `Geo_<Shape>_<Type>.png`, `M_<ring material>.png`, plus `index.json`. |
| Licence? | Screenshots from the game (its looks, rings, scenery and cube maps; the Geo rings are ours, in front of that scenery), so not CC0. **LuciDin OK'd committing and shipping all of them** (15 Nov): "Commit all the shots". His ruling the same evening: no blanket "no game assets" rule any more; **anything that ships game assets needs his OK first**. |

## 2. What was shot (66 pictures)

- **32 game looks** (`hubdata.DESIGN_NAMES`), each at its height from `portal-heights.csv` (this session's `;` heights win).
- **24 Geo rings** (CRD-043) on the engine plane as square C, at each shape's starting size, with the pad's own look hidden. They load
  from `PortalHubLooks_P` through `AssetRegistryHelpers:GetAsset` (LoadAsset finds nothing in our pak, as in CRD-043).
- **10 game ring materials** on the same plane at 1.8 x 1.8 m (CRD-044's optional ring stills). **`M_Portal_Arch` (Night Realm's arch)
  draws nothing on the flat ring**, so it gets no picture (`make_previews.py` `NO_PICTURE`); the editor shows the base look's picture.
- Faint by nature: Dark, Rift and Tiny are hard to see against the tutorial's bright rock. A darker spot would suit them better (open).

## 3. How to shoot them again (when a look changes)

1. Install the lab (dispatcher's OK; game closed). Stand at a pad (a game pad, or a hub slot on a plain look with no design: a design's
   mesh ring would show too) or anywhere with no pad within 15 m. Pick a neutral, even background.
2. `[` until "stills". SCROLL LOCK: the camera (and the stand-in pad if needed). SCROLL LOCK: view from the camera. M / N (Shift: fine)
   move it closer or further, O / P up or down, LEFT / RIGHT to the pad's other side. SCROLL LOCK: one test shot. SCROLL LOCK: the run
   (about 3.7 min, hands off; SCROLL LOCK stops it, PAUSE ends it). In the tutorial run LuciDin framed at 439 cm, height -20 cm.
3. `python tools\dev\make_previews.py` (`--check` lists the pairing first). It reads the last run in the installed lab's `stills.txt`,
   gives each screenshot to the last note made at or before its time (shots are at least 3 s apart), crops and sizes them, and rewrites
   `index.json`. A partial reshoot (stop after the designs you need) only replaces those pictures.
4. Ask LuciDin before committing new pictures (game assets rule), then commit them.

## 4. In-game calls (first tried here, 15 Nov, beta install v1.5.0)

| Call | Result |
|---|---|
| `World:SpawnActor` of `/Script/Engine.CameraActor` | works (twice) |
| `PlayerController:SetViewTargetWithBlend(camera, 0, 0, 0, false)` and back to the pawn | works; instant switch, no HUD change needed |
| `Actor:K2_SetActorLocationAndRotation` on the camera | works (framing keys) |
| `KismetSystemLibrary:ExecuteConsoleCommand(pc, "shot", pc)` | works; one PNG per call, written within the second |
| Stand-in pad (the lab INSERT's spawn: teleporter Blueprint, ID `cordona_stills`, destination None, active) | works; the hub (CRD-044 build) logged nothing about it |

The camera uses the CameraActor's default 90 degree field of view (nothing written to it). No `Ref was not function`, nothing written to
a save. A first run was ended with PAUSE after 5 designs (LuciDin reframed); the second ran all 67.

## 5. What animated clips (GIFs) would need later

- **Frames:** the game has no video capture we can call. Options: `shot` in a loop (a PNG per call: the write takes most of a frame, so
  expect a few frames per second at best, uneven); or `HighResShot` (renders its own frame, slower); or an outside recorder (OBS) with the
  lab driving the designs at fixed times and a script cutting the video by the `stills.txt` times. The OBS route gives smooth 5 s clips
  and keeps the lab simple (a "clips" variant of the run: each design held 6 s, no shots).
- **Size:** 66 clips x 5 s at 320 x 240 and 15 fps is about 5,000 frames; as GIF (256 colours) roughly 0.5-1.5 MB each, 50-100 MB in all.
  WebP or APNG are smaller; Tk shows GIF frames natively but not WebP, so the editor (CRD-044) decides the format.
- **Licence:** the same game-assets rule: LuciDin's OK before committing or shipping them.

## 6. Open

- Dark, Rift and Tiny are faint against the bright rock: a reshoot of those three against a darker background if LuciDin wants.
- `M_Portal_Arch` on the mesh ring: no picture (it needs the arch's own sprite setup; not a stills problem).
- The pictures are 11 MB in the repo (66 PNGs, about 170 KB each). A smaller size or a palette PNG would cut that if it matters.
