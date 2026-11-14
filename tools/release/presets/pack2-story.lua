-- Portal Hub preset: Pack 2, Story. Made by the author, LuciDin, in the Portal Hub config editor (13 November 2026).
-- Nine worlds from the story, in story order: Far Garden, Flathill, The Train, Furniture Store, The Mycofields, Canaan, Voussoir,
-- Village Den da'ko Yeer and Shadowgate (contains story spoilers). Every portal is in exit mode "manual": it leads to the world's
-- Manual Hub Exit, which always leads back. To use it: back up Mods\PortalHub\Scripts\config.lua, copy this file over it (keep the
-- name config.lua), and restart the game. Released under CC0 like the rest of Portal Hub.
-- Portal Hub configuration. Edit this file, then restart the game to apply. "Restart All Mods" in the UE4SS window works for a
-- quick try, but restart the game before you play on (README, Known issues).
--
-- Each entry in `portals` puts one portal into one of the open slots of the Homeworld portal room.
--   slot         Which container: "A-3", "B-1", ... Open slots: A-3 A-4 B-1 B-2 B-4 C-1 C-2 C-3 C-4.
--                (A-1, A-2 and B-3 are the game's own Stone Garden, Torii and Cabin portals.)
--   destination  The ID (MyTeleporterID) of the ARRIVAL pad in the world you are connecting. The portal sends players
--                to that pad, and the pad's exit point puts them down in front of it.
--   name         Optional label, used in log messages.
--   design       Optional Niagara particle system for the portal's look, e.g.
--                "/Game/Particles/Niagara_Portal_Torii.Niagara_Portal_Torii". Default is the plain game portal.
--   lightColor   Optional colour of the pad's own light, { r, g, b } with each value 0 to 1, e.g. { 0.2, 0.9, 0.4 } for green.
--                It tints the surroundings and works with every look. (The editor offers rainbow presets and a colour picker.)
--   lightBrightness  Optional multiplier for that light's brightness (1 = the game's normal brightness, 2 = twice as bright).
--
-- The two DLC areas (Temple of Stone and Torii: H_Garden_Start, H_Garden_Entrance, H_Japan_Start, H_Japan_Entrance) cannot be used
-- as destinations; entries that name them are skipped.
--
-- The way back is handled for you: when someone uses a hub portal, the arrival pad is pointed back at that portal, so
-- players always return to the portal they came through (even if the world also has a different original entrance).

return {
    -- Hub portal volume (the looping hum of the portals in the portal room):
    --   "dynamic"  unchanged with the game's 3 base portals, then an equal step down per added portal, reaching
    --              humFloor when every open slot is filled.
    --   "manual"   every hub portal uses humManual.
    --   "default"  leave the game's volume alone.
    humMode = "dynamic",
    humFloor = 0.1,    -- dynamic: lowest volume, 0 to 1
    humManual = 0.15,    -- manual: volume, 0 to 1

    -- Parts of a portal effect to switch off, by look. Example: hide the "Swirl" part (the accretion disk) of the SnowFlurry look:
    --   ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "Swirl" },
    -- SnowFlurry parts: Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02, Swirl.  The portal part of a look can never be switched off.
    hideEmitters = {
        ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "smoke", "snowflakes", "SnowParticle01", "SnowParticle02", "Swirl" },
        ["/Game/Particles/Niagara_Portal_Dark.Niagara_Portal_Dark"] = { "lightning1", "lightning2" },
        ["/Game/Particles/Niagara_Portal_Fog.Niagara_Portal_Fog"] = { "lightning1", "lightning2" },
        ["/Game/Particles/Niagara_Portal_Friendly_Green.Niagara_Portal_Friendly_Green"] = { "sparks" },
        ["/Game/Particles/Niagara_Portal_Rift.Niagara_Portal_Rift"] = { "smoke", "sparks" },
        ["/Game/Particles/Niagara_Portal_Botanical_Green.Niagara_Portal_Botanical_Green"] = { "Ivy" },
        ["/Game/Particles/Niagara_Portal_Door.Niagara_Portal_Door"] = { "sparks" },
        ["/Game/Particles/Niagara_Portal_Friendly_Black.Niagara_Portal_Friendly_Black"] = { "sparks" },
        ["/Game/Particles/Niagara_Portal_Friendly_Orange.Niagara_Portal_Friendly_Orange"] = { "sparks" },
        ["/Game/Particles/Niagara_Portal_Shadowgate2.Niagara_Portal_Shadowgate2"] = { "sparks" },
    },

    -- Custom worlds: worlds that ship their own pak. A world is loaded by spawning its "loader" actor Blueprint, and a
    -- teleporter pad with the world's id is spawned at origin + arrive, so a hub portal can use that id as its destination.
    -- Example (remove the leading -- to use):
    --   mymod_start = { loaderAsset = "/Game/Mods/MyWorld/BP_MyWorldLoader", loaderClass = "BP_MyWorldLoader_C",
    --     level = "/Game/Mods/MyWorld/Maps/MyWorld_L0", origin = { 1000000, 1200000, 0 }, arrive = { 700, -350, 30, -27 } },
    -- loaderAsset / loaderClass: the loader actor in the pak.  level: the map it streams (used to see when it is ready).
    -- origin: where the loader is spawned (far from the Facility).  arrive: the arrival pad, relative to origin: x, y, z (floor) and yaw.
    worlds = {
    },

    portals = {
        { slot = "A-3", name = "Far Garden", destination = "anteverse_a_start", design = "/Game/Particles/Niagara_Portal_Blueverse.Niagara_Portal_Blueverse", lightColor = { 0.627, 0.188, 1 }, exits = "manual" },
        { slot = "A-4", name = "Flathill", destination = "fog_start", design = "/Game/Particles/Niagara_Portal_Fog.Niagara_Portal_Fog", lightColor = { 0.918, 0.918, 0.918 }, exits = "manual" },
        { slot = "B-1", name = "The Train", destination = "train_start", design = "/Game/Particles/Niagara_Portal_Friendly_Black.Niagara_Portal_Friendly_Black", lightColor = { 0.627, 0.627, 0.627 }, exits = "manual" },
        { slot = "B-2", name = "Furniture Store", destination = "warehouse_start", design = "/Game/Particles/Niagara_Portal_Door.Niagara_Portal_Door", lightColor = { 1, 0.125, 0.125 }, exits = "manual" },
        { slot = "B-4", name = "The Mycofields", destination = "anteverse_b_start", design = "/Game/Particles/Niagara_Portal_Friendly_Orange.Niagara_Portal_Friendly_Orange", lightColor = { 1, 0.541, 0.102 }, exits = "manual" },
        { slot = "C-1", name = "Canaan", destination = "salem_begin", design = "/Game/Particles/Niagara_Portal_Salem.Niagara_Portal_Salem", lightColor = { 0.91, 0.639, 0.075 }, exits = "manual" },
        { slot = "C-2", name = "Voussoir", destination = "alps_start", design = "/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry", lightColor = { 0, 1, 1 }, exits = "manual" },
        { slot = "C-3", name = "Village Den da'ko Yeer", destination = "anteverse_c_start", design = "/Game/Particles/Niagara_Portal_Blueverse.Niagara_Portal_Blueverse", exits = "manual" },
        { slot = "C-4", name = "Shadowgate", destination = "shadowgate_start", design = "/Game/Particles/Niagara_Portal_Shadowgate2.Niagara_Portal_Shadowgate2", lightColor = { 0.294, 0.165, 0.71 }, exits = "manual" },
    },
}
