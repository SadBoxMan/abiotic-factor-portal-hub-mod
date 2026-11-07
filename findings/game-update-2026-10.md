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

### Open after CRD-004 (for CRD-006; all answered in the next section)

| What | Seen 6 November | Next |
|---|---|---|
| **Portal sickness** | `Debuff_PortalSickness` in no survey, in either save, though the zones name their flags. On 27 October a 222-flag save had it, with the world not yet claimed | Is it the hotfix, the claim, or the flag rows? Check `DT_WorldFlags` holds the `PortalHub_*` rows (the CRD-005 registry question) |
| **Completion** | No completion message and no `PortalHub_*` flag in two visits; the log does not show which pad was used to leave | Use the proper exit pad on purpose, then NUMPAD 7 |
| **Leyak in custom worlds** | Required flag now `Residence_Entered`; forced spawn in World B landed at 0, 0, 0, about 19 km away | Compare with World D; check the zone and the nav mesh separately |
| **Location banner** | World B's title banner shows on entry. The lab's lighting browser, which calls the same `TransitionToNewEnvironmentFX` outside a claimed world, no longer shows its sector name (the lab now shows the row name itself) | Low priority: only matters if a world needs a banner without a level entry |
| **Hook removal on a save switch** | Once with third-party mods installed, not in two switches without them | Bring parked mods back one at a time only if one is needed |

## Full assessment, 6 November 2026 (CRD-006, v1.5.0.31876, Steam build 26373201)

**Verdict: the hub works on the current build.** Everything CRD-004 left open turned out to be fine or a false alarm. Two real faults remain, both
about loading a save inside a custom world, and neither was caused by the update's data changes. UE4SS stayed on the July build (c838a8ac).

Tested in game on Mod Testing and CordonaCorp, 16 world loads across four runs, keys and logs as listed below.

### What each open item turned out to be

- **Portal sickness: false alarm.** `Debuff_PortalSickness` is applied on v1.5.0 (seen in Test World with the flag cleared, gone in the Facility). It
  was missing on 6 November because `PortalHub_cordonatest_start_Completed` and `PortalHub_world_b_start_Completed` were already in CordonaCorp's
  save, and World B's in Mod Testing's, all from before the update (both are in the 27 October backups). Neither the hotfix nor the claim is involved.
- **Completion: false alarm, same cause.** A flag that is already set cannot change, so no message shows. Also, NUMPAD 7 read the save's flag list without
  `:get()`, so it printed `(none)` whatever was set; fixed in the lab. With the flag cleared, the exit pad sets it within 1.5 s and the message shows, in
  both Test World and World B. Leaving by the arrival pad does not set it.
- **Leyak: works, and the safety zone works.** In World D (nav mesh, no zone) she spawned 30 m away and came towards the player. In World B (nav mesh and
  zone) she spawned 34 m away, stopped at 27 m, then was moved to 0, 0, 0. That is the "19 km away" spawn CRD-004 saw: the game putting her away, not
  a failed spawn. In World A (zone, no nav mesh) nothing spawned, as on 17 October. The director's required flag changes between runs of the same save
  (`LABS_EnteredLabs`, then `Residence_Entered`); both are set in Mod Testing, so it did not matter. CordonaCorp has neither, so she cannot appear there.
- **Hook removal: not the parked mods.** It happened again with only our mods installed (fault 2 below).
- **Location banner:** not retested. World B's banner shows on entry; the lab's browser passes a sector name without a claimed level and shows none.
  Matters only if a world needs a banner without a level entry.

### Pass / fail / unknown

