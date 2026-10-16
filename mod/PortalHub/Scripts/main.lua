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
            -- optional: lighting = { sun = n, sunColor = { r, g, b }, sunPitch = deg, sky = n, fog = n }  (only the keys you give are changed)
            local lighting = nil
            if type(w.lighting) == "table" then
                lighting = {}
                for _, k in ipairs({ "sun", "sunPitch", "sky", "fog" }) do
                    local v = tonumber(w.lighting[k])
                    if v then lighting[k] = v end
                end
                if type(w.lighting.sunColor) == "table" and #w.lighting.sunColor >= 3 then
                    lighting.sunColor = { tonumber(w.lighting.sunColor[1]) or 1, tonumber(w.lighting.sunColor[2]) or 1, tonumber(w.lighting.sunColor[3]) or 1 }
                end
                if next(lighting) == nil then lighting = nil end
            end
            -- optional: lightingFrom = "HGarden" or { day = "...", night = "..." }: rows of the game's lighting table (DT_LevelFX) the game
            -- lights the world with while the player is inside (day/night, fog, colour grading). Checked when the world is entered.
            local lightDay, lightNight = nil, nil
            if type(w.lightingFrom) == "string" and w.lightingFrom ~= "" then
                lightDay, lightNight = w.lightingFrom, w.lightingFrom
            elseif type(w.lightingFrom) == "table" then
                lightDay = type(w.lightingFrom.day) == "string" and w.lightingFrom.day or nil
                lightNight = type(w.lightingFrom.night) == "string" and w.lightingFrom.night or lightDay
            end
            worldDefs[id] = {
                id = id, loaderAsset = w.loaderAsset, loaderClass = w.loaderClass, level = w.level,
                origin = { tonumber(w.origin[1]) or 0, tonumber(w.origin[2]) or 0, tonumber(w.origin[3]) or 0 },
                arrive = { tonumber(w.arrive[1]) or 0, tonumber(w.arrive[2]) or 0, tonumber(w.arrive[3]) or 0, tonumber(w.arrive[4]) or 0 },
                lighting = lighting,
                radius = tonumber(w.radius) or 100000,       -- how far (sideways) from origin counts as "inside this world"
                killZ = tonumber(w.killZ),                   -- optional: below origin z + killZ the player is returned to the arrival pad
                vignette = (w.vignette ~= false),            -- default on: the world counts as a vignette (no weather); vignette = false opts out
                title = type(w.title) == "string" and w.title ~= "" and w.title or nil,   -- shown by the game on arrival; default: the portal's name
                leyakSafe = w.leyakSafe,                     -- true / false / nil: Leyak safety zone; default on (see world_leyak_safe)
                type = type(w.type) == "string" and w.type or nil,  -- "home" (default) or "vignette" (see world_type)
                exit = (type(w.exit) == "table" and #w.exit >= 3) and { tonumber(w.exit[1]) or 0, tonumber(w.exit[2]) or 0,
                    tonumber(w.exit[3]) or 0, tonumber(w.exit[4]) or 0 } or nil,  -- a vignette's proper exit, relative to origin: x, y, z, yaw
                lightingDay = lightDay, lightingNight = lightNight,
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
-- Where a world's arrival pad sends players back to until someone walks in through a hub portal (route_return then points it at the
-- portal they used): the first hub portal leading to this world. Without this, a save loaded inside the world has an exit that goes nowhere.
local function default_return(def)
    for _, e in ipairs(state.entries) do
        if e.dest == def.id then return e.id end
    end
    return nil
end

local function spawn_arrival_pad(world, def)
    for _, t in ipairs(all_pads()) do
        if pad_id(t) == def.id then                     -- already there: make sure its exit leads somewhere
            local back = default_return(def)
            local cur = nil
            pcall(function() cur = t.DestinationTeleporterID:ToString() end)
            if back and (cur == nil or cur == "None" or cur == "") then
                pcall(function() t.DestinationTeleporterID = FName(back) end)
                log("worlds: arrival pad " .. def.id .. " had no exit; it now returns to " .. back)
            end
            return t
        end
    end
    local class = StaticFindObject(TELEPORTER_CLASS)
    if not (class and class:IsValid()) then log("worlds: teleporter class not found") return nil end
    local loc = { X = def.origin[1] + def.arrive[1], Y = def.origin[2] + def.arrive[2], Z = def.origin[3] + def.arrive[3] }
    local pad = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = def.arrive[4], Roll = 0.0 })
    if not (pad and pad:IsValid()) then log("worlds: could not spawn the arrival pad for " .. def.id) return nil end
    pad.MyTeleporterID = FName(def.id)
    pad.DestinationTeleporterID = FName(default_return(def) or "None")
    pad.IsTeleporterActive = true
    pcall(function() pad:OnRep_IsTeleporterActive() end)
    apply_design(pad, DEFAULT_DESIGN)
    log(string.format("worlds: arrival pad %s at %.0f, %.0f, %.0f facing %.0f, returns to %s", def.id, loc.X, loc.Y, loc.Z, def.arrive[4], default_return(def) or "nowhere yet"))
    return pad
end

