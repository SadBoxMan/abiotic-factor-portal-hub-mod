-- Portal Hub: Manual Hub Exits (MHEs), one per base-game world, and the Failsafe Exit. You may edit, add or remove the spots here.
-- Keyed by the world's arrival pad id (a hub portal's destination); each spot is { x, y, z (the floor), yaw } in world coordinates, where the
-- exit portal stands and the way it faces. A world's MHE is a portal back to the hub: to the hub portal leading to that world (exits = "manual"
-- makes that portal lead to the MHE as well), or, with no hub portal to that world, to the Failsafe Exit.
-- failsafe = { x, y, z, yaw } is where such a player arrives in the hub room (an invisible landing; z is the floor).
-- Switch a world's MHE off in config.lua (mhe = { [arrival pad id] = false }). Changes are used after NUMPAD 1 or a mods restart.
-- The spots shipped here were placed by the project's author in game (the lab's F2 saves a spot, INSERT records it here).

return {
    ["anteverse_a_start"] = { 127627, 335370, 1930, 302 },    -- MHE recorded 2026-11-09 20:08
    ["failsafe"] = { -11938, 8293, 257, 183 },    -- MHE recorded 2026-11-09 20:15
    ["train_start"] = { 333394, 13460, 872, 359 },    -- MHE recorded 2026-11-09 20:12
}
