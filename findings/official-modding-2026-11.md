# Official modding (v1.5.0) and what it means for the Portal Hub

Checked 3 November 2026 (CRD-005), read-only. Sources: the new exe's strings, the UE4SS object dump of 27 October (first
launch on v1.5.0), the game log and `Modio.log` of that launch, the local mod.io folder, and public pages (list at the end).
The Mod Editor was still downloading (`C:\Users\lukea\Games\Mods\SCIENCE\MOD EDITOR`, empty), so section 6 lists what to check
in it later.

**Game moved again today:** hotfix **v1.5.0.31876** (Steam build 26373201, 3 Nov; the exe and `pakchunk0` are dated 3 Nov 22:39).
Before it came 1.5.0.31650 (27 Oct) and 1.5.0.31836 (30 Oct, a fix for saves corrupted by adding mods). None of the three
notes mention data tables, levels or structs. The 27 Oct object dump is from a slightly older build, so treat member lists
below as "true on 27 Oct".

## Verdict

**Keep the UE4SS route for the hub and the worlds.** The official system cannot do what the hub does: Deep Field says
official mods cannot add Facility levels or portal worlds, or edit existing levels, and the row system behind it has no row
type for `DT_Levels`. Deep Field also says it will not block unofficial mods and that working around the tools' limits is
fine. Watch two things: (1) whether the new row registry wipes rows the hub adds with `AddRow` (one in-game test, section 4);
(2) the Mod Editor itself, which may still be useful as a **better editor for building worlds** (real game assets), even if
the worlds keep shipping as `~mods` paks.

## 1. Official vs unofficial

