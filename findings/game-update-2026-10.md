# Game update check: Community Update #5 (v1.5.0), October 2026

Checked 27 October 2026, read-only, before the game was launched on the new build. The `UE4SS.log` (17 October) and
`UE4SS_ObjectDump.txt` (11 October) in the install are from the **old** build; nothing below comes from a run of the new one.

## Result, added 6 November 2026 (hotfix v1.5.0.31876, Steam build 26373201)

The break below was confirmed in game and fixed (CRD-004). The rest of this note is the check as written on 27 October, before any launch.

Three things differ from what it predicted:

- **`LevelMetadata` has no `LevelFileName`.** It has `Level`, a soft-object field, and it has no `MapResourceRowHandle` (`bIsSublevel` is there).
  The hub never writes `Level`; UE4SS's `AddRow` leaves fields missing from the Lua table at their defaults. The new object dump shows the
  same fields on the hotfix.
- **The controller's `Day_FX_Row` / `Night_FX_Row` are `LevelFXRowHandle` structs,** so reading them as names gave nil; the hub re-applied the
  lighting every 3 s in worlds with no lighting block. Fixed by reading `.RowName`.
- **`DT_Levels.RowStruct` reads fine from Lua,** so the hub and lab no longer depend on the struct's path.

Answers to the risks below: UE4SS and all mods run on the new exe. The hub's level row stays in the table while the game runs (60 to 61 rows),
but the row registry is not cleared: see the table below. CordonaCorp and the Mod Testing save both loaded. **Portal Entrance works again in
vignette worlds ("Nearest Location").**

### Open after CRD-004 (for CRD-006)

| What | Seen 6 November | Next |
|---|---|---|
| **Portal sickness** | `Debuff_PortalSickness` in no survey, in either save, though the zones name their flags. On 27 October a 222-flag save had it, with the world not yet claimed | Is it the hotfix, the claim, or the flag rows? Check `DT_WorldFlags` holds the `PortalHub_*` rows (the CRD-005 registry question) |
| **Completion** | No completion message and no `PortalHub_*` flag in two visits; the log does not show which pad was used to leave | Use the proper exit pad on purpose, then NUMPAD 7 |
| **Leyak in custom worlds** | Required flag now `Residence_Entered`; forced spawn in World B landed at 0, 0, 0, about 19 km away | Compare with World D; check the zone and the nav mesh separately |
| **Location banner** | World B's title banner shows on entry. The lab's lighting browser, which calls the same `TransitionToNewEnvironmentFX` outside a claimed world, no longer shows its sector name (the lab now shows the row name itself) | Low priority: only matters if a world needs a banner without a level entry |
| **Hook removal on a save switch** | Once with third-party mods installed, not in two switches without them | Bring parked mods back one at a time only if one is needed |

## Verdict on 27 October: needs fixes (one known break, rest unknown until a launch)

The hub will most likely load and run, but its **vignette level entry fails** on the new build (details below). It fails
safely: the hub logs "the game's level table has no field ReleaseGroup (game update?)" and the world is treated as a Facility
area, so no portal sickness check, no title banner and no lighting switch for vignette worlds. Whether UE4SS itself still
hooks the new exe is unknown until the author launches the game once.

## Versions

| | Before | Now |
|---|---|---|
| Game version | not recorded in the repo | 1.5.0.31459 (patch notes) |
| Steam build id | not recorded | 26092436 (`appmanifest_427410.acf`, updated 27 Oct 01:13) |
| Engine | 5.4.4-1040001+++DF+ABF (game log, 17 Oct) | 5.4.4, changelist **1050002** (`++DF+ABF-CL-1050002` in the exe, built 15 Oct) |
| UE4SS | v3.0.1 Beta, Git SHA c838a8ac | unchanged files (Jul 15); `dwmapi.dll` proxy still in `Binaries\Win64` |
| Last launch | 17 Oct 23:07 | not launched since the update |

