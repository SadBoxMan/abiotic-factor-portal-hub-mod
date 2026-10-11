# Building a tiny test world for the Portal Hub

Goal: a minimal custom world, packaged as a patch pak, that the hub can load and send players to. It proves the whole chain and doubles as a
template for other modders. Nothing here needs C++.

**What you build:** a map with a flat floor and a few lights (`CordonaTest_L0`), and a tiny actor Blueprint, the *loader*
(`BP_CordonaTestLoader`), that streams the map in at its own location. The hub spawns the loader far from the Facility, waits for the level,
then puts a teleporter pad at the arrival point.

Names used below (change them for your own world, but keep the three places that use them in step):

| What | Value |
|---|---|
| Content folder | `/Game/Mods/CordonaTest/` |
| Map | `/Game/Mods/CordonaTest/Maps/CordonaTest_L0` |
| Loader Blueprint | `/Game/Mods/CordonaTest/BP_CordonaTestLoader` (class `BP_CordonaTestLoader_C`) |
| Arrival id | `cordonatest_start` |
| Chunk id | `90` (the game itself uses 0) |

## 0. Requirements
Unreal Engine **5.4** (the game is 5.4.4), the Windows 10/11 SDK and Visual Studio build tools, and the game with UE4SS and this hub installed.

## 1. The project
The project folder is `TestWorld/AbioticFactor/` in this repository's working copy (git-ignored). It must be named exactly `AbioticFactor`.
Its `Config/DefaultGame.ini` already turns on **IoStore**, **chunk generation** and lists the map to cook.
1. Open `AbioticFactor.uproject` (double-click, or right-click > Launch). It is a Blueprint-only project.
2. **Edit > Editor Preferences > Experimental > Allow ChunkID Assignments**: tick it.
3. **Edit > Project Settings > Packaging**: confirm *Use Pak File*, *Use Io Store* and *Generate Chunks* are on, and that
   *List of Maps to Include in a Packaged Build* contains `/Game/Mods/CordonaTest/Maps/CordonaTest_L0`
   (the map must be listed here: a level loaded as an instance is not part of any persistent map, so it is not packaged unless listed).

## 2. The map
1. In the Content Browser open `Content/Mods/CordonaTest/Maps`. **File > New Level > Empty Level** (or Basic), save it as `CordonaTest_L0`.
2. Make the floor use **your own** mesh, not an engine one (engine assets are not part of your chunk): in the Content Browser, show Engine content,
   find `BasicShapes/Cube`, right-click > **Asset Actions > Create Copy** into `/Game/Mods/CordonaTest/`, and use that copy.
3. Floor: place the copy at (0, 0, -50) scaled (40, 40, 1). Its top face is at Z = 0, which is the floor height used by the hub's `arrive` setting.
4. A few things to look at: a couple of the copy cubes as pillars, a Point Light or two. **Set every light's Mobility to Movable** so no baked lighting is needed.
   Add a Sky Light (Movable) if the floor looks black.
5. Keep everything near the origin (within about +-4000 units). Everything you place is relative to where the loader is spawned.
6. **Arrival point:** the hub puts a pad at the `arrive` position facing a yaw you choose; players appear **215 units in front of it and 127 up**.
   With `arrive = { 0, 0, 0, 0 }` (pad at the map's origin, facing +X) players stand at (215, 0, 127), on the floor. Leave that area clear.

## 3. The loader Blueprint
1. In `Content/Mods/CordonaTest/`: right-click > **Blueprint Class > Actor**, name it `BP_CordonaTestLoader`.
2. In its Event Graph, from **Event BeginPlay** add **Load Level Instance (by Name)**
   ([Epic docs](https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/LevelStreaming/LoadLevelInstance_byName)):
   - **Level Name:** `/Game/Mods/CordonaTest/Maps/CordonaTest_L0` (the full package path; a short name forces a slow disk search)
   - **Location:** **Get Actor Location** (the hub spawns the loader at the `origin` you configure, so the level appears there)
   - **Rotation:** (0, 0, 0)
   - **Optional Level Name Override:** leave empty. Optional: connect **Out Success** to **Print String** to see it in the log.
3. Compile and save. Do not place the loader in the map: the hub spawns it.

## 4. Mark the assets for your chunk
1. In `Content/Mods/CordonaTest/`: right-click > **Miscellaneous > Data Asset > Primary Asset Label**, name it `PAL_CordonaTest`.
2. Open it: **Priority** 1, **Chunk ID** 90, tick **Label Assets in My Directory**, and set the cook rule to always cook if offered.
3. Save everything (**File > Save All**).

## 5. Package
1. **Platforms > Windows > Package Project**, pick an output folder (for example `TestWorld/Packaged`). The first package is slow (shaders).
2. In the output, find `Windows/AbioticFactor/Content/Paks/`. You need only `pakchunk90-Windows.pak`, `.ucas` and `.utoc`.
3. Rename all three together so the part before the extension ends in `_P`: `pakchunk90-Windows_P.pak`, `.ucas`, `.utoc`.

## 6. Install and connect
1. Copy the three files **directly into** `AbioticFactor/Content/Paks` (not a subfolder: a `~mods` subfolder is not mounted on the Steam install).
2. In the hub's `config.lua` add:
   ```lua
   worlds = {
       cordonatest_start = {
           loaderAsset = "/Game/Mods/CordonaTest/BP_CordonaTestLoader",
           loaderClass = "BP_CordonaTestLoader_C",
           level       = "/Game/Mods/CordonaTest/Maps/CordonaTest_L0",
           origin      = { 1100000, 1300000, 0 },
           arrive      = { 0, 0, 0, 0 },
       },
   },
   ```
   and give a hub portal the destination `cordonatest_start` (in the editor: **Custom Destination**).
3. Restart the game, load a world, wait about 5 seconds, open the UE4SS GUI (Ctrl+O). Expected log:
   `worlds: loader spawned for cordonatest_start ...` then `worlds: cordonatest_start is ready after ... s`. The hub portal switches on and takes you in.

## If something goes wrong
| Log line | Meaning |
|---|---|
| `the world's pak is not installed (no BP_CordonaTestLoader_C ...)` | The pak was not mounted (wrong folder, not restarted) or the Blueprint path/class in the config does not match. |
| `loader spawned ...` but never `ready` | The loader ran but the level did not stream in: check the map is in the Packaging map list, the Level Name path is exact, and Out Success. |
| `ready`, but you fall or land in a wall | Adjust `arrive` (z is the floor, yaw is where the pad faces). |
| The game crashes on load | Usually a bad cook: re-package, and check the chunk id is not 0. |

## Open questions this exercise answers
- Whether a self-contained map plus a loader Blueprint streams in at the configured origin.
- Whether the hub's `LoadAsset`-first lookup finds the loader class (the registry lookup is the fallback).
- How the packaging settings need to look for a new content chunk to mount alongside the game's own.
