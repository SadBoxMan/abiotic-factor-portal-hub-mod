# Lighting rows

Every row of the game's lighting table (`DT_LevelFX`): the values a world can use for `LightingDay` and `LightingNight`
on its loader Blueprint (see [world-settings.md](world-settings.md)). A row sets the sun, the sky light, the fog, colour
grading, the weather particles, the ambient sound and music, and the temperature for the area that uses it.

All 153 rows were applied one by one in World D on 17 October 2026, with the dev lab's lighting browser at 07:00 in-game time.
The sun, sky and fog columns are the light values measured 2 seconds after the switch: sun = sunlight intensity, sky = sky light
intensity, fog = fog density. **#** is the row's number in the browser. The notes are what could be seen in game; rows without
a note were not described, which does not mean they have no particles.

To look at a row yourself: install the dev lab (`mod/PortalMaterialLab`), stand in the Facility or in a world with
`NoWeather` off, press NUMPAD * (next) or NUMPAD / (previous) until the banner shows the row's name, and NUMPAD . to put the
game's lighting back.

## Things to know

- **Day and night rows.** Most Facility sectors have a pair (`Labs` / `labs_night`, `office1` / `Office1_Night`). Set both
  on a world, or set `LightingDay` alone and it is used at night too.
- **Particles come with the row.** Snow, rain, ash, spores and radiation are part of the row, so a world lit with `Alps` snows.
- **`Weather_` rows** are what the game switches the Facility to during weather events. They work as world lighting too, but
  they show the weather's particles all the time.
- **`HGarden`, `HJapan` and the other home rows** have no sunlight (sun 0) and a sky light of 0.9. They look well lit in the
  game's own home worlds, most likely because those maps carry their own lights and a dynamic sky (the `HGarden` row has
  `HasDynamicSkybox` set). A basic-block world has neither, so it looks unlit with these rows. Not verified: a world would need
  its own lights to test it.
- **Very high fog** (`Salem_Swamp` 17, `Weather_BlackFog` 10) belongs to areas designed around it. Avoid these for an open world.
- **Main-menu, intro and credits rows** (`MainMenu_*`, `Intro*`, `EndCredits`, `EndGame`, `TraitSelect`) light the game's
  menus and story scenes. They work, but may carry menu music.
- **Unknown names.** `HShip` and `HTerminal` follow the home-world naming (`H` + name) but are not home worlds the author
  recognises; they may be cut or unreleased content. `Suomi` (Finnish for Finland) has its own sector icon and textures in
  the game files, so it is an area of the game.

## All rows

