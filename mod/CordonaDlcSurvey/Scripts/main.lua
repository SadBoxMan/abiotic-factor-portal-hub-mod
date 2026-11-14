-- Cordona DLC survey (CRD-033, dev only, not shipped, read-only): where the game's two DLC areas are, so the Portal Hub can refuse any spot
-- inside them. The game gates its home worlds by entitlement: Stone Garden (row HomeworldGarden) and Torii (row SupportersEdition). Its
-- level streaming volumes (AbioticLevelStreamingVolume, in the Facility's persistent level) and level managers (LevelManagerInstance) carry
-- that row in RequiredEntitlement. This survey lists every volume and manager with an entitlement, the volume's box (GetActorBounds), and the
-- game's own home pads, then the box around each DLC area. It changes nothing in the game.
--   ' (apostrophe, UE4SS Key.OEM_SEVEN) = survey. Free in the game: no default binding in its input config or Controls list (checked for
--   CRD-023, 10 November); none of our mods uses it. US layout: the key left of Enter.
-- Untried calls, which is why this is its own step: AbioticLevelStreamingVolume:GetActorBounds (out-parameters as tables), reading
-- RequiredEntitlement / RequiredWorldFlag row handles on volumes and managers, FindAllOf("LevelManagerInstance").
-- Output: UE4SS.log ([CordonaDlcSurvey] lines) and ue4ss/Mods/CordonaDlcSurvey/survey.txt (overwritten at each press).

local OUT_PATH = "ue4ss/Mods/CordonaDlcSurvey/survey.txt"      -- relative to UE4SS's working folder (Win64), like the hub's manual_exits.lua
local DLC_ROWS = { HomeworldGarden = "Stone Garden", SupportersEdition = "Torii" }
local HOME_PADS = { "H_Garden_Start", "H_Garden_Entrance", "H_Japan_Start", "H_Japan_Entrance", "H_Cabin_Start", "H_Cabin_Entrance" }

