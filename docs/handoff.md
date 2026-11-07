# Handoff: where the Portal Hub project stands

Read this at the start of every session, and update it before the session ends with anything new or unfinished.
The order of work lives in [`docs/roadmap.html`](roadmap.html); this note holds what a new session needs on top of that:
the queue, unfinished threads, findings that are not written down anywhere else, open questions, and how to build and test.

Last updated: 6 November 2026 (CRD-013).

## 1. Work queue (the project author's order)

Tasks carry IDs (CRD-nnn); new cards take the next free number. The dispatcher is the pinned "Cordona dispatcher" session.

**Roadmap order (author, 3 November; `docs/roadmap.html` still shows the old one, the step-2 docs task rewrites it):**
(1) find out what broke (CRD-004, then CRD-006); (2) update the docs to show where those details live now; (3) fix custom worlds back
to how they worked before the update; (4) Portal Hub 1.0 (base-game worlds only; the author outlines it after the repairs); (5) resume
custom-world work (CRD-009, lighting, template, exact-spot loading, Facility-area type, auto-detect GUI); (6) Portal Hub 2.0 (custom
worlds = any world not in the base game).

**Task status:**
- CRD-003 game update check: done ([`findings/game-update-2026-10.md`](../findings/game-update-2026-10.md)).
- CRD-004 level and lighting struct fix: done 6 November, confirmed in game on v1.5.0.31876. Vignette worlds are claimed again, Portal
  Entrance works, the lab's level and lighting keys read their rows.
- CRD-006 full post-update assessment: done 6 November ([`findings/game-update-2026-10.md`](../findings/game-update-2026-10.md), "Full assessment"). The hub works on
  v1.5.0.31876. Portal sickness and completion were false alarms (the worlds were already completed in those saves). Row registry: `AddRow` rows survive, and `DT_Levels` is
  managed after all. Two faults left: falling through a world on an in-session reload (`world_is_ready`, stale state) and UE4SS dropping all delayed callbacks (1 load in 16,
  with no third-party mods). The findings note also holds the "where things moved" list for the step-2 docs task. UE4SS stays on the July build until the author decides;
  the plan is one shared world-check loop first, then a controlled update if the fault returns.
- CRD-005 official modding research: done 3 Nov (findings/official-modding-2026-11.md). Keep the UE4SS hub and ~mods world paks: official mods can't add levels or portal worlds, and there is no DT_Levels row type. Still open: test whether the row registry drops the hub's AddRow flag rows, and check the Mod Editor once it is installed. Step 8 stays Nexus/GitHub unless Deep Field allows unofficial uploads on mod.io.
- CRD-007 done 3 Nov: Mod Editor = cooked editor, same 5.4.4 CL 1050002 as the game, all game content cooked in, no level templates or docs; it cooks only UGC plugins at /<PluginName>/, untested from ~mods; step 7 stays on plain UE 5.4 until the world-plugin experiment (CRD-009) says otherwise (findings/official-modding-2026-11.md, addendum).
- CRD-008 retired: its roadmap edits are folded into the step-2 docs task after CRD-006.
- CRD-009 Mod Editor world-plugin experiment: queued.
- CRD-013 config GUI rebuilt in Tkinter: done 6 November, the author signed off on the look. `tools/PortalHubConfig/PortalHubConfig.py` (window title "Cordona Corporations Portal Hub Assistant Tool"), dark purple, slot board plus side panel, Custom Worlds tab. Parity with the `.ps1`, plus the Botanical Wing, optional `arrive`, Hub Exit fields, and editing worlds that hold extra fields. `luaconfig.py` edits only changed values, so comments and unknown keys survive and an unedited save is byte-identical on the live config (the `.ps1` rewrites the file). Tests: `tools/PortalHubConfig/tests/test_luaconfig.py [live config]`, `test_gui.py`. **Decisions (author):** ship a one-folder exe plus the Python source (`build_exe.bat`; `PortalHubConfig.bat` tries exe, then Python, then the `.ps1`); keep shipping the wiki icons, which are the developers' art and outside CC0 (README says so); No Symbol on A-1, A-2 and B-3 (`NO_ENTRY_SLOTS` in `hubdata.py`, a mark only; the Cabin pad is still not refused as a destination). **Open:** the `hubExits` / `hubExitBuff` format is the suggested one, unconfirmed until CRD-012 reports (coordinates expected absolute; the code is one small block in `luaconfig.py`, the BUFF button text is a placeholder); not tried in game, and the exe not tried on another PC or against antivirus (unsigned); the `.ps1` stays until retired; the Botanical Wing is listed as two Story destinations, "Botanical Wing (Present)" (`botanical_present_01`, a pad in the Facility's persistent level per the teleporter dump) and "Botanical Wing (Future)" (`botanical_future_01`, Divarication), author's decision 7 November; no wiki icon for either; looks (Red for present, Green for future) inferred. **Botanical Wing return route (inferred, untested):** the two pads are the game's own link between the halves, so `route_return` would probably repoint whichever one a hub portal arrives at and cut players off from the other half; the author wants it as the first Hub Exit test, which also needs `route_return` to leave that arrival pad alone.

