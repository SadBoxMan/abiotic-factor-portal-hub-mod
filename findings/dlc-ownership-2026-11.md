# DLC worlds and the hub (CRD-033, November 2026)

LuciDin's ruling (13 November): the mod must not let players bypass the paid DLC. A hub portal to Stone Garden (`H_Garden_*`) or Torii
(`H_Japan_*`) must be refused when the player doesn't own that DLC. This note records how the game itself knows DLC ownership, what the hub
does, the design LuciDin chose, and the routes into a DLC world that were checked. Desk research only: the UE4SS object dump (6 November,
`ue4ss_backup_2026-11-10_pre-fresh-install\ue4ss\UE4SS_ObjectDump.txt`, game v1.5.0) and the teleporter dump (`PortalLogger.txt`, in the
game's `Win64` folder). Only the game's own objects were read. No third-party mod code was used.

## Verdict and design

- **The hub already refused every DLC destination, owned or not.** `BLOCKED_DESTINATIONS` in `mod/PortalHub/Scripts/main.lua` (since
  bce2c4e, 11 October) lists `h_garden_start`, `h_garden_entrance`, `h_japan_start` and `h_japan_entrance`. `resolve_config` compares each
  portal's destination in lower case (the game's FNames ignore case) and skips a match with the log line
  `config entry N: <pad> is a DLC area and cannot be a destination, skipped`. The config editor refuses the same four pads
  (`hubdata.DLC_PADS`, since CRD-013). So a hand-edited `config.lua` was already covered. The card's starting point ("the hub doesn't
  check a hand-edited config.lua") was not right.
- **LuciDin's design choice (13 November): keep the blanket block.** It is stricter than the ruling: owners can't make a hub portal to their
  own DLC home either. They lose little, because the game's own Stone Garden and Torii portals stand in the same room (locked slots A-1 and
  A-2). It needs no entitlement calls and raises no multiplayer question.
- **Then (same night): make it as airtight as practical against curious users.** LuciDin knows an open-source mod can't stop someone who
  edits its code, but every route that only needs `config.lua` or `manual_exits.lua` edits should be closed. The routes found are in the
  table below. He chose all four guards, now in `main.lua` (the `DLC` table near the top):
  - **names:** any destination starting with `h_garden` or `h_japan` (not just the four pads), any of the hub's own pad IDs (`hub_...`,
    `portalroom_...`; an MHE stands inside its world, so `destination = "hub_mhe_<world>"` would lead into any world), and custom worlds whose
    ID, loader or level names a DLC area (by path part, so `Th_Gardens` is fine). All in lower case, as the game's pad IDs ignore case.
  - **spots:** a manual portal's spot (the portal falls back to `game`), an MHE (not placed; the DLC homes' own MHEs included, since the
    game's home pads already lead out), the Failsafe Exit (the fallback spot in front of the first hub portal is used), a custom world's
    origin or arrival from `config.lua` (the world is refused) or from its loader Blueprint (no arrival pad, its portals stay off), and a
    vignette's exit pad. "Inside" means inside the box around the game's own DLC-gated streaming volumes, plus 20 m (see "The DLC areas").
  - **pads:** at each spawn, a hub portal whose destination pad stands inside a DLC area (for example a player-built `teleporterpadN` there)
    is not spawned. The pads' positions are read once per spawn (one pad search, as the spawn already does).
  - **use (backstop):** after any hub pad is used (host only), the player is looked at 0.1, 0.6 and 1.5 s later; one who stands inside a DLC
    area is moved straight back to the front of the hub portal they used (for a manual portal its hub portal, otherwise the portal room),
    held 1 s, then let fall, as the exit moves do. A log line says so, and this machine's own player gets an on-screen line. It catches
    what the others can't see beforehand: a destination pad that wasn't loaded at spawn time, or one built later. The game's own pads,
    its home portals included, are never touched.
