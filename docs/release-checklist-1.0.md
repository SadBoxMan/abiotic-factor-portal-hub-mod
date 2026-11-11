# Portal Hub 1.0 release checklist (Saturday 14 November 2026)

For CRD-015. The builder is `tools/release/build_release.py`; the player README is `tools/release/README-player.md` (it ships as
`README.md`); the Nexus page text is `tools/release/nexus-description.md`. **Publishing is LuciDin's:** he creates the Nexus page,
uploads the file and pushes to GitHub. Sessions only build, check and install on his word.

**Scope (LuciDin, 10 November):** 1.0 is the hub for the game's own worlds. The custom-world code stays in, unsupported, and the World
A-D paks ship as an optional "2.0 teaser" folder. Client mode ships as **experimental** multiplayer. A demo preset (`Presets/config-demo.lua`)
ships, made by LuciDin in the GUI. The old `PortalHubConfig.ps1` is retired (deleted).

## 1. Before Saturday

- [ ] The last two-player test(s) are done and anything that blocks a release is fixed and committed.
- [ ] Card C decided: the hub's NUMPAD 1 / 2 sit on the game's debug-only camera-shake actions (`DebugCameraShake`,
      `DebugDecreaseCameraShake`; not in the Controls list). Accept as is, or move them (then update `KNOWN_BINDS` in the builder and the README).
- [ ] The demo preset is LuciDin's (`tools/release/config-demo.lua`, not the provisional copy of the beta config).
- [ ] The installed `manual_exits.lua` is copied back into the repo if any MHE was recorded since (`git diff` shows it), and committed.
- [ ] Every change to ship is committed (the builder reads **HEAD only**; a working-tree file never reaches the zip).

## 2. Nexus page and URL (LuciDin)

1. On Nexus Mods, create the mod page for Abiotic Factor (it can stay unpublished / hidden while you set it up). Title, summary and
   description: from `tools/release/nexus-description.md`. Category: probably "Gameplay" or "Utilities"; requirements: UE4SS for
   Abiotic Factor (mod 35). Tags and images as you like.
2. Copy the page's URL (`https://www.nexusmods.com/abioticfactor/mods/<number>`).
3. A session pastes it into `PORTAL_HUB_NEXUS_URL` in `tools/PortalHubConfig/install_check.py` (the line under the
   `TODO(CRD-015, LuciDin)` comment), runs the GUI tests, and commits it through the approval path.

## 3. Build

    python tools\release\build_release.py --final

- `--final` refuses to build while the Nexus URL is empty. Without it you get a test build with a warning.
- It builds the config editor exe from HEAD's sources (PyInstaller, about a minute), strips the dev keys from the packaged `main.lua`
  (the repo file keeps them), runs the syntax check and `test_hub_client_mode.py` + `test_hub_reload.py` on the packaged copy, checks
  the path allowlist, scans every file for third-party and private names, and prints the key binds that ship.
