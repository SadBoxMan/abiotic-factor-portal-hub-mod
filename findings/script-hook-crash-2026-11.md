# Script-hook crash isolation (CRD-032, November 2026)

Three game crashes during CRD-031's MHE recording (11 and 13 November), all inside UE4SS. This note holds the log and dump analysis, what
UE4SS's own source says about hooks and mod restarts, what we changed, and the in-game isolation runs. UE4SS here is v3.0.1-1212-gd4aebbf0
(the Nexus 1.25.0 build); the source quoted is that exact commit of the public UE4SS repository (MIT), read through GitHub's API and raw
files on 13 November. Its `UEPseudo` part (the Unreal layer: object search, `FindFirstOf`) is a private repository and was not read.

## Verdict

- **Crashes 1 and 2 are not on our hooks' path.** Both died in the pre-callback of a hook on a **native** (C++) function, reached through
  `UFunction::Invoke` from Blueprint bytecode that stores the function's bool result. Our hooks are all on **Blueprint** functions
  (AttemptTeleport, the probe's Button_Generic), which UE4SS fires *after* the function ran, from its ProcessLocalScriptFunction detour: a
  different path. The only native hooks in those runs were UE4SS's stock ClientRestart hooks and the third-party cheat-command mod's
  `CharacterBuffComponent:Server_ApplyBuff` (god mode). `Server_ApplyBuff` returns a bool and takes a struct first, which fits both stacks.
  In both crashes the Lua state the callback used was already garbage.
- **Crash 3 is probably ours to reduce, not ours alone to fix.** No hook at all: a game-thread Lua callback walked the game's object list
  (UE4SS's object search) and hit an object with a garbage outer pointer while Rise streamed in. The call chain (queued callback, Lua,
  `pcall`, Lua, object search) matches the hub's tracker (`loop`, `pcall(track_tick)`, then `FindFirstOf("WorldFlagSubsystem")` every 2 s),
  the only periodic Lua running in that run. The walk racing the game's streaming is UE4SS's; how often we walk is ours.
- **Restart All Mods, in this UE4SS, already takes our Blueprint hooks off.** CRD-031's first reading ("the old AttemptTeleport and
  Button_Generic hooks stayed registered") came from the log: UE4SS logs "Unregistering hook" lines only for native hooks and removes
  Blueprint hooks silently. There is still a gap (below), now closed by unregistering on unload.

## The crashes

| | When | Signature | Path (cdb, nearest exports; UE4SS has no PDB) | Restart All Mods before? | Mods |
|---|---|---|---|---|---|
| 1 | 11 Nov 00:11:16, 0.8 s after Canaan's manual portal, portal room streaming | access violation reading 0x80 | component tick (`ReceiveTick`) > Blueprint frames > `execLetBool` > `CallFunction` > `UFunction::Invoke` > UE4SS function-hook thunk > `FirePreCallbacks` > Lua callback runs > a UE4SS Lua binding > object wrapper > a Lua API call on stack index -2 with a garbage state (`rax = 0x78`) | yes, 23:14:24 (`Ref was not function` at 23:16:24) | hub, lab, probe, cheat mod (god mode on), UE4SS stock |
| 2 | 11 Nov ~00:52:10, Botanical Wing (Future), 30 s after arriving, no pad use | access violation reading 0x2f6000008 | `FTimerManager::Tick` > Blueprint frames > `execLetBool` > `CallFunction` > `UFunction::Invoke` > thunk > `FirePreCallbacks` > the pre-callback while pushing the parameters (a property pusher) > the same Lua API call on index -2, garbage state (`rax = 0x2f6000000`) | no | same |
| 3 | 13 Nov ~17:53:45, 90 s after entering Rise, stutter, ~8.5 GB | access violation reading 0x20000001f | `FEngineLoop::Tick` > UE4SS engine-tick hook > queued game-thread action > Lua > `pcall` > Lua > UE4SS Lua binding > object search (`ForEachUObject`) > `GetOutermost` on an object whose outer is `0x1ffffffff` | no | hub, lab (F7 off), probe, UE4SS stock; **no cheat mod** |

Crashes 1 and 2 stop on the same instruction (`test byte ptr [rax+8], 0Fh`, the type tag of a Lua stack slot, with `rbx = -2`), so they
are one bug. Crash 1 got further: the Lua callback itself ran (on freed memory that still looked like a Lua state) and crashed inside the
first UE4SS call it made.

**What the logs show and don't.** The UE4SS.log of runs 1 and 2 was overwritten by later launches. CRD-031 read it before then: hook ids,
the restart at 23:14:24 and `Ref was not function` at 23:16:24 are from its notes. Run 3's UE4SS.log stops at 17:52:12 (it lags), so the
last 90 s are not in it. It shows the hooks registered: stock ClientRestart (1, 2) and (3, 4, unregistered by its own mod at 17:51:24),
probe Button_Generic (5-8), hub AttemptTeleport (9), lab AttemptTeleport (10). The minidumps hold no heap, so the hooked function's name
and the Lua state's contents cannot be read; which native hook crashed is inferred (only the stock ClientRestart and `Server_ApplyBuff`
existed, and ClientRestart returns nothing). The game logs (`AbioticFactor.log` in each crash folder) say nothing about mods.

