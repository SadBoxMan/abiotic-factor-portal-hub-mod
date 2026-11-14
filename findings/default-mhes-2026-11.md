# Default Manual Hub Exits and shipped presets (CRD-031, November 2026)

Portal Hub 1.0 ships with at least one Manual Hub Exit (MHE) in every base-game portal world, placed by the author in game with the lab's
F2 + INSERT, and with the author's preset(s). This file holds the world checklist, the validation and the in-game (lab) results.

**Scope (LuciDin, 10 November):** the 22 portal worlds of the config GUI's destination list (`hubdata.DESTINATIONS`) get a default MHE.
World A-D (custom worlds, a 2.0 preview in 1.0) get none: the hub gives custom worlds no MHE, their arrival pad already leads back. The
game's homes (Cabin, Stone Garden, Torii) get none either (allowed in the file, not required).

## World checklist

MHE present = in `mod/PortalHub/Scripts/manual_exits.lua`. Validated = passes `tools/dev/tests/test_default_mhes.py`.
Lab-tested = in game: arrived, found the MHE, used it, landed at the hub, and the log showed it.

| World | Arrival pad | MHE present | Validated | Lab-tested |
|---|---|---|---|---|
| Far Garden | `anteverse_a_start` | yes (10 Nov 23:14) | yes | yes (run 1: manual portal back to A-3) |
| Flathill | `fog_start` | yes (10 Nov 23:20) | yes | yes (run 1: preview back to A-4) |
| The Train | `train_start` | yes (9 Nov 20:12) | yes | yes (CRD-012, CRD-026 runs) |
| Furniture Store | `warehouse_start` | yes (10 Nov 23:24) | yes | recorded in run 1; its use line is in a log that was overwritten |
| The Mycofields | `anteverse_b_start` | yes (10 Nov 23:26) | yes | recorded in run 1; its use line is in a log that was overwritten |
| The Night Realm | `nightrealm_start_A` | yes (11 Nov 00:00) | yes | yes (run 1: manual portal back to C-1) |
| Canaan | `salem_begin` | yes (11 Nov 00:10) | yes | yes (run 1: back to C-2; crash 1 followed) |
| Voussoir | `alps_start` | yes (11 Nov 00:34) | yes | recorded in run 2; its use line is in a log that was overwritten |
| Village Den da'ko Yeer | `anteverse_c_start` | yes (11 Nov 00:36) | yes | recorded in run 2; its use line is in a log that was overwritten |
| Shadowgate | `shadowgate_start` | yes (11 Nov 00:43) | yes | recorded in run 2; its use line is in a log that was overwritten |
| Praetorium | `INQ_Entrance` | yes (11 Nov 00:45) | yes | yes (run 2: back to A-4) |
| Botanical Wing (Present) | `botanical_present_01` | yes (11 Nov 00:51) | yes | yes (run 2: back to B-4; run 3: MHE to the failsafe) |
| GATE Arch Defense Facility | `wall_start` | yes (11 Nov 00:47) | yes | yes (run 2: back to B-1) |
| Botanical Wing (Future) | `botanical_future_01` | yes (13 Nov 22:20) | yes | yes (run 4: back to C-1) |
| Albatross | `island_start` | yes (11 Nov 00:48) | yes | yes (run 2: back to B-2) |
| Rise | `rise_start` | yes (13 Nov 22:02) | yes | yes (run 4: back to A-3) |
| North Pole | `V_Snowglobe_Start` | yes (13 Nov 22:05) | yes | yes (run 4: back to A-4) |
| Dunkeltaler Forest | `signal_start` | yes (13 Nov 22:07) | yes | yes (run 4: MHE to B-1, then manual portal) |
| Royal Range (IS-0083) | `VWinter_Start` | yes (13 Nov 22:13) | yes | yes (run 4: back to B-2) |
| The World in the Mirror | `mirrorworld_start` | yes (13 Nov 22:16) | yes | yes (run 4: back to B-4) |
| The Pool Room | `tile_entrance` | yes (13 Nov 22:22) | yes | yes (run 4: back to C-2) |
| Some Distant Shore | `DistantShore` | yes (13 Nov 22:23) | yes | yes (run 4: back to C-3) |
| Failsafe Exit (portal room) | `failsafe` | yes (9 Nov 20:15) | yes | yes (run 3: Botanical (Present)'s MHE landed there) |
| World A-D | custom | n/a | n/a | n/a |
| Cabin, Stone Garden, Torii (homes) | `H_*_Start` | n/a | n/a | n/a |

Validated = `test_default_mhes.py` passes on the final file (379 checks, 0 failed: 22 worlds + the failsafe). Every recording's lab line named the right world: its arrival pad was the nearest one, 16-434 m away. Five round trips were done in run 1/2 sessions whose `UE4SS.log` has since been overwritten (each game start replaces it), so they are not counted as seen here.

## Validation

`tools/dev/tests/test_default_mhes.py [path]` (default: the repo copy) checks: no BOM; real Lua returning a table; `return {` and `}` on lines
of their own (the lab writes into that shape); no duplicate keys; only known keys; every world above has an MHE; the failsafe is there;
four numbers per spot, |x|,|y| <= 20 km, |z| <= 3 km, yaw 0-360, not the origin; no MHE within 30 m of the failsafe (recorded in the portal
room by mistake); no two worlds' MHEs within 5 m (one probably went to the wrong world); the GUI's `read_manual_exits` reads the same keys
and numbers as Lua (the GUI never writes this file, so this is its round trip); the lab's `MHE_WORLDS` match the GUI's list.

## Lab test

Run 1 (10-11 November, 23:12-00:11, CordonaCorp; hub, lab, probe and the cheat-command mod installed). LuciDin's live config put each
world being recorded on a slot with `exits = "manual"`, so a world's MHE showed as that slot's manual portal. Recorded: Far Garden, Flathill,
Furniture Store, The Mycofields, The Night Realm, Canaan (plus the Train and the failsafe from 9 November). Round trips logged as expected
(`used the manual portal of <world>, back to hub_XX`).

**Crash at 00:11:16** (`EXCEPTION_ACCESS_VIOLATION reading 0x80`), about 0.8 s after using Canaan's manual portal back to hub C-2, while the
portal room streamed in. The minidump (cdb, UE4SS has no PDB, so the names are only the nearest exports) shows a Blueprint function, called
from a component's tick, firing a UE4SS **script hook** pre-callback (`UnrealScriptFunctionData::FirePreCallbacks`), which crashed while
building the Lua arguments (`LuaType::auto_construct_object`), before any mod's Lua code ran. Most likely cause: **Restart All Mods at 23:14:24
left the old Lua states' script hooks registered**. UE4SS unregistered only the ClientRestart hooks; the hub's and lab's AttemptTeleport hooks
(ids 9, 10) and the probe's four Button_Generic hooks (5-8) from before the restart stayed, pointing at Lua states that no longer exist.
Every pad use fires AttemptTeleport, so each use also called the stale hooks. One of them logged `Ref was not function` at 23:16:24, and one
crashed at 00:11:16. The cheat mod's god mode hook (`Server_ApplyBuff`) is a native hook on a C++ function, not this path. This is the
known UE4SS "Ref was not function" family, now with a crash: not the MHE data and not hub logic. All 8 recorded spots were intact after the
crash (installed = repo, test passes apart from the missing worlds). **Workaround:** don't use Restart All Mods while recording; after one,
quit the game and start it again.

Run 2 (11 November, 00:30-00:52, fresh game start, **no** Restart All Mods). Recorded: Voussoir, Village Den, Shadowgate, Praetorium, GATE Arch,
Albatross, Botanical Wing (Present); round trips logged as expected. **Second crash at about 00:52:10** in Botanical Wing (Future), about
30 s after arriving and turning no-clip on, with no pad use logged (`EXCEPTION_ACCESS_VIOLATION reading 0x2f6000008`). **Same signature:** a
Blueprint function called from a timer (`FTimerManager::Tick` > three Blueprint frames > `CallFunction`, its result stored in a bool) fired
a UE4SS script-hook pre-callback that crashed while converting the arguments for Lua (`get_mod_ref` > `push_...`), before any Lua ran.
So the stale-hook theory from run 1 is not enough: this run had only the current hooks: the probe's four `Button_Generic` hooks
(5-8), the hub's and the lab's `AttemptTeleport` (11, 12), and the cheat mod's native `Server_ApplyBuff` (9, 10, a different path). The
minidump has no heap memory, so the hooked function's name can't be read from it. A `pcall` in our Lua cannot catch this (UE4SS crashes
before calling it). All 15 spots were intact after the crash.

**The cheat-command mod (first look, 11 November).** With LuciDin's saved settings (god mode and infinite ammo on; they load with the
game), it registers **no script hooks**: its only hook is the native `Server_ApplyBuff` hook (god mode's debuff shortener), which is
a different path from the crash. Its script hooks (furniture construction, deploy proxies, crouch roll, journal, toilet, power
sockets, a minigame) are only registered when their features are switched on, and none were in either run's log. So it is **not
the hook that crashed**. It can still be involved indirectly. It runs a `LoopAsync(250)` loop: each pass hands the feature work to the game
thread, but saves its settings file on UE4SS's async thread. It writes to the player 4 times a second. And it was enabled both times in
October when UE4SS lost its game-tick hook after a mod restart (handoff, UE4SS notes). Our mods use no `LoopAsync`. Against it: CRD-026's
three runs and CRD-028's run had it on with no crash (whether god mode was on then is not recorded). The two crash runs had the probe, the
hub, the lab and the cheat mod with god mode, and long sessions with many world hops. One crash per 20-40 minutes is too rare to settle the
question in a few trips. That needs its own run with one mod changed at a time.

**Ruling (LuciDin, 11 November):** the cheat-command mod is out of testing from now on. The lab got its own **F7 infinite health** key
(sets the player's `Invincible` flag, checked again every 2 s on the game thread while on, no hook, no async loop; test
`tools/dev/tests/test_lab_invincible.py`, 20 checks). F7 is unbound in the game's input config (pakchunk0 ActionMappings / AxisMappings:
F1, F2, F3, F4, F5, F9, F10, F11 are bound, F7 and F8 are not) and in our other mods (the Logger has only F6). The cheat mod was removed
from the install (its folder is still in the pre-beta backup; its settings file was copied to the CRD-031 backup folder). Compatibility with it,
or a compatibility patch, waits until after 2.0.

