-- PortalMaterialLab: the project's read-only survey lab. It never changes the game; it only logs what it finds, so features can be
-- designed from facts. (It started as a material-swap experiment, hence the name; those experiments are finished and were removed, they
-- are in the git history.) Keys, all read-only:
--   NUMPAD 4        sky domes: dome meshes, their materials and parameters, and the sky Blueprint actors
--   NUMPAD 5        hazards: water / pain-causing volumes, hazard-style classes, underwater and damage data tables
--   NUMPAD 6        NPCs: NPC, creature and spawner classes, plus the settings of one spawner and one NPC
--   HOME            the player's lighting state: the controller's FX rows, the real light values, and the DT_LevelFX row names
--   NUMPAD 0        lighting rows: every row of DT_LevelFX with its main values;  NUMPAD * / NUMPAD / step through them in game,
--                   NUMPAD . gives the lighting back (the only keys besides NUMPAD 3 that change anything, and only the lighting)
--   NUMPAD -        Leyak director: required story flag, CanSpawn, cooldown, active Leyak, each Leyak's distance (read-only); F4 forces a spawn
--   F5              no-clip on / off (changes the player: collision off, flying)
--   F2              save the player's position (world and world-relative, for ArriveSpot / ExitSpot) to the log and saved_positions.txt
--   PAGE UP         flags and row registry: flags in this save, hub rows in DT_WorldFlags and DT_Levels, BaseTables, zones, pads (read-only)
--   PAGE DOWN       the same questions asked through native calls not used elsewhere (flag library, HasWorldFlag handle forms; on their own key)
--   (no key)        every pad use is logged by a passive hook on AttemptTeleport: which pad, where it leads, which flag it sets
-- Keys stay clear of the game's own bindings: F1 is its player list, F10 its HUD toggle, + its pager (NUMPAD 1 and 2 belong to PortalHub, F6-F10 to PortalLogger). Note: Shift + a numpad digit does not work,
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

local FX_TABLE = "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX"
-- the lighting row struct's known homes, used only when DT_LevelFX.RowStruct cannot be read: native since game update v1.5.0
-- (27 October 2026), a Blueprint struct before it
local FX_STRUCTS = { "/Script/AbioticFactor.LevelFXData", "/Game/Blueprints/Data/LevelFXData_Struct.LevelFXData_Struct" }

local function valid(o)
    local ok, v = pcall(function() return o ~= nil and o:IsValid() end)
    return ok and v == true
end

-- A data table's row struct: the table's own RowStruct first (survives the struct moving again), then the known paths.
-- Returns the struct and where it came from.
local function row_struct(tablePath, knownPaths)
    local dt = StaticFindObject(tablePath)
    if valid(dt) then
        local ok, s = pcall(function() return dt.RowStruct end)
        if ok and valid(s) then return s, "RowStruct" end
    end
    for _, p in ipairs(knownPaths) do
        local s = StaticFindObject(p)
        if valid(s) then return s, p end
    end
    return nil, "not found"
end

local function struct_text(st, from)
    if not st then return "none (" .. from .. ")" end
    local ok, n = pcall(function() return st:GetFullName() end)
    return ((ok and type(n) == "string") and n or "?") .. " (from " .. from .. ")"
end

local function fx_struct() return row_struct(FX_TABLE, FX_STRUCTS) end

-- A row handle property such as the controller's Day_FX_Row (a LevelFXRowHandle struct since v1.5.0): the row name inside it.
local function handle_name(obj, prop)
    local ok, v = pcall(function() return obj[prop].RowName:ToString() end)
    if ok and type(v) == "string" then return v end
    ok, v = pcall(function() return obj[prop]:ToString() end)
    if ok and type(v) == "string" then return v end
    return nil
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
    local def, from = fx_struct()
    if not def then log("    " .. label .. ": struct definition not found"); return end
    log("    " .. label .. ": (" .. struct_text(def, from) .. ")")
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
pcall(function() RegisterKeyBind(Key.HOME, function() ExecuteInGameThread(fx_player_survey) end) end)
log("keys: NUMPAD 4 = sky domes, NUMPAD 5 = hazards, NUMPAD 6 = NPCs, HOME = player lighting (all read-only)")

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
-- up in DT_Levels (rows of LevelMetadata: Level, IsVignette, EntranceTeleporter, ...; a Blueprint struct with LevelFileName instead of
-- Level before game update v1.5.0). The row it lands on becomes the
-- controller's ActiveLevelName, which PlayerIsInVignette, the respawn menu and the weather read. A custom world has no row, so the game
-- keeps the last one (Facility). This logs every row and what the level manager reports where the player stands.
------------------------------------------------------------------------------------------------------------------------
local LEVELS_TABLE = "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels"
local LEVEL_STRUCTS = { "/Script/AbioticFactor.LevelMetadata", "/Game/Blueprints/Data/LevelMetadata_Struct.LevelMetadata_Struct" }
local function level_struct() return row_struct(LEVELS_TABLE, LEVEL_STRUCTS) end

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
    local def = level_struct()
    local parts = {}
    if not def then return "(struct definition not found)" end
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
    log("  row struct: " .. struct_text(level_struct()))
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
    local def = level_struct()
    if def then
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
    for _, k in ipairs({ "ReleaseGroup", "LevelFXRow_Day", "LevelFXRow_Night", "SectorName",
                         "ResettablePortalWorld", "HasFacilityShakes", "IsVignette", "EntranceTeleporter" }) do
        if not f[k] then log("  field not found in the struct: " .. k .. " (stopping)"); return end
    end
    local fx = StaticFindObject(FX_TABLE_PATH)
    local row = {}
    row[f.ReleaseGroup] = 0
    if f.LevelFileName then row[f.LevelFileName] = FName(TEST_ROW) end   -- before v1.5.0; never write its successor Level (a soft object)
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
        tag, name_of("ActiveLevelFXName"), handle_name(pc, "Day_FX_Row") or "?", handle_name(pc, "Night_FX_Row") or "?", name_of("ActiveWeatherFXName"), tostring(in_vignette(pc)),
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
    saved = { levelName = s("ActiveLevelName"), fxName = s("ActiveLevelFXName"), day = handle_name(pc, "Day_FX_Row"), night = handle_name(pc, "Night_FX_Row") }
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
-- Vignette buff survey (read-only), NUMPAD 7 (also the Leyak safety zones and their sizes). Vignette worlds hold a Vignette_Zone (a BuffZone_ParentBP): it applies BuffToApply to
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