local lines = {}
local function log(msg)
    lines[#lines + 1] = msg
    print("[CordonaDlcSurvey] " .. msg .. "\n")
end

local function valid(o) return o ~= nil and type(o) ~= "number" and type(o) ~= "string" and type(o) ~= "boolean" and o:IsValid() end

local function str(v)
    if v == nil then return "nil" end
    local t = type(v)
    if t == "string" or t == "number" or t == "boolean" then return tostring(v) end
    local ok, s = pcall(function() return v:ToString() end)
    if ok then return tostring(s) end
    return "<" .. t .. ">"
end

local function row_of(obj, prop)            -- a row handle's RowName as text, or nil
    local ok, s = pcall(function() return obj[prop].RowName:ToString() end)
    if ok and s and s ~= "" then return s end
    return nil
end

local function vec(v) return string.format("%.1f, %.1f, %.1f", v.X or 0, v.Y or 0, v.Z or 0) end

local function location(a)
    if not valid(a) then return nil end
    local ok, l = pcall(function() return a:K2_GetActorLocation() end)
    if ok and l then return { X = l.X, Y = l.Y, Z = l.Z } end
    return nil
end

local function bounds(a)                    -- origin, extent (world, axis-aligned) or nil, why
    if not valid(a) then return nil, nil, "not valid" end
    local o, e = {}, {}
    local ok, err = pcall(function() a:GetActorBounds(false, o, e, false) end)
    if not ok then return nil, nil, tostring(err):match("^[^\r\n]*") end
    if type(o.X) ~= "number" or type(e.X) ~= "number" then return nil, nil, "out-parameters were not filled" end
    return { X = o.X, Y = o.Y, Z = o.Z }, { X = e.X, Y = e.Y, Z = e.Z }, nil
end

local function grow(box, o, e)
    local lo = { X = o.X - e.X, Y = o.Y - e.Y, Z = o.Z - e.Z }
    local hi = { X = o.X + e.X, Y = o.Y + e.Y, Z = o.Z + e.Z }
    if not box.lo then box.lo, box.hi = lo, hi return end
    for _, k in ipairs({ "X", "Y", "Z" }) do
        box.lo[k] = math.min(box.lo[k], lo[k]); box.hi[k] = math.max(box.hi[k], hi[k])
    end
end

local function inside(box, p)
    return box.lo and p and p.X >= box.lo.X and p.X <= box.hi.X and p.Y >= box.lo.Y and p.Y <= box.hi.Y and p.Z >= box.lo.Z and p.Z <= box.hi.Z
end

local function survey()
    lines = {}
    log("survey (" .. os.date("%Y-%m-%d %H:%M:%S") .. ")")
    local areas = {}
    local pc = FindFirstOf("Abiotic_PlayerController_C")
    if valid(pc) then
        local ok, pawn = pcall(function() return pc.Pawn end)
        local l = ok and location(pawn) or nil
        if l then log("player at " .. vec(l)) end
    end

    -- 1. the level streaming volumes
    local vols, gated = FindAllOf("AbioticLevelStreamingVolume") or {}, 0
    log("streaming volumes: " .. #vols)
    for _, v in ipairs(vols) do
        if valid(v) then
            local row, flag = row_of(v, "RequiredEntitlement"), row_of(v, "RequiredWorldFlag")
            if (row and row ~= "None") or (flag and flag ~= "None") then
                gated = gated + 1
                local name = "?"
                pcall(function() name = v:GetFName():ToString() end)
                local l = location(v)
                local o, e, why = bounds(v)
                local xyz = ""
                pcall(function() xyz = string.format(" | X/Y/Z %.1f/%.1f/%.1f", v.X, v.Y, v.Z) end)
                log(string.format("volume %s | entitlement %s | world flag %s | at %s | bounds %s%s", name, tostring(row), tostring(flag),
                    l and vec(l) or "?", o and ("origin " .. vec(o) .. " extent " .. vec(e)) or ("unreadable (" .. tostring(why) .. ")"), xyz))
                local area = row and DLC_ROWS[row]
                if area and o then
                    areas[area] = areas[area] or { n = 0 }
                    areas[area].n = areas[area].n + 1
                    grow(areas[area], o, e)
                end
            end
        end
    end
    log("volumes with an entitlement or world flag: " .. gated)

    -- 2. the level managers
    local mgrs = FindAllOf("LevelManagerInstance") or {}
    log("level managers: " .. #mgrs)
    for _, m in ipairs(mgrs) do
        if valid(m) then
            local row, flag = row_of(m, "RequiredEntitlement"), row_of(m, "RequiredWorldFlag")
            if (row and row ~= "None") or (flag and flag ~= "None") then
                local level, nvol = "?", "?"
                pcall(function() local ls = m.LevelStreaming; if valid(ls) then level = ls:GetFullName() end end)
                pcall(function() nvol = tostring(#m.LevelStreamingVolumes) end)
                log(string.format("manager | entitlement %s | world flag %s | level %s | volumes %s", tostring(row), tostring(flag), level, nvol))
            end
        end
    end

    -- 3. the game's home pads
    local pads = {}
    for _, t in ipairs(FindAllOf("BP_Teleporter_HomeWorld_C") or {}) do
        if valid(t) then
            local id = "?"
            pcall(function() id = t.MyTeleporterID:ToString() end)
            pads[id] = t
        end
    end
    for _, id in ipairs(HOME_PADS) do
        local t = pads[id]
        local l = location(t)
        log(string.format("home pad %s | at %s | RequiredDLC %s | RequiredWorldFlag %s", id, l and vec(l) or "not found",
            tostring(t and row_of(t, "RequiredDLC")), tostring(t and row_of(t, "RequiredWorldFlag"))))
    end

    -- 4. the box around each DLC area, and which home pads stand in it
    for _, area in ipairs({ "Stone Garden", "Torii" }) do
        local b = areas[area]
        if b and b.lo then
            local ins = {}
            for _, id in ipairs(HOME_PADS) do if inside(b, location(pads[id])) then ins[#ins + 1] = id end end
            log(string.format("AREA %s | %d volume(s) | min %s | max %s | home pads inside: %s", area, b.n, vec(b.lo), vec(b.hi),
                #ins > 0 and table.concat(ins, ", ") or "none"))
        else
            log("AREA " .. area .. " | no volume with its entitlement and readable bounds")
        end
    end

    local f = io.open(OUT_PATH, "w")
    if f then f:write(table.concat(lines, "\n") .. "\n"); f:close(); log("written to " .. OUT_PATH)
    else log("could not write " .. OUT_PATH .. " (the log above has it all)") end
end

RegisterKeyBind(Key.OEM_SEVEN, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(survey)
        if not ok then log("survey failed: " .. tostring(err)) end
    end)
end)
log("loaded; press ' (apostrophe) in game for the DLC survey")