Run 3 (13 November, 17:50-17:53, fresh start, hub + lab + probe, **no cheat mod**, F7 not pressed). LuciDin saw **stuttering** while
placing portals; the game used about 8.5 GB of memory. **Third crash at about 17:53:45**, about 90 s after entering Rise
(`EXCEPTION_ACCESS_VIOLATION reading 0x20000001f`). **A different signature:** no script hook this time. UE4SS's game-tick hook ran a queued
Lua callback (the `ExecuteWithDelay` / `ExecuteInGameThread` queue), that Lua called an object search, and UE4SS crashed walking the
object array (`FindObject` > `ForEachUObject` > `GetOutermost` on a bad object), while Rise was still streaming in. Which mod's callback
it was cannot be read from the dump. Our game-thread loops: the hub's tracker (500 ms; uses a cached controller, so it normally searches
nothing), the hub's world-loading check (only while a custom world loads), the lab's F7 check (not on in this run), and one-off delayed
calls. **So the crashes are not the cheat mod alone:** three crashes in three runs, all inside UE4SS on a Lua path, all while worlds
stream. `manual_exits.lua` was unchanged (14 worlds + failsafe, as on 11 November). LuciDin is running his own extended tests to see whether the
stutter and crashes come from the game itself or from the mods.

**LuciDin's isolation tests (13 November):**