-- one entry of an out-parameter name array: a plain FName, or wrapped (then it needs :get() first)
local function array_name(x)
    local s
    if pcall(function() s = x:ToString() end) and type(s) == "string" then return s end
    if pcall(function() s = x:get():ToString() end) and type(s) == "string" then return s end
    return nil
end

-- the story flags set in this world save: the readable names, and how many entries the game handed back
local function saved_flags()
    local fs = FindFirstOf("WorldFlagSubsystem")
    if not valid(fs) then return nil, 0 end
    local out, names = {}, {}
    pcall(function() fs:GetWorldFlags(out) end)
    for i = 1, #out do
        local n = array_name(out[i])
        if n then names[#names + 1] = n end
    end
    return names, #out
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
    local names, total = saved_flags()
    if names then
        local ours = {}
        for _, n in ipairs(names) do
            if n:find("PortalHub_") then ours[#ours + 1] = n end
        end
        log(string.format("  story flags set: %d (%d readable), Portal Hub ones: %s", total, #names, #ours > 0 and table.concat(ours, ", ") or "(none)"))
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
    -- the Leyak safety zones too (same kind of buff zone; the box component's name is not known, so the likely ones are tried)
    local lzones = FindAllOf("LeyakSafetyZone_C") or {}
    log("  Leyak safety zones in the world: " .. #lzones)
    for _, z in ipairs(lzones) do
        if z:IsValid() and not z:GetFullName():find("Default__") then
            local zl = z:K2_GetActorLocation()
            local ext, inside, via = "?", "?", "?"
            for _, prop in ipairs({ "BuffVolume", "TriggerVolume", "CollisionComponent", "BoxComponent", "Box", "TriggerBox" }) do
                local okC, comp = pcall(function() return z[prop] end)
                if okC and comp and comp:IsValid() and pcall(function() local e = comp:GetScaledBoxExtent(); ext = string.format("%.0f x %.0f x %.0f", e.X, e.Y, e.Z) end) then
                    via = prop
                    pcall(function() inside = tostring(comp:IsOverlappingActor(pawn)) end)
                    break
                end
            end
            log(string.format("  Leyak zone %s at %.0f, %.0f, %.0f  half-size %s (%s)  player inside: %s", z:GetFullName():match("[^ ]+$") or "?",
                zl.X, zl.Y, zl.Z, ext, via, inside))
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
    local okG, ret = pcall(function() return fs:GetWorldFlags(out) end)
    local names = {}
    for i = 1, #out do
        local x = out[i]
        local n
        if not (pcall(function() n = x:ToString() end) and type(n) == "string") then pcall(function() n = x:get():ToString() end) end
        if type(n) == "string" then names[#names + 1] = n end
    end
    log(string.format("clear flags: GetWorldFlags call %s (returned %s), %d entries, %d readable; first: %s", tostring(okG), tostring(ret), #out, #names,
        table.concat(names, ", ", 1, math.min(#names, 8))))
    -- also take every Portal Hub completion flag from the game's flag table itself (the hub adds them there), so clearing does not
    -- depend on what GetWorldFlags hands back
    local dt = StaticFindObject("/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags")
    if dt and dt:IsValid() then
        pcall(function()
            local rows = dt:GetRowNames()
            for i = 1, #rows do
                local r = rows[i]
                local n
                if not (pcall(function() n = r:ToString() end) and type(n) == "string") then n = tostring(r) end
                if n:find("^PortalHub_") and n:find("_Completed$") then
                    local h = { RowName = FName(n), DataTablePath = path }
                    local okH, set = pcall(function() return fs:HasWorldFlag(pc, h) end)
                    log("clear flags: table row " .. n .. " set: " .. tostring(okH and set))
                    if okH and set then names[#names + 1] = n end
                end
            end
        end)
    end
    local done = {}
    for _, n in ipairs(names) do
        if n:find("^PortalHub_") and n:find("_Completed$") and not done[n] then
            done[n] = true
            local h = { RowName = FName(n), DataTablePath = path }
            local ok = pcall(function() fs:SetWorldFlag(h, false, pc) end)
            local okH, still = pcall(function() return fs:HasWorldFlag(pc, h) end)
            log("clear flags: " .. n .. " -> call " .. tostring(ok) .. ", still set afterwards: " .. tostring(okH and still))
            if ok and okH and still == false then cleared[#cleared + 1] = n
            elseif ok then cleared[#cleared + 1] = n .. " (could not confirm)" end
        end
    end
    local msg = #cleared > 0 and ("Cleared " .. table.concat(cleared, ", ")) or "No Portal Hub completion flags to clear"
    if pawn and pawn:IsValid() then pcall(function() pawn:Client_DisplayWarningMessage(FText(msg), 1, false) end) end
    log("clear flags: " .. msg)
end
RegisterKeyBind(Key.NUM_THREE, function() ExecuteInGameThread(clear_hub_flags) end)
log("test key: NUMPAD 3 = clear Portal Hub completion flags in this save (portal sickness comes back on the next entry)")
log("survey key: NUMPAD 7 = vignette zones, the player's buffs and tags (read-only)")

------------------------------------------------------------------------------------------------------------------------
-- Lighting browser, NUMPAD 0 / * / slash / . (17 October 2026). Every row of the game's lighting table (DT_LevelFX) is a possible
-- LightingDay / LightingNight value for a world. NUMPAD 0 lists them all with their main values; NUMPAD * and NUMPAD / step forward and
-- back through them, each applied for day and night through the game's own TransitionToNewEnvironmentFX (row handles only, the call
-- already proven safe; the banner shows the row's name); NUMPAD . hands the lighting back to the rows that were there before.
-- Use it in the Facility or in a world with NoWeather off (World D): inside a no-weather world the Portal Hub puts the world's own
-- lighting back every few seconds.
------------------------------------------------------------------------------------------------------------------------
local browse = { rows = nil, i = 0, before = nil }

local function lighting_rows()
    if browse.rows then return browse.rows end
    local dt = StaticFindObject(FX_TABLE_PATH)
    if not (dt and dt:IsValid()) then log("  DT_LevelFX is not loaded"); return nil end
    local rows = {}
    local ok, names = pcall(function() return dt:GetRowNames() end)
    if ok and type(names) == "table" then
        for _, n in ipairs(names) do
            local s = type(n) == "string" and n or nil
            if not s then pcall(function() s = n:ToString() end) end
            if not s then pcall(function() s = n:get():ToString() end) end
            if type(s) == "string" and s ~= "" then rows[#rows + 1] = s end
        end
    end
    log(string.format("  GetRowNames: %s, %d row(s)", tostring(ok), #rows))
    if #rows == 0 then rows = level_fx_rows() or {} end
    table.sort(rows, function(a, b) return a:lower() < b:lower() end)
    if #rows > 0 then browse.rows = rows end
    return rows
end

-- the plain values of one lighting row (numbers, booleans, names), short field names; `only` limits it to fields matching a pattern
local function fx_row_values(name, only)
    local dt = StaticFindObject(FX_TABLE_PATH)
    if not (dt and dt:IsValid()) then return "?" end
    local okR, row = pcall(function() return dt:FindRow(name) end)
    if not okR or row == nil then return "(row not found)" end
    -- FindRow hands back the row as a struct (userdata), not a Lua table: read it field by field through the row struct's properties.
    -- Read-only: soft-object fields (music, cubemap, particles) are read but never written, and only plain values are shown.
    local fields = {}
    if type(row) == "table" then
        for k, v in pairs(row) do fields[#fields + 1] = { tostring(k), v } end
    else
        local def = fx_struct()
        if not def then return "(lighting row struct not found)" end
        pcall(function()
            def:ForEachProperty(function(p)
                local n = p:GetFName():ToString()
                local okv, v = pcall(function() return row[n] end)
                if okv then fields[#fields + 1] = { n, v } end
            end)
        end)
        if #fields == 0 then return "(row not readable: no fields)" end
    end
    local parts = {}
    for _, kv in ipairs(fields) do
        local k, v = kv[1], kv[2]
        local key = short_field(k)
        local wanted = not only
        if type(only) == "table" then for _, pat in ipairs(only) do if key:find(pat) then wanted = true end end
        elseif only then wanted = key:find(only) ~= nil end
        if wanted then
            local t, txt = type(v), nil
            if t == "number" then txt = string.format("%.3g", v)
            elseif t == "boolean" then txt = tostring(v)
            elseif t == "string" then txt = v
            else pcall(function() local s = v:ToString(); if type(s) == "string" then txt = s end end) end
            if txt then parts[#parts + 1] = key .. "=" .. txt end
        end
    end
    table.sort(parts)
    return table.concat(parts, "  ")
end

-- the fields the row list shows: sun, sky, fog, temperature, dynamic sky (field names of the native LevelFXData since v1.5.0)
local LIST_FIELDS = { "^DirLight_Intensity$", "^SkyLight_Intensity$", "^Fog_Density$", "^Fog_MaxOpacity$", "Temperature", "Dynamic" }

local function list_lighting()
    log("---- LIGHTING ROWS (DT_LevelFX)")
    local rows = lighting_rows()
    if not rows or #rows == 0 then log("  no row names could be read") return end
    for i, r in ipairs(rows) do
        log(string.format("  %3d  %-28s %s", i, r, fx_row_values(r, LIST_FIELDS)))
    end
    log(string.format("  %d rows. NUMPAD * / NUMPAD / = next / previous, NUMPAD . = back to the game's lighting", #rows))
end

local function step_lighting(delta)
    local pc = player_controller()
    if not pc then log("lighting browser: no controller") return end
    local rows = lighting_rows()
    if not rows or #rows == 0 then log("lighting browser: no row names could be read") return end
    if not browse.before then
        local function s(prop) local ok, v = pcall(function() return pc[prop]:ToString() end); return ok and v or nil end
        browse.before = { day = handle_name(pc, "Day_FX_Row"), night = handle_name(pc, "Night_FX_Row") }
    end
    browse.i = ((browse.i - 1 + delta) % #rows) + 1
    local r = rows[browse.i]
    log(string.format("---- LIGHTING %d/%d: %s", browse.i, #rows, r))
    -- the row name on screen: the sector name passed below stopped showing as a banner here in v1.5.0 (seen 6 November 2026)
    pcall(function() pc.Pawn:Client_DisplayWarningMessage(FText(string.format("Lighting %d/%d: %s", browse.i, #rows, r)), 1, false) end)
    if transition_to(pc, r, r, string.format("%s (%d/%d)", r, browse.i, #rows)) then
        log("  " .. fx_row_values(r))
        ExecuteWithDelay(2000, function() ExecuteInGameThread(function() fx_status("  2 s later") end) end)
    end
end

local function restore_browse()
    local pc = player_controller()
    local b = browse.before
    if not (pc and b and b.day and b.night) then log("lighting browser: nothing to put back") return end
    browse.before = nil
    transition_to(pc, b.day, b.night, "")
    log("lighting browser: back to " .. b.day .. " / " .. b.night)
end

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
if not EXPERIMENT_KEYS then
    RegisterKeyBind(Key.NUM_ZERO, function() ExecuteInGameThread(list_lighting) end)
    RegisterKeyBind(Key.MULTIPLY, function() ExecuteInGameThread(function() step_lighting(1) end) end)
    if not pcall(function() RegisterKeyBind(Key.DIVIDE, function() ExecuteInGameThread(function() step_lighting(-1) end) end) end) then log("NUMPAD / could not be bound") end
    RegisterKeyBind(Key.DECIMAL, function() ExecuteInGameThread(restore_browse) end)
    log("lighting keys: NUMPAD 0 = list every lighting row, NUMPAD * / NUMPAD / = next / previous row, NUMPAD . = back to the game's lighting")
end

------------------------------------------------------------------------------------------------------------------------
-- Leyak, NUMPAD - (read-only survey) and F4 (force a spawn) (17 October 2026). The Leyak is spawned by the AI director's
-- LeyakDirectorComponent (Abiotic_AIDirector_C_1 in the Facility map; its parent StalkingNpcDirector_ParentBP). From the object dump: it
-- has a RequiredWorldFlag (a story flag that must be set before she can appear), a StalkingTag, LeyakCooldown / TimeLastLeyakSpawn,
-- CanSpawn(), ActiveStalkingNPC, CurrentStalkingNpcTarget, DirectorDebugOn (the game's own on-screen debug messages) and
-- Server_ForceSpawn() (no parameters). F4 is the only key here that changes anything: it switches the director's debug messages
-- on and calls Server_ForceSpawn (untried: kept on its own key). Compare World B (Leyak safety zone) with World D (none).
------------------------------------------------------------------------------------------------------------------------
local function leyak_director()
    for _, d in ipairs(FindAllOf("LeyakDirectorComponent_C") or {}) do
        if d:IsValid() and not d:GetFullName():find("Default__") and not d:GetFullName():find("_GEN_VARIABLE") then return d end
    end
    return nil
end

local function leyak_survey(tag)
    log("---- LEYAK " .. (tag or "SURVEY"))
    local d = leyak_director()
    if not d then log("  no LeyakDirectorComponent in this world") return nil end
    log("  director: " .. d:GetFullName())
    local function get(prop) local ok, v = pcall(function() return d[prop] end); return ok and v or nil end
    local function name_of(v, field) local ok, s = pcall(function() return v[field]:ToString() end); return ok and s or "?" end
    local flag = get("RequiredWorldFlag")
    local flagRow = flag and name_of(flag, "RowName") or "?"
    local flagSet = "?"
    local pc = player_controller()
    local names = saved_flags()          -- the save's own list: flag handles have no DataTablePath since v1.5.0
    if names and #names > 0 then
        flagSet = "false"
        for _, n in ipairs(names) do
            if n == flagRow then flagSet = "true" end
        end
    end
    log(string.format("  required story flag: %s (set in this save: %s)", flagRow, flagSet))
    local st = get("StalkingTag")
    log("  stalking tag: " .. (st and name_of(st, "TagName") or "?"))
    local okC, can = pcall(function() return d:CanSpawn() end)
    log("  CanSpawn(): " .. (okC and tostring(can) or "call failed"))
    for _, p in ipairs({ "LeyakCooldown", "TimeLastLeyakSpawn", "LeyakViewCounter", "SuperTauntActive", "DirectorDebugOn", "ActiveLeyakContainmentID" }) do
        local v = get(p)
        local txt = type(v) == "number" and string.format("%.1f", v) or tostring(v)
        if type(v) ~= "number" and type(v) ~= "boolean" and v ~= nil then pcall(function() txt = v:ToString() end) end
        log(string.format("  %-24s %s", p, txt))
    end
    for _, p in ipairs({ "ActiveStalkingNPC", "CurrentStalkingNpcTarget" }) do
        local v = get(p)
        local okV, valid = pcall(function() return v and v:IsValid() end)
        log(string.format("  %-24s %s", p, (okV and valid) and v:GetFullName() or "none"))
    end
    local pawn = pc and pc.Pawn
    local me = nil
    if pawn and pawn:IsValid() then
        local okL, l = pcall(function() return pawn:K2_GetActorLocation() end)
        if okL then me = l; log(string.format("  player at %.0f, %.0f, %.0f", l.X, l.Y, l.Z)) end
    end
    -- every Leyak in the world and how far she is from the player (100 units = 1 m)
    local n = 0
    for _, a in ipairs(FindAllOf("NPC_Leyak_C") or {}) do
        if a:IsValid() and not a:GetFullName():find("Default__") then
            n = n + 1
            local okA, l = pcall(function() return a:K2_GetActorLocation() end)
            if okA and me then
                local dx, dy, dz = l.X - me.X, l.Y - me.Y, l.Z - me.Z
                local dist, flat = math.sqrt(dx * dx + dy * dy + dz * dz), math.sqrt(dx * dx + dy * dy)
                log(string.format("  Leyak %d at %.0f, %.0f, %.0f: %.1f m away (%.1f m sideways, %.1f m %s)", n, l.X, l.Y, l.Z,
                    dist / 100, flat / 100, math.abs(dz) / 100, dz >= 0 and "above" or "below"))
            else
                log(string.format("  Leyak %d: %s (location unknown)", n, a:GetFullName()))
            end
        end
    end
    if n == 0 then log("  no Leyak in the world right now") end
    -- her spawn is an EQS query over the nav mesh: list what nav data is loaded, so the zone and the nav mesh can be told apart
    for _, class in ipairs({ "RecastNavMesh", "NavMeshBoundsVolume" }) do
        local list = FindAllOf(class) or {}
        log(string.format("  %s objects: %d", class, #list))
        for i, a in ipairs(list) do
            if i > 12 then log("    ...") break end
            if valid(a) then log("    " .. a:GetFullName() .. " at " .. loc_text(a)) end
        end
    end
    return d
end

local function leyak_force()
    local d = leyak_survey("FORCE SPAWN (before)")
    if not d then return end
    pcall(function() d.DirectorDebugOn = true end)
    local ok, err = pcall(function() d:Server_ForceSpawn() end)
    log("  DirectorDebugOn set; Server_ForceSpawn(): " .. tostring(ok) .. (ok and "" or (" (" .. one_line(err) .. ")")))
    ExecuteWithDelay(3000, function() ExecuteInGameThread(function() leyak_survey("3 s after the force spawn") end) end)
end

RegisterKeyBind(Key.SUBTRACT, function() ExecuteInGameThread(function() leyak_survey() end) end)
if not pcall(function() RegisterKeyBind(Key.F4, function() ExecuteInGameThread(leyak_force) end) end) then log("F4 could not be bound") end
log("Leyak keys: NUMPAD - = Leyak director survey (read-only), F4 = force a Leyak spawn (and the game's director debug messages)")

------------------------------------------------------------------------------------------------------------------------
-- No-clip, F5 (18 October 2026), so the cheat-command mod is not needed for testing. Written from the engine's own character
-- functions: the player's collision off (SetActorEnableCollision), movement mode Flying (CharacterMovement:SetMovementMode 5) with the
-- engine's cheat-flying switch (bCheatFlying) and a faster fly speed. Pressing it again puts everything back and drops the player
-- (Falling, mode 3), and logs where they are. A new pawn (after dying) starts with collision on, so the next press switches no-clip on
-- for it. Changes only the local player.
------------------------------------------------------------------------------------------------------------------------
local noclip = nil      -- { key = pawn name, fly = previous MaxFlySpeed } while on

-- one line at the top of the screen (the game's own player message: text, colour 0 green / 1 gray / 2 yellow / 3 red / 4 purple, beep)
local function say(msg, colour)
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if pawn and pawn:IsValid() then pcall(function() pawn:Client_DisplayWarningMessage(FText(msg), colour or 0, false) end) end
end

local function toggle_noclip()
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not (pawn and pawn:IsValid()) then log("no-clip: no player pawn") return end
    local mv = pawn.CharacterMovement
    if not (mv and mv:IsValid()) then log("no-clip: the player has no movement component") return end
    local key = pawn:GetFName():ToString()
    local okL, l = pcall(function() return pawn:K2_GetActorLocation() end)
    local where = okL and string.format("%.0f, %.0f, %.0f", l.X, l.Y, l.Z) or "?"
    if not noclip or noclip.key ~= key then
        local okF, fly = pcall(function() return mv.MaxFlySpeed end)
        noclip = { key = key, fly = okF and fly or nil }
        local okC = pcall(function() pawn:SetActorEnableCollision(false) end)
        pcall(function() mv.bCheatFlying = true end)
        local okM = pcall(function() mv:SetMovementMode(5, 0) end)                -- MOVE_Flying
        pcall(function() mv.MaxFlySpeed = 2000.0 end)
        log(string.format("no-clip ON at %s (collision off: %s, flying: %s, fly speed was %s)", where, tostring(okC), tostring(okM), tostring(noclip.fly)))
        say("No-clip ON", 2)
    else
        pcall(function() pawn:SetActorEnableCollision(true) end)
        pcall(function() mv.bCheatFlying = false end)
        if noclip.fly then pcall(function() mv.MaxFlySpeed = noclip.fly end) end
        pcall(function() mv:SetMovementMode(3, 0) end)                            -- MOVE_Falling: lands and walks again
        noclip = nil
        log("no-clip OFF at " .. where)
        say("No-clip OFF", 1)
    end
end


------------------------------------------------------------------------------------------------------------------------
-- Save position, F2 (18 October 2026): where the player's feet are and which way they face, for typing into a world's loader Blueprint
-- (ArriveSpot / ArriveYaw, ExitSpot / ExitYaw) or config.lua. The spot is given in world coordinates and, when it lies inside one of the
-- hub's custom worlds (read from the hub's config.lua), also relative to that world's origin, which is what the Blueprint wants. Each
-- spot is logged, shown on screen and appended to Mods\PortalMaterialLab\saved_positions.txt.
------------------------------------------------------------------------------------------------------------------------
local HUB_CONFIG = "ue4ss/Mods/PortalHub/Scripts/config.lua"            -- relative to the game's Win64 folder (UE4SS's working folder)
local POSITIONS_FILE = "ue4ss/Mods/PortalMaterialLab/saved_positions.txt"
local savedCount = 0

local function hub_worlds()
    local ok, cfg = pcall(dofile, HUB_CONFIG)
    if ok and type(cfg) == "table" and type(cfg.worlds) == "table" then return cfg.worlds end
    return {}
end

local function save_position()
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not (pawn and pawn:IsValid()) then log("save position: no player pawn") return end
    local okL, l = pcall(function() return pawn:K2_GetActorLocation() end)
    if not okL then log("save position: location not readable") return end
    local half = 0
    pcall(function() half = pawn.CapsuleComponent:GetScaledCapsuleHalfHeight() end)
    local yaw = 0
    pcall(function() yaw = pc:GetControlRotation().Yaw end)
    yaw = math.floor(((yaw % 360) + 360) % 360 + 0.5)
    local x, y, z = math.floor(l.X + 0.5), math.floor(l.Y + 0.5), math.floor(l.Z - half + 0.5)      -- z = the feet (the floor)
    savedCount = savedCount + 1
    local line = string.format("%d  world %d, %d, %d  yaw %d", savedCount, x, y, z, yaw)
    local short = string.format("%d, %d, %d facing %d", x, y, z, yaw)
    for id, w in pairs(hub_worlds()) do
        local o = type(w) == "table" and w.origin
        local r = type(w) == "table" and tonumber(w.radius) or 100000
        if type(o) == "table" and tonumber(o[1]) and tonumber(o[2]) then
            local dx, dy, dz = x - o[1], y - o[2], z - (tonumber(o[3]) or 0)
            if dx * dx + dy * dy < r * r then
                line = line .. string.format("  |  in %s: %d, %d, %d  yaw %d  (ArriveSpot / ExitSpot = %d, %d, %d; Yaw = %d)", id, dx, dy, dz, yaw, dx, dy, dz, yaw)
                short = string.format("%s: %d, %d, %d facing %d", id, dx, dy, dz, yaw)
                break
            end
        end
    end
    log("position " .. line)
    local f = io.open(POSITIONS_FILE, "a")
    if f then f:write(os.date("%Y-%m-%d %H:%M:%S") .. "  " .. line .. "\n"); f:close() else log("save position: could not write " .. POSITIONS_FILE) end
    say(string.format("Position %d saved: %s", savedCount, short), 0)
end

-- F3: kill the player, for testing the respawn menu. The character only reacts to point and radial damage (it has no any-damage event) and
-- takes nothing from the engine's plain DamageType (6 November 2026: the hit went through, no damage), so this is a point hit of the game's
-- own DeathPit damage type, with no instigator to keep friendly-fire rules out of it. If the player is still alive a second later, the
-- character's IsDead is set and its OnRep_IsDead runs (Server_PerformDeathSequence alone did nothing on 6 November). The log shows the health.
local KILL_DAMAGE = 1000000.0
local KILL_TYPE = "/Game/Blueprints/DamageTypes/DamageType_DeathPit.DamageType_DeathPit_C"
local function is_dead(pawn)
    local ok, v = pcall(function() return pawn.IsDead end)
    return ok and v == true
end

local function total_health(pawn)
    local ok, v = pcall(function() return pawn:GetTotalHealth() end)
    return ok and tostring(v) or "?"
end

local function kill_type()
    local cls = StaticFindObject(KILL_TYPE)
    if valid(cls) then return cls end
    pcall(function() LoadAsset("/Game/Blueprints/DamageTypes/DamageType_DeathPit.DamageType_DeathPit") end)
    cls = StaticFindObject(KILL_TYPE)
    return valid(cls) and cls or nil
end

local function kill_player()
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    if not valid(pawn) then log("kill: no player pawn (already dead?)") return end
    if is_dead(pawn) then log("kill: already dead") return end
    local lib, cls = StaticFindObject("/Script/Engine.Default__GameplayStatics"), kill_type()
    log("kill: health " .. total_health(pawn) .. ", damage type " .. (cls and "DeathPit" or "not found"))
    local steps = {
        { "point damage, no instigator", function() lib:ApplyPointDamage(pawn, KILL_DAMAGE, { X = 0, Y = 0, Z = 1 }, {}, nil, pawn, cls) end },
        { "IsDead and OnRep_IsDead", function() pawn.IsDead = true; pawn:OnRep_IsDead() end },
    }
    if not (valid(lib) and cls) then table.remove(steps, 1) end
    local function step(i)
        if i > 1 and (not valid(pawn) or is_dead(pawn)) then log("kill: dead") return end
        if i > #steps then log("kill: still alive after every step, health " .. total_health(pawn)) return end
        local ok, err = pcall(steps[i][2])
        log(string.format("kill: %s: %s, health %s%s", steps[i][1], tostring(ok), total_health(pawn), ok and "" or (" (" .. one_line(err) .. ")")))
        ExecuteWithDelay(1000, function() ExecuteInGameThread(function() step(i + 1) end) end)
    end
    step(1)
end

------------------------------------------------------------------------------------------------------------------------
-- CRD-006, the assessment after game update v1.5.0 (6 November 2026). Nothing here changes the game or the save.
-- Since v1.5.0 a flag handle is the native RowHandle: something at offset 0 that is not a property, then RowName. There is no
-- DataTablePath any more, and the hub and lab still pass one (see findings/game-update-2026-10.md).
--   PAGE UP    only reads of the kinds already used in this file: flags in this save, hub rows in the two tables the hub adds to,
--              ABFRowRegistrySubsystem.BaseTables (which tables the row registry manages), zones and pads with their flags.
--   PAGE DOWN  native calls not used before, on their own key: the flag library, the forms of a handle, and the registry's load order.
--              Each is logged before it runs, so a crash shows which one it was.
--   Pad use    a passive hook on AttemptTeleport logs which pad was used and whether its flag was set just after.
------------------------------------------------------------------------------------------------------------------------
local WORLD_FLAGS_PATH = "/Game/Blueprints/DataTables/DT_WorldFlags.DT_WorldFlags"
local BUFFS_PATH = "/Game/Blueprints/DataTables/BuffsDebuffs/DT_BuffsDebuffs.DT_BuffsDebuffs"
local FLAG_LIBRARY = "/Script/AbioticFactor.Default__WorldFlagHandleFunctionLibrary"
local TELEPORT_FN = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C:AttemptTeleport"
local HOMEWORLD_PAD = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C"
local GAME_FLAG = "TrainCompletedOnce"          -- a flag of the game's own, to compare with

local function row_names(dt)
    local names = {}
    pcall(function()
        local r = dt:GetRowNames()
        for i = 1, #r do names[#names + 1] = text_of(r[i]) end
    end)
    return names
end

local function has_row(dt, name)
    local ok, row = pcall(function() return dt:FindRow(name) end)
    return ok and row ~= nil
end

local function contains(list, value)
    for _, v in ipairs(list or {}) do
        if v == value then return true end
    end
    return false
end

-- rows of a table whose name matches, and the row count
local function table_report(label, path, pattern)
    local dt = StaticFindObject(path)
    if not valid(dt) then log("  " .. label .. ": not loaded") return nil end
    local names, ours = row_names(dt), {}
    for _, n in ipairs(names) do
        if n:find(pattern) then ours[#ours + 1] = n end
    end
    log(string.format("  %s: %d rows, matching %s: %s", label, #names, pattern, #ours > 0 and table.concat(ours, ", ") or "(none)"))
    return dt
end

-- the flag rows the hub uses, from the table, the zones and the save, so a row missing from the table still shows up
local function hub_flag_names()
    local names, seen = {}, {}
    local function add(n) if n and n:find("^PortalHub_") and not seen[n] then seen[n] = true; names[#names + 1] = n end end
    local dt = StaticFindObject(WORLD_FLAGS_PATH)
    if valid(dt) then
        for _, n in ipairs(row_names(dt)) do add(n) end
    end
    for _, z in ipairs(FindAllOf("Vignette_Zone_C") or {}) do
        if valid(z) then add(handle_row(z.PortalSicknessWorldFlag)) end
    end
    for _, n in ipairs(saved_flags() or {}) do add(n) end
    return names
end

local function flag_registry_survey()
    log("---- FLAG AND REGISTRY SURVEY")
    local fs = FindFirstOf("WorldFlagSubsystem")
    local loaded = "?"
    if valid(fs) then pcall(function() loaded = tostring(fs:HasWorldFlagsLoaded()) end) end
    local flags, total = saved_flags()
    log(string.format("  flags loaded: %s; set in this save: %d (%d readable)", loaded, total or 0, flags and #flags or 0))
    log(string.format("  %s set in this save: %s", GAME_FLAG, tostring(contains(flags, GAME_FLAG))))
    local flagTable = table_report("DT_WorldFlags", WORLD_FLAGS_PATH, "^PortalHub_")
    table_report("DT_Levels", LEVELS_TABLE, "^PortalHub_")
    for _, n in ipairs(hub_flag_names()) do
        log(string.format("  %s: row in DT_WorldFlags %s, set in this save %s", n, tostring(valid(flagTable) and has_row(flagTable, n)), tostring(contains(flags, n))))
    end
    local buffs = StaticFindObject(BUFFS_PATH)
    if valid(buffs) then
        log("  Debuff_PortalSickness row in DT_BuffsDebuffs: " .. tostring(has_row(buffs, "Debuff_PortalSickness")))
        table_report("DT_BuffsDebuffs", BUFFS_PATH, "[Ss]ick")
    else
        log("  DT_BuffsDebuffs: not loaded")
    end
    local reg = FindFirstOf("ABFRowRegistrySubsystem")
    if valid(reg) then
        local n, tables = 0, {}
        local ok = pcall(function()
            reg.BaseTables:ForEach(function(_, e)
                local dt = e:get()
                n = n + 1
                if valid(dt) then tables[#tables + 1] = dt:GetFName():ToString() end
            end)
        end)
        table.sort(tables)
        log(string.format("  row registry BaseTables: readable %s, %d table(s): %s", tostring(ok), n, table.concat(tables, ", ")))
        log(string.format("  DT_WorldFlags in BaseTables: %s, DT_LevelFX: %s, DT_Levels: %s", tostring(contains(tables, "DT_WorldFlags")),
            tostring(contains(tables, "DT_LevelFX")), tostring(contains(tables, "DT_Levels"))))
        local mods = 0
        pcall(function() reg.RootedModObjects:ForEach(function() mods = mods + 1 end) end)
        log("  row registry RootedModObjects: " .. mods)
    else
        log("  ABFRowRegistrySubsystem not found")
    end
    local pc = player_controller()
    local pawn = pc and pc.Pawn
    for _, z in ipairs(FindAllOf("Vignette_Zone_C") or {}) do
        if valid(z) and not z:GetFullName():find("Default__") then
            local row, inside = handle_row(z.PortalSicknessWorldFlag), "?"
            if valid(pawn) then pcall(function() inside = tostring(z.BuffVolume:IsOverlappingActor(pawn)) end) end
            log(string.format("  zone at %s: flag %s, set in this save %s, player inside %s", loc_text(z), row, tostring(contains(flags, row)), inside))
        end
    end
    for _, t in ipairs(FindAllOf("BP_Teleporter_HomeWorld_C") or {}) do
        if valid(t) then
            log("  a game pad's RequiredWorldFlag: row " .. handle_row(t.RequiredWorldFlag))
            local okP, path = pcall(function() return t.RequiredWorldFlag.DataTablePath:ToString() end)
            log("    its DataTablePath: " .. (okP and tostring(path) or ("not readable (" .. one_line(path) .. ")")))
            break
        end
    end
    local shown = 0
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if valid(t) then
            local row, dest = "?", "?"
            pcall(function() row = handle_row(t.WorldFlagToTriggerOnUse) end)
            pcall(function() dest = t.DestinationTeleporterID:ToString() end)
            if row ~= "None" and row ~= "?" then
                shown = shown + 1
                log(string.format("  pad %s -> %s at %s sets %s (in this save %s)", tostring(pad_id(t)), dest, loc_text(t), row, tostring(contains(flags, row))))
            end
        end
    end
    log(string.format("  pads that set a flag: %d", shown))
    log("---- FLAG AND REGISTRY SURVEY done")
end

-- Runs one native call, logging it first (the log line survives a crash) and its result after.
local function probe(label, fn)
    log("  calling: " .. label)
    local ok, v = pcall(fn)
    if ok then log("    -> " .. value_text(v)) else log("    -> failed: " .. one_line(v)) end
    return ok, v
end

local function flag_native_probe()
    log("---- FLAG NATIVE PROBE (calls not used before)")
    local pc = player_controller()
    local fs = FindFirstOf("WorldFlagSubsystem")
    local lib = StaticFindObject(FLAG_LIBRARY)
    if not (pc and valid(fs) and valid(lib)) then log("  no controller, flag subsystem or flag library") return end
    probe("DoesWorldFlagRowExist " .. GAME_FLAG, function() return lib:DoesWorldFlagRowExist(FName(GAME_FLAG)) end)
    local names = hub_flag_names()
    for _, n in ipairs(names) do
        probe("DoesWorldFlagRowExist " .. n, function() return lib:DoesWorldFlagRowExist(FName(n)) end)
    end
    local all = {}
    local okA = probe("GetAllWorldFlagRowNames", function() return lib:GetAllWorldFlagRowNames(all) end)
    if okA then
        local ours = {}
        for i = 1, #all do
            local n = array_name(all[i])
            if n and n:find("^PortalHub_") then ours[#ours + 1] = n end
        end
        log(string.format("    %d names, Portal Hub ones: %s", #all, #ours > 0 and table.concat(ours, ", ") or "(none)"))
    end
    local n = names[1]
    if n then
        local okH, h = probe("Conv_NameToWorldFlag " .. n, function() return lib:Conv_NameToWorldFlag(FName(n)) end)
        if okH and h ~= nil then
            log("    handle row: " .. handle_row(h))
            probe("HasWorldFlag with the game's own handle", function() return fs:HasWorldFlag(pc, h) end)
        end
        -- the form the hub passes every 2 s, then (only if that one is refused) the same without the field that no longer exists
        local okT = probe("HasWorldFlag with the hub's table", function()
            return fs:HasWorldFlag(pc, { RowName = FName(n), DataTablePath = WORLD_FLAGS_PATH })
        end)
        if not okT then probe("HasWorldFlag with RowName only", function() return fs:HasWorldFlag(pc, { RowName = FName(n) }) end) end
    else
        log("  no Portal Hub flag known yet: walk near the portal room first")
    end
    local reg = FindFirstOf("ABFRowRegistrySubsystem")
    if valid(reg) then
        probe("IsSessionLoadOrderActive", function() return reg:IsSessionLoadOrderActive() end)
        probe("K2_GetResolvedLoadOrder (count)", function() return #reg:K2_GetResolvedLoadOrder() end)
    end
    log("---- FLAG NATIVE PROBE done")
end

-- Which pad was used, and what the save says just after. Only reads; the game's own teleport runs as usual.
local padUse = { hooked = false, at = {} }
local function pad_used(pad)
    if not valid(pad) then return end
    local id = tostring(pad_id(pad))
    local now = os.clock()
    if padUse.at[id] and now - padUse.at[id] < 1 then return end    -- the overlap can fire more than once per crossing
    padUse.at[id] = now
    local dest, row, active = "?", "?", "?"
    pcall(function() dest = pad.DestinationTeleporterID:ToString() end)
    pcall(function() row = handle_row(pad.WorldFlagToTriggerOnUse) end)
    pcall(function() active = tostring(pad.IsTeleporterActive) end)
    log(string.format("pad use: %s -> %s, active %s, sets flag %s", id, dest, active, row))
    if row == "None" or row == "?" then return end
    ExecuteWithDelay(1500, function() ExecuteInGameThread(function()
        log(string.format("pad use: 1.5 s after %s, flag %s set in this save: %s", id, row, tostring(contains(saved_flags(), row))))
    end) end)
end

local function hook_pads()
    if padUse.hooked then return end
    local ok, err = pcall(function() RegisterHook(TELEPORT_FN, function(self) pad_used(self:get()) end) end)
    padUse.hooked = ok
    log(ok and "pad use: logging every pad use" or ("pad use: hook failed: " .. one_line(err)))
end

local function hook_pads_soon() ExecuteWithDelay(5000, function() ExecuteInGameThread(hook_pads) end) end
NotifyOnNewObject(HOMEWORLD_PAD, hook_pads_soon)
if valid(FindFirstOf("BP_Teleporter_HomeWorld_C")) then hook_pads_soon() end

if not pcall(function() RegisterKeyBind(Key.PAGE_UP, function() ExecuteInGameThread(flag_registry_survey) end) end) then log("PAGE UP could not be bound") end
if not pcall(function() RegisterKeyBind(Key.PAGE_DOWN, function() ExecuteInGameThread(flag_native_probe) end) end) then log("PAGE DOWN could not be bound") end
log("assessment keys: PAGE UP = flags and row registry (read-only), PAGE DOWN = flag calls not used before (read-only, its own key)")

if not pcall(function() RegisterKeyBind(Key.F5, function() ExecuteInGameThread(toggle_noclip) end) end) then log("F5 could not be bound") end
if not pcall(function() RegisterKeyBind(Key.F2, function() ExecuteInGameThread(save_position) end) end) then log("F2 could not be bound") end
if not pcall(function() RegisterKeyBind(Key.F3, function() ExecuteInGameThread(kill_player) end) end) then log("F3 could not be bound") end
log("player keys: F5 = no-clip on / off, F2 = save this position (log, screen, saved_positions.txt), F3 = kill the player")