| # | Row | Sun | Sky | Fog | Seen in game |
|---|---|---|---|---|---|
| 1 | `Alps` | 0.50 | 0.50 | 0.03 | snow particles |
| 2 | `Anteverse` | 0.50 | 0.70 | 0.50 |  |
| 3 | `Anteverse_B` | 2.00 | 0.10 | 0.12 |  |
| 4 | `Anteverse_C` | 2.00 | 2.00 | 0.25 |  |
| 5 | `Containment` | 0.00 | 0.20 | 0.01 |  |
| 6 | `Containment_Night` | 0.00 | 0.00 | 0.00 |  |
| 7 | `CrissCave` | 1.00 | 0.90 | 0.10 |  |
| 8 | `Dam` | 0.00 | 1.00 | 0.01 | rain particles |
| 9 | `Dam_LowerChamber` | 0.00 | 0.10 | 0.02 |  |
| 10 | `dam_night` | 0.00 | 0.10 | 0.01 |  |
| 11 | `demo2` | 0.00 | 0.70 | 0.02 |  |
| 12 | `DistantShore` | 5.00 | 0.50 | 0.02 | snow-like particles (unconfirmed) |
| 13 | `EndCredits` | 0.00 | 0.90 | 0.00 |  |
| 14 | `EndGame` | 0.00 | 0.90 | 0.00 |  |
| 15 | `Farm` | 0.00 | 0.90 | 0.00 |  |
| 16 | `Flathill` | 0.00 | 1.70 | 0.60 | ash particles |
| 17 | `Flathill_Arcade` | 0.00 | 0.75 | 0.30 |  |
| 18 | `Flathill_Interior_School` | 0.00 | 0.75 | 0.30 |  |
| 19 | `Flathill_InteriorA` | 0.00 | 0.75 | 0.30 |  |
| 20 | `Flathill_Library` | 0.00 | 0.30 | 0.10 |  |
| 21 | `Fracture` | 0.00 | 0.85 | 0.00 | red and green radiation particles |
| 22 | `Fracture_NoMusic` | 0.00 | 0.85 | 0.00 |  |
| 23 | `FusionCentral` | 0.00 | 0.15 | 0.01 |  |
| 24 | `FusionLabs` | 0.00 | 1.00 | 0.02 |  |
| 25 | `FusionLabs_Night` | 0.00 | 0.08 | 0.00 |  |
| 26 | `FusionOvergrowth` | 0.00 | 0.20 | 0.05 | spore particles |
| 27 | `FusionOvergrowth_Night` | 0.00 | 0.05 | 0.01 |  |
| 28 | `FusionRadWaste` | 0.00 | 1.00 | 0.01 |  |
| 29 | `FusionRadWaste_Night` | 0.00 | 0.20 | 0.00 |  |
| 30 | `FusionWar` | 0.00 | 0.20 | 0.00 |  |
| 31 | `FusionWar_Night` | 0.00 | 0.05 | 0.00 |  |
| 32 | `HCabin` | 0.00 | 0.10 | 0.00 | snow particles |
| 33 | `HCabin_Interior` | 0.00 | 0.10 | 0.00 |  |
| 34 | `HFirewatch` | 0.00 | 0.90 | 0.00 |  |
| 35 | `HGarden` | 0.00 | 0.90 | 0.03 | looks unlit in a basic-block world (see Things to know) |
| 36 | `HJapan` | 0.00 | 0.90 | 0.00 | looks unlit in a basic-block world (see Things to know) |
| 37 | `HJapan_Interior` | 0.00 | 0.90 | 0.00 |  |
| 38 | `HJapan_Night` | 0.00 | 0.90 | 0.00 |  |
| 39 | `HShip` | 0.00 | 0.90 | 0.00 | unknown area (see Things to know) |
| 40 | `HTerminal` | 0.00 | 0.90 | 0.00 | unknown area (see Things to know) |
| 41 | `Intro` | 1.00 | 2.25 | 0.00 | the Portal Hub's default for worlds that set no lighting |
| 42 | `Intro_Elevator` | 0.00 | 0.90 | 0.00 |  |
| 43 | `Intro_Interior` | 0.00 | 0.90 | 0.00 |  |
| 44 | `Labs` | 0.00 | 0.20 | 0.01 |  |
| 45 | `labs_night` | 0.00 | 0.00 | 0.00 |  |
| 46 | `MainMenu` | 0.00 | 0.90 | 0.00 |  |
| 47 | `MainMenu_DFLab` | 0.00 | 0.15 | 0.01 |  |
| 48 | `MainMenu_Fracture` | 0.00 | 0.85 | 0.00 |  |
| 49 | `MainMenu_Hydroplant` | 0.00 | 1.00 | 0.01 |  |
| 50 | `MainMenu_Inq` | 0.00 | 0.20 | 0.01 |  |
| 51 | `MainMenu_Labs` | 0.00 | 0.20 | 0.01 |  |
| 52 | `MainMenu_MFWest` | 0.00 | 0.20 | 0.01 |  |
| 53 | `MainMenu_Offices` | 0.00 | 0.90 | 0.00 |  |
| 54 | `MainMenu_Outback` | 6.00 | 0.85 | 0.05 |  |
| 55 | `MainMenu_PowerServices` | 0.00 | 0.25 | 0.00 |  |
| 56 | `MainMenu_Residence` | 0.00 | 0.20 | 0.01 |  |
| 57 | `MainMenu_Security` | 0.00 | 0.00 | 0.00 |  |
| 58 | `MainMenu_TheWall` | 0.00 | 0.70 | 0.30 |  |
| 59 | `MainMenu_VWinter` | 1.00 | 1.50 | 0.04 |  |
| 60 | `MFFoundry` | 0.00 | 0.20 | 0.01 |  |
| 61 | `MFFoundry_Night` | 0.00 | 0.00 | 0.00 |  |
| 62 | `MFHQ` | 0.00 | 0.20 | 0.01 |  |
| 63 | `MFHQ_Night` | 0.00 | 0.00 | 0.00 |  |
| 64 | `MFMaggot` | 0.00 | 0.20 | 0.01 |  |
| 65 | `MFMaggot_Night` | 0.00 | 0.00 | 0.00 |  |
| 66 | `MFMines` | 0.00 | 0.20 | 0.01 |  |
| 67 | `MFMines_Frake` | 0.00 | 0.20 | 0.01 |  |
| 68 | `MFMines_Night` | 0.00 | 0.00 | 0.00 |  |
| 69 | `MFOldMines` | 0.00 | 0.00 | 1.00 |  |
| 70 | `MFWest` | 0.00 | 0.20 | 0.01 |  |
| 71 | `MFWest_Night` | 0.00 | 0.00 | 0.00 |  |
| 72 | `MirrorWorld` | 1.00 | 0.90 | 0.00 |  |
| 73 | `Motherboard` | 2.00 | 0.90 | 0.00 |  |
| 74 | `office1` | 0.00 | 0.10 | 0.01 |  |
| 75 | `Office1_Night` | 0.00 | 0.00 | 0.00 |  |
| 76 | `Office2` | 0.00 | 0.20 | 0.01 |  |
| 77 | `Office2_Night` | 0.00 | 0.00 | 0.00 |  |
| 78 | `Office3` | 0.00 | 0.20 | 0.01 |  |
| 79 | `Office3_Night` | 0.00 | 0.00 | 0.00 |  |
| 80 | `Parking` | 0.00 | 0.20 | 0.00 |  |
| 81 | `Parking_Night` | 0.00 | 0.00 | 0.00 |  |
| 82 | `pens` | 0.00 | 0.70 | 0.02 |  |
| 83 | `Pens_Night` | 0.00 | 0.00 | 0.00 |  |
| 84 | `Plant` | 0.00 | 0.25 | 0.00 | spore and radiation particles |
| 85 | `Plant_Night` | 0.00 | 0.01 | 0.00 |  |
| 86 | `PlantFusion` | 0.00 | 0.20 | 0.00 | blue and purple radiation particles |
| 87 | `PlantFusion_Night` | 0.00 | 0.05 | 0.00 |  |
| 88 | `Reservoir` | 0.00 | 1.00 | 0.01 | rain particles |
| 89 | `Reservoir_Night` | 0.00 | 0.10 | 0.01 |  |
| 90 | `Residence` | 0.00 | 0.20 | 0.01 | snow particles |
| 91 | `Residence_Night` | 0.00 | 0.00 | 0.00 |  |
| 92 | `Salem` | 0.20 | 0.19 | 0.04 |  |
| 93 | `Salem_Swamp` | 0.10 | 0.28 | 17.00 | right colours, but the fog (17) is too thick to see anything |
| 94 | `Security` | 0.00 | 0.00 | 0.00 |  |
| 95 | `ShadowVoid` | 0.00 | 0.30 | 0.03 | rising energy particles |
| 96 | `SouthIsland` | 0.00 | 1.25 | 0.01 |  |
| 97 | `Suomi` | 0.00 | 0.30 | 0.03 | rising energy particles |
| 98 | `Suomi_Interior` | 0.00 | 0.30 | 0.03 |  |
| 99 | `Theatre` | 0.00 | 0.10 | 0.00 |  |
| 100 | `TheWall` | 0.00 | 0.70 | 0.30 |  |
| 101 | `Train` | 3.00 | 2.00 | 0.01 |  |
| 102 | `TraitSelect` | 0.00 | 0.90 | 0.00 |  |
| 103 | `V_BOTANICAL` | 0.00 | 0.20 | 0.05 |  |
| 104 | `VArcade` | 0.00 | 1.00 | 0.01 |  |
| 105 | `VDummy` | 0.00 | 0.50 | 0.00 |  |
| 106 | `VDummy_Night` | 0.00 | 0.00 | 0.00 |  |
| 107 | `VINQ` | 0.00 | 0.20 | 0.01 |  |
| 108 | `VINQ_Hallway` | 0.00 | 0.20 | 0.01 |  |
| 109 | `VNight` | 3.00 | 10.00 | 0.02 | spore particles |
| 110 | `VRise` | 0.00 | 1.00 | 0.03 |  |
| 111 | `VSignal_Night` | 0.00 | 0.11 | 0.00 |  |
| 112 | `VSignal_Night_Basement` | 0.00 | 0.11 | 0.00 |  |
| 113 | `VSignal_Night_Interior` | 0.00 | 0.11 | 0.00 |  |
| 114 | `VSnowglobe` | 0.00 | 0.40 | 0.01 | snow particles |
| 115 | `VSnowglobe_Blizzard` | 0.00 | 0.40 | 0.40 |  |
| 116 | `VTemple` | 8.00 | 0.90 | 0.00 |  |
| 117 | `VWinter` | 1.00 | 1.50 | 0.04 | snow particles |
| 118 | `Warehouse` | 0.00 | 0.15 | 0.00 |  |
| 119 | `Warehouse_Roof` | 0.00 | 0.15 | 0.00 |  |
| 120 | `Warehouse_Underground` | 0.00 | 0.00 | 0.00 |  |
| 121 | `Weather_BlackFog` | 0.00 | 1.70 | 10.00 | leaf particles and wispy black fog |
| 122 | `Weather_ColdSnap` | 0.00 | 0.00 | 0.00 | white spore-like particles |
| 123 | `Weather_Fog` | 0.00 | 1.70 | 2.50 | dark ash particles |
| 124 | `Weather_Fog_BVT_SUBC` | 2.00 | 0.10 | 0.20 |  |
| 125 | `Weather_Fog_BVT_SUBC_Night` | 2.00 | 0.10 | 0.20 |  |
| 126 | `Weather_Fog_Night` | 0.00 | 0.00 | 4.50 |  |
| 127 | `Weather_Fog_Security` | 0.00 | 1.70 | 2.50 |  |
| 128 | `Weather_RadLeak` | 0.00 | 0.10 | 0.06 | shooting-star particles |
| 129 | `Weather_RadLeak_Dam` | 0.00 | 0.10 | 0.06 |  |
| 130 | `Weather_RadLeak_Dam_Central` | 0.00 | 0.10 | 0.06 |  |
| 131 | `Weather_RadLeak_Dam_Central_Night` | 0.00 | 0.00 | 0.20 |  |
| 132 | `Weather_RadLeak_Dam_Hydroplant` | 0.00 | 0.10 | 0.06 |  |
| 133 | `Weather_RadLeak_Dam_Hydroplant_Night` | 0.00 | 0.00 | 0.20 |  |
| 134 | `Weather_RadLeak_Dam_Night` | 0.00 | 0.00 | 0.20 |  |
| 135 | `Weather_RadLeak_Fracture` | 0.00 | 0.85 | 0.00 |  |
| 136 | `Weather_RadLeak_Night` | 0.00 | 0.00 | 0.20 |  |
| 137 | `Weather_RadLeak_Residence` | 0.00 | 0.10 | 0.06 |  |
| 138 | `Weather_RadLeak_Residence_Night` | 0.00 | 0.00 | 0.20 |  |
| 139 | `Weather_RadLeak_Security` | 0.00 | 0.10 | 0.06 |  |
| 140 | `Weather_Spore` | 0.00 | 0.10 | 0.17 |  |
| 141 | `Weather_Spore_Dam` | 0.00 | 0.10 | 0.17 |  |
| 142 | `Weather_Spore_Dam_Central` | 0.00 | 0.10 | 0.17 |  |
| 143 | `Weather_Spore_Dam_Central_Night` | 0.00 | 0.00 | 0.60 |  |
| 144 | `Weather_Spore_Dam_Hydroplant` | 0.00 | 0.10 | 0.17 |  |
| 145 | `Weather_Spore_Dam_Hydroplant_Night` | 0.00 | 0.00 | 0.60 |  |
| 146 | `Weather_Spore_Dam_Night` | 0.00 | 0.00 | 0.60 |  |
| 147 | `Weather_Spore_Fracture` | 0.00 | 0.85 | 0.00 |  |
| 148 | `Weather_Spore_FusionOvergrowth` | 0.00 | 0.20 | 0.05 |  |
| 149 | `Weather_Spore_FusionOvergrowth_Night` | 0.00 | 0.05 | 0.01 |  |
| 150 | `Weather_Spore_Night` | 0.00 | 0.00 | 0.60 |  |
| 151 | `Weather_Spore_Residence` | 0.00 | 0.10 | 0.17 |  |
| 152 | `Weather_Spore_Residence_Night` | 0.00 | 0.00 | 0.60 |  |
| 153 | `Weather_Spore_Security` | 0.00 | 0.10 | 0.30 |  |
