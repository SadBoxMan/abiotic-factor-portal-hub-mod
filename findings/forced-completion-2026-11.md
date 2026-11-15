# Forced world completion (CRD-038, November 2026)

LuciDin's "Last Call" question (14 November): can the hub mark worlds such as GATE Arch Defense Facility and Some Distant Shore as
"Completed", which the base game never does, as an optional feature? This note answers it from desk research only. No code was changed,
nothing was installed, and nothing was written to a save.

Sources: the game's own assets only. These were the raw paks of 21 August 2026 in `Modding Tools\Abiotic\PAK Assets` (the name tables of
every `V_*` / `H_*` map, `DT_WorldFlags`, `DT_Quests`, `Facility_Pens`, `Facility_Residence`), the fresh FModel export in
`Fresh-Extract\Exports` (`DT_Levels`, string tables, `V_Signal`), the official modding project's headers (`WorldFlagSubsystem.h`,
`QuestData.h`), our earlier findings (CRD-001, CRD-006) and three abioticfactor.wiki.gg `/wiki/` pages (Locations, GATE Arch Defense
Facility, Some Distant Shore). No third-party mod was read.

## Verdict

- **Possible and safe, with one firm rule: never set the game's flag. Re-point the world's zone at a hub-owned flag instead.**
  The two worlds that can't be completed most likely wait on one shared flag, `DemoNeverSet`, which the game never sets. The same flag also
  gates content in `DT_Quests`, `Facility_Pens` and `Facility_Residence`, so setting it would change story and Facility state in ways
  nobody has mapped.
- The hub already does the safe version for custom worlds. `apply_vignette_type` adds `PortalHub_<id>_Completed` to `DT_WorldFlags`
  and re-points the world's `Vignette_Zone` at it. A forced completion is that same step aimed at a base-game zone, with the hub setting
  the flag itself.
- **"Completed" in this game means one thing only: portal sickness is lifted for good in that world.** Equipment, the jetpack included,
  then works there. Nothing found records completion anywhere else: no "completed" text exists for portal worlds in the string tables,
  and these worlds have no true-exit reward. So forcing it changes no rewards and no story. It makes those worlds easier.
- **Only these two worlds are outliers (LuciDin, 14 November, from play).** ARCH Defense and Distant Shore both lock equipment, and
  every other world that gives portal sickness has a way to lift it. Albatross (`V_ISLAND`) also names `DemoNeverSet` in its map, but
  it gives no portal sickness, so it is not a candidate. The flag is used by something else there, which shows that a name in a map's
  name table is a clue, not proof of the zone's flag.

## 1. How the game records a portal world as completed

- Every vignette world holds a `Vignette_Zone` (`BuffZone_ParentBP`) whose `PortalSicknessWorldFlag` names a story flag in
  `DT_WorldFlags`. Until that flag is set in the world save, players in the zone carry `Debuff_PortalSickness` (equipment locked). Once
  it is set, the sickness never comes back for that world. This is confirmed since CRD-001; handoff "Zones, world types and flags".
- The world's proper ending sets the flag. Two kinds were seen:
  - a pad's `WorldFlagToTriggerOnUse`, the true exit (the Train's `train_end` sets `TrainCompletedOnce`, proven in game, CRD-006);
  - an object in the world. In Dunkeltaler (`V_Signal`, fresh export), `Vignette_Zone_C_1.PortalSicknessWorldFlag = V_Signal_Complete`,
    and `ComputerTerminal_VOTV_C_1.WorldFlagToUse = V_Signal_Complete` sets it.
- Flags are saved with the world save as plain names (`WorldFlagSubsystem:GetWorldFlags`; `LoadWorldFlags(TArray<FName>)` on load).
  `SetWorldFlag(handle, state, context)` both sets and clears. Since v1.5.0 a handle is `{ RowName }` only.
- Completion flags found in the map name tables: `TrainCompletedOnce` (Train), `Fog_Completed` (Flathill), `LABS_CompletedAnteverseB`
  (Mycofields), `DAMS_CompletedVoussoir` (Voussoir), `Salem_Complete` (Canaan), `SnowglobeComplete` (North Pole), `VWinter_Complete`
  (IS-0083), `V_Signal_Complete` (Dunkeltaler). The other worlds' flags are not in their persistent level's name table (probably in a
  sublevel). That doesn't matter here.
- The game shows completion only through the sickness: no message, no journal or portal-room marker. A "visited" flag can exist without
  completion. ARCH Defense's map names `Wall_AG_met` (meeting Garrick), and `DT_WorldFlags` holds `returned from wall` and
  `MapReveal_Wall`, yet none of them lifts the sickness.
