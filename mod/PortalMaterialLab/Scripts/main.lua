-- PortalMaterialLab: the project's read-only survey lab. It never changes the game; it only logs what it finds, so features can be
-- designed from facts. (It started as a material-swap experiment, hence the name; those experiments are finished and were removed, they
-- are in the git history.) Keys, all read-only:
--   NUMPAD 4        sky domes: dome meshes, their materials and parameters, and the sky Blueprint actors
--   NUMPAD 5        hazards: water / pain-causing volumes, hazard-style classes, underwater and damage data tables
--   NUMPAD 6        NPCs: NPC, creature and spawner classes, plus the settings of one spawner and one NPC
--   CTRL + NUMPAD + the player's lighting state: the controller's FX rows, the real light values, and the DT_LevelFX row names
-- Free keys: NUMPAD 0 1 2 3 7 8 9, NUMPAD . * / - and +  (NUMPAD 1 and 2 belong to PortalHub). Note: Shift + a numpad digit does not work,
-- because with Num Lock on Shift turns the digit into Home / arrow keys.
-- Rule: every object is checked with IsValid() before anything is called on it (a call on an invalid object crashes the game).


local function log(msg) print("[MaterialLab] " .. msg .. "\n") end

local function short(path) return (path:gsub("^.*/", ""):gsub("%..*$", "")) end

local function pad_id(t)
    local ok, id = pcall(function() return t.MyTeleporterID:ToString() end)
    if ok then return id end
    return nil
end

local function class_of(obj)
    if not (obj and obj:IsValid()) then return "?" end
    local cls = obj:GetClass()
    if not (cls and cls:IsValid()) then return "?" end
    return cls:GetFName():ToString()
end

local function lower_has(s, words)
    s = s:lower()
    for _, w in ipairs(words) do if s:find(w, 1, true) then return true end end
    return false
end

local function loc_text(actor)
    local ok, t = pcall(function() local l = actor:K2_GetActorLocation(); return string.format("%.0f, %.0f, %.0f", l.X, l.Y, l.Z) end)
    return ok and t or "?"
end

local function rot_text(actor)
    local ok, t = pcall(function() local r = actor:K2_GetActorRotation(); return string.format("pitch %.1f yaw %.1f roll %.1f", r.Pitch, r.Yaw, r.Roll) end)
    return ok and t or "?"
end

-- Logs the readable simple settings (numbers, booleans, names) of an object, up to a limit.

local function dump_settings(obj, label, limit)
    if not (obj and obj:IsValid()) then return end
    local cls = obj:GetClass()
    if not (cls and cls:IsValid()) then return end
    log("    settings of " .. label .. ":")
    local n = 0
    pcall(function()
        cls:ForEachProperty(function(prop)
            if n >= limit then return end
            local name = prop:GetFName():ToString()
            local ok, v = pcall(function() return obj[name] end)
            if not ok then return end
            local t, shown = type(v), nil
            if t == "number" or t == "boolean" or t == "string" then shown = tostring(v)
            elseif t == "userdata" then
                local ok2, s = pcall(function() if v.GetFullName then return nil end; return v:ToString() end)
                if ok2 and type(s) == "string" then shown = s end
            end
            if shown then n = n + 1; log(string.format("      %-36s %s", name, shown)) end
        end)
    end)
    if n == 0 then log("      (no readable simple settings)") end
end

local FX_STRUCT = "/Game/Blueprints/Data/LevelFXData_Struct.LevelFXData_Struct"
local FX_TABLE = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"

local function value_text(v)
    local t = type(v)
    if t == "number" or t == "boolean" or t == "string" then return tostring(v) end
    if t == "nil" then return "nil" end
    local out
    pcall(function()
        if v.R ~= nil and v.G ~= nil and v.B ~= nil then out = string.format("(%.3f, %.3f, %.3f, %.3f)", v.R, v.G, v.B, v.A or 1)
        elseif v.Pitch ~= nil then out = string.format("(pitch %.1f, yaw %.1f, roll %.1f)", v.Pitch, v.Yaw, v.Roll) end
    end)
    if out then return out end
    pcall(function() if not v.GetFullName then out = v:ToString() end end)
    return out or "<object>"
end

local FX_TABLE = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"

local function value_text(v)
    local t = type(v)
    if t == "number" or t == "boolean" or t == "string" then return tostring(v) end
    if t == "nil" then return "nil" end
    local out
    pcall(function()
        if v.R ~= nil and v.G ~= nil and v.B ~= nil then out = string.format("(%.3f, %.3f, %.3f, %.3f)", v.R, v.G, v.B, v.A or 1)
        elseif v.Pitch ~= nil then out = string.format("(pitch %.1f, yaw %.1f, roll %.1f)", v.Pitch, v.Yaw, v.Roll) end
    end)
    if out then return out end
    pcall(function() if not v.GetFullName then out = v:ToString() end end)
    return out or "<object>"
end

local function value_text(v)
    local t = type(v)
    if t == "number" or t == "boolean" or t == "string" then return tostring(v) end
    if t == "nil" then return "nil" end
    local out
    pcall(function()
        if v.R ~= nil and v.G ~= nil and v.B ~= nil then out = string.format("(%.3f, %.3f, %.3f, %.3f)", v.R, v.G, v.B, v.A or 1)
        elseif v.Pitch ~= nil then out = string.format("(pitch %.1f, yaw %.1f, roll %.1f)", v.Pitch, v.Yaw, v.Roll) end
    end)
    if out then return out end
    pcall(function() if not v.GetFullName then out = v:ToString() end end)
    return out or "<object>"
end

local function short_field(n) return (n:gsub("_%d+_%x+$", "")) end

local function dump_fx_struct(pc, prop, label)
    local ok, val = pcall(function() return pc[prop] end)
    if not ok or val == nil then log("    " .. label .. ": unreadable"); return end
    local def = StaticFindObject(FX_STRUCT)
    if not (def and def:IsValid()) then log("    " .. label .. ": struct definition not found"); return end
    log("    " .. label .. ":")
    pcall(function()
        def:ForEachProperty(function(p)
            local n = p:GetFName():ToString()
            local okv, v = pcall(function() return val[n] end)
            if okv then log(string.format("      %-28s %s", short_field(n), value_text(v))) end
        end)
    end)
