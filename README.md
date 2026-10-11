# abiotic-factor-portal-hub-mod

Foreword from the Human:

Sup! SadBoxMan (aka LuciDin) here to let y'all know that this mod would not have been possible without the aid of Claude Code. 
Everything in this mod is open source and free for anyone to take apart, put together, alter, whatever-the-fuck you want to do with it!
If you'd like to use any part of this mod or its contents for your own modding journey, go right ahead! Hell, you don't even need to
credit me! 

I get it, AI be quite a smelly beast, and no part of this utilizes generative content. All code, data, the entire journey of this mod was all
done with publicly available knowledge and documentation (and some of my own manual game data exports).

If you aren't too put off by this having the stench of AI Assistance, enjoy!
Otherwise, apologies for getting your hopes up!

Back to the AI's walkthrough. If any part of the process is poorly explained, let me know via the Nexus Mod Page and I'll update accordingly!

---------------------------------------------------

A [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) Lua mod for **Abiotic Factor** that turns the Homeworld "portal room" (Office Sector) into a
real hub. Extra portals are added to its empty slots and linked to any world that has an arrival pad. For worlds already in the game no
custom game assets are needed. Includes a dark-mode editor so players never have to touch a config file.

**Status:** working for every existing portal world. A portal in each of the nine open slots takes you to a world and back, with exits
placed correctly, a per-portal look, pad light colour, switchable effect parts, and the hub's portal hum scaled as portals are added.
Worlds that ship their own pak can be hooked in too; see [Connecting your own world](#connecting-your-own-world).

## Layout
- `mod/PortalHub/` - the hub mod itself. `Scripts/config.lua` connects worlds to slots; `Scripts/slots.lua` holds the slot geometry.
- `PortalHubConfig.bat` + `tools/PortalHubConfig/` - the dark-mode editor for `config.lua`. It finds the installed mod on its own, or asks
  you to locate `config.lua`. Wiki icons for the portal worlds are in `tools/PortalHubConfig/icons/`.
- `mod/PortalMaterialLab/` - experiments (material swap, overlay effects, colours, level streaming). Not needed to play.
- `mod/PortalPoC/` - the original proof of concept, kept for reference. `mod/PortalLogger/` - debugging dumps.
- `data/portal_slots.json` - the 12 portal-room slots (tiers A/B/C, slots 1-4), their positions and the placement rules.
- `findings/` - notes on how the game's portals, levels and teleporter pairing work, plus what did and did not work.

## Install (tested with UE4SS 3.0.1 Beta)
1. Install UE4SS for Abiotic Factor.
2. Copy `mod/PortalHub` into `AbioticFactor/Binaries/Win64/ue4ss/Mods/`.
3. Add `PortalHub : 1` to `Mods/mods.txt` above the `Keybinds` line.
4. Run `PortalHubConfig.bat` (or edit `Mods/PortalHub/Scripts/config.lua` by hand), choose your portals, **Save**, then restart mods
   (UE4SS GUI: Ctrl+O, **Restart All Mods**). Portals spawn automatically when a world loads. In game: **Numpad 1** respawns them, **2** removes them.

## The editor
Each open slot (A-1, A-2 and B-3 are the game's own Stone Garden, Torii and Cabin portals and are locked) has:
- **Enabled** - tick to put a portal in the slot. Unticking clears the row.
- **Name** - a label of your own. It is only used in the mod's log; it does not have to match anything in the game.
- **Destination pad ID** - the arrival pad the portal sends players to (its `MyTeleporterID`). Pick a world from the list (20 wiki portal
  worlds in story/optional order), or choose **Custom Destination** and type any pad ID. The two DLC areas (Temple of Stone / Torii) are refused.
- **Base Portal** - the portal's look. Picking a world sets that world's own entrance look; **Default Portal** is the plain one.
- **Effects** - switch parts of a look on or off (for example SnowFlurry's accretion disk is its `Swirl` part). The `portal` part is always on.
- **Light / Bright** - tint the pad's own light with a rainbow preset or **Custom** colour, and scale its brightness in 0.1 steps (1.0 = the game's normal).
- A **hub portal volume** mode: dynamic (quieter as portals are added), manual, or the game's default.

Save is blocked, with the problem shown in red, while a ticked portal has no valid destination.

## How it works (short version)
Each teleporter pad has a `MyTeleporterID` and a `DestinationTeleporterID`; a pad sends you to the pad named by its destination and
places you at that pad's fixed exit point (215 units in front of it, 127 up), so a pad's facing decides where you come out. Many pads can share
one destination. Because an arrival pad has only one destination, the mod rewrites it just before use so the return trip goes back through the
portal you entered. See `findings/` for details.

## Connecting your own world
The hub only needs one thing from your world: **an arrival pad with a known ID** that exists in the world when a player is sent to it.
Everything else (the portal in the hub, its look, the return trip) is handled by this mod.

**What your world must provide**
1. A level (map) with a teleporter pad actor of the game's `BP_Teleporter_ParentBP` class
   (`/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP`), with `MyTeleporterID` set to an ID of your choice, e.g. `mymod_start`.
2. The pad faces the way you want players to stand: they are placed 215 units in front of it. Put it on open floor facing open space.
3. Nothing else is needed for the return trip: the hub points your pad back at whichever hub portal the player used.

**What you add to the hub**
- In `PortalHubConfig.bat`, pick a slot, choose **Custom Destination**, and type `mymod_start` (or add `{ slot = "A-4", name = "My World", destination = "mymod_start" }`
  to `config.lua`). Pick a look and a light colour if you like.

**Getting your level into the game**
1. **Ship it as a pak.** Create a blank UE 5.4 Blueprint project named `AbioticFactor`, mirror the game's content folders, assign your assets to a
   chunk with a Primary Asset Label, package, and rename the output `pakchunk<N>-Windows_P.*`. Copy the three files (`.pak`, `.ucas`, `.utoc`)
   **directly into** `AbioticFactor/Content/Paks` (not a subfolder: a `~mods` subfolder is not mounted on the Steam install).
   See the community guide: <https://hackmd.io/f3Bl-APIQrOlKmAuBxbI_A>.
2. **Include a loader actor.** A small actor Blueprint in your pak whose BeginPlay calls Epic's
   [Load Level Instance (by Name)](https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/LevelStreaming/LoadLevelInstance_byName) node, with the level's full package path and the actor's own location. That node streams a level in at a world
   location without it being listed in any persistent map. List your map under Project Settings > Packaging > "List of Maps to Include in a Packaged Build" so it is packaged.
   Baking the level path into the Blueprint means Lua never has to pass a text argument (calling the streaming functions with text from Lua fails in UE4SS 3.0.1).
3. **Add a `worlds` entry to the hub's `config.lua`:**
   ```lua
   worlds = {
       mymod_start = {
           loaderAsset = "/Game/Mods/MyWorld/BP_MyWorldLoader",   -- package path of the loader Blueprint
           loaderClass = "BP_MyWorldLoader_C",                    -- its generated class
           level       = "/Game/Mods/MyWorld/Maps/MyWorld_L0",    -- the map it streams (used to see when it is ready)
           origin      = { 1000000, 1200000, 0 },                 -- where the loader is spawned: far from the Facility
           arrive      = { 700, -350, 30, -27 },                  -- arrival pad relative to origin: x, y, floor z, yaw
       },
   },
   ```
   Then give a hub portal that world's id as its destination (in the editor: **Custom Destination**, type `mymod_start`).
4. **What the hub does:** it spawns your loader, waits for the level to become visible, spawns a teleporter pad with your id at `origin + arrive`
   (players appear 215 units in front of it, so face it into open space), and only then switches the hub portal on. The return trip works unchanged.
   If your pak is missing or the level never loads, the log says so and the portal stays off.

Loading a world is heavy, so the hub loads it at world start. How each piece of this works, with public sources, is in `findings/custom-world-loading.md`.
## Credits and notes
- **World icons:** the small portal-world icons in `tools/PortalHubConfig/icons/` were pulled from the Portal Worlds section of the
  [Abiotic Factor wiki's Locations page](https://abioticfactor.wiki.gg/wiki/Locations#Portal_Worlds). The artwork belongs to the game's
  developers and is used here only to label the editor; it is not covered by this project's MIT license. The editor works without it:
  delete the `icons` folder or set `$ShowWorldIcons = $false` in `PortalHubConfig.ps1`.
- World names and the story/optional grouping in the destination list follow the same wiki.
- No game files, extracted game data or mapping files are in this repository. This is an unofficial fan project and is not
  affiliated with the game's developers.

## License
[MIT](LICENSE). Fork it, learn from it, change it, and build your own portals or worlds on top of it. Please keep the copyright notice.