- **14 November: owners may have hub portals there (LuciDin).** He pointed out that players without the DLC can visit the DLC areas a host
  owns (the game's own rule), so the guards are for sessions without the DLC: a single-player world or a host that doesn't own it. Now
  each guard applies only to an area whose DLC the session doesn't own:
  - **Ownership** is the game's own check, `AbioticGameState:HasServerGameEntitlement({ DataTable = DT_GameEntitlements, RowName = row })`,
    with the rows the game's home pads name (`HomeworldGarden`, `SupportersEdition`). It is server-wide (any present player who owns it,
    as the game counts it), the same rule as the game's A-1 / A-2 portals, so the hub never gives more than the game does. The game state
    is read from the world (`world.GameState`); no object search.
  - It is read when the portals spawn (the config is read again whenever the answer changes) and again by the backstop when someone lands
    in an area, so an owner who leaves closes the area at once. An owner who joins opens it at the next spawn (NUMPAD 1 or the next load).
    Unreadable counts as not owned.
  - **Still refused for everyone:** the hub's own `hub_*` IDs as destinations, and custom worlds that name or sit on a DLC map (origin,
    arrival, vignette exit). Owners don't need those.
  - **The editor** can't know ownership offline: a DLC destination saves, with an amber warning ("only if you, or the host in multiplayer,
    own that DLC"). The `hub_*` and custom-world refusals stay.
  - **Dev key PAUSE** got a "pretend not owned" switch, so an owner can test both sides (below).
- Tests: `tools/dev/tests/test_hub_dlc_block.py` (109 checks), `test_gui.py` (71), `tools/dev/tests/test_dlc_survey.py` (28).
- `main.lua` is close to Lua's limit of 200 local variables in one function: 13 free in the main chunk, before and after this work (the
  guards live in one table). New top-level code should go into tables too.

## How the game knows DLC ownership

The game has an entitlement system of its own (native classes in `/Script/AbioticFactor`, Blueprints in `/Game/Blueprints`):

| Object | What it is |
|---|---|
| `DT_GameEntitlements` (`/Game/Blueprints/DataTables/`) | One row per entitlement. Row struct `GameEntitlement`: the store IDs `ID_STEAM`, `ID_EOS`, `ID_GDK`, `ID_PS5` (strings). |
| `GameEntitlementRowHandle` | The handle every check takes (a row handle into that table, 0x10 bytes). `GameEntitlementHandleFunctionLibrary` makes and breaks them. |
| `AbioticGameInstance:GetUnlockedEntitlements()` / `HasGameEntitlement(handle)` | **This machine's** platform ownership (the store's own answer for the signed-in user). |
| `Abiotic_PlayerController_C:Request_UpdateDLCEntitlements(PlayerEntitlements)` | Each player reports their own entitlements to the server. |
| `Abiotic_Survival_GameMode_C:InitDLCEntitlements`, `AddPlayerDLCEntitlements(PlayerId, ...)`, `RemovePlayerDLCEntitlements(PlayerId)` | The server keeps a map of player ID to entitlements. Init builds a new map (`MakeMap`), so it is rebuilt at each world start. |
| `AbioticGameState:ServerEntitlements` (replicated string array), `SetServerEntitlements(map)`, `HasServerGameEntitlement(handle)`, `OnServerEntitlementsUpdated` | **The server-wide set**: what the players in the session own, together. Clients get it by replication. |
| `PlatformFunctionLibrary_C:ShouldHomeworldBeActive(RequiredDLC, RequiredWorldFlag)` | Calls `HasServerGameEntitlement`. This is the check behind the home portals. |
| `BP_Teleporter_HomeWorld_C`: `RequiredDLC`, `RequiredWorldFlag`, `OnServerEntitlementsUpdated` | The game's home pads. They switch themselves on or off when the server's set changes. |
| `AbioticGameState:CanLevelBeActive(RequiredEntitlement, RequiredWorldFlag)`, `LevelManagerInstance:RequiredEntitlement`, `AbioticLevelStreamingVolume:RequiredEntitlement` | Level streaming is gated by entitlement too. |
| `AbioticCharacter:RejectDLCTeleport` | Blueprint-implemented; finds actors of a class and teleports the player. Most likely it sends a player out of a DLC area they may not be in. |

The game's home pads, from the teleporter dump (all six are in the Facility's **persistent level**, so they are always loaded):

| Pad | Leads to | `RequiredDLC` | `RequiredWorldFlag` |
|---|---|---|---|
| `H_Garden_Entrance` (A-1) / `H_Garden_Start` | each other | `HomeworldGarden` | None |
| `H_Japan_Entrance` (A-2) / `H_Japan_Start` | each other | `SupportersEdition` | None |
| `H_Cabin_Entrance` (B-3) / `H_Cabin_Start` | each other | None | `SnowglobeComplete` (story, not DLC) |

So Torii comes with the **Supporter Edition** entitlement, not a homeworld DLC of its own. The Cabin is gated by story progress only, which
is why the hub allows `H_Cabin_Start` as a destination.