| Test | Setup | Result |
|---|---|---|
| 1 | UE4SS off (`dwmapi.dll` renamed) | **No stutter** |
| 2 | UE4SS on with its stock mods (console and cheat-manager enablers, console commands, Blueprint mod loader, Keybinds); hub, lab and probe off (log at 18:01 confirms) | **No stutter** |
| 3 | + hub only (log at 18:05 confirms) | **Stutter** |
| 3b | same game, NUMPAD 2 (all 23 hub pads gone, 14 MHEs included), then NUMPAD 1 | **Stutter unchanged**: not the pads |
| 3c | hub only, `tracker = false` in config.lua (log 18:12: "tracker: switched off"), hops to North Pole, Rise, Botanical (Future) | **Smooth** ("smooth as butter"): the tracker is the cause |
| 4 | + lab (and probe) | not needed |

**Likely cause (11/13, reported to the dispatcher, not fixed here):** the hub's tracker (500 ms) calls `watch_flags` every 2 s. It runs
`FindFirstOf("WorldFlagSubsystem")`, and `flag_is_set` runs it again for each vignette world: about 5 full object-array scans every
2 s on the game thread. Their cost grows with the number of loaded objects (8.5 GB after many world hops), and crash 3's dump is that path. The fix is
to cache the subsystem and pass it in. Confirmation test: `tracker = false` in config.lua, restart, hub only.

