# World settings for map makers

A world describes itself. Everything about how your world behaves in the Portal Hub (its title, whether it is a home or a
vignette, where players arrive, how far they may fall) is set as a variable on your world's **loader Blueprint**, so it
ships inside your pak. The hub only needs to know which portal slot the world goes in and where it sits in hub space
(`origin`); players set those in the hub's config editor.

Every variable is optional. Leave one out and the hub uses the value from its `config.lua`, or else the default below.
When both are given, **the Blueprint wins**.

## The variables

Names must be spelt exactly as below (capital letters included). Only plain value types are used: never add a variable
that holds an asset, class or soft reference, because the hub cannot read those safely.

| Variable | Type | What it does | When it is missing |
|---|---|---|---|
| `WorldTitle` | Text | The name the game shows as a banner when a player enters the world. Only shown while `NoWeather` is on: the banner comes with the game's own level status. | `title` in `config.lua`, else the portal's name. |
| `WorldType` | Name | `Home` or `Vignette` (capitals do not matter). A **Vignette** gives players portal sickness (equipment locked) until they leave through the world's proper exit (see `ExitSpot`); after that it never comes back for that save. A **Home** has no sickness. | `Home` |
| `NoWeather` | Boolean | Ticked: the game treats your world as one of its own worlds: the Facility's weather (fog, particles) stays out, your lighting rows are used, and the respawn menu's *Portal Entrance* leads to your arrival pad. Unticked: the Facility's weather and lighting follow the player in. A `Vignette` needs this ticked. | On |
| `LeyakSafeZone` | Boolean | Ticked: the Leyak cannot follow players into your world (most of the game's worlds do this). Unticked: it can, **if your map has a nav mesh** (see below). | On |
| `LightingDay` | Name | The row of the game's lighting table (`DT_LevelFX`) that lights your world by day, for example `HGarden` (Temple of Stone's look). All 153 rows, with their light values and particles, are listed in [lighting-rows.md](lighting-rows.md). An unknown name falls back to the default and is reported in the log. Only used while `NoWeather` is on. | `Intro` (the game's intro lighting: bright sun and sky, no fog), so a world is always lit; the log says no lighting is set. |
| `LightingNight` | Name | The same for night. | `LightingDay` |
| `ArriveSpot` | Vector | Where the arrival pad stands, in your map's own coordinates (the map's 0, 0, 0 is the world's origin). Z is the floor under the pad. Players step out 215 units in front of the pad and 127 up, so keep that space clear. | `arrive` in `config.lua`, else 0, 0, 0 |
| `ArriveYaw` | Float | Which way the arrival pad faces, in degrees (0 = +X, 90 = +Y). | `arrive` in `config.lua`, else 0 |
| `ExitSpot` | Vector | Vignettes only: where the proper exit pad stands (map coordinates, Z = floor). Using it sends players back to the hub and lifts the portal sickness for good. A vignette without an exit is reported in the log and cannot be completed. | `exit` in `config.lua`, else no exit |
| `ExitYaw` | Float | Which way the exit pad faces, in degrees. | 0 |
| `KillZ` | Float | A safety floor: a player who falls below this height (map coordinates) is put back on the arrival pad. Use a value well below your lowest floor, for example `-3000`. **0 switches it off.** | `killZ` in `config.lua`, else off |
| `Radius` | Float | How far sideways from the world's origin counts as being inside your world (in units; 100 units = 1 m). It also sets the size of the no-weather and Leyak zones. Make it cover your whole map, and keep it well under the distance to the next world. Values of 0 or less are ignored. | 100000 (1 km) |

The hub reads the variables once, when the world is loaded, and writes one line to `UE4SS.log` listing what it found,
for example:

```
[PortalHub] worlds: world_b_start settings from its loader Blueprint: WorldTitle='Spell ICUP', KillZ=-3000.0
```

If a variable you added is not in that line, check its spelling and type, and that you compiled and saved.

### The Leyak and other NPCs need a nav mesh

The game places the Leyak by searching for walkable ground near the player, and its NPCs walk on the same data: the map's
**navigation mesh**. A map without one is never visited by the Leyak, whatever `LeyakSafeZone` says, and NPCs cannot move in it.
To add one: **Place Actors** (the **+** cube in the toolbar) > **Volumes** > **Nav Mesh Bounds Volume**, drag it into the map,
scale it to cover every floor (a little above and below), press **P** in the viewport to see the walkable area in green, then
**Build** > **Build Paths** and **Save**. Confirmed on 17 October 2026: the Leyak came into World D only after it got a nav mesh.

### What stays in the hub's config

| Setting | Why |
|---|---|
| `loaderAsset`, `loaderClass`, `level` | The hub needs them to find your loader in the first place. The config editor fills them in. |
| `origin` | Where your world sits in hub space. It must not overlap other worlds, which only the hub can know. |
| The portal (`slot`, `name`, look, light colour) | That is the player's choice of how the portal room looks. |
| `lighting = { sun, sunColor, sunPitch, sky, fog }` | Fine-tuning on top of the lighting rows. It stays in `config.lua` for now; custom lighting is the next roadmap step and will decide how worlds set it. |

## Adding a variable, step by step

The example adds a title; every variable works the same way, only the name, type and value change.

1. In the Content Browser, double-click your loader Blueprint (for World B: `Mods > World_B > BP_World_B_Loader`).
2. In the **My Blueprint** panel on the left, click **+** next to **Variables**.
3. Type the name, `WorldTitle`, and press Enter.
4. In the **Details** panel on the right, open the **Variable Type** drop-down and pick the type from the table
   (**Text**). Leave it a single value (not an array, set or map).
5. Click **Compile** in the toolbar. The **Default Value** box appears at the bottom of the Details panel.
6. Type the value under **Default Value**: the title text; tick or untick the box for a Boolean; type a number for a
   Float; type the three numbers X, Y, Z for a Vector.
7. Click **Save**, then package the world again and install the new pak (see `docs/test-world-walkthrough.md`).

Tips:

- For a **Name** variable (`WorldType`, `LightingDay`, `LightingNight`) type the value without quotes: `Vignette`.
- For a **Boolean** that should be *off* (`NoWeather`, `LeyakSafeZone`), add the variable and leave its default
  unticked. A missing Boolean counts as on; an added, unticked one counts as off.
- To find a spot for `ArriveSpot` or `ExitSpot`, place any actor (a cube will do) where the pad should stand, read its
  **Location** in the Details panel, type those numbers into the variable, then delete the cube.

## Not built yet: marker actors instead of typed spots

Typing coordinates is error-prone. A friendlier way, proposed for the custom-exit step of the roadmap: the map maker
places an ordinary **Target Point** actor in the map where the pad should stand, rotates it the way the pad should face,
and gives it an **Actor Tag** (Details panel > Actor > Tags) of `PortalHubArrive` or `PortalHubExit`. When the world
has loaded, the hub would look for Target Points with those tags near the world's origin and use their location and
rotation, ahead of `ArriveSpot` / `ExitSpot`. Tags are plain names and Target Point is an engine class, so the world
would not need any asset from the hub. Not built: say if you want it.
