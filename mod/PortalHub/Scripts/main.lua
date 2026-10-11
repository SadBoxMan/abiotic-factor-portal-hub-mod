-- Portal Hub: lets modders connect worlds to the Homeworld portal room.
-- Reads Scripts/config.lua, spawns a teleporter pad into each configured slot whenever the world loads, routes the
-- return trip back through the portal the player came in by, and lowers the hub's portal hum as portals are added.
--   NUMPAD 1 = respawn the configured portals now      NUMPAD 2 = remove all hub portals

local UEHelpers = require("UEHelpers")
local Slots = require("slots")
local Config = require("config")

local TELEPORTER_CLASS = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C"
local HOMEWORLD_CLASS = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C"
local ATTEMPT_FN = TELEPORTER_CLASS .. ":AttemptTeleport"
local ID_PREFIX = "hub_"
local LEGACY_PREFIXES = { "portalroom_" }          -- pads left behind by the old proof-of-concept mod
local DEFAULT_DESIGN = "/Game/Particles/Niagara_Portal.Niagara_Portal"
local HUM_MODE = Config.humMode or "dynamic"      -- "dynamic", "manual" or "default"
local HUM_FLOOR = Config.humFloor or 0.15
local HUM_MANUAL = Config.humManual or 0.5
local SPAWN_DELAY_MS = 4000

local state = { entries = {}, dests = {}, hooked = false, pending = false }

local function log(msg) print("[PortalHub] " .. msg .. "\n") end

