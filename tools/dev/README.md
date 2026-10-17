# Developer helpers

Small tools used while building and testing the Portal Hub. None of them are needed to use the mod.

| File | What it does | Run it with |
|---|---|---|
| `lua_syntax_check.py` | Checks Lua files with a real Lua before they are installed in the game. | `python tools\dev\lua_syntax_check.py mod\PortalHub\Scripts\main.lua` |
| `tests\hub_mock.lua` | A fake of the UE4SS functions the hub uses (controller, pawn, data tables, world, timers), so the hub's real `main.lua` can run outside the game. | used by the tests below |
| `tests\test_hub_vignette.py` | Runs the hub against the mock: level entry, vignette claim and release, lighting switch, title from the loader Blueprint, death, respawn elsewhere, mod restart. | `python tools\dev\tests\test_hub_vignette.py` |
| `tests\test_hub_vignette_type.py` | The vignette world type: completion flag row, zone pointed at it, proper exit pad, on-screen messages. | `python tools\dev\tests\test_hub_vignette_type.py` |
| `check_config.py` | Loads a hub `config.lua` with a real Lua and lists its worlds and portals (catches typos before the game does). | `python tools\dev\check_config.py <path to config.lua>` |
| `read_utoc.py` | Reads a world pak's table of contents (`.utoc`): flags, compression, container id and the list of files (folder, loader, map). Read-only. | `python tools\dev\read_utoc.py <path to .utoc>` |
| `copy_world.ps1` + `rename_world.py` | Copies a test world project under a new name and renames its assets in a headless editor so every reference follows, then reports what it checked. | see the top of `copy_world.ps1` |

The Python helpers need **lupa** (`pip install lupa`). They also look in `%TEMP%\pylib`, where it can be installed with `pip install --target %TEMP%\pylib lupa`.

The mock tests are not proof that something works in the game; they catch mistakes (a misspelt name, a missing function, the wrong order of steps) before a test run in the game.