| Feature | For | Result | Evidence |
|---|---|---|---|
| All five world paks mount | 2.0 | Pass | `LogPakFile` mounts `Test_P`, `WorldA_P` to `WorldD_P`; object dump of 6 Nov present |
| Hub portals: NUMPAD 1 respawn, NUMPAD 2 remove | 1.0 | Pass | 6 pads removed and spawned; hum applied |
| Portal to a base-game world | 1.0 | Pass | `hub_A4 -> train_start` |
| Way back from a base-game world | 1.0 | **Decision needed** | The Train's way out is its own `train_earlyexit -> train_earlyreturn`, not `train_start`, so `route_return` has no effect. See the list for Portal Hub 1.0 |
| Base-game world's own flags | 1.0 | Pass | `train_end` set `TrainCompletedOnce` |
| Other base-game destinations | 1.0 | Unknown | Pad ids in the GUI match `DT_Levels`; only the Train was walked |
| Entry and exit, home-type custom world | 2.0 | Pass | World A, World D, arrival pad back to the same portal |
| Entry and exit, vignette custom world | 2.0 | Pass | Test World, World B |
| Arrival pad | 2.0 | Pass | Spawned at its spot, returns to the portal used |
| Fall rescue | 2.0 | Pass | World A below -3000, World B below -1000, on arrival pad each time while the tracker runs |
| Vignette claim, banner, lighting, Portal Entrance | 2.0 | Pass | CRD-004, repeated in these runs |
| Portal sickness, completion, exit pad | 2.0 | Pass | See above |
| Leyak safety zone and nav mesh | 2.0 | Pass | See above |
| Weather inside and outside worlds | 2.0 | Unknown | `ActiveWeatherFXName` was `None` in every run; no way to force weather with the cheat mods parked. Needs a weather day |
| Save and reload in the Facility | 1.0 | Pass | CordonaCorp, flags kept |
| Save and reload inside a custom world, first load after launch | 2.0 | Pass | Hold, then back on the ground |
| Save and reload inside a custom world, later loads | 2.0 | **Fail** | Fault 1: falls every time, rescued unless fault 2 hits |
| Completion flags kept across reloads and the update | 2.0 | Pass | Both still set on CordonaCorp |
| Save switch | 1.0 | Pass | Mod Testing to CordonaCorp and back, several times |
| CordonaCorp's mod list | 1.0 | Pass | Whiteboard mod enabled for that save; loads and saves normally |
| Row registry | 1.0 | Pass | See below |
| Delayed callbacks staying alive | 1.0 | **Fail, rare** | Fault 2 |
| Lab: NUMPAD 3, 4, 5, 6, 7, 8, 9, 0, `*`, `/`, `.`, `-`, HOME, F2, F3, F4, F5, PAGE UP, PAGE DOWN | Dev | Pass | PAGE UP and PAGE DOWN are new |
| PortalLogger F6 to F10 | Dev | Unknown | Not pressed; only used for the old proof of concept |
| `PortalHubConfig.ps1` | 2.0 | Pass | `-RoundTrip` on the live config: same lines, `check_config.py` passes; live file untouched |

### Faults

**Fault 1: falling through a world on reload (2.0; not from the update).** `mod/PortalHub/Scripts/main.lua`, `world_is_ready` (line 1148). `worldState` survives a
map load, so after quitting to the menu and reloading (no relaunch) a world still reads "ready" though its level is gone. The tracker skips the hold, the player
falls, and the state only resets when `ensure_worlds` runs about 4 s later. After a relaunch the state is empty, the hold starts within 1 s and the player
lands on the floor. Seen on every in-session reload inside a world, and it is what the author has seen as "sometimes I fall through". **Restore:** in
`world_is_ready`, count "ready" only when `loader_present(def)` is true; otherwise clear the entry so the normal load and hold run. Check `presence.inside`
too: it also survives, so a reload may not claim the world again until the tracker sees the player leave.

