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
  The three worlds that can't be completed all wait on one shared flag, `DemoNeverSet`, which the game never sets. The same flag also
  gates content in `DT_Quests`, `Facility_Pens` and `Facility_Residence`, so setting it would change story and Facility state in ways
  nobody has mapped.
- The hub already does the safe version for custom worlds. `apply_vignette_type` adds `PortalHub_<id>_Completed` to `DT_WorldFlags`
  and re-points the world's `Vignette_Zone` at it. A forced completion is that same step aimed at a base-game zone, with the hub setting
  the flag itself.
- **"Completed" in this game means one thing only: portal sickness is lifted for good in that world.** Equipment, the jetpack included,
  then works there. Nothing found records completion anywhere else: no "completed" text exists for portal worlds in the string tables,
  and these worlds have no true-exit reward. So forcing it changes no rewards and no story. It makes those worlds easier.
- **Third world in the same position: Albatross (`V_ISLAND`).** It also names `DemoNeverSet`. It is the final story world
  (`EndBossDefeated`, `End_Boss_FightStartedOnce`), so the sickness there is plainly deliberate. Offering it is LuciDin's call (see
  "Open questions").

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
  `DemoNeverSet` (both) and `Wall_AG_met` (the Wall). `V_ISLAND.umap` (Albatross) also names `DemoNeverSet`. No other world map does.
  As the name suggests, `DemoNeverSet` is a flag that is never set. So these zones keep the sickness on forever: **this is by design,
  not a missing trigger.**
  - Inference, not yet read in game: the map files use unversioned properties, so the name table shows that the map uses
    `DemoNeverSet` but not which property holds it. The zone's `PortalSicknessWorldFlag` is the only flag property these maps need,
    and the wiki agrees ("Some Distant Shore cannot be completed", so the jetpack can't be used there). The data is also from 21 August,
    before v1.5.0. Test 1 below confirms both with an existing lab key.
- Some Distant Shore (wiki): a secret world reached from a Portal Toilet. It has a true exit (walking into the "ocean" goes to the Data
  Farm bathroom), but that exit sets no flag. It gives no reward, and its only achievement comes on the first visit.
- GATE Arch Defense Facility (wiki): a required story world. On the first visit the player is held in a forcefield until Garrick tells
  the Gatekeeper to let them out. Its pod holds the Motion Module and Excursion Suit recipes. Its pads are `wall_start`, `wall_exit`,
  `wall_return`. No completion is described.
- **Other worlds:** only Albatross shares the same zone flag. Homes (`H_Cabin`, `H_Garden`, `H_Japan`) have no sickness. `V_Tile`
  (IS-0031) is not a vignette in `DT_Levels`. `V_Dummy` and `V_Intro` hold no zone.

## 3. Is a forced completion possible and safe?

**Which call:** the hub's existing calls, no new native ones. Done on the host, in order:

1. `ensure_flag_row` for a hub row, `PortalHub_force_<key>_Completed`. Keeping the `PortalHub_..._Completed` shape lets lab NUMPAD 3
   clear it too.
2. Find that world's `Vignette_Zone_C` (within 1 km of a known pad: `wall_start`, the Distant Shore arrival, `island_start`) whose
   `PortalSicknessWorldFlag.RowName` is `DemoNeverSet`. Write `z.PortalSicknessWorldFlag = { RowName = FName(row) }`, the same write as
   `apply_vignette_type`. Check `IsValid` first and read the value back.
3. `SetWorldFlag({ RowName = FName(row) }, true, pc)` once, after `HasWorldFlagsLoaded()` is true (the CRD-001 early-ask bug).

**What else it changes:**
- Rewards: none. These worlds have no true-exit buff, and the jetpack and equipment unlocking is the whole effect.
- Story: none. No game flag is set and `DemoNeverSet` stays clear, so `DT_Quests`, the Pens and the Residence are untouched.
- Portal room: nothing. The game shows no completion state there.
- **Never set `DemoNeverSet` itself.** That would "complete" all three worlds at once and flip whatever the quests and the two Facility
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

None were run (no install was approved, and the lab is not installed right now). One read-only check is worth doing before the build
card, with an existing lab key (no new key, no code change):

| Key | Run it in | What it logs |
|---|---|---|
| NUMPAD 7 | Inside GATE Arch Defense Facility (hub portal to `wall_start`), CordonaCorp or Mod Testing | The zone's `world flag:` (expected `DemoNeverSet`), whether `Debuff_PortalSickness` is on, the save's Portal Hub flags |
| NUMPAD 7 | Inside Some Distant Shore (hub portal to Distant Shore) | The same; expected `DemoNeverSet` |
| PAGE UP | Same two places | Zones with their flag and "set in this save", pads that set a flag (expected: none for these worlds) |

Writing a flag to a save (the build card's own test) needs LuciDin's yes and a save backup first.

## Open questions for LuciDin

1. Which worlds go in the switch: ARCH Defense and Distant Shore only, or Albatross too (final story world, sickness deliberate)?
2. Where the switch goes in the editor: HUB EXITS tab, or a tab of its own?
3. Does it ship in 1.0 (after the touch-ups, before CRD-035), or wait for 1.x?
