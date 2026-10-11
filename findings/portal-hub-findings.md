# Step 2 findings — DT_Levels / Facility / Teleporters

Source: strings pulled from `PAK Assets\AbioticFactor\Content\...` (cooked assets, no decompile).

## DT_Levels (`Blueprints/DataTables/Environment/DT_Levels`)
- Row struct: `LevelMetadata_Struct`. Rows are keyed by level name; the name table includes
  `H_Cabin`, `H_Garden`, `H_Japan` plus per-level start ids `H_Cabin_Start`, `H_Garden_Start`,
  `H_Japan_Start`.
- Display names come from `StringTable_Locations` (keys such as `vignette_h_garden`, `vignette_h_torii`).
- It references `DT_LevelFX` for day/night FX rows. Night variants exist as separate rows (e.g. `HJapan_Night`).
- Other vignette portal worlds use `<name>_start` ids (`alps_start`, `train_start`, `wall_start`, ...).
- **Takeaway:** a Dunkeltaler row needs `H_Dunkeltaler` + `H_Dunkeltaler_Start`, and a new
  `StringTable_Locations` key (or reuse an existing one) for the sector name.

## Facility map (`Maps/Facility`)
- Three Homeworld portals are placed as `BP_Teleporter_HomeWorld_C` actors:
  `H_Cabin_Entrance`, `H_Garden_Entrance`, `H_Japan_Entrance`.
- The matching `*_Start` ids belong to teleporters inside the destination levels.
- Pairing is by string: `MyTeleporterID` on one actor matches `DestinationTeleporterID` on the other.
- Naming convention confirmed: `H_<Name>_Entrance` (in Facility) / `H_<Name>_Start` (in world).

## BP_Teleporter_ParentBP
- Key properties: `MyTeleporterID`, `DestinationTeleporterID`, `IsTeleporterActive` (replicated),
  `TeleportOverlapBox`, `ExitPoint`, `DestText`, `ParticleLoop`, `PortalHumLoop`, `PortalTexture`.
- Key functions: `AttemptTeleport`, `TeleportPlayer`, `CheckRecentArrivals`, `SavePortalState`.
- Uses `GetAllActorsOfClass` to find the destination teleporter, so the destination actor must be
  loaded before the player can arrive.

## BP_Teleporter_HomeWorld (child of ParentBP)
- Adds `RequiredDLC` (row handle into `DT_GameEntitlements`), `RequiredWorldFlag` (row handle into
  `DT_WorldFlags`), `CanLevelBeActive`, `HomeWorlds` and `OnWorldFlagUpdated`.
- A new portal with no DLC or flag requirement should leave both row handles null
  (the BP checks `IsRowHandleNull`).

## Implications for the Dunkeltaler plan
1. A spawned `BP_Teleporter_HomeWorld_C` in Facility needs `MyTeleporterID=H_Dunkeltaler_Entrance`,
   `DestinationTeleporterID=H_Dunkeltaler_Start`, and `IsTeleporterActive=true`.
2. The destination level must contain a teleporter with `MyTeleporterID=H_Dunkeltaler_Start`
   (and presumably the reverse pairing back out).
3. Still unknown: the exact trigger that streams a level in when a portal activates
   (ParentBP uses `LoadAsset`/`OnLoaded` and the LevelManager subsystem, not a visible load call).
   Needs a live look in UE4SS, or the `.pdb`.
4. Still unknown: whether a DT_Levels row alone is enough for streaming, or the streaming sublevel
   must also be registered in the persistent `Facility` map. A UE4SS runtime check should settle it.

