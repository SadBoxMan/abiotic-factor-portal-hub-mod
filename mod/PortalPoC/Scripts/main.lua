-- PortalPoC v2: slot test. Spawns a test pad in every OPEN portal-room slot, each leading to Dunkeltaler Forest ("Signal").
--   NUMPAD 1 = spawn test pads in all open slots     NUMPAD 2 = remove all test pads     NUMPAD 3 = dump exit points
-- Slot data mirrors Cordona\portal_slots.json. Pad placement rule (derived from the existing Cabin/Garden/Japan pads):
--   pad XY = container anchor XY, pad yaw = container yaw + 91.5, Z = anchor + 4.4.  A-3 uses the proven Cabin-copied placement.
-- Every teleporter's ExitPoint is a fixed +215.1 forward / +127.5 up from the pad, so yaw alone decides where players exit.

local UEHelpers = require("UEHelpers")

local CLASS_PATH = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C"
local ATTEMPT_FN = CLASS_PATH .. ":AttemptTeleport"
local DEST_ID = "signal_start"
local ID_PREFIX = "portalroom_"
local YAW_OFFSET = 91.5

-- name, container anchor (X, Y, Z), container yaw. A-1, A-2 and B-3 hold real portals and are skipped.
local OPEN_SLOTS = {
    { name = "A-3", pad = { -13024.8, 7990.4, 259.8 }, yaw = 32.7 },   -- proven placement
    { name = "A-4", anchor = { -12610.1, 7745.9, 255.4 }, cyaw = 0.1 },
    { name = "B-1", anchor = { -12719.0, 8788.2, -394.6 }, cyaw = -170.3 },
    { name = "B-2", anchor = { -13091.7, 8467.8, -394.6 }, cyaw = -108.0 },
    { name = "B-4", anchor = { -12610.1, 7745.9, -394.6 }, cyaw = 0.1 },
    { name = "C-1", anchor = { -12719.0, 8788.2, -1044.6 }, cyaw = -170.3 },
    { name = "C-2", anchor = { -13091.7, 8467.8, -1044.6 }, cyaw = -108.0 },
    { name = "C-3", anchor = { -13038.7, 7981.7, -1044.6 }, cyaw = -59.0 },
    { name = "C-4", anchor = { -12610.1, 7745.9, -1044.6 }, cyaw = 0.1 },
}

local function log(msg) print("[PortalPoC] " .. msg .. "\n") end

local hooked = false
local apply_hum  -- forward declaration; defined below

local function pad_id(slot) return ID_PREFIX .. slot.name:gsub("-", "") end

local function slot_pose(s)
    if s.pad then return { X = s.pad[1], Y = s.pad[2], Z = s.pad[3] }, s.yaw end
    return { X = s.anchor[1], Y = s.anchor[2], Z = s.anchor[3] + 4.4 }, s.cyaw + YAW_OFFSET
end