The engine stays on **UE 5.4.4**: no engine bump, so the world paks (built with UE 5.4) and UE4SS's 5.4 layouts should still fit.
The changelist moved, so the `.usmap` in the ue4ss folder (`AbioticFactor-5.4.4-1040001...`) is stale (only matters for
external tools reading unversioned assets, not for the mods).

## What still matches

- Base paks: still only `pakchunk0-Windows` and `pakchunk0optional-Windows` (+ `global`), rewritten 27 Oct. Our world paks in
  `~mods` (Test_P, WorldA_P..WorldD_P, chunks 90-94) are untouched and do not clash with the game's chunk layout.
- Asset paths the hub and lab use, all still in the new `pakchunk0` file list: `DT_Levels`, `DT_LevelFX`, `DT_WorldFlags`,
  `Vignette_Zone`, `LeyakSafetyZone`, `BP_Teleporter_ParentBP`, `BP_Teleporter_HomeWorld`, `Niagara_Portal` (and `_Torii`,
  `_SnowFlurry`), `AbioticFunctionLibrary`, `DayNightManager`, `Abiotic_PlayerController`, `W_RespawnOptions`.
- Native names still in the exe: `LevelManagerSubsystem`, `WorldFlagSubsystem` with `HasWorldFlagsLoaded`, `SetWorldFlag`,
  `HasWorldFlag`, `GetWorldFlags`. The `WorldFlag` row struct was already native.
- Blueprint-side names (`TransitionToNewEnvironmentFX`, `ActiveLevelFXName`, `ActiveLevelName`, `DisableAutomaticFX`,
  `Day_FX_Row`, `Client_DisplayWarningMessage`, `PlayerIsInVignette`, `PortalSicknessWorldFlag`, `WorldFlagToTriggerOnUse`) live
  in Blueprints that still exist, but their signatures can only be confirmed with a new object dump.

## What changed

1. **`LevelMetadata_Struct` and `LevelFXData_Struct` are gone as Blueprint structs.** Both `/Game/Blueprints/Data/...` assets
   are missing from the new file list; the exe now has native structs `LevelMetadata` and `LevelFXData`. Their field names are
   the same as the old ones without the `_N_GUID` suffix (`LevelFileName`, `LevelFXRow_Day/Night`, `SectorName`,
   `ResettablePortalWorld`, `HasFacilityShakes`, `IsVignette`, `EntranceTeleporter`; `HasDynamicSkybox`, `MusicTracks` on the FX
   side). New fields next to them: `MapResourceRowHandle` (an `EMapResourceTable` handle) and `bIsSublevel`, tied to a new
   `MapPamphletHandleFunctionLibrary` (the GATEPal map now shows several quests).
2. **New native `ABFRowRegistrySubsystem`** (log category `LogRowRegistry`), next to strings for item/recipe/NPC/pet row types.
   Probably how official mods add data-table rows. Not known yet whether it rebuilds tables like `DT_Levels` / `DT_WorldFlags`
   after load (which would drop rows the hub added with `AddRow`).
3. **Official mod support** (mod.io browser, an official Mod Editor on the Epic launcher, per-save mod list). The notes say
   unofficial mods can still be loaded as before but that nearly all of them are expected to break, because a lot of the game's
   code and data was restructured.

## What breaks and where

| File | Function / line | Problem | Fix |
|---|---|---|---|
| `mod/PortalHub/Scripts/main.lua` | `LEVEL_STRUCT` (line 818), `level_fields()`, used by `ensure_level_row()` | `StaticFindObject` of the old Blueprint struct path returns nothing, so no fields are found and every vignette level entry is refused | Read the struct from the table itself (`DT_Levels.RowStruct`), or try `/Script/AbioticFactor.LevelMetadata` first and fall back to the old path. The suffix strip already handles plain native names. Leave the new `MapResourceRowHandle` / `bIsSublevel` at their defaults (never write the handle from Lua: crash rule) |
| `mod/PortalMaterialLab/Scripts/main.lua` | `FX_STRUCT` (line 77, `dump_fx_struct` and the NUMPAD 0 lighting list) and `LEVEL_STRUCT` (line 547, NUMPAD 8 level dump) | Same old paths; the lab's dumps come back empty | Same fix: `DT_LevelFX.RowStruct` / `DT_Levels.RowStruct`, or `/Script/AbioticFactor.LevelFXData` / `.LevelMetadata` |