## What UE4SS v3.0.1-1212 does (from its source)

1. **Two hook paths.** `RegisterHook` on a native function puts a pre and post callback on the `UFunction` itself (logged "Registered
   native hook"); its pre-callback builds the Lua arguments before the function runs. On a Blueprint function it adds the callback to a
   per-function list fired after the function, from the ProcessLocalScriptFunction / ProcessInternal hooks (logged "Registered script hook").
2. **One shared hook thread per mod, kept alive by one reference.** Every hook, `NotifyOnNewObject` and `ExecuteInGameThread` callback of a
   mod runs on one Lua thread (`m_hook_lua`). Only the **first** of them is handed the registry reference that keeps that thread alive; the
   rest get none. If the holder is later removed (a native hook that `UnregisterHook` takes off, or a `NotifyOnNewObject` callback that
   returns `true`), UE4SS releases that reference, and Lua's garbage collector can free the thread while every other hook of the mod still
   points at it. The next callback then runs on freed memory: crashes 1 and 2 exactly. The cheat-command mod hooks ClientRestart and
   unhooks it again through its hooks manager; whether that hook was its first holder depends on timing (its 250 ms async loop makes the
   other candidate). Not proven, but it is the one mechanism in the source that produces a garbage hook state without a mod restart.
   **Our mods:** the first holder is a `NotifyOnNewObject` (hub, lab) or an `ExecuteInGameThread` (probe) that never ends, and we never
   unhook a native function, so our hook threads stay anchored. Rule kept in the code and tested: our `NotifyOnNewObject` callbacks
   return nothing.
3. **Restart All Mods** (`queue_reinstall_mods`) runs on UE4SS's event-loop thread, not the game thread. Each Lua mod's `uninstall()` calls
   `ModRef.OnUnload`, removes the mod's NotifyOnNewObject callbacks, Blueprint hooks, queued game-thread actions and key binds, unhooks its
   native hooks, then closes its Lua state; afterwards every mod's `main.lua` runs again **on that same event-loop thread**.
4. **The gap:** a Blueprint function's hook list belongs to the mod that hooked it **first**, and uninstall drops the whole list only with
   that mod. A second mod's callback on the same function stays in the list after its own state is closed until the first mod is
   uninstalled too. With Restart All Mods that is a moment; with one mod restarted alone, or with another mod (a third-party one in a
   player's install) owning AttemptTeleport's list, the hub's callback would stay behind on a closed state.
5. **`ModRef.OnUnload`** (UE4SS PR #1394, in this build): a function a mod sets, called during uninstall before anything is torn down, while
   UE4SS holds back the game thread's Lua callbacks (the game-thread execution and action mutexes). `UnregisterHook` on a Blueprint function
   marks the callback as gone (`lua_index = -1`) under the same mutex; it also looks the function up with `StaticFindObject`.

**October's tick-hook losses** happened on the July UE4SS build (c838a8ac), whose source was not read. The pattern there (a timer from the
old state firing after a restart, `Ref was not function`, then every delayed callback gone; the cheat mod was enabled in both October
sightings, not in the two on 6 November) fits the same family of stale or freed Lua references, but the July code may differ.

## What we changed (CRD-032)

- **Hub (ships), lab and probe (dev):** `RegisterHook`'s ids are kept, and `ModRef.OnUnload` unregisters each hook (`pcall`, logged:
  `unloading: AttemptTeleport hook N unregistered`). Closes the gap above for any order of mods and for single-mod restarts. On an older
  UE4SS without `ModRef`, the hub logs that and loads as before.
- **Hub and lab:** the load-time `FindFirstOf("BP_Teleporter_HomeWorld_C")` now runs in `ExecuteInGameThread`: after Restart All Mods,
  `main.lua` runs on UE4SS's own thread while the game is running, and an object walk from there races the game.
- **Hub:** the tracker no longer walks the object list on a timer. The `WorldFlagSubsystem` (every 2 s, plus once per vignette world) and a
  ready world's loader (every 500 ms while inside a custom world) are found once and kept, keyed by the player controller's address: a load
  or a new map brings a new controller and a fresh search, so nothing from an old map is asked. While the player is held in a custom world
  that is still loading, the game world now comes from the tracker's controller (`pc:GetWorld()`, the call `UEHelpers` itself makes)
  instead of `UEHelpers.GetWorld()`, which searched every PlayerController first, every tick.

**The stutter was the tracker (LuciDin, 13 November, from CRD-031):** UE4SS off: smooth. UE4SS with its stock mods: smooth. Plus the hub
alone: stutter. Hub with all 23 hub pads removed (NUMPAD 2): still stutter. Hub with `tracker = false` (18:12, North Pole, Rise and
Botanical Wing (Future), back and forth): "smooth as butter", no crash. Table in [`default-mhes-2026-11.md`](default-mhes-2026-11.md)
("LuciDin's isolation tests"). The tracker's only searches outside custom worlds were `watch_flags` / `flag_is_set`'s
`FindFirstOf("WorldFlagSubsystem")`: about 5 walks of the whole object list every 2 s, costlier as more objects load (8.5 GB after many
hops). That is the same path as crash 3's dump.

**Object searches left after the change (audit, hub / lab / probe):** none on a timer in the hub outside a loading hold. While held in a
still-loading custom world, `loader_present` still walks once per tick (seconds at a time). Event-driven, once each: on a pad use
(`hub_exit_use` may look up a pad; `route_return` only for custom worlds), on arrival (`lighting_parts`, `is_night`, the vignette zone,
`ensure_return_portal`), on a fall rescue, and in `spawn_all` (a few `FindAllOf` of the teleporters, 4 s after the portal room appears).
Lab (dev): F7's controller lookup every 2 s (CRD-031 is caching it); pad-use logging does not search. Probe (dev): two lookups when a
Homeworld pad appears and 4 s later. None of these run on a timer; they still fall in streaming moments now and then.
- **Not changed:** the hooks' callbacks. The evidence does not point at our argument building (our hooks are post-callbacks on Blueprint
  functions); `on_attempt` and the lab's callback return nothing, so they never override a return value.