- **What the hub already writes to saves:** one name per custom vignette world, `PortalHub_<id>_Completed`, set by its exit pad. If the
  mod is removed, the name stays harmless and unused (CRD-006: kept across reloads and the v1.5.0 update). Lab NUMPAD 3 clears every
  `PortalHub_*_Completed` row with `SetWorldFlag(false)`, so clearing works in game.

## 2. Why ARCH Defense and Distant Shore can't be completed

- `V_TheWall.umap` and `V_DistantShore.umap` each hold a `Vignette_Zone`. The only `DT_WorldFlags` names in their name tables are
  `DemoNeverSet` (both) and `Wall_AG_met` (the Wall). As the name suggests, `DemoNeverSet` is a flag that is never set. Both worlds
  keep the sickness on forever (LuciDin, from play: both lock equipment; the wiki says Distant Shore cannot be completed and the jetpack
  can't be used there). **This is by design, not a missing trigger.**
  - Which flag their zones wait on is still an inference, not yet read in game. The map files use unversioned properties, so the name
    table shows that a map uses `DemoNeverSet` but not which property holds it. `V_ISLAND.umap` (Albatross) also names `DemoNeverSet`
    yet gives no sickness, so the name alone proves nothing. The data is also from 21 August, before v1.5.0. The build card must read
    each zone's flag in game first (test 1 below), and match the zone by its own flag value, whatever that turns out to be.
- Some Distant Shore (wiki): a secret world reached from a Portal Toilet. It has a true exit (walking into the "ocean" goes to the Data
  Farm bathroom), but that exit sets no flag. It gives no reward, and its only achievement comes on the first visit.
- GATE Arch Defense Facility (wiki): a required story world. On the first visit the player is held in a forcefield until Garrick tells
  the Gatekeeper to let them out. Its pod holds the Motion Module and Excursion Suit recipes. Its pads are `wall_start`, `wall_exit`,
  `wall_return`. No completion is described.
- **Other worlds:** none (LuciDin: every other world that gives portal sickness can be completed). Albatross gives no sickness. Homes (`H_Cabin`, `H_Garden`, `H_Japan`) have no sickness. `V_Tile`
  (IS-0031) is not a vignette in `DT_Levels`. `V_Dummy` and `V_Intro` hold no zone.

## 3. Is a forced completion possible and safe?

**Which call:** the hub's existing calls, no new native ones. Done on the host, in order:

1. `ensure_flag_row` for a hub row, `PortalHub_force_<key>_Completed`. Keeping the `PortalHub_..._Completed` shape lets lab NUMPAD 3
   clear it too.
2. Find that world's `Vignette_Zone_C` (within 1 km of a known pad: `wall_start` or the Distant Shore arrival) whose
   `PortalSicknessWorldFlag.RowName` is the flag test 1 reads (expected `DemoNeverSet`). Write `z.PortalSicknessWorldFlag = { RowName = FName(row) }`, the same write as
   `apply_vignette_type`. Check `IsValid` first and read the value back.
3. `SetWorldFlag({ RowName = FName(row) }, true, pc)` once, after `HasWorldFlagsLoaded()` is true (the CRD-001 early-ask bug).

**What else it changes:**
- Rewards: none. These worlds have no true-exit buff, and the jetpack and equipment unlocking is the whole effect.
- Story: none. No game flag is set and `DemoNeverSet` stays clear, so `DT_Quests`, the Pens and the Residence are untouched.
- Portal room: nothing. The game shows no completion state there.
- **Never set `DemoNeverSet` itself.** That would "complete" both worlds at once and flip whatever the quests and the two Facility
  maps gate on it.

**Save integrity:** the save gains one plain name per forced world, the same kind of entry the hub already writes for custom worlds. If
the hub is removed, the zone goes back to `DemoNeverSet` when the map loads, so the sickness returns and the name sits unused. It is
harmless (CRD-006).

**Reversible:** yes. Switch the world off in the config and the hub clears its own flag (`SetWorldFlag(false)`) on the next load, and
the sickness comes back. Lab NUMPAD 3 also clears it. A no-write variant exists: re-point the zone at a flag the save already has. It is
not recommended, because no game flag is set in every save and it would muddle what "completed" means.

**Multiplayer:** host only, like everything else the hub writes. Flags live on the host's world save (`HasWorldFlagsLoaded` is
`BlueprintAuthorityOnly`), and the zone applies its debuff on the server, so a host-side change should cover every player. On a client,
the hub's client mode (CRD-027) does nothing here. Not verified with two players: add it to the two-player plan.

**Zone re-load:** streamed worlds reload their zone, which then holds `DemoNeverSet` again. The hub must re-point it each time the zone
appears, through the existing 2 s tracker (which already finds zones for custom worlds). The flag stays set either way. Without the
re-point the zone simply waits on `DemoNeverSet` again.

