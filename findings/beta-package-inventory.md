# CRD-024: select beta package (inventory)

Built 10 November 2026 by `tools/beta/build_beta.py` into `Beta\` at the repo root (git-ignored; the zips are never committed).
A private beta for a few testers (LuciDin's two-player test, `findings/two-player-test-plan.md`), not a public release. Delivered through
LuciDin's Drive (he uploads). Each build also writes `Beta\<name>-files.txt` (every file with size and SHA-1 prefix).

| Pack | Zip | Contents |
|---|---|---|
| Run 1 | `CordonaBeta-run1-2026-11-10.zip` (19.2 MB, 1030 files) | probe, worlds A-D, config editor, README, licence; no Portal Hub |
| Full | `CordonaBeta-full-2026-11-10.zip` (19.3 MB, 1034 files) | the same plus `Mods\PortalHub\` from 2745f2d (CRD-027 + CRD-028); built 10 November |

## What is in the zip, where it comes from, and its licence

| In the zip | Source | Licence / status |
|---|---|---|
| `README.md` | `tools/beta/README-tester.md` | ours, CC0 |
| `LICENSE.txt` | `LICENSE` (CC0 1.0) | — |
| `Mods/CordonaProbe/Scripts/main.lua` | `mod/CordonaProbe/Scripts/main.lua` (identical to the installed copy) | ours, CC0 |
| `Paks/World[A-D]_P.pak/.ucas/.utoc` (12) | `World Projects/Builds/` (identical to the installed `~mods` copies) | ours, CC0; contents checked in `findings/world-upload-inventory.md` (no game assets; the Ruins textures cleared by LuciDin on 9 November) |
| `PortalHubConfig.bat` | `PortalHubConfig.bat` (finds `PortalHubConfig\PortalHubConfig.exe` next to it) | ours, CC0 |
| `PortalHubConfig/PortalHubConfig.exe` | `tools/PortalHubConfig/dist/` (built 10 November 01:02 by `build_exe.bat`, PyInstaller 6.22.3, after the last source edit) | our program, CC0; the PyInstaller bootloader is GPL with an exception that allows any licence for the bundled program |
| `PortalHubConfig/_internal/icons/*.png` (20) | `tools/PortalHubConfig/icons/` (fetched by `Get-WorldIcons.ps1` from the game wiki) | **the game developers' art, outside CC0**; shown for recognition only (same files as in the public repo) |
| `PortalHubConfig/_internal/` (the rest, ~990 files) | Python 3.12 runtime collected by PyInstaller: `python312.dll`, `base_library.zip`, Tcl/Tk 8.6 (`tcl86t.dll`, `tk86t.dll`, `_tcl_data`, `_tk_data`, `tcl8`), Pillow (`PIL`), OpenSSL (`libcrypto-3`, `libssl-3`), libffi, zlib, `VCRUNTIME140.dll`, the Universal CRT (`ucrtbase.dll`, `api-ms-win-*.dll`) | third-party, all redistributable with an app: PSF licence, Tcl/Tk BSD-style, Pillow MIT-CMU, OpenSSL Apache 2.0, libffi MIT, zlib licence, Microsoft's Visual C++ / UCRT redistributable terms |
| `Mods/PortalHub/Scripts/main.lua` (full only) | `mod/PortalHub/Scripts/main.lua` at 2745f2d, with `local DEV_KEYS = true` changed to `false` in the packaged copy only | ours, CC0 |
| `Mods/PortalHub/Scripts/slots.lua`, `manual_exits.lua` (full only) | `mod/PortalHub/Scripts/` (`manual_exits.lua` identical to the installed one, 10 November) | ours, CC0 |
| `Mods/PortalHub/Scripts/config.lua` (full only) | `tools/beta/config-beta.lua`: the repo template with worlds A-D defined and on C-1 to C-4, other slots free (no Test World) | ours, CC0 |

## Left out

The lab (`PortalMaterialLab`), PortalLogger (its F10 is the game's HUD key), PortalPoC, the old `PortalHubConfig.ps1` (does not know exit
modes or MHEs), the Test World (`Test_P`), `config.lua.bak`, UE4SS itself (the README links its Nexus page), the cheat-command mod, the item
spawner and UE4SS's test mods, `Cordona Local Patches`, and anything from `External Mods`.

## Flags for LuciDin

- The GUI's world pictures are the developers' art. They are already in the public repo; shipping them to a few testers is the same exposure.
- The UE4SS link in the README is `nexusmods.com/abioticfactor/mods/35`: confirmed, the 1.25.0 zip LuciDin downloaded in CRD-026 carries mod id 35 in its file name.
- A fresh UE4SS install has its GUI window off (`GuiConsoleEnabled = 0`); the README tells testers to switch it on for Ctrl+O and Restart All Mods.
