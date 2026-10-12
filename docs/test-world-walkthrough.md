# Building a tiny test world for the Portal Hub

Goal: a minimal custom world, packaged as a patch pak, that the hub can load and send players to. It proves the whole chain and doubles as a
template for other modders. Nothing here needs C++.

Numbers in brackets, like <sup>[[1]](#ref-1)</sup>, point to the sources at the bottom. A source is either Epic's or UE4SS's own documentation, a community guide, or
this project's own test results; the **Sources** list says which, and notes where a claim comes from testing rather than from documentation.

**What you build:** a map with a flat floor and a few lights (`CordonaTest_L0`), and a tiny Level Instance Blueprint, the *loader*
(`BP_CordonaTestLoader`), that streams the map in at its own location.<sup>[[1]](#ref-1)</sup> The hub spawns the loader far from the Facility, waits for the level,
then puts a teleporter pad at the arrival point.

Names used below (change them for your own world; see **How the names fit together** in step 6 for which ones must match):

| What | Value |
|---|---|
| Content folder | `/Game/Mods/CordonaTest/` |
| Map | `/Game/Mods/CordonaTest/Maps/CordonaTest_L0` |
| Loader Blueprint | `/Game/Mods/CordonaTest/BP_CordonaTestLoader` (class `BP_CordonaTestLoader_C`) |
| Arrival id | `cordonatest_start` |
| Chunk id | `90` (the game itself uses 0)<sup>[[3]](#ref-3)</sup> |

## 0. Requirements
Unreal Engine **5.4** (the game is 5.4.4), the Windows 10/11 SDK and Visual Studio build tools, and the game with UE4SS and this hub installed.

## 1. The project
The project folder is `TestWorld/AbioticFactor/` in this repository's working copy (git-ignored). It must be named exactly `AbioticFactor`.
Its `Config/DefaultGame.ini` already turns on **IoStore**, **chunk generation** and lists the map to cook.
1. Open `AbioticFactor.uproject` (double-click, or right-click > Launch). It is a Blueprint-only project.
2. **Edit > Editor Preferences > Experimental > Allow ChunkID Assignments**: tick it.<sup>[[3]](#ref-3)</sup>
3. **Edit > Project Settings > Packaging**: confirm *Use Pak File*, *Use Io Store* and *Generate Chunks* are on, and that
   *List of Maps to Include in a Packaged Build* contains `/Game/Mods/CordonaTest/Maps/CordonaTest_L0`
   (the map must be listed here: a level loaded as an instance is not part of any persistent map, so it is not packaged unless listed).<sup>[[2]](#ref-2)</sup>
4. **Leave *Use Io Store* on.** The game loads packages through IoStore only: a pak built without it still mounts, but the game never finds the loader class in it.<sup>[[10]](#ref-10)</sup>

## 2. The map
1. In the Content Browser open `Content/Mods/CordonaTest/Maps`. **File > New Level > Empty Level** (**not** Basic: the Basic template adds a sky, fog, clouds,
   a directional light and an engine floor mesh. Those lights and atmosphere actors are global and would change the lighting of the whole game world, and the
   engine mesh would not be in your pak). Save it as `CordonaTest_L0`. If you already made a Basic level, delete every actor in it.
   **Check where it saved:** the Save dialog defaults to the top of `Content`. Make sure the map ends up in `Content/Mods/CordonaTest/Maps` (if it is in the wrong place, drag it
   there in the Content Browser, choose Move Here, then right-click the `Content` folder > Update Redirector References, called Fix Up Redirectors in Folder in older editors). Its path must be exactly `/Game/Mods/CordonaTest/Maps/CordonaTest_L0`.
2. Make the floor use **your own** mesh, not an engine one (engine assets are not part of your chunk): open the Content Browser (bottom-left **Content Drawer**, or Ctrl+Space),
   open its own **Settings** menu (not the editor's Settings at the top right) and tick **View > Show Engine Content**,
   find `BasicShapes/Cube`, right-click > **Asset Actions > Create Copy** into `/Game/Mods/CordonaTest/`, and use that copy.
3. Floor: place the copy at (0, 0, -50) scaled (40, 40, 1). Its top face is at Z = 0, which is the floor height used by the hub's `arrive` setting.
4. A few things to look at: a couple of the copy cubes as pillars, a Point Light or two placed from **Place Actors > Lights** (do not drop light assets onto the cubes).
   **Set every light's Mobility to Movable** so no baked lighting is needed. Add a Sky Light (Movable) if the floor looks black.
5. Keep everything near the origin (within about +-4000 units). Everything you place is relative to where the loader is spawned.
6. **Arrival point:** the hub puts a pad at the `arrive` position facing a yaw you choose; players appear **215 units in front of it and 127 up**.
   With `arrive = { 0, 0, 0, 0 }` (pad at the map's origin, facing +X) players stand at (215, 0, 127), on the floor. Leave that area clear.<sup>[[10]](#ref-10)</sup>

## 3. The loader Blueprint
1. In `Content/Mods/CordonaTest/`: right-click > **Blueprint Class**, open **All Classes**, search `Level Instance` and pick **Level Instance**
   (Epic's Level Instance actor, `ALevelInstance`).<sup>[[1]](#ref-1)</sup> Name it `BP_CordonaTestLoader`.
2. Open it and click **Class Defaults**. Under **Level**, set the level to `CordonaTest_L0`. This is the Level Instance's world asset (`SetWorldAsset` / `GetWorldAsset` in the API).<sup>[[1]](#ref-1)</sup>
3. Still in Class Defaults, expand **Level Instance > Advanced** and set **Desired Runtime Behavior** to **Standalone**. The API lists this setting (`DesiredRuntimeBehavior`)<sup>[[1]](#ref-1)</sup>
   but does not describe the choices. In testing, **Standalone** loads the map as its own streaming level, which the hub can watch for; **Embedded** would merge it into the main
   world. With the default setting the map reference was **not written into the cooked Blueprint** and nothing loaded.<sup>[[10]](#ref-10)</sup>
4. Leave the Event Graph empty, compile, and save. Do not place the loader in the map: the hub spawns it, and the engine streams the level in at the loader's location.<sup>[[10]](#ref-10)</sup>

   *Do not* build the loader as an Actor whose BeginPlay calls **Load Level Instance (by Name)**.<sup>[[2]](#ref-2)</sup> It is documented, but in this game it reported failure and loaded
   nothing.<sup>[[10]](#ref-10)</sup> Print String is Development Only and prints nothing in the shipping game, so do not use it to debug.<sup>[[10]](#ref-10)</sup>

## 4. Mark the assets for your chunk
1. In `Content/Mods/CordonaTest/`: right-click > **Miscellaneous > Data Asset > Primary Asset Label**, name it `PAL_CordonaTest`.<sup>[[3]](#ref-3)</sup>
2. Open it: **Priority** 1, **Chunk ID** 90, tick **Label Assets in My Directory**, and set the cook rule to always cook if offered. Assets with no chunk id (or a negative one) go into chunk 0, the game's own.<sup>[[3]](#ref-3)</sup>
3. **Make sure the loader is cooked.** Nothing references it (the hub spawns it), so the packager skips it unless told otherwise. In **Project Settings > Packaging > Advanced**,
   add `/Game/Mods/CordonaTest` to **Additional Asset Directories to Cook** (it is already set in the project's `DefaultGame.ini`).<sup>[[10]](#ref-10)</sup>
4. Save everything (**File > Save All**).

## 5. Package
1. **Platforms > Windows > Package Project**, pick an output folder (for example `TestWorld/Packaged`). The first package is slow (shaders).
2. **Check the cooked loader before installing anything.** Open `TestWorld/AbioticFactor/Saved/Cooked/Windows/AbioticFactor/Content/Mods/CordonaTest/` and confirm that
   `BP_CordonaTestLoader.uasset` contains the text `/Game/Mods/CordonaTest/Maps/CordonaTest_L0` (open it in a text editor and search, or run
   `Select-String -Path BP_CordonaTestLoader.uasset -Pattern CordonaTest_L0 -Encoding Default` in PowerShell). If it is missing, the loader's Level or its Desired Runtime Behavior
   (step 3) is not set, and the game will load nothing.<sup>[[10]](#ref-10)</sup>
3. In the output, find `Windows/AbioticFactor/Content/Paks/`. You need **only** `pakchunk90-Windows.pak`, `.ucas` and `.utoc` (the `.pak` is only a few hundred bytes: that is normal
   for IoStore). **Do not install `pakchunk0-*` or `global.*`**: those hold engine content and a shader cache that would override the game's own and crash it on start.<sup>[[10]](#ref-10)</sup>
4. Rename all three together so the part before the extension ends in `_P`: `pakchunk90-Windows_P.pak`, `.ucas`, `.utoc`.<sup>[[4]](#ref-4)</sup>

## 6. Install and connect
1. Copy the three files **directly into** `AbioticFactor/Content/Paks` (not a subfolder: a `~mods` subfolder is not mounted on the Steam install).<sup>[[4]](#ref-4)</sup><sup>[[10]](#ref-10)</sup>
   Replace any earlier `pakchunk90-Windows_P.*` files, and make sure no leftover single `.pak` from a build made without IoStore remains.
2. Add the world to the hub. The easy way: open `PortalHubConfig.bat`, click **Custom worlds**, **Add world**, and fill in the form (the editor fills in the loader class, suggests a free origin, and warns about clashes). Then pick the world under *Your worlds* in a free slot's destination menu and **Save**. Or edit the hub's `config.lua` by hand and add:
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
   `worlds: loader spawned for cordonatest_start ...`, then `worlds: cordonatest_start waiting (0 s): streaming level found, loaded=true, visible=true`, then
   `worlds: cordonatest_start is ready after ... s`. The hub portal switches on and takes you in.

What the hub does behind that log, in order: it finds the loader class with `LoadAsset`<sup>[[5]](#ref-5)</sup> (falling back to the asset registry's `GetAsset`<sup>[[9]](#ref-9)</sup>), spawns it at `origin`
with `SpawnActor`<sup>[[6]](#ref-6)</sup>, watches `world.StreamingLevels` for the entry whose `PackageNameToLoad` is your map and asks whether it is loaded and visible<sup>[[7]](#ref-7)</sup>
(flushing level streaming now and then<sup>[[8]](#ref-8)</sup>), places the arrival pad at `origin + arrive`, and switches the hub portal on. Because the level is chosen inside the Blueprint, Lua never
has to pass a text argument, which fails in this UE4SS build.<sup>[[10]](#ref-10)</sup>

## How the names fit together
Only some of these names have to match each other, and none of them is set inside Unreal except the asset paths.

| Name | Where you set it | Must match |
|---|---|---|
| World id, e.g. `cordonatest_start` | **Only in the hub's `config.lua`** (or the editor's *Custom Destination* box): as the key of your `worlds` entry, and as the portal's `destination`. You invent it. Nothing in Unreal holds it. | The `worlds` key and the portal's `destination` must be the same text. Do not start it with `hub_`. |
| `loaderAsset` and `loaderClass` | In the `worlds` entry. | Your loader Blueprint's package path and its generated `_C` class. |
| `level` | In the `worlds` entry. | Your map's package path. It is only used to recognise the level when it has loaded; the loader Blueprint is what actually loads it. |
| `origin` | In the `worlds` entry. | Free choice, but **every world needs its own** (see below). |
| `arrive` | In the `worlds` entry. | Free choice: where the arrival and return pad goes (x, y, floor z, yaw). |
| The map's name, e.g. `CordonaTest_L0` | In Unreal. | Not an id: it is not turned into the world id. |

The hub connects a portal to a world through the shared id: the portal's `destination` is looked up as a key in `worlds`, and that entry names your loader and your level. The same id is stamped on the arrival pad the hub spawns, which is how the game's teleporter finds it. The arrival pad is also the way back: its destination is pointed at whichever hub portal you came through just before you step in.

**Several custom worlds.** Each world is placed at its own `origin`, and the hub does not choose or check these for you. If two worlds share an origin (or are close enough for their levels to overlap) they will occupy the same space. Give each world an origin far from every other world and from the Facility, for example 200,000 units apart. Only worlds that an enabled portal points at are loaded.

## If something goes wrong
| Log line | Meaning |
|---|---|
| `the world's pak is not installed (no BP_CordonaTestLoader_C ...)` | The pak was not mounted (wrong folder, not restarted), was built **without IoStore** (it mounts but the game never loads it), or the Blueprint path/class in the config does not match. |
| `loader spawned ...` but never `ready` | The loader ran but the level did not stream in: check the loader's Level is set, **Desired Runtime Behavior is Standalone**, the cooked loader contains the map path (step 5.2), and the map is in the Packaging map list. |
| `ready`, but you fall or land in a wall | Adjust `arrive` (z is the floor, yaw is where the pad faces). |
| (packaging) `Unable to find package for cooking /Game/Mods/CordonaTest/Maps/CordonaTest_L0` | The map is not at that path (it was saved in the wrong folder). Move it into Content/Mods/CordonaTest/Maps. |
| (packaging) `Failed to load '/Game/Mods/CordonaTest/...': Can't find file` | The map still references an asset you moved or deleted (for example a light asset dropped onto a cube). Replace it with a plain Point Light from Place Actors and package again. It is usually harmless but worth cleaning up. |
| (packaging) `Stage Failed. Missing receipt ...-Win64-Shipping.target` / `Missing UnrealGame binary` | The packager thinks the project has code. Make sure the .uproject has no Modules entry (a Blueprint-only project has none), then reopen the editor. |
| The game crashes at start with `Missing global shader ...` | You installed the wrong pak: `pakchunk0` or `global` (engine content and a shader cache). Remove it and install only the `pakchunk90` files. |
| The loader is not in your chunk (the chunk manifest lists only the map and meshes) | The loader was never cooked. Add `/Game/Mods/CordonaTest` to Additional Asset Directories to Cook and package again. |
| The game crashes on load | Usually a bad cook: re-package, and check the chunk id is not 0. |
| Every hub or other UE4SS mod stops reacting after a Lua error | A Lua error inside any mod's hook can make UE4SS remove its tick hook ("removing hook!" in the log), and all game-thread work stops until the game is restarted. Disable the mod that errored and restart. |

## What this exercise answered
- A self-contained map plus a Level Instance loader Blueprint streams in at the configured origin: ready after 0.2 s in testing.
- The hub's `LoadAsset`-first lookup finds the loader class.
- The packaging settings that work for a new content chunk alongside the game's own: IoStore on, chunk id 90, the always-cook directory, and only the `pakchunk90` triplet installed.

## Sources
Source types: **Epic** is Epic Games' documentation, **UE4SS** is the UE4SS documentation, **Community** is a modding guide, **Testing** is this project's own results. Where the documentation is silent, the text above says
the claim comes from testing.

<a id="ref-1"></a>1. Epic, *ALevelInstance* (Unreal Engine API reference). Lists the Level Instance actor, `GetWorldAsset`/`SetWorldAsset` and the `DesiredRuntimeBehavior` setting. It does not describe cooking or the runtime behaviour choices. <https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/ALevelInstance>

<a id="ref-2"></a>2. Epic, *Load Level Instance (by Name)* (Blueprint API). Says the map should be in the packaging map list so it is packaged, and that `Out Success` reports whether the map was found. We tested this node in a loader and it failed in this game (see 10). <https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/LevelStreaming/LoadLevelInstance_byName>

<a id="ref-3"></a>3. Epic, *Cooking Content and Creating Chunks in Unreal Engine*. Covers Primary Asset Labels and chunk ids; assets without a chunk id, or with a negative one, go into chunk 0. <https://dev.epicgames.com/documentation/unreal-engine/cooking-content-and-creating-chunks-in-unreal-engine>

<a id="ref-4"></a>4. Community guide to making a patch pak for this game (Blueprint project named `AbioticFactor`, chunk label, `_P` naming of the output). <https://hackmd.io/f3Bl-APIQrOlKmAuBxbI_A>

<a id="ref-5"></a>5. UE4SS, *LoadAsset*. Loads an asset by path and name; game thread only. <https://docs.ue4ss.com/lua-api/global-functions/loadasset.html>

<a id="ref-6"></a>6. UE4SS, *UWorld* Lua class, `SpawnActor`. The class passed must be the Blueprint's generated `_C` class. <https://docs.ue4ss.com/dev/lua-api/classes/uworld.html>

<a id="ref-7"></a>7. Epic, *ULevelStreaming* (API reference). Lists `PackageNameToLoad`, `IsLevelLoaded()` and `IsLevelVisible()`. <https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/ULevelStreaming>

<a id="ref-8"></a>8. Epic, *UWorld::FlushLevelStreaming* (API reference). <https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UWorld/FlushLevelStreaming>

<a id="ref-9"></a>9. Epic, *Get Asset* in the Asset Registry Helpers (Blueprint API); the hub's fallback lookup. <https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/AssetData/GetAsset>

<a id="ref-10"></a>10. This project's own test results, recorded in [`findings/custom-world-loading.md`](../findings/custom-world-loading.md): what failed, what worked, and the observations the documentation does not cover (IoStore only, `Content/Paks` not `~mods`, the Standalone setting, the
cooked-map-reference check, the dev-only Print String, the UE4SS text-argument limit, the 215 / 127 arrival offset).