-- The game's own vignette worlds hold a Vignette_Zone: a buff zone (BuffZone_ParentBP) that also checks a story flag named
-- PortalSicknessWorldFlag. It is not what makes an area a vignette (that is the level table, see "vignette status" below), but it is part
-- of what a vignette has, so one is spawned over a vignette world's area, sized to its radius, once the world is ready. It is the game's
-- own class, looked up by path; nothing is copied.
-- Do NOT spawn Trigger_WeatherBlocker: it is a story trigger that ends the CURRENT WEATHER FOR EVERYONE (it asks the DayNightManager)
-- when a player walks into it. Weather inside a custom world is handled per player through the level table instead.
local VIGNETTE_ZONE = "/Game/Blueprints/Environment/Volumes/Vignette_Zone.Vignette_Zone_C"
-- Most of the game's worlds also hold a LeyakSafetyZone (another buff zone; it gives Buff_LeyakSafetyZone, which keeps the Leyak away).
-- A world gets one too unless its map maker switches it off (LeyakSafeZone on the loader Blueprint) or config.lua does (leyakSafe = false).
local LEYAK_ZONE = "/Game/Blueprints/Environment/Volumes/LeyakSafetyZone.LeyakSafetyZone_C"

local function zone_present(shortClass, def)
    for _, a in ipairs(FindAllOf(shortClass) or {}) do
        if a:IsValid() then
            local ok, dx, dy = pcall(function() local l = a:K2_GetActorLocation(); return l.X - def.origin[1], l.Y - def.origin[2] end)
            if ok and dx * dx + dy * dy < 1000 * 1000 then return true end
        end
    end
    return false
end

