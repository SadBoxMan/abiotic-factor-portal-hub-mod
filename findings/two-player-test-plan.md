# Two-player test plan (CRD-023)

Date: 10 November 2026. This is a desk check of `mod/PortalHub/Scripts/main.lua` (CRD-022 state, commit 4b00e30), the probe
(`mod/CordonaProbe/`) and the game's own input config. No game run has been done for it yet. Everything so far was tested solo on the host,
so this note sets out what one evening with a second player must answer. The host is LuciDin; the friend joins.

## 1. What is true today

### 1a. Do the host's hub settings apply to everyone?

**No. Nothing in the hub tells host from client.** `main.lua` never checks authority (no `HasAuthority`, no net mode, no local-controller
test). Every machine that has the hub installed runs all of it, on its own `config.lua`:

| Part | What a client with the hub does today (from the code) | Which config wins |
|---|---|---|
| Hub pads | When a Homeworld pad appears, `spawn_all` runs on the client too. It tries to destroy every `hub_*` pad, but the engine refuses to destroy a replicated actor without authority, so the host's pads stay. Then it spawns its **own** pads from its own config. A pad spawned on a client stays on that client (local authority, never sent to the server). | **Duplicates.** The host's replicated pads and the client's local ones stand together. Same slot, same ID: two pads in one spot. Different configs: the client also sees pads only it has, or a different look on the same slot. |
| Where a pad leads | Probably decided where the teleport runs. The host is the only one that knows the host's pads, so a client stepping into a host pad should be teleported by the host's config. A client-only pad is unknown to the server: its teleport would run on the client (if at all) and be corrected or rubber-banded. | Host for host pads (expected; must be tested). |
| Look and light (`apply_design`, `apply_light`) | Set on the machine that spawned the pad. A particle asset and a light colour are component settings, not replicated. | A client with no hub probably sees the host's pads in the **default** look. A client with the hub sees its own pads in its own look. |
| Exit modes (`dynamic`, `hub`, `manual`), MHEs, failsafe | The `AttemptTeleport` hook runs on the host for every player (`InPlayer`), so the host moves a client to the hub portal by its own config. If the hook also fires on the client, the client's hub moves its own pawn as well: a double move, by the client's config. | Host, if the hook fires only there (test). |
| `manualBuffs` | Host: `Server_ApplyBuff` on the client's character, which is fine on the server. A client with the hub calling it as well would add a second request. | Host (test for double buffs). |
| Custom worlds (loaders, arrival pads, zones) | Each machine spawns its own loader actor and streams the level itself. Whether the host's loader also replicates is unknown. | Unknown: the riskiest part (double level instances, or none on a client with no hub). |
| Presence tracker (vignette claim, lighting, fall rescue, hold on load) | Tracks one pawn per machine, found by `FindFirstOf("Abiotic_PlayerController_C")`. **On the host that can be a client's controller** (every player has one on the host), so the host's own claim, lighting and rescue could follow the wrong player. On a client it tracks the client, but teleports (rescue) and `ActiveLevelFXName` writes made on a client probably do not reach the server. | Each machine for itself; the host part may follow the wrong player. |
| Hum volume | Each machine, its own config (see 1b). | Local. |
| Keys NUMPAD 1 / 2 / END | Each machine acts on its own hub: on a client, NUMPAD 1 respawns its own duplicates. | Local. |