The DT_WorldFlags row (`WorldFlag`, already native) and the lighting `FindRow` calls should be unaffected.

## What looks risky (unknown until a launch)

- **UE4SS on the new exe.** Same engine version, so likely fine, but the exe was rebuilt; check that `UE4SS.log` reaches
  "Starting mods" and that both Lua mods start.
- **Row registry vs `AddRow`.** If the new registry rebuilds tables, our `PortalHub_<id>` level rows and completion flags may vanish
  after a reload. Watch for a level entry that is added then not found, or completion flags that do not stick.
- **Save format.** Saves now carry a mod list; CordonaCorp may be upgraded on first load. Our completion flags are stored as plain
  names and should survive, but check after the first save/load.
- **Respawn menu / `PlayerIsInVignette`.** The respawn options and map widgets were reworked for multi-quest; the Portal Entrance
  option reading `ActiveLevelFXName` needs a re-test.
- **Long term:** the official Mod Editor may offer a supported way to ship custom levels. Worth a separate look before building
  the GUI packaging step (roadmap step 8).

## In-game checks (CordonaCorp save only, never `stahp`)

Before the first launch: back up nothing (CordonaCorp is fine to break), launch once with the mods as they are, then press the keys below.

| Key | Run it in | What it logs |
|---|---|---|
| (launch only) | Title screen | `UE4SS.log`: UE4SS version line, "Using engine version: 5.4", both mods started, no Lua errors. Ask UE4SS to regenerate the object dump (GUI, Dumpers tab) |
| (load save) | CordonaCorp, Facility | Hub: portal spawn lines, world loading checks for Test World and Worlds A-D, `HasWorldFlagsLoaded` wait passing |
| NUMPAD 8 | Facility, portal room | Lab: level table and where the game thinks the player is; expected to show empty field list (old struct path) |
| NUMPAD 9 | Facility, then inside Test World | Lab: level name, vignette state, weather |
| (walk through portal) | Test World (vignette) | Hub: expected "the game's level table has no field ReleaseGroup (game update?)"; confirms the break above |
| (walk through portal) | World B (home) | Hub: settings line from the loader Blueprint, arrival pad, lighting rows applied |
| NUMPAD 7 | Inside Test World | Lab: vignette zones, buffs (`Buff_InVignette`, `Debuff_PortalSickness`), flags |
| NUMPAD 0 | Inside World D | Lab: lighting row list still readable from `DT_LevelFX` |
| (save, quit to menu, reload) | CordonaCorp | Completion flags still set (hub completion message once only, no `HasWorldFlag` warnings) |

After the run, the session reads `UE4SS.log`, the game log (`Saved\Logs\AbioticFactor.log`) and the new object dump, and confirms
the native struct paths (`/Script/AbioticFactor.LevelMetadata`, `.LevelFXData`) before the fix is written.

## Sources

- Steam news, "Community Update #5 - The Modding Update!" and "How to Install Mods in Abiotic Factor" (26 Oct 2026), and the
  developers' v1.5.0 patch notes thread on the Steam community discussions (posted 22 Oct, edited 26 Oct). robots.txt of
  store.steampowered.com and steamcommunity.com allow these paths; api.steampowered.com disallows everything and was not used.
- Local: `appmanifest_427410.acf`, strings in `AbioticFactor-Win64-Shipping.exe`, the new `pakchunk0-Windows.utoc` file list
  (`tools\dev\read_utoc.py`), the 17 Oct `UE4SS.log` and game log, the 11 Oct object dump.
