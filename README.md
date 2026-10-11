# abiotic-factor-portal-hub-mod

A modding tool for editing/adding new Home Portals to the Portal Hub Room in the Office Sector of Abiotic Factor.

A [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) Lua mod for **Abiotic Factor** that turns the Homeworld "portal room" into a real hub:
extra portals can be added to its empty slots and linked to any world that has an arrival pad, with no custom game assets needed
for existing worlds.

**Status: proof of concept.** A portal spawned into every open slot takes you to Dunkeltaler Forest ("Signal") and back,
with exits placed correctly and the hub's portal hum scaled down as portals are added.

## Layout
- `mod/PortalHub/` - the hub mod itself. `Scripts/config.lua` connects worlds to slots; `Scripts/slots.lua` holds the slot geometry.
- `PortalHubConfig.bat` + `tools/PortalHubConfig/` - a dark-mode editor (with the wiki's portal-world icons in `tools/PortalHubConfig/icons/`) for `config.lua` (pick a world, a portal look and the hub volume from drop-downs). It finds the installed mod on its own, or asks you to locate `config.lua`.
- `mod/PortalPoC/` - the original proof-of-concept mod (kept for reference; superseded by PortalHub).
- `mod/PortalMaterialLab/` - experiment: tries swapping the material/texture of a hub portal from Lua (Numpad 7 report, 8 next material, 9 next texture, 0 reset).
- `mod/PortalLogger/` - debugging helpers that dump teleporter, streaming-level and room data to text files.
- `data/portal_slots.json` - the 12 portal-room slots (tiers A/B/C, slots 1-4), their positions and the placement rules.
- `findings/` - notes on how the game's portals, levels and teleporter pairing work, gathered by inspecting the running game.

## Install (tested with UE4SS 3.0.1 Beta)
1. Install UE4SS for Abiotic Factor.
2. Copy `mod/PortalHub` into `AbioticFactor/Binaries/Win64/ue4ss/Mods/`.
3. Add `PortalHub : 1` to `Mods/mods.txt` above the `Keybinds` line.
4. Run `PortalHubConfig.bat` from this repo (dark-mode editor), or edit `Mods/PortalHub/Scripts/config.lua` by hand, to choose which worlds appear in which slots. Then restart mods.
   Portals spawn automatically when the world loads. In game: **Numpad 1** respawns them, **2** removes them.

`mod/PortalLogger` is optional debugging help (dumps teleporter, streaming and room data).

## How it works (short version)
Each teleporter pad has a `MyTeleporterID` and a `DestinationTeleporterID`; a pad sends you to the pad named by its destination and
places you at that pad's fixed exit point, so a pad's facing decides where you come out. Many pads can share one destination.
Because an arrival pad has only one destination, the mod rewrites it just before use so the return trip goes back through the portal
you entered. See `findings/` for details.

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







