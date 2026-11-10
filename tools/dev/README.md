# Developer helpers

Small tools used while building and testing the Portal Hub. None of them are needed to use the mod.

| File | What it does | Run it with |
|---|---|---|
| `lua_syntax_check.py` | Checks Lua files with a real Lua before they are installed in the game. | `python tools\dev\lua_syntax_check.py mod\PortalHub\Scripts\main.lua` |
| `tests\hub_mock.lua` | A fake of the UE4SS functions the hub uses (controller, pawn, data tables, world, timers), so the hub's real `main.lua` can run outside the game. | used by the tests below |
| `tests\test_hub_vignette.py` | Runs the hub against the mock: level entry, vignette claim and release, lighting switch, title from the loader Blueprint, death, respawn elsewhere, mod restart. | `python tools\dev\tests\test_hub_vignette.py` |
| `tests\test_hub_world_settings.py` | World settings on the loader Blueprint (title, type, no weather, Leyak zone, lighting rows, arrival and exit spots, kill height, radius): the Blueprint wins over `config.lua`, which wins over the defaults. | `python tools\dev\tests\test_hub_world_settings.py` |
| `tests\test_hub_dropped_timers.py` | Timers lost on a mods restart: the world's loading check and the tracker are restarted by NUMPAD 1, and never run twice. | `python tools\dev\tests\test_hub_dropped_timers.py` |
| `tests\test_hub_reload.py` | Save reloads inside a custom world, with five worlds and a player who falls unless held or on a visible level: held, landed and claimed once each across ten reloads, a reload while loading, into another world and into the Facility; all loading worlds share one timer chain. An optional path runs it on another `main.lua`. | `python tools\dev\tests\test_hub_reload.py` |
| `tests\test_hub_level_struct.py` | The game's level row struct in each layout: native since game update v1.5.0 (through `DT_Levels.RowStruct`, or its `/Script` path), the old Blueprint struct, none. The level entry is added without ever writing the soft-object `Level` field; leaving puts the level name back. The mock models the native struct by default (`LEGACY_LEVEL_STRUCT` / `NO_ROW_STRUCT` switch it). | `python tools\dev\tests\test_hub_level_struct.py` |
| `tests\test_hub_vignette_type.py` | The vignette world type: completion flag row, zone pointed at it, proper exit pad, on-screen messages. | `python tools\dev\tests\test_hub_vignette_type.py` |
| `tests\test_hub_exits.py` | Hub Exits (CRD-012): the exit modes (game, hub, dynamic per player, manual), MHEs and the Failsafe Exit, the world's exits found by list, arrival pad or distance, manualBuffs, NUMPAD 1 reading `manual_exits.lua` again. | `python tools\dev\tests\test_hub_exits.py` |
| `tests\test_lab_hub_exit_preview.py` | The lab's INSERT: the Hub Exit preview, recording a world's MHE (or the Failsafe Exit in the portal room) into the hub's `manual_exits.lua`, linking a mode-4 portal at once, one MHE per world; also that both mods bind only real UE4SS key names and stay off DELETE and F11. | `python tools\dev\tests\test_lab_hub_exit_preview.py` |
| `check_config.py` | Loads a hub `config.lua` with a real Lua and lists its worlds and portals (catches typos before the game does). | `python tools\dev\check_config.py <path to config.lua>` |
| `read_utoc.py` | Reads a world pak's table of contents (`.utoc`): flags, compression, container id and the list of files (folder, loader, map). Read-only. | `python tools\dev\read_utoc.py <path to .utoc>` |
| `copy_world.ps1` + `rename_world.py` | Copies a test world project under a new name and renames its assets in a headless editor so every reference follows, then reports what it checked. | see the top of `copy_world.ps1` |

The Python helpers need **lupa** (`pip install lupa`). They also look in `%TEMP%\pylib`, where it can be installed with `pip install --target %TEMP%\pylib lupa`.

The mock tests are not proof that something works in the game; they catch mistakes (a misspelt name, a missing function, the wrong order of steps) before a test run in the game.