local function spawn_zone(world, def, path, shortClass, label)
    if zone_present(shortClass, def) then return true end
    -- The class is only in memory once something loaded it (for example after visiting one of the game's vignettes), so load it here,
    -- trying the forms UE4SS's LoadAsset may expect: the package, the Blueprint asset, the generated class.
    local pkg = path:gsub("%.[^%.]*$", "")
    local asset = pkg .. "." .. pkg:match("[^/]+$")
    local cls = StaticFindObject(path)
    local how = "already loaded"
    for _, try in ipairs({ pkg, asset, path }) do
        if cls and cls:IsValid() then break end
        pcall(LoadAsset, try)
        cls = StaticFindObject(path)
        how = "loaded via " .. try
    end
    if not (cls and cls:IsValid()) then
        local helpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
        if helpers and helpers:IsValid() then
            pcall(function() helpers:GetAsset({ PackageName = FName(pkg), AssetName = FName(pkg:match("[^/]+$")) }) end)
            cls = StaticFindObject(path)
            how = "loaded via the asset registry"
        end
    end
    if not (cls and cls:IsValid()) then log("worlds: the game's " .. label .. " class could not be loaded; " .. def.id .. " has no " .. label .. " yet (tried again on entry)") return false end
    log("worlds: " .. label .. " class " .. how)
    local actor
    local ok, e = pcall(function()
        actor = world:SpawnActor(cls, { X = def.origin[1], Y = def.origin[2], Z = def.origin[3] }, { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 })
    end)
    if not (ok and actor and actor:IsValid()) then log("worlds: could not spawn a " .. label .. " for " .. def.id .. ": " .. tostring(e)) return end
    -- size its box to cover the world's area: try the box component names the two classes might use
    local sized = false
    for _, prop in ipairs({ "BuffVolume", "TriggerVolume", "CollisionComponent", "BoxComponent", "Box", "TriggerBox" }) do
        local okC, comp = pcall(function() return actor[prop] end)
        if okC and comp and comp:IsValid() then
            local r = def.radius
            if pcall(function() comp:SetBoxExtent({ X = r, Y = r, Z = r }, false) end) then sized = true; break end
        end
    end
    log(string.format("worlds: %s spawned over %s (radius %.0f, box resized: %s)", label, def.id, def.radius, tostring(sized)))
    return true
end

-- a Boolean variable on the world's loader Blueprint (class defaults); nil when the world does not have it
local function loader_flag(def, var)
    local cdo = StaticFindObject(def.loaderAsset .. ".Default__" .. def.loaderClass)
    if not (cdo and cdo:IsValid()) then return nil end
    local ok, v = pcall(function() return cdo[var] end)
    if ok and type(v) == "boolean" then return v end
    return nil
end

local function world_leyak_safe(def)
    local v = loader_flag(def, "LeyakSafeZone")
    if v == nil and type(def.leyakSafe) == "boolean" then v = def.leyakSafe end
    if v == nil then v = true end
    return v
end

-- World settings made by the map maker live on the world's own loader Blueprint, as plain variables (text, name, number, vector) on its
-- class defaults, so a world describes itself and needs no hub configuration beyond which slot it goes in. Read-only; never soft
-- references. Returns nil when the variable is missing or empty.
local function loader_setting(def, var)
    local cdo = StaticFindObject(def.loaderAsset .. ".Default__" .. def.loaderClass)     -- the class defaults object
    if not (cdo and cdo:IsValid()) then
        local cls = StaticFindObject(def.loaderAsset .. "." .. def.loaderClass)
        if cls and cls:IsValid() then pcall(function() cdo = cls:GetCDO() end) end
    end
    if not (cdo and cdo:IsValid()) then return nil end
    local ok, v = pcall(function() return cdo[var]:ToString() end)
    if ok and type(v) == "string" and v ~= "" and v ~= "None" then return v end
    return nil
end

-- ---------------------------------------------------------------- world type: home (default) or vignette
-- The game's home worlds (H_Garden, H_Japan, H_Cabin) and vignettes both hold a Vignette_Zone that gives Buff_InVignette. In a vignette the
-- zone also names a story flag (PortalSicknessWorldFlag; the Train's is TrainCompletedOnce): until that flag is set the player has
-- Debuff_PortalSickness (equipment locked). The vignette's proper exit is a teleporter whose WorldFlagToTriggerOnUse sets the flag, after
-- which the sickness never comes back for that world. Story flags are saved with the world save as plain names.
-- For a vignette world the hub adds a flag "PortalHub_<world id>_Completed" to the game's flag table, points the world's zone at it, and
-- spawns the proper exit pad (exit = { x, y, z, yaw } relative to origin), which sets the flag and leads back to the world's hub portal.
local WORLD_FLAGS_TABLE = "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags"

local function world_type(def)
    local v = (loader_setting(def, "WorldType") or def.type or "home"):lower()
    if v ~= "vignette" then v = "home" end
    return v
end

local function completion_flag(def) return "PortalHub_" .. def.id .. "_Completed" end
local function exit_pad_id(def) return def.id .. "_exit" end

-- the table path the game itself writes into flag handles (read from the portal room's home pads), else the table's object path
local function flag_table_path()
    for _, t in ipairs(FindAllOf("BP_Teleporter_HomeWorld_C") or {}) do
        if t:IsValid() then
            local ok, p = pcall(function() return t.RequiredWorldFlag.DataTablePath:ToString() end)
            if ok and type(p) == "string" and p ~= "" then return p end
        end
    end
    return WORLD_FLAGS_TABLE
end

local function flag_handle(name) return { RowName = FName(name), DataTablePath = flag_table_path() } end

local function ensure_flag_row(def)
    local dt = StaticFindObject(WORLD_FLAGS_TABLE)
    if not (dt and dt:IsValid()) then pcall(LoadAsset, (WORLD_FLAGS_TABLE:gsub("%.[^%.]*$", ""))); dt = StaticFindObject(WORLD_FLAGS_TABLE) end
    if not (dt and dt:IsValid()) then log("vignette: the game's story-flag table is not loaded; " .. def.id .. " gets no completion flag yet") return false end
    local name = completion_flag(def)
    local okF, row = pcall(function() return dt:FindRow(name) end)
    if okF and row ~= nil then return true end
    local ok, err = pcall(function() dt:AddRow(name, { ReleaseGroup = 0, DebugText = "Portal Hub: " .. def.id .. " completed" }) end)
    local okB, back = pcall(function() return dt:FindRow(name) end)
    if not (ok and okB and back ~= nil) then log("vignette: could not add the story flag " .. name .. ": " .. tostring(err):match("^[^\r\n]*")) return false end
    log("vignette: story flag " .. name .. " added")
    return true
end

local function spawn_exit_pad(world, def)
    for _, t in ipairs(all_pads()) do
        if pad_id(t) == exit_pad_id(def) then return t end
    end
    if not def.exit then log("vignette: " .. def.id .. " is a vignette but has no exit; set exit = { x, y, z, yaw } (relative to its origin)") return nil end
    local class = StaticFindObject(TELEPORTER_CLASS)
    if not (class and class:IsValid()) then return nil end
    local loc = { X = def.origin[1] + def.exit[1], Y = def.origin[2] + def.exit[2], Z = def.origin[3] + def.exit[3] }
    local pad = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = def.exit[4], Roll = 0.0 })
    if not (pad and pad:IsValid()) then log("vignette: could not spawn the exit pad for " .. def.id) return nil end
    pad.MyTeleporterID = FName(exit_pad_id(def))
    pad.DestinationTeleporterID = FName(default_return(def) or "None")
    pcall(function() pad.WorldFlagToTriggerOnUse = flag_handle(completion_flag(def)) end)
    pad.IsTeleporterActive = true
    pcall(function() pad:OnRep_IsTeleporterActive() end)
    apply_design(pad, DEFAULT_DESIGN)
    local okR, set = pcall(function() return pad.WorldFlagToTriggerOnUse.RowName:ToString() end)
    log(string.format("vignette: exit pad %s at %.0f, %.0f, %.0f, returns to %s, sets flag %s", exit_pad_id(def), loc.X, loc.Y, loc.Z,
        default_return(def) or "nowhere yet", okR and set or "?"))
    return pad
end

-- point the world's vignette zone at the completion flag, so the game applies portal sickness until the proper exit is used
local function apply_vignette_type(world, def)
    if world_type(def) ~= "vignette" then return end
    if not ensure_flag_row(def) then return end
    local name = completion_flag(def)
    for _, z in ipairs(FindAllOf("Vignette_Zone_C") or {}) do
        if z:IsValid() then
            local ok, dx, dy = pcall(function() local l = z:K2_GetActorLocation(); return l.X - def.origin[1], l.Y - def.origin[2] end)
            if ok and dx * dx + dy * dy < 1000 * 1000 then
                local okC, cur = pcall(function() return z.PortalSicknessWorldFlag.RowName:ToString() end)
                if not (okC and cur == name) then
                    pcall(function() z.PortalSicknessWorldFlag = flag_handle(name) end)
                    local okB, back = pcall(function() return z.PortalSicknessWorldFlag.RowName:ToString() end)
                    log("vignette: " .. def.id .. "'s zone now waits for " .. tostring(okB and back or "?") .. " (portal sickness until the proper exit)")
                end
            end
        end
    end
    spawn_exit_pad(world, def)
end

local function spawn_zones(world, def)
    if def.vignette then spawn_zone(world, def, VIGNETTE_ZONE, "Vignette_Zone_C", "vignette zone") end
    if world_leyak_safe(def) then spawn_zone(world, def, LEYAK_ZONE, "LeyakSafetyZone_C", "Leyak safety zone") end
    if def.vignette then apply_vignette_type(world, def) end
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
                spawn_zones(world, def)
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
                spawn_zones(world, def)
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

-- ---------------------------------------------------------------- presence tracker: vignette status, lighting, fall rescue, saved-inside rescue
-- A world's levels are streamed in far from the Facility, but the game's own level tracking never notices them, so it keeps treating the
-- player as being in the Facility level they came from (weather, lighting, respawn options). About twice a second the hub checks whether
-- the local player is inside one of the custom worlds (sideways distance from the world's origin under its radius) and:
--   * on arrival in a vignette world (the default): marks the player as being in that world's own entry of the game's level table, so the
--     game itself treats it as a vignette (no weather, the Portal Entrance respawn option leads to the world's arrival pad) and lights it
--     with the world's lighting rows, showing its title (see "vignette status" below); this is put back when the player leaves;
--   * if the world has a `lighting` block: then switches the game's automatic lighting off and applies those values on top, and hands
--     control back when the player leaves;
--   * if the world is ready and has `killZ`: sends a player who falls below origin z + killZ back to the world's arrival pad;
--   * if the world is NOT ready (for example a save was loaded while standing in it, or its pak was removed): sends the player to the
--     portal room instead of letting them fall through the missing level forever.
local TRACK_MS = 500
local EXIT_FORWARD, EXIT_UP = 215.1, 127.5          -- where the game puts a player who comes out of a pad (findings/portal-hub-findings.md)
local presence = { running = false, lit = nil, saved = nil, lastNote = 0, cleaned = false, held = nil,
                   inside = nil, claim = nil, lightAt = nil, reclaimAt = 0 }

local cachedPc = nil
local function local_pawn()
    local pc = cachedPc
    if not (pc and pc:IsValid()) then
        pc = FindFirstOf("Abiotic_PlayerController_C")       -- only searched for again when the old one is gone (a new world)
        cachedPc = pc
    end
    if not (pc and pc:IsValid()) then return nil, nil end
    local pawn = pc.Pawn
    if pawn and pawn:IsValid() then return pawn, pc end
    return nil, pc
end

local function lighting_parts()
    local sunA, skyA, fogA = FindFirstOf("DirectionalLight"), FindFirstOf("SkyLight"), FindFirstOf("ExponentialHeightFog")
    local function comp(a, prop)
        if a and a:IsValid() then
            local c = a[prop]
            if c and c:IsValid() then return c end
        end
        return nil
    end
    return (sunA and sunA:IsValid()) and sunA or nil, comp(sunA, "LightComponent"), comp(skyA, "LightComponent"), comp(fogA, "Component")
end

local function is_night()
    local mgr = FindFirstOf("DayNightManager_C")
    if mgr and mgr:IsValid() then
        local ok, v = pcall(function() return mgr.IsNight end)
        if ok then return v == true end
    end
    return false
end

local function apply_lighting(def, pc)
    local L = def.lighting
    local sunA, sunC, skyC, fogC = lighting_parts()
    if not presence.saved then
        presence.saved = { disable = false }
        pcall(function() presence.saved.disable = pc.DisableAutomaticFX end)
        if sunA then pcall(function() local r = sunA:K2_GetActorRotation(); presence.saved.rot = { Pitch = r.Pitch, Yaw = r.Yaw, Roll = r.Roll } end) end
    end
    pcall(function() pc.DisableAutomaticFX = true end)
    if L.sun and sunC then pcall(function() sunC:SetIntensity(L.sun) end) end
    if L.sunColor and sunC then pcall(function() sunC:SetLightColor({ R = L.sunColor[1], G = L.sunColor[2], B = L.sunColor[3], A = 1.0 }, true) end) end
    if L.sunPitch and sunA then
        local yaw = presence.saved.rot and presence.saved.rot.Yaw or 0.0
        pcall(function() sunA:K2_SetActorRotation({ Pitch = L.sunPitch, Yaw = yaw, Roll = 0.0 }, false) end)
    end
    if L.sky and skyC then pcall(function() skyC:SetIntensity(L.sky); skyC:RecaptureSky() end) end
    if L.fog and fogC then pcall(function() fogC:SetFogDensity(L.fog) end) end
    log("lighting: inside " .. def.id .. ", its lighting is applied (the game's automatic lighting is off)")
end

-- Hands lighting back to the game. When the world's level entry is also being put back, that switches the lighting rows itself, so the
-- extra update is skipped (refresh = false).
local function restore_lighting(pc, why, refresh)
    local saved = presence.saved
    if not saved then return end
    presence.saved = nil
    pcall(function() pc.DisableAutomaticFX = saved.disable or false end)
    -- let the game apply the values it holds for the current time of day, then put the sun back where it was
    local okU = true
    if refresh ~= false then okU = pcall(function() pc:UpdateToNewEnvironmentFX(not is_night(), 1.0) end) end
    local sunA = lighting_parts()
    if sunA and saved.rot then pcall(function() sunA:K2_SetActorRotation(saved.rot, false) end) end
    log("lighting: " .. why .. ", the game's own lighting is back" .. (okU and "" or " (its update call failed; it will refresh on the next change)"))
end

-- ---------------------------------------------------------------- vignette status through the game's own level table
-- Where the game thinks a player is comes from its level table, DT_Levels (rows of LevelMetadata_Struct: LevelFileName, IsVignette,
-- EntranceTeleporter, LevelFXRow_Day / LevelFXRow_Night, SectorName, ...). The player controller keeps the name of the current row in
-- ActiveLevelFXName; the game's vignette check (AbioticFunctionLibrary PlayerIsInVignette) and the respawn menu's Portal Entrance read that
-- row. A custom world has no row and the game's level tracking never reports it, so for each vignette world the hub:
--   * adds a row "PortalHub_<world id>" (in memory only, through UE4SS's data-table API) with IsVignette on, EntranceTeleporter = the world
--     id (its arrival pad), the world's lighting rows and its title;
--   * on arrival writes that row name into ActiveLevelFXName (a name property; never write ActiveLevelName, a string the game does not
--     use for this) and asks the controller to switch to the row's lighting with TransitionToNewEnvironmentFX. That call takes two
--     DataTableRowHandles (table + row name) and the title, which the game shows as the location banner; the weather's fog and
--     particles go with the old lighting rows;
--   * on leaving puts the previous row and the Facility's lighting rows back, unless the game has already moved on to a level by itself.
-- Never pass nil or made-up values to a soft-object parameter from Lua with this UE4SS build: it crashed the game inside UE4SS
-- (push_softobjectproperty) during the tests that found all this.
local LEVELS_TABLE = "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels"
local LEVEL_STRUCT = "/Game/Blueprints/Data/LevelMetadata_Struct.LevelMetadata_Struct"
local FX_TABLE = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"
local DEFAULT_LIGHTING_ROW = "HGarden"     -- Temple of Stone's lighting; used when a world names none (or one that does not exist)
local FALLBACK_LEVEL_ROW = "office1"       -- the portal room's level; used only when the previous row is unknown (mods restarted)
local ROW_PREFIX = "PortalHub_"

local function level_row_name(def) return ROW_PREFIX .. def.id end

local function name_prop(obj, prop)
    local ok, v = pcall(function() return obj[prop]:ToString() end)
    if ok and type(v) == "string" then return v end
    return nil
end

local function find_row(tablePath, row)
    local dt = StaticFindObject(tablePath)
    if not (dt and dt:IsValid()) then return nil end
    local ok, data = pcall(function() return dt:FindRow(row) end)
    if ok then return data end
    return nil
end

-- The title shown on entry: the map maker's WorldTitle on the loader Blueprint first, then a title from config.lua, then the portal name.
local function world_title(def)
    local fromWorld = loader_setting(def, "WorldTitle")
    if fromWorld then return fromWorld end
    if def.title then return def.title end
    for _, e in ipairs(state.entries) do
        if e.dest == def.id and e.name and e.name ~= e.dest then return e.name end
    end
    return def.id
end

-- the world's lighting rows, checked against the game's lighting table
local function world_light_rows(def)
    local day, night = def.lightingDay or DEFAULT_LIGHTING_ROW, def.lightingNight or def.lightingDay or DEFAULT_LIGHTING_ROW
    if find_row(FX_TABLE, day) == nil then
        log("vignette: lighting row '" .. day .. "' of " .. def.id .. " is not in the game's lighting table; using " .. DEFAULT_LIGHTING_ROW)
        day = DEFAULT_LIGHTING_ROW
    end
    if find_row(FX_TABLE, night) == nil then night = day end
    return day, night
end

local function level_fields()
    local names = {}
    local st = StaticFindObject(LEVEL_STRUCT)
    if st and st:IsValid() then
        pcall(function() st:ForEachProperty(function(p) local n = p:GetFName():ToString(); names[(n:gsub("_%d+_%x+$", ""))] = n end) end)
    end
    return names
end

local function ensure_level_row(def, day, night)
    local dt = StaticFindObject(LEVELS_TABLE)
    if not (dt and dt:IsValid()) then log("vignette: the game's level table is not loaded yet") return false end
    local rowName = level_row_name(def)
    if find_row(LEVELS_TABLE, rowName) ~= nil then return true end
    local f = level_fields()
    for _, k in ipairs({ "ReleaseGroup", "LevelFileName", "LevelFXRow_Day", "LevelFXRow_Night", "SectorName", "ResettablePortalWorld",
                         "HasFacilityShakes", "IsVignette", "EntranceTeleporter" }) do
        if not f[k] then log("vignette: the game's level table has no field " .. k .. " (game update?); " .. def.id .. " stays a Facility area") return false end
    end
    local fx = StaticFindObject(FX_TABLE)
    local row = {}
    row[f.ReleaseGroup] = 0
    row[f.LevelFileName] = FName(rowName)
    row[f.LevelFXRow_Day] = { DataTable = fx, RowName = FName(day) }
    row[f.LevelFXRow_Night] = { DataTable = fx, RowName = FName(night) }
    pcall(function() row[f.SectorName] = FText(world_title(def)) end)
    row[f.ResettablePortalWorld] = false
    row[f.HasFacilityShakes] = false
    row[f.IsVignette] = true
    row[f.EntranceTeleporter] = FName(def.id)
    local ok, err = pcall(function() dt:AddRow(rowName, row) end)
    if not ok or find_row(LEVELS_TABLE, rowName) == nil then
        log("vignette: could not add a level entry for " .. def.id .. ": " .. tostring(err):match("^[^\r\n]*"))
        return false
    end
    log(string.format("vignette: level entry %s added (vignette, entrance %s, lighting %s / %s, title '%s')", rowName, def.id, day, night, world_title(def)))
    return true
end

local function switch_lighting(pc, day, night, title)
    local fx = StaticFindObject(FX_TABLE)
    if not (fx and fx:IsValid()) then return false, "lighting table not loaded" end
    pcall(function() pc.DisableAutomaticFX = false end)
    return pcall(function()
        pc:TransitionToNewEnvironmentFX(false, { DataTable = fx, RowName = FName(day) }, { DataTable = fx, RowName = FName(night) }, 1.0, FText(title or ""))
    end)
end

local function claim_level(def, pc)
    -- the vignette zone (Buff_InVignette) may have been missing when the world loaded; it is only spawned if not there yet
    local world = UEHelpers.GetWorld()
    if world and world:IsValid() then spawn_zones(world, def) end
    local day, night = world_light_rows(def)
    if not ensure_level_row(def, day, night) then return false end
    local rowName = level_row_name(def)
    local prev = name_prop(pc, "ActiveLevelFXName")
    if prev and prev:sub(1, #ROW_PREFIX) == ROW_PREFIX then prev = nil end      -- ours from before a mod restart: unknown
    local okW = pcall(function() pc.ActiveLevelFXName = FName(rowName) end)
    if not okW then log("vignette: could not mark the player as being in " .. def.id) return false end
    local okT, err = switch_lighting(pc, day, night, world_title(def))
    -- the level's name as the game reports it (ActiveLevelName, a STRING property: write a Lua string, never an FName). In the game's own
    -- vignettes it holds the row's LevelFileName (V_ISLAND, H_Garden, ...), so ours holds the row name (also its LevelFileName).
    local prevName = name_prop(pc, "ActiveLevelName")
    if prevName and prevName:sub(1, #ROW_PREFIX) == ROW_PREFIX then prevName = nil end
    pcall(function() pc.ActiveLevelName = rowName end)
    presence.claim = { id = def.id, row = rowName, prev = prev, prevName = prevName, day = day, night = night }
    log(string.format("vignette: inside %s; the game now treats it as a vignette (level entry %s, was %s); lighting %s / %s: %s",
        def.id, rowName, tostring(prev), day, night, okT and "switched" or ("not switched (" .. tostring(err):match("^[^\r\n]*") .. ")")))
    return true
end

-- The Facility's lighting rows for a level row: the weather's rows while weather is on (the controller still holds the weather's name),
-- otherwise the level's own day / night rows.
local function facility_light_rows(pc, levelRow)
    local w = name_prop(pc, "ActiveWeatherFXName")
    if w and w ~= "None" and find_row(FX_TABLE, w) ~= nil then
        local wn = w .. "_Night"
        return w, (find_row(FX_TABLE, wn) ~= nil) and wn or w
    end
    local row = find_row(LEVELS_TABLE, levelRow)
    local f = level_fields()
    if row and f.LevelFXRow_Day and f.LevelFXRow_Night then
        local okD, d = pcall(function() return row[f.LevelFXRow_Day].RowName:ToString() end)
        local okN, n = pcall(function() return row[f.LevelFXRow_Night].RowName:ToString() end)
        if okD and okN then return d, n end
    end
    return nil
end

local function level_title(levelRow)
    local row = find_row(LEVELS_TABLE, levelRow)
    local f = level_fields()
    if row and f.SectorName then
        local ok, t = pcall(function() return row[f.SectorName]:ToString() end)
        if ok and type(t) == "string" then return t end
    end
    return ""
end

-- Put the level entry and the Facility's lighting back. `claim` may be nil when an entry of ours was left behind by a mod restart.
local function release_level(pc, why)
    local c = presence.claim
    presence.claim = nil
    local now = name_prop(pc, "ActiveLevelFXName")
    if not now or now:sub(1, #ROW_PREFIX) ~= ROW_PREFIX then
        if c then log("vignette: " .. why .. "; the game has already moved on to " .. tostring(now) .. ", nothing to put back") end
        return
    end
    local back = (c and c.prev) or FALLBACK_LEVEL_ROW
    pcall(function() pc.ActiveLevelFXName = FName(back) end)
    -- the level name back too: the one from before, or the file name of the level row being restored
    local nowName = name_prop(pc, "ActiveLevelName")
    if nowName and nowName:sub(1, #ROW_PREFIX) == ROW_PREFIX then
        local backName = c and c.prevName
        if not backName then
            local row, f = find_row(LEVELS_TABLE, back), level_fields()
            if row and f.LevelFileName then pcall(function() backName = row[f.LevelFileName]:ToString() end) end
        end
        if backName then pcall(function() pc.ActiveLevelName = backName end) end
    end
    local day, night = facility_light_rows(pc, back)
    local okT = false
    if day then okT = switch_lighting(pc, day, night, level_title(back)) end
    log(string.format("vignette: %s; level entry back to %s%s, lighting %s", why, back, (c and c.prev) and "" or " (previous one unknown)",
        day and ((day .. " / " .. night) .. (okT and "" or " (switch failed)")) or "left to the game"))
end

-- While inside: the game may set its own level entry again (for example after a respawn at the arrival pad), or switch to the weather's
-- lighting rows. Put ours back, at most every few seconds.
-- ---------------------------------------------------------------- on-screen messages
-- One short line at the top of the screen through the game's own player function (Client_DisplayWarningMessage: text, colour, beep).
-- Colours (the game's ECriticalityLevels): 0 green, 1 gray, 2 yellow, 3 red, 4 purple.
local MSG_GREEN, MSG_GRAY, MSG_YELLOW = 0, 1, 2
local function show(msg, colour)
    local pawn = local_pawn()
    if pawn then pcall(function() pawn:Client_DisplayWarningMessage(FText(msg), colour or MSG_GREEN, false) end) end
    log("message: " .. msg)
end

-- Is a vignette world's completion flag set in this world save? nil when it cannot be asked.
local function flag_is_set(def, pc)
    local fs = FindFirstOf("WorldFlagSubsystem")
    if not (fs and fs:IsValid()) then return nil end
    local ok, v = pcall(function() return fs:HasWorldFlag(pc, flag_handle(completion_flag(def))) end)
    if ok and type(v) == "boolean" then return v end
    return nil
end

-- Watch the completion flags of vignette worlds (every 2 s) and say when one gets set or cleared.
local flagSeen, flagCheckAt = {}, 0
local function watch_flags(pc)
    if os.clock() - flagCheckAt < 2 then return end
    flagCheckAt = os.clock()
    for _, def in pairs(worldDefs) do
        if def.vignette and world_type(def) == "vignette" then
            local now = flag_is_set(def, pc)
            local before = flagSeen[def.id]
            if now ~= nil and before ~= nil and now ~= before then
                if now then show(world_title(def) .. " completed: portal sickness lifted for good", MSG_GREEN)
                else show(world_title(def) .. "'s completion flag cleared", MSG_GRAY) end
            end
            if now ~= nil then flagSeen[def.id] = now end
        end
    end
end

local function keep_claim(def, pc)
    local c = presence.claim
    if not c or os.clock() - presence.reclaimAt < 3 then return end
    local now = name_prop(pc, "ActiveLevelFXName")
    local day = name_prop(pc, "Day_FX_Row")
    if now == c.row and (def.lighting or day == c.day) then return end
    presence.reclaimAt = os.clock()
    if now ~= c.row then
        pcall(function() pc.ActiveLevelFXName = FName(c.row) end)
        pcall(function() pc.ActiveLevelName = c.row end)
    end
    if not def.lighting and day ~= c.day then switch_lighting(pc, c.day, c.night, "") end
    log(string.format("vignette: the game changed %s inside %s; put back", now ~= c.row and ("the level entry to " .. tostring(now)) or ("the lighting to " .. tostring(day)), def.id))
end

-- where a pad puts the player who comes out of it
local function pad_exit(pad)
    local ok, x, y, z, yaw = pcall(function()
        local loc, fwd, rot = pad:K2_GetActorLocation(), pad:GetActorForwardVector(), pad:K2_GetActorRotation()
        return loc.X + fwd.X * EXIT_FORWARD, loc.Y + fwd.Y * EXIT_FORWARD, loc.Z + EXIT_UP, rot.Yaw
    end)
    if ok then return { X = x, Y = y, Z = z }, yaw end
    return nil
end

local function arrival_exit(def)
    for _, t in ipairs(all_pads()) do
        if pad_id(t) == def.id then return pad_exit(t) end
    end
    return nil
end

-- The portal room may not be streamed in yet (for example right after loading a save made inside a custom world), so its pads cannot be
-- relied on. Slot positions are fixed in slots.lua, so the exit point of a slot is computed from those numbers instead.
local function portal_room_exit()
    local slot = (state.entries[1] and state.entries[1].slot) or Slots.byId["A-3"]
    if not slot then return nil end
    local ok, x, y, z, yaw = pcall(function()
        local loc, yw = Slots.pose(slot)
        local rad = math.rad(yw)
        return loc.X + math.cos(rad) * EXIT_FORWARD, loc.Y + math.sin(rad) * EXIT_FORWARD, loc.Z + EXIT_UP, yw
    end)
    if ok then return { X = x, Y = y, Z = z }, yaw end
    return nil
end

local function send_player(pawn, loc, yaw)
    pcall(function() pawn.CharacterMovement:StopMovementImmediately() end)          -- no leftover fall speed
    local ok = pcall(function() return pawn:K2_TeleportTo(loc, { Pitch = 0.0, Yaw = yaw or 0.0, Roll = 0.0 }) end)
    return ok
end

local function note(msg)       -- rate-limited log line for things that can repeat every tick
    local now = os.clock()
    if now - presence.lastNote > 5 then presence.lastNote = now; log(msg) end
end

-- A world counts as ready when the hub says so, or when its level is already visible (for example the mods were restarted while the
-- player was standing in it, so the hub's own state is empty). In that case the hub adopts it.
local function world_is_ready(def)
    local st = worldState[def.id]
    if st and st.status == "ready" then return true end
    local world = UEHelpers.GetWorld()
    if world and world:IsValid() and loader_present(def) then
        local ls = find_streaming(world, def.level)
        local visible = false
        if ls then pcall(function() visible = ls:IsLevelVisible() end) end
        if visible then
            worldState[def.id] = { status = "ready", tries = 0 }
            spawn_arrival_pad(world, def)
            spawn_zones(world, def)
            set_portals_active(def.id, true)
            log("worlds: " .. def.id .. " was already loaded; adopted")
            return true
        end
    end
    return false
end

-- While a world is still loading and the player is standing in its area (a save made inside it was loaded), the player is held in
-- place (no gravity) instead of falling through the missing level, and set back down once the level is there.
local function hold_player(pawn, loc)
    local key = pawn:GetFName():ToString()
    if presence.held and presence.held.key == key then return end
    presence.held = { key = key, X = loc.X, Y = loc.Y, Z = loc.Z + 20 }
    pcall(function() pawn.CharacterMovement:StopMovementImmediately() end)
    pcall(function() pawn.CharacterMovement:SetMovementMode(0, 0) end)       -- MOVE_None: no gravity, no movement
    log("hold: the player is inside a world that is still loading; held in place until it is ready")
end

local function release_player(pawn)
    local h = presence.held
    presence.held = nil
    if not h then return end
    pcall(function() pawn:K2_TeleportTo({ X = h.X, Y = h.Y, Z = h.Z }, pawn:K2_GetActorRotation()) end)
    pcall(function() pawn.CharacterMovement:SetMovementMode(3, 0) end)       -- MOVE_Falling: lands on the floor and walks again
    log("hold: the world is ready; the player is back on the ground")
end

local function track_tick()
    local pawn, pc = local_pawn()
    if not pc then return end
    if not presence.cleaned then       -- a leftover from before a mod restart: the game's automatic lighting must not stay off
        presence.cleaned = true
        local stuck = false
        pcall(function() stuck = pc.DisableAutomaticFX == true end)
        if stuck then
            pcall(function() pc.DisableAutomaticFX = false; pc:UpdateToNewEnvironmentFX(not is_night(), 1.0) end)
            log("lighting: automatic lighting was left off; switched back on")
        end
    end
    watch_flags(pc)
    if not pawn then return end         -- dead, or between pawns: change nothing until there is a pawn again
    local okL, loc = pcall(function() return pawn:K2_GetActorLocation() end)
    if not okL or not loc then return end
    local here
    for _, def in pairs(worldDefs) do
        local dx, dy = loc.X - def.origin[1], loc.Y - def.origin[2]
        if dx * dx + dy * dy < def.radius * def.radius then here = def; break end
    end
    if not here then
        presence.held = nil
        if presence.inside or presence.claim or presence.lit then
            local id = presence.inside or presence.lit or (presence.claim and presence.claim.id) or "a custom world"
            presence.inside, presence.lightAt = nil, nil
            if presence.lit then
                restore_lighting(pc, "left " .. presence.lit, presence.claim == nil)
                presence.lit = nil
            end
            release_level(pc, "left " .. id)
        else
            -- a level entry of ours left behind by a mod restart: the player is outside every custom world, so give the game its own back
            local now = name_prop(pc, "ActiveLevelFXName")
            if now and now:sub(1, #ROW_PREFIX) == ROW_PREFIX then release_level(pc, "a leftover level entry " .. now .. " was found outside the custom worlds") end
        end
        return
    end
    if world_is_ready(here) then
        if presence.held then release_player(pawn) end
        if presence.inside ~= here.id then
            -- just arrived (or the mods were restarted while inside)
            presence.inside = here.id
            if here.vignette then claim_level(here, pc) end
            if here.vignette and world_type(here) == "vignette" and flag_is_set(here, pc) == false then
                show("Portal sickness: find " .. world_title(here) .. "'s proper exit to lift it", MSG_YELLOW)
            end
            -- a `lighting` block goes on top once the game has switched to the world's lighting rows (that takes about a second)
            presence.lightAt = here.lighting and (os.clock() + (presence.claim and 2.0 or 0.0)) or nil
        elseif here.vignette then
            keep_claim(here, pc)
        end
        if presence.lightAt and os.clock() >= presence.lightAt and presence.lit ~= here.id then
            presence.lightAt = nil
            apply_lighting(here, pc)
            presence.lit = here.id
        end
        if here.killZ and loc.Z < here.origin[3] + here.killZ then
            local dest, yaw = arrival_exit(here)
            if dest then
                send_player(pawn, dest, yaw)
                note(string.format("rescue: the player fell below z %.0f in %s and was returned to its arrival pad", here.origin[3] + here.killZ, here.id))
            end
        end
        return
    end
    local st = worldState[here.id]
    if st and st.status == "failed" then
        -- the world cannot load (its pak is missing or broken): do not leave the player in the void
        local wasHeld = presence.held ~= nil
        presence.held = nil
        pcall(function() pawn.CharacterMovement:SetMovementMode(3, 0) end)
        local dest, yaw = portal_room_exit()
        if dest then
            send_player(pawn, dest, yaw)
            note("rescue: " .. here.id .. " could not be loaded; the player was sent back to the portal room" .. (wasHeld and "" or " (they were inside its area)"))
        end
    else
        -- not loaded yet: start loading it now (it does not need the portal room) and hold the player until it is ready
        local world = UEHelpers.GetWorld()
        if not st and world and world:IsValid() then
            log("worlds: the player is inside the area of " .. here.id .. " before it was loaded; loading it now")
            start_world(world, here)
        end
        hold_player(pawn, loc)
    end
end

-- Dying inside a vignette world needs nothing extra: the respawn menu reads the level entry the player is marked as being in, and the
-- world's entry names its arrival pad as the Portal Entrance (see "vignette status" above).

local function start_tracker()
    if Config.tracker == false then log("tracker: switched off in config.lua (tracker = false)") return end
    if presence.running or next(worldDefs) == nil then return end
    presence.running = true
    local function loop()
        local ok, err = pcall(track_tick)
        if not ok then note("tracker error: " .. tostring(err):match("^[^\r\n]*")) end
        ExecuteWithDelay(TRACK_MS, function() ExecuteInGameThread(loop) end)
    end
    ExecuteWithDelay(TRACK_MS, function() ExecuteInGameThread(loop) end)
    log("tracker: watching " .. (function() local n = 0; for _ in pairs(worldDefs) do n = n + 1 end; return n end)() .. " custom world area(s)")
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
start_tracker()

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
