**Why this is real ownership, not "visited once":** the server's set is built from each present player's own store check
(`GetUnlockedEntitlements` → `Request_UpdateDLCEntitlements`), and the map is rebuilt at world start. Nothing in it comes from the save's
history. Not confirmed (it would need the Blueprint bytecode, which the dump doesn't hold): whether `RemovePlayerDLCEntitlements` runs when a
player leaves (most likely, given its name and its PlayerId argument).

**Multiplayer, as the game does it:** a home portal opens for everyone in the session when any present player owns that DLC
(`HasServerGameEntitlement`, server-wide). The game decides that, and the hub's block doesn't change it.

**Why the block matters:** all six home pads are always loaded, so without the block a hub portal to `H_Garden_Start` or `H_Japan_Start`
would land a player who doesn't own the DLC on the game's own pad inside the world.

## Routes into a DLC world, and what stops each

The "Now" column is for a session that doesn't own that DLC; with the DLC owned, only the always-refused routes stay closed (the hub's
own IDs, custom worlds on a DLC map).

| Route (hand edits a curious user could make) | Before CRD-033 | Now |
|---|---|---|
| A portal in `config.lua` to any of the four pads, in any letter case | Refused | Refused (names) |
| A portal to another `h_garden*` / `h_japan*` pad name (one inside the DLC maps that the dump didn't list) | **Open** | Refused (names) |
| A portal to one of the hub's own pads, e.g. `hub_mhe_H_Garden_Start` after adding a Garden spot to `manual_exits.lua` | **Open** | Refused (names); no MHE is placed in a DLC area anyway (spots) |
| An MHE spot moved into a DLC area plus `exits = "manual"` on that world's portal | **Open** | The spot is refused, the portal falls back to `game` (spots) |
| An MHE or the Failsafe Exit moved into a DLC area, reached as a destination or by the hub's own moves | **Open** | Not placed / fallback spot (spots) |
| A custom world named after a DLC pad, or whose loader or level names a DLC map | Partly (the name only) | Refused, with its portals (names) |
| A custom world whose origin or arrival (config.lua or loader Blueprint) is inside a DLC area | **Open** | Refused / portals stay off (spots) |
| A vignette's exit pad moved into a DLC area, then named as a destination | **Open** | Not placed (spots) |
| A portal to a player-built portal (`teleporterpadN`) that someone built inside a DLC home | **Open** | Not spawned (pads); if the pad loads later, the backstop sends the player back (use) |
| Anything else that gets a player into a DLC area through a hub pad | **Open** | Backstop (use) |
| Exit mode `manual` to a DLC pad; locked slots A-1 / A-2; NUMPAD 1 | Refused / untouched / nothing comes back | The same |
| Hub and dynamic exit routing, `route_return` | Only lead to hub portals in the portal room, or rewrite custom worlds' arrival pads | The same |
| The config editor | The four pads | The same names as the hub |

**What can't be closed** in an open-source mod: editing `main.lua` or `slots.lua` (the slot positions), or building a custom world pak whose
loader streams a DLC map in under another name somewhere else. Those take deliberate work, not a curious edit. The game's own gate also still
stands behind ours: its level streaming won't load a DLC area for a session that doesn't own it (`RequiredEntitlement` on the streaming
volumes and level managers), and `AbioticCharacter:RejectDLCTeleport` most likely moves a player out of one.

## The DLC areas

Read by the `CordonaDlcSurvey` run on 14 November, 12:05 (CordonaCorp, game v1.5.0; `mod/CordonaDlcSurvey/`, key `'`, read-only). Of the
game's 223 `AbioticLevelStreamingVolume`s, three carry a gate, each with one `LevelManagerInstance` of its own:

| Volume | Gate | Box centre | Half-size (x, y, z) |
|---|---|---|---|
| `AbioticLevelStreamingVolume_155` | entitlement `HomeworldGarden` (Stone Garden) | 127267, 157550, 59059 | 12000, 11000, 8000 |
| `AbioticLevelStreamingVolume_109` | entitlement `SupportersEdition` (Torii) | 126883, 121733, 60453 | 12000, 11000, 4000 |
| `AbioticLevelStreamingVolume_156` | world flag `SnowglobeComplete` (the Cabin) | 127267, 112062, -1477 | 12000, 11000, 8000 |

Each DLC box holds its area's arrival pad (`H_Garden_Start`, `H_Japan_Start`). The hub keeps the two DLC boxes as `DLC.areas`, with a 100 m
margin, since a streaming volume only triggers the load and the level may reach a little past it. Clearance: the Cabin's area lies under
Torii in x and y but about 500 m lower (its arrival pad is 593 m from the Torii box), the nearest recorded MHE (Canaan, `salem_begin`) is
785 m away, and the nearest other pads (Rise, Praetorium, Albatross) are over 1 km away. `test_hub_dlc_block.py` checks that none of the 22
shipped MHEs or the failsafe falls inside. The two player-built pads in LuciDin's save (`teleporterpad1`, `teleporterpad87`) are inside
Stone Garden. The survey's untried calls worked: `GetActorBounds` filled its out-parameters, and the row handles read as text.

## Notes kept from before "allow owners" was built

- Check with `AbioticGameState:HasServerGameEntitlement(handle)`: the same rule the game's home pads use. The handle is
  `{ DataTable = <DT_GameEntitlements>, RowName = FName("HomeworldGarden" | "SupportersEdition") }`, or the game pad's own `RequiredDLC`
  read from `H_*_Entrance`. The game state comes from the world (`GetGameState` / `GameState`), found once per load, not by a periodic search.
- Ownership can change mid-session when the owner leaves. A Blueprint hook on `BP_Teleporter_HomeWorld_C:OnServerEntitlementsUpdated` (a
  Blueprint function, so the same hook path as AttemptTeleport) could re-check the pads. AttemptTeleport's hook runs after the teleport,
  so it can't refuse a use beforehand.
- Every one of these calls is untried in game: each would go on its own test step. If the answer can't be read, refuse.
- (Built 14 November as above, without the OnServerEntitlementsUpdated hook: the backstop asks again instead.)

## In game

Two steps, after CRD-032 part 2's soak has the install back. The survey's ownership readout comes first, because the ownership call has
never been tried in game. Then the hub test.

| Key | Run it in | What it logs |
|---|---|---|
| `'` (survey, switched on for the run) | CordonaCorp or Mod Testing, anywhere in the Facility | `ownership Stone Garden (HomeworldGarden) | session ... | this machine ...`, the same for Torii, the lists behind them, and the game's own DLC pads' `IsTeleporterActive`. For an owner of both, all `true` |
| PAUSE (1st press) | portal room | `pretend not owned ON`, the portals respawn; the self-check (`self-check: 14 PASS, 0 FAIL`, and "the game says ... owned; the hub treats it as not owned"); a test pad 3 m ahead into Stone Garden |
| walk into the pad | same | sent straight back: `DLC: ... landed inside Stone Garden ... sent back`, on screen "Stone Garden is DLC: the Portal Hub doesn't lead there" |
| PAUSE (2nd press), walk in | same | the same for Torii |
| PAUSE (3rd press), walk in | same | `pretend not owned OFF`, the portals respawn; the pad into Stone Garden says "owned": you stay there |
| PAUSE (4th press) | same | the test pad is removed |

The first round (14 November, the blanket version) was installed but never run: "allow owners" came first.

**Results, 14 November.**
- Survey, ownership readout (15:40, CRD-032 part 2's install, hub d061ced): world, game state, game instance and entitlement table all
  readable; Stone Garden and Torii both `true` for the session (`HasServerGameEntitlement`) and for this machine (`HasGameEntitlement`);
  `ServerEntitlements = [SupportersEdition, HomeworldGarden]`; the game's A-1 / A-2 pads active. Only `GetUnlockedEntitlements` didn't
  read (informative; the hub doesn't use it). No error, clean exit.
- PAUSE test (17:10, CordonaCorp, hub 3b8fa87 = 14f9e62 + CRD-032's game-thread delay fix e92f782, dev keys on; LuciDin owns both DLCs):
  at the spawn both owned, all 9 configured portals spawned. Press 1 (pretend not owned): portals respawned, the game's real answer
  "owned" logged beside "treated as not owned"; walking into the test pad landed LuciDin in Stone Garden and the backstop sent him straight
  back to the portal room, with the on-screen line. Press 2: the same from Torii (twice). Press 3 (pretend off, owned): no bounce, he stayed
  in Stone Garden. Press 4: pad removed. 0 "Ref was not function", no error, clean exit, no crash report.
- The self-check read 13 PASS, 1 FAIL: it expected the player-built pad `teleporterpad87` inside Stone Garden, as in the save the
  teleporter dump came from, but in this save that ID is a different pad far away (player-built pad IDs differ per save). A test mistake,
  not the hub's; that expectation is dropped (the self-check now has 13 checks).
- The non-owner path can only be shown with "pretend not owned" (LuciDin owns both); the mock tests cover the rest (partial ownership,
  an owner leaving, unreadable = refused). A real check with a host who lacks the DLC and a guest who owns it stays open (optional).
