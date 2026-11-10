# In-game and per-save portal configuration (CRD-018, research)

Date: 9 November 2026. Desk research only: the UE4SS object dump (`ue4ss\UE4SS_ObjectDump.txt`, taken 6 November in a loaded
save on v1.5.0), the save folders, the hub's own code and the earlier findings. No game files were changed and no probe was run.
Everything marked **(probe)** is read from the dump and still needs an in-game check.

The Tkinter config GUI stays the main way to set portals. Everything below is in addition to it.

## Summary and recommendation

| Question | Answer |
|---|---|
| Can the hub tell which save is loaded? | Yes, very likely: `AbioticGameInstance.ActiveWorldSaveName` (a String) holds the world save's folder name (probe: when it is set, and what a client sees). |
| Where should a per-save config live? | In the hub's own mod folder, `Mods\PortalHub\saves\<save name>.lua`, not in the save folder. |
| How does it layer? | Per-save overrides global, portal by portal (keyed by slot); everything not named falls through to `config.lua`. |
| In-game option A (Main Menu entry) | Feasible but the riskiest and least useful: no world is loaded there, so it can only edit files, and the menu is a Blueprint widget tree we would have to graft into. |
| In-game option B (terminal in the hub) | Feasible and fits the theme: an interactable spawned in the portal room, handled on the host, changes apply at once. Start with a cycling-prompt button, not a UMG list. |
| Which first? | **B, as a cycling prompt, after CRD-012 lands.** A later, if at all. |
| Per-save for 1.0? | **No, 2.0 (or 1.x).** It is cheap on the mod side, but it needs a GUI save picker, multiplayer rules and a probe round; 1.0 should ship the global config it already has. Do the identification probe now (it is small) so the design is ready. |

## 1. Per-save portal configuration

### How the mod can tell which save is loaded

From the dump (`/Script/AbioticFactor`):

- `AbioticGameInstance:ActiveWorldSaveName` (StrProperty, offset 0x350). The game instance outlives level changes, so the hub can
  read it from `FindFirstOf("AbioticGameInstance")` (or `UEHelpers.GetGameInstance()`) whenever it spawns portals.
- Also there: `AbioticGameInstance:WorldSaveMap`, `GetWorldSave(LevelSuffix, bNewSave)`, `GetMetaDataSave(bNewSave)`,
  `DoesWorldSaveExist(LevelSuffix)`; `AbioticSave:SaveIdentifier` (String) on every save object; `AbioticWorldSave:LevelGUID`.
- `AbioticFunctionLibrary`: `GetSaveSubfolderName()`, `SanitizeSaveFolderName(FolderName)`, `GetWorldSaveFileList(WorldFolder)`,
  `GetWorldSandboxSettingsFilePath(WorldSaveName)`, `SortSavesByDate(SaveMap, bSortByNewest)`. These are static and could be
  called from Lua through the class default object.
- `AbioticWorldMetadataSave:CustomLevelOverride` (Name) and `StoryProgressionRow` (Name): not needed for identification, but they
  say which map a world uses, which may matter later for custom-level saves.

