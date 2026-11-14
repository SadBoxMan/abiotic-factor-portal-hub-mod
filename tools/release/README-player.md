# Portal Hub 1.0 for Abiotic Factor

*Cordona Corporations Portal Hub*: turns the portal room in the Office Sector into a real hub. Extra portals fill the room's nine empty
slots, and each one can lead to any of the game's portal worlds. A config editor is included, so you never have to touch a file by hand.

- Made for **Abiotic Factor v1.5.0**, with **UE4SS for Abiotic Factor 1.25.0** or later.
- Works with the game's own worlds. No game files are replaced: the hub is a UE4SS Lua mod.
- Starts **blank**: only the game's own portals, until you add yours. Every portal world already has a Manual Hub Exit (section 5).
- **Optional preset packs:** ready-made portal rooms by the author, as separate downloads. Pack 4 includes a 2.0 teaser: four small
  custom worlds (World A-D). Custom worlds are unsupported in 1.0 (see section 7).

## 1. Install UE4SS first (not included)

UE4SS is someone else's tool, so it is not in this zip. Get **"UE4SS for Abiotic Factor", version 1.25.0 or later**, from its Nexus
Mods page, https://www.nexusmods.com/abioticfactor/mods/35, and follow that page's install steps. When it is right, the game folder
has `AbioticFactor\Binaries\Win64\ue4ss\` with a `Mods` folder in it. Start the game once and quit, so UE4SS sets itself up.

The game folder is usually `...\Steam\steamapps\common\AbioticFactor` (in Steam: right-click the game > Manage > Browse local files).
Below, `<game>` means that folder.

**Optional: UE4SS's own window.** It is off in a fresh UE4SS install. To switch it on, open `<game>\AbioticFactor\Binaries\Win64\ue4ss\UE4SS-settings.ini`
in Notepad and change `GuiConsoleEnabled = 0` to `GuiConsoleEnabled = 1`. Ctrl + O then opens the window. It shows the log live and has
a **Restart All Mods** button, which applies config changes without restarting the game: handy for a quick try, but restart the game
before you play on (see Known issues). The hub works without it; you then restart the game after changing the config.

## 2. Install the Portal Hub

1. Open the `PortalHub 1.0.0` folder in this zip and copy its **`AbioticFactor`** folder into `<game>`, merging it with the folder that
   is already there. This puts the hub in `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\`.
2. Open `<game>\AbioticFactor\Binaries\Win64\ue4ss\Mods\mods.txt` in Notepad and add this line **above** the `Keybinds : 1` line:

       PortalHub : 1

3. Copy `PortalHubConfig.bat`, the `PortalHubConfig` folder and the `tools` folder anywhere you like (your desktop, for example).
   Keep them side by side.
4. Start the game and load a save. A fresh config has no portals of its own: add yours in the config editor (section 3), or use a
   preset pack (section 7). The hub portals appear when the portal room loads.

**Upgrading from an earlier copy:** your `config.lua` holds your portals. Back it up, install, then put it back. `manual_exits.lua` holds
the Manual Hub Exit spots (section 5): keep yours if you recorded or edited any.

## 3. The config editor

Double-click `PortalHubConfig.bat`. The editor finds the game through Steam (or asks you for the folder) and checks the install first:
UE4SS, the hub's files and the `mods.txt` line. If something is missing it says what to do, and it won't edit anything until the hub
is installed. It only ever edits the hub's `config.lua`.

- **Slots:** click an open slot to give it a world, a look, a light colour and brightness, and an exit mode. A-1, A-2 and B-3 are the
  game's own Stone Garden, Torii and Cabin portals and are locked.
- **Hub Exits tab:** the default exit mode for every portal, and an on/off switch for each world's Manual Hub Exit.
- **Custom Worlds tab:** connect a world that comes in its own pak (advanced, see section 7).
- **Save**, then restart the game to apply it. **Restart All Mods** in the UE4SS window works for a quick try (see Known issues).

**The exe is not signed.** Windows SmartScreen may say "Windows protected your PC". Click **More info**, then **Run anyway**. To stop it
asking, right-click the downloaded zip **before extracting it** > Properties > tick **Unblock** > OK, then extract again. Some antivirus
tools flag unsigned programs made with PyInstaller. The editor's full Python source is in `tools\PortalHubConfig\`. If you have Python
with Tkinter, the `.bat` runs that source when the exe is missing.

## 4. Exit modes: where a world's own exits take you

The hub always takes you **into** a world. Each portal's exit mode says what happens when you use that world's **own** exits:

| Mode | What the world's exits do |
|---|---|
| **game** (default) | What they always do. The hub portal only takes you in. |
| **hub** | Take everyone back to this hub portal, however they came in. |
| **dynamic** | Per player: if you came in through the hub portal, you leave to it. If you came the game's way, you leave the game's way. |
| **manual** | This hub portal leads to the world's **Manual Hub Exit** (below). The world's own exits stay the game's. |

Set it per portal in the editor (or `exits = "hub"` on a portal in `config.lua`), or for every portal at once on the Hub Exits tab
(`exitMode`). **manual** is per portal only. With **manual**, the **Buffs** switch also gives you the buffs of the world's true exit at
the Manual Hub Exit. It is off by default because it makes the game much easier.

## 5. Manual Hub Exits and the Failsafe Exit

A **Manual Hub Exit (MHE)** is an extra exit portal placed inside a world that always leads back to the hub. 1.0 ships an MHE in
**every portal world** the editor offers (22 worlds), each placed by hand by the author. A world with an MHE gets that portal whether or
not a hub portal leads there:

- If a hub portal leads to that world, the MHE takes you back to it. For the game's homes, it takes you to their own portal in the hub room.
- If no hub portal leads there, the MHE takes you to the **Failsafe Exit**: an invisible landing spot on the top tier of the portal room.

Switch a world's MHE off on the editor's Hub Exits tab (`mhe = { train_start = false }` in `config.lua`). The spots are kept in
`Mods\PortalHub\Scripts\manual_exits.lua`, one line per world (`[arrival pad id] = { x, y, z, yaw }`). You may edit it; press NUMPAD 1
or restart the game to use the changes. A world set to **manual** with no MHE recorded falls back to **game**.

## 6. Keys

| Key | What it does |
|---|---|
| NUMPAD 1 | Respawns the hub portals and reads `manual_exits.lua` again. Use it if portals are missing. |
| NUMPAD 2 | Removes the hub portals until NUMPAD 1 or the next load. |

These are the hub's only keys. The game binds NUMPAD 1 and 2 only to two developer debug actions (camera shake), which are not in its
Controls list, so they don't clash with normal play.

## 7. Preset packs and the 2.0 teaser worlds (optional)

The author's preset packs are **separate optional downloads** on the mod page, one zip each. A preset is a ready-made `config.lua` that
fills the portal room. Each pack's zip has its own README with the details.

| Pack | Download | What it is |
|---|---|---|
| 1, Demo | `PortalHub-1.0.0-Pack1-Demo.zip` | The flagship sample: nine varied optional worlds, no major story spoilers, every portal leading back through its world's Manual Hub Exit |
| 2, Story | `PortalHub-1.0.0-Pack2-Story.zip` | Nine worlds from the story, in story order (Far Garden to Shadowgate); contains story spoilers |
| 3, Builder Worlds | `PortalHub-1.0.0-Pack3-Builder-Worlds.zip` | Five worlds for building: The World in the Mirror, Furniture Store, The Pool Room, Dunkeltaler Forest, Some Distant Shore |
| 4, Custom Worlds | `PortalHub-1.0.0-Pack4-Custom-Worlds.zip` | The four 2.0 teaser worlds (World A-D) on slots C-1 to C-4, with the worlds themselves included (unsupported preview) |

**To use a pack:** back up `Mods\PortalHub\Scripts\config.lua`, copy the pack's preset (in its `Presets` folder) over it, keeping the
name `config.lua`, and restart the game. You can change it in the editor afterwards like any other config.

**The 2.0 teaser worlds:** custom worlds (worlds that ship their own pak, not part of the game) are what Portal Hub 2.0 is about. The code
is already in 1.0, and four small test worlds come with Pack 4. **They are unsupported in 1.0:** expect rough edges, and please don't
report them as bugs. Pack 4's README says how to install them (twelve files in `<game>\AbioticFactor\Content\Paks\~mods\`). Install them
before you use Pack 4's preset, or its portals lead nowhere.

## 8. Multiplayer (experimental)

The hub runs on the **host**. The host's portals, exit modes and MHEs apply to everyone in the game. Joining players don't need the hub
to use the host's portals to the game's own worlds. This has been tested in two two-player sessions only, so treat it as experimental and
please report what you see.

If a joining player **also** has the hub installed, their hub notices that it is not the host and stands down ("client mode"). It
spawns no portals of its own and only sets the hum volume and portal looks on their own screen. **Custom worlds** (the teaser) need
every player to have the hub, the same world paks and the same worlds in their config, because a custom world is loaded on each
player's own machine.

## 9. Good to know

- **The hub's tracker** follows where you are, for custom worlds (lighting, title, fall rescue) and for showing the hub portals as soon
  as a save made inside a custom world has loaded. `tracker = false` in `config.lua` switches it off. Don't, unless asked: without it, a
  custom world's exit says "No Exit Found" for about 2.6 seconds after such a load, until the hub portals spawn.
- **Saves:** the hub adds its own flags to a save (a custom world's completion). Removing the hub leaves a few harmless unused names.
  Your save's own progress is not changed.
- **DLC areas:** the Temple of Stone and Torii pads can't be used as destinations. Buy the DLC to visit them the game's way.

## 10. Known issues

- **UE4SS can stop all delayed actions** in rare cases. The log says "Ref was not function" and the hub stops reacting, even to NUMPAD 1.
- **After Restart All Mods, restart the game before you play on.** Restart All Mods is fine for trying out config changes, but on
  UE4SS 1.25.0 it can leave a mod's old hooks or timers behind, and the game may crash later, even an hour on. The hub takes its own hook
  off when mods restart; other mods may not.
  Restart the game. It was seen once on UE4SS 1.25.0, two minutes after a Restart All Mods.
- **Rare crashes inside UE4SS** were seen in long test sessions while worlds were loading, with several mods installed. The hub now does
  as little as it can at those moments; whether it played a part is still being tested. If the game crashes, a crash report in
  `%LOCALAPPDATA%\AbioticFactor\Saved\Crashes\` and UE4SS's `UE4SS.log` help us find out.
- **Loading a save made inside a custom world** may put you on its arrival pad rather than where you saved.
- **Not yet tried in the game:** the **hub** exit mode, the **Buffs** switch, and the true-exit buffs of worlds other than Far Garden.
  The Botanical Wing's return trip is untested (its two pads are the game's own link between the two halves).
- **Multiplayer:** see section 8. Portal looks and light colours you set may show differently on a joining player's screen.
- **The old PowerShell editor** (`PortalHubConfig.ps1`) is retired. It knew nothing of exit modes or MHEs; use the new editor.

## 11. Removing it

Delete `Mods\PortalHub\`, its line in `mods.txt` and, if you installed them, the twelve `World?_P.*` files in `Content\Paks\~mods\`.
Delete the editor's folder. It keeps one small file in `%APPDATA%\PortalHubConfig\` (the game folder it found); delete that too if you like.

## Credits and licence

- By **SadBoxMan (LuciDin)**, made with the help of Claude Code. *Cordona Corporations* is from the author's own writing; it is flavour,
  not a real company.
- **UE4SS** by the UE4SS team, which this mod runs on. **Abiotic Factor** by Deep Field Games; this mod is not made or endorsed by them.
- The world pictures in the config editor come from the Abiotic Factor wiki and are the game developers' art, shown for recognition only.
- Everything else, meaning the mod, the config editor and the teaser worlds, is released under **CC0 1.0** (public domain; see
  `LICENSE.txt`). Take it apart, change it, reuse it. Credit is welcome but not required.

Bugs and questions: the mod's Nexus page (Posts and Bugs tabs).
