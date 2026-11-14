-- Portal Hub preset: Pack 4, Custom Worlds. Made by the author, LuciDin, in the Portal Hub config editor (14 November 2026).
-- Demos the 2.0 teaser worlds: World A, B, C and D on slots C-1 to C-4 (red, blue, green and yellow). Install the teaser worlds from
-- this pack's AbioticFactor folder first (twelve files in Content\Paks\~mods), or these portals lead nowhere. Custom worlds are an
-- unsupported preview in 1.0. To use it: back up Mods\PortalHub\Scripts\config.lua, copy this file over it (keep the name
-- config.lua), and restart the game. Released under CC0 like the rest of Portal Hub.
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
        ["/Game/Particles/Niagara_Portal_Greenverse.Niagara_Portal_Greenverse"] = { "lightning1", "lightning2" },
    },

    -- Custom worlds: worlds that ship their own pak. A world is loaded by spawning its "loader" actor Blueprint, and a
    -- teleporter pad with the world's id is spawned at origin + arrive, so a hub portal can use that id as its destination.
    -- Example (remove the leading -- to use):
    --   mymod_start = { loaderAsset = "/Game/Mods/MyWorld/BP_MyWorldLoader", loaderClass = "BP_MyWorldLoader_C",
    --     level = "/Game/Mods/MyWorld/Maps/MyWorld_L0", origin = { 1000000, 1200000, 0 }, arrive = { 700, -350, 30, -27 } },
    -- loaderAsset / loaderClass: the loader actor in the pak.  level: the map it streams (used to see when it is ready).
    -- origin: where the loader is spawned (far from the Facility).  arrive: the arrival pad, relative to origin: x, y, z (floor) and yaw.
    worlds = {
        -- test worlds A-D (World Projects): basic-block copies, each its own pak (WorldA_P ... WorldD_P in ~mods)
        world_a_start = { loaderAsset = "/Game/Mods/World_A/BP_World_A_Loader", loaderClass = "BP_World_A_Loader_C",
            level = "/Game/Mods/World_A/Maps/World_A_L0", origin = { 1400000, 1300000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
        world_b_start = { loaderAsset = "/Game/Mods/World_B/BP_World_B_Loader", loaderClass = "BP_World_B_Loader_C",
            level = "/Game/Mods/World_B/Maps/World_B_L0", origin = { 1100000, 1600000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
        world_c_start = { loaderAsset = "/Game/Mods/World_C/BP_World_C_Loader", loaderClass = "BP_World_C_Loader_C",
            level = "/Game/Mods/World_C/Maps/World_C_L0", origin = { 1400000, 1600000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
        world_d_start = { loaderAsset = "/Game/Mods/World_D/BP_World_D_Loader", loaderClass = "BP_World_D_Loader_C",
            level = "/Game/Mods/World_D/Maps/World_D_L0", origin = { 1100000, 1000000, 0 }, arrive = { 0, 0, 0, 0 }, killZ = -3000 },
    },

    portals = {
        { slot = "C-1", name = "world_a_start", destination = "world_a_start", design = "/Game/Particles/Niagara_Portal_Friendly_Red.Niagara_Portal_Friendly_Red", lightColor = { 1, 0.125, 0.125 } },
        { slot = "C-2", name = "world_b_start", destination = "world_b_start", design = "/Game/Particles/Niagara_Portal_Friendly_Blue.Niagara_Portal_Friendly_Blue", lightColor = { 0.165, 0.42, 1 } },
        { slot = "C-3", name = "world_c_start", destination = "world_c_start", design = "/Game/Particles/Niagara_Portal_Friendly_Green.Niagara_Portal_Friendly_Green", lightColor = { 0.18, 0.902, 0.361 } },
        { slot = "C-4", name = "world_d_start", destination = "world_d_start", design = "/Game/Particles/Niagara_Portal_Friendly_Yellow.Niagara_Portal_Friendly_Yellow", lightColor = { 1, 0.91, 0.102 } },
    },
}
