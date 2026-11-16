-- Portal Hub: saved portal designs. Made in the config editor's PORTAL DESIGNER tab (PortalHubConfig.bat); you may edit them here too.
-- A portal in config.lua uses one by its name:  design = "Cordona Arch".  A design value starting with / is one of the game's own looks.
-- Every field is optional:
--   look      the pad's own look: one of the game's looks (Niagara_Portal, Niagara_Portal_Friendly_Red, ...) or "none" (hidden: needs a ring)
--   ring      a ring drawn on the pad: one of the 24 Geo rings "<Shape>_<Type>" (Arch, Gothic, Square, Door, Round, Oval x Con, Col,
--             Ren, Pri; they need the PortalHubLooks_P pak) or a game ring material (M_Portal_Garden, M_Portal_Friendly_White, ...)
--   size      the ring's width and height in metres          tint    the ring's colour, red, green, blue from 0 to 1
--   scene     the picture inside the ring (TC_Portal_Alps, TC_Portal_Warehouse, TC_H_Cabin, ...)
--   scale     the look's own size X, Y, Z (only the Friendly looks change size)
--   height    how high the look and the ring sit above the pad, in cm (default: that look's usual height)
--   mheHeight the height on the portal's Manual Hub Exit, if it should differ      hide    parts of the look to switch off
-- Restart the game to apply (or NUMPAD 1 in the portal room, for designs already named in config.lua).

return {
    ["Cordona Arch"] = {
        look = "none",
        ring = "Arch_Col",
        size = { 1.0, 2.0 },
        tint = { 0.71, 0.51, 1.0 },
        height = 128,
    },
    ["Big Friendly Red"] = {
        look = "Niagara_Portal_Friendly_Red",
        scale = { 1.3, 1.3, 1.3 },
        height = 125,
    },
    ["Mall Door"] = {
        look = "none",
        ring = "Door_Pri",
        size = { 1.75, 3.0 },
        scene = "TC_Portal_Warehouse",
        height = 178,
    },
}