On disk a world save is a folder:
`%LOCALAPPDATA%\AbioticFactor\Saved\SaveGames\<steam id>\Worlds\<save name>\` holding `WorldSave_MetaData.sav`,
`WorldSave_Facility*.sav`, one `WorldSave_V_<world>.sav` per vignette visited, `SandboxSettings.ini` and `PlayerData\`. The folder
name is what the main menu shows (`CordonaCorp`, `Mod Testing`), so `ActiveWorldSaveName` is expected to be that string (probe).

Open points for the probe:
1. Is `ActiveWorldSaveName` already set when the hub spawns its portals (the Homeworld pad's `NotifyOnNewObject` plus the spawn
   delay)? It should be, since the game reads the save before it builds the level, but it must be logged.
2. What does a **client** in someone else's game see? Probably empty or its own last save; the client must not pick a per-save
   file from it (see multiplayer below).
3. On a **dedicated server** the name comes from the server's own world setting; it should still be the folder name (not checked).
4. A fallback key if the name is empty: none needed; empty means "global config only".

### Where a per-save config could live

| Place | For | Against |
|---|---|---|
| **`Mods\PortalHub\saves\<save name>.lua` (recommended)** | Ours: the game and Steam never touch it; the hub already reads Lua files beside `main.lua` with `require` and the lab already writes files under `ue4ss/Mods/...` with `io.open` (relative to `Binaries\Win64`); the GUI already knows that folder | Not removed when the save is deleted (harmless: a stale file is just never used); a save renamed outside the game loses its config (rename the file) |
| Next to the save (`Worlds\<save name>\PortalHub.lua`) | Travels with the save; deleted with it | The save folder belongs to the game: `SaveGames` has `steam_autocloud.vdf`, so Steam Cloud may sync or drop unknown files, and the game's own copy/backup/delete code (`DeleteDirectory`, the `-Backup` folders) may or may not carry it. One mistake there touches a player's real save. Not worth it. |
| Inside the save (a world flag or save field) | Truly per save, synced with it | Would need writing game save data; out of the question for a config file. |

File name: run the save name through the same cleaning the game uses (`SanitizeSaveFolderName`) or simply keep letters, digits,
space, `-` and `_` and replace the rest with `_`. Write without a BOM; read with `loadfile` inside `pcall` at spawn time (not
`require`, which caches the first file it loaded, so a save switch in the same session would keep the old save's table).

### How it layers with the global config

Suggested rule: **per-save overrides global, slot by slot.**

```lua
-- Mods\PortalHub\saves\CordonaCorp.lua  (written by the GUI or the in-game terminal)
return {
    portals = {
        { slot = "A-3", destination = "train_start", name = "The Train" },   -- replaces whatever config.lua puts on A-3
        { slot = "C-2", off = true },                                         -- empties C-2 for this save only
    },
    exitMode = "hub",   -- optional: any top-level key the hub reads may be overridden the same way
}
```

- `portals`: merged by `slot`. A slot named here replaces the global entry for that slot (whole entry, not field by field, so a
  per-save portal never inherits a stray `design` or `exits` from the global one); `off = true` empties it; slots not named keep
  the global entry.
- Top-level scalars (`exitMode`, `humMode`, `humFloor`, `humManual`): per-save value wins if present.
- `worlds` (custom worlds) and `hideEmitters` stay **global only**: they describe installed paks, not a save's choices.
- `manual_exits.lua` stays global (it is shipped data).
- Log one line on load: `per-save config for 'CordonaCorp': 2 slots overridden (A-3, C-2), exitMode=hub`.

Where it plugs in: one function after `local Config = require("config")` that returns the merged table, called at spawn time (not at
mod load, because the save is not known yet at mod load). CRD-012 is reworking `main.lua` right now; this is a small, separate change
once it lands.

### What the GUI would need

- A **"Applies to"** picker at the top: `All saves (global)` plus one entry per folder under
  `SaveGames\<id>\Worlds\` (skip `*-Backup` folders), newest first by `WorldSave_MetaData.sav` time. Steam id: the single numeric
  folder, or a picker if there are several.
- In a save's view: slots inherited from global are drawn dimmed with a "global" tag; editing one creates the override; a
  "Back to global" button per slot removes it; an "Empty for this save" action writes `off = true`.
- Saving writes only `saves\<name>.lua` (a whole small file, generated, so the comment-preserving `luaconfig.py` editing is not
  needed there; keep a header comment saying the file is generated).
- `luaconfig.py` / `hubdata.py` gain a reader for the override file and a merge used only for display; tests: round-trip, merge
  order, `off`, a missing file, an unknown slot.
- Rough size: GUI 1 card (Opus, medium); mod side 1 small card (Opus, medium) including mock tests.

### Multiplayer

Today every player must install the same hub files themselves (findings/official-modding-2026-11.md); nothing syncs them. Per-save
makes that worse: a client joining `CordonaCorp` has no idea of the host's per-save file. Rule to adopt: **only the host (or
dedicated server) applies per-save overrides; a client uses its global config.** Whether the hub's spawned pads are replicated, and so
whether clients even need their own copy, is not established anywhere in the project yet: that is a precondition for any in-game
editing too (see 2.3).

## 2. In-game configuration

### 2A. A Main Menu entry

What the menu is made of (all Blueprint widgets, `/Game/Blueprints/Widgets/MenuSystem/`):

- `W_MainMenu_Master_C` holds a `MainMenuWidgetSwitcher` and one child page per screen (`W_MainMenu_Initial`, `W_MainMenu_Play`,
  `W_MainMenu_ContinueGame`, `W_MainMenu_HostGame`, `W_MainMenu_Mods`, `W_SettingsMenu`, ...).
- `W_MainMenu_Initial_C` holds the buttons as variables: `W_MainMenuButton_Play`, `_Customize`, `_Mods`, `_Settings`, `_Tutorial`,
  `_Credits`, `_Feedback`, `_ReportBug`, `_Quit`. Their container (a vertical box) is not a variable; it is reached with
  `W_MainMenuButton_Play:GetParent()`.
- `W_MainMenuButton_C`: `ButtonText` (Text), `ButtonLabelText`, `AbioticButton`, `Icon`, a `ButtonPressed` multicast delegate,
  `ChangeLabelText`, `ReconstructButton`. The page reacts through bound events such as
  `BndEvt__W_MainMenuButton_Settings_..._ButtonPressed__DelegateSignature`.
- Ready-made popups: `W_MenuPopup_YesNo_C`, `W_MenuPopup_Notice_C`, `W_MenuPopup_TextInputBox_C`, `W_MenuPopup_DualTextInputBox_C`.

How a mod would add an entry (all **probe**):
1. When `W_MainMenu_Initial_C` constructs (`NotifyOnNewObject` or a hook on its `Construct`), create a `W_MainMenuButton_C` with
   `/Script/UMG.WidgetBlueprintLibrary:Create(world, class, nil)`, set `ButtonText` and call `ChangeLabelText`, then
   `parent:AddChild(button)` on the Play button's parent.
2. Catch the click with a hook on `W_MainMenuButton_C:BndEvt__AbioticButton_K2Node_ComponentBoundEvent_0_OnButtonClickedEvent__DelegateSignature`
   and compare the context with our button (a Lua function cannot be bound to the Blueprint delegate directly).
3. Show the choices. Options, from least to most work: (a) the click cycles a line of text on the button itself; (b) reuse the
   game's popups (`W_MenuPopup_YesNo` for confirm, `W_MenuPopup_TextInputBox` for typing a slot/destination) by creating them and
   setting their text fields; (c) build a whole UMG page in Lua (`StaticConstructObject` of `VerticalBox`, `TextBlock`, `Button`
   into a `WidgetTree`): possible, fragile, and a lot of code for what the GUI already does.

Feasibility and risk:
- Adding children to a live Blueprint widget tree from UE4SS Lua works in general but is the area most likely to crash (widgets built
  outside their `WidgetTree`, a missing `Initialize`, gamepad focus navigation that does not know the new button). The game also
  rebuilds the menu when returning from a world, so the insert has to run every time.
- **Usefulness is low:** at the menu no world is loaded, so nothing can be previewed or applied; it can only edit `config.lua` or a
  per-save file, which the GUI already does better. To be per-save it would also have to ask which save, i.e. re-implement the
  save list (`W_MainMenu_ContinueGame`).
- Multiplayer: none at the menu; it edits the local machine's files only, which a host then uses.
- Saving: `io.open` writes the file (the lab already does this for `manual_exits.lua`, with a load check before writing).
- Rough size: probe card (Opus, medium) plus a build card (Opus, high: new widget code, crash-prone) for even option (a)/(b).

### 2B. An interactable terminal in the Facility or hub

What the game offers:

- **Terminals:** `ComputerTerminal_ParentBP_C` (components `Monitor`, `Base`, `Camera`, `TeleportSpot`, `RectLight`; variables
  `TerminalName`, `TerminalInUse`, `CurrentUser`, `WorldFlagToUse`; functions `InteractWith_A(InteractingCharacter, ComponentUsed)`,
  `UseTerminal_Primary` / `UseTerminal_Secondary` (interface `I_TerminalUse`), `UserTerminalStateChanged(UsingTerminal)`,
  `GetInteractText`). `ComputerTerminal_Standard_C` adds the in-world operating system: `OperatingSystemWidget` (a
  `W_Operating_System_Main` on a widget component), `Emails` (row handles into the email table, `InitEmails`), `Terminal_OS_Theme`.
  Using one zooms the camera onto the screen and drives the OS widget (`W_OsAppWrapper`, `W_OsAppIconButton`, the email widgets;
  apps implement `I_TerminalApp`: `Begin_TerminalInteract` / `End_TerminalInteract`).
- **Buttons:** `Button_Generic_C` has `ButtonName` (Text), `ButtonPressed` (multicast delegate), `Activated`, `ToggleSwitch`,
  `ButtonCooldown`, `ShouldSave`, `WorldFlagRequirements`, `LastInteractCharacter`, and `InteractWith_A`. Every interactable
  implements the Blueprint interface `I_Interactable_C` (64 classes have `InteractWith_A`).
- **Interaction path:** the player's `Request_InteractA(Object, HitComponent, HoldInteraction)` is a request to the server, which
  then calls the target's `InteractWith_A`. So an interaction lands **on the host**, with the interacting character as a parameter.
  (There is also `Request_RadialWheelSelectionInteract` / `RadialWheelInteractWith_A(..., SelectionWheelContentName)`, the game's
  radial wheels; their contents are fixed in Blueprint, so not usable for a portal list.)
- **On-screen text:** `Client_DisplayWarningMessage(FText, colour, beep)` on the interacting character (already used by the hub)
  reaches that player even on a client, because it is a client call.

Ways to build it, simplest first:

| Variant | How | Size | Risk |
|---|---|---|---|
| **B1. Cycling prompt (recommended first)** | The hub spawns one small console per open slot in the portal room (a `Button_Generic` or a terminal mesh with a button), or one console with "next slot" / "next destination" / "apply" buttons. Hook `InteractWith_A` (post-hook) on that class, ignore actors that are not ours, step the destination in a list (the GUI's destination list, shipped as a Lua table), set `ButtonName` so the look-at prompt reads e.g. `C-1: World B -> press for next`, show `Client_DisplayWarningMessage`, and re-spawn that one portal. | 1 card, Opus medium | Low: the same spawn/hook patterns the hub already uses (`AttemptTeleport` hook, `SpawnActor`). Probe: does `GetInteractText` show `ButtonName`; does a spawned `Button_Generic` work without a power parent (`ButtonAlwaysPowered`) and without saving itself (`ShouldSave = false`). |
| B2. Read-out on a real terminal | Spawn a `ComputerTerminal_Standard` in the portal room and add an email row (`AddRow` on the email table, as the hub does on `DT_Levels`) listing the current assignments, refreshed on change. Read only; pairs with B1's buttons. | +0.5 card | Medium: the email row struct and the OS widget's refresh are unknown; email reads may be saved per player (`Local_AreAllEmailsRead`). |
| B3. Full UMG list | A Lua-built widget on the player's screen (list of slots, list of destinations, mouse input, input mode switches). | 2+ cards, Opus high | High: input mode, focus, gamepad, and it must be created on the interacting player's own machine, which a host-side hook cannot do for a client. |

Multiplayer (B1):
- The hook runs on the host, so only the host's hub decides; **the host can also limit it** (only the host player, or anyone).
- Whether clients see the new portal depends on whether the hub's pads replicate when the host spawns them, and on what the client's
  own copy of the hub does. This is untested in the project and must be checked before B ships (probe card below). If clients run
  their own hub and spawn their own pads, the host's change must reach them some other way (there is no mod network channel), and
  B1 becomes host-only until that is solved.
- The prompt text (`ButtonName`) is a plain variable; whether it replicates to clients is a probe item. The on-screen message does
  reach the right player.

How changes get saved (B1): the host writes the slot change to a file with `io.open` (load-checked before replacing, the way the
lab writes `manual_exits.lua`):
- with per-save in place: `saves\<save name>.lua` (the natural home: a change made inside a save is a change to that save);
- before per-save exists: a separate `ingame.lua` override, never `config.lua` itself, so the GUI's file and the player's in-game
  choices never fight and the author's manual edits are never overwritten. The GUI shows the override and offers "clear in-game
  changes".

Theme: a Cordona Corporations console in the portal room ("Portal assignment console") fits the flavour; wording for the author to
approve.

## 3. Card-sized next steps

Ordered. All wait for CRD-012 to land where they touch `mod/PortalHub` or the GUI.

1. **CRD-0xx Probe: save identity and interactables** (Opus, medium). A separate probe mod (new folder, single keys, no Ctrl):
   log `ActiveWorldSaveName` and `GetSaveSubfolderName()` at load and on a key; spawn a `Button_Generic` in the portal room with a
   custom `ButtonName`, hook its `InteractWith_A`, log what fires and what the prompt shows; one two-player check (host and client)
   for both the name and the hook, and whether a host-spawned hub pad appears on a client. Runs on CordonaCorp / Mod Testing.
   Can run now, beside CRD-012, since it is its own mod.
2. **Per-save config, mod side** (Opus, medium; 2.0 or 1.x): the merge function, `saves\` folder, logging, mock tests. After the
   probe and CRD-012.
3. **Per-save config, GUI side** (Opus, medium): "Applies to" picker, dimmed inherited slots, override file writer, tests.
4. **In-game console B1** (Opus, medium; Opus high if the probe shows replication trouble): cycling prompt, host-only option,
   writes the override file, author approves the wording.
5. Optional later: **B2 read-out terminal** (Opus, medium) and **Main Menu entry A** (probe Opus medium, build Opus high) only if
   the author still wants them after B1.

Per-save for 1.0: not recommended; 1.0 keeps one global config. The probe (step 1) is cheap and worth doing before 2.0 planning.
