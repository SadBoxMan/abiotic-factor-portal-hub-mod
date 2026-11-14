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
| Ladder (a): hub only, the hub that ships (d061ced: CRD-032 fix + CRD-033's DLC guards, DEV_KEYS off, SHA-1 2d1229b2), tracker on; config `8d2e40f7`; DLC survey off, probe off, no lab | 14 Nov 13:19-13:58, Mod Testing | Every portal world once (Rise, Botanical Wing (Future), North Pole, World A-D), then a hop between restarts; 35 min of play before the restarts, 8.9 GB at 33 min | 8 back to the hub: manual portals of Rise, Botanical Wing (Future), North Pole (2 each), MHEs of Signal and Fog to the Failsafe Exit | 8 (13:54-13:55) | 0 | **No stutter, no hang** (LuciDin). All 8 restarts logged `unloading: AttemptTeleport hook N unregistered` (5 to 40 in fives) right after UE4SS's own line, and the hub loaded again with a new hook each time. No `Ref was not function`, no Lua error, no new crash report. The game log was closed normally at 13:58. Logs kept in `Cordona Game Backups\2026-11-14_CRD-032-ladder\`. |
| Ladder (b): hub (as (a)) + lab (959e5c5 + CRD-032's unload hunk, SHA-1 712f1bfd), F7 on at 14:03; config `8d2e40f7`; probe off | 14 Nov 14:00-15:20, Mod Testing (LuciDin away 14:03-15:13: 70 min idle, autosaves only) | World A-D and back, North Pole and back (its MHE re-recorded at 15:14 with F2 + INSERT, kept); not the planned 30 min of hops | 10 pad uses logged by the lab; 5 back to the hub | 4 (15:13:44-15:14:03), then a 5th at 15:20:52 | **1, during the 5th restart** | Restarts 1-4: both mods unregistered their hooks (hub 5/11/17, lab 6/12/18). **After restart 4, `Ref was not function`** (15:14:04.335, 0.5 s after "All mods re-installed"): the hub's delayed portal spawn was lost (the four world-settings lines of the same moment were logged, `spawn_all` never came), so the hub portals stayed away until NUMPAD 1 (15:14:16), which spawned them and registered the hub's hook (24) **after** the lab's (23): the first time the lab, not the hub, owned AttemptTeleport's hook list. Other delayed actions kept working (the lab's 5 s hook, world readiness, pad logging). **Crash at the 5th restart (15:20:52, 80 min after launch):** UE4SS logged every mod's stop up to PortalHub and the hub's `unloading: AttemptTeleport hook 24 unregistered`, then nothing (the log lags, so the lab's stop may be missing). Dump (cdb, nearest exports): UE4SS's own event-loop thread, `UE4SSProgram::delete_mod` > the Lua mod's uninstall > Lua's state close (Lua library frames) > a UE4SS C function that takes argument 1 as an object and calls its virtual destructor, with a null object: access violation reading 0x0. That is a garbage-collection finalizer meeting an empty object while a mod's Lua state is closed, after our unload callback had finished. Crash folder, dump and both logs in `Cordona Game Backups\2026-11-14_CRD-032-ladder\crash_run_b_1520\`. |
| (Before the re-run) CRD-033's ownership readout, as an untried-call step: hub of (a), lab, DLC survey (14f9e62) on | 14 Nov 15:39-15:40, Mod Testing | none | none | 0 | 0 | `HasServerGameEntitlement` true for Stone Garden and Torii on the game thread, no error (CRD-033's verdict: clean). |
| **Re-run after the fix: hub + lab + probe**, hub e92f782 with DEV_KEYS off (SHA-1 e5fdc32f; 14f9e62 + the game-thread delays), lab 59f55ba3, probe 56ab6252 (CordonaProbe 1), F7; config `8d2e40f7`, then **LuciDin's own edit at 15:56:23** (`72a3c448`: 9 portals instead of 7, applied with a Restart All Mods); new North Pole MHE (`manual_exits` 3544b049) | 14 Nov 15:53-16:24, Mod Testing, active play | Rise, Botanical Wing (Future), North Pole, Signal, Distant Shore, Fog, World A-D, the Stone Garden and Torii pads (owned) | 80 pad uses logged by the lab; 28 back to the hub by manual portals and 1 by an MHE (Fog, to the Failsafe Exit); 48 probe button events; NUMPAD 1 three times | **11** (2 at 15:56 for the config change, then 9 from 16:22:14 to 16:23:54, a hop between each) | **0** | Every restart: the probe (4 hooks), the hub and the lab unregistered their hooks, and **the hub's delayed portal spawn ran 0.5 s after each one** ("9 of 9 configured portal(s) spawned"), the step run (b) lost. No `Ref was not function`, no `[DelayedAction]` error, no tracker error, no Lua error, no new crash report; game log without a fatal line; 9.0 GB at the end. CRD-033's ownership check logged both areas owned at each spawn. |

### Run (b)'s crash: what the source says (14 November)

Read from the same UE4SS commit (d4aebbf0): `LuaMadeSimple.hpp`, `LuaMadeSimple.cpp`, `LuaMod.cpp`.

- **The crashing function is LuaMadeSimple's automatic `__gc`:** `static_cast<ObjectType*>(lua_touserdata(L, 1))->~ObjectType()`. The
  instructions in the dump match it exactly (`lua_touserdata(L, 1)`, then a virtual destructor call through the vtable with no free).
  `lua_touserdata` returns null only when its argument is not a userdata, so Lua's state close finalized **a value that was not one of
  UE4SS's objects but carried one of their metatables**: a sign that this Lua state was already damaged, not a fault in the close itself.
- **The same state had shown damage 7 minutes earlier.** "Ref was not function" at 15:14:04 was logged as `Error: ...` with "No
  traceback", the form the game-thread action runner uses (the async runner writes `[DelayedAction] ...`). So a game-thread action's
  registry slot held something other than the function stored there: the registry had been written twice at once.
- **Where two threads write one Lua state at once.** `ExecuteWithDelay` and `LoopAsync` queue the callback for the mod's **async thread**,
  which runs it on `async_lua`, a Lua thread of the mod's own state, every 5 ms, **holding no lock against the game thread**. Game-thread
  Lua (hooks, `ExecuteInGameThread` actions, `NotifyOnNewObject` callbacks) runs on `m_hook_lua`, another thread of the same state. A Lua
  state is not thread-safe: its registry, allocator and garbage collector are shared by all its threads. UE4SS guards part of it
  (`ExecuteInGameThread` takes `m_thread_actions_mutex` before its `luaL_ref`, with the comment "when async thread and game thread both
  access the same hook_lua state"), but `ExecuteWithDelay`'s own `make_ref` takes no lock, the async callback's Lua runs unguarded, and the game-thread runner
  (`process_simple_actions`) holds the mutex only while it takes the queue: it runs each action and `luaL_unref`s its slot without it.
- **Our mods use exactly that pattern:** `ExecuteWithDelay(ms, function() ExecuteInGameThread(fn) end)`, 12 times in the hub (its tracker
  and world poll loops re-arm one every 2 s and 500 ms, so the race window is open all session), 9 in the lab, 1 in the probe. Each one
  runs a little Lua on the async thread and writes the registry from both threads.
- **The safe calls exist in this UE4SS:** `ExecuteInGameThreadWithDelay(ms, fn)` and `LoopInGameThreadWithDelay`, queued under the
  mutex and run by the engine-tick hook on the game thread. With them, none of our Lua would ever run on the async thread.
- **Fits the other sightings:** the October "Ref was not function, then every delayed action gone" losses, the 6 November sighting two
  minutes after a restart, and crashes 1 and 2 (a hook's Lua state already garbage) are all what this race can produce; restarts make it
  likelier (bursts of re-arming from several threads at once). Not proven for those (no heap in the dumps), but it is the first mechanism
  found that damages a state with no restart and no third-party mod.
- **Our unload callback is not implicated:** the damage showed at 15:14, the crash at 15:20 when that state was closed.

**Fix (e92f782, LuciDin's go):** one helper used everywhere instead of `ExecuteWithDelay(ms, function() ExecuteInGameThread(fn) end)`:
`ExecuteInGameThreadWithDelay(ms, fn)` when it exists, the old pair otherwise (an older UE4SS). Hub (`state.later`, all 12 calls including
CRD-033's DLC backstop chain and the delayed portal spawn that run (b) lost), lab and probe (`later`). Test:
`test_game_thread_delays.py` (24; 7 fail on the old files); `hub_mock` knows the game-thread delays. (The hub's loops re-arm every 500 ms,
the tracker, and 250 ms, the world check, not every 2 s as written above.)

**What still runs our Lua off the game thread (UE4SSProgram.cpp, same commit):**
- **Key binds.** `RegisterKeyBind` callbacks run on UE4SS's event-loop thread (`UE4SSProgram::update` > `m_input_handler.process_event()`),
  but holding both `m_game_thread_execution_mutex` and `m_thread_actions_mutex`. The engine-tick and ProcessEvent hooks, which run every
  `ExecuteInGameThread` and game-thread delayed action, hold the first for their whole run, so a key press never overlaps those. It can
  still overlap a **Blueprint hook callback** (our AttemptTeleport post-hooks, the probe's Button_Generic) or a **`NotifyOnNewObject`
  callback**, which take neither lock. Our binds run one line there (`ExecuteInGameThread(fn)`), so the window is a key press landing on the
  same instant as a pad use or a watched object appearing: rare, against the old async race's every 250-500 ms with no lock at all. NUMPAD
  1/2 ship. Not fixable from Lua short of polling keys from the game thread.
- **The main chunk at Restart All Mods** runs on the event-loop thread with no lock (`queue_reinstall_mods` > `start_lua_mods`). Once it has
  registered a `NotifyOnNewObject` or queued an `ExecuteInGameThread`, the game thread may run that callback while the rest of the chunk is
  still running. Only at restarts, for the last few statements of the chunk.

**Ladder verdict (14 November).** Hub alone, on 0b9a141's fix: clean (40 min, 8 restarts). Hub + lab: "Ref was not function" after a
restart, then a crash closing that damaged Lua state at the next one; the source pointed at our `ExecuteWithDelay` timers running Lua on
UE4SS's async thread beside the game thread. After e92f782 (game-thread delays), hub + lab + probe: clean (30 min of active play, 80 pad
uses, 11 restarts). The dispatcher ruled the combined run enough (it is the case that crashed); CRD-029's fresh-install test runs the
shipping hub alone from the release zip. **Left:** the two narrow windows above (a key press during a hook callback; the main chunk at a
restart), both inside UE4SS's design and not reachable from Lua; and one clean 30-minute run is evidence, not proof, against a crash
that came every one to three long sessions. The README still tells players to restart the game after Restart All Mods.