**Fault 2: UE4SS drops all delayed callbacks (both, rare).** `Hook threw exception: [Lua::Registry::get_function_ref] Ref was not function ... removing hook!`
from `UE4SS.EngineTick.LuaModImpl`, 1 load in 16, at 21:32:38 on a reload inside World B, 0.6 s after `spawn_all`. The world checks stopped (World D never finished) and
the tracker with them, so the hold never released and the rescue never ran: the player was left stuck under the world until a game restart. Only
our mods were installed, and the lab's own timers were not due yet. **What is known:** it fired while the five world checks and the tracker were all polling. Earlier
sightings were also moments of many queued callbacks. **What is not known:** whether UE4SS or the burst is at fault. **Restore, in order:** run the
world checks in `start_world` (line 610) as one shared loop instead of five chains; then, if it comes back, the controlled UE4SS update (back up the `ue4ss`
folder, keep `Mods\`, latest experimental build, same tests). A one-in-16 fault needs many reloads to judge either way. With no custom worlds there
is no tracker or world check, so 1.0 is far less exposed.

**Not a fault:** a crash in `UE4SS!RC::LuaMadeSimple::handle_error` at 21:40 from stepping lighting rows about five a second (NUMPAD `*`), each queuing a
2 s timer. Dev key only; the author does not count it, and no player can reach it. It is one more sign that bursts of callbacks are what this UE4SS build handles badly.

**Cleanup, harmless:** flag handles have no `DataTablePath` since v1.5.0 (below), but UE4SS ignores the extra field: `HasWorldFlag` and `SetWorldFlag` work
with the hub's table. `flag_table_path` and `flag_handle` in the hub (lines 525-535) and the lab's NUMPAD 3 (lines 932, 956, 968) can drop it.

### Row registry (the CRD-005 question)

- **`BaseTables` holds 113 tables, including `DT_WorldFlags`, `DT_LevelFX` and `DT_Levels`.** The CRD-005 note said `DT_Levels` was not managed; that is corrected there.
- **Rows added with `AddRow` survive.** With hub rows already in both tables, the Whiteboard mod registered, unregistered and registered again (`LogRowRegistry`, prefix
  `NZJKQ`; `RootedModObjects` 5; load order 1). `DT_WorldFlags` stayed at 273 rows and `DT_Levels` at 61, both with their hub rows, and the hub logged no "added"
  line afterwards, which it does when a row is missing.
- **Limit of the test:** one mod that adds no flag or level rows. A mod that adds to those two tables might behave differently. The hub re-adds both rows when
  needed (`ensure_flag_row`, `ensure_level_row`), so the risk stays small.
- `LogRowRegistry` is silent with no mods enabled, so its absence proves nothing.

### For Portal Hub 1.0 (base-game worlds)

- Everything 1.0 needs passed: spawn and removal, entering a base-game world, saves, save switching, official mods side by side.
- **Decide:** a world with its own exits sends players to the game's return point, not the hub portal. The hub's `route_return` only rewrites the arrival pad, and the
  Train does not leave through that. Either accept it (players walk back) or find each world's exit pad and rewrite its `DestinationTeleporterID` too.
  Check a second world before deciding.
- `Divarication` (`V_BOTANICAL`, entrance `botanical_future_01`) is in `DT_Levels` but not in the GUI's destination list.

### Where things moved (for the step-2 docs task)

| What | Before | Now |
|---|---|---|
| Level row struct | Blueprint `LevelMetadata_Struct` | Native `/Script/AbioticFactor.LevelMetadata`; find it through `DT_Levels.RowStruct` |
| Lighting row struct | Blueprint `LevelFXData_Struct` | Native `/Script/AbioticFactor.LevelFXData` |
| Level file field | `LevelFileName` (a name) | `Level` (a soft object: never write it) |
| New level fields | | `bIsSublevel` |
| Flag handle | `{RowName, DataTablePath}` | Native `WorldFlagRowHandle` (base `RowHandle`): `RowName` at offset 8, a hidden field at 0. Library: `/Script/AbioticFactor.WorldFlagHandleFunctionLibrary` (`DoesWorldFlagRowExist`, `Conv_NameToWorldFlag`, `GetAllWorldFlagRowNames`) |
| New flag table type | | `WorldFlagTrigger` (`RequiredWorldFlags`, `WorldFlagToGrant`); teleporters still use a plain `WorldFlagRowHandle` |
| Controller's FX rows | Names | `LevelFXRowHandle` structs: read `.RowName` |
| `DT_Levels` | 60 rows | 60 rows, 61+ with hub rows; 24 portal worlds with `ResettablePortalWorld` |
| `DT_LevelFX` | 153 rows | 153 rows |
| `DT_WorldFlags` | | 271 rows, 273 with two hub flags |
| Buffs table | | `/Game/Blueprints/DataTables/BuffsDebuffs/DT_BuffsDebuffs` (545 rows; `Debuff_PortalSickness` unchanged) |
| Leyak's required flag | `LABS_EnteredLabs` | Varies between runs, also `Residence_Entered` |

**Portal worlds in `DT_Levels` (row, title, entrance pad):** AnteverseA, Far Garden, `anteverse_a_start`; AnteverseB, The Mycofields, `anteverse_b_start`; AnteverseC, Village Den
da'ko Yeer, `anteverse_c_start`; Flathill, `fog_start`; Warehouse, Furniture Store, `warehouse_start`; MirrorWorld, The World in the Mirror, `mirrorworld_start`; Alps, Voussoir,
`alps_start`; Suomi, Shadowgate, `shadowgate_start`; Train, `train_start`; Wall, GATE Arch Defense Facility (N.S.Z.), `wall_start`; HCabin, Unknown Location, `H_Cabin_Start`;
HGarden, Temple of Stone, `H_Garden_Start`; HJapan, Torii, `H_Japan_Start`; Rise, `rise_start`; NightRealm, `nightrealm_start_A`; ArcadeWinter, IS-0083, `VWinter_Start`; Salem, Canaan,
`salem_begin`; V_Inq, The Praetorium, `INQ_Entrance`; V_BOTANICAL, Divarication, `botanical_future_01`; V_ISLAND, Albatross, `island_start`; V_SnowGlobe, North Pole, `V_Snowglobe_Start`;
V_Signal, Dunkeltaler Forest, `signal_start`. All are vignettes (`IsVignette` true). DistantShore (Some Distant Shore) has no entrance listed. Tile is resettable but **not** a vignette, and has no
entrance listed (the GUI's `tile_entrance` is a real pad).

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
