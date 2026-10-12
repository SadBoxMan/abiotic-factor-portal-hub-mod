-- PortalMaterialLab: experiment to see whether the material (or texture) of a hub portal can be swapped from Lua.
--
-- Background: the game's plain portal effect (Niagara_Portal, and looks built on it such as Blueverse) exposes a Niagara user
-- parameter called  User.PortalTexture , and the teleporter Blueprint calls "SetVariableMaterial" and refers to M_WorldPortal.
-- So the "window" of those portals may be a material that can be replaced. This lab tries that, one step at a time, and logs
-- every result so we can see what is possible. It only touches the hub portals spawned by PortalHub (IDs starting "hub_").
--
--   NUMPAD 7 = report: what the hub portals' effects look like, which test materials/textures are already loaded
--   NUMPAD 8 = apply the NEXT material in the list to every hub portal (SetVariableMaterial), then look at the portals
--   NUMPAD 9 = apply the NEXT texture in the list to every hub portal (SetVariableTexture)
--   NUMPAD 0 = put the original M_WorldPortal material back
--
-- Everything is wrapped in pcall, so a call that does not exist or fails prints a message instead of crashing the game.

local PARAM_NAMES = { "User.PortalTexture", "PortalTexture" }   -- tried in this order; the second is a fallback spelling

local MATERIALS = {
    "/Game/Particles/Materials/M_WorldPortal.M_WorldPortal",
    "/Game/Particles/Materials/M_WorldPortal_HCabin.M_WorldPortal_HCabin",
    "/Game/Particles/Materials/M_WorldPortal_Offices.M_WorldPortal_Offices",
    "/Game/Particles/Materials/M_WorldPortal_Warehouse.M_WorldPortal_Warehouse",
    "/Game/Particles/Materials/M_WorldPortal_Fog.M_WorldPortal_Fog",
    "/Game/Particles/Materials/M_WorldPortal_AnteA.M_WorldPortal_AnteA",
    "/Game/Particles/Materials/M_WorldPortal_AnteC.M_WorldPortal_AnteC",
    "/Game/Particles/Materials/M_Portal_Torii.M_Portal_Torii",
    "/Game/Particles/Materials/M_Portal_Arch.M_Portal_Arch",
    "/Game/Particles/Materials/M_Portal_FractureOpening.M_Portal_FractureOpening",
    "/Game/Particles/Materials/M_Portal_Friendly_Blue.M_Portal_Friendly_Blue",
    "/Game/Particles/Materials/M_Portal_Friendly_Cyan.M_Portal_Friendly_Cyan",
    "/Game/Particles/Materials/M_Portal_Shadowgate.M_Portal_Shadowgate",
    "/Game/Particles/Materials/M_Portal_Botanical_Green.M_Portal_Botanical_Green",
}

local TEXTURES = {
    "/Game/Particles/RenderTargets/TC_Portal_Torii.TC_Portal_Torii",
    "/Game/Particles/RenderTargets/TC_Portal_Alps.TC_Portal_Alps",
    "/Game/Particles/RenderTargets/TC_Portal_Anteverse_A.TC_Portal_Anteverse_A",
    "/Game/Particles/RenderTargets/TC_Portal_Fog.TC_Portal_Fog",
    "/Game/Particles/RenderTargets/TC_Portal_Offices.TC_Portal_Offices",
    "/Game/Particles/RenderTargets/TC_Portal_Warehouse.TC_Portal_Warehouse",
}

local mat_index, tex_index = 0, 0

local function log(msg) print("[MaterialLab] " .. msg .. "\n") end

local function short(path) return (path:gsub("^.*/", ""):gsub("%..*$", "")) end

local function pad_id(t)
    local ok, id = pcall(function() return t.MyTeleporterID:ToString() end)
    if ok then return id end
    return nil
end

