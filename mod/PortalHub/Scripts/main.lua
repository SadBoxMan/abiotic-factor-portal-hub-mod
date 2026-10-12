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

-- The two DLC areas (Temple of Stone / Garden, Torii / Japan) are DLC-gated by the game's own entrance pads; a hub portal would
-- bypass that, so these pad IDs are refused as destinations (the config editor refuses them too). Compared in lower case.
local BLOCKED_DESTINATIONS = { h_garden_start = true, h_garden_entrance = true, h_japan_start = true, h_japan_entrance = true }

local state = { entries = {}, dests = {}, hooked = false, pending = false }
local worldDefs = {}     -- custom worlds from config.worlds, checked (see resolve_worlds)
local worldState = {}    -- id -> { status = "loading" | "ready" | "failed", tries = n }

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
        elseif type(p.destination) == "string" and BLOCKED_DESTINATIONS[p.destination:lower()] then
            log("config entry " .. i .. ": " .. p.destination .. " is a DLC area and cannot be a destination, skipped")
        elseif type(p.destination) ~= "string" or p.destination == "" then
            log("config entry " .. i .. ": missing destination, skipped")
        else
            local lc, lb = nil, nil
            if type(p.lightColor) == "table" and #p.lightColor >= 3 then
                lc = {}
                for k = 1, 3 do lc[k] = math.min(1.0, math.max(0.0, tonumber(p.lightColor[k]) or 0.0)) end
            end
            if p.lightBrightness ~= nil then
                lb = tonumber(p.lightBrightness)
                if lb and lb <= 0 then lb = nil end
            end
            used[p.slot] = true
            dests[p.destination] = true
            entries[#entries + 1] = {
                slot = slot,
                name = p.name or p.destination,
                dest = p.destination,
                design = p.design or DEFAULT_DESIGN,
                world = worldDefs[p.destination],
                lightColor = lc,
                lightBrightness = lb,
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
-- Look and hidden parts of a portal's particle effect. Hidden parts (hideEmitters)
-- come from config.lua.
local function apply_design(actor, design)
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

    local hide = Config.hideEmitters and Config.hideEmitters[design]
    if hide then
        for _, name in ipairs(hide) do
            local lname = tostring(name):lower()
            local ok3, err3
            if lname == "portal" or lname == "portalmap" then
                ok3, err3 = false, "the portal part of a look cannot be switched off"
            else
                ok3, err3 = pcall(function() actor.ParticleLoop:SetEmitterEnable(FName(name), false) end)
            end
            log(ok3 and ("  effect part off: " .. name) or ("  could not switch off '" .. name .. "': " .. tostring(err3)))
        end
    end
end
-- Pad light: each portal pad has a light that tints its surroundings. lightColor = { r, g, b } (0 to 1) sets its colour and
-- lightBrightness = 1.5 multiplies its intensity (both optional). Works with every portal look.
local function apply_light(actor, e)
    if not (e.lightColor or e.lightBrightness) then return end
    local ok, err = pcall(function()
        local light = actor.PointLight
        if not (light and light:IsValid()) then error("the pad has no light component") end
        if e.lightColor then
            light:SetLightColor({ R = e.lightColor[1], G = e.lightColor[2], B = e.lightColor[3], A = 1.0 }, true)
        end
        if e.lightBrightness then
            local base = light.Intensity
            light:SetIntensity(base * e.lightBrightness)
        end
    end)
    local what = {}
    if e.lightColor then what[#what + 1] = string.format("colour %.2f, %.2f, %.2f", e.lightColor[1], e.lightColor[2], e.lightColor[3]) end
    if e.lightBrightness then what[#what + 1] = string.format("brightness x%.2f", e.lightBrightness) end
    log(ok and ("  pad light: " .. table.concat(what, ", ")) or ("  could not set the pad light: " .. tostring(err)))
end
-- Custom worlds ---------------------------------------------------------------------------------------------------------
-- config.worlds[<arrival pad id>] = { loaderAsset, loaderClass, level, origin = { x, y, z }, arrive = { x, y, z, yaw } }
-- A custom world is loaded by spawning a "loader" actor Blueprint that ships in the world's own pak; the actor streams the level in
-- itself, so no text argument ever has to be passed from Lua. Once the level is visible the hub spawns the arrival pad at
-- origin + arrive and switches on the hub portals that lead to it. Until then those portals stay off.
local WORLD_POLL_MS = 250
local WORLD_MAX_TRIES = 720      -- about 3 minutes

local function resolve_worlds()
    worldDefs = {}
    for id, w in pairs(Config.worlds or {}) do
        local ok = type(id) == "string" and id ~= "" and type(w) == "table"
        ok = ok and type(w.loaderAsset) == "string" and type(w.loaderClass) == "string" and type(w.level) == "string"
        ok = ok and type(w.origin) == "table" and #w.origin >= 3 and type(w.arrive) == "table" and #w.arrive >= 3
        if ok then
            worldDefs[id] = {
                id = id, loaderAsset = w.loaderAsset, loaderClass = w.loaderClass, level = w.level,
                origin = { tonumber(w.origin[1]) or 0, tonumber(w.origin[2]) or 0, tonumber(w.origin[3]) or 0 },
                arrive = { tonumber(w.arrive[1]) or 0, tonumber(w.arrive[2]) or 0, tonumber(w.arrive[3]) or 0, tonumber(w.arrive[4]) or 0 },
            }
            if is_hub_id(id) then log("worlds: '" .. id .. "' starts with a reserved prefix and may be removed with the hub portals; rename it") end
        else
            log("worlds: entry '" .. tostring(id) .. "' is incomplete (needs loaderAsset, loaderClass, level, origin = {x,y,z}, arrive = {x,y,z,yaw}), ignored")
        end
    end
end

local function loader_class(def)
    -- 1) UE4SS's documented LoadAsset (loads the Blueprint package), then find its generated class (<asset>.<ClassName>_C).
    pcall(LoadAsset, def.loaderAsset)
    local cls = StaticFindObject(def.loaderAsset .. "." .. def.loaderClass)
    if cls and cls:IsValid() then return cls end
    -- 2) Fallback: Unreal's AssetRegistryHelpers:GetAsset, which takes names (FName) only.
    local helpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
    if helpers and helpers:IsValid() then
        pcall(function()
            cls = helpers:GetAsset({
                PackageName = UEHelpers.FindOrAddFName(def.loaderAsset),
                AssetName = UEHelpers.FindOrAddFName(def.loaderClass),
            })
        end)
        if cls and cls:IsValid() then return cls end
    end
    return nil, "the world's pak is not installed (no " .. def.loaderClass .. " in " .. def.loaderAsset .. ")"
end
local function loader_present(def)
    for _, a in ipairs(FindAllOf(def.loaderClass) or {}) do
        if a:IsValid() then return true end
    end
    return false
end

local function find_streaming(world, level)
    local found
    pcall(function()
        world.StreamingLevels:ForEach(function(_, elem)
            local ls = elem:get()
            if ls and ls:IsValid() then
                local ok, name = pcall(function() return ls.PackageNameToLoad:ToString() end)
                local ok2, asset = pcall(function() return ls:GetWorldAssetPackageFName():ToString() end)
                if (ok and name == level) or (ok2 and type(asset) == "string" and asset:sub(1, #level) == level) then found = ls end
            end
        end)
    end)
    return found
end

-- Diagnostic: what does the world's streaming list actually hold, and where is the loader? Read-only; every object is checked first.
local function diag_streaming(world, def)
    local n, matches = 0, {}
    local ok = pcall(function()
        world.StreamingLevels:ForEach(function(_, elem)
            n = n + 1
            local ls = elem:get()
            if ls and ls:IsValid() then
                local a, b = "?", "?"
                pcall(function() a = ls.PackageNameToLoad:ToString() end)
                pcall(function() b = ls:GetWorldAssetPackageFName():ToString() end)
                local hay = (a .. " " .. b):lower()
                if hay:find("cordona") or hay:find("levelinstance") or hay:find("/mods/") then matches[#matches + 1] = a .. " | " .. b end
            end
        end)
    end)
    log(string.format("worlds: diag: StreamingLevels readable=%s, entries=%d, entries that look like ours=%d", tostring(ok), n, #matches))
    for i = 1, math.min(#matches, 5) do log("worlds: diag:   " .. matches[i]) end
    local dyn = FindAllOf("LevelStreamingDynamic") or {}
    log("worlds: diag: LevelStreamingDynamic objects in the world: " .. #dyn)
    for _, a in ipairs(FindAllOf(def.loaderClass) or {}) do
        if a:IsValid() then
            local ok2, loc = pcall(function() local l = a:K2_GetActorLocation(); return string.format("%.0f, %.0f, %.0f", l.X, l.Y, l.Z) end)
            log("worlds: diag: loader actor " .. a:GetFName():ToString() .. " at " .. (ok2 and loc or "?"))
        end
    end
end
local function spawn_arrival_pad(world, def)
    for _, t in ipairs(all_pads()) do
        if pad_id(t) == def.id then return t end        -- already there
    end
    local class = StaticFindObject(TELEPORTER_CLASS)
    if not (class and class:IsValid()) then log("worlds: teleporter class not found") return nil end
    local loc = { X = def.origin[1] + def.arrive[1], Y = def.origin[2] + def.arrive[2], Z = def.origin[3] + def.arrive[3] }
    local pad = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = def.arrive[4], Roll = 0.0 })
    if not (pad and pad:IsValid()) then log("worlds: could not spawn the arrival pad for " .. def.id) return nil end
    pad.MyTeleporterID = FName(def.id)
    pad.DestinationTeleporterID = FName("None")
    pad.IsTeleporterActive = true
    pcall(function() pad:OnRep_IsTeleporterActive() end)
    apply_design(pad, DEFAULT_DESIGN)
    log(string.format("worlds: arrival pad %s at %.0f, %.0f, %.0f facing %.0f", def.id, loc.X, loc.Y, loc.Z, def.arrive[4]))
    return pad
end

local function set_portals_active(id, on)
    for _, e in ipairs(state.entries) do
        if e.world and e.world.id == id and e.actor and e.actor:IsValid() then
            pcall(function() e.actor.IsTeleporterActive = on; e.actor:OnRep_IsTeleporterActive() end)
        end
    end
end

local function start_world(world, def)
    local st = { status = "loading", tries = 0 }
    worldState[def.id] = st
    if loader_present(def) then log("worlds: a loader for " .. def.id .. " already exists, not spawning another") end
    if not loader_present(def) then
        local cls, err = loader_class(def)
        if not cls then st.status = "failed"; log("worlds: " .. def.id .. " cannot load: " .. tostring(err)) return end
        local ok, e = pcall(function()
            world:SpawnActor(cls, { X = def.origin[1], Y = def.origin[2], Z = def.origin[3] }, { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 })
        end)
        if not ok then st.status = "failed"; log("worlds: " .. def.id .. " loader spawn failed: " .. tostring(e)) return end
        log("worlds: loader spawned for " .. def.id .. ", waiting for the level to stream in")
    end
    local function poll()
        if st.status ~= "loading" then return end
        st.tries = st.tries + 1
        if not world:IsValid() then st.status = "failed"; log("worlds: " .. def.id .. ": the game world changed while loading") return end
        local ls = find_streaming(world, def.level)
        if st.tries == 1 or st.tries % 20 == 0 then
            local loaded, visible = "?", "?"
            if ls then pcall(function() loaded = tostring(ls:IsLevelLoaded()) end); pcall(function() visible = tostring(ls:IsLevelVisible()) end) end
            log(string.format("worlds: %s waiting (%.0f s): streaming level %s, loaded=%s, visible=%s", def.id, st.tries * WORLD_POLL_MS / 1000, ls and "found" or "NOT found", loaded, visible))
            if not ls and (st.tries == 1 or st.tries == 40) then diag_streaming(world, def) end
        end
        if ls then
            if st.tries % 5 == 0 then pcall(function() UEHelpers.GetGameplayStatics():FlushLevelStreaming(world) end) end
            local visible = false
            pcall(function() visible = ls:IsLevelVisible() end)
            if visible then
                st.status = "ready"
                spawn_arrival_pad(world, def)
                set_portals_active(def.id, true)
                log(string.format("worlds: %s is ready after %.1f s, hub portals to it are on", def.id, st.tries * WORLD_POLL_MS / 1000))
                return
            end
        end
        if st.tries >= WORLD_MAX_TRIES then
            st.status = "failed"
            log("worlds: " .. def.id .. " did not finish loading in time")
            return
        end
        ExecuteWithDelay(WORLD_POLL_MS, function() ExecuteInGameThread(poll) end)
    end
    ExecuteWithDelay(WORLD_POLL_MS, function() ExecuteInGameThread(poll) end)
end

-- Called whenever the hub portals are (re)spawned: load every custom world a hub portal leads to, once.
local function ensure_worlds(world)
    local seen = {}
    for _, e in ipairs(state.entries) do
        local def = e.world
        if def and not seen[def.id] then
            seen[def.id] = true
            local st = worldState[def.id]
            log("worlds: checking " .. def.id .. " (status " .. (st and st.status or "none") .. ", loader present " .. tostring(loader_present(def)) .. ")")
            if st and st.status ~= "failed" and not loader_present(def) then st = nil end    -- a new game world: start over
            if not st or st.status == "failed" then
                start_world(world, def)
            elseif st.status == "ready" then
                spawn_arrival_pad(world, def)
                set_portals_active(def.id, true)
            end
        end
    end
end
local function spawn_entry(world, class, e)
    local loc, yaw = Slots.pose(e.slot)
    local actor = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    if not actor or not actor:IsValid() then log(e.slot.id .. ": SpawnActor failed") return false end
    actor.MyTeleporterID = FName(e.id)
    actor.DestinationTeleporterID = FName(e.dest)
    local waiting = e.world and not (worldState[e.world.id] and worldState[e.world.id].status == "ready")
    actor.IsTeleporterActive = not waiting          -- a portal to a custom world stays off until that world has loaded
    pcall(function() actor:OnRep_IsTeleporterActive() end)
    e.actor = actor
    apply_design(actor, e.design)
    apply_light(actor, e)
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
    log("spawn_all: starting")
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
    ensure_worlds(world)
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

resolve_worlds()
resolve_config()
log(#state.entries .. " portal(s) configured")

-- Spawn whenever the hub room's own portals appear (world load), and now if the world is already up.
NotifyOnNewObject(HOMEWORLD_CLASS, function() log("a Homeworld pad appeared; spawning the hub portals shortly"); schedule_spawn(SPAWN_DELAY_MS) end)
local existing = FindFirstOf("BP_Teleporter_HomeWorld_C")
if existing and existing:IsValid() then
    log("the portal room is already loaded; spawning the hub portals")
    schedule_spawn(500)
else
    log("the portal room is not loaded yet; the hub portals will spawn when you get near it (or press NUMPAD 1 in the room)")
end

RegisterKeyBind(Key.NUM_ONE, function() log("NUMPAD 1 pressed"); ExecuteInGameThread(spawn_all) end)
RegisterKeyBind(Key.NUM_TWO, function()
    ExecuteInGameThread(function()
        log("removed " .. destroy_hub_pads() .. " pad(s)")
        apply_hum(0)
    end)
end)
log("loaded - NUMPAD 1 respawn portals, NUMPAD 2 remove them")
















