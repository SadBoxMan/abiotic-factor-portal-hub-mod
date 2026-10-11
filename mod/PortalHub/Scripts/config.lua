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
--   scale        Optional size of the portal effect (1.0 = normal, 0.8 = smaller). See designScales below to size every portal that uses a look.
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
    humFloor = 0.15,    -- dynamic: lowest volume, 0 to 1
    humManual = 0.5,    -- manual: volume, 0 to 1

    -- Portal size for testing (1.0 = normal). Only the portal effect is resized; the walk-through trigger and exit point stay put.
    -- designScales gives every portal that uses a look the same size; a portal's own  scale = 0.8  (in portals below) overrides it.
    designScales = {
        ["/Game/Particles/Niagara_Portal_Door.Niagara_Portal_Door"] = 1.0,
        ["/Game/Particles/Niagara_Portal_NightRDoor_2.Niagara_Portal_NightRDoor_2"] = 1.0,
        ["/Game/Particles/Niagara_Portal_Salem.Niagara_Portal_Salem"] = 1.0,
        ["/Game/Particles/Niagara_Portal_Shadowgate2.Niagara_Portal_Shadowgate2"] = 1.0,
        ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = 1.0,
    },

    -- Parts of a portal effect to switch off, by look. Example: hide the "Blackhole" part of the SnowFlurry look:
    --   ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "Blackhole" },
    -- SnowFlurry parts: Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02, Swirl.
    hideEmitters = {
    },

    portals = {
        { slot = "A-3", name = "Dunkeltaler Forest", destination = "signal_start" },
    },
}