local function hub_pads()
    local list = {}
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if t:IsValid() then
            local id = pad_id(t)
            if id and id:sub(1, 4) == "hub_" then list[#list + 1] = t end
        end
    end
    return list
end

-- Find an asset that is already loaded, or load it. Returns the object or nil.
local function find_object(path)
    local obj = StaticFindObject(path)
    if obj and obj:IsValid() then return obj, "already loaded" end
    local ok = pcall(LoadAsset, path)
    obj = StaticFindObject(path)
    if ok and obj and obj:IsValid() then return obj, "loaded now" end
    return nil, "not found"
end

local function describe(v)
    if v == nil then return "nil" end
    local t = type(v)
    if t == "userdata" then
        local ok, s = pcall(function()
            if v.IsValid and not v:IsValid() then return "<invalid object>" end
            if v.GetFullName then return v:GetFullName() end
            return "<" .. tostring(v) .. ">"
        end)
        return ok and tostring(s) or "<unreadable>"
    end
    return t .. ":" .. tostring(v)
end

-- NOTE: calling a method (GetFName, GetFullName, ...) on an object that is not valid crashes the game, and pcall cannot
-- catch that. So every object is checked with IsValid() before anything is called on it, and each step is logged first.
local function design_of(pad)
    local pl = pad.ParticleLoop
    if not (pl and pl:IsValid()) then return "(no effect component)" end
    local asset = pl:GetAsset()
    if not (asset and asset:IsValid()) then return "(no effect asset)" end
    return asset:GetFName():ToString()
end

local function class_of(obj)
    if not (obj and obj:IsValid()) then return "?" end
    local cls = obj:GetClass()
    if not (cls and cls:IsValid()) then return "?" end
    return cls:GetFName():ToString()
end

local function report()
    local pads = hub_pads()
    log("---- REPORT: " .. #pads .. " hub portal(s)")
    for i, p in ipairs(pads) do
        local id = pad_id(p) or "?"
        log("step: pad " .. i .. " " .. id)
        local design = design_of(p)
        log("  effect = " .. design)
        local pl = p.ParticleLoop
        if pl and pl:IsValid() then
            log("  step: checking SetVariableMaterial on the effect component")
            local ok, fn = pcall(function() return pl.SetVariableMaterial end)
            log("  SetVariableMaterial member type = " .. (ok and type(fn) or "error"))
        end
        log("  step: PortalImage / PortalTexture")
        log("  PortalImage = " .. describe(select(2, pcall(function() return p.PortalImage end))))
        log("  PortalTexture = " .. describe(select(2, pcall(function() return p.PortalTexture end))))
    end
    log("---- test materials (already loaded only; nothing is loaded by this report):")
    for _, path in ipairs(MATERIALS) do
        local obj = StaticFindObject(path)
        local loaded = obj and obj:IsValid()
        log(string.format("  %-34s %s%s", short(path), loaded and "loaded" or "not loaded yet", loaded and (" | class " .. class_of(obj)) or ""))
    end
    log("---- test textures (already loaded only):")
    for _, path in ipairs(TEXTURES) do
        local obj = StaticFindObject(path)
        local loaded = obj and obj:IsValid()
        log(string.format("  %-34s %s%s", short(path), loaded and "loaded" or "not loaded yet", loaded and (" | class " .. class_of(obj)) or ""))
    end
    log("---- REPORT done")
end
local function apply(kind, path)
    log("step: " .. kind .. " " .. short(path))
    local obj, how = find_object(path)
    if not obj then log(kind .. " " .. short(path) .. ": " .. how .. ", nothing applied") return end
    local pads = hub_pads()
    log(string.format("---- %s -> %s (%s) on %d hub portal(s)", kind, short(path), how, #pads))
    for _, p in ipairs(pads) do
        local applied = false
        for _, name in ipairs(PARAM_NAMES) do
            local ok, err = pcall(function()
                local pl = p.ParticleLoop
                if not (pl and pl:IsValid()) then error("no effect component") end
                if kind == "material" then pl:SetVariableMaterial(FName(name), obj)
                else pl:SetVariableTexture(FName(name), obj) end
            end)
            if ok then
                log(string.format("  %-8s %-26s ok with '%s'", pad_id(p), design_of(p), name))
                applied = true
                break
            else
                log(string.format("  %-8s %-26s '%s' failed: %s", pad_id(p), design_of(p), name, tostring(err)))
            end
        end
    end
end

RegisterKeyBind(Key.NUM_SEVEN, function() ExecuteInGameThread(report) end)
RegisterKeyBind(Key.NUM_EIGHT, function()
    ExecuteInGameThread(function()
        mat_index = (mat_index % #MATERIALS) + 1
        apply("material", MATERIALS[mat_index])
    end)
end)
RegisterKeyBind(Key.NUM_NINE, function()
    ExecuteInGameThread(function()
        tex_index = (tex_index % #TEXTURES) + 1
        apply("texture", TEXTURES[tex_index])
    end)
end)
RegisterKeyBind(Key.NUM_ZERO, function()
    ExecuteInGameThread(function()
        mat_index = 0
        apply("material", MATERIALS[1])
    end)
end)

log("loaded - NUMPAD 7 report, 8 next material, 9 next texture, 0 reset material")


------------------------------------------------------------------------------------------------------------------------
-- Prototype 2: overlay effects, colours and level streaming.  Everything is checked with IsValid() first and wrapped in pcall.
--   NUMPAD 4 = OVERLAY: spawn a SnowFlurry effect on top of the first hub portal with only its "Swirl" part left on
--   NUMPAD 5 = COLOUR (pad light): cycle the first hub portal's own light through red / green / blue / white
--   NUMPAD 6 = COLOUR SURVEY: tint every hub portal's effect (red / green / blue / white) and log which looks declare a colour setting
--   NUMPAD 3 = LEVEL STREAM test: try to stream the tiny existing map "Vignette_Theatre" in far below the world (log only)
--   NUMPAD . (decimal point) = remove the overlay / rift effects again
------------------------------------------------------------------------------------------------------------------------
local UEHelpers = require("UEHelpers")
local SNOW = "/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"
local RIFT = "/Game/Particles/Niagara_Portal_Rift.Niagara_Portal_Rift"
local COLOURS = {
    { name = "red",   v = { R = 1.0, G = 0.1, B = 0.1, A = 1.0 } },
    { name = "green", v = { R = 0.1, G = 1.0, B = 0.2, A = 1.0 } },
    { name = "blue",  v = { R = 0.1, G = 0.3, B = 1.0, A = 1.0 } },
    { name = "white", v = { R = 1.0, G = 1.0, B = 1.0, A = 1.0 } },
}
local spawned_fx = {}
local light_index, rift_index = 0, 0
local rift_comp = nil

local function first_pad()
    local pads = hub_pads()
    return pads[1]
end

local function niagara_lib()
    local lib = StaticFindObject("/Script/Niagara.Default__NiagaraFunctionLibrary")
    if lib and lib:IsValid() then return lib end
    return nil
end

local function spawn_effect(path, loc, rot)
    local lib = niagara_lib()
    if not lib then log("  NiagaraFunctionLibrary not found") return nil end
    local sys = find_object(path)
    if not sys then log("  effect asset not found: " .. short(path)) return nil end
    local world = UEHelpers.GetWorld()
    if not (world and world:IsValid()) then log("  no world") return nil end
    local ok, comp = pcall(function()
        -- WorldContext, System, Location, Rotation, Scale, bAutoDestroy, bAutoActivate, PoolingMethod (0 = none), bPreCullCheck
        return lib:SpawnSystemAtLocation(world, sys, loc, rot, { X = 1, Y = 1, Z = 1 }, false, true, 0, false)
    end)
    if not ok then log("  SpawnSystemAtLocation failed: " .. tostring(comp)) return nil end
    if not (comp and comp:IsValid()) then log("  SpawnSystemAtLocation returned nothing usable") return nil end
    spawned_fx[#spawned_fx + 1] = comp
    return comp
end

local function overlay_test()
    log("---- OVERLAY test")
    local pad = first_pad()
    if not pad then log("  no hub portal in the world") return end
    local loc = pad:K2_GetActorLocation()
    loc = { X = loc.X, Y = loc.Y, Z = loc.Z + 120 }
    local rot = pad:K2_GetActorRotation()
    local comp = spawn_effect(SNOW, loc, rot)
    if not comp then return end
    log("  overlay effect spawned at " .. pad_id(pad))
    for _, part in ipairs({ "Blackhole", "smoke", "snowflakes", "SnowParticle01", "SnowParticle02" }) do
        local ok, err = pcall(function() comp:SetEmitterEnable(FName(part), false) end)
        log("  part off: " .. part .. (ok and " ok" or (" FAILED: " .. tostring(err))))
    end
    log("  only 'Swirl' should remain. Look at the first hub portal (hub_A3).")
end

local function light_test()
    log("---- PAD LIGHT colour test")
    local pad = first_pad()
    if not pad then log("  no hub portal in the world") return end
    local light = pad.PointLight
    if not (light and light:IsValid()) then log("  pad has no PointLight component") return end
    light_index = (light_index % #COLOURS) + 1
    local c = COLOURS[light_index]
    local ok, err = pcall(function() light:SetLightColor(c.v, true) end)
    log("  " .. pad_id(pad) .. " light -> " .. c.name .. (ok and " ok" or (" FAILED: " .. tostring(err))))
    pcall(function() light:SetIntensity(20000.0) end)
end

-- COLOUR SURVEY: tints the effect of EVERY hub portal at once, whatever its look, and logs which ones declare a colour setting.
-- Niagara silently ignores a setting a look does not have, so the call always "succeeds"; the only way to tell is to watch which
-- portals change colour. DECLARED = the look's effect file lists that parameter (from the game's data); watch those first.
local DECLARED_COLOUR = {
    Niagara_Portal_Rift = "User.Color", Niagara_Portal_Rift_BlueFade = "User.Color", Niagara_Portal_Rift_Collapse = "User.Color",
}
local COLOUR_PARAMS = { "User.Color", "User.Color01", "User.Tint", "User.PortalColor" }

local function rift_test()
    rift_index = (rift_index % #COLOURS) + 1
    local c = COLOURS[rift_index]
    local BOOST = 6.0      -- effect colours often need values above 1.0 to show as a strong tint
    local v = { R = c.v.R * BOOST, G = c.v.G * BOOST, B = c.v.B * BOOST, A = 1.0 }
    log(string.format("---- COLOUR SURVEY: %s (x%.0f) on every hub portal", c.name, BOOST))
    local pads = hub_pads()
    if #pads == 0 then log("  no hub portals in the world") return end
    for _, p in ipairs(pads) do
        local id = pad_id(p) or "?"
        local pl = p.ParticleLoop
        if not (pl and pl:IsValid()) then
            log("  " .. id .. ": no effect component")
        else
            local asset = pl:GetAsset()
            local design = (asset and asset:IsValid()) and asset:GetFName():ToString() or "(no effect asset)"
            local sent = 0
            for _, name in ipairs(COLOUR_PARAMS) do
                if pcall(function() pl:SetVariableLinearColor(FName(name), v) end) then sent = sent + 1 end
            end
            log(string.format("  %-7s %-30s sent %d colour setting(s) | declares: %s", id, design, sent, DECLARED_COLOUR[design] or "none"))
        end
    end
    log("  -> now watch which portals changed colour; press NUMPAD 6 again for the next colour")
end
local function kill_effect(comp, label)
    local ok1 = pcall(function() comp:DeactivateImmediate() end)
    local ok2, err2 = pcall(function() comp:K2_DestroyComponent(comp) end)
    local ok3 = pcall(function() comp:SetVisibility(false, true) end)
    log(string.format("  %s: deactivate=%s destroy=%s%s hide=%s", label, tostring(ok1), tostring(ok2), ok2 and "" or (" (" .. tostring(err2) .. ")"), tostring(ok3)))
end

-- Removes the test effects. After a mod restart our list is gone, so we look for SnowFlurry / Rift effect components in the world.
-- Every one found is LOGGED with its owner. Components that belong to a teleporter pad (the game's own portals, and our hub
-- portals, keep their effect on the pad) are left alone; the rest are treated as leftover test effects and removed.
-- Every object is checked with IsValid() before anything is called on it.
local function owner_label(comp)
    local owner = comp:GetOwner()
    if not (owner and owner:IsValid()) then return "(no owner)", "" end
    local cls = owner:GetClass()
    local cname = (cls and cls:IsValid()) and cls:GetFName():ToString() or "?"
    return owner:GetFName():ToString() .. " [" .. cname .. "]", cname
end

local function clear_fx()
    local n = 0
    for _, comp in ipairs(spawned_fx) do
        if comp and comp:IsValid() then kill_effect(comp, "tracked effect"); n = n + 1 end
    end
    spawned_fx = {}; rift_comp = nil
    local scanned, loose, kept = 0, 0, 0
    for _, comp in ipairs(FindAllOf("NiagaraComponent") or {}) do
        if comp:IsValid() then
            scanned = scanned + 1
            local asset = comp:GetAsset()
            if asset and asset:IsValid() then
                local aname = asset:GetFName():ToString()
                if aname == "Niagara_Portal_SnowFlurry" or aname == "Niagara_Portal_Rift" then
                    local label, cname = owner_label(comp)
                    local active = "?"
                    pcall(function() active = tostring(comp:IsActive()) end)
                    log(string.format("  found %s | comp %s | owner %s | active %s", aname, comp:GetFName():ToString(), label, active))
                    if cname:find("Teleporter") then
                        kept = kept + 1
                    else
                        kill_effect(comp, "removing " .. aname)
                        loose = loose + 1
                    end
                end
            end
        end
    end
    log(string.format("removed %d tracked + %d leftover; kept %d on teleporter pads (looked at %d effect components)", n, loose, kept, scanned))
end
-- Level streaming: which of the loading calls does this game accept? Only logs; uses the tiny empty map Vignette_Theatre.
-- Prints a function's real parameter list (name and type, in order), so we stop guessing at call shapes.
local function dump_signature(path)
    local fn = StaticFindObject(path)
    if not (fn and fn:IsValid()) then log("  signature " .. short(path) .. ": function not found") return end
    log("  signature of " .. path .. ":")
    local n = 0
    local ok, err = pcall(function()
        fn:ForEachProperty(function(prop)
            n = n + 1
            local pname, ptype = "?", "?"
            pcall(function() pname = prop:GetFName():ToString() end)
            pcall(function() ptype = prop:GetClass():GetFName():ToString() end)
            log(string.format("    %d. %s : %s", n, pname, ptype))
        end)
    end)
    if not ok then log("  could not list parameters: " .. tostring(err)) end
end
local function stream_test()
    log("---- LEVEL STREAM test (Vignette_Theatre, far below the world)")
    dump_signature("/Script/Engine.LevelStreamingDynamic:LoadLevelInstance")
    dump_signature("/Script/Engine.LevelStreamingDynamic:LoadLevelInstanceBySoftObjectPtr")
    dump_signature("/Script/AbioticFactor.LevelStreamingCustom:LoadStreamLevel")
    local world = UEHelpers.GetWorld()
    if not (world and world:IsValid()) then log("  no world") return end
    local where = { X = 0.0, Y = 0.0, Z = -900000.0 }
    local rot = { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }
    local dyn = StaticFindObject("/Script/Engine.Default__LevelStreamingDynamic")
    local dynClass = StaticFindObject("/Script/Engine.LevelStreamingDynamic")
    log("  LevelStreamingDynamic default object: " .. ((dyn and dyn:IsValid()) and "found" or "NOT found"))
    log("  LevelStreamingDynamic class: " .. ((dynClass and dynClass:IsValid()) and "found" or "NOT found"))
    local before = #(FindAllOf("LevelStreamingDynamic") or {})
    if dyn and dyn:IsValid() then
        -- The call wants 9 arguments (the earlier try with 6 was refused). Known shape in UE 5.4:
        -- WorldContext, LevelName, Location, Rotation, bOutSuccess, OptionalLevelNameOverride, OptionalLevelStreamingClass, bLoadAsTempPackage, (return slot)
        -- The success flag (bOutSuccess) is an OUT parameter, so it must be given as a table, e.g. {}.
        -- Signature confirmed from the game: (WorldContext, LevelName: Str, Location, Rotation, bOutSuccess: Bool OUT,
        -- OptionalLevelNameOverride: Str, OptionalLevelStreamingClass: Class, bLoadAsTempPackage: Bool) -> LevelStreamingDynamic.
        -- The earlier tries failed in push_strproperty, so test whether an EMPTY text value is the problem by giving real names.
        -- Plain Lua strings fail in push_strproperty (even non-empty ones). Try the engine's own text type, if this UE4SS has one,
        -- and the game's own LoadStreamLevel (also text-based) so we learn whether any string parameter can be passed at all.
        log("  FString constructor available: " .. tostring(type(FString)))
        local attempts = {}
        if type(FString) == "function" then
            attempts[#attempts + 1] = { "FString names", function()
                return dyn:LoadLevelInstance(world, FString("/Game/Maps/Vignette_Theatre"), where, rot, {}, FString("PortalHubTest"), dynClass, false) end }
        end
        local custom0 = StaticFindObject("/Script/AbioticFactor.Default__LevelStreamingCustom")
        if custom0 and custom0:IsValid() then
            attempts[#attempts + 1] = { "game LoadStreamLevel (plain string)", function()
                return custom0:LoadStreamLevel(world, "Vignette_Theatre", true, false, {}, {}) end }
            if type(FString) == "function" then
                attempts[#attempts + 1] = { "game LoadStreamLevel (FString)", function()
                    return custom0:LoadStreamLevel(world, FString("Vignette_Theatre"), true, false, {}, {}) end }
            end
        end        for _, a in ipairs(attempts) do
            local ok, res = pcall(a[2])
            local desc = ok and ("returned " .. tostring(res)) or ("FAILED: " .. tostring(res):match("^[^\r\n]*"))
            if ok and res ~= nil then
                local good, nm = pcall(function() return res:IsValid() and res:GetFName():ToString() or "(invalid)" end)
                desc = desc .. " -> " .. (good and nm or "?")
            end
            log("  LoadLevelInstance (" .. a[1] .. "): " .. desc)
            if ok then break end
        end
    end
    local after = #(FindAllOf("LevelStreamingDynamic") or {})
    log(string.format("  LevelStreamingDynamic objects: %d before, %d after", before, after))
    local custom = StaticFindObject("/Script/AbioticFactor.Default__LevelStreamingCustom")
    log("  game's LevelStreamingCustom library: " .. ((custom and custom:IsValid()) and "found" or "NOT found"))
end
RegisterKeyBind(Key.NUM_FOUR, function() ExecuteInGameThread(overlay_test) end)
RegisterKeyBind(Key.NUM_FIVE, function() ExecuteInGameThread(light_test) end)
RegisterKeyBind(Key.NUM_SIX, function() ExecuteInGameThread(rift_test) end)
RegisterKeyBind(Key.NUM_THREE, function() ExecuteInGameThread(stream_test) end)
RegisterKeyBind(Key.DECIMAL, function() ExecuteInGameThread(clear_fx) end)
log("prototype keys: NUMPAD 4 overlay, 5 pad-light colour, 6 rift colour, 3 level-stream test, NUMPAD . (decimal) clear effects")











------------------------------------------------------------------------------------------------------------------------
-- Prototype 3: can an existing, unused LevelStreamingDynamic slot be pointed at a different map WITHOUT passing text?
-- The game keeps 59 LevelStreamingDynamic objects, one per world. If one of them can be re-pointed at another package name (an FName,
-- which Lua can pass), a custom map could be streamed in without LoadLevelInstance. This step is READ-ONLY: it lists the objects,
-- what each is pointed at, and which relevant functions/properties exist. Nothing is changed.
--   NUMPAD * (multiply) = report
------------------------------------------------------------------------------------------------------------------------
local function slot_report()
    log("---- STREAMING SLOT report")
    local all = FindAllOf("LevelStreamingDynamic") or {}
    log("  objects: " .. #all)
    local first = true
    for i, ls in ipairs(all) do
        if ls:IsValid() then
            local name = ls:GetFName():ToString()
            local pkg = "?"
            local ok1, v1 = pcall(function() return ls:GetWorldAssetPackageFName():ToString() end)
            if ok1 then pkg = tostring(v1) end
            local loaded, visible = "?", "?"
            pcall(function() loaded = tostring(ls:IsLevelLoaded()) end)
            pcall(function() visible = tostring(ls:IsLevelVisible()) end)
            local off = "?"
            pcall(function() local t = ls.LevelTransform.Translation; off = string.format("%.0f, %.0f, %.0f", t.X, t.Y, t.Z) end)
            log(string.format("  %2d. %-26s pkg=%-44s loaded=%-5s visible=%-5s offset=%s", i, name, pkg, loaded, visible, off))
            if first then
                first = false
                log("  -- members available on the first object:")
                for _, member in ipairs({ "SetWorldAssetByPackageName", "SetShouldBeLoaded", "SetShouldBeVisible", "SetLevelTransform",
                                          "GetWorldAssetPackageFName", "GetWorldAssetPackageName", "WorldAsset", "PackageNameToLoad", "LevelTransform",
                                          "bShouldBeLoaded", "bShouldBeVisible", "bInitiallyLoaded", "bInitiallyVisible", "bDisableDistanceStreaming" }) do
                    local ok, v = pcall(function() return ls[member] end)
                    log(string.format("       %-28s %s", member, ok and type(v) or "error"))
                end
            end
        end
    end
    log("---- STREAMING SLOT report done")
end
RegisterKeyBind(Key.MULTIPLY, function() ExecuteInGameThread(slot_report) end)
log("prototype 3 key: NUMPAD * (multiply) = list the game's streaming slots (read-only)")

------------------------------------------------------------------------------------------------------------------------
-- Prototype 4: does the packaged loader Blueprint actually create a level instance when its BeginPlay runs?
--   NUMPAD / (divide) = call BeginPlay again on the test loader, then (2 s later) report whether the streaming list grew.
-- It also reads the loader's own variables if the Blueprint has them (BeginPlayRan, LoadSucceeded). Read-only apart from the one call.
------------------------------------------------------------------------------------------------------------------------
local function count_streaming()
    local n = 0
    local world = UEHelpers.GetWorld()
    if world and world:IsValid() then
        pcall(function() world.StreamingLevels:ForEach(function() n = n + 1 end) end)
    end
    return n
end

local function loader_test()
    log("---- LOADER TEST")
    local loaders = FindAllOf("BP_CordonaTestLoader_C") or {}
    local loader
    for _, a in ipairs(loaders) do if a:IsValid() then loader = a end end
    if not loader then log("  no BP_CordonaTestLoader_C actor in the world") return end
    log("  loader: " .. loader:GetFName():ToString())
    for _, v in ipairs({ "BeginPlayRan", "LoadSucceeded", "LevelInstance" }) do
        local ok, val = pcall(function() return loader[v] end)
        log(string.format("  variable %-14s %s", v, ok and describe(val) or "(not on this Blueprint)"))
    end
    local before = count_streaming()
    log("  streaming levels before: " .. before)
    local ok, err = pcall(function() loader:ReceiveBeginPlay() end)
    log("  called ReceiveBeginPlay: " .. (ok and "ok" or ("FAILED: " .. tostring(err))))
    ExecuteWithDelay(2000, function()
        ExecuteInGameThread(function()
            log("  streaming levels 2 s later: " .. count_streaming() .. " (before: " .. before .. ")")
            for _, v in ipairs({ "BeginPlayRan", "LoadSucceeded" }) do
                local ok2, val = pcall(function() return loader[v] end)
                if ok2 then log("  variable " .. v .. " = " .. describe(val)) end
            end
            log("---- package access (full object paths; a cooked Blueprint exists as its _C class)")
            local helpers = StaticFindObject("/Script/AssetRegistry.Default__AssetRegistryHelpers")
            for _, p in ipairs({
                { "map",    "/Game/Mods/CordonaTest/Maps/CordonaTest_L0", "CordonaTest_L0" },
                { "cube",   "/Game/Mods/CordonaTest/Cube",                "Cube" },
                { "loader", "/Game/Mods/CordonaTest/BP_CordonaTestLoader", "BP_CordonaTestLoader_C" },
            }) do
                local full = p[2] .. "." .. p[3]
                local okL = pcall(LoadAsset, full)
                local obj = StaticFindObject(full)
                local viaLoad = obj and obj:IsValid()
                local viaReg = false
                if helpers and helpers:IsValid() then
                    pcall(function()
                        local o = helpers:GetAsset({ PackageName = UEHelpers.FindOrAddFName(p[2]), AssetName = UEHelpers.FindOrAddFName(p[3]) })
                        viaReg = (o and o:IsValid()) and true or false
                    end)
                end
                local cls = "?"
                if viaLoad then pcall(function() cls = obj:GetClass():GetFName():ToString() end) end
                log(string.format("  %-7s %-52s LoadAsset call %s | found by path: %s%s | found by asset registry: %s", p[1], full,
                    okL and "ok" or "failed", tostring(viaLoad), viaLoad and (" (" .. cls .. ")") or "", tostring(viaReg)))
            end
            log("---- direct load from Lua, using the engine's text type for the level name")
            log("  FString constructor: " .. type(FString))
            local world = UEHelpers.GetWorld()
            local dyn = StaticFindObject("/Script/Engine.Default__LevelStreamingDynamic")
            local dynClass = StaticFindObject("/Script/Engine.LevelStreamingDynamic")
            if type(FString) == "function" and world and world:IsValid() and dyn and dyn:IsValid() then
                local n0 = count_streaming()
                local ok3, res = pcall(function()
                    return dyn:LoadLevelInstance(world, FString("/Game/Mods/CordonaTest/Maps/CordonaTest_L0"), { X = 1100000.0, Y = 1400000.0, Z = 0.0 },
                        { Pitch = 0.0, Yaw = 0.0, Roll = 0.0 }, {}, FString("CordonaTestDirect"), dynClass, false)
                end)
                log("  LoadLevelInstance with FString: " .. (ok3 and ("returned " .. tostring(res)) or ("FAILED: " .. tostring(res):match("^[^\r\n]*"))))
                log("  streaming levels: " .. n0 .. " -> " .. count_streaming())
            else
                log("  skipped (no FString constructor in this UE4SS build)")
            end
            log("---- LOADER TEST done")
        end)
    end)
end
RegisterKeyBind(Key.DIVIDE, function() ExecuteInGameThread(loader_test) end)
log("prototype 4 key: NUMPAD / (divide) = loader test")