Run 4 (13 November, 21:58-22:26, hub + lab, probe off, no cheat mod, `tracker = false`). Recorded the last 8: Rise, North Pole, Dunkeltaler, Royal Range, World in the Mirror, Botanical (Future), Pool Room, Some Distant Shore; each used and landed back at its hub portal. No stutter, no crash (one mods restart at 22:09). Afterwards the install was put back: the `tracker = false` line removed (LuciDin's own change to B-1, `exits = "manual"`, kept), the lab removed, `CordonaProbe : 1` again.

## Presets

**LuciDin's plan (13 November): four presets ship in 1.0.** Pack 1 is the flagship demo (varied optional areas, no major story
spoilers), Pack 2 is story, Pack 3 is "Builder Worlds", and Pack 4 demos the custom worlds (World A-D). In the repo they go in
`tools/release/presets/`, and they ship as `Presets\pack1-demo.lua` ... `pack4-custom-worlds.lua` (the builder change needs the dispatcher's OK).

| Pack | File | Made | Slots | Notes |
|---|---|---|---|---|
| 1 Demo | `pack1-demo.lua` | 13 Nov 23:17 | A-3 Dunkeltaler, A-4 Flathill, B-1 Royal Range, B-2 Rise, B-4 World in the Mirror, C-1 Furniture Store, C-2 Pool Room, C-3 Some Distant Shore, C-4 the Train; all `manual` | The A-D `worlds` block was dropped (LuciDin); syntax OK; the GUI round trip is byte-identical |
| 2 Story | `pack2-story.lua` | 13 Nov 23:35 | A-3 Far Garden, A-4 Flathill, B-1 the Train, B-2 Furniture Store, B-4 Mycofields, C-1 Canaan, C-2 Voussoir, C-3 Village Den, C-4 Shadowgate; all `manual` | A-D block dropped; committed in 959e5c5 |
| 3 Builder Worlds | `pack3-builder-worlds.lua` | 13 Nov 23:55 | A-4 World in the Mirror, B-1 Furniture Store, B-4 Pool Room, C-2 Dunkeltaler, C-4 Some Distant Shore; all `manual`; four slots empty | A-D block dropped; committed in ccd0d31 |
| 4 Custom worlds | `pack4-custom-worlds.lua` | 14 Nov 00:04 | C-1 World A, C-2 World B, C-3 World C, C-4 World D (red, blue, green, yellow) | keeps the A-D block; its zip carries the twelve teaser files |

A test build (`--worktree`, 14 November) made all five zips: main 1047 files, 19.5 MB, no paks; Packs 1-3 with 4 files each; Pack 4 with 16
(its preset, the twelve World A-D files under `AbioticFactor/Content/Paks/~mods/`, README, licence, file list).