- **Untried native calls:** `ModRef.OnUnload` and `UnregisterHook` have never run in our mods. The first in-game step below tries them on
  their own. One risk stays: `OnUnload` runs on UE4SS's thread, and `UnregisterHook` calls the game's `StaticFindObject` from there,
  which the engine refuses (a fatal log) if garbage collection is running at that instant. UE4SS's own uninstall does not need that lookup.
  The window is a few milliseconds once a minute against one call per restart.

Tests: `test_hub_reload.py` (68; new: no object search off the game thread at load, the loader not searched again while standing in a
ready world, a reload still noticed, no `UEHelpers.GetWorld` while held, unload unregisters with the hook's ids once, NotifyOnNewObject callback returns nothing),
`test_hub_client_mode.py` (68; unload on host and client, a throwing `UnregisterHook` only logged, no `ModRef`),
`test_hub_vignette_type.py` (21; one subsystem search per controller, a new one after a new controller or when the kept one goes invalid),
`test_probe.py` (60) and the new `test_lab_unload.py` (10). The new checks fail on the old files. Test build (`build_release.py --worktree
--reuse-gui` in a scratch clone of HEAD plus these changes only): the packaged hub passes its built-in client-mode and reload tests.

## In-game isolation

(The table fills in as LuciDin runs it; the cheat-command mod stays out by ruling, the lab's F7 gives infinite health. Every run uses
UE4SS 1.25.0 with its stock mods on: CheatManagerEnabler, ConsoleCommands, ConsoleEnabler, BPML_GenericFunctions, BPModLoader, Keybinds.)

| Setup | When | World hops | Pad uses / MHEs | Restart All Mods | Crashes | Notes |
|---|---|---|---|---|---|---|
| Step 1: hub only (CRD-032 build, `main.lua` SHA-1 d0ecf8b5, DEV_KEYS off), tracker on; config `8d2e40f7` (Rise B-1, Botanical Wing (Future) B-2, North Pole B-4 manual; World A-D on C-1 to C-4) | 14 Nov 02:00-02:04, Mod Testing | 7 round trips: Rise, Botanical Wing (Future), North Pole | 7 manual-portal uses back to the hub | 4 | 0 | **Smooth** (LuciDin), against the stutter of the same hub-only setup before the fix (13 Nov 18:05). Each restart logged `unloading: AttemptTeleport hook N unregistered` (hooks 5, 10, 15, 20) right after UE4SS's own `Unregistering script hook with id: N`; the new hook came back each time and the next pad use worked. No `Ref was not function`, no tracker error. **`ModRef.OnUnload` and `UnregisterHook` work in game.** |

**Still to run:** the longer ladder (hub alone, hub + lab with F7, hub + lab + probe), each a long session with many hops, MHEs and a
Failsafe Exit, then Restart All Mods several times. The three crashes came 20-60 minutes into long sessions, so a 4-minute run says the
fix works, not that the crash rate is zero.
