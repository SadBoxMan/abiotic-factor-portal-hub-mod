# Portal Hub 1.0 preset packs

Optional extras for **Portal Hub 1.0** for Abiotic Factor. Each pack is a ready-made portal room: a `config.lua` made by the author in the
Portal Hub config editor. You need Portal Hub itself first (the main download, with UE4SS for Abiotic Factor 1.25.0 or later); a pack
does nothing on its own.

| Pack | Preset file | What it is |
|---|---|---|
| 1, Demo | `Presets\pack1-demo.lua` | The flagship sample: nine varied optional worlds (Dunkeltaler Forest, Flathill, Royal Range, Rise, The World in the Mirror, Furniture Store, The Pool Room, Some Distant Shore, The Train), no major story spoilers. Every portal leads back through its world's Manual Hub Exit |
| 2, Story | `Presets\pack2-story.lua` | Nine worlds from the story, in story order: Far Garden, Flathill, The Train, Furniture Store, The Mycofields, Canaan, Voussoir, Village Den da'ko Yeer, Shadowgate. Contains story spoilers |
| 3, Builder Worlds | `Presets\pack3-builder-worlds.lua` | Five worlds for building: The World in the Mirror, Furniture Store, The Pool Room, Dunkeltaler Forest, Some Distant Shore (four slots left empty) |
| 4, Custom Worlds | `Presets\pack4-custom-worlds.lua` | Demos the 2.0 teaser worlds (World A-D), which come with it |

This zip holds one of them; its `Presets` folder shows which. The others are separate downloads on the mod page.

## Use a preset

1. Back up your own `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\Scripts\config.lua` (copy it somewhere safe).
2. Copy the pack's preset from its `Presets` folder into that `Scripts` folder and rename it to `config.lua`, replacing the old one.
3. Start the game (or restart it) and load a save. The pack's portals appear when the portal room loads.

You can open the preset in the config editor afterwards and change it like any other config. To go back, put your backup in place again.

## Pack 4 only: install the teaser worlds first

Pack 4's zip also has an `AbioticFactor` folder with the four teaser worlds. Copy it into `<game>` (the folder that holds `AbioticFactor`),
merging it with the folder that is already there. This puts twelve files (`WorldA_P.pak/.ucas/.utoc` ... `WorldD_P.*`) in
`<game>\AbioticFactor\Content\Paks\~mods\`. Do this before you use Pack 4's preset, or its custom-world portals lead nowhere.

Custom worlds are what Portal Hub 2.0 is about. **In 1.0 they are an unsupported preview:** expect rough edges, and please don't report
them as bugs. In multiplayer, every player needs the hub, these paks and the same preset. To remove them, delete those twelve files.

## Credits and licence

The presets were made by the project's author, LuciDin. Portal Hub, its presets and the teaser worlds are released under **CC0 1.0**
(public domain; see `LICENSE.txt`). Abiotic Factor is by Deep Field Games; this is a fan mod and is not affiliated with them.
