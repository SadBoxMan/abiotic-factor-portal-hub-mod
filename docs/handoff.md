# Handoff: where the Portal Hub project stands

Read this at the start of every session, and update it before the session ends with anything new or unfinished.
The order of work lives in [`docs/roadmap.html`](roadmap.html); this note holds what a new session needs on top of that:
the queue, unfinished threads, findings that are not written down anywhere else, open questions, and how to build and test.

Last updated: 17 October 2026.

## 1. Work queue (the project author's order)

1. **Finish step 1, vignette confirmation.** Two tests, both need the author in the editor:
   - **Custom title:** add a Text variable `WorldTitle` to `BP_World_B_Loader` in the World_B project, repackage, install as `WorldB_P`. Expected: the entry banner shows that title instead of "World B". (The hub reads it; tested only against the mock so far.)
   - **Chunk id:** set `PAL_World_C`'s Chunk ID to 92 (same as World_B), repackage (output becomes `pakchunk92-Windows.*`), install as `WorldC_P`. If World B and World C both still load, reusing chunk ids is harmless. Hypothesis: the IoStore container id comes from the build name (`pakchunk92-Windows`), so two worlds with the same chunk id may clash. Each installed world pak currently has a different container id (read with `tools/dev/read_utoc.py`).
2. **Lighting** (roadmap step 2): day and night lighting of our own; dynamic like Stone Garden, static like Albatross. See section 5 for what is known.
3. **Skyboxes**, 4. **Music and ambient tracks**, 5. **Custom exit** (a coordinate in the Facility), 6. **Full tutorial**, 7. **Mod packaging** (GUI work, one mod, Nexus presets). Details on each card in the roadmap.

## 2. Unfinished threads

- **World settings to the GUI (designed, not built):** the GUI reads a world pak's `.utoc` file list (folder, loader, map: readable without the game) to add a world in one click and pick a free position and slot; the hub reads the map maker's Blueprint settings in game and writes a small catalog file the GUI shows after one launch; players' overrides are saved by the GUI and applied by the hub. Part of roadmap step 7.
- **Loading a save made inside a world** puts the player on the arrival pad rather than where they saved (they fall during the loading screen, before the hub can hold them; the fall rescue catches it). The author has not said whether keeping the exact spot matters.
- **`ActiveWeatherFXName`** stays `Weather_Fog` inside our worlds (real vignettes show `None`); the fog is gone visually because the lighting rows are switched. Left alone unless it turns out to matter.
- **Editor bulk-fix scripts** (`tools/UnrealEditorScripts`) are shelved; the author fixes materials and collision by hand.
- **Material Lab** has a few duplicate local functions (`value_text`, `dump_fx_struct`, `level_fx_rows`); harmless clutter.

## 3. Where things are

| What | Where |
|---|---|
| The hub mod | `mod/PortalHub/Scripts/main.lua` (+ `slots.lua`, `config.lua` template) |
| Dev survey mod (not shipped) | `mod/PortalMaterialLab/Scripts/main.lua` |
| Config editor (GUI) | `tools/PortalHubConfig/PortalHubConfig.ps1`, started by `PortalHubConfig.bat` |
| Dev helpers and mock tests | `tools/dev/` (see its README) |
| Docs and research notes | `docs/` (roadmap, Test World walkthrough), `findings/` |
| Game install | `%USERPROFILE%\Games\Steam Library\steamapps\common\AbioticFactor\AbioticFactor` |
| Installed mods, log, object dump | `<game>\Binaries\Win64\ue4ss\` (`Mods\`, `UE4SS.log`, `UE4SS_ObjectDump.txt`) |
| **Live hub config** (not the repo copy) | `<game>\Binaries\Win64\ue4ss\Mods\PortalHub\Scripts\config.lua`: Test World on A-3 (vignette, exit `{0,500,0,0}`), the Train on A-4, World A-D on C-1 to C-4 |
| World paks | `<game>\Content\Paks\~mods\` (`Test_P`, `WorldA_P` ... `WorldD_P`) |
| Game log and crash reports | `%LOCALAPPDATA%\AbioticFactor\Saved\Logs\`, `...\Saved\Crashes\` |
| Test world projects (git-ignored) | `TestWorld\AbioticFactor\`, `World Projects\World A-D\` (README there with names, chunks 91-94, hub entries) |
| Unreal Engine 5.4 | `%USERPROFILE%\Games\UE5\UE_5.4` |
| Third-party reference mod (git-ignored, never copied or named in the repo) | `External Mods\` |

## 4. Build, run and test

- **Install a mod change:** edit the repo file, check it with `python tools\dev\lua_syntax_check.py <file>`, run the mock tests (`python tools\dev\tests\test_hub_vignette.py` and `test_hub_vignette_type.py`), then copy `main.lua` into `<game>\...\ue4ss\Mods\<Mod>\Scripts\` and confirm the copy is identical (file hash).
- **Test in game:** the author runs the game and presses keys; the session reads `UE4SS.log` afterwards (it is overwritten at each launch and lags; the game log keeps backups). Mods can be reloaded without restarting the game (Restart All Mods in the UE4SS GUI, Ctrl+O toggles it); the author often does that, so in-memory state (added data-table rows, controller values) carries over.
- **Lab keys:** NUMPAD 3 clears Portal Hub completion flags in the save; NUMPAD 7 vignette zones, buffs, tags, flags and the exit offset; NUMPAD 8 level table and where the game thinks the player is; NUMPAD 9 one-line status (level name, vignette, weather). All read-only except NUMPAD 3. Hub keys: NUMPAD 1 respawn portals, NUMPAD 2 remove them.
- **Package a world:** in its project, package for Windows; take only `pakchunkNN-Windows.pak/.ucas/.utoc` (NN = the world's chunk id), rename the three to `<Name>_P.*`, put them in `<game>\Content\Paks\~mods\`. Never install `pakchunk0-*` or `global.*` (they crash the game). Details in `docs/test-world-walkthrough.md`.
- **Copy a test world:** `tools\dev\copy_world.ps1` (headless editor; the editor must not have the projects open).
- **Read a world pak's file list:** `python tools\dev\read_utoc.py <...>\WorldA_P.utoc`.
- **Headless Unreal editor:** `UnrealEditor-Cmd.exe <project>.uproject -run=PythonScript -Script=<file.py> -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout`. Passing `None` into the material-editing library crashes the editor; check every value first.
- **Crash dumps:** `cdb.exe` is at `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64`. Run it locally on `UEMinidump.dmp` with `-y`/`-i` pointing at the ue4ss folder (no symbol downloads); `.ecxr; kn` shows where it died.
- **Save backup:** the author's test save is `stahp` (`%LOCALAPPDATA%\AbioticFactor\Saved\SaveGames\<steam id>\Worlds\stahp`). Back it up before risky tests.

## 5. Findings that are not written down elsewhere yet

These came out of in-game tests on 13-16 October 2026. They belong in `findings/` and the tutorial eventually.

**How the game decides where the player is**
- The Facility map holds about 224 `AbioticLevelStreamingVolume`s; the `LevelManagerSubsystem` tracks which level the player is in, and the controller's `Attempt Level FXChange` looks that level up in **`DT_Levels`** (`/Game/Blueprints/DataTables/Environment/DT_Levels`, rows of `LevelMetadata_Struct`: `LevelFileName`, `IsVignette`, `EntranceTeleporter`, `LevelFXRow_Day/Night`, `SectorName`, `ResettablePortalWorld`, `HasFacilityShakes`, `ReleaseGroup`). Custom worlds are never reported by the level manager.
- The player controller's **`ActiveLevelFXName`** (a Name) holds the current `DT_Levels` row name (`office1`, `V_ISLAND`); `PlayerIsInVignette` and the respawn menu's Portal Entrance read it. **`ActiveLevelName`** (a String) holds the level's file name (`Facility_Office1`, `H_Garden`). The hub adds a row `PortalHub_<id>` and writes both on arrival, then restores them on leaving.
- **Lighting rows:** `TransitionToNewEnvironmentFX(UseCurrentFX, DayFX, NightFX, Speed, SectorName)` takes two **DataTableRowHandles** `{DataTable = DT_LevelFX, RowName = ...}` (not row data) and an FText; the game shows the SectorName as the location banner. Weather works by swapping the controller's `Day_FX_Row`/`Night_FX_Row` to `Weather_Fog` / `Weather_Fog_Night`, so switching to the world's rows removes the weather's look. `DT_LevelFX` rows (`LevelFXData_Struct`) carry sun, sky, fog, colour grading, music (`MusicTracks`), ambient sound, temperature, weather particle and `HasDynamicSkybox`. Idea for custom lighting: `AddRow` a copy of an existing row, then edit the copy's values; beware its soft-object fields (see the crash rule below).
- `DetermineCorrectWeatherFX()` and `OnWeatherUpdated(Name)` do not clear weather by themselves. `Trigger_WeatherBlocker` is a story trigger that ends the weather for everyone: never spawn it.

**Zones, world types and flags**
- Homes and vignettes both hold a `Vignette_Zone` (a `BuffZone_ParentBP`) giving `Buff_InVignette` (tag `Character.InVignette`). A vignette's zone also names a story flag (`PortalSicknessWorldFlag`, e.g. `TrainCompletedOnce`); until it is set the player has `Debuff_PortalSickness` (equipment locked). Most worlds also hold a `LeyakSafetyZone` (`Buff_LeyakSafetyZone`). The zone classes are only in memory after something loaded them; the hub loads them itself (`LoadAsset` of `<package>.<name>` worked).
- Story flags: table `DT_WorldFlags` (row struct `WorldFlag`: `ReleaseGroup`, `DebugText`); handles are `{RowName, DataTablePath}` (copy the path from a `BP_Teleporter_HomeWorld_C`'s `RequiredWorldFlag`). `WorldFlagSubsystem:SetWorldFlag(handle, state, context)`, `HasWorldFlag(context, handle)`, `GetWorldFlags(out)` (its items must be unwrapped with `:get()`). A teleporter's `WorldFlagToTriggerOnUse` sets a flag when used: that is how a vignette's proper exit works. Saves store flags as plain names, so removing a world's mod leaves one harmless unused name.
- The respawn menu (`W_RespawnOptions`) is already built before mods load, so watching for it to be created never fires.
- On-screen messages: the player character's `Client_DisplayWarningMessage(FText, colour, beep)`; colours 0 green, 1 gray, 2 yellow, 3 red, 4 purple.

**UE4SS (this build) quirks**
- **Crash rule:** never pass `nil`, a table or a made-up value to a **soft-object or soft-class parameter** from Lua: it crashes the game inside UE4SS (`push_softobjectproperty`), and `pcall` cannot catch it. Also never call methods on an invalid object (check `IsValid()` first).
- Write `ActiveLevelName` (a String property) only as a Lua string; writing an FName corrupted it and crashed the game.
- `UDataTable` has Lua methods: `GetRowNames`, `FindRow`, `AddRow(name, table)`, `RemoveRow`, `ForEachRow`.
- Out-parameter arrays come back wrapped; unwrap items with `:get()` when `:ToString()` fails. `FText("...")` works.
- `ok and v or nil` turns `false` into `nil` in Lua; use explicit `if`s for booleans.

**World paks**
- A world pak's `.utoc` is Oodle-compressed but neither encrypted nor signed, and it lists every file, so the folder, loader and map can be read without the game. Blueprint values are inside the Oodle-compressed `.ucas`; the game builds Oodle into its program (no DLL to borrow, and none could be shipped in a CC0 project).

## 6. Questions waiting on the author

- Push the latest local commits to GitHub? (Pushing always waits for a yes.)
- Should loading a save inside a world keep the player's exact spot (needs an earlier hold), or is the arrival pad fine?
- Build the GUI auto-detect and catalog now, or after lighting?
- Keep the Test World as a vignette (`type = "vignette"` and `exit` in the live config) or switch it back to a home?