## Mod folder cleanup done this session
Non-essential mods were moved to `Removed-Mods-Backup\` in this folder. `mods.txt` and `mods.json`
originals are saved there as well. Left in place: BPModLoaderMod, BPML_GenericFunctions, Keybinds, shared.

## Live dump results (PortalLogger, F6 in Homeworld Room)
- 116 teleporter actors, ALL in /Game/Maps/Facility.Facility:PersistentLevel
  (92 ParentBP, 14 Teleporter_WaterPipe_BP, 6 BP_Teleporter_HomeWorld, 4 PlayerPortal).
- Six HomeWorld actors = three pairs, **both ends in the persistent Facility level**
  (the *_Start pads are not inside a streamed sublevel; the world content is physically placed in Facility):
  - H_Cabin_Entrance <-> H_Cabin_Start      DLC None,            flag SnowglobeComplete
  - H_Garden_Entrance <-> H_Garden_Start    DLC HomeworldGarden, flag None
  - H_Japan_Entrance <-> H_Japan_Start      DLC SupportersEdition, flag None
- All IsTeleporterActive = true. Row-handle names: RequiredDLC.RowName / RequiredWorldFlag.RowName ("None" = ungated).
- Location/rotation were not logged on the first run (script fixed; needs a re-run).
- Implication: the "new streaming sublevel" assumption is unproven. A Dunkeltaler world may only need
  a Start pad placed far from the base map, or a sublevel that includes its own Start pad. Next check: the
  Start pads' locations, and whether any Facility sublevels are streamed in near them.

## Live results: portal slots, streaming, Dunkel (2026-10-10 evening)
- Portal room has 12 Lodestone containers in 3 tiers; see portal_slots.json. Tier C has none active in current game.
- Home worlds are separate maps: Maps/H_Cabin.umap, H_Garden.umap, H_Japan.umap, streamed as LevelStreamingDynamic_N
  (_56 Cabin @129594,113666,-4657; _55 Garden @130000,160241,59000; _52 Japan @131851,126601,56628).
  Only the level the player is in is loaded (Facility area _14 unloads while in a home world).
- Dunkel (hidden Hydroplant portal, free update, no DLC): streaming level LevelStreamingDynamic_58, offset
  (-253036.6, -65773.8, 0). Player stood at (-237144, -67303, -16933). Arrival pad = BP_Teleporter_PlayerPortal_C
  teleporterpad87 at (-237159.9, -66762.6, -17058.7); its partner at (128399, 157245, 59241). No HomeWorld-class pads or
  H_ IDs exist for Dunkel; it uses PlayerPortal pads.
- The local PAK Assets dump predates Dunkel (no Dunkel/Forest map, DT_Levels has no row). Needs a fresh FModel extract of the
  current game version (and possibly a newer .usmap).
- F10 Lodestone scan crashed (null deref, EXCEPTION_ACCESS_VIOLATION 0x18) after printing all it needed. Hardened; avoid wide actor scans.

## CONFIRMED: Dunkeltaler Forest == "Signal" (fresh FModel export, current game version)
- DT_Levels row key V_SIGNAL: LevelFileName V_Signal, EntranceTeleporter signal_start, ReleaseGroup EReleaseGroup::MOXY,
  SectorName key ignette_signal -> "Dunkeltaler Forest", LevelFX rows VSignal_Night (day+night), ResettablePortalWorld true,
  IsVignette true, HasFacilityShakes false.
- Teleporter pair (both BP_Teleporter_ParentBP_C, active): signal_entrance @ (-40258, 10441, -801) in the Facility (Hydroplant area)
  <-> signal_start @ (-198058, -59578, -17212). V_Signal.json itself contains no teleporter actors; both pads live in Facility.
- Correction: the old PAK Assets dump DID already contain Dunkel under the name Signal (V_Signal.umap, signal_start). My earlier
  "dump predates Dunkel" conclusion was wrong; I searched for the wrong name. DT_Levels row struct also has fields not seen before:
  ReleaseGroup, HasFacilityShakes, IsVignette (the new export lists them by full names with GUID suffixes).
- Non-home-world portal worlds (vignettes) use ParentBP pads named <name>_entrance / <name>_start, not the H_ HomeWorld class.
