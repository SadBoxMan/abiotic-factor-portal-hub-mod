# Handoff: where the Portal Hub project stands

Read this at the start of every session, and update it before the session ends with anything new or unfinished.
The order of work lives in [`docs/roadmap.html`](roadmap.html); this note holds what a new session needs on top of that:
the queue, unfinished threads, findings that are not written down anywhere else, open questions, and how to build and test.

Last updated: 17 October 2026.

## 1. Work queue (the project author's order)

1. **Step 1, vignette confirmation: done 17 October.**
   - **Custom title works:** `WorldTitle` ('Spell ICUP') on `BP_World_B_Loader` became World B's level entry title and banner.
   - **Shared chunk id is harmless so far:** World C rebuilt on chunk 92 has the same container id as World B (`2990919af0b18c3a`); both mounted with no warning, both streamed in, entered and left without a crash. World C is still installed on chunk 92 (its project's `PAL_World_C` says 92). Not checked: whether anything goes wrong when two such worlds hold files of the *same* path (they can't in practice: each world has its own folder).
   - **Fixed after the test:** on every save load the hub showed "Test World completed: portal sickness lifted for good" and the game logged `HasWorldFlag ... ran before world flags were loaded` every 2 s. The hub asked for the flag before the save's flags were loaded (answer: false), then saw it turn true. It now waits for `WorldFlagSubsystem:HasWorldFlagsLoaded()` (first use of that function; installed, mock-tested, not yet confirmed in game).
2. **Settings in the world's Blueprint** (author's direction, see section 2): list them, build the reading, document each variable for map makers.
3. **Lighting** (roadmap step 2): day and night lighting of our own; dynamic like Stone Garden, static like Albatross. See section 5 for what is known.
4. **Skyboxes**, 5. **Music and ambient tracks**, 6. **Custom exit** (a coordinate in the Facility), 7. **Full tutorial**, 8. **Mod packaging** (GUI work, one mod, Nexus presets). Details on each card in the roadmap.

## 2. Unfinished threads

- **Design direction (author, 17 October):** the hub is a connection hub, not a driving dependency. Map makers bake every setting they can into their world's loader Blueprint (plain value variables only: Text, Name, Boolean, Float, Integer, Vector; never asset references), and `config.lua` keeps only what belongs to the hub (slot, position in hub space). Worlds *may* depend on the hub, but they shouldn't have to. Next, after the item 1 tests: list which settings can move into the Blueprint, build the reading, and document each variable for map makers. Read today: `WorldTitle`, `WorldType`, `LeyakSafeZone`. Candidates: `NoWeather`, `LightingDay`/`LightingNight`, `KillZ`, arrival and exit spots (a marker actor in the map is probably friendlier than coordinates).
- **GUI: edit any world directly** (author's wish, 17 October): part of roadmap step 7.
- **Waypoint / position tool for the dev lab (not shipped):** save the player's spot by name, teleport back to it, print the spot relative to the current world's origin in `config.lua` format. Written from the game's own functions (`K2_GetActorLocation`, `K2_TeleportTo`, the character's `TeleportPlayer`, all in our object dump), not copied from any other mod. The lab's numpad keys are almost all used, so this probably needs UE4SS console commands (not tried in our mods yet: give it its own test). A trimmed hub debugger for release comes later.

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
- **Saves:** the mod testing save is **`CordonaCorp`** (`%LOCALAPPDATA%\AbioticFactor\Saved\SaveGames\<steam id>\Worlds\CordonaCorp`); it is fine if a test breaks it, so no backup is needed. **`stahp` is the author's personal playthrough: never use it for tests or change it.**

## 5. Findings that are not written down elsewhere yet

These came out of in-game tests on 13-16 October 2026 (and an offline check on 17 October). They belong in `findings/` and the tutorial eventually.

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
- **Container id = CityHash64 of the build name**, lower-cased, as UTF-16LE bytes (`pakchunk92-windows` → `2990919af0b18c3a`); it matches all five installed paks (Test_P = chunk 90, World A-D = 91-94). It is baked into the `.utoc`, so renaming the files does not change it: two worlds built with the same chunk id always share a container id. The game itself only uses chunk 0 (`pakchunk0`, `pakchunk0optional`). The GUI can warn about a clash by reading the id from each `.utoc`.
- A world pak's `.utoc` is Oodle-compressed but neither encrypted nor signed, and it lists every file, so the folder, loader and map can be read without the game. Blueprint values are inside the Oodle-compressed `.ucas`; the game builds Oodle into its program (no DLL to borrow, and none could be shipped in a CC0 project).

## 6. Questions waiting on the author

- Push the latest local commits to GitHub? (Pushing always waits for a yes.)
- Should loading a save inside a world keep the player's exact spot (needs an earlier hold), or is the arrival pad fine?
- Build the GUI auto-detect and catalog now, or after lighting?
- Keep the Test World as a vignette (`type = "vignette"` and `exit` in the live config) or switch it back to a home?