## 4. What an opt-in feature would look like (for the build card)

- **Config:** `forceComplete = { wall = true, distantshore = true }`. It is absent or empty by default, so nothing changes unless a
  player opts in. Keys are short world names mapped in the hub to a known pad and the `DemoNeverSet` zone. Only worlds whose zone waits
  on `DemoNeverSet` are accepted, so the switch can never short-cut a world that has a real ending. Any other key is ignored with a log
  line.
- **Editor:** a small "FORCE COMPLETION" block (HUB EXITS tab, or its own tab) with one ON/OFF switch per world, all OFF, and one line
  of warning ("lifts portal sickness for good in this save; switch off to undo"). It writes or removes the key the way the MHE switches
  do (`mhe = { ... }` handling in `luaconfig.py`).
- **Hub code path (main.lua), about 1-2 main-chunk locals out of the ~13 free:**
  - one table of the eligible worlds (pad id per key) and one function `force_completion(world, pc)`. Put both in one closure, as
    `flag_subsystem` does, if locals are tight.
  - It is called from the existing tracker tick (host only, game thread). For each enabled world it re-points the zone if it is loaded
    and still on `DemoNeverSet`, then sets the flag once per load after `HasWorldFlagsLoaded`. For each world switched off whose hub
    flag is set, it clears the flag once and shows a gray message.
  - It reuses `ensure_flag_row`, `flag_handle`, `flag_subsystem`, `flags_loaded` and `show`. `ensure_flag_row` takes a `def`; a small
    `{ id = "force_" .. key }` works, or split out a name-taking helper.
  - Mock tests: a new `tools/dev/tests/test_hub_force_completion.py` covering off by default, zone re-point, set once, clear on off,
    client does nothing, an ineligible key refused, and `DemoNeverSet` never passed to `SetWorldFlag`. Plus the GUI tests for the
    switches.
- **Risks for that card:** the 21 August data (test 1 first); zone reloads (re-point each time); two-player behaviour; the main-chunk
  local budget.

## 5. In-game reads

**Done 15 November, 01:44-01:45 (CRD-040, lab from HEAD ce12935, read only).** LuciDin entered each world by a hub portal in manual mode
(B-1 to `wall_start`, B-2 to `DistantShore`), then pressed NUMPAD 7 and PAGE UP. The test save had 222 flags set, none `DemoNeverSet`.
No "Ref was not function".

- **GATE Arch Defense:** `V_TheWall.V_TheWall:PersistentLevel.Vignette_Zone_C_0` at -334930, 333386, 13206 (extent 17935 x 14697 x
  10000). It gives `Buff_InVignette_TimeScramble`, not the plain `Buff_InVignette`, and its **world flag is `DemoNeverSet`**. The player
  carried `Debuff_PortalSickness`. Pads that set a flag: `wall_start`, `wall_entrance`, `wall_return` set `Residence_Wall` (set in this
  save); `wall_exit` (at -334833, 329613) sets `RES_ExitWall` (not set). Neither is the zone's flag, so neither lifts the sickness.
- **Some Distant Shore:** `V_DistantShore.V_DistantShore:PersistentLevel.Vignette_Zone_C_0` at 332356, -333983, 1588 (extent 10000
  cubed), `Buff_InVignette`, **world flag `DemoNeverSet`**, and `Debuff_PortalSickness` on the player. No pad in the world sets a flag.
