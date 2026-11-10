# Test world projects (World_A to World_D)

Copies of the Test World, each with its own names so the hub and the game can tell them apart.
World_A was made from `TestWorld\AbioticFactor` on 14 October 2026 and its map redone with basic blocks only; World_B to World_D were remade from World_A on 15 October 2026. The assets were renamed in the editor (headless), so every reference follows: each map depends only on its own folder.

| World | Project | Content folder | Loader | Map | Chunk ID | World id (hub) |
|---|---|---|---|---|---|---|
| A | `World A\World_A\AbioticFactor.uproject` | `/Game/Mods/World_A` | `BP_World_A_Loader` | `Maps/World_A_L0` | 91 | `world_a_start` |
| B | `World B\World_B\AbioticFactor.uproject` | `/Game/Mods/World_B` | `BP_World_B_Loader` | `Maps/World_B_L0` | 92 | `world_b_start` |
| C | `World C\World_C\AbioticFactor.uproject` | `/Game/Mods/World_C` | `BP_World_C_Loader` | `Maps/World_C_L0` | 93 | `world_c_start` |
| D | `World D\World_D\AbioticFactor.uproject` | `/Game/Mods/World_D` | `BP_World_D_Loader` | `Maps/World_D_L0` | 94 | `world_d_start` |

Each project's `Config` already points at its own map and folder (default map, maps to cook, always-cook directory),
and its Primary Asset Label carries its own chunk ID. The content is the same as the Test World; change anything you
like in the map so you can tell the worlds apart in game.

## What is in the repo

Each project's own files only: `AbioticFactor.uproject`, `Config\Default*.ini`, `Content\Mods\World_X\` and `Scripts\`.
Open a project by double-clicking its `AbioticFactor.uproject` (Unreal Engine 5.4); the editor rebuilds `Intermediate`,
`Saved` and `DerivedDataCache` on first open. The built worlds, ready to install, are in `Builds\` (`WorldA_P` to
`WorldD_P`, each a `.pak/.ucas/.utoc` set, copied as installed in the game's `Content\Paks\~mods\`). Generated folders and
`Packaged\` (engine binaries) are not committed. The Test World is not in the repo yet. These are test worlds: they will
change during the custom-world work, so repackage and copy the new chunk files into `Builds\` when one is updated. Inventory
and checks: `findings/world-upload-inventory.md`.

## Packaging each one

Same as the Test World: package, then take only `pakchunk91-Windows.pak/.ucas/.utoc` (92, 93, 94 for B, C, D) from
`Windows\AbioticFactor\Content\Paks\`, rename the three together (for example `World_A_P.pak/.ucas/.utoc`) and put them
where the Test World's `Test_P` files are (`Content\Paks\~mods\`). Never install `pakchunk0-*` or `global.*`.

## Hub config

Add these to `worlds` and `portals` in the hub's `config.lua` once the paks are installed. Each world has its own
`origin`, 300,000 units from the Test World and from each other.

```lua
world_a_start = { loaderAsset = "/Game/Mods/World_A/BP_World_A_Loader", loaderClass = "BP_World_A_Loader_C",
    level = "/Game/Mods/World_A/Maps/World_A_L0", origin = { 1400000, 1300000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
world_b_start = { loaderAsset = "/Game/Mods/World_B/BP_World_B_Loader", loaderClass = "BP_World_B_Loader_C",
    level = "/Game/Mods/World_B/Maps/World_B_L0", origin = { 1100000, 1600000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
world_c_start = { loaderAsset = "/Game/Mods/World_C/BP_World_C_Loader", loaderClass = "BP_World_C_Loader_C",
    level = "/Game/Mods/World_C/Maps/World_C_L0", origin = { 1400000, 1600000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
world_d_start = { loaderAsset = "/Game/Mods/World_D/BP_World_D_Loader", loaderClass = "BP_World_D_Loader_C",
    level = "/Game/Mods/World_D/Maps/World_D_L0", origin = { 1100000, 1000000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
```

```lua
{ slot = "C-1", name = "World A", destination = "world_a_start" },
{ slot = "C-2", name = "World B", destination = "world_b_start" },
{ slot = "C-3", name = "World C", destination = "world_c_start" },
{ slot = "C-4", name = "World D", destination = "world_d_start" },
```

## Renaming by hand (for a future copy)

In the editor's Content Browser: right-click the world's folder under `Mods` > **Rename**, then rename the loader
Blueprint, the map and the Primary Asset Label the same way (right-click > **Rename**). Afterwards right-click the
`Content` folder > **Update Redirector References** (called *Fix Up Redirectors* in older versions), and open the
label to set a new **Chunk ID**. Finally edit `Config\DefaultEngine.ini` (`GameDefaultMap`, `EditorStartupMap`)
and `Config\DefaultGame.ini` (`+MapsToCook`, `+DirectoriesToAlwaysCook`) to the new paths. Renaming in the editor,
not in Windows Explorer, is what keeps the loader pointing at its map.

## The world's title (set in the world, not the hub)

The banner shown on entry comes from the world itself: open the loader Blueprint (`BP_World_B_Loader`), click
**+** next to **Variables**, name it `WorldTitle`, set its type to **Text**, click **Compile**, then type the title
under **Default Value** in the Details panel and **Save**. The hub reads it; if it is missing, it falls back to a
`title` in `config.lua`, then to the portal's name. Suggested test: give B and D a title, leave A and C without one.

## All world settings

The title is one of several variables a loader Blueprint can carry (world type, no-weather status, lighting rows,
arrival and exit spots, safety floor, radius). They are all added the same way; the full list with types and defaults
is in `docs/world-settings.md`. A value on the Blueprint wins over the same setting in `config.lua`.

## Leyak safety zone (also set in the world)

Most of the game's worlds keep the Leyak away with a Leyak safety zone, so custom worlds get one by default. To switch it
off, add a **Boolean** variable `LeyakSafeZone` to the loader Blueprint, compile, leave its default value unticked, and
save. (`leyakSafe = false` in the hub's `config.lua` does the same from the hub side.)