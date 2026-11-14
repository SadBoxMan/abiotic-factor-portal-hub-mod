-- Portal Hub: lets modders connect worlds to the Homeworld portal room.
-- Reads Scripts/config.lua, spawns a teleporter pad into each configured slot whenever the world loads, routes the
-- return trip back through the portal the player came in by, and lowers the hub's portal hum as portals are added.
-- In someone else's game (no authority here) the hub stands down: the host's hub runs the portals, exits and worlds, and this one only sets
-- the hum (see "client mode" further down).
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

local state = { entries = {}, dests = {}, byId = {}, byManual = {}, byMhe = {}, hubMode = {}, acts = {}, hooked = false, pending = false }
local is_client             -- true on a joining player's machine (client mode, CRD-027); defined with the presence tracker below
local spawn_all             -- spawns the hub portals (defined at the end; the tracker also calls it, CRD-028)

-- Hub Exits (CRD-012): what a base-game world's own exits do for a hub portal leading to it. exitMode = ... sets modes 1-3 for every portal
-- ("game" if not set); exits = ... on a portal overrides it, and is the only way to choose mode 4. Numbers 1-4 work too.
--   game     1  the world's exits are the game's: the hub only takes players in
--   hub      2  the world's exits take everyone to the hub portal, however they came in
--   dynamic  3  per player: someone who came in through a hub portal leaves to it, someone who came the game's way leaves the game's way
-- MHEs (Manual Hub Exits, manual_exits.lua): every world with a recorded MHE also gets that exit portal on its own, unless config.lua switches
-- it off (mhe = { [arrival pad id] = false }). It leads to the first hub portal to that world (for the game's homes, such as the Cabin, their
-- own hub-room portal), or, if there is none, to the Failsafe Exit: a
-- hidden landing on the portal room's first floor in front of the door (manual_exits.lua failsafe = { x, y, z, yaw }, where the player stands).
-- A world whose hub portal uses mode 4 needs no extra MHE: that portal's manual portal is its MHE.
--   manual   4  the hub portal leads to the world's MHE (manual_exits.lua; a portal cannot carry its own spot: the hub portals are final) that
--               always leads back to the hub portal; the world's own exits stay the game's. manualBuffs = true also gives the buffs of the
--               world's true exit there (off by default: it makes the game much easier).
-- game, hub and dynamic exclude each other. Custom worlds always return to the hub through their arrival pad, so they have no mode.
local EXIT_MODE_NUMBERS = { "game", "hub", "dynamic", "manual" }
local EXIT_MODES = { game = true, hub = true, dynamic = true, manual = true }
local function exit_mode(v)
    if type(v) == "number" then v = EXIT_MODE_NUMBERS[v] end
    if type(v) == "string" and EXIT_MODES[v:lower()] then return v:lower() end
    return nil