- Both zones stayed in memory after the player left (the Wall's was still listed from inside Distant Shore, and the other way round). The
  only zones on `DemoNeverSet` were these two; the hub's custom-world zones (at 1.1-1.4 million) are far from both.
- So the CRD-038 inference holds: the zone match is on `DemoNeverSet`, within 1 km of each zone's position above.

The planned reads were:

| Key | Run it in | What it logs |
|---|---|---|
| NUMPAD 7 | Inside GATE Arch Defense Facility (hub portal to `wall_start`), CordonaCorp or Mod Testing | The zone's `world flag:` (expected `DemoNeverSet`), whether `Debuff_PortalSickness` is on, the save's Portal Hub flags |
| NUMPAD 7 | Inside Some Distant Shore (hub portal to Distant Shore) | The same; expected `DemoNeverSet` |
| PAGE UP | Same two places | Zones with their flag and "set in this save", pads that set a flag (expected: none for these worlds) |

Writing a flag to a save (the build card's own test) needs LuciDin's yes and a save backup first.

## Open questions for LuciDin

1. Answered (14 November): ARCH Defense and Distant Shore only. Albatross gives no portal sickness.
2. Answered (14 November): neither. The switch sits in the slot side panel, next to EXIT MODE / BUFFS, and shows only when the
   selected portal leads to one of those two worlds ("The switch should appear if the selected portal is one of those two worlds").
3. Answered (14 November): it ships in 1.0 ("Yes, this should ship with the 1.0 release").

## 6. As built (CRD-040, 15 November)

The rulings changed section 4's config shape: the key is **per portal**, not a global block.

- **Config:** `forceComplete = true` in a portal entry, like `manualBuffs`. A world counts as forced while any portal to it in the
  config (every entry is an enabled slot: a slot switched off is wiped) has the key. The key on any other destination, a custom world
  included, is ignored with a log line (`config entry N: forceComplete is only for ...`).
- **Editor:** a FORCE COMPLETE ON/OFF button left of BUFFS in the side panel, and one amber line under the exit-mode note ("Force
  complete lifts portal sickness for good in this save; switch off to undo."), both shown only for `wall_start` and `DistantShore`. OFF by
  default. Picking or typing any other destination clears it (moving between the two worlds keeps it); a slot switched off is wiped.
- **Hub:** `state.force` (no new main-chunk local). The world table holds each world's key, the game's flag its zone waits on, its title
  and where its zone stands (section 5's reads). Every 2 s from the tracker, host only (client mode does nothing):
  a forced world's `Vignette_Zone_C` within 1 km of its spot that still waits on the game's flag is pointed at
  `PortalHub_force_wall_Completed` / `PortalHub_force_distantshore_Completed` (again after each stream-in). No object scan runs on the tracker tick (CRD-032): the zone is looked for only while a player is in that world (this player within 1 km, or any player's pad use that led there in the last minute, from the AttemptTeleport hook, a mode-4 portal's manual portal included), then kept; each tick only checks the kept zone is valid and reads its flag; an invalid one is looked for again (5 tries 2 s apart, then every 10 s). Then, once per load (a new
  player controller) and only once `HasWorldFlagsLoaded`, the hub's row is added to `DT_WorldFlags` and the flag is set if the save does
  not have it. A world not forced has its hub flag cleared once per load if the save has it, with a gray message (the undo). Only the
  hub's own rows are ever passed to `SetWorldFlag`; a zone on any other flag is never touched. Lab NUMPAD 3 clears these flags too.
- **Re-pointing alone is not enough (save-write test, 15 November).** A zone streams in with the player and gives
  `Debuff_PortalSickness` on that first overlap (`Vignette_Zone_C:DelayedPortalSicknessCheck`), and a later flag change does not take an
  applied debuff off. Run 1: both flags set, both zones re-pointed about 2 s after entry, the sickness stayed in both worlds. So the hub
  also:
  - **catches the zone as it streams in:** while a world is forced, the host watches the Vignette zone class (`NotifyOnNewObject`, set up
    once after the class is in memory; the callback only queues `state.later`) and re-points the zone on the game thread as soon as its
    flag has read in. It matches the zone by its map in the zone's full name (`/Game/Maps/V_TheWall.`, `/Game/Maps/V_DistantShore.`),
    because a new zone's position can still read 0, 0, 0. Retest: both zones caught on the first look, 55-65 ms after the pad use, yet
    one of two first entries still got the sickness (the zone's own check runs in the same few ms);
  - **takes the sickness off:** once the zone waits for the hub's flag and that flag is set, the hub removes `Debuff_PortalSickness`
    from this machine's player in that world and from players whose pad use led there in the last minute, with the game's own
    `CharacterBuffComponent:Server_RemoveBuff(BuffDebuffRowHandle { RowName }, true, EBodyLimbs 0 = AllBones, false)` (types from the
    object dump). Lab F9 tried the call first (`returned true`, 1 -> 0, still 0 two seconds later; one untried call per press, with
    `Server_RemoveSpecificBuffs` on a second press, never needed). It runs from the 2 s check while the zone is the hub's (cached, no
    scan), right after a zone is found, and 0.3 s after a stream-in catch. Host only.
- **Save-write test (15 November, Mod Testing, after a save backup):** with FORCE COMPLETE on for both worlds, LuciDin reports equipment
  working in both worlds on first entry and after re-entering. That run's UE4SS.log was overwritten by the next launch, so it rests on his
  report. Switched off, the next load showed both gray messages, and `Debuff_PortalSickness` was back in both worlds, untouched by the hub
  (logged). No crash and no "Ref was not function" in any of the six runs.
- **Tests:** `tools/dev/tests/test_hub_force_completion.py` (106 checks), `test_lab_remove_sickness.py` (22), `test_gui.py` and
  `test_luaconfig.py` (the switch and the key).
- **Commits:** adaada1 (hub + editor), 50194e1 (stream-in watch), 54f7735 (map-name match), 506413d (taking the sickness off), d383b85
  (lab F9).