- Output (git-ignored): `Release\PortalHub-1.0.0.zip`, `Release\PortalHub-1.0.0-files.txt` (path, size, SHA-1; also inside the zip
  as `FILES.txt`) and the unpacked copy in `Release\stage\`. The last line gives the zip's SHA-1 and the commit.
- Expected key binds: NUMPAD 1 and NUMPAD 2 only.
- Before any build or commit: `python tools\dev\lua_syntax_check.py mod\PortalHub\Scripts\main.lua`, the hub tests in `tools\dev\tests`,
  `tools\PortalHubConfig\tests\*` and `python tools\release\tests\test_build_release.py`.

## 4. Install the zip into the game (LuciDin's beta install)

The game install is LuciDin's **beta install** (CRD-024): stock UE4SS 1.25.0 with `GuiConsoleEnabled = 1`, the probe, worlds A-D and the
hub. A session installs only on his yes, and says what it changed.

1. **Back up first:** copy `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\` whole to
   `<game>\AbioticFactor\Binaries\Win64\hub_backup_<date>_pre-1.0\` and `mods.txt` beside it.
2. **Copy the installed `manual_exits.lua` back into the repo** if it differs from the repo's (it holds recordings); commit it
   and build again before installing. Never copy over it unseen.
3. Install from the zip's `PortalHub 1.0.0\AbioticFactor\` exactly as the README says (merge into `<game>`). Keep LuciDin's
   own `config.lua`, or use the zip's template or the demo preset for a clean check (say which).
4. Teaser worlds: copy `Optional - 2.0 teaser worlds\AbioticFactor\` in too. The installed `World?_P.*` should already be
   byte-identical; compare the SHA-1s with `FILES.txt`.
5. Check the installed hub files against `FILES.txt` (SHA-1) and that `mods.txt` has `PortalHub : 1`. Switch the probe off
   (`CordonaProbe : 0`) for a release-like run.
6. Unzip the editor somewhere else (the desktop, for example), double-click `PortalHubConfig.bat`, check that the install line says
   INSTALLED, and look at the SmartScreen prompt (More info > Run anyway), so the README's words match what players see.

## 5. Smoke test (LuciDin runs the game; a session reads `UE4SS.log`)

Use the **CordonaCorp** or **Mod Testing** save, never `stahp`.

| Key | Run it in | What it logs |
|---|---|---|
| (none, load the save) | Main menu > CordonaCorp | `loaded - NUMPAD 1 respawn portals, NUMPAD 2 remove them` with **no** `END` in it; `client mode: on`; `tracker: watching N custom world area(s)` |
| (walk in) | Portal room | `N of N configured portal(s) spawned`; `hum volume (dynamic) x... on N hub pad(s)`; every configured slot shows its portal |
| END | Anywhere | Nothing. No `Hub Exits test` message on screen, no log line (the dev key is gone) |
| (use a hub portal, then the world's exit) | Portal room > a base-game world (the Train on A-4, `exits: game`) | `hub exits: ... entered train_start through hub portal hub_A4`; the exit lands where the game sends you |
| (use the MHE) | Inside the Train | `hub exits: ... used the MHE of train_start, to hub_A4`; you land in front of hub portal A-4 |
| (manual portal) | A slot set to `manual` (Far Garden on B-1 in the beta config) | `used the manual portal of anteverse_a_start, back to hub_B1` on the way back |
| (teaser world) | Portal room > World B (C-2) | `worlds: world_b_start is ready after ... s, hub portals to it are on`; the trip in and back works |
| NUMPAD 2 | Portal room | `removed N pad(s)`; the hub portals vanish |
| NUMPAD 1 | Portal room | `NUMPAD 1 pressed`, then `N of N configured portal(s) spawned` again |
| Ctrl + O > Restart All Mods | Portal room | The `loaded - ...` line again, then the spawn line; no `Ref was not function` |
| (save inside World B, load it) | World B | `hold: ... held in place until it is ready`, then `hold: the world is ready`; the hub portals spawn at once (CRD-028); World B's pad works right away |
| (quit) | — | Search the whole log for `Ref was not function` and `error`: none expected |

Afterwards: put the probe back on if the next two-player test needs it (`CordonaProbe : 1`), and say what is installed now.

## 6. Upload (LuciDin)

1. Nexus page > Manage > Files: upload `Release\PortalHub-1.0.0.zip`. Name "Portal Hub 1.0.0", version `1.0.0`, category Main
   Files. Description: one line, e.g. "Portal Hub 1.0 with the config editor, a demo preset and the optional 2.0 teaser worlds."
2. Requirements tab: UE4SS for Abiotic Factor (mod 35), "Lua mod loader, 1.25.0 or later".
3. Publish the page.
4. Optional: download the uploaded file again and compare its SHA-1 with the builder's last line.
5. GitHub: push the release commits (LuciDin pushes). A tag `v1.0.0` on the built commit is optional.
6. Tell the dispatcher it is out; the CRD-015 row in `docs/handoff.md` goes to `done`.

## 7. Not in 1.0 (for the record)

Custom worlds as a supported feature (2.0, against the Full Understanding list), per-save config, the in-game portal console, a
trimmed debug key set, a signed exe.