local function has_prefix(id, prefix) return id:sub(1, #prefix) == prefix end

local function is_hub_id(id)
    if has_prefix(id, ID_PREFIX) then return true end
    for _, p in ipairs(LEGACY_PREFIXES) do
        if has_prefix(id, p) then return true end
    end
    return false
end

local function all_pads()
    local list = {}
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if t:IsValid() then list[#list + 1] = t end
    end
    return list
end

local function pad_id(t)
    local ok, id = pcall(function() return t.MyTeleporterID:ToString() end)
    if ok then return id end
    return nil
end

-- Turn config.lua into a checked list of entries; bad entries are logged and skipped.
local function resolve_config()
    local entries, used, dests = {}, {}, {}
    for i, p in ipairs(Config.portals or {}) do
        local slot = Slots.byId[p.slot]
        if not slot then
            log("config entry " .. i .. ": unknown slot '" .. tostring(p.slot) .. "', skipped")
        elseif slot.base then
            log("config entry " .. i .. ": slot " .. p.slot .. " holds a game portal, skipped")
        elseif used[p.slot] then
            log("config entry " .. i .. ": slot " .. p.slot .. " is already used, skipped")
        elseif type(p.destination) ~= "string" or p.destination == "" then
            log("config entry " .. i .. ": missing destination, skipped")
        else
            used[p.slot] = true
            dests[p.destination] = true
            entries[#entries + 1] = {
                slot = slot,
                name = p.name or p.destination,
                dest = p.destination,
                design = p.design or DEFAULT_DESIGN,
                scale = tonumber(p.scale),
                id = ID_PREFIX .. (p.slot:gsub("-", "")),
            }
        end
    end
    state.entries, state.dests = entries, dests
end

local function destroy_hub_pads()
    local n = 0
    for _, t in ipairs(all_pads()) do
        local id = pad_id(t)
        if id and is_hub_id(id) then t:K2_DestroyActor(); n = n + 1 end
    end
    return n
end

-- Hub hum volume (hub room pads only: the base 3 entrances plus ours), chosen by config.humMode:
--   "default"  leave the game's volume alone (hub pads are set back to normal)
--   "manual"   every hub pad uses humManual
--   "dynamic"  unchanged with just the base 3 portals, then an equal step down per added portal, reaching
--              humFloor when every open slot is filled:   volume = 1 - added * (1 - humFloor) / openSlots
local function hum_multiplier(added)
    if HUM_MODE == "default" then return 1.0 end
    if HUM_MODE == "manual" then return math.min(1.0, math.max(0.0, HUM_MANUAL)) end
    if Slots.openCount > 0 then
        return math.max(HUM_FLOOR, 1.0 - added * (1.0 - HUM_FLOOR) / Slots.openCount)
    end
    return 1.0
end

local function apply_hum(added)
    local mult = hum_multiplier(added)
    local touched = 0
    for _, t in ipairs(all_pads()) do
        local id = pad_id(t)
        if id and (is_hub_id(id) or Slots.baseEntrances[id]) then
            pcall(function()
                local h = t.PortalHumLoop
                if h and h:IsValid() then h:SetVolumeMultiplier(mult); touched = touched + 1 end
            end)
        end
    end
    log(string.format("hum volume (%s) x%.3f on %d hub pad(s) (%d added)", HUM_MODE, mult, touched, added))
end
-- Look, size and hidden parts of a portal's particle effect. Size (scale / designScales) and hidden parts (hideEmitters)
-- come from config.lua. Only the effect is resized: the walk-through trigger and the exit point do not move.
local function apply_design(actor, design, scale)
    local sys = StaticFindObject(design)
    if not (sys and sys:IsValid()) then
        local ok, loaded = pcall(LoadAsset, design)
        if ok then sys = StaticFindObject(design) end
    end
    if not (sys and sys:IsValid()) then log("design not found: " .. design) return end
    local ok, err = pcall(function()
        local pl = actor.ParticleLoop
        pl:SetAsset(sys, true)
        pl:Activate(true)
    end)
    if not ok then log("could not apply design " .. design .. ": " .. tostring(err)) return end

    local s = scale or (Config.designScales and Config.designScales[design]) or 1.0
    if s ~= 1.0 then
        local ok2, err2 = pcall(function() actor.ParticleLoop:SetRelativeScale3D({ X = s, Y = s, Z = s }) end)
        log(ok2 and string.format("  effect size x%.2f", s) or ("  could not resize effect: " .. tostring(err2)))
    end
    local hide = Config.hideEmitters and Config.hideEmitters[design]
    if hide then
        for _, name in ipairs(hide) do
            local ok3, err3 = pcall(function() actor.ParticleLoop:SetEmitterEnable(FName(name), false) end)
            log(ok3 and ("  effect part off: " .. name) or ("  could not switch off '" .. name .. "': " .. tostring(err3)))
        end
    end
end
local function spawn_entry(world, class, e)
    local loc, yaw = Slots.pose(e.slot)
    local actor = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    if not actor or not actor:IsValid() then log(e.slot.id .. ": SpawnActor failed") return false end
    actor.MyTeleporterID = FName(e.id)
    actor.DestinationTeleporterID = FName(e.dest)
    actor.IsTeleporterActive = true
    pcall(function() actor:OnRep_IsTeleporterActive() end)
    apply_design(actor, e.design, e.scale)
    log(string.format("%s: '%s' -> %s (pad %s)", e.slot.id, e.name, e.dest, e.id))
    return true
end

-- The arrival pad of a world only has one destination, so before any pad that leads to a hub-connected world is used
-- we point that world's arrival pad back at the pad being used. This also covers the world's original entrance.
local function route_return(pad)
    local ok, err = pcall(function()
        local dest = pad.DestinationTeleporterID:ToString()
        if not state.dests[dest] then return end
        local mine = pad.MyTeleporterID:ToString()
        for _, t in ipairs(all_pads()) do
            if pad_id(t) == dest and t.DestinationTeleporterID:ToString() ~= mine then
                t.DestinationTeleporterID = FName(mine)
                log("arrival pad " .. dest .. " now returns to " .. mine)
            end
        end
    end)
    if not ok then log("route_return failed: " .. tostring(err)) end
end

local function install_hook()
    if state.hooked then return end
    local ok, err = pcall(function() RegisterHook(ATTEMPT_FN, function(self) route_return(self:get()) end) end)
    if ok then state.hooked = true else log("hook failed: " .. tostring(err)) end
end

local function spawn_all()
    local world = UEHelpers.GetWorld()
    if not world or not world:IsValid() then log("no world yet") return end
    local class = StaticFindObject(TELEPORTER_CLASS)
    if not class or not class:IsValid() then log("teleporter class not found") return end
    destroy_hub_pads()
    install_hook()
    local added = 0
    for _, e in ipairs(state.entries) do
        if spawn_entry(world, class, e) then added = added + 1 end
    end
    apply_hum(added)
    log(added .. " of " .. #state.entries .. " configured portal(s) spawned")
end

local function schedule_spawn(delay_ms)
    if state.pending then return end
    state.pending = true
    ExecuteWithDelay(delay_ms, function()
        state.pending = false
        ExecuteInGameThread(spawn_all)
    end)
end

resolve_config()
log(#state.entries .. " portal(s) configured")

-- Spawn whenever the hub room's own portals appear (world load), and now if the world is already up.
NotifyOnNewObject(HOMEWORLD_CLASS, function() schedule_spawn(SPAWN_DELAY_MS) end)
local existing = FindFirstOf("BP_Teleporter_HomeWorld_C")
if existing and existing:IsValid() then schedule_spawn(500) end

RegisterKeyBind(Key.NUM_ONE, function() ExecuteInGameThread(spawn_all) end)
RegisterKeyBind(Key.NUM_TWO, function()
    ExecuteInGameThread(function()
        log("removed " .. destroy_hub_pads() .. " pad(s)")
        apply_hum(0)
    end)
end)
log("loaded - NUMPAD 1 respawn portals, NUMPAD 2 remove them")




