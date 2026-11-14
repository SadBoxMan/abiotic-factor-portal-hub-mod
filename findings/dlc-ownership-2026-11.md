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
- The config editor refuses the same names (`hubdata.is_dlc` by prefix, `is_reserved`, `names_dlc_map`).
- Tests: `tools/dev/tests/test_hub_dlc_block.py` (83 checks; the guards and the dev test below are new), `test_gui.py` (9 new checks),
  `tools/dev/tests/test_dlc_survey.py` (the survey mod, 24 checks).
- `main.lua` is close to Lua's limit of 200 local variables in one function: the main chunk had room for 10 more before and after this
  change (the guards live in one table). New top-level code should go into tables too.

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

PENDING: boxes from the `CordonaDlcSurvey` run (`mod/CordonaDlcSurvey/`, key `'`, read-only, its own test step). The survey lists every
`AbioticLevelStreamingVolume` and `LevelManagerInstance` with a `RequiredEntitlement` or `RequiredWorldFlag`, each volume's box
(`GetActorBounds`), the six home pads, and the box around each DLC area. The hub keeps those two boxes, plus 20 m, as `DLC.areas`.

## If "allow when owned" is ever wanted (not built)

- Check with `AbioticGameState:HasServerGameEntitlement(handle)`: the same rule the game's home pads use. The handle is
  `{ DataTable = <DT_GameEntitlements>, RowName = FName("HomeworldGarden" | "SupportersEdition") }`, or the game pad's own `RequiredDLC`
  read from `H_*_Entrance`. The game state comes from the world (`GetGameState` / `GameState`), found once per load, not by a periodic search.
- Ownership can change mid-session when the owner leaves. A Blueprint hook on `BP_Teleporter_HomeWorld_C:OnServerEntitlementsUpdated` (a
  Blueprint function, so the same hook path as AttemptTeleport) could re-check the pads. AttemptTeleport's hook runs after the teleport,
  so it can't refuse a use beforehand.
- Every one of these calls is untried in game: each would go on its own test step. If the answer can't be read, refuse.
- The editor would have to stop refusing DLC pads for owners.

## In game

The guards don't depend on owning the DLC, so LuciDin (who owns both) can test them as they are: no ownership spoof is needed. What a
player without the DLC would meet is exactly what an owner meets: no hub route in. The one part that can't be shown by refusing is the
backstop, so a dev key stands in for "a route the guards missed": **PAUSE** (hub, `DEV_KEYS` only; the release builder cuts the whole
`if DEV_KEYS then` block, so it never ships; Pause has no default binding in the game).

| Key | Run it in | What it logs |
|---|---|---|
| PAUSE (1st press) | CordonaCorp or Mod Testing, portal room | `DLC test: PASS/FAIL ...` for each home pad, `train_start` and the name rules against the real game (the surveyed boxes must hold `H_Garden_Start` and `H_Japan_Start` and nothing in the portal room or the Cabin), then `self-check: N PASS, 0 FAIL`; a test pad `hub_dlctest` 3 m ahead leads into Stone Garden |
| walk into the pad | same | `DLC: ... landed inside Stone Garden ... after using hub_dlctest; sent back`; on screen: "Stone Garden is DLC: the Portal Hub doesn't lead there" |
| PAUSE (2nd press), walk in | same | the same for Torii |
| PAUSE (3rd press) | same | the test pad is removed |

Plus a config check: a hand-added line such as `{ slot = "C-4", destination = "H_Garden_Pond" }` or `destination = "hub_mhe_train_start"`
in a copy of `config.lua` (after copying LuciDin's own aside) is refused at load. Results: PENDING.