end

local function dump_fx_struct(pc, prop, label)
    local ok, val = pcall(function() return pc[prop] end)
    if not ok or val == nil then log("    " .. label .. ": unreadable"); return end
    local def = StaticFindObject(FX_STRUCT)
    if not (def and def:IsValid()) then log("    " .. label .. ": struct definition not found"); return end
    log("    " .. label .. ":")
    pcall(function()
        def:ForEachProperty(function(p)
            local n = p:GetFName():ToString()
            local okv, v = pcall(function() return val[n] end)
            if okv then log(string.format("      %-28s %s", short_field(n), value_text(v))) end
        end)
    end)
end

-- Row names of DT_LevelFX, read through the engine's own data-table function (names pass as FName, no text needed).

local fx_rows = nil
local function level_fx_rows()
    if fx_rows then return fx_rows end
    local dt = StaticFindObject(FX_TABLE)
    if not (dt and dt:IsValid()) then log("  DT_LevelFX is not loaded"); return nil end
    local rows = {}
    local lib = StaticFindObject("/Script/Engine.Default__DataTableFunctionLibrary")
    if lib and lib:IsValid() then
        local out = {}
        local ok, a, b = pcall(function() return lib:GetDataTableRowNames(dt, out) end)
        log(string.format("  GetDataTableRowNames: call %s, out table has %d entries (return types: %s, %s)", tostring(ok), #out, type(a), type(b)))
        -- turn one array element into text, trying the ways UE4SS can hand an FName back
        local function text_of(x)
            local s
            if pcall(function() s = x:ToString() end) and type(s) == "string" and s ~= "" then return s end
            if pcall(function() s = x:get():ToString() end) and type(s) == "string" and s ~= "" then return s end
            if pcall(function() s = tostring(x) end) and type(s) == "string" and s ~= "" then return s end
            return nil
        end
        if #out > 0 then
            local first = out[1]
            local okT, tn = pcall(function() return type(first) end)
            local okS, sv = pcall(function() return tostring(first) end)
            log(string.format("  first entry: type %s, tostring %s", okT and tn or "?", okS and sv or "?"))
        end
        for i = 1, #out do
            local s = text_of(out[i])
            if s then rows[#rows + 1] = s end
        end
        if #rows == 0 and ok and type(b) == "table" then
            for i = 1, #b do local s = text_of(b[i]); if s then rows[#rows + 1] = s end end
        end
        if #rows > 0 and rows[1]:find("^userdata") then rows = {} end    -- tostring gave only a pointer: not usable
    end
    if #rows == 0 then
        local okR = pcall(function() dt.RowMap:ForEach(function(k) rows[#rows + 1] = k:get():ToString() end) end)
        log("  RowMap:ForEach fallback: " .. tostring(okR) .. ", rows " .. #rows)
    end
    table.sort(rows)
    fx_rows = rows
    return rows
end
local function level_fx_rows()
    if fx_rows then return fx_rows end
    local dt = StaticFindObject(FX_TABLE)
    if not (dt and dt:IsValid()) then log("  DT_LevelFX is not loaded"); return nil end
    local rows = {}
    local lib = StaticFindObject("/Script/Engine.Default__DataTableFunctionLibrary")
    if lib and lib:IsValid() then
        local out = {}
        local ok, a, b = pcall(function() return lib:GetDataTableRowNames(dt, out) end)
        log(string.format("  GetDataTableRowNames: call %s, out table has %d entries (return types: %s, %s)", tostring(ok), #out, type(a), type(b)))
        -- turn one array element into text, trying the ways UE4SS can hand an FName back
        local function text_of(x)
            local s
            if pcall(function() s = x:ToString() end) and type(s) == "string" and s ~= "" then return s end
            if pcall(function() s = x:get():ToString() end) and type(s) == "string" and s ~= "" then return s end
            if pcall(function() s = tostring(x) end) and type(s) == "string" and s ~= "" then return s end
            return nil
        end
        if #out > 0 then
            local first = out[1]
            local okT, tn = pcall(function() return type(first) end)
            local okS, sv = pcall(function() return tostring(first) end)
            log(string.format("  first entry: type %s, tostring %s", okT and tn or "?", okS and sv or "?"))
        end
        for i = 1, #out do
            local s = text_of(out[i])
            if s then rows[#rows + 1] = s end
        end
        if #rows == 0 and ok and type(b) == "table" then
            for i = 1, #b do local s = text_of(b[i]); if s then rows[#rows + 1] = s end end
        end
        if #rows > 0 and rows[1]:find("^userdata") then rows = {} end    -- tostring gave only a pointer: not usable
    end
    if #rows == 0 then
        local okR = pcall(function() dt.RowMap:ForEach(function(k) rows[#rows + 1] = k:get():ToString() end) end)
        log("  RowMap:ForEach fallback: " .. tostring(okR) .. ", rows " .. #rows)
    end
    table.sort(rows)
    fx_rows = rows
    return rows
end

local PC_FX_PROPS = { "ActiveLevelName", "ActiveLevelFXName", "ActiveSubFXName", "ActiveWeatherFXName", "OverrideLevelFXName", "CheatLevelFXName",
                      "Day_FX_Row", "Night_FX_Row", "PreviousDayFXRow", "PreviousNightFXRow", "DisableAutomaticFX", "HasDynamicSkyboxActive",
                      "IsDebugLevel", "CurrentFXLevel", "LastLevelFXTransitionTime" }

local function player_controller()
    local pc = FindFirstOf("Abiotic_PlayerController_C")
    if pc and pc:IsValid() then return pc end
    return nil
end

local function fx_player_survey()
    log("---- PLAYER FX SURVEY")
    local pc = player_controller()
    if not pc then log("  no Abiotic_PlayerController_C found"); return end
    local pawn = pc.Pawn
    if pawn and pawn:IsValid() then log("  player at " .. loc_text(pawn)) end
    log("  -- controller FX state")
    for _, name in ipairs(PC_FX_PROPS) do
        local ok, v = pcall(function() return pc[name] end)
        log(string.format("    %-28s %s", name, ok and value_text(v) or "unreadable"))
    end
    local okV, inV = pcall(function()
        local lib = StaticFindObject("/Game/Blueprints/Libraries/AbioticFunctionLibrary.Default__AbioticFunctionLibrary_C")
        return lib:PlayerIsInVignette(pc, pc)
    end)
    log(string.format("    %-28s %s", "PlayerIsInVignette", okV and tostring(inV) or ("call failed: " .. tostring(inV))))
    local mgr = FindFirstOf("DayNightManager_C")
    if mgr and mgr:IsValid() then
        local okW, w = pcall(function() return mgr.CurrentWeatherEvent:ToString() end)
        log(string.format("    %-28s %s", "CurrentWeatherEvent", okW and w or "unreadable"))
    end
    dump_fx_struct(pc, "CurrentDaytimeFX", "CurrentDaytimeFX (the day values in force)")
    dump_fx_struct(pc, "CurrentNighttimeFX", "CurrentNighttimeFX (the night values in force)")
    log("  -- what the lights are actually set to right now")
    for _, e in ipairs({ { "DirectionalLight", "LightComponent", { "Intensity", "LightColor", "Temperature" } },
                         { "SkyLight", "LightComponent", { "Intensity", "LightColor" } },
                         { "ExponentialHeightFog", "Component", { "FogDensity", "FogHeightFalloff", "FogInscatteringColor", "FogMaxOpacity" } } }) do
        local a = FindFirstOf(e[1])
        if a and a:IsValid() then
            local okc, comp = pcall(function() return a[e[2]] end)
            if okc and comp and comp:IsValid() then
                for _, f in ipairs(e[3]) do
                    local okf, v = pcall(function() return comp[f] end)
                    log(string.format("    %-22s %-22s %s", e[1], f, okf and value_text(v) or "unreadable"))
                end
            end
        end
    end
    local rows = level_fx_rows()
    if rows then
        log(string.format("  -- DT_LevelFX rows (%d)", #rows))
        local line = "    "
        for _, r in ipairs(rows) do
            if #line + #r > 150 then log(line); line = "    " end
            line = line .. " " .. r
        end
        if #line > 4 then log(line) end
    end
    log("---- PLAYER FX SURVEY done")
end

------------------------------------------------------------------------------------------------------------------------
-- Prototype 8: three read-only surveys for the next features. Nothing is changed.
--   NUMPAD 4 = sky domes: every dome-like mesh actor with its mesh and material paths and material parameter values, and the
--                      game's sky Blueprint actors with their object properties. Run in Stone Garden (day and night) and an outdoor world.
--   NUMPAD 5 = hazards: engine volumes (water, pain-causing), underwater / drowning / oxygen classes, and the underwater FX table.
--                      Run in Albatross (standing near the water) and once in the Facility.
--   NUMPAD 6 = NPCs: NPC / creature / spawner classes with counts, positions and the settings of one of each, and NPC data tables.
--                      Run in the Facility near NPCs.
------------------------------------------------------------------------------------------------------------------------
local function full_name(o)
    if o and o:IsValid() then
        local ok, s = pcall(function() return o:GetFullName() end)
        if ok then return s end
    end
    return "none"
end

-- parameter values of a material instance (scalar and vector), as far as UE4SS lets us read them
local function dump_material_params(mat, indent)
    if not (mat and mat:IsValid()) then return end
    local parent = "?"
    pcall(function() parent = full_name(mat.Parent) end)
    log(indent .. "material " .. full_name(mat) .. "  (parent " .. parent .. ")")
    local n = 0
    pcall(function()
        mat.ScalarParameterValues:ForEach(function(_, v)
            local e = v:get()
            n = n + 1
            log(string.format("%s    scalar %-30s %s", indent, e.ParameterInfo.Name:ToString(), tostring(e.ParameterValue)))
        end)
    end)
    pcall(function()
        mat.VectorParameterValues:ForEach(function(_, v)
            local e = v:get()
            n = n + 1
            log(string.format("%s    vector %-30s %s", indent, e.ParameterInfo.Name:ToString(), value_text(e.ParameterValue)))
        end)
    end)
    if n == 0 then log(indent .. "    (no readable parameters)") end
end

local function sky_dome_survey()
    log("---- SKY DOME SURVEY")
    local pc = FindFirstOf("PlayerController")
    local ploc = "?"
    if pc and pc:IsValid() and pc.Pawn and pc.Pawn:IsValid() then ploc = loc_text(pc.Pawn) end
    log("  player at " .. ploc)
    local WORDS = { "sky", "dome", "bubble", "backdrop", "horizon", "panorama" }
    log("  -- dome-like static mesh actors")
    local listed = 0
    for _, a in ipairs(FindAllOf("StaticMeshActor") or {}) do
        if a:IsValid() and listed < 12 then
            local comp = a.StaticMeshComponent
            local meshName = "?"
            local okM, mesh = pcall(function() return comp.StaticMesh end)
            if okM and mesh and mesh:IsValid() then meshName = mesh:GetFName():ToString() end
            if lower_has(a:GetFName():ToString(), WORDS) or lower_has(meshName, WORDS) then
                listed = listed + 1
                local scale = "?"
                pcall(function() local s = a:GetActorScale3D(); scale = string.format("%.2f, %.2f, %.2f", s.X, s.Y, s.Z) end)
                log(string.format("  %s  at %s  facing %s  scale %s", a:GetFName():ToString(), loc_text(a), rot_text(a), scale))
                log("    mesh " .. full_name(mesh))
                local nm = 0
                pcall(function() nm = comp:GetNumMaterials() end)
                for i = 0, math.min(nm, 3) - 1 do
                    local okMat, m = pcall(function() return comp:GetMaterial(i) end)
                    if okMat then dump_material_params(m, "    ") end
                end
            end
        end
    end
    if listed == 0 then log("  (none)") end
    log("  -- sky Blueprint actors")
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local cname = class_of(a)
            if lower_has(cname, { "skydome", "skybox", "sky_" }) then
                log(string.format("  %s (%s) at %s", a:GetFName():ToString(), cname, loc_text(a)))
                local cls = a:GetClass()
                pcall(function()
                    cls:ForEachProperty(function(prop)
                        local name = prop:GetFName():ToString()
                        local ok, v = pcall(function() return a[name] end)
                        if ok and v ~= nil then
                            local t = type(v)
                            if t == "number" or t == "boolean" or t == "string" then
                                log(string.format("      %-34s %s", name, tostring(v)))
                            elseif t == "userdata" then
                                local isObj = false
                                pcall(function() isObj = (v.IsValid ~= nil) end)
                                if isObj then
                                    if v:IsValid() then
                                        log(string.format("      %-34s -> %s", name, full_name(v)))
                                        local isMat = false
                                        pcall(function() isMat = (v.ScalarParameterValues ~= nil) end)
                                        if isMat then dump_material_params(v, "        ") end
                                    end
                                else
                                    log(string.format("      %-34s %s", name, value_text(v)))
                                end
                            end
                        end
                    end)
                end)
            end
        end
    end
    log("---- SKY DOME SURVEY done")
end

local function hazard_survey()
    log("---- HAZARD SURVEY")
    local pc = FindFirstOf("PlayerController")
    if pc and pc:IsValid() and pc.Pawn and pc.Pawn:IsValid() then log("  player at " .. loc_text(pc.Pawn)) end
    log("  -- physics volumes (water / pain-causing ones)")
    local n, shown = 0, 0
    for _, v in ipairs(FindAllOf("PhysicsVolume") or {}) do
        if v:IsValid() then
            n = n + 1
            local water, pain, dps = false, false, 0
            pcall(function() water = v.bWaterVolume end)
            pcall(function() pain = v.bPainCausing end)
            pcall(function() dps = v.DamagePerSec end)
            if (water or pain) and shown < 25 then
                shown = shown + 1
                log(string.format("  %s (%s) at %s  water=%s pain=%s damagePerSec=%s", v:GetFName():ToString(), class_of(v), loc_text(v), tostring(water), tostring(pain), tostring(dps)))
            end
        end
    end
    log(string.format("  %d physics volume(s) in total, %d water or pain-causing", n, shown))
    log("  -- game classes about water, drowning, oxygen, damage areas")
    local WORDS = { "underwater", "drown", "oxygen", "swim", "water", "radiation", "toxic", "acid", "lava", "kill", "void", "pain", "hurt", "damagevolume", "damagezone" }
    local counts, order, example = {}, {}, {}
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local cname = class_of(a)
            if lower_has(cname, WORDS) and not lower_has(cname, { "deployed_", "figurine", "painting", "cooler", "filter" }) then
                if not counts[cname] then counts[cname] = 0; order[#order + 1] = cname; example[cname] = a end
                counts[cname] = counts[cname] + 1
            end
        end
    end
    for i, cname in ipairs(order) do
        if i > 25 then break end
        log(string.format("  %-44s x%d  e.g. %s at %s", cname, counts[cname], example[cname]:GetFName():ToString(), loc_text(example[cname])))
        if i <= 6 then dump_settings(example[cname], cname, 40) end
    end
    if #order == 0 then log("  (none by name)") end
    log("  -- underwater / damage data tables")
    for _, dt in ipairs(FindAllOf("DataTable") or {}) do
        if dt:IsValid() then
            local name = dt:GetFName():ToString()
            if lower_has(name, { "underwater", "damage", "hazard", "drown", "oxygen" }) then
                log("  " .. dt:GetFullName())
                local lib = StaticFindObject("/Script/Engine.Default__DataTableFunctionLibrary")
                local out = {}
                if lib and lib:IsValid() then pcall(function() lib:GetDataTableRowNames(dt, out) end) end
                local rows = {}
                for i = 1, #out do
                    local ok, s = pcall(function() return tostring(out[i]) end)
                    if ok then rows[#rows + 1] = s end
                end
                log("    rows (" .. #rows .. "): " .. table.concat(rows, " "):sub(1, 400))
            end
        end
    end
    log("---- HAZARD SURVEY done")
end

local function npc_survey()
    log("---- NPC SURVEY")
    local pc = FindFirstOf("PlayerController")
    if pc and pc:IsValid() and pc.Pawn and pc.Pawn:IsValid() then log("  player at " .. loc_text(pc.Pawn)) end
    local WORDS = { "npc", "creature", "enemy", "spawn", "pest", "mob", "critter", "ai_" }
    local counts, order, example = {}, {}, {}
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local cname = class_of(a)
            if lower_has(cname, WORDS) then
                if not counts[cname] then counts[cname] = 0; order[#order + 1] = cname; example[cname] = a end
                counts[cname] = counts[cname] + 1
            end
        end
    end
    table.sort(order)
    log(string.format("  %d NPC-like class(es)", #order))
    for i, cname in ipairs(order) do
        if i > 60 then log("  ..."); break end
        log(string.format("  %-46s x%-3d e.g. %s at %s", cname, counts[cname], example[cname]:GetFName():ToString(), loc_text(example[cname])))
    end
    -- the settings of one spawner and one NPC, to see what an NPC needs
    local shownSpawner, shownNpc = false, false
    for _, cname in ipairs(order) do
        local a = example[cname]
        local low = cname:lower()
        if not shownSpawner and low:find("spawn", 1, true) then shownSpawner = true; dump_settings(a, cname, 60) end
        if not shownNpc and low:find("npc", 1, true) and not low:find("spawn", 1, true) then shownNpc = true; dump_settings(a, cname, 80) end
    end
    log("  -- NPC / enemy data tables that are loaded")
    for _, dt in ipairs(FindAllOf("DataTable") or {}) do
        if dt:IsValid() then
            local name = dt:GetFName():ToString()
            if lower_has(name, { "npc", "enemy", "creature", "spawn", "faction", "ai" }) then log("  " .. dt:GetFullName()) end
        end
    end
    log("---- NPC SURVEY done")
end

RegisterKeyBind(Key.NUM_FOUR, function() ExecuteInGameThread(sky_dome_survey) end)
RegisterKeyBind(Key.NUM_FIVE, function() ExecuteInGameThread(hazard_survey) end)
RegisterKeyBind(Key.NUM_SIX, function() ExecuteInGameThread(npc_survey) end)
pcall(function() RegisterKeyBind(Key.ADD, { ModifierKey.CONTROL }, function() ExecuteInGameThread(fx_player_survey) end) end)
log("keys: NUMPAD 4 = sky domes, NUMPAD 5 = hazards, NUMPAD 6 = NPCs, CTRL+NUMPAD+ = player lighting (all read-only)")

------------------------------------------------------------------------------------------------------------------------
-- Status (read-only): NUMPAD 9 logs the controller's ActiveLevelName, PlayerIsInVignette, the weather FX name and the weather event.
-- NOTE: never write ActiveLevelName from Lua. It is a STRING property (StrProperty), not a name; writing an FName into it corrupted the
-- value and the game crashed when it was written again. Check a property's type in UE4SS_ObjectDump.txt before writing to it.
------------------------------------------------------------------------------------------------------------------------
local function vignette_status(tag)
    local pc = player_controller()
    if not pc then log(tag .. ": no controller") return end
    local okL, lvl = pcall(function() return pc.ActiveLevelName:ToString() end)
    local okV, inV = pcall(function()
        local lib = StaticFindObject("/Game/Blueprints/Libraries/AbioticFunctionLibrary.Default__AbioticFunctionLibrary_C")
        return lib:PlayerIsInVignette(pc, pc)
    end)
    local okW, wfx = pcall(function() return pc.ActiveWeatherFXName:ToString() end)
    local weather = "?"
    local mgr = FindFirstOf("DayNightManager_C")
    if mgr and mgr:IsValid() then pcall(function() weather = mgr.CurrentWeatherEvent:ToString() end) end
    log(string.format("%s: ActiveLevelName=%s  PlayerIsInVignette=%s  ActiveWeatherFXName=%s  CurrentWeatherEvent=%s",
        tag, okL and lvl or "?", okV and tostring(inV) or "call failed", okW and wfx or "?", weather))
end
RegisterKeyBind(Key.NUM_NINE, function() ExecuteInGameThread(function() vignette_status("status") end) end)
log("status key: NUMPAD 9 = level name, vignette and weather status (read-only)")

------------------------------------------------------------------------------------------------------------------------
-- Level table survey (read-only), NUMPAD 8. The game finds the level the player is in through its level manager, then looks that level
-- up in DT_Levels (rows of LevelMetadata_Struct: LevelFileName, IsVignette, EntranceTeleporter, ...). The row it lands on becomes the
-- controller's ActiveLevelName, which PlayerIsInVignette, the respawn menu and the weather read. A custom world has no row, so the game
-- keeps the last one (Facility). This logs every row and what the level manager reports where the player stands.
------------------------------------------------------------------------------------------------------------------------
local LEVELS_TABLE = "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels"
local LEVEL_STRUCT = "/Game/Blueprints/Data/LevelMetadata_Struct.LevelMetadata_Struct"

local function text_of(v)
    if v == nil then return "nil" end
    local t = type(v)
    if t == "string" or t == "number" or t == "boolean" then return tostring(v) end
    local s
    if pcall(function() s = v:ToString() end) and type(s) == "string" then return s end
    if pcall(function() s = v.RowName:ToString() end) and type(s) == "string" then return "row " .. s end
    if pcall(function() s = v:get():ToString() end) and type(s) == "string" then return s end
    return value_text(v)
end

local function row_fields(data)
    local def = StaticFindObject(LEVEL_STRUCT)
    local parts = {}
    if not (def and def:IsValid()) then return "(struct definition not found)" end
    pcall(function()
        def:ForEachProperty(function(p)
            local n = p:GetFName():ToString()
            local okv, v = pcall(function() return data[n] end)
            parts[#parts + 1] = short_field(n) .. "=" .. (okv and text_of(v) or "?")
        end)
    end)
    return table.concat(parts, "  ")
end

local function level_table_survey()
    log("---- LEVEL TABLE SURVEY")
    local dt = StaticFindObject(LEVELS_TABLE)
    if not (dt and dt:IsValid()) then log("  DT_Levels is not loaded"); return end
    log("  table: " .. dt:GetFullName())
    -- rows, through UE4SS's own data-table API
    local names = {}
    local okN, err = pcall(function()
        local r = dt:GetRowNames()
        for i = 1, #r do names[#names + 1] = text_of(r[i]) end
    end)
    log(string.format("  GetRowNames: %s, %d row(s)%s", tostring(okN), #names, okN and "" or (" (" .. tostring(err) .. ")")))
    for _, name in ipairs(names) do
        local okR, data = pcall(function() return dt:FindRow(name) end)
        if okR and data ~= nil then log("  [" .. name .. "] " .. row_fields(data))
        else log("  [" .. name .. "] FindRow failed: " .. tostring(data)) end
    end
    -- where the game thinks the player is
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not (pawn and pawn:IsValid()) then log("  no player pawn"); log("---- LEVEL TABLE SURVEY done"); return end
    local loc = pawn:K2_GetActorLocation()
    log(string.format("  player at %.0f, %.0f, %.0f", loc.X, loc.Y, loc.Z))
    pcall(function() log("  controller CurrentFXLevel: " .. text_of(pc.CurrentFXLevel)) end)
    local mgr = FindFirstOf("LevelManagerSubsystem")
    if mgr and mgr:IsValid() then
        local okA, at = pcall(function() return mgr:GetLevelAtLocation(loc) end)
        log("  level manager, level at the player's location: " .. (okA and text_of(at) or ("call failed: " .. tostring(at))))
        -- FindLatestLevelPlayerIsIn (soft-object out parameter) was removed after the run 5 crash in UE4SS's soft-object parameter code.
        -- It reported true in the Facility and false inside the Test World (2026-10-14).
    else
        log("  level manager subsystem not found")
    end
    local lib = StaticFindObject("/Script/AbioticFactor.Default__LevelStreamingCustom")
    if lib and lib:IsValid() then
        local okL, name = pcall(function() return lib:GetActorLevelName(pawn, pawn) end)
        log("  level the player actor belongs to: " .. (okL and text_of(name) or ("call failed: " .. tostring(name))))
    end
    -- the respawn menu: is one already built (then a hook on new menus never fires)?
    local menus = FindAllOf("W_RespawnOptions_C") or {}
    log(string.format("  respawn menus already built: %d", #menus))
    vignette_status("  status")
    log("---- LEVEL TABLE SURVEY done")
end
RegisterKeyBind(Key.NUM_EIGHT, function() ExecuteInGameThread(level_table_survey) end)
log("survey key: NUMPAD 8 = level table and where the game thinks the player is (read-only)")

------------------------------------------------------------------------------------------------------------------------
-- Vignette experiment (WRITES; in memory only, nothing here is saved to disk).
--   NUMPAD 0: add a DT_Levels row for the Test World (IsVignette, entrance = its arrival pad), then read it back.
--   NUMPAD . : while standing in the Test World, set the controller's ActiveLevelName to that row (a real Lua string, never an FName),
--              then ask the controller to re-check the weather, and log the status before and after.
-- The level manager reports no level inside a custom world, so the game should leave the value alone until the player walks back
-- into a Facility level.
------------------------------------------------------------------------------------------------------------------------
local TEST_ROW = "PortalHub_cordonatest_start"
local TEST_ENTRANCE = "cordonatest_start"
local FX_TABLE_PATH = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"

local function struct_field_names()
    local names = {}
    local def = StaticFindObject(LEVEL_STRUCT)
    if def and def:IsValid() then
        def:ForEachProperty(function(p) local n = p:GetFName():ToString(); names[short_field(n)] = n end)
    end
    return names
end

local function add_test_row()
    log("---- VIGNETTE EXPERIMENT: add row")
    local dt = StaticFindObject(LEVELS_TABLE)
    if not (dt and dt:IsValid()) then log("  DT_Levels is not loaded"); return end
    local okE, existing = pcall(function() return dt:FindRow(TEST_ROW) end)
    if okE and existing ~= nil then log("  row already there: " .. row_fields(existing)); return end
    local f = struct_field_names()
    for _, k in ipairs({ "ReleaseGroup", "LevelFileName", "LevelFXRow_Day", "LevelFXRow_Night", "SectorName",
                         "ResettablePortalWorld", "HasFacilityShakes", "IsVignette", "EntranceTeleporter" }) do
        if not f[k] then log("  field not found in the struct: " .. k .. " (stopping)"); return end
    end
    local fx = StaticFindObject(FX_TABLE_PATH)
    local row = {}
    row[f.ReleaseGroup] = 0
    row[f.LevelFileName] = FName(TEST_ROW)
    row[f.LevelFXRow_Day] = { DataTable = fx, RowName = FName("HGarden") }
    row[f.LevelFXRow_Night] = { DataTable = fx, RowName = FName("HGarden") }
    pcall(function() row[f.SectorName] = FText("Test World") end)
    row[f.ResettablePortalWorld] = false
    row[f.HasFacilityShakes] = false
    row[f.IsVignette] = true
    row[f.EntranceTeleporter] = FName(TEST_ENTRANCE)
    local okA, err = pcall(function() dt:AddRow(TEST_ROW, row) end)
    log("  AddRow: " .. tostring(okA) .. (okA and "" or (" (" .. tostring(err) .. ")")))
    local okR, back = pcall(function() return dt:FindRow(TEST_ROW) end)
    log("  read back: " .. ((okR and back ~= nil) and row_fields(back) or ("not found (" .. tostring(back) .. ")")))
    local okG, garden = pcall(function() return dt:FindRow("HGarden") end)
    log("  HGarden row untouched: " .. ((okG and garden ~= nil) and row_fields(garden) or "?"))
    log("---- VIGNETTE EXPERIMENT: add row done")
end

-- PlayerIsInVignette looks a DT_Levels row up by a name it reads straight off the controller (no string conversion in it), so
-- ActiveLevelName is not it. Try each name property in turn: set it to the test row, ask, put the old value back at once.
local NAME_CANDIDATES = { "ActiveLevelFXName", "ActiveSubFXName", "OverrideLevelFXName", "CheatLevelFXName", "Day_FX_Row", "Night_FX_Row",
                          "PreviousDayFXRow", "PreviousNightFXRow", "TerminalRespawnID", "ActiveWeatherFXName", "HeldTimer_LastTutorialPanelRow" }

local function in_vignette(pc)
    local lib = StaticFindObject("/Game/Blueprints/Libraries/AbioticFunctionLibrary.Default__AbioticFunctionLibrary_C")
    local ok, r = pcall(function() return lib:PlayerIsInVignette(pc, pc) end)
    if not ok then return "call failed" end
    return r
end

local function probe_vignette_name(pc)
    for _, prop in ipairs(NAME_CANDIDATES) do
        local okO, old = pcall(function() return pc[prop]:ToString() end)
        if not okO then
            log("  probe " .. prop .. ": unreadable")
        else
            local okW = pcall(function() pc[prop] = FName(TEST_ROW) end)
            local r = okW and in_vignette(pc) or nil
            pcall(function() pc[prop] = FName(old) end)
            local okB, back = pcall(function() return pc[prop]:ToString() end)
            log(string.format("  probe %-30s was %-24s -> PlayerIsInVignette=%s  (restored: %s)", prop, old, tostring(r), tostring(okB and back == old)))
        end
    end
end

-- Run 2 found it: PlayerIsInVignette looks DT_Levels up by ActiveLevelFXName (a NameProperty holding the DT_Levels ROW name, e.g.
-- "office1", "V_ISLAND"). ActiveLevelName (a string holding the map file name) is not read by the vignette check.

local function light_values()
    local function read(class, comp, prop)
        local a = FindFirstOf(class)
        if not (a and a:IsValid()) then return "?" end
        local ok, v = pcall(function() return a[comp][prop] end)
        return ok and string.format("%.2f", tonumber(v) or -1) or "?"
    end
    return string.format("sun %s  sky %s  fog %s", read("DirectionalLight", "LightComponent", "Intensity"),
        read("SkyLight", "LightComponent", "Intensity"), read("ExponentialHeightFog", "Component", "FogDensity"))
end

local function fx_status(tag)
    local pc = player_controller()
    if not pc then return end
    local function name_of(prop) local ok, v = pcall(function() return pc[prop]:ToString() end); return ok and v or "?" end
    local okA, auto = pcall(function() return pc.DisableAutomaticFX end)
    log(string.format("%s: ActiveLevelFXName=%s  Day_FX_Row=%s  Night_FX_Row=%s  ActiveWeatherFXName=%s  PlayerIsInVignette=%s  DisableAutomaticFX=%s  %s",
        tag, name_of("ActiveLevelFXName"), name_of("Day_FX_Row"), name_of("Night_FX_Row"), name_of("ActiveWeatherFXName"), tostring(in_vignette(pc)),
        okA and tostring(auto) or "?", light_values()))
end

-- Run 4: the weather check changed nothing even with the game's automatic lighting on, and TransitionToNewEnvironmentFX refused row DATA:
-- its DayFX / NightFX inputs are DataTableRowHandles (table + row name), not LevelFXData.
-- Run 5 CRASHED THE GAME (twice): calling the controller's "Attempt Level FXChange" with nil for its soft-object parameter (Level).
-- Crash dump: UE4SS!RC::LuaType::push_softobjectproperty+0x124, null read at 0x70; pcall cannot catch it.
-- NEVER pass nil, a table or anything made up to a SoftObjectProperty / soft class parameter from Lua with this UE4SS build.
-- Run 6 uses only calls already proven safe: write ActiveLevelFXName (NUMPAD .), and TransitionToNewEnvironmentFX with row handles (NUMPAD /).
local saved = nil     -- what NUMPAD * puts back

local function one_line(err) return (tostring(err):gsub("[\r\n]+%s*", " | ")):sub(1, 300) end

local function remember(pc)
    if saved then return end
    local function s(prop) local ok, v = pcall(function() return pc[prop]:ToString() end); return ok and v or nil end
    saved = { levelName = s("ActiveLevelName"), fxName = s("ActiveLevelFXName"), day = s("Day_FX_Row"), night = s("Night_FX_Row") }
    log(string.format("  kept for NUMPAD *: level %s, level row %s, lighting rows %s / %s",
        tostring(saved.levelName), tostring(saved.fxName), tostring(saved.day), tostring(saved.night)))
end

local function fx_handle(name)
    return { DataTable = StaticFindObject(FX_TABLE_PATH), RowName = FName(name) }
end

local function transition_to(pc, dayName, nightName, sector)
    pcall(function() pc.DisableAutomaticFX = false end)
    local okT, errT = pcall(function() pc:TransitionToNewEnvironmentFX(false, fx_handle(dayName), fx_handle(nightName), 1.0, FText(sector)) end)
    log(string.format("  TransitionToNewEnvironmentFX(%s / %s): %s%s", dayName, nightName, tostring(okT), okT and "" or (" (" .. one_line(errT) .. ")")))
    return okT
end

local function claim_test_level()
    log("---- VIGNETTE EXPERIMENT: claim level (run 6: ActiveLevelFXName only)")
    local dt = StaticFindObject(LEVELS_TABLE)
    local okE, existing = pcall(function() return dt:FindRow(TEST_ROW) end)
    if not (okE and existing ~= nil) then add_test_row() end
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not (pawn and pawn:IsValid()) then log("  no player pawn"); return end
    local loc = pawn:K2_GetActorLocation()
    if math.abs(loc.X - 1100000) > 100000 or math.abs(loc.Y - 1300000) > 100000 then
        log(string.format("  you are not in the Test World (at %.0f, %.0f); nothing changed", loc.X, loc.Y)); return
    end
    remember(pc)
    vignette_status("  before")
    fx_status("  before")
    local okW, err = pcall(function() pc.ActiveLevelFXName = FName(TEST_ROW) end)
    log("  write ActiveLevelFXName: " .. tostring(okW) .. (okW and "" or (" (" .. one_line(err) .. ")")))
    fx_status("  after write")
end

-- NUMPAD /: light the Test World with Stone Garden's lighting rows through the game's own lighting system (no manual light values).
local function borrow_lighting()
    log("---- VIGNETTE EXPERIMENT: borrow Stone Garden lighting")
    local pc = player_controller()
    if not pc then log("  no controller"); return end
    remember(pc)
    fx_status("  before")
    transition_to(pc, "HGarden", "HGarden", "Test World")
    fx_status("  right after")
    ExecuteWithDelay(2000, function() ExecuteInGameThread(function() fx_status("  2 s later") end) end)
    ExecuteWithDelay(6000, function() ExecuteInGameThread(function() fx_status("  6 s later") end) end)
end

local function release_test_level()
    log("---- VIGNETTE EXPERIMENT: put everything back")
    local pc = player_controller()
    if not pc then log("  no controller"); return end
    if not saved then log("  nothing to put back (NUMPAD . and NUMPAD / were not used since the lab loaded)"); fx_status("  status"); return end
    if saved.fxName then
        local okW = pcall(function() pc.ActiveLevelFXName = FName(saved.fxName) end)
        log("  ActiveLevelFXName written back to " .. saved.fxName .. ": " .. tostring(okW))
    end
    if saved.day and saved.night then transition_to(pc, saved.day, saved.night, "") end
    saved = nil
    fx_status("  after")
    ExecuteWithDelay(2000, function() ExecuteInGameThread(function() fx_status("  2 s later"); vignette_status("  2 s later") end) end)
end

------------------------------------------------------------------------------------------------------------------------
-- Vignette buff survey (read-only), NUMPAD 7. Vignette worlds hold a Vignette_Zone (a BuffZone_ParentBP): it applies BuffToApply to
-- characters inside it unless they carry one of BuffBlockingTags, and checks a world flag (PortalSicknessWorldFlag). The player's buffs
-- live in BuffComponent.CurrentBuffs (BuffDebuffEntry: BuffRow, BuffExpireTime) and its tags in BuffComponent.BuffTagContainer.
-- Run it in a real vignette (equipment locked), a home world (H_, not locked) and the Test World to compare.
------------------------------------------------------------------------------------------------------------------------
local function handle_row(h)
    for _, k in ipairs({ "RowName", "Row", "Name" }) do
        local ok, s = pcall(function() return h[k]:ToString() end)
        if ok and type(s) == "string" then return s end
    end
    return "?"
end

local function tag_list(container)
    local out = {}
    pcall(function()
        container.GameplayTags:ForEach(function(_, e)
            local ok, s = pcall(function() return e:get().TagName:ToString() end)
            out[#out + 1] = ok and s or "?"
        end)
    end)
    return #out > 0 and table.concat(out, ", ") or "(none)"
end

local function vignette_buff_survey()
    log("---- VIGNETTE BUFF SURVEY")
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not (pawn and pawn:IsValid()) then log("  no player pawn"); return end
    local loc = pawn:K2_GetActorLocation()
    log(string.format("  player at %.0f, %.0f, %.0f", loc.X, loc.Y, loc.Z))
    vignette_status("  status")
    local bc = nil
    pcall(function() bc = pawn.BuffComponent end)
    if bc and bc:IsValid() then
        local n = 0
        pcall(function()
            bc.CurrentBuffs:ForEach(function(_, e)
                local entry = e:get()
                n = n + 1
                local okT, t = pcall(function() return entry.BuffExpireTime end)
                log(string.format("  buff %d: %s (expires %s)", n, handle_row(entry.BuffRow), okT and tostring(t) or "?"))
            end)
        end)
        if n == 0 then log("  buffs: (none)") end
        log("  buff tags: " .. tag_list(bc.BuffTagContainer))
    else
        log("  no buff component")
    end
    pcall(function() log("  character tags: " .. tag_list(pawn.GameplayTags)) end)
    -- where this spot is relative to the Test World's origin (for a world's exit = { x, y, z, yaw })
    pcall(function()
        local r = pawn:K2_GetActorRotation()
        log(string.format("  relative to the Test World origin: exit = { %.0f, %.0f, %.0f, %.0f }", loc.X - 1100000, loc.Y - 1300000, loc.Z - 90, r.Yaw))
    end)
    -- the story flags set in this world save that belong to Portal Hub worlds (GetWorldFlags fills a list of names)
    local fs = FindFirstOf("WorldFlagSubsystem")
    if fs and fs:IsValid() then
        local out, ours, total = {}, {}, 0
        pcall(function() fs:GetWorldFlags(out) end)
        for i = 1, #out do
            total = total + 1
            local okN, n = pcall(function() return out[i]:ToString() end)
            if okN and n:find("PortalHub_") then ours[#ours + 1] = n end
        end
        log(string.format("  story flags set: %d, Portal Hub ones: %s", total, #ours > 0 and table.concat(ours, ", ") or "(none)"))
    end
    local zones = FindAllOf("Vignette_Zone_C") or {}
    log("  vignette zones in the world: " .. #zones)
    for _, z in ipairs(zones) do
        if z:IsValid() then
            local zl = z:K2_GetActorLocation()
            local ext, inside = "?", "?"
            pcall(function() local e = z.BuffVolume:GetScaledBoxExtent(); ext = string.format("%.0f x %.0f x %.0f", e.X, e.Y, e.Z) end)
            pcall(function() inside = tostring(z.BuffVolume:IsOverlappingActor(pawn)) end)
            log(string.format("  zone %s at %.0f, %.0f, %.0f  extent %s  player inside: %s", z:GetFullName():match("[^ ]+$") or "?", zl.X, zl.Y, zl.Z, ext, inside))
            log("    buff to apply: " .. handle_row(z.BuffToApply) .. "   world flag: " .. handle_row(z.PortalSicknessWorldFlag))
            pcall(function() log("    blocked by tags: " .. tag_list(z.BuffBlockingTags)) end)
        end
    end
    log("---- VIGNETTE BUFF SURVEY done")
end
RegisterKeyBind(Key.NUM_SEVEN, function() ExecuteInGameThread(vignette_buff_survey) end)

-- NUMPAD 3 (testing): clear every Portal Hub completion flag ("PortalHub_<world>_Completed") in this world save, so a vignette world
-- applies portal sickness again. Uses the game's own WorldFlagSubsystem:SetWorldFlag(flag, false, context); says so on screen.
local function clear_hub_flags()
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    local fs = FindFirstOf("WorldFlagSubsystem")
    if not (pc and fs and fs:IsValid()) then log("clear flags: no controller or flag subsystem") return end
    local path = "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags"
    for _, t in ipairs(FindAllOf("BP_Teleporter_HomeWorld_C") or {}) do
        if t:IsValid() then pcall(function() local p = t.RequiredWorldFlag.DataTablePath:ToString(); if p ~= "" then path = p end end) end
    end
    local out, cleared = {}, {}
    pcall(function() fs:GetWorldFlags(out) end)
    for i = 1, #out do
        local okN, n = pcall(function() return out[i]:ToString() end)
        if okN and n:find("^PortalHub_") and n:find("_Completed$") then
            local ok = pcall(function() fs:SetWorldFlag({ RowName = FName(n), DataTablePath = path }, false, pc) end)
            log("clear flags: " .. n .. " -> " .. tostring(ok))
            if ok then cleared[#cleared + 1] = n end
        end
    end
    local msg = #cleared > 0 and ("Cleared " .. table.concat(cleared, ", ")) or "No Portal Hub completion flags to clear"
    if pawn and pawn:IsValid() then pcall(function() pawn:Client_DisplayWarningMessage(FText(msg), 1, false) end) end
    log("clear flags: " .. msg)
end
RegisterKeyBind(Key.NUM_THREE, function() ExecuteInGameThread(clear_hub_flags) end)
log("test key: NUMPAD 3 = clear Portal Hub completion flags in this save (portal sickness comes back on the next entry)")
log("survey key: NUMPAD 7 = vignette zones, the player's buffs and tags (read-only)")

-- The experiment keys (NUMPAD 0 / . / slash / *) are switched off: the Portal Hub now does the same thing itself on arrival and departure, and
-- pressing them as well would fight it. The functions above stay as a record of how each step was found (runs 1-6, 2026-10-14).
local EXPERIMENT_KEYS = false
if EXPERIMENT_KEYS then
    RegisterKeyBind(Key.NUM_ZERO, function() ExecuteInGameThread(add_test_row) end)
    RegisterKeyBind(Key.DECIMAL, function() ExecuteInGameThread(claim_test_level) end)
    RegisterKeyBind(Key.MULTIPLY, function() ExecuteInGameThread(release_test_level) end)
    if not pcall(function() RegisterKeyBind(Key.DIVIDE, function() ExecuteInGameThread(borrow_lighting) end) end) then log("NUMPAD / could not be bound") end
    log("experiment keys: NUMPAD 0 = add Test World level row, NUMPAD . = claim it in the Test World, NUMPAD / = borrow Stone Garden lighting, NUMPAD * = put everything back (memory only)")
end