| | Official (mod.io / UGC) | Unofficial (our hub and worlds) |
|---|---|---|
| What it is | An Unreal **content-only plugin**: a `.uplugin` plus `Content\Paks\` (`.pak`, plus `.ucas`/`.utoc` with IoStore), zipped and uploaded to mod.io. Mounted by the game's `ModioUGC` plugin (`UGCSubsystem`, `UGCPackage`: `DescriptorPath`, `MountedPakFilePaths`, `EngineVersion`, `MountState`) | UE4SS Lua in `Binaries\Win64\ue4ss\Mods\`, world paks in `Content\Paks\~mods\` |
| How it's installed | In-game browser on the title screen (subscribe), then picked per save (Saved Worlds > MODS). Cosmetic mods are "local only" and picked on the customisation screen | By hand, by every player; not shown in the browser |
| Load order | `ABFRowRegistrySubsystem` resolves a load order (`K2_GetResolvedLoadOrder`, `LoadAfter` dependencies, pinning above or below in the list); local-only mods always load last | Pak mount order (the 27 Oct log mounts `~mods` paks before `pakchunk0`); the game's mod list does not know about them |
| Per save | Saved with the world; disabling one later removes its content from the save | Nothing stored, except the hub's completion flags (plain names) |
| Game updates | Version-checked against the game's engine build (`EUGCRejectionReason::IncompatibleEngineVersion`, `ModioUGCSettings` checks major, minor, patch and changelist): **disabled after every game update until the author rebuilds and re-uploads** | Not checked; keeps loading, and breaks if the game's code or data changed (as v1.5.0 did) |
| Multiplayer | Server sends its list, client downloads it in one click; a mismatch is refused ("Rejecting %s for mod load order: client has [...], server runs [...]"). Local-only mods are refused unless the server allows them (`AllowLocalOnlyMods`, "Allow local cosmetic mods" on hosts) | Not synced or checked by the game: every player must install the same files themselves. Some hosts cannot run UE4SS at all |
| Dedicated servers | `-Mods=<id;id>`, `-ModioToken=`, `-ModsDir=`, `-ModInstallTimeout=`, `-OverrideModWarnings`, `-SideloadMods` (+ `-SideloadModsPath=`, default `AbioticFactor\Mods`; exe has `AbioticModSideloadUgcProvider`) | Hand-copied paks; UE4SS where the host allows it |
| Warnings | The game's own mod list shows issues (`EAbioticModListIssue`: NotInstalled, NotEnabled, FailedToLoad, Refused) | Every hotfix note says to remove unofficial mods first if the game crashes; no in-game warning seen |
| Consoles | PC, Xbox, PS5 | PC only |

## 2. What official mods can and cannot do

- **Can** (the 76 `*ModRowAsset` classes in the dump, matching the store page's list): items, deployables, recipes, NPCs, pets,
  traders, buffs, perks, traits, PhDs, chemistry, emotes, animations, customisation, fish, plants, projectiles, quests, salvage,
  **weather events**, **waypoints**, **lighting rows (`LevelFXModRowAsset`)**, **story flags (`WorldFlagModRowAsset`)**,
  `UnderwaterFXModRowAsset`, spawn substitutes. Each asset has `RowName` and `bOverrideExistingRow`. A mod plugin needs an
  `AbioticModConfig` asset (it sets the mod's **row prefix**); without it no rows are registered.
- **Script-like code:** `UGCMutator` Blueprints (`Initialised`, `PostPlayerInit`, `PostPawnSpawned`, `AssetOverrides`,
  registered with a priority by `UGCMutatorSubsystem`). This is the official way to run logic. Blueprint only, no Lua.
- **Cannot** (Deep Field's Modding FAQ and the Entropic Break update, both on Steam): add Facility levels or **portal worlds**,
  or **edit existing levels**; add sandbox or gameplay settings or keybindings; localisation. New levels and sectors are "being
  investigated" and called very complicated; no promise. This is the full version of the hosting guide's cut-off sentence.
- There is **no `LevelMetadata` row type**, so an official mod cannot register a level in `DT_Levels`. That is exactly what the hub
  needs for vignette worlds (`ensure_level_row`).

**So: no supported way to add a world without UE4SS.** A mutator could in theory spawn a teleporter or stream a map that sits
inside its own plugin (UE's `LoadLevelInstance` is open to Blueprints), but that runs against the stated rule, would need the
whole hub rewritten in Blueprint, still could not add a `DT_Levels` row, and could be pulled from mod.io. Not recommended;
noted only as the one technical opening.

## 3. Could our world paks be official mods while the hub stays UE4SS?

Technically mostly yes, in practice no:
- A world would have to be rebuilt as a UGC plugin **in the Mod Editor** (same engine build as the game; our UE 5.4.4 projects
  would not pass the changelist check), mounted at the plugin's own root (`/<PluginName>/...`, not `/Game/...`), so the hub's
  loader paths change.
- It would be **disabled after every game update** until rebuilt, which is worse than today (our `~mods` paks survived v1.5.0
  untouched).
- It would carry a map, which the rules say mods may not add, and on its own it does nothing: it needs the unofficial hub, which
  console and most server players cannot run. A listing like that would mislead people browsing in game.
- One upside if it were ever allowed: the hub could find worlds by itself (`UGCSubsystem:K2_EnumerateAllUGCPackages`, readable
  from Lua) instead of `config.lua`, and the per-save list would decide which worlds a save has.

Keep the worlds as `~mods` paks. The official route may become right if Deep Field ever adds level support; check their news
on each update.

## 4. `ABFRowRegistrySubsystem`

From the dump and the exe's `LogRowRegistry` messages:
- An **engine subsystem** (`Subsystems\Engine\ABFRowRegistrySubsystem.cpp`) with `BaseTables` (an array of DataTables),
  `RootedModObjects`, and a load order (`SetSessionLoadOrder` / `ClearSessionLoadOrder` for a server's order,
  `GetLoadOrderForNetwork`, `GetLocalOnlyModsForNetwork`, `InvalidateLoadOrder`, `SetModioDependencies`, cached mod profiles).
- It listens to **`OnUGCPackagesChanged`** and then registers each mod plugin "as a row source" with its prefix, merging the mod
  rows into the game's tables. Rules from its messages: a mod row with a base-game name is skipped unless it is marked as an
  override; mod rows colliding with each other: first one wins; an override with no target yet is kept "dormant"; a row type that
  does not support UGC is skipped. Rows are tagged with their origin (`UGCRowInfo`: `bIsUGC`, `ModId`, `ModName`, `Author`), which
  is where the "modded" tooltip comes from.
- **Which tables it manages:** the ones that have a row-asset type. That includes **`DT_WorldFlags`** (the hub's completion flags)
  and **`DT_LevelFX`** (lighting), but **not `DT_Levels`** (the hub's level rows).
- **Does it rebuild tables?** Not provable from strings alone. `BaseTables` plus "registered dormant" suggest it keeps a copy of
  the base rows and rebuilds the managed tables when the set of mounted mods changes (mods enabled per save, joining a server,
  `InvalidateLoadOrder`). If so, a `PortalHub_<id>_Completed` row added with `AddRow` would be **dropped at the next rebuild**,
  while the `PortalHub_<id>` level rows in `DT_Levels` would be left alone. With no official mods enabled nothing logged a
  `LogRowRegistry` line on 27 Oct.
- **What the hub already does about it:** `ensure_flag_row` looks the row up with `FindRow` and adds it again if it is missing,
  so the risk is only between a rebuild and the hub's next check.
- **Test to settle it (CordonaCorp):** read `ABFRowRegistrySubsystem.BaseTables` from Lua (which tables are listed), then enable
  any one official mod for CordonaCorp, load in, and check that `DT_WorldFlags:FindRow("PortalHub_<id>_Completed")` still finds
  the row, and whether a completed vignette world stays completed. Good as a lab key next to NUMPAD 3.

## 5. Shipping on mod.io (roadmap step 8)

- The **in-game browser only installs UGC plugins**: it unzips, reads the `.uplugin` ("Failed to read uplugin file", "uplugin
  missing engine version") and mounts the paks. A zip holding a UE4SS mod or `~mods` paks would show as broken or refused in game.
  The hub cannot be installed from inside the game.
- A **web-only listing** on mod.io (download by hand) might be possible, but mod.io's main site cannot be read from here (it blocks
  AI crawlers) and the game's mod.io rules are not on Steam. Ask Deep Field (Discord or the Steam forum) whether unofficial or
  tool uploads are allowed in the Abiotic Factor category before planning on it. AI-made mods are allowed on mod.io (checked by
  LuciDin).
- **Recommendation for step 8:** keep the plan (one download with the GUI, the hub and the presets), aimed at Nexus and GitHub.
  Add a clear note on the page: unofficial, PC only, every player in a session needs the same files, not shown in the in-game mod
  list, may break on game updates. Add mod.io only if Deep Field says yes.

## 6. Mod Editor: check once it is installed (read-only, never sign in)

1. Engine build (`Engine\Build\Build.version`, the editor's own version string) against the game's `++DF+ABF-CL-...`.
2. Is it a full Unreal editor with the game's content (or stand-ins)? If so, it may be a better place to **build worlds**: real
   teleporters, zones and materials to reference, instead of our placeholders. Question: can a world built there still be cooked
   to a plain `pakchunkNN` for `~mods`, or only to a UGC plugin?
3. Templates and samples (the hotfix notes mention NPC, pet and deployable templates): is there any map or level template, a
   mutator template, a `LevelFX` or `WorldFlag` row example?
4. `AbioticModConfig` fields (row prefix, anything about levels).
5. Docs bundled with it (the Modding FAQ promised an advanced guide).
6. Whether `DT_Levels` and the native `LevelMetadata` struct are editable or visible there.

## 7. Roadmap changes

- **Step 8 (packaging):** stays on Nexus and GitHub; drop "maybe mod.io" until Deep Field answers; add the unofficial and
  multiplayer note above.
- **Step 3 (lighting):** official mods can add lighting rows (`LevelFXModRowAsset`), but a world pak cannot carry one, so the plan
  stays: the hub copies a row with `AddRow` and edits it. Add the registry-rebuild test (section 4) before relying on added rows.
- **Step 7 (tutorial):** once the Mod Editor is checked, decide whether map makers should build worlds in it instead of plain
  UE 5.4.
- **New small task:** the row-registry survival test (section 4).

## Sources

- Steam news (RSS feed `store.steampowered.com/feeds/news/app/427410/`): "Community Update #5 - The Modding Update!" and "How to
  Install Mods" (26 Oct), hotfixes 1.5.0.31650 (27 Oct), 1.5.0.31836 (30 Oct), 1.5.0.31876 (3 Nov), "Entropic Break Development
  Update" (17 Sep).
- Steam community: the developers' Modding FAQ thread (`steamcommunity.com/app/427410/discussions/0/572675720491522460/`).
- Hosting guides (robots.txt allows them): GameServerKings "Abiotic Factor mods" knowledge-base page, Supercraft "mods dedicated
  server" wiki page. Not used: the main mod.io site (blocks AI crawlers), Nexus.
- abioticfactor.wiki.gg, `/wiki/` pages only (`1.5.0_Community_Update_5`, `Mods`; added after the first pass on LuciDin's go-ahead;
  its robots.txt allows `*` with `search=yes, ai-train=no, use=reference` and disallows the `ClaudeBot` training crawler,
  `index.php` and `api.php`). Nothing there contradicts the above. It adds: local-only (cosmetic) mods "work on any server"
  (the exe also has a server-side `AllowLocalOnlyMods` switch and "Rejecting ... AllowLocalOnlyMods is off", so a server can
  still refuse them); and Deep Field runs an **official modding Discord** with guides. That Discord is the place to ask the
  mod.io question in section 5, and to look for the advanced modding guide. The wiki has no Mod Editor page yet.
- docs.mod.io (robots.txt allows it) answered HTTP 403 to page fetches; its ModioUGC packaging summary here comes from search
  results only (a plugin folder with `.uplugin` and `Content\Paks`, zipped and uploaded; cooked with the game's exact engine build).
- Local: `AbioticFactor-Win64-Shipping.exe` (3 Nov) strings; `ue4ss\UE4SS_ObjectDump.txt` (27 Oct); `Saved\Logs\AbioticFactor.log`
  and `Modio.log` (27 Oct); `C:\Users\Public\mod.io\13105\` (game id 13105; only browser thumbnails cached, no mods installed);
  `mod/PortalHub/Scripts/main.lua` (`ensure_flag_row`, `ensure_level_row`).