The numbered items below are the older detail on each piece of work.

1. **CRD-001, step 1, vignette confirmation: done 17 October.**
   - **Custom title works:** `WorldTitle` ('Spell ICUP') on `BP_World_B_Loader` became World B's level entry title and banner.
   - **Shared chunk id is harmless so far:** World C rebuilt on chunk 92 has the same container id as World B (`2990919af0b18c3a`); both mounted with no warning, both streamed in, entered and left without a crash. World C is still installed on chunk 92 (its project's `PAL_World_C` says 92). Not checked: whether anything goes wrong when two such worlds hold files of the *same* path (they can't in practice: each world has its own folder).
   - **Fixed after the test:** on every save load the hub showed "Test World completed: portal sickness lifted for good" and the game logged `HasWorldFlag ... ran before world flags were loaded` every 2 s. The hub asked for the flag before the save's flags were loaded (answer: false), then saw it turn true. It now waits for `WorldFlagSubsystem:HasWorldFlagsLoaded()` (first use of that function; installed, mock-tested, not yet confirmed in game).
2. **CRD-002, settings in the world's Blueprint: done, committed 27 October (515aaff); partly confirmed in game (see the list at the end of this item).** The hub reads 13 plain variables from the
   loader Blueprint's class defaults (`WorldTitle`, `WorldType`, `NoWeather`, `LeyakSafeZone`, `LightingDay`, `LightingNight`,
   `ArriveSpot`/`ArriveYaw`, `ExitSpot`/`ExitYaw`, `KillZ`, `Radius`); Blueprint > `config.lua` > default. Map-maker docs:
   [`docs/world-settings.md`](world-settings.md). Read once by `apply_world_settings` when the loader class is in memory, logged as
   one line `settings from its loader Blueprint: ...`. `arrive` is now optional in `config.lua` (default 0, 0, 0, 0). Mock-tested
   (`tools/dev/tests/test_hub_world_settings.py`, 27 checks) and installed. **Not yet known:** whether this UE4SS build reads Blueprint
   Float (a double in UE 5.4) and Vector variables as numbers (answered: it does, see the test below). Stays in `config.lua`: loader
   paths, `level`, `origin`, the portal, and the `lighting` block (left for roadmap step 3). Proposed, not built: Target Point
   actors tagged `PortalHubArrive` / `PortalHubExit` instead of typed spots (end of `docs/world-settings.md`), for the custom-exit step.
   **In-game test 17 October (CordonaCorp):** World B (all seven variables) and World D (`NoWeather`, `LeyakSafeZone` off, `Radius`) read
   correctly, Float and Vector included; arrival and exit pads, the -1000 rescue and completion all worked.
   **Leyak (Mod Testing save):** the director needs story flag `LABS_EnteredLabs` (else `CanSpawn()` is false and `Server_ForceSpawn`
   does nothing), and a world needs a **nav mesh** (Nav Mesh Bounds Volume + Build Paths): without one the director's spawn search finds
   no ground and she never comes; with one she appeared in World D (22.9 m away). World B with a nav mesh and the safety zone: tested 6 November, the zone works (section 5).
   A world's title banner only shows while `NoWeather` is on (it comes with the claimed level entry).
   **Lighting default is now `Intro`** (author, 17 October): a world without `LightingDay` (or with an unknown row) is lit with the
   game's bright intro row, logged as "no lighting set ... using Intro". (Tried first: "none", keeping the game's current rows; on a
   weather day that showed the weather inside no-weather worlds A and C, so it was dropped.) `NoWeather` stays on by default: weather
   in a world is the map maker's choice. The dev lab got a lighting browser (NUMPAD 0 list, NUMPAD * / NUMPAD / step,
   NUMPAD . back). The author stepped through all 153 rows in World D on 17 October: catalogue with measured sun / sky / fog and
   the particles seen is in [`docs/lighting-rows.md`](lighting-rows.md). `DT_LevelFX:FindRow` returns a userdata struct, not a Lua table, so the lab reads
   rows field by field through the row struct's `ForEachProperty` (fixed under CRD-004). Open: why `HGarden` / `HJapan` look unlit in a
   basic-block world (sun 0; probably the home maps' own lights and dynamic sky), and what `HShip` / `HTerminal` are.
   **Retested 6 November after the struct fix (CRD-004), v1.5.0.31876:**
   - **Confirmed:** `Intro` fallback lighting in Test World, A and C; World B's `LightingDay` Office1; NUMPAD 1 respawns the portals (no
     stuck check to recover in that run, so the dropped-timer recovery itself is still untested); World B's title banner; lab F5 no-clip
     (was F1), F2 save position, F3 kill; the lab's level and lighting keys.
   - **Moved to CRD-006, now answered:** the World B proper exit and the Leyak zone test both work (section 5).
