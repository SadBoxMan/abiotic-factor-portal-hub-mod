-- Portal Hub: Manual Hub Exits (MHEs), one per base-game world, and the Failsafe Exit. You may edit, add or remove the spots here.
-- Keyed by the world's arrival pad id (a hub portal's destination); each spot is { x, y, z (the floor), yaw } in world coordinates, where the
-- exit portal stands and the way it faces. A world's MHE is a portal back to the hub: to the hub portal leading to that world (exits = "manual"
-- makes that portal lead to the MHE as well), or, with no hub portal to that world, to the Failsafe Exit.
-- failsafe = { x, y, z, yaw } is where such a player arrives in the hub room (an invisible landing; z is the floor).
-- Switch a world's MHE off in config.lua (mhe = { [arrival pad id] = false }). Changes are used after NUMPAD 1 or a mods restart.
-- The spots shipped here were placed by the project's author in game (the lab's F2 saves a spot, INSERT records it here).

return {
    ["alps_start"] = { -277209, 77599, -687, 57 },    -- MHE recorded 2026-11-11 00:34
    ["anteverse_a_start"] = { 128562, 334800, 1993, 172 },    -- MHE recorded 2026-11-10 23:14
    ["anteverse_b_start"] = { 319809, 321052, 3567, 231 },    -- MHE recorded 2026-11-10 23:26
    ["anteverse_c_start"] = { 37713, -334944, 185, 203 },    -- MHE recorded 2026-11-11 00:36
    ["botanical_future_01"] = { -43917, 61199, 53802, 211 },    -- MHE recorded 2026-11-13 22:20
    ["botanical_present_01"] = { -50116, 66556, 3416, 247 },    -- MHE recorded 2026-11-11 00:51
    ["DistantShore"] = { 336753, -326008, 757, 275 },    -- MHE recorded 2026-11-13 22:23
    ["failsafe"] = { -11938, 8293, 257, 183 },    -- MHE recorded 2026-11-09 20:15
    ["fog_start"] = { 7119, 339167, 2908, 16 },    -- MHE recorded 2026-11-10 23:20
    ["INQ_Entrance"] = { 93295, 37789, -1600, 182 },    -- MHE recorded 2026-11-11 00:45
    ["island_start"] = { 154457, 37078, 134418, 354 },    -- MHE recorded 2026-11-11 00:48
    ["mirrorworld_start"] = { -333930, -335335, 54, 135 },    -- MHE recorded 2026-11-13 22:16
    ["nightrealm_start_A"] = { 29588, -237243, 5326, 289 },    -- MHE recorded 2026-11-11 00:00
    ["rise_start"] = { -150892, -326683, 1880, 89 },    -- MHE recorded 2026-11-13 22:02
    ["salem_begin"] = { 151374, 33434, 50943, 164 },    -- MHE recorded 2026-11-11 00:10
    ["shadowgate_start"] = { -335330, 213144, 665, 111 },    -- MHE recorded 2026-11-11 00:43
    ["signal_start"] = { -239942, -70810, -17205, 73 },    -- MHE recorded 2026-11-13 22:07
    ["tile_entrance"] = { 345526, -182669, -71, 273 },    -- MHE recorded 2026-11-13 22:22
    ["train_start"] = { 333394, 13460, 872, 359 },    -- MHE recorded 2026-11-09 20:12
    ["V_Snowglobe_Start"] = { 190427, 30239, 1179, 34 },    -- MHE recorded 2026-11-13 22:05
    ["VWinter_Start"] = { 131582, -90581, 58712, 334 },    -- MHE recorded 2026-11-13 22:13
    ["wall_start"] = { -335025, 331123, 11999, 338 },    -- MHE recorded 2026-11-11 00:47
    ["warehouse_start"] = { 343263, -113998, 2, 272 },    -- MHE recorded 2026-11-10 23:24
}