local function destroy_all_ours()
    local n = 0
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if t:IsValid() then
            local ok, id = pcall(function() return t.MyTeleporterID:ToString() end)
            if ok and id:sub(1, #ID_PREFIX) == ID_PREFIX then t:K2_DestroyActor(); n = n + 1 end
        end
    end
    return n
end

-- Exit routing: signal_start sends players to its Destination ID, so just before a pad is used we point
-- signal_start at the pad the player entered through (one of ours, or the original Hydroplant pad).
local last_route = nil
local function route_return(pad)
    local ok, err = pcall(function()
        local id = pad.MyTeleporterID:ToString()
        local want
        if id:sub(1, #ID_PREFIX) == ID_PREFIX or id == "signal_entrance" then want = id end
        if not want then return end
        for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
            if t:IsValid() and t.MyTeleporterID:ToString() == "signal_start" then
                t.DestinationTeleporterID = FName(want)
            end
        end
        if want ~= last_route then log("signal_start now returns to " .. want); last_route = want end
    end)
    if not ok then log("route_return failed: " .. tostring(err)) end
end

local function install_hook()
    if hooked then return end
    local ok, err = pcall(function() RegisterHook(ATTEMPT_FN, function(self) route_return(self:get()) end) end)
    if ok then hooked = true; log("hooked AttemptTeleport") else log("hook failed: " .. tostring(err)) end
end

local function spawn_slot(world, class, s)
    local loc, yaw = slot_pose(s)
    local actor = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    if not actor or not actor:IsValid() then log(s.name .. ": SpawnActor failed") return end
    actor.MyTeleporterID = FName(pad_id(s))
    actor.DestinationTeleporterID = FName(DEST_ID)
    actor.IsTeleporterActive = true
    pcall(function() actor:OnRep_IsTeleporterActive() end)
    log(string.format("%s: pad %s at %.1f, %.1f, %.1f yaw %.1f", s.name, pad_id(s), loc.X, loc.Y, loc.Z, yaw))
end

local function spawn_all()
    destroy_all_ours()
    local world = UEHelpers.GetWorld()
    if not world or not world:IsValid() then log("no world") return end
    local class = StaticFindObject(CLASS_PATH)
    if not class or not class:IsValid() then log("teleporter class not found") return end
    install_hook()
    for _, s in ipairs(OPEN_SLOTS) do spawn_slot(world, class, s) end
    apply_hum()
end

local function fmtv(v) return string.format("%.1f, %.1f, %.1f", v.X, v.Y, v.Z) end
local function dump_exits()
    local f = io.open("PortalExits.txt", "w")
    if not f then log("cannot open PortalExits.txt") return end
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if t:IsValid() then
            local ok, line = pcall(function()
                local id = t.MyTeleporterID:ToString()
                if id:sub(1, #ID_PREFIX) ~= ID_PREFIX then return nil end
                return id .. " pad " .. fmtv(t:K2_GetActorLocation()) .. "  exit " .. fmtv(t.ExitPoint:K2_GetComponentLocation())
            end)
            if ok and line then log(line); f:write(line .. "\n") end
        end
    end
    f:close()
end

RegisterKeyBind(Key.NUM_ONE, function() ExecuteInGameThread(spawn_all) end)
RegisterKeyBind(Key.NUM_TWO, function() ExecuteInGameThread(function() log("removed " .. destroy_all_ours() .. " pad(s)"); apply_hum() end) end)
RegisterKeyBind(Key.NUM_THREE, function() ExecuteInGameThread(dump_exits) end)
log("loaded - NUMPAD 1 spawn test pads, NUMPAD 2 remove, NUMPAD 3 dump exits")

-- NUMPAD 4: dump the "design" of every teleporter pad (particle system, portal texture/image, sounds, text, light colour)
-- to PortalDesigns.txt, one line per pad, plus a summary of how often each particle system is used.
local function describe(v)
    if v == nil then return "nil" end
    if type(v) == "userdata" or type(v) == "table" then
        local ok, s = pcall(function()
            if v.IsValid and not v:IsValid() then return "<invalid>" end
            if v.GetFullName then return v:GetFullName() end
            if v.ToString then return v:ToString() end
            return "<" .. type(v) .. ">"
        end)
        return ok and tostring(s) or "<unreadable>"
    end
    return tostring(v)
end
local function try(fn) local ok, v = pcall(fn); if ok then return describe(v) end return "<err>" end

local function dump_designs()
    local f = io.open("PortalDesigns.txt", "w")
    if not f then log("cannot open PortalDesigns.txt") return end
    local counts = {}
    local seen = {}
    for _, cn in ipairs({ "BP_Teleporter_HomeWorld_C", "BP_Teleporter_ParentBP_C", "BP_Teleporter_PlayerPortal_C" }) do
        for _, t in ipairs(FindAllOf(cn) or {}) do
            if t:IsValid() and not seen[t:GetFullName()] then
                seen[t:GetFullName()] = true
                local id = try(function() return t.MyTeleporterID:ToString() end)
                local particle = try(function() local pl = t.ParticleLoop; if pl and pl:IsValid() then return pl:GetAsset() end end)
                local tex = try(function() return t.PortalTexture end)
                local img = try(function() return t.PortalImage end)
                local hum = try(function() local h = t.PortalHumLoop; if h and h:IsValid() then return h.Sound end end)
                local act = try(function() return t.PortalActivateSound end)
                local text = try(function() return t.DestText.Text:ToString() end)
                local light = try(function() local l = t.PointLight.LightColor; return string.format("%d,%d,%d", l.R, l.G, l.B) end)
                local quiet = try(function() return t.QuieterPortal end)
                local line = table.concat({ id, cn, "particle=" .. particle, "texture=" .. tex, "image=" .. img,
                    "hum=" .. hum, "activateSound=" .. act, "text=" .. text, "lightRGB=" .. light, "quiet=" .. quiet }, " | ")
                f:write(line .. "\n")
                counts[particle] = (counts[particle] or 0) + 1
            end
        end
    end
    f:write("\n=== particle systems in use ===\n")
    for k, n in pairs(counts) do f:write(string.format("%3d  %s\n", n, k)) end
    f:close()
    log("design dump done")
end
RegisterKeyBind(Key.NUM_FOUR, function() ExecuteInGameThread(dump_designs) end)

-- Hum volume for the whole portal hub: the 3 base portals plus every added portal share one volume.
-- No change until a portal is added beyond the base 3; then each added portal lowers it by an equal step,
-- reaching HUM_MIN when all slots are filled:   volume = 1 - n * (1 - HUM_MIN) / MAX_PORTALS   (n = added portals)
-- Only pads in the hub room are touched (the 3 base Entrance pads + ours), never the pads inside the worlds.
-- NUMPAD 5 re-applies it; NUMPAD 6 resets every pad's hum to normal.
local HUM_MIN = 0.15
local MAX_PORTALS = #OPEN_SLOTS
local BASE_ENTRANCES = { H_Cabin_Entrance = true, H_Garden_Entrance = true, H_Japan_Entrance = true }

local function hub_pads()
    local ours, base = {}, {}
    for _, cn in ipairs({ "BP_Teleporter_HomeWorld_C", "BP_Teleporter_ParentBP_C" }) do
        for _, t in ipairs(FindAllOf(cn) or {}) do
            if t:IsValid() then
                local ok, id = pcall(function() return t.MyTeleporterID:ToString() end)
                if ok then
                    if id:sub(1, #ID_PREFIX) == ID_PREFIX then ours[#ours + 1] = t
                    elseif BASE_ENTRANCES[id] then base[#base + 1] = t end
                end
            end
        end
    end
    return ours, base
end

apply_hum = function()
    local ours, base = hub_pads()
    local n = #ours
    local mult = math.max(HUM_MIN, 1.0 - n * (1.0 - HUM_MIN) / MAX_PORTALS)
    local touched = 0
    for _, list in ipairs({ ours, base }) do
        for _, t in ipairs(list) do
            pcall(function()
                local h = t.PortalHumLoop
                if h and h:IsValid() then h:SetVolumeMultiplier(mult); touched = touched + 1 end
            end)
        end
    end
    log(string.format("hum volume x%.3f on %d hub pad(s) (%d base + %d added)", mult, touched, #base, n))
end
local function reset_all_hum()
    local n = 0
    for _, cn in ipairs({ "BP_Teleporter_HomeWorld_C", "BP_Teleporter_ParentBP_C" }) do
        for _, t in ipairs(FindAllOf(cn) or {}) do
            if t:IsValid() then
                pcall(function()
                    local h = t.PortalHumLoop
                    if h and h:IsValid() then h:SetVolumeMultiplier(1.0); n = n + 1 end
                end)
            end
        end
    end
    log("hum volume reset to x1.0 on " .. n .. " pads")
end

RegisterKeyBind(Key.NUM_FIVE, function() ExecuteInGameThread(apply_hum) end)
RegisterKeyBind(Key.NUM_SIX, function() ExecuteInGameThread(reset_all_hum) end)

