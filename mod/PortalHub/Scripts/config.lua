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

    portals = {
        { slot = "A-3", name = "Dunkeltaler Forest", destination = "signal_start" },

        -- Examples (remove the leading -- to enable):
        -- { slot = "A-4", name = "My World", destination = "mymod_start", design = "/Game/Particles/Niagara_Portal_Torii.Niagara_Portal_Torii" },
    },
}