3. **Lighting** (roadmap step 2): day and night lighting of our own; dynamic like Stone Garden, static like Albatross. See section 5 for what is known.
4. **Skyboxes**: first how to make a custom skybox, then test the dynamic skybox (`HasDynamicSkybox` on rows like `HGarden`; does it explain why home rows look unlit in a basic-block world?). 5. **Music and ambient tracks**, 6. **Custom exit** (a coordinate in the Facility), 7. **Full tutorial**, 8. **Mod packaging** (GUI work, one mod, Nexus presets). Details on each card in the roadmap.

## 2. Unfinished threads

- **Design direction (author, 17 October):** the hub is a connection hub, not a driving dependency. Map makers bake every setting they can into their world's loader Blueprint (plain value variables only: Text, Name, Boolean, Float, Integer, Vector; never asset references), and `config.lua` keeps only what belongs to the hub (slot, position in hub space). Worlds *may* depend on the hub, but they shouldn't have to. Next, after the item 1 tests: list which settings can move into the Blueprint, build the reading, and document each variable for map makers. Built (queue item 2): every per-world setting except the loader paths, `level`, `origin` and the `lighting` block. `arrive` is optional in the GUI since CRD-013.
- **GUI: edit any world directly** (author's wish, 17 October): part of roadmap step 7.
- **Waypoint / position tool for the dev lab (not shipped):** saving and printing the spot relative to the world's origin is done (lab F2, 18 October); still open: naming spots and teleporting back to them. Written from the game's own functions (`K2_GetActorLocation`, `K2_TeleportTo`, the character's `TeleportPlayer`, all in our object dump), not copied from any other mod. The lab's numpad keys are almost all used, so this probably needs UE4SS console commands (not tried in our mods yet: give it its own test). A trimmed hub debugger for release comes later.

- **World settings to the GUI (designed, not built):** the GUI reads a world pak's `.utoc` file list (folder, loader, map: readable without the game) to add a world in one click and pick a free position and slot; the hub reads the map maker's Blueprint settings in game and writes a small catalog file the GUI shows after one launch; players' overrides are saved by the GUI and applied by the hub. Part of roadmap step 7.
- **Loading a save made inside a world** puts the player on the arrival pad rather than where they saved (they fall during the loading screen, before the hub can hold them; the fall rescue catches it). The author has not said whether keeping the exact spot matters. CRD-006 found why: after a relaunch the hold works and the player lands on the floor; on an in-session reload `worldState` still says "ready", so the hold is skipped (findings note, fault 1).
- **Loading a save made inside a world** also leaves the level entry's previous row as the text `None`, so leaving logs "level entry back to None, lighting left to the game". The game put its own row back within seconds (6 November). Harmless so far; treating `None` as unknown would send it to the fallback row.
- **`ActiveWeatherFXName`** stays `Weather_Fog` inside our worlds (real vignettes show `None`); the fog is gone visually because the lighting rows are switched. Left alone unless it turns out to matter.
- **Editor bulk-fix scripts** (`tools/UnrealEditorScripts`) are shelved; the author fixes materials and collision by hand.
- **Material Lab** has a few duplicate local functions (`value_text`, `dump_fx_struct`, `level_fx_rows`); harmless clutter.

## 3. Where things are

| What | Where |
|---|---|
| The hub mod | `mod/PortalHub/Scripts/main.lua` (+ `slots.lua`, `config.lua` template) |
| Dev survey mod (not shipped) | `mod/PortalMaterialLab/Scripts/main.lua` |
| Config editor (GUI) | `tools/PortalHubConfig/PortalHubConfig.py` (+ `luaconfig.py`, `hubdata.py`), built by `build_exe.bat`, started by `PortalHubConfig.bat`; the older `PortalHubConfig.ps1` stays as a fallback |
| Dev helpers and mock tests | `tools/dev/` (see its README) |
| Docs and research notes | `docs/` (roadmap, Test World walkthrough, world settings for map makers), `findings/` |
| Game install | `%USERPROFILE%\Games\Steam Library\steamapps\common\AbioticFactor\AbioticFactor` |
| Installed mods, log, object dump | `<game>\Binaries\Win64\ue4ss\` (`Mods\`, `UE4SS.log`, `UE4SS_ObjectDump.txt`) |
| **Live hub config** (not the repo copy) | `<game>\Binaries\Win64\ue4ss\Mods\PortalHub\Scripts\config.lua`: Test World on A-3 (vignette, exit `{0,500,0,0}`), the Train on A-4, World A-D on C-1 to C-4 |
| World paks | `<game>\Content\Paks\~mods\` (`Test_P`, `WorldA_P` ... `WorldD_P`) |
| Game log and crash reports | `%LOCALAPPDATA%\AbioticFactor\Saved\Logs\`, `...\Saved\Crashes\` |
| Test world projects (git-ignored) | `TestWorld\AbioticFactor\`, `World Projects\World A-D\` (README there with names, chunks 91-94, hub entries) |
| Unreal Engine 5.4 | `%USERPROFILE%\Games\UE5\UE_5.4` |
| Third-party reference mod (git-ignored, never copied or named in the repo) | `External Mods\` |

## 4. Build, run and test

- **Install a mod change:** edit the repo file, check it with `python tools\dev\lua_syntax_check.py <file>`, run the mock tests (`python tools\dev\tests\test_hub_vignette.py`, `test_hub_vignette_type.py`, `test_hub_world_settings.py`, `test_hub_dropped_timers.py`, `test_hub_level_struct.py` and, for the lab, `test_lab_assessment.py`; if they fail with "no attribute 'LuaRuntime'", the temp copy of lupa was cleared: `pip install --upgrade --target %TEMP%\pylib lupa`), then copy `main.lua` into `<game>\...\ue4ss\Mods\<Mod>\Scripts\` and confirm the copy is identical (file hash).
- **Test in game:** the author runs the game and presses keys; the session reads `UE4SS.log` afterwards (it is overwritten at each launch and lags; the game log keeps backups). Mods can be reloaded without restarting the game (Restart All Mods in the UE4SS GUI, Ctrl+O toggles it); the author often does that, so in-memory state (added data-table rows, controller values) carries over.
- **Lab keys:** NUMPAD 3 clears Portal Hub completion flags in the save; NUMPAD 7 vignette zones, buffs, tags, flags and the exit offset; NUMPAD 8 level table and where the game thinks the player is; NUMPAD 9 one-line status (level name, vignette, weather). NUMPAD 0 lists every lighting row (DT_LevelFX) with its sun, sky, fog and temperature values; NUMPAD * / NUMPAD / apply the next / previous row and show its name on screen, NUMPAD . gives the lighting back (use outside no-weather worlds; the hub puts their lighting back). NUMPAD - surveys the Leyak director (required story flag, CanSpawn, cooldown, active Leyak); F4 turns on the director's debug messages and calls its `Server_ForceSpawn`. HOME is the player lighting survey. F3 kills the player (a point hit of the game's `DamageType_DeathPit`, then the character's `IsDead` + `OnRep_IsDead` if still alive). F5 toggles no-clip (collision off, flying) and F2 saves the player's position (feet, yaw; also relative to the custom world it lies in, read from the hub's live config.lua, ready for ArriveSpot / ExitSpot), both with an on-screen message; F2 appends to `ue4ss\Mods\PortalMaterialLab\saved_positions.txt` (confirmed in game 6 November). PAGE UP lists flags in the save, the hub's rows in `DT_WorldFlags` and `DT_Levels`, the row registry's `BaseTables`, zones and pads; PAGE DOWN asks the same through the flag library and shows the load order. Every pad use is logged by itself (`pad use: ...`), with whether its flag was set 1.5 s later. All read-only except NUMPAD 3, the lighting keys, F2 (only its text file), F3, F4 and F5. Hub keys: NUMPAD 1 respawn portals, NUMPAD 2 remove them. PortalLogger: F6-F10. **Key rule (author, 4 November):** single keys with no Ctrl hold; never W A S D E F R Q Tab, the number row, G Z X C V B; stay off the game's own F1 (player list), F10 (HUD) and + (pager).
- **Installed mods are only ours (6 November):** Hub, Lab, Logger, the disabled PoC, plus UE4SS's `shared` and `Keybinds`. Everything else was moved, not deleted, to `ue4ss\Mods_parked` with the old `mods.txt` as `mods.txt.before`: the item spawner (its item commands are broken by the update), the cheat-command mod, and UE4SS's console and cheat-manager enablers and Blueprint mod loader. So there is no tilde console. Ctrl + J (object dump) still works.
- **Package a world:** in its project, package for Windows; take only `pakchunkNN-Windows.pak/.ucas/.utoc` (NN = the world's chunk id), rename the three to `<Name>_P.*`, put them in `<game>\Content\Paks\~mods\`. Never install `pakchunk0-*` or `global.*` (they crash the game). Details in `docs/test-world-walkthrough.md`.
- **Copy a test world:** `tools\dev\copy_world.ps1` (headless editor; the editor must not have the projects open).
- **Read a world pak's file list:** `python tools\dev\read_utoc.py <...>\WorldA_P.utoc`.
- **Headless Unreal editor:** `UnrealEditor-Cmd.exe <project>.uproject -run=PythonScript -Script=<file.py> -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout`. Passing `None` into the material-editing library crashes the editor; check every value first.
- **Crash dumps:** `cdb.exe` is at `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64`. Run it locally on `UEMinidump.dmp` with `-y`/`-i` pointing at the ue4ss folder (no symbol downloads); `.ecxr; kn` shows where it died.
- **Saves:** the mod testing save is **`CordonaCorp`** (`%LOCALAPPDATA%\AbioticFactor\Saved\SaveGames\<steam id>\Worlds\CordonaCorp`); it is fine if a test breaks it, so no backup is needed. **`stahp` is the author's personal playthrough: never use it for tests or change it.**

## 5. Findings that are not written down elsewhere yet

These came out of in-game tests on 13-16 October 2026 (and an offline check on 17 October). They belong in `findings/` and the tutorial eventually.

**How the game decides where the player is**
- The Facility map holds about 224 `AbioticLevelStreamingVolume`s; the `LevelManagerSubsystem` tracks which level the player is in, and the controller's `Attempt Level FXChange` looks that level up in **`DT_Levels`** (`/Game/Blueprints/DataTables/Environment/DT_Levels`, rows of native `/Script/AbioticFactor.LevelMetadata` since v1.5.0, a Blueprint struct before it: `ReleaseGroup`, `Level`, `LevelFXRow_Day/Night`, `SectorName`, `bIsSublevel`, `ResettablePortalWorld`, `HasFacilityShakes`, `IsVignette`, `EntranceTeleporter`). **`Level` is a soft-object field that replaced the old name `LevelFileName`; never write it.** UE4SS's `AddRow` leaves fields missing from the Lua table at their defaults, so the hub just leaves it out. The row struct is found through `DT_Levels.RowStruct`, which reads fine from Lua. The added row stays while the game runs (row count 60 to 61). Custom worlds are never reported by the level manager.
- The player controller's **`ActiveLevelFXName`** (a Name) holds the current `DT_Levels` row name (`office1`, `V_ISLAND`); `PlayerIsInVignette` and the respawn menu's Portal Entrance read it. **`ActiveLevelName`** (a String) holds the level's file name (`Facility_Office1`, `H_Garden`). The hub adds a row `PortalHub_<id>` and writes both on arrival, then restores them on leaving.
- **Lighting rows:** `TransitionToNewEnvironmentFX(UseCurrentFX, DayFX, NightFX, Speed, SectorName)` takes two **DataTableRowHandles** `{DataTable = DT_LevelFX, RowName = ...}` (not row data) and an FText; the game shows the SectorName as the location banner. The controller's `Day_FX_Row`/`Night_FX_Row` are `LevelFXRowHandle` structs: read `.RowName`, not the property itself (reading it as a name gave nil and the hub re-applied the lighting every 3 s). Weather works by swapping them to `Weather_Fog` / `Weather_Fog_Night`, so switching to the world's rows removes the weather's look. `DT_LevelFX` rows (native `/Script/AbioticFactor.LevelFXData`) carry sun, sky, fog, colour grading, music (`MusicTracks`), ambient sound, temperature, weather particle and `HasDynamicSkybox`. Idea for custom lighting: `AddRow` a copy of an existing row, then edit the copy's values; beware its soft-object fields (see the crash rule below).
- `DetermineCorrectWeatherFX()` and `OnWeatherUpdated(Name)` do not clear weather by themselves. `Trigger_WeatherBlocker` is a story trigger that ends the weather for everyone: never spawn it.

**Zones, world types and flags**
- Homes and vignettes both hold a `Vignette_Zone` (a `BuffZone_ParentBP`) giving `Buff_InVignette` (tag `Character.InVignette`). A vignette's zone also names a story flag (`PortalSicknessWorldFlag`, e.g. `TrainCompletedOnce`); until it is set the player has `Debuff_PortalSickness` (equipment locked). Most worlds also hold a `LeyakSafetyZone` (`Buff_LeyakSafetyZone`). The zone classes are only in memory after something loaded them; the hub loads them itself (`LoadAsset` of `<package>.<name>` worked).
- Story flags: table `DT_WorldFlags` (row struct `WorldFlag`: `ReleaseGroup`, `DebugText`); handles are `{RowName, DataTablePath}` (copy the path from a `BP_Teleporter_HomeWorld_C`'s `RequiredWorldFlag`). `WorldFlagSubsystem:SetWorldFlag(handle, state, context)`, `HasWorldFlag(context, handle)`, `GetWorldFlags(out)` (its items must be unwrapped with `:get()`). Since v1.5.0 a handle is the native `WorldFlagRowHandle` with no `DataTablePath`; UE4SS ignores that extra field, so tables still work. A flag already set in a save never changes, so a test of completion needs a world whose flag is clear (NUMPAD 3, or check PAGE UP first). A teleporter's `WorldFlagToTriggerOnUse` sets a flag when used: that is how a vignette's proper exit works. Saves store flags as plain names, so removing a world's mod leaves one harmless unused name.
- The respawn menu (`W_RespawnOptions`) is already built before mods load, so watching for it to be created never fires.
- On-screen messages: the player character's `Client_DisplayWarningMessage(FText, colour, beep)`; colours 0 green, 1 gray, 2 yellow, 3 red, 4 purple.

**Killing the player (6 November):** the character reacts only to point and radial damage, and takes nothing from the engine's plain `DamageType`. A point hit of `DamageType_DeathPit` kills at once (health 371 to 0). `Server_PerformDeathSequence` alone does nothing.

**Leyak after the update (6 November, CRD-006):** the director's required story flag changes between runs of the same save (`LABS_EnteredLabs`, `Residence_Entered`). World D (nav mesh, no zone): she spawns 30 m away and comes towards the player. World B (nav mesh and zone): she spawns about 34 m away, stops at 27 m, then the game moves her to 0, 0, 0, so that spot means she was put away, not a failed spawn. World A (zone, no nav mesh): nothing spawns.

**UE4SS (this build) quirks**
- **Crash rule:** never pass `nil`, a table or a made-up value to a **soft-object or soft-class parameter** from Lua: it crashes the game inside UE4SS (`push_softobjectproperty`), and `pcall` cannot catch it. Also never call methods on an invalid object (check `IsValid()` first).
- Write `ActiveLevelName` (a String property) only as a Lua string; writing an FName corrupted it and crashed the game.
- `UDataTable` has Lua methods: `GetRowNames`, `FindRow`, `AddRow(name, table)`, `RemoveRow`, `ForEachRow`.
- Out-parameter arrays come back wrapped; unwrap items with `:get()` when `:ToString()` fails. `FText("...")` works.
- `ok and v or nil` turns `false` into `nil` in Lua; use explicit `if`s for booleans.
- **Restart All Mods can drop queued timers.** A timer left from the old Lua state fires after the restart ("Hook threw exception:
  Ref was not function, removing hook!", then "Freed invalid callbacks"), and the `ExecuteWithDelay` callbacks queued in that tick are
  lost (17 October: worlds A-D never got their loading check, their portals stayed off). Since then NUMPAD 1 restarts a world's
  loading check or the tracker that has not run for 10 s; each loop has a generation number, so only the newest copy keeps running.
  When the whole game-tick hook is removed, though, nothing delayed runs for any mod (not even NUMPAD 1) until a full game restart. Both
  times this happened the third-party cheat-command mod was enabled and the mods were restarted, so it is **disabled again** (18 October:
  `Mods\CheatConsoleCommands\enabled.txt` renamed to `enabled.txt.disabled`). The lab's F5 no-clip and F2 save position replace it.
  **Third sighting, 6 November:** 7 s after switching saves in game, with no mod restart; the item spawner and the enablers were
  installed, and the item spawner had thrown errors a few minutes earlier. All delayed callbacks stopped and the keys went dead. With
  those mods parked, two save switches in the next run went clean. The error means the callback's Lua reference was already released when it fired.
  **Fourth sighting, 6 November (CRD-006):** on a reload inside World B with only our mods installed, so the parked mods are not the cause: 1 load in 16. Details and the plan
  are in the findings note, fault 2.

**World paks**
- **Container id = CityHash64 of the build name**, lower-cased, as UTF-16LE bytes (`pakchunk92-windows` → `2990919af0b18c3a`); it matches all five installed paks (Test_P = chunk 90, World A-D = 91-94). It is baked into the `.utoc`, so renaming the files does not change it: two worlds built with the same chunk id always share a container id. The game itself only uses chunk 0 (`pakchunk0`, `pakchunk0optional`). The GUI can warn about a clash by reading the id from each `.utoc`.
- A world pak's `.utoc` is Oodle-compressed but neither encrypted nor signed, and it lists every file, so the folder, loader and map can be read without the game. Blueprint values are inside the Oodle-compressed `.ucas`; the game builds Oodle into its program (no DLL to borrow, and none could be shipped in a CC0 project).

## 6. Questions waiting on the author

- UE4SS: shared world-check loop first and a controlled update only if the hook fault returns, or update now?
- Portal Hub 1.0: a base-game world with its own exits (the Train) drops players at the game's return point, not the hub portal. Accept that, or rewrite those exit pads too?
- Push the latest local commits to GitHub? (Pushing always waits for a yes.)
- Should loading a save inside a world keep the player's exact spot (needs an earlier hold), or is the arrival pad fine?
- Build the GUI auto-detect and catalog now, or after lighting?
- Keep the Test World as a vignette (`type = "vignette"` and `exit` in the live config) or switch it back to a home?
