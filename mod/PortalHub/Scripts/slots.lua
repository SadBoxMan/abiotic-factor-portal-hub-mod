-- Portal Hub slot table: the 12 portal containers in the Homeworld portal room.
-- Slots are named <tier><number>. Tiers A/B/C are the three levels of containers, numbers 1-4 run around the room
-- counter-clockwise starting from the Stone Garden position. Slots A-1, A-2 and B-3 hold the game's own portals
-- (Stone Garden, Torii, Cabin) and cannot be used. See data/portal_slots.json for how these positions were found.
--
-- Pad placement rule for open slots (derived from the existing pads):
--   pad XY = container XY, pad Z = container Z + PAD_LIFT, pad yaw = container yaw + YAW_OFFSET.
--   Every teleporter's exit point is a fixed 215.1 units in front of the pad, so the pad's yaw alone decides where
--   players come out. A slot may override this with an explicit pad = {x, y, z} and yaw.

local Slots = {}

Slots.PAD_LIFT = 4.4
Slots.YAW_OFFSET = 91.5

Slots.list = {
    { id = "A-1", base = true, entrance = "H_Garden_Entrance" },
    { id = "A-2", base = true, entrance = "H_Japan_Entrance" },
    { id = "A-3", pad = { -13024.8, 7990.4, 259.8 }, yaw = 32.7 },   -- placement copied from the Cabin pad
    { id = "A-4", anchor = { -12610.1, 7745.9, 255.4 }, cyaw = 0.1 },

    { id = "B-1", anchor = { -12719.0, 8788.2, -394.6 }, cyaw = -170.3 },
    { id = "B-2", anchor = { -13091.7, 8467.8, -394.6 }, cyaw = -108.0 },
    { id = "B-3", base = true, entrance = "H_Cabin_Entrance" },
    { id = "B-4", anchor = { -12610.1, 7745.9, -394.6 }, cyaw = 0.1 },

    { id = "C-1", anchor = { -12719.0, 8788.2, -1044.6 }, cyaw = -170.3 },
    { id = "C-2", anchor = { -13091.7, 8467.8, -1044.6 }, cyaw = -108.0 },
    { id = "C-3", anchor = { -13038.7, 7981.7, -1044.6 }, cyaw = -59.0 },
    { id = "C-4", anchor = { -12610.1, 7745.9, -1044.6 }, cyaw = 0.1 },
}

Slots.byId = {}
Slots.baseEntrances = {}   -- IDs of the game's own hub entrance pads (used for the hub hum volume)
Slots.openCount = 0
for _, s in ipairs(Slots.list) do
    Slots.byId[s.id] = s
    if s.base then Slots.baseEntrances[s.entrance] = true else Slots.openCount = Slots.openCount + 1 end
end

-- Returns the world location table and yaw for a pad in an open slot.
function Slots.pose(slot)
    if slot.pad then
        return { X = slot.pad[1], Y = slot.pad[2], Z = slot.pad[3] }, slot.yaw
    end
    return { X = slot.anchor[1], Y = slot.anchor[2], Z = slot.anchor[3] + Slots.PAD_LIFT }, slot.cyaw + Slots.YAW_OFFSET
end

return Slots
