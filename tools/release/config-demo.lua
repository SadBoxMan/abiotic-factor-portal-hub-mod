-- Portal Hub demo preset (PROVISIONAL, CRD-015): replaced by the author's own preset before release. The four 2.0 teaser worlds on
-- C-1 to C-4 (install their paks from "Optional - 2.0 teaser worlds" first). Copy this over Mods\PortalHub\Scripts\config.lua to use it.
-- Portal Hub configuration. Edit this file, then restart mods (UE4SS GUI: "Restart All Mods") to apply.
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
--   exits        Optional: what the world's own exits do for players of this portal (overrides exitMode below):
--                  "game" (1)     the world's exits are the game's: the portal only takes players in
--                  "hub" (2)      the world's exits take everyone to this portal, however they came in
--                  "dynamic" (3)  someone who came in through this portal leaves to it; someone who came the game's way leaves the game's way
--                  "manual" (4)   this portal leads to the world's Manual Hub Exit (MHE, see manual_exits.lua), a portal placed in the world
--                                 that always leads back here; the world's own exits stay the game's
--   manualBuffs  Optional, with exits = "manual": true also gives the buffs of the world's true exit at the MHE. Off by default: it makes
--                the game much easier.
--
-- The two DLC areas (Temple of Stone and Torii: H_Garden_Start, H_Garden_Entrance, H_Japan_Start, H_Japan_Entrance) cannot be used
-- as destinations; entries that name them are skipped.
--
-- Custom worlds (below) always lead back to the portal they were entered by, through their arrival pad; exits does not apply to them.
-- Base-game worlds: see exits above and exitMode below.

return {
    -- Hub portal volume (the looping hum of the portals in the portal room):
    --   "dynamic"  unchanged with the game's 3 base portals, then an equal step down per added portal, reaching
    --              humFloor when every open slot is filled.
    --   "manual"   every hub portal uses humManual.
    --   "default"  leave the game's volume alone.
    humMode = "dynamic",
    humFloor = 0.15,    -- dynamic: lowest volume, 0 to 1
    humManual = 0.5,    -- manual: volume, 0 to 1

    -- What base-game worlds' own exits do, for every portal at once: "game" (default), "hub" or "dynamic" (see exits above).
    -- A portal's own exits wins; "manual" can only be chosen per portal.
    -- exitMode = "game",

    -- Manual Hub Exits (MHEs, manual_exits.lua): every world with an MHE also gets that exit portal on its own, leading to the first portal
    -- to that world here (for the game's homes, their own hub-room portal), or, if there is none, to the hub room (the Failsafe Exit).
    -- To switch a world's MHE off, name its arrival pad here, e.g. mhe = { train_start = false },
    -- mhe = {},

    -- Multiplayer: when you join someone else's game, your hub stands down and the host's portals, exits and worlds apply to you ("client
    -- mode"). Only your hum volume above is used on your machine (and your look, on a host portal that leads where yours in that slot does).
    -- Custom worlds are loaded on your machine too (the host's never reach you), so list the same worlds as the host, with their paks
    -- installed: a world loads when the host's portal takes you there, or ahead of time where the host has a portal in a slot that you
    -- give that world here.
    -- clientMode = false switches this off, for testing only: your hub then also spawns its own portals beside the host's.
    -- clientMode = true,

    -- Parts of a portal effect to switch off, by look. Example: hide the "Swirl" part (the accretion disk) of the SnowFlurry look:
    --   ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "Swirl" },
    -- SnowFlurry parts: Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02, Swirl.  The portal part of a look can never be switched off.
    hideEmitters = {
    },

    -- Custom worlds: worlds that ship their own pak. A world is loaded by spawning its "loader" actor Blueprint, and a
    -- teleporter pad with the world's id is spawned at origin + arrive, so a hub portal can use that id as its destination.
    -- Example (remove the leading -- to use):
    --   mymod_start = { loaderAsset = "/Game/Mods/MyWorld/BP_MyWorldLoader", loaderClass = "BP_MyWorldLoader_C",
    --     level = "/Game/Mods/MyWorld/Maps/MyWorld_L0", origin = { 1000000, 1200000, 0 }, arrive = { 700, -350, 30, -27 } },
    -- loaderAsset / loaderClass: the loader actor in the pak.  level: the map it streams (used to see when it is ready).
    -- origin: where the loader is spawned (far from the Facility).  arrive: the arrival pad, relative to origin: x, y, z (floor) and yaw.
    -- The world's own settings (title, home or vignette, arrival and exit spots, lighting rows, ...) are best set by its map maker on the
    -- loader Blueprint, which wins over this file; see docs/world-settings.md. arrive may then be left out.
    worlds = {
        -- the four beta test worlds (WorldA_P ... WorldD_P in Content\Paks\~mods)
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
        { slot = "C-1", name = "World A", destination = "world_a_start" },
        { slot = "C-2", name = "World B", destination = "world_b_start" },
        { slot = "C-3", name = "World C", destination = "world_c_start" },
        { slot = "C-4", name = "World D", destination = "world_d_start" },
    },
}
