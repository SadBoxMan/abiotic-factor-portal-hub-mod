# Portal Hub select beta: tester notes

Thanks for testing! This is a private beta of the Portal Hub (by Cordona Corporations) for Abiotic Factor, not a public release.
Everything here is for testing with the host; please don't pass it on.

There are two packs:
- **Run-1 pack** (`CordonaBeta-run1`): the probe, the four test worlds and the config editor. No Portal Hub inside: your first run is
  with the hub off, so this is all you need to start.
- **Full pack** (`CordonaBeta-full`): everything above plus the Portal Hub itself, for run 2. Install it over the run-1 pack.

## 1. Install UE4SS first (not included)

UE4SS is someone else's tool, so it is not in this zip. Get **"UE4SS for Abiotic Factor", version 1.25.0 or later**, from its Nexus
Mods page: https://www.nexusmods.com/abioticfactor/mods/35
Follow that page's install steps. When it is right, the game folder has `AbioticFactor\Binaries\Win64\ue4ss\` with a `Mods` folder in it.
Start the game once and quit, so UE4SS sets itself up.

The game folder is usually `...\Steam\steamapps\common\AbioticFactor` (in Steam: right-click the game > Manage > Browse local files).
Below, `<game>` means that folder.

## 2. Where each folder in this zip goes

| In the zip | Copy it to |
|---|---|
| `Mods\CordonaProbe\` | `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\CordonaProbe\` |
| `Mods\PortalHub\` (full pack only) | `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\` |
| `Paks\WorldA_P.pak/.ucas/.utoc` ... `WorldD_P.*` (12 files) | `<game>\AbioticFactor\Content\Paks\~mods\` (make the `~mods` folder if it isn't there) |
| `PortalHubConfig\` and `PortalHubConfig.bat` | anywhere you like, kept side by side (for example your desktop) |

## 3. Switch the mods on: `mods.txt`

Open `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\mods.txt` in Notepad and add these lines **above** the `Keybinds : 1` line:

    CordonaProbe : 1
    PortalHub : 0

- **Run 1:** `PortalHub : 0` (hub off). With the run-1 pack you can leave the PortalHub line out for now.
- **Run 2:** change it to `PortalHub : 1`, then restart the game. Before run 2, open the config editor (`PortalHubConfig.bat`) and set
  up a config that is deliberately **different** from the host's (the host will tell you what to pick).

If you have other UE4SS mods (cheats, item spawners), please switch them off (`: 0`) for these runs, so the logs only show ours.

## 4. Keys

| Key | What it does |
|---|---|
| `]` | Probe: writes a survey to the UE4SS log (who you are, which portals you can see, how loud they are). Read-only, safe to press any time. Typing `]` in chat also runs it, which is harmless. **Not a US keyboard?** On a US layout it is the key two to the right of `P` (`OEM_6`); on your layout it may sit elsewhere. Tell the host your layout if `]` does nothing. |
| DELETE | Probe: spawns or removes a test button in front of the player. Host only. |
| NUMPAD 1 | Portal Hub (run 2): respawn the hub portals. |
| NUMPAD 2 | Portal Hub (run 2): remove the hub portals. |
| Ctrl + O | UE4SS's own window (its console shows the log live). |

None of these clash with the game's normal controls: the game uses `]` and NUMPAD 1/2 only for developer debug actions, and DELETE
only to clear a key while rebinding in the Controls menu (pressing it there also toggles the test button; harmless).

## 5. Logs to send back

UE4SS **overwrites its log every time the game starts**, so copy it **before** restarting for run 2, and again at the end:
- `<game>\AbioticFactor\Binaries\Win64\ue4ss\UE4SS.log`
- `%LOCALAPPDATA%\AbioticFactor\Saved\Logs\AbioticFactor.log` and the `-backup-` files from that evening
  (paste `%LOCALAPPDATA%\AbioticFactor\Saved\Logs` into the Explorer address bar)
- `%LOCALAPPDATA%\AbioticFactor\Saved\Crashes\` if anything crashed
- your `Mods\mods.txt` and, for run 2, `Mods\PortalHub\Scripts\config.lua`

If the game crashes, stop, keep the logs and the crash folder, and send them before trying again.

## 6. Removing it afterwards

Delete `Mods\CordonaProbe\`, `Mods\PortalHub\`, the twelve `World?_P.*` files in `Content\Paks\~mods\`, and the two lines in `mods.txt`.
Your saves are not changed by the probe; the hub only adds its own flags. Test in a spare save, not your main playthrough.

## Licence

The mods, the test worlds and the config editor are the project's own work, released under CC0 1.0 (see `LICENSE.txt`). The world
pictures in the config editor are the game developers' art, shown for recognition only; they are not covered by CC0.