**Does per-save config (CRD-018) cover this? No.** Per-save only decides *which* config the host's hub uses. It does not stop a client
from running its own hub, spawning its own pads or acting on its own exits. The rule CRD-018 already wrote ("only the host applies
per-save overrides; a client uses its global config") assumes the client's hub does something, and today that something is a whole
second hub. What is missing is a **client mode**: where the machine has no authority, the hub spawns nothing, hooks no exits and moves
no one, and keeps only the local, cosmetic parts (hum volume, perhaps look and light re-applied to the host's pads). With that in place,
per-save fits on top unchanged, and players with different local settings can play together. Card A below.

The evening has to answer the parts the code cannot: do the host's pads replicate (with their IDs, active state and hidden flag), does
the teleport run on the host, does the hook fire on a client, and what a client with no hub at all gets. If a client with no hub gets
working portals, then "host settings for everyone" is already true for players without the mod, and client mode only has to make
installed copies stand down.

### 1b. Portal volume

**It is client-side already, by its nature.** The hum is the pads' `PortalHumLoop` audio component, set with
`SetVolumeMultiplier` (`apply_hum`, `main.lua` around line 220). Audio is never replicated, so each machine hears what its own hub set,
from its own `humMode` / `humFloor` / `humManual`. A host-set volume is **not possible** without code on the client: the host cannot
reach a client's audio component.

What that means today:
- A client with **no hub** hears every pad at the game's default (x1.0), the host's added pads too, so a full portal room is louder for
  them than for the host (LuciDin's live config: `manual` x0.15).
- A client **with the hub** sets the volume only on pads it found when its own `spawn_all` ran. The host's pads may replicate in later
  and keep x1.0. The "dynamic" step is also counted from the client's own config, not from the pads that are really there.
- The fix belongs in client mode (card A): apply the client's own hum setting to every hub pad it sees, again whenever a new hub pad
  arrives, counting the pads that are actually there.

### 1c. Tested only solo so far

- Exit modes for a joining player: `dynamic` per player (END only stood in for a second player), `hub` (never tried at all), `manual` +
  MHE, the Failsafe Exit, `game`.
- `manualBuffs` (never tried in game, even solo).
- Hub pads and their looks as a client sees them; hum volume on a client.
- The presence tracker for a second player: vignette claim, portal sickness message, lighting, fall rescue, hold on load (all per machine,
  see 1a).
- Reload paths: host Restart All Mods and NUMPAD 1 with a client connected; a client joining while the host stands in a custom world; a
  client joining or rejoining while standing inside one; the CRD-011/022 hold and claim retry for a client.
- Custom worlds A-D for a client (streaming, arrival pad, title banner, lighting, `NoWeather`).
- The probe console button (CRD-020 open points 1-4): what a client sees, whether a client's press reaches the host's hook, the save
  name on a client.
- The 9 November, 21:49 question: a player went back into `hub_B1` 2 s after a `dynamic` early-exit move put them in front of it. Was the
  landing spot too close to the portal, or did the player walk back in? (The UE4SS log of that run has been overwritten, so only a
  retest can tell.)

**Probe solo check (10 November, 01:45-01:47, CordonaCorp, LuciDin):** `]` gave the full survey: save name, `1 player controller(s)`,
10 hub pads with no duplicates, and 13 room and hub pads with their look and hum. The hub portals read x0.150, as the live config says.
The MHE and failsafe pads read x1.000, since `apply_hum` touches only the hub-room pads. DELETE spawned the button, two presses reached
the hook (`press 1`, `press 2`), and DELETE removed it. F11 only toggled fullscreen. No `Ref was not function`. The in-game Controls
list (Settings > Input Bindings) has no entry on `]`, Delete, End or any numpad key except NumPad + (Activate Pager); the debug
actions are not listed there. LuciDin's own additions: Holster also on Mouse 5, Crafting panel also on Mouse 4.

## 2. Keys for the beta

Bindings checked (10 November, v1.5.0.31876):
- The game's default input config: the `ActionMappings`, `AxisMappings`, `DebugExecBindings` and `ConsoleKeys` lines in `pakchunk0-Windows.pak`
  (the config text is stored uncompressed and was read with a text search; nothing was extracted or changed).
- LuciDin's own overrides in `%LOCALAPPDATA%\AbioticFactor\Saved\Config\Windows\Settings.ini` (AutoSettings `InputMappingManager`: Holster on
  Mouse 5 and H, Flashlight on the middle mouse button, Crafting panel on Mouse 4).
- UE4SS's `Keybinds` mod (all Ctrl + key) and every key our own mods register.
- The wiki has no controls page (`/wiki/Controls` and `/wiki/Keybinds` return 404). **LuciDin: during the solo check, open Settings >
  Controls and look for `]`, Delete, End and NumPad 1 / 2.** The pak config is the source the Controls list is built from, so no
  surprises are expected.

| Key | Mod | Game's default binding | Verdict |
|---|---|---|---|
| `]` (UE4SS `Key.OEM_SIX`) | Probe: survey (was F11) | `DebugCycleCultureBack` (a debug action) | Author's choice (10 November). Typing `]` in text chat also runs the survey (harmless, read-only). On non-US keyboard layouts `OEM_SIX` is a different physical key: ask the friend which layout they use. |
| DELETE | Probe: spawn / remove the test button (host only) | `UIClearKeybind`, only in the Controls menu | Kept (author, 10 November). Pressing it while rebinding a key in the Controls menu also spawns or removes the button. |
| NUMPAD 1 | Hub: respawn portals, read `manual_exits.lua` again | `DebugCameraShake` (debug) | Ships in the hub today; for LuciDin to accept or move (card C). |
| NUMPAD 2 | Hub: remove portals | `DebugDecreaseCameraShake` (debug) | As NUMPAD 1. |
| END | Hub: pretend to be Player 2 (`DEV_KEYS`) | none | Not needed with a real second player. The package ships `DEV_KEYS = false` (LuciDin, 9 November). |
| F11 | (old probe survey) | Fullscreen toggle | Moved off. |

Host-only lab keys that help in the run (the lab is not packaged): NUMPAD 9 (status line: level row, vignette, weather) and F2 (save
position) have no game binding. Don't press the lab's F3 during the run: the game binds F3 to `BetaFeedback`, and the lab's F3 kills the
player. PortalLogger's F10 is the game's HUD toggle, so the Logger stays off and out of the package.

Other single keys, checked at the author's request: `'` is free. `,` `.` `/` are free as plain keys (the game binds them only with
Ctrl + Shift, as debug commands). `-` and `=` are free but sit on the number row. `;` is the engine's debug camera (debug builds). `\` is the
game's `GameCommandMenu` (a real action). `` ` `` (tilde) is the console. `[` is `DebugCycleCulture`. F12, Pause and Scroll Lock are free
in the game (F12 is Steam's screenshot key). Every numpad key is taken: the game binds NumPad 1-3 and NumPad +, and our hub and lab use
the rest.

## 3. What each player installs (feeds CRD-024's package)

| Item | Host (LuciDin) | Friend |
|---|---|---|
| UE4SS for Abiotic Factor 1.25.0 or later (Nexus; not bundled: it is a third-party download) | yes (installed) | yes |
| `PortalHub` (package build: `DEV_KEYS = false`) | yes | **installed, switched off** (`PortalHub : 0` in `mods.txt`) for run 1, on for run 2 |
| `CordonaProbe` (keys `]` and DELETE) | yes | yes |
| World paks A-D (`World Projects/Builds/WorldA_P` ... `WorldD_P`, into `Content\Paks\~mods\`) | yes (installed) | yes (needed for the custom-world rows and for any host slot that points at them) |
| Config GUI (`tools/PortalHubConfig`, exe + source) | yes | yes: makes run 2's deliberately different config easy |
| Lab (`PortalMaterialLab`) | optional, host only, not packaged | no |
| Not in the package | PortalLogger, PortalPoC, the cheat-command mod, the item spawner and UE4SS's own test mods (switch them off in `mods.txt` for a clean host run), any private local fix of a test aid, anything from the third-party reference mod | |

**Host config for the evening** (LuciDin sets it with the GUI before the friend joins; only worlds the friend also has):
- Phase 1: A-4 The Train `exits = hub`; B-1 Far Garden `exits = dynamic`; C-1 to C-4 Worlds A-D as now. **Take the Test World off A-3:** it is
  not in the package, so a client who used that slot would land in a world they don't have.
- Phase 2 (changed in the GUI, then Restart All Mods on the host, which is a test row of its own): B-1 Far Garden `exits = manual`,
  BUFFS ON (`manualBuffs = true`); A-4 off, so the Train's MHE leads to the Failsafe Exit.
- Keep `humMode = "manual"`, `humManual = 0.15` on the host so the volume difference is easy to hear.

**Friend's config for run 2** (deliberately different): a different world on B-1 (for example Flathill) and on one free slot the host
leaves empty, `exitMode = "game"`, `humMode = "manual"`, `humManual = 1.0`.

## 4. The evening's test table

Run 1 is with the friend's hub off; run 2 is with it on (the friend sets `PortalHub : 1` and restarts the game; the host keeps the save
running). Both players say the time aloud at each row, and the host notes it. Saves: CordonaCorp or Mod Testing (never `stahp`).

| # | Key / action | Run it in | Host logs (`UE4SS.log`) | Friend logs / reports |
|---|---|---|---|---|
| 0 | Host loads the save, friend joins | Facility | Hub: portals spawned, `hum volume (manual) x0.150` | Probe: `identity (mod load)`, then at portal-spawn time (save name on a client: open point 4) |
| 1 | `]` on both, standing in the portal room | Portal room | `2 player controller(s)`, every `hub_*` pad `role=Authority`, look and hum per pad | Which pads arrived: IDs (or `None`), `role=SimulatedProxy`, look (default or the host's), hum (expect 1.000), duplicate IDs (none in run 1) |
| 2 | Friend looks at each hub portal and says what they see and hear | Portal room | – | Look, light colour, loudness compared with the host's description |
| 3 | DELETE (host), friend looks at the button, presses it 3 times, then `]` on both | Portal room | `hook InteractWith_A fired on our button` with the friend's character as `arg1`, `press 1..3` (open point 2) | Prompt text follows `press N` (open point 1); the on-screen "pressed" message shows; their `]` lists the button with `role=SimulatedProxy` |
| 4 | Friend walks into C-2 World B, out by the exit pad; host follows later | World B | `hub exits:` lines naming the friend; the arrival pad's `route_return`; host's own claim and lighting only when the host is inside (watch for the wrong-player tracker in 1a) | Lands in World B (or falls: the custom-world streaming question); title banner; lighting; portal sickness message; exit works |
| 5 | Friend: A-4 The Train (`hub` mode), out by the early exit; then again by the true exit | The Train | `entered train_start through hub portal hub_A4 (exits: hub)`, then `moved on ... to the front of hub_A4` and `check after ...: ... (at the hub portal)` | Ends at hub_A4 in the portal room, no rubber-band back to the Train's return point; no falling through the floor |
| 6 | Friend: B-1 Far Garden by the hub (`dynamic`), out by the early exit, then **stands still 5 s** | Far Garden, portal room | Move to `hub_B1`, then within 5 s **no** second `entered anteverse_a_start through hub portal hub_B1` (the 21:49 question) | Where they landed relative to the portal; whether they were pulled back in without moving |
| 7 | Host enters Far Garden the game's way at the same time as row 6 and leaves the game's way | Far Garden | Host `entered ... the game's way`, no move for the host while the friend is moved: per-player separation | – |
| 8 | Host: change to phase 2 in the GUI, Restart All Mods | Portal room (both) | Hub restarts, 7 of 7 spawned, no `Ref was not function` | Pads vanish and come back? Duplicates? `]` before and after |
| 9 | Friend: B-1 Far Garden (`manual`, BUFFS ON), steps through the manual portal | Far Garden | `used the manual portal of anteverse_a_start`, `true-exit buff Buff_Hygroscopic given` | Back at hub_B1; buff icon shows; no double buff |
| 10 | Friend: the Train's MHE (Train reached the game's way, A-4 is off) | The Train | `used the MHE of train_start, to hub_failsafe` | Lands at the Failsafe Exit spot on the top tier, not in the floor |
| 11 | Host NUMPAD 1 in the portal room | Portal room | Respawn lines | Pads flicker? Duplicates? |
| 12 | Friend leaves the game while standing in World B, rejoins | World B | Join lines; hub keeps running | Lands in World B or falls (a client's hold / rescue is untested: 1a) |
| 13 | Host saves, quits to the menu, reloads, friend rejoins | Facility | Probe button not back (`ShouldSave = false`); hub spawns again | – |
| 14 | **Run 2:** friend switches their hub on, restarts, rejoins; `]` on both in the portal room | Portal room | As row 1 | **Duplicates** (`more than one with the same ID`), the friend's own pads `role=Authority` next to the host's `SimulatedProxy` ones; their hum x1.0 on their pads and what it is on the host's |
| 15 | Run 2: friend uses B-1 (where the two configs differ) and the slot only their config fills | Portal room | Which pad the server used; any `hub exits:` line | Where they ended up; any rubber-band; the friend's hub log for `hub exits:` lines (does the hook fire on a client?) |
| 16 | Run 2: friend leaves Far Garden by its early exit (host config: `manual` on B-1, friend's: `game`) | Far Garden | – | Moved twice, or once? Friend's log for a move of their own |
| 17 | Run 2: friend NUMPAD 1 and NUMPAD 2 | Portal room | Nothing should change on the host | Their own pads respawn or vanish; the host's stay |

Rows 0-13 are the core; 14-17 only if time allows. If anything crashes, stop, keep both machines' logs and crash folders, and send them
before trying again.

## 5. Logs to collect afterwards

UE4SS overwrites `UE4SS.log` at every launch, so **the friend must copy it before restarting for run 2**, and both copy it again at the end.
- `<game>\Binaries\Win64\ue4ss\UE4SS.log` (both, once per run).
- `%LOCALAPPDATA%\AbioticFactor\Saved\Logs\AbioticFactor.log` and the `-backup-` files from that evening (both).
- `%LOCALAPPDATA%\AbioticFactor\Saved\Crashes\` if anything crashed.
- Both players' `Mods\mods.txt` and `Mods\PortalHub\Scripts\config.lua` as used (the friend's for run 2).
- The host's list of row times.
- Then: `grep "Ref was not function"` in both UE4SS logs, and read the probe's `]` blocks side by side.

## 6. Code cards (for the dispatcher; none built here)

- **A. Hub client mode** (`mod/PortalHub/Scripts/main.lua`, a new `tools/dev/tests/test_hub_client_mode.py`; Opus, high: multiplayer
  semantics across the hub). Where the local pawn has no authority: no pad spawning or destroying, no exit moves or `route_return`, no
  buffs, no world loader spawning (pending row 4's answer); keep the hum, applied to every hub pad seen and again when one arrives
  (1b), counting what is there; pick the local player controller (`IsLocalController`) in `local_pawn`, which matters on the host too.
  It needs a dev switch that turns client mode off, so a run can still compare. Done: mock tests for host, client and switch-off; one
  two-player check. **Timing is LuciDin's call:** built before the evening, run 2 tests the intended behaviour; built after, it is
  shaped by the evening's data. The local-controller fix alone is small and safe before the evening.
- **B. Host-side tracking for every player** (same file; Opus, high; after the evening): the presence tracker for all player pawns on the
  host (vignette claim on each controller, fall rescue and hold done by the server), if rows 4 and 12 show a client is left alone.
- **C. Hub keys vs the game's debug bindings** (LuciDin's decision; then a small hub + GUI README change, Sonnet, low, or none): NUMPAD 1
  and 2 sit on the game's debug camera-shake actions. Accept as is (debug actions, probably dead in the shipped game) or move them before
  CRD-015 / CRD-024.
- **E. "No Exit Found" right after loading a save inside a custom world** (`main.lua` `spawn_all` / `schedule_spawn`, `test_hub_reload.py`;
  Opus, medium; found in the solo probe check, 10 November 01:46, CordonaCorp, World B). The log shows the hold released at 01:46:12.09.
  World B's arrival and exit pads return to `hub_C2`, but the hub portals spawned only at 01:46:14.71: the 4 s delay after the portal
  room's Homeworld pads appear (`SPAWN_DELAY_MS`). Walking into a World B pad in those ~2.6 s gave the game's "No Exit Found". A few
  seconds later it worked. Possible fixes: spawn the hub portals at once when the player is inside a custom world at load, keep the
  world's own pads off until their hub portal exists, or hold the player until then. Not urgent, but with a client joining into a
  world (row 12) it is worth having first.
- **D. Hub-exit landing spot** (`main.lua` `send_to_hub`, `test_hub_exits.py`; Opus, medium; only if row 6 shows the re-entry): land further
  from the portal, or ignore a re-entry by the same player for a few seconds after a move.