end
local DEFAULT_EXIT_MODE = exit_mode(Config.exitMode) or "game"
if DEFAULT_EXIT_MODE == "manual" then DEFAULT_EXIT_MODE = "game" end      -- the global choice is modes 1-3 only (reported in resolve_config)
-- The MHEs (Manual Hub Exits, manual_exits.lua) are read again each time the hub portals are spawned, so one recorded with the lab's INSERT
-- is used after NUMPAD 1, without restarting the mods. The file itself is read (not require: UE4SS keeps a module it has loaded even after
-- package.loaded is cleared, 9 November); require is only the fallback when the file cannot be opened. mheKey says whether it changed.
local MHE_PATH = rawget(_G, "PORTALHUB_MHE_PATH") or "ue4ss/Mods/PortalHub/Scripts/manual_exits.lua"   -- relative to UE4SS's working folder
local MANUAL_EXITS, mheKey = {}, nil
local function load_manual_exits()
    local t = nil
    local f = io.open(MHE_PATH, "rb")
    if f then
        local text = f:read("*a")
        f:close()
        local chunk = load(text, "=manual_exits.lua")
        local ok, r = pcall(chunk or error)
        if ok and type(r) == "table" then t = r end
    end
    if not t then
        package.loaded["manual_exits"] = nil
        local ok, r = pcall(require, "manual_exits")
        t = (ok and type(r) == "table") and r or {}
    end
    local keys = {}
    for k, v in pairs(t) do
        if type(v) == "table" then keys[#keys + 1] = tostring(k) .. "=" .. table.concat({ tostring(v[1]), tostring(v[2]), tostring(v[3]), tostring(v[4]) }, ",") end
    end
    table.sort(keys)
    MANUAL_EXITS = t
    local key = table.concat(keys, ";")
    local changed = mheKey ~= nil and key ~= mheKey
    mheKey = key
    return changed, #keys
end
load_manual_exits()
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
            local world = worldDefs[p.destination]
            local mode, manual = nil, nil
            if not world then
                mode = DEFAULT_EXIT_MODE
                if p.exits ~= nil then
                    mode = exit_mode(p.exits)
                    if not mode then
                        log("config entry " .. i .. ": unknown exits '" .. tostring(p.exits) .. "', using \"" .. DEFAULT_EXIT_MODE .. "\"")
                        mode = DEFAULT_EXIT_MODE
                    end
                end
                if mode == "manual" then
                    local function spot(m)
                        if type(m) == "table" and tonumber(m[1]) and tonumber(m[2]) and tonumber(m[3]) then
                            return { tonumber(m[1]), tonumber(m[2]), tonumber(m[3]), tonumber(m[4]) or 0.0 }
                        end
                        return nil
                    end
                    if p.manual ~= nil then
                        log("config entry " .. i .. ": manual is ignored: a hub portal has no spot of its own; edit the MHE of " .. p.destination .. " in manual_exits.lua")
                    end
                    manual = spot(MANUAL_EXITS[p.destination])
                    if not manual then
                        log("config entry " .. i .. ": exits = \"manual\", but " .. p.destination .. " has no manual portal yet (manual_exits.lua); using \"game\"")
                        mode = "game"
                    end
                end
            elseif p.exits ~= nil then
                log("config entry " .. i .. ": " .. p.destination .. " is a custom world, which always returns to the hub; exits ignored")
            end
            if mode ~= "manual" then dests[p.destination] = true end
            entries[#entries + 1] = {
                slot = slot,
                name = p.name or p.destination,
                dest = p.destination,
                design = p.design or DEFAULT_DESIGN,
                world = worldDefs[p.destination],
                lightColor = lc,
                lightBrightness = lb,
                id = ID_PREFIX .. (p.slot:gsub("-", "")),
                exits = mode,
                manual = manual,
                manualBuffs = mode == "manual" and p.manualBuffs == true,
            }
            local e = entries[#entries]
            if manual then e.manualId = e.id .. "_manual" end
        end
    end
    local byId, byManual, hubMode, acts = {}, {}, {}, {}
    for _, e in ipairs(entries) do
        byId[e.id] = e
        if e.manualId then byManual[e.manualId] = e end
        if e.exits == "hub" and not hubMode[e.dest] then hubMode[e.dest] = e.id end
        if e.exits == "hub" or e.exits == "dynamic" then acts[e.dest] = true end
    end
    state.entries, state.dests, state.byId, state.byManual, state.hubMode, state.acts = entries, dests, byId, byManual, hubMode, acts
    if Config.exitMode ~= nil and not exit_mode(Config.exitMode) then log("config: unknown exitMode '" .. tostring(Config.exitMode) .. "', using \"game\"") end
    if exit_mode(Config.exitMode) == "manual" then log("config: exitMode is for modes 1-3 (game, hub, dynamic); \"manual\" is chosen per portal; using \"game\"") end
end

-- A destroyed actor is still found (and IsValid) until the frame ends, so apply_hum, which runs in the same call, skips the pads destroyed here
-- (after Restart All Mods it counted 20 hub pads for 10: CRD-028). Keyed by address: each FindAllOf hands out new Lua objects.
local doomed = {}
local function obj_key(t)
    local ok, a = pcall(function() return t:GetAddress() end)
    if ok and a then return a end
    return t
end

local function destroy_hub_pads()
    local n = 0
    doomed = {}
    for _, t in ipairs(all_pads()) do
        local id = pad_id(t)
        if id and is_hub_id(id) then doomed[obj_key(t)] = true; t:K2_DestroyActor(); n = n + 1 end
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
        if id and (is_hub_id(id) or Slots.baseEntrances[id]) and not doomed[obj_key(t)] then
            pcall(function()
                local h = t.PortalHumLoop
                if h and h:IsValid() then h:SetVolumeMultiplier(mult); touched = touched + 1 end
            end)
        end
    end
    doomed = {}              -- only good for the call that destroyed them (a freed address can be used again later)
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
-- config.worlds[<arrival pad id>] = { loaderAsset, loaderClass, level, origin = { x, y, z }, arrive = { x, y, z, yaw } (optional) }
-- The world's own settings (title, type, arrival spot, ...) are best set on its loader Blueprint; see apply_world_settings.
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
        ok = ok and type(w.origin) == "table" and #w.origin >= 3
        ok = ok and (w.arrive == nil or (type(w.arrive) == "table" and #w.arrive >= 3))     -- optional: ArriveSpot on the loader Blueprint
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
            local lightDay, lightNight, nightOwn = nil, nil, false
            if type(w.lightingFrom) == "string" and w.lightingFrom ~= "" then
                lightDay, lightNight = w.lightingFrom, w.lightingFrom
            elseif type(w.lightingFrom) == "table" then
                lightDay = type(w.lightingFrom.day) == "string" and w.lightingFrom.day or nil
                nightOwn = type(w.lightingFrom.night) == "string"
                lightNight = nightOwn and w.lightingFrom.night or lightDay
            end
            worldDefs[id] = {
                id = id, loaderAsset = w.loaderAsset, loaderClass = w.loaderClass, level = w.level,
                origin = { tonumber(w.origin[1]) or 0, tonumber(w.origin[2]) or 0, tonumber(w.origin[3]) or 0 },
                arrive = w.arrive and { tonumber(w.arrive[1]) or 0, tonumber(w.arrive[2]) or 0, tonumber(w.arrive[3]) or 0, tonumber(w.arrive[4]) or 0 }
                    or { 0, 0, 0, 0 },                       -- default: the arrival pad at origin, facing +X
                lighting = lighting,
                radius = tonumber(w.radius) or 100000,       -- how far (sideways) from origin counts as "inside this world"
                killZ = tonumber(w.killZ),                   -- optional: below origin z + killZ the player is returned to the arrival pad
                vignette = (w.vignette ~= false),            -- default on: the world counts as a vignette (no weather); vignette = false opts out
                title = type(w.title) == "string" and w.title ~= "" and w.title or nil,   -- shown by the game on arrival; default: the portal's name
                leyakSafe = w.leyakSafe,                     -- true / false / nil: Leyak safety zone; default on (see world_leyak_safe)
                type = type(w.type) == "string" and w.type or nil,  -- "home" (default) or "vignette" (see world_type)
                exit = (type(w.exit) == "table" and #w.exit >= 3) and { tonumber(w.exit[1]) or 0, tonumber(w.exit[2]) or 0,
                    tonumber(w.exit[3]) or 0, tonumber(w.exit[4]) or 0 } or nil,  -- a vignette's proper exit, relative to origin: x, y, z, yaw
                lightingDay = lightDay, lightingNight = lightNight, cfgNightOwn = nightOwn,
            }
            -- Every setting above except origin can also come from the world's loader Blueprint, which wins (apply_world_settings).
            if is_hub_id(id) then log("worlds: '" .. id .. "' starts with a reserved prefix and may be removed with the hub portals; rename it") end
        else
            log("worlds: entry '" .. tostring(id) .. "' is incomplete (needs loaderAsset, loaderClass, level, origin = {x,y,z}; arrive, if given, = {x,y,z,yaw}), ignored")
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

-- World settings made by the map maker live on the world's own loader Blueprint, as plain variables (text, name, boolean, float,
-- vector) on its class defaults, so a world describes itself and needs no hub configuration beyond its slot and its place in hub space.
-- Read-only; never soft or asset references (see the crash rule in docs/handoff.md). Each reader returns nil when the variable is
-- missing (or, for text, empty). The full list is in docs/world-settings.md.
local function loader_cdo(def)
    local cdo = StaticFindObject(def.loaderAsset .. ".Default__" .. def.loaderClass)     -- the class defaults object
    if not (cdo and cdo:IsValid()) then
        local cls = StaticFindObject(def.loaderAsset .. "." .. def.loaderClass)
        if cls and cls:IsValid() then pcall(function() cdo = cls:GetCDO() end) end
    end
    if cdo and cdo:IsValid() then return cdo end
    return nil
end

-- a Text, Name or String variable
local function loader_setting(def, var)
    local cdo = loader_cdo(def)
    if not cdo then return nil end
    local ok, v = pcall(function() return cdo[var]:ToString() end)
    if ok and type(v) == "string" and v ~= "" and v ~= "None" then return v end
    return nil
end

-- a Boolean variable
local function loader_flag(def, var)
    local cdo = loader_cdo(def)
    if not cdo then return nil end
    local ok, v = pcall(function() return cdo[var] end)
    if ok and type(v) == "boolean" then return v end
    return nil
end

-- a Float (or Integer) variable
local function loader_number(def, var)
    local cdo = loader_cdo(def)
    if not cdo then return nil end
    local ok, v = pcall(function() return cdo[var] end)
    if ok and type(v) == "number" and v == v then return v end      -- v == v: not NaN
    return nil
end

-- a Vector variable, as { x, y, z }
local function loader_vector(def, var)
    local cdo = loader_cdo(def)
    if not cdo then return nil end
    local ok, x, y, z = pcall(function() local v = cdo[var]; return v.X, v.Y, v.Z end)
    if ok and type(x) == "number" and type(y) == "number" and type(z) == "number" then return { x, y, z } end
    return nil
end

-- Lay the loader Blueprint's values over the ones resolve_worlds took from config.lua (or the defaults): the Blueprint wins. Done once the
-- loader's class is in memory (it is loaded with the world); until then config.lua and the defaults apply. Returns true once done.
local function apply_world_settings(def)
    if def.settled then return true end
    if not loader_cdo(def) then return false end
    def.settled = true
    local got = {}
    local function take(var, key, v)
        if v == nil then return end
        def[key] = v
        got[#got + 1] = var .. "=" .. (type(v) == "table" and ("{" .. table.concat(v, ", ") .. "}") or (type(v) == "string" and ("'" .. v .. "'") or tostring(v)))
    end
    take("WorldTitle", "title", loader_setting(def, "WorldTitle"))
    take("WorldType", "type", loader_setting(def, "WorldType"))
    take("LeyakSafeZone", "leyakSafe", loader_flag(def, "LeyakSafeZone"))
    take("NoWeather", "vignette", loader_flag(def, "NoWeather"))
    local day, night = loader_setting(def, "LightingDay"), loader_setting(def, "LightingNight")
    take("LightingDay", "lightingDay", day)
    take("LightingNight", "lightingNight", night)
    if day and not night and not def.cfgNightOwn then def.lightingNight = day end     -- a day row alone lights the night too
    local killZ = loader_number(def, "KillZ")
    if killZ == 0 then def.killZ = nil; got[#got + 1] = "KillZ=0 (off)" else take("KillZ", "killZ", killZ) end
    local radius = loader_number(def, "Radius")
    if radius and radius > 0 then take("Radius", "radius", radius) end
    local spot, yaw = loader_vector(def, "ArriveSpot"), loader_number(def, "ArriveYaw")
    if spot or yaw then
        local a = def.arrive
        take("ArriveSpot/ArriveYaw", "arrive", { spot and spot[1] or a[1], spot and spot[2] or a[2], spot and spot[3] or a[3], yaw or a[4] })
    end
    spot, yaw = loader_vector(def, "ExitSpot"), loader_number(def, "ExitYaw")
    if spot then take("ExitSpot/ExitYaw", "exit", { spot[1], spot[2], spot[3], yaw or (def.exit and def.exit[4]) or 0 }) end
    log("worlds: " .. def.id .. " settings from its loader Blueprint: " .. (#got > 0 and table.concat(got, ", ") or "none (config.lua and defaults)"))
    return true
end

local function world_leyak_safe(def)
    apply_world_settings(def)
    if def.leyakSafe == false then return false end
    return true
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
    apply_world_settings(def)
    local v = (def.type or "home"):lower()
    if v ~= "vignette" then v = "home" end
    return v
end

local function completion_flag(def) return "PortalHub_" .. def.id .. "_Completed" end
local function exit_pad_id(def) return def.id .. "_exit" end

-- a story-flag handle (the native WorldFlagRowHandle since v1.5.0: only the row name is ours to set)
local function flag_handle(name) return { RowName = FName(name) } end

-- Load a data table the game has not loaded yet; the table, or nil. UE4SS's LoadAsset loads it from the object path (".../DT_X.DT_X"); the
-- package path alone loaded nothing in game (CRD-022), so it is only tried second. Game thread only (all callers run there).
local function load_table(path)
    local dt = StaticFindObject(path)
    for _, try in ipairs({ path, (path:gsub("%.[^%.]*$", "")) }) do
        if dt and dt:IsValid() then return dt end
        pcall(LoadAsset, try)
        dt = StaticFindObject(path)
    end
    if dt and dt:IsValid() then return dt end
    return nil
end

local function ensure_flag_row(def)
    local dt = StaticFindObject(WORLD_FLAGS_TABLE)
    if not (dt and dt:IsValid()) then
        dt = load_table(WORLD_FLAGS_TABLE)
        if dt then log("vignette: the game's story-flag table was not loaded yet; loaded it") end
    end
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

local STALE_S = 10      -- a world check loop or the tracker that has not run for this long (os.clock seconds) was dropped; NUMPAD 1 restarts it

-- What the presence tracker (further down) knows about where the player is. inside, claim, lit, saved, lightAt and held all describe the
-- map that was loaded when they were set; forget_old_map clears them.
local presence = { running = false, lit = nil, saved = nil, lastNote = 0, cleaned = false, held = nil,
                   inside = nil, claim = nil, lightAt = nil, reclaimAt = 0, claimRetryAt = nil, claimTries = 0 }

-- This Lua state outlives map loads: after quitting to the menu and loading a save, worldState still says "ready" and presence still says
-- "inside", though the levels and the controller they meant are gone. A world's loader is a Level Instance actor, which lives exactly as long
-- as its level, so a world with a state but no loader belongs to the old map. Everything is cleared at once (the first one found means the
-- map changed), so the tracker claims the world again exactly once and the normal load and hold run. Returns true if it found old state.
local function forget_old_map()
    local stale = 0
    for id, st in pairs(worldState) do
        if st.status ~= "failed" and not loader_present(worldDefs[id]) then
            worldState[id] = nil
            stale = stale + 1
        end
    end
    if stale == 0 then return false end
    presence.inside, presence.claim, presence.lit, presence.saved, presence.lightAt, presence.held = nil, nil, nil, nil, nil, nil
    presence.claimRetryAt, presence.claimTries = nil, 0
    log("worlds: a new map was loaded; " .. stale .. " world(s) start over")
    return true
end

-- One look at one world that is loading. The caller (world_checks_tick) keeps it going until it is ready or failed.
local function poll_world(def, st)
    st.tries = st.tries + 1
    local world = st.world
    if not world:IsValid() then
        log("worlds: " .. def.id .. ": the game world changed while loading; starting over")
        worldState[def.id] = nil       -- not "failed": the tracker would send a player standing in it to the portal room
        forget_old_map()
        return
    end
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
            if is_client() then         -- CRD-027: loaded here only so the level is there to stand on; its pads, zones and portals are the host's
                log(string.format("worlds: %s is ready after %.1f s (client mode: loaded on this machine only; its pads and zones are the host's)", def.id, st.tries * WORLD_POLL_MS / 1000))
                return
            end
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
    end
end

-- Every world that is loading is checked in one callback. Five worlds used to mean five timer chains on top of the tracker's, and UE4SS
-- dropped its whole game-tick hook during such a burst (findings/game-update-2026-10.md, fault 2). Returns true while any world is loading.
local function world_checks_tick()
    local more = false
    for id, st in pairs(worldState) do
        if st.status == "loading" then
            local ok, err = pcall(poll_world, worldDefs[id], st)
            if not ok and st.tries % 20 == 1 then log("worlds: " .. id .. " check error: " .. tostring(err):match("^[^\r\n]*")) end
            if worldState[id] == st and st.status == "loading" then more = true end
        end
    end
    return more
end

-- Starts the shared loop if it is not running, or again if its timer was dropped (UE4SS can lose queued timers). Like the tracker's loop it
-- has a generation number, so only the newest copy keeps running.
local worldLoop = { running = false, gen = 0, lastTick = 0 }
local function run_world_checks()
    if worldLoop.running then
        if os.clock() - worldLoop.lastTick <= STALE_S then return end
        log("worlds: the loading check stopped running; starting it again")
    end
    worldLoop.running = true
    local gen = worldLoop.gen + 1
    worldLoop.gen, worldLoop.lastTick = gen, os.clock()
    local function loop()
        if worldLoop.gen ~= gen then return end
        worldLoop.lastTick = os.clock()
        if world_checks_tick() then
            ExecuteWithDelay(WORLD_POLL_MS, function() ExecuteInGameThread(loop) end)
        else
            worldLoop.running = false
        end
    end
    ExecuteWithDelay(WORLD_POLL_MS, function() ExecuteInGameThread(loop) end)
end

local function start_world(world, def)
    local st = { status = "loading", tries = 0, world = world }
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
    apply_world_settings(def)
    run_world_checks()
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
            if not st or st.status == "failed" then
                start_world(world, def)
            elseif st.status == "loading" then
                run_world_checks()                -- restarts the loop if its timer was dropped
            elseif st.status == "ready" then
                spawn_arrival_pad(world, def)
                spawn_zones(world, def)
                set_portals_active(def.id, true)
            end
        end
    end
end
-- Exit mode "manual": the portal placed in the world. It leads back to its hub portal, always (nothing ever rewrites it).
local function spawn_manual(world, class, e)
    local m = e.manual
    local pad = world:SpawnActor(class, { X = m[1], Y = m[2], Z = m[3] }, { Pitch = 0.0, Yaw = m[4], Roll = 0.0 })
    if not pad or not pad:IsValid() then log(e.slot.id .. ": could not spawn the manual portal") return end
    pad.MyTeleporterID = FName(e.manualId)
    pad.DestinationTeleporterID = FName(e.id)
    pad.IsTeleporterActive = true
    pcall(function() pad:OnRep_IsTeleporterActive() end)
    apply_design(pad, e.design)
    apply_light(pad, e)
    log(string.format("%s: manual portal %s at %.0f, %.0f, %.0f facing %.0f in %s, leads back to %s%s", e.slot.id, e.manualId, m[1], m[2], m[3], m[4],
        e.dest, e.id, e.manualBuffs and " (gives the true exit's buffs)" or ""))
end

local function spawn_entry(world, class, e)
    local loc, yaw = Slots.pose(e.slot)
    local actor = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    if not actor or not actor:IsValid() then log(e.slot.id .. ": SpawnActor failed") return false end
    actor.MyTeleporterID = FName(e.id)
    actor.DestinationTeleporterID = FName(e.manualId or e.dest)
    local waiting = e.world and not (worldState[e.world.id] and worldState[e.world.id].status == "ready")
    actor.IsTeleporterActive = not waiting          -- a portal to a custom world stays off until that world has loaded
    pcall(function() actor:OnRep_IsTeleporterActive() end)
    e.actor = actor
    apply_design(actor, e.design)
    apply_light(actor, e)
    log(string.format("%s: '%s' -> %s (pad %s)", e.slot.id, e.name, e.dest, e.id))
    if e.exits then log(string.format("%s: exits: %s", e.slot.id, e.exits)) end
    if e.manualId then spawn_manual(world, class, e) end
    return true
end

-- The arrival pad of a custom world only has one destination, so before any pad that leads to it is used we point that arrival pad back at
-- the pad being used. Base-game worlds are left alone: what their pads do is the portal's exit mode (Hub Exits, below).
local function route_return(pad)
    local ok, err = pcall(function()
        local dest = pad.DestinationTeleporterID:ToString()
        if not state.dests[dest] or not worldDefs[dest] then return end
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
-- A vignette claim that failed (level table not loaded yet) is tried again this often for as long as the player stays inside: on a fresh game
-- start the table took over 10 s (CRD-022). The first CLAIM_TRIES tries log why they failed; after that one line every CLAIM_TRIES tries.
local CLAIM_RETRY_S, CLAIM_TRIES = 1.0, 10
local claimQuiet = false                           -- true while a quiet retry runs: ensure_level_row does not log why it failed
local EXIT_FORWARD, EXIT_UP = 215.1, 127.5          -- where the game puts a player who comes out of a pad (findings/portal-hub-findings.md)

-- The player controller of this machine's player. On a host every player has a controller, so the first one found may be a client's
-- (CRD-023): the one that says IsLocalController wins. It is remembered (and only searched for again when it is gone, in a new world) once
-- it has said so; a controller that cannot be asked is used, but not remembered.
local cachedPc = nil
local function find_local_pc()
    local first = nil
    for _, pc in ipairs(FindAllOf("Abiotic_PlayerController_C") or {}) do
        if pc:IsValid() then
            first = first or pc
            local ok, isLocal = pcall(function() return pc:IsLocalController() end)
            if ok and isLocal == true then return pc, true end
        end
    end
    if first then return first, false end
    local pc = FindFirstOf("Abiotic_PlayerController_C")
    if pc and pc:IsValid() then return pc, false end
    return nil, false
end

local function local_pawn()
    local pc = cachedPc
    if not (pc and pc:IsValid()) then
        local sure
        pc, sure = find_local_pc()
        cachedPc = sure and pc or nil
    end
    if not (pc and pc:IsValid()) then return nil, nil end
    local pawn = pc.Pawn
    if pawn and pawn:IsValid() then return pawn, pc end
    return nil, pc
end

-- ---------------------------------------------------------------- client mode (CRD-027)
-- Every machine with the hub installed runs this file. Where this machine's own controller has no authority (a player who joined someone
-- else's game), the host's hub already runs what matters to the game: its portals replicate to every player (without their IDs and
-- destinations, run 1), and its AttemptTeleport hook sees every player's pad use. So a joining player's hub stands down: it spawns and
-- destroys no pads, moves no one (no exit moves, route_return, buffs, fall rescue or hold), spawns no zones or arrival pads, and only does
-- what is local by nature: the hum volume of the hub portals it sees (from its own config, counting the host's portals that are really
-- there), its own look on a host portal that leads where its own portal in that slot does, the vignette lighting on its own screen, and the
-- custom worlds' levels: the host's loaders never reach a client (run 1, 10 November), so a client loads a world itself when the host's
-- teleport puts it in that world's area, and ahead of time where the host has a portal in a slot its own config fills with that world (a
-- guess). clientMode = false in config.lua switches this off, for comparison runs: the hub then acts as it did before (a whole second hub).
local CLIENT_MODE = Config.clientMode ~= false
local ROLE_AUTHORITY = 3                  -- ENetRole: 1 simulated proxy, 2 autonomous proxy (a client's own controller), 3 authority

-- "host" (also a game on its own), "client", or nil while this machine has no player controller yet. A controller whose authority cannot be
-- read counts as the host, which is what the hub always assumed before client mode.
local function net_role()
    local _, pc = local_pawn()
    if not pc then return nil end
    local ok, a = pcall(function() return pc:HasAuthority() end)
    if ok and type(a) == "boolean" then return a and "host" or "client" end
    local okR, r = pcall(function() return pc:GetLocalRole() end)
    if okR and type(r) == "number" then return (r == ROLE_AUTHORITY) and "host" or "client" end
    return "host"
end

is_client = function() return CLIENT_MODE and net_role() == "client" end

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
-- Where the game thinks a player is comes from its level table, DT_Levels (rows of LevelMetadata: IsVignette, EntranceTeleporter,
-- LevelFXRow_Day / LevelFXRow_Night, SectorName, ...). Game update v1.5.0 (27 October 2026) made that row struct native
-- (/Script/AbioticFactor.LevelMetadata, plain field names) and swapped the old LevelFileName (a name) for Level, a soft-object field the
-- hub never writes (crash rule below; UE4SS's AddRow leaves fields missing from the Lua table at their defaults). The hub reads the
-- struct from the table itself (DT_Levels.RowStruct) so it survives another move. The player controller keeps the name of the current row in
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
-- the level row struct's known homes, used only when DT_Levels.RowStruct cannot be read: native since v1.5.0, a Blueprint struct before
local LEVEL_STRUCTS = { "/Script/AbioticFactor.LevelMetadata", "/Game/Blueprints/Data/LevelMetadata_Struct.LevelMetadata_Struct" }
local FX_TABLE = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"
local DEFAULT_LIGHTING_ROW = "Intro"       -- the game's intro lighting (bright sun and sky, no fog); used when a world names none (or one that does not exist)
local FALLBACK_LEVEL_ROW = "office1"       -- the portal room's level; used only when the previous row is unknown (mods restarted)
local FALLBACK_LEVEL_NAME = "Facility_Office1"   -- its level name (ActiveLevelName), for rows that no longer carry LevelFileName
local ROW_PREFIX = "PortalHub_"

local function level_row_name(def) return ROW_PREFIX .. def.id end

local function name_prop(obj, prop)
    local ok, v = pcall(function() return obj[prop]:ToString() end)
    if ok and type(v) == "string" then return v end
    return nil
end

-- A row handle property such as the controller's Day_FX_Row (a LevelFXRowHandle struct since v1.5.0): the row name inside it.
local function row_handle_name(obj, prop)
    local ok, v = pcall(function() return obj[prop].RowName:ToString() end)
    if ok and type(v) == "string" then return v end
    return name_prop(obj, prop)
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
    apply_world_settings(def)
    if def.title then return def.title end
    for _, e in ipairs(state.entries) do
        if e.dest == def.id and e.name and e.name ~= e.dest then return e.name end
    end
    return def.id
end

-- The world's lighting rows, checked against the game's lighting table. A world that names none (or a row that does not exist) is lit with
-- DEFAULT_LIGHTING_ROW, a bright fallback, and the log says so.
local function world_light_rows(def)
    local day, night = def.lightingDay, def.lightingNight or def.lightingDay
    if day and find_row(FX_TABLE, day) == nil then
        log("vignette: lighting row '" .. day .. "' of " .. def.id .. " is not in the game's lighting table; using " .. DEFAULT_LIGHTING_ROW)
        day, night = nil, nil
    end
    if not day then
        log("vignette: " .. def.id .. " has no lighting set (LightingDay on its loader Blueprint); using " .. DEFAULT_LIGHTING_ROW)
        day, night = DEFAULT_LIGHTING_ROW, DEFAULT_LIGHTING_ROW
    end
    if find_row(FX_TABLE, night) == nil then night = day end
    return day, night
end

local function valid(o)
    local ok, v = pcall(function() return o ~= nil and o:IsValid() end)
    return ok and v == true
end

-- The level table's row struct: DT_Levels.RowStruct first, then the known paths. Logged once (and again if the answer changes).
local level_struct_seen = nil
local function level_struct()
    local st, from = nil, nil
    local dt = StaticFindObject(LEVELS_TABLE)
    if valid(dt) then
        local ok, s = pcall(function() return dt.RowStruct end)
        if ok and valid(s) then st, from = s, "DT_Levels.RowStruct" end
    end
    if not st then
        for _, p in ipairs(LEVEL_STRUCTS) do
            local s = StaticFindObject(p)
            if valid(s) then st, from = s, p break end
        end
    end
    local name = "none"
    if st then
        local okN, n = pcall(function() return st:GetFullName() end)
        name = (okN and type(n) == "string") and n or from
    end
    if name ~= level_struct_seen then
        level_struct_seen = name
        log("vignette: the level table's row struct is " .. name .. (st and (" (from " .. from .. ")") or ""))
    end
    return st
end

-- short field name -> the struct's own name (a Blueprint struct adds _<n>_<GUID>; native fields are plain)
local function level_fields()
    local names = {}
    local st = level_struct()
    if st then
        pcall(function() st:ForEachProperty(function(p) local n = p:GetFName():ToString(); names[(n:gsub("_%d+_%x+$", ""))] = n end) end)
    end
    return names
end

local function ensure_level_row(def, day, night)
    local dt = StaticFindObject(LEVELS_TABLE)
    if not (dt and dt:IsValid()) then
        -- on a fresh game start the game had still not loaded it a minute after a save made inside a world (CRD-022): load it here
        dt = load_table(LEVELS_TABLE)
        if dt then log("vignette: the game's level table was not loaded yet; loaded it") end
    end
    if not (dt and dt:IsValid()) then
        if not claimQuiet then log("vignette: the game's level table is not loaded yet") end
        return false
    end
    local rowName = level_row_name(def)
    if find_row(LEVELS_TABLE, rowName) ~= nil then return true end
    local f = level_fields()
    for _, k in ipairs({ "ReleaseGroup", "LevelFXRow_Day", "LevelFXRow_Night", "SectorName", "ResettablePortalWorld",
                         "HasFacilityShakes", "IsVignette", "EntranceTeleporter" }) do
        if not f[k] then if not claimQuiet then log("vignette: the game's level table has no field " .. k .. " (game update?); " .. def.id .. " stays a Facility area") end return false end
    end
    local fx = StaticFindObject(FX_TABLE)
    local row = {}
    row[f.ReleaseGroup] = 0
    -- before v1.5.0 only (a name); its successor Level is a soft object and stays unset
    if f.LevelFileName then row[f.LevelFileName] = FName(rowName) end
    if f.bIsSublevel then row[f.bIsSublevel] = false end
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

-- The level entry to put back on leaving, or nil when it is unknown: empty, "None" (a fresh controller after a save is loaded holds that until
-- the game's level tracking runs, CRD-022) or ours from before a mod restart. Unknown falls back to the Facility's row on leaving
-- (FALLBACK_LEVEL_ROW); the game sets its own row again within seconds wherever the player lands. Also used for the level name.
local function known_level(v)
    if not v or v == "" or v == "None" or v:sub(1, #ROW_PREFIX) == ROW_PREFIX then return nil end
    return v
end

local function claim_level(def, pc)
    -- the vignette zone (Buff_InVignette) may have been missing when the world loaded; it is only spawned if not there yet
    -- (not on a client: zones are the host's, CRD-027)
    local world = UEHelpers.GetWorld()
    if world and world:IsValid() and not is_client() then spawn_zones(world, def) end
    local day, night = world_light_rows(def)
    if not ensure_level_row(def, day, night) then return false end
    local rowName = level_row_name(def)
    local prevRaw = name_prop(pc, "ActiveLevelFXName")
    local prev = known_level(prevRaw)
    local okW = pcall(function() pc.ActiveLevelFXName = FName(rowName) end)
    if not okW then log("vignette: could not mark the player as being in " .. def.id) return false end
    local okT, err = switch_lighting(pc, day, night, world_title(def))
    -- the level's name as the game reports it (ActiveLevelName, a STRING property: write a Lua string, never an FName). In the game's own
    -- vignettes it holds the level's file name (V_ISLAND, H_Garden, ...), so ours holds the row name.
    -- a level name kept only with a known row: after a reload the name can be left from the previous map while the row is "None"
    local prevName = prev and known_level(name_prop(pc, "ActiveLevelName")) or nil
    pcall(function() pc.ActiveLevelName = rowName end)
    presence.claim = { id = def.id, row = rowName, prev = prev, prevName = prevName, day = day, night = night }
    log(string.format("vignette: inside %s; the game now treats it as a vignette (level entry %s, was %s); lighting %s / %s: %s",
        def.id, rowName, prev or ("unknown (" .. tostring(prevRaw) .. "), will fall back to " .. FALLBACK_LEVEL_ROW), day, night, okT and "switched" or ("not switched (" .. tostring(err):match("^[^\r\n]*") .. ")")))
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
    local prev = c and known_level(c.prev)
    local back = prev or FALLBACK_LEVEL_ROW
    pcall(function() pc.ActiveLevelFXName = FName(back) end)
    -- the level name back too: the one from before, or the file name of the level row being restored
    local nowName = name_prop(pc, "ActiveLevelName")
    if nowName and nowName:sub(1, #ROW_PREFIX) == ROW_PREFIX then
        local backName = prev and c.prevName or nil
        if not backName then
            local row, f = find_row(LEVELS_TABLE, back), level_fields()
            if row and f.LevelFileName then pcall(function() backName = row[f.LevelFileName]:ToString() end) end
            if not backName and back == FALLBACK_LEVEL_ROW then backName = FALLBACK_LEVEL_NAME end
        end
        if backName then pcall(function() pc.ActiveLevelName = backName end) end
    end
    local day, night = facility_light_rows(pc, back)
    local okT = false
    if day then okT = switch_lighting(pc, day, night, level_title(back)) end
    log(string.format("vignette: %s; level entry back to %s%s, lighting %s", why, back, prev and "" or " (previous one unknown)",
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

-- Is a vignette world's completion flag set in this world save? nil when it cannot be asked, including before the save's flags are loaded
-- (asking then answers false, which looked like the flag being set later, and the game logs an error for each early ask).
local function flags_loaded(fs)
    local ok, loaded = pcall(function() return fs:HasWorldFlagsLoaded() end)
    return not (ok and loaded == false)                       -- if the game cannot be asked, carry on as before
end

-- The flag subsystem is found once per player controller and kept (CRD-032). FindFirstOf walks the game's whole object list, and the
-- tracker asked for it every 2 s; on 13 November the game crashed inside such a walk, from a game-thread callback, while Rise streamed in.
-- A new controller (a load, a new map) means a new search, so a subsystem left from the old map is never asked.
-- (One main-chunk local for the cache and the function: the main chunk is near Lua's 200-local limit.)
local flag_subsystem = (function()
    local kept = { obj = nil, pc = nil }
    return function(pc)
        local key = pc and obj_key(pc)
        if kept.obj and kept.pc == key and kept.obj:IsValid() then return kept.obj end
        kept.obj, kept.pc = nil, nil
        local fs = FindFirstOf("WorldFlagSubsystem")
        if not (fs and fs:IsValid()) then return nil end
        if key then kept.obj, kept.pc = fs, key end
        return fs
    end
end)()

local function flag_is_set(def, pc)
    local fs = flag_subsystem(pc)
    if not (fs and fs:IsValid()) or not flags_loaded(fs) then return nil end
    local ok, v = pcall(function() return fs:HasWorldFlag(pc, flag_handle(completion_flag(def))) end)
    if ok and type(v) == "boolean" then return v end
    return nil
end

-- Watch the completion flags of vignette worlds (every 2 s) and say when one gets set or cleared.
local flagSeen, flagCheckAt = {}, 0
local function watch_flags(pc)
    if os.clock() - flagCheckAt < 2 then return end
    flagCheckAt = os.clock()
    local fs = flag_subsystem(pc)
    if fs and fs:IsValid() and not flags_loaded(fs) then flagSeen = {} return end   -- a save is loading: its flags are new, not changes
    for _, def in pairs(worldDefs) do
        if world_type(def) == "vignette" and def.vignette then
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
    local day = row_handle_name(pc, "Day_FX_Row")
    local lightOk = def.lighting or day == c.day
    if now == c.row and lightOk then return end
    presence.reclaimAt = os.clock()
    if now ~= c.row then
        pcall(function() pc.ActiveLevelFXName = FName(c.row) end)
        pcall(function() pc.ActiveLevelName = c.row end)
    end
    if not lightOk then switch_lighting(pc, c.day, c.night, "") end
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

-- The game world, from the tracker's own controller (CRD-032): UEHelpers.GetWorld() searches every PlayerController in the object list
-- first, and the tracker asked for it every tick while the player stood in a world that was still loading.
local function world_of(pc)
    if pc then
        local ok, w = pcall(function() return pc:GetWorld() end)
        if ok and w and w:IsValid() then return w end
    end
    return UEHelpers.GetWorld()
end

-- A world counts as ready when the hub says so and its loader is still there (without one that "ready" is from before a map load: see
-- forget_old_map), or when its level is already visible (for example the mods were restarted while the player was standing in it, so the
-- hub's own state is empty). In that case the hub adopts it. On a client (CRD-027) it is only adopted: its arrival pad, zones and portals
-- are the host's.
-- While the player stays in a ready world, the tracker checked its loader with FindAllOf every tick, a walk of the game's whole object
-- list (CRD-032). The loader found is kept with the player controller it was found under; a load or a new map brings a new controller,
-- so the loader is searched for again then (and a loader gone with its map still counts as gone).
local function world_is_ready(def, client, pc)
    local st = worldState[def.id]
    if st and st.status == "ready" then
        -- the loader kept with the controller it was found under (see above); searched for again under a new controller
        local key = pc and obj_key(pc)
        if key and st.loader and st.loaderPc == key and st.loader:IsValid() then return true end
        st.loader, st.loaderPc = nil, nil
        for _, a in ipairs(FindAllOf(def.loaderClass) or {}) do
            if a:IsValid() then st.loader, st.loaderPc = a, key; return true end
        end
        forget_old_map()
    end
    local world = world_of(pc)
    if world and world:IsValid() and loader_present(def) then
        local ls = find_streaming(world, def.level)
        local visible = false
        if ls then pcall(function() visible = ls:IsLevelVisible() end) end
        if visible then
            worldState[def.id] = { status = "ready", tries = 0 }
            apply_world_settings(def)
            if client then
                log("worlds: " .. def.id .. " was already loaded on this machine; adopted (client mode: its pads and zones are the host's)")
                return true
            end
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

-- After a save made inside a custom world is loaded, the world is often ready before the hub portals exist: they spawn SPAWN_DELAY_MS after
-- the portal room's own pads appear, and the world's pads (its arrival and exit pads) lead to a hub portal, so for a few seconds they gave the
-- game's "No Exit Found" (10 November: the hold let go at 01:46:12.09, hub_C2 spawned at 01:46:14.71). So when the player is in a ready world
-- whose hub portal is not there, the host spawns the hub portals at once (CRD-028). They are pads at fixed spots and need no portal room.
local function ensure_return_portal(def)
    local want = {}
    for _, e in ipairs(state.entries) do
        if e.world and e.world.id == def.id then want[e.id] = true end
    end
    if next(want) == nil then return end
    for _, t in ipairs(all_pads()) do
        if want[pad_id(t) or ""] then return end
    end
    log("worlds: the player is in " .. def.id .. " but its hub portal is not there yet; spawning the hub portals now")
    spawn_all()
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
    -- a client (CRD-027) keeps the claim and the lighting (its own screen) but never moves its pawn (the server would undo it) or loads a world
    local client = is_client()
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
    if world_is_ready(here, client, pc) then
        local justIn = presence.inside ~= here.id
        if presence.held then
            if client then presence.held = nil else release_player(pawn) end
        end
        -- in the same call as the release, so the player cannot reach a pad first; never on a client (the host's portals)
        if justIn and not client then ensure_return_portal(here) end
        if presence.inside ~= here.id then
            -- just arrived (or the mods were restarted while inside)
            presence.inside = here.id
            presence.claimRetryAt, presence.claimTries = nil, 0
            claimQuiet = false
            -- right after a save is loaded the game's level table may not be loaded yet: try again shortly (see below)
            if here.vignette and not claim_level(here, pc) then presence.claimRetryAt, presence.claimTries = os.clock() + CLAIM_RETRY_S, 1 end
            if here.vignette and world_type(here) == "vignette" and flag_is_set(here, pc) == false then
                show("Portal sickness: find " .. world_title(here) .. "'s proper exit to lift it", MSG_YELLOW)
            end
            -- a `lighting` block goes on top once the game has switched to the world's lighting rows (that takes about a second)
            presence.lightAt = here.lighting and (os.clock() + (presence.claim and 2.0 or 0.0)) or nil
        elseif here.vignette and presence.claimRetryAt then
            if os.clock() >= presence.claimRetryAt then
                local n = presence.claimTries + 1         -- this try's number (the one on arrival was 1)
                claimQuiet = n > CLAIM_TRIES
                local ok = claim_level(here, pc)
                claimQuiet = false
                if ok then
                    presence.claimRetryAt = nil
                    if n > CLAIM_TRIES then log("vignette: " .. here.id .. " was marked as a vignette on try " .. n) end
                else
                    presence.claimRetryAt, presence.claimTries = os.clock() + CLAIM_RETRY_S, n
                    if n % CLAIM_TRIES == 0 then
                        log("vignette: " .. here.id .. " could not be marked as a vignette after " .. n .. " tries; trying again every "
                            .. CLAIM_RETRY_S .. " s while the player is inside")
                    end
                end
            end
        elseif here.vignette then
            keep_claim(here, pc)
        end
        if presence.lightAt and os.clock() >= presence.lightAt and presence.lit ~= here.id then
            presence.lightAt = nil
            apply_lighting(here, pc)
            presence.lit = here.id
        end
        if here.killZ and loc.Z < here.origin[3] + here.killZ and not client then
            local dest, yaw = arrival_exit(here)
            if dest then
                send_player(pawn, dest, yaw)
                note(string.format("rescue: the player fell below z %.0f in %s and was returned to its arrival pad", here.origin[3] + here.killZ, here.id))
            end
        end
        return
    end
    if client then
        -- Only the host's teleport can put this player here, so the host has this world: load it on this machine (the host's loader and level
        -- never reach a client, run 1, 10 November). No hold: the pawn is the server's to move; the level streams in within about a second.
        local st = worldState[here.id]
        local world = world_of(pc)
        if not st and world and world:IsValid() then
            log("client mode: the host's teleport brought this player into " .. here.id .. "'s area; loading it on this machine")
            start_world(world, here)
        elseif st and st.status == "failed" then
            note("client mode: " .. here.id .. " cannot be loaded on this machine (is its pak installed?); this player stands in empty space")
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
        local world = world_of(pc)
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
    local gen = (presence.gen or 0) + 1        -- only the newest loop keeps going (see spawn_all)
    presence.gen, presence.lastTick = gen, os.clock()
    local function loop()
        if presence.gen ~= gen then return end
        presence.lastTick = os.clock()
        local ok, err = pcall(track_tick)
        if not ok then note("tracker error: " .. tostring(err):match("^[^\r\n]*")) end
        ExecuteWithDelay(TRACK_MS, function() ExecuteInGameThread(loop) end)
    end
    ExecuteWithDelay(TRACK_MS, function() ExecuteInGameThread(loop) end)
    log("tracker: watching " .. (function() local n = 0; for _ in pairs(worldDefs) do n = n + 1 end; return n end)() .. " custom world area(s)")
end

-- ---------------------------------------------------------------- Hub Exits (CRD-012): a base-game world's own exits
-- A base-game world's exits lead to the game's return points in the Facility. For exit modes "hub" and "dynamic" (see the top of this file)
-- the hub leaves those pads exactly as the game made them: everyone goes through the game's own teleport (so the pad's story flag and buffs
-- are given as usual), and a moment later a player who should leave to the hub is moved on to the front of the hub portal. AttemptTeleport is
-- told which player used the pad (InPlayer), so this is per player.
-- Why not change the pad's destination instead: the game has already teleported the player when the hook runs, so a destination set then
-- only counts for the NEXT use of that pad, and pads in streamed levels go back to the game's value when they reload (probe 1, 8 November).
-- A world's exits: the known ones below, the world's arrival pad (in some worlds it is also a way out), and any pad within FIND_NEAR_M of the
-- arrival pad whose teleport takes the player more than FIND_FAR_M away (found by distance; the log names it, for the list).
local HUB_EXITS = {                                  -- arrival pad id -> its exits (found in game)
    train_start = { "train_earlyexit", "train_end" },   -- 8 November
    anteverse_a_start = { "anteverse_a_exit" },         -- Far Garden, 9 November
}
local TRUE_EXIT_BUFFS = {   -- arrival pad id -> the buff rows its true exit gives, for manualBuffs (also read from its listed exits when loaded)
    anteverse_a_start = { "Buff_Hygroscopic" },        -- Far Garden: anteverse_a_exit, 9 November (lab pad-use survey)
}
local DEV_KEYS = true       -- END pretends to be a second player, for testing the dynamic mode alone (switch off for release)
local FIND_NEAR_M = 1000    -- a pad this close to a world's arrival pad counts as part of that world (the widest seen: Village Den, ~730 m;
                            -- the Cabin's arrival pad is ~1.7 km from the hub room and ~630 m from Torii's)
local FIND_FAR_M = 1500     -- and a teleport that takes the player this far from the pad counts as leaving the world
local LAND_CHECK_MS = 3000
local MOVED_M = 20          -- the game has teleported the player once they are this far from the exit pad they used
local WAIT_STEPS_MS = { 250, 500, 750 }   -- if not moved yet when the hook runs, look again after these waits (1.5 s in all)
local HOLD_MS = 1000        -- after the move the player is held still this long, so the portal room's floor can stream in
local exitWorld = {}        -- exit pad id -> the arrival pad id of the world it leaves
for dest, pads in pairs(HUB_EXITS) do for _, id in ipairs(pads) do exitWorld[id] = dest end end
local hubExit = { trips = {}, spoof = nil, said = {} }   -- trips[player][arrival id] = the hub portal that player came in by

local function player_key(char)
    if hubExit.spoof then return hubExit.spoof end
    local key = nil
    pcall(function()
        local ps = char.PlayerState
        if ps and ps:IsValid() then key = ps:GetFName():ToString() end
    end)
    if not key then pcall(function() key = char:GetFName():ToString() end) end
    return key or "unknown player"
end

-- the overlap can fire more than once per crossing: say each thing once a second at most
local function say_once(key, msg)
    local now = os.clock()
    if hubExit.said[key] and now - hubExit.said[key] < 1 then return end
    hubExit.said[key] = now
    log(msg)
end

local function metres(a, b)
    local dx, dy, dz = a.X - b.X, a.Y - b.Y, a.Z - b.Z
    return math.sqrt(dx * dx + dy * dy + dz * dz) / 100
end

-- Where the game puts a player who comes out of the hub pad in a slot, from the fixed slot positions (the portal room may not be streamed in).
local function hub_pad_exit(hubId)
    for _, e in ipairs(state.entries) do
        if e.id == hubId then
            local loc, yaw = Slots.pose(e.slot)
            local rad = math.rad(yaw)
            return { X = loc.X + math.cos(rad) * EXIT_FORWARD, Y = loc.Y + math.sin(rad) * EXIT_FORWARD, Z = loc.Z + EXIT_UP }, yaw
        end
    end
    return nil
end

local function check_after_move(char, used, hub, target)
    ExecuteWithDelay(LAND_CHECK_MS, function() ExecuteInGameThread(function()
        local ok, err = pcall(function()
            if not (char and char:IsValid()) then log("hub exits: check after " .. used .. ": the player is gone") return end
            local m = metres(char:K2_GetActorLocation(), target)
            log(string.format("hub exits: check after %s: the player is %.0f m from the front of %s%s", used, m, hub,
                m < 10 and " (at the hub portal)" or " (NOT at the hub portal: moved away, fell, or the move was undone)"))
        end)
        if not ok then log("hub exits: check failed: " .. tostring(err)) end
    end) end)
end

-- Move a player who just used a world exit on to a hub portal, once the game's own teleport has put them down.
local function send_to_hub(char, exitPad, used, hub, farM)
    local target, yaw = hub_pad_exit(hub)
    if not target then log("hub exits: " .. hub .. " is not a configured hub portal any more; " .. used .. " works as the game made it") return end
    local start = exitPad:K2_GetActorLocation()
    local t0 = os.clock()
    local function moved() return char:IsValid() and metres(char:K2_GetActorLocation(), start) > (farM or MOVED_M) end
    local function go(when)
        local ok, err = pcall(function()
            local from = char:K2_GetActorLocation()
            send_player(char, target, yaw)
            pcall(function() char.CharacterMovement:SetMovementMode(0, 0) end)      -- MOVE_None: held until the floor is there
            log(string.format("hub exits: %s: the game had moved the player %s; moved on from %.0f, %.0f, %.0f to the front of %s",
                used, when, from.X, from.Y, from.Z, hub))
        end)
        if not ok then log("hub exits: move failed: " .. tostring(err)) return end
        ExecuteWithDelay(HOLD_MS, function() ExecuteInGameThread(function()
            pcall(function() char.CharacterMovement:SetMovementMode(3, 0) end)      -- MOVE_Falling: lands and walks again
        end) end)
        check_after_move(char, used, hub, target)
    end
    if moved() then
        ExecuteWithDelay(100, function() ExecuteInGameThread(function() go("before the hook ran") end) end)
        return
    end
    local step = 1
    local function again()
        ExecuteWithDelay(WAIT_STEPS_MS[step], function() ExecuteInGameThread(function()
            local ok, isMoved = pcall(moved)
            if ok and isMoved then go(string.format("%.2f s after the hook", os.clock() - t0)) return end
            step = step + 1
            if step > #WAIT_STEPS_MS then
                log("hub exits: " .. used .. ": the game had not moved the player" .. (farM and " out of the world" or "") .. " after 1.5 s; not moving them")
                return
            end
            again()
        end) end)
    end
    again()
end

-- Which hub portal a player who just left a world by one of its exits goes to (nil: leave them where the game put them), and the mode.
local function hub_target(world, who)
    local trip = hubExit.trips[who] and hubExit.trips[who][world]
    local e = trip and state.byId[trip]
    if e and (e.exits == "dynamic" or e.exits == "hub") then return trip, e.exits end
    if state.hubMode[world] then return state.hubMode[world], "hub" end
    return nil, (e and e.exits) or (state.acts[world] and "dynamic") or "game"
end

local function find_pad(id)
    for _, t in ipairs(all_pads()) do if pad_id(t) == id then return t end end
    return nil
end

-- Is this pad an exit of a base-game world a hub portal leads to? Returns the world and how that is known ("list", "arrival", "distance").
local function exit_of(pad, mine)
    local w = exitWorld[mine]
    if w and state.dests[w] then return w, "list" end
    if state.dests[mine] and not worldDefs[mine] then return mine, "arrival" end
    local here = nil
    if mine:sub(1, 2) == "H_" then return nil end      -- the game's homes: their way out is their arrival pad, never found by distance
    for world in pairs(state.acts) do                 -- found by distance only for worlds whose exits the hub acts on
        local arrival = find_pad(world)
        if arrival then
            here = here or pad:K2_GetActorLocation()
            if metres(here, arrival:K2_GetActorLocation()) < FIND_NEAR_M then return world, "distance" end
        end
    end
    return nil
end

-- manualBuffs: the buffs the world's true exit gives, given by the manual portal (the game's own call, as its pads make it).
local function true_exit_buffs(world)
    local rows, seen = {}, {}
    local function add(r) if r and r ~= "None" and not seen[r] then seen[r] = true; rows[#rows + 1] = r end end
    for _, r in ipairs(TRUE_EXIT_BUFFS[world] or {}) do add(r) end
    for _, id in ipairs(HUB_EXITS[world] or {}) do
        local t = find_pad(id)
        if t then
            pcall(function() t.BuffsToApplyOnUse:ForEach(function(_, el) add(el:get().RowName:ToString()) end) end)
        end
    end
    return rows
end

local function give_exit_buffs(char, e)
    local rows = true_exit_buffs(e.dest)
    if #rows == 0 then log("hub exits: " .. e.manualId .. ": no true-exit buffs known for " .. e.dest .. "; none given") return end
    for _, r in ipairs(rows) do
        local ok, err = pcall(function() return char.BuffComponent:Server_ApplyBuff({ RowName = FName(r) }, false, 0.0, 0, nil, false) end)
        log("hub exits: " .. e.manualId .. ": true-exit buff " .. r .. (ok and " given" or (" failed: " .. tostring(err))))
    end
end

local function hub_exit_use(pad, char)
    local mine = pad_id(pad)
    if not mine then return end
    local dest = pad.DestinationTeleporterID:ToString()
    local who = player_key(char)
    local first = not hubExit.said[who .. mine] or os.clock() - hubExit.said[who .. mine] >= 1
    local e = state.byId[mine]
    if e then                                                -- a hub portal: remember who came in by which
        if state.dests[e.dest] and not worldDefs[e.dest] then
            local trips = hubExit.trips[who] or {}
            hubExit.trips[who] = trips
            trips[e.dest] = mine
            say_once(who .. mine, string.format("hub exits: %s entered %s through hub portal %s (exits: %s)", who, e.dest, mine, e.exits))
        end
        return
    end
    local m = state.byManual[mine]
    if m then                                                -- a manual portal: the game takes the player back to the hub portal
        say_once(who .. mine, string.format("hub exits: %s used the manual portal of %s, back to %s%s", who, m.dest, m.id,
            m.manualBuffs and " (with the true exit's buffs)" or ""))
        if m.manualBuffs and first and char then give_exit_buffs(char, m) end
        return
    end
    local mh = state.byMhe[mine]
    if mh then                                               -- an MHE on its own: the game takes the player to its hub portal or the failsafe
        say_once(who .. mine, string.format("hub exits: %s used the MHE of %s, to %s", who, mh.world, mh.dest))
        return
    end
    if is_hub_id(mine) or is_hub_id(dest) then return end
    if state.dests[dest] then                                -- the game's way into a world a hub portal leads to
        local trips = hubExit.trips[who]
        if trips and trips[dest] then
            trips[dest] = nil
            say_once(who .. mine, "hub exits: " .. who .. " entered " .. dest .. " the game's way (" .. mine .. ")")
        end
        return
    end
    local world, how = exit_of(pad, mine)
    if not world then return end
    local hub, mode = hub_target(world, who)
    if not hub then
        say_once(who .. mine, string.format("hub exits: %s used %s, an exit of %s (%s): exits %s, the game sends them to %s", who, mine, world, how, mode, dest))
        return
    end
    say_once(who .. mine, string.format("hub exits: %s used %s, an exit of %s (%s): exits %s, the game sends them to %s, then the hub moves them to %s",
        who, mine, world, how, mode, dest, hub))
    if first and char then send_to_hub(char, pad, mine, hub, how == "distance" and FIND_FAR_M or nil) end
end

local function on_attempt(self, inPlayer)
    local pad = self:get()
    if is_client() then          -- CRD-027: the host's hub sees every player's pad use; a client's would only fight it. Logged, to learn when it fires.
        local id = pad_id(pad) or "?"
        say_once("client " .. id, "client mode: AttemptTeleport ran on this client (pad " .. id .. "); the host's hub handles it, nothing done here")
        return
    end
    route_return(pad)
    local ok, err = pcall(function()
        local char = nil
        if inPlayer then pcall(function() char = inPlayer:get() end) end
        hub_exit_use(pad, char)
    end)
    if not ok then log("hub exits failed: " .. tostring(err)) end
end

-- The ids RegisterHook returns are kept so the hook can be taken off when this Lua state is unloaded (CRD-032, see unregister_hook below).
local function install_hook()
    if state.hooked then return end
    local ok, pre, post = pcall(RegisterHook, ATTEMPT_FN, on_attempt)
    if ok then
        state.hooked = true
        if type(pre) == "number" and type(post) == "number" then state.hookIds = { pre, post } end
    else
        log("hook failed: " .. tostring(pre))
    end
end

-- Restart All Mods, or restarting this mod alone, closes this Lua state (CRD-032). UE4SS v3.0.1-1212 drops a Blueprint function's hooks
-- only together with the mod that hooked that function first, so if another mod hooked AttemptTeleport before the hub, the hub's callback
-- would stay behind on a closed state and the next pad use would call into it. ModRef.OnUnload runs just before the state is closed, while
-- UE4SS holds back the game thread's Lua callbacks; UnregisterHook on a Blueprint function only marks the callback as gone. (The unload
-- function is a field, not a main-chunk local: the main chunk is near Lua's 200-local limit.)
state.unregister_hook = function()
    if not state.hookIds then return end
    local ids = state.hookIds
    state.hookIds, state.hooked = nil, false
    local ok, err = pcall(UnregisterHook, ATTEMPT_FN, ids[1], ids[2])
    log(ok and ("unloading: AttemptTeleport hook " .. ids[1] .. " unregistered")
        or ("unloading: the AttemptTeleport hook could not be unregistered: " .. tostring(err):match("^[^\r\n]*")))
end

-- MHEs on their own (see the top of this file) and the Failsafe Exit they may lead to. The failsafe is a landing pad only: off (like the
-- game's own return pads, which pads still teleport to) and hidden, placed so that a player arriving there stands at the recorded spot.
local FAILSAFE_ID = ID_PREFIX .. "failsafe"
local FAILSAFE_LIFT = 10    -- the hidden landing pad floats 0.1 m above the recorded floor, so an arrival never ends up in the floor (author, 9 November)
local function mhe_id(world) return ID_PREFIX .. "mhe_" .. world end
local function spawn_failsafe(world, class)
    local spot, yaw, from = nil, nil, "recorded"
    local f = MANUAL_EXITS.failsafe
    if type(f) == "table" and tonumber(f[1]) and tonumber(f[2]) and tonumber(f[3]) then
        spot, yaw = { X = tonumber(f[1]), Y = tonumber(f[2]), Z = tonumber(f[3]) }, tonumber(f[4]) or 0.0
    else
        local s0, y0 = portal_room_exit()
        if not s0 then log("MHE: no Failsafe Exit recorded and no slot to fall back on; not spawned") return false end
        spot, yaw, from = { X = s0.X, Y = s0.Y, Z = s0.Z - EXIT_UP }, y0, "not recorded yet: in front of the first hub portal"
    end
    local rad = math.rad(yaw)
    local loc = { X = spot.X - math.cos(rad) * EXIT_FORWARD, Y = spot.Y - math.sin(rad) * EXIT_FORWARD, Z = spot.Z + FAILSAFE_LIFT }
    local pad = world:SpawnActor(class, loc, { Pitch = 0.0, Yaw = yaw, Roll = 0.0 })
    if not pad or not pad:IsValid() then log("MHE: could not spawn the Failsafe Exit") return false end
    pad.MyTeleporterID = FName(FAILSAFE_ID)
    pad.DestinationTeleporterID = FName("None")
    pad.IsTeleporterActive = false
    pcall(function() pad:OnRep_IsTeleporterActive() end)
    local hidden = pcall(function() pad:SetActorHiddenInGame(true) end)
    log(string.format("MHE: Failsafe Exit (%s) at %.0f, %.0f, %.0f facing %.0f, hidden: %s", from, spot.X, spot.Y, spot.Z, yaw, tostring(hidden)))
    return true
end

local function spawn_mhes(world, class)
    local off = type(Config.mhe) == "table" and Config.mhe or {}
    local first, mode4 = {}, {}
    for _, e in ipairs(state.entries) do
        if e.exits == "manual" then mode4[e.dest] = true elseif not first[e.dest] then first[e.dest] = e.id end
    end
    local byMhe, needFailsafe, n = {}, false, 0
    for w, m in pairs(MANUAL_EXITS) do
        if w ~= "failsafe" and type(m) == "table" and tonumber(m[1]) and tonumber(m[2]) and tonumber(m[3]) and off[w] ~= false
                and not mode4[w] and not worldDefs[w] then
            local home = type(w) == "string" and w:match("^H_(.+)_Start$")     -- the game's homes have their own hub-room portal
            local dest = first[w] or (home and ("H_" .. home .. "_Entrance")) or FAILSAFE_ID
            local pad = world:SpawnActor(class, { X = tonumber(m[1]), Y = tonumber(m[2]), Z = tonumber(m[3]) }, { Pitch = 0.0, Yaw = tonumber(m[4]) or 0.0, Roll = 0.0 })
            if pad and pad:IsValid() then
                pad.MyTeleporterID = FName(mhe_id(w))
                pad.DestinationTeleporterID = FName(dest)
                pad.IsTeleporterActive = true
                pcall(function() pad:OnRep_IsTeleporterActive() end)
                apply_design(pad, DEFAULT_DESIGN)
                byMhe[mhe_id(w)] = { world = w, dest = dest }
                needFailsafe = needFailsafe or dest == FAILSAFE_ID
                n = n + 1
                log(string.format("MHE: %s at %.0f, %.0f, %.0f leads to %s%s", w, tonumber(m[1]), tonumber(m[2]), tonumber(m[3]), dest,
                    dest == FAILSAFE_ID and " (no hub portal to this world: the Failsafe Exit)" or ""))
            else
                log("MHE: could not spawn the MHE of " .. w)
            end
        elseif w ~= "failsafe" and off[w] == false then
            log("MHE: " .. w .. " is switched off in config.lua (mhe)")
        end
    end
    state.byMhe = byMhe
    if needFailsafe then spawn_failsafe(world, class) end
    return n
end

-- ---------------------------------------------------------------- client mode: what a joining player's hub still does (see "client mode" above)
-- The host's portals in the room: by ID (hub_A3 ...) or, if their ID has not come through, by standing where a slot's pad stands.
local SLOT_BY_PAD = {}
for _, s in ipairs(Slots.list) do
    if not s.base then SLOT_BY_PAD[ID_PREFIX .. (s.id:gsub("-", ""))] = s end
end
local SLOT_NEAR = 50                -- units: a pad this close to a slot's pad position stands in that slot
local CLIENT_REFRESH_MS = 1000      -- after a teleporter arrives from the host, look again this much later (its ID comes with it)
local client = { watching = false, pending = false, pendingAt = 0, styled = {}, line = nil, gen = 0 }

local function slot_of_pad(t, id)
    if id and SLOT_BY_PAD[id] then return SLOT_BY_PAD[id] end
    if id and id ~= "" and id ~= "None" then return nil end
    local ok, l = pcall(function() return t:K2_GetActorLocation() end)
    if not (ok and l) then return nil end
    for _, s in ipairs(Slots.list) do
        if not s.base then
            local p = Slots.pose(s)
            local dx, dy, dz = l.X - p.X, l.Y - p.Y, l.Z - p.Z
            if dx * dx + dy * dy + dz * dz < SLOT_NEAR * SLOT_NEAR then return s end
        end
    end
    return nil
end

-- This player's own look and light, on a host portal whose slot this player's config also fills with a portal to the same place. Once per
-- pad (the light's brightness is a multiplier). Look and light are settings of the pad's own components on this machine: never sent anywhere.
local function style_host_pad(t, slot)
    local okN, name = pcall(function() return t:GetFName():ToString() end)
    local key = (okN and type(name) == "string") and name or (slot.id .. " " .. tostring(t))
    if client.styled[key] then return end
    client.styled[key] = true
    local e = nil
    for _, x in ipairs(state.entries) do if x.slot == slot then e = x end end
    if not e then return end
    local dest = nil
    pcall(function() dest = t.DestinationTeleporterID:ToString() end)
    local mine = e.manualId or e.dest
    if not dest or dest == "" or dest == "None" then
        log("client mode: the host's portal in " .. slot.id .. " shows no destination here; your look for it is not applied")
        return
    end
    if dest ~= mine then
        log("client mode: the host's portal in " .. slot.id .. " leads to " .. dest .. " (yours: " .. mine .. "); your look for it is not applied")
        return
    end
    apply_design(t, e.design)
    apply_light(t, e)
    log("client mode: your look for " .. slot.id .. " ('" .. e.name .. "') is on the host's portal there")
end

-- The hum volume (this player's own humMode) on every hub-room pad here: the game's 3 entrances and the host's portals, counted as they are.
local function client_refresh()
    local seen, count, pads = {}, 0, {}
    for _, t in ipairs(all_pads()) do
        local id = pad_id(t)
        local slot = slot_of_pad(t, id)
        if slot then
            if not seen[slot.id] then seen[slot.id] = true; count = count + 1 end
            pads[#pads + 1] = { t = t, slot = slot }
        elseif id and Slots.baseEntrances[id] then
            pads[#pads + 1] = { t = t }
        end
    end
    local mult, touched = hum_multiplier(count), 0
    for _, p in ipairs(pads) do
        pcall(function()
            local h = p.t.PortalHumLoop
            if h and h:IsValid() then h:SetVolumeMultiplier(mult); touched = touched + 1 end
        end)
    end
    for _, p in ipairs(pads) do
        if p.slot then pcall(style_host_pad, p.t, p.slot) end
    end
    -- Custom worlds, loaded ahead of time by a guess: the host's portals reach a client without their IDs or destinations (run 1), so where
    -- the host has a portal in a slot that this player's config fills with a custom world, that world is loaded here. Right when both configs
    -- give the slot the same world; when wrong, a world loads that nothing leads to. (The tracker also loads a world on arrival.)
    local world = UEHelpers.GetWorld()
    for _, e in ipairs(state.entries) do
        if e.world and seen[e.slot.id] and not worldState[e.world.id] and world and world:IsValid() then
            log("client mode: the host has a portal in " .. e.slot.id .. ", where your config puts " .. e.world.id .. "; loading it on this machine ahead of time")
            start_world(world, e.world)
        end
    end
    local line = string.format("client mode: hum volume (%s) x%.3f on %d hub pad(s) (%d portal(s) from the host)", HUM_MODE, mult, touched, count)
    if line ~= client.line then client.line = line; log(line) end
    return count
end

-- Hub portals reach a client whenever the host spawns them or the player comes near them (and they are new objects each time), so every new
-- teleporter means one more look a moment later. Registered once, the first time this machine is a client; does nothing while it hosts.
local function watch_client_pads()
    if client.watching then return end
    client.watching = true
    NotifyOnNewObject(TELEPORTER_CLASS, function()
        if client.pending and os.clock() - client.pendingAt < STALE_S then return end     -- one look per burst (a dropped timer is replaced)
        client.pending, client.pendingAt = true, os.clock()
        client.gen = client.gen + 1
        local gen = client.gen
        ExecuteWithDelay(CLIENT_REFRESH_MS, function() ExecuteInGameThread(function()
            if gen ~= client.gen then return end
            client.pending = false
            local ok, err = pcall(function() if is_client() then client_refresh() end end)
            if not ok then log("client mode: refresh failed: " .. tostring(err):match("^[^\r\n]*")) end
        end) end)
    end)
    log("client mode: watching for hub portals that arrive from the host")
end

local ROLE_TRIES = 10       -- no player controller yet when the portals are due: look again every second this many times, then act as host
local roleTries = 0
local schedule_spawn        -- (below)

spawn_all = function()
    log("spawn_all: starting")
    local world = UEHelpers.GetWorld()
    if not world or not world:IsValid() then log("no world yet") return end
    local class = StaticFindObject(TELEPORTER_CLASS)
    if not class or not class:IsValid() then log("teleporter class not found") return end
    if CLIENT_MODE then
        local role = net_role()
        if role == nil and roleTries < ROLE_TRIES then
            roleTries = roleTries + 1
            log("client mode: no player controller yet, so host or client is not known; looking again in 1 s (" .. roleTries .. "/" .. ROLE_TRIES .. ")")
            schedule_spawn(1000)
            return
        end
        if role == nil then log("client mode: still no player controller; acting as host") end
        roleTries = 0
        if role == "client" then
            log("client mode: this player joined someone else's game; the host's hub runs the portals, exits and worlds (clientMode = false turns this off)")
            install_hook()               -- inert on a client: it only logs that AttemptTeleport ran here
            forget_old_map()
            if presence.running and os.clock() - (presence.lastTick or 0) > STALE_S then
                log("tracker: it stopped running (a dropped timer); starting it again")
                presence.running = false
                start_tracker()
            end
            watch_client_pads()
            client.line = nil            -- the hum line is logged once per load (after that only when it changes)
            client_refresh()
            return
        end
    end
    destroy_hub_pads()
    state.spawns = (state.spawns or 0) + 1        -- a spawn that was scheduled before this one is not needed (see schedule_spawn)
    install_hook()
    local mheChanged, mheCount = load_manual_exits()
    if mheChanged then
        log("manual_exits.lua changed (" .. mheCount .. " MHE(s)); reading the portals again")
        resolve_config()
    end
    forget_old_map()        -- before the portals spawn: a portal to a world of the old map must start off
    if presence.running and os.clock() - (presence.lastTick or 0) > STALE_S then
        log("tracker: it stopped running (a dropped timer); starting it again")
        presence.running = false
        start_tracker()
    end
    local added = 0
    for _, e in ipairs(state.entries) do
        if spawn_entry(world, class, e) then added = added + 1 end
    end
    apply_hum(added)
    spawn_mhes(world, class)
    ensure_worlds(world)
    log(added .. " of " .. #state.entries .. " configured portal(s) spawned")
end

schedule_spawn = function(delay_ms)
    if state.pending then return end
    state.pending = true
    local before = state.spawns or 0
    ExecuteWithDelay(delay_ms, function()
        state.pending = false
        ExecuteInGameThread(function()
            -- the hub portals were spawned while this one waited (the tracker, CRD-028, or NUMPAD 1): spawning again would only replace them
            if (state.spawns or 0) ~= before then log("the hub portals were spawned in the meantime; not spawning them again") return end
            spawn_all()
        end)
    end)
end

resolve_worlds()
resolve_config()
log(#state.entries .. " portal(s) configured")
log(CLIENT_MODE and "client mode: on (in someone else's game this hub stands down; clientMode = false in config.lua turns it off)"
    or "client mode: OFF (clientMode = false in config.lua): in someone else's game this hub also spawns its own portals")
start_tracker()

-- Spawn whenever the hub room's own portals appear (world load), and now if the world is already up.
-- The callback returns nothing on purpose: a NotifyOnNewObject callback that returns true is removed, and with it, in UE4SS v3.0.1-1212, the
-- reference that may be keeping this mod's shared hook thread alive (CRD-032).
NotifyOnNewObject(HOMEWORLD_CLASS, function() log("a Homeworld pad appeared; spawning the hub portals shortly"); schedule_spawn(SPAWN_DELAY_MS) end)
-- On Restart All Mods this file runs on UE4SS's own thread while the game runs, so the object search waits for the game thread (CRD-032).
ExecuteInGameThread(function()
    local existing = FindFirstOf("BP_Teleporter_HomeWorld_C")
    if existing and existing:IsValid() then
        log("the portal room is already loaded; spawning the hub portals")
        schedule_spawn(500)
    else
        log("the portal room is not loaded yet; the hub portals will spawn when you get near it (or press NUMPAD 1 in the room)")
    end
end)

-- ModRef.OnUnload (UE4SS 3.x) is called just before Restart All Mods closes this Lua state; older builds without it ignore the field.
if not pcall(function() ModRef.OnUnload = state.unregister_hook end) then log("unload callback not available in this UE4SS; the hook stays until the game restarts") end

RegisterKeyBind(Key.NUM_ONE, function() log("NUMPAD 1 pressed"); ExecuteInGameThread(spawn_all) end)
RegisterKeyBind(Key.NUM_TWO, function()
    ExecuteInGameThread(function()
        if is_client() then log("client mode: NUMPAD 2 does nothing here; the portals are the host's") return end
        log("removed " .. destroy_hub_pads() .. " pad(s)")
        apply_hum(0)
    end)
end)
if DEV_KEYS then
    RegisterKeyBind(Key.END, function()
        ExecuteInGameThread(function()
            hubExit.spoof = (not hubExit.spoof) and "Player 2 (pretend)" or nil
            show(hubExit.spoof and "Hub Exits test: you now count as Player 2" or "Hub Exits test: you are yourself again")
        end)
    end)
end
log("loaded - NUMPAD 1 respawn portals, NUMPAD 2 remove them" .. (DEV_KEYS and ", END pretend to be Player 2 (Hub Exits test)" or ""))
