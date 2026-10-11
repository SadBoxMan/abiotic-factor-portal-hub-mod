# abiotic-factor-portal-mod

A modding tool for editing/adding new Home Portals to the Portal Hub Room in the Office Sector of Abiotic Factor.

A [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) Lua mod for **Abiotic Factor** that turns the Homeworld "portal room" into a real hub:
extra portals can be added to its empty slots and linked to any world that has an arrival pad, with no custom game assets needed
for existing worlds.

**Status: proof of concept.** A portal spawned into every open slot takes you to Dunkeltaler Forest ("Signal") and back,
with exits placed correctly and the hub's portal hum scaled down as portals are added.

## Layout
- `mod/PortalPoC/` - the proof-of-concept mod (spawns test portals into the open slots).
- `mod/PortalLogger/` - debugging helpers that dump teleporter, streaming-level and room data to text files.
- `data/portal_slots.json` - the 12 portal-room slots (tiers A/B/C, slots 1-4), their positions and the placement rules.
- `findings/` - notes on how the game's portals, levels and teleporter pairing work, gathered by inspecting the running game.

## Install (tested with UE4SS 3.0.1 Beta)
1. Install UE4SS for Abiotic Factor.
2. Copy `mod/PortalPoC` (and optionally `mod/PortalLogger`) into `AbioticFactor/Binaries/Win64/ue4ss/Mods/`.
3. Add `PortalPoC : 1` to `Mods/mods.txt` above the `Keybinds` line.
4. In game: **Numpad 1** spawn the test portals, **2** remove them, **3** dump exit points, **4** dump pad designs,
   **5** re-apply hub hum volume, **6** reset every pad's hum volume.

## How it works (short version)
Each teleporter pad has a `MyTeleporterID` and a `DestinationTeleporterID`; a pad sends you to the pad named by its destination and
places you at that pad's fixed exit point, so a pad's facing decides where you come out. Many pads can share one destination.
Because an arrival pad has only one destination, the mod rewrites it just before use so the return trip goes back through the portal
you entered. See `findings/` for details.

## Not included
No game files, extracted assets, mapping files or other authors' work are in this repository. This is an unofficial fan project and
is not affiliated with the game's developers.

## License
[MIT](LICENSE). Fork it, learn from it, change it, and build your own portals or worlds on top of it. Please keep the copyright notice.
