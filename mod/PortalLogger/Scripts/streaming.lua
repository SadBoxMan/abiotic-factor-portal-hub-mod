-- PortalLogger part 2
-- F7: dump streaming levels (name, loaded/visible state, transform) + player location.
-- F8: dump every actor within ROOM_RADIUS of the Homeworld Room portal cluster, nearest first,
--     to find the "container" objects the portals sit in. Output: PortalStreaming.txt / PortalRoom.txt

local ROOM_CENTER = { X = -12950.0, Y = 8380.0, Z = 0.0 }
local ROOM_RADIUS = 3000.0

local function safe(fn)
    local ok, v = pcall(fn)
    if ok then return v end
    return "<err>"
end

local function str(v)
    if v == nil then return "nil" end
    if type(v) == "userdata" then
        local ok, s = pcall(function() return v:ToString() end)
        if ok then return s end
        return "<userdata>"
    end
    return tostring(v)
end

local function vec(v)
    if type(v) ~= "table" and type(v) ~= "userdata" then return str(v) end
    local ok, s = pcall(string.format, "%.1f, %.1f, %.1f", v.X, v.Y, v.Z)
    return ok and s or "<err>"
end

local function open(path)
    local f = io.open(path, "w")
    if not f then print("[PortalLogger] cannot open " .. path .. "\n") end
    return f
end

local function out(f, line)
    print("[PortalLogger] " .. line .. "\n")
    f:write(line .. "\n")
end

local function player_loc()
    local pc = FindFirstOf("PlayerController")
    if not pc or not pc:IsValid() then return nil end
    local pawn = safe(function() return pc:K2_GetPawn() end)
    if type(pawn) ~= "userdata" or not pawn:IsValid() then return nil end
    return safe(function() return pawn:K2_GetActorLocation() end)
end

local function dump_streaming()
    local f = open("PortalStreaming.txt")
    if not f then return end
    local pl = player_loc()
    out(f, "Player location: " .. (pl and vec(pl) or "unknown"))
    local levels = FindAllOf("LevelStreaming") or {}
    out(f, "LevelStreaming objects: " .. #levels)
    for _, ls in ipairs(levels) do
        if ls:IsValid() then
            out(f, "----")
            out(f, "Class: " .. str(safe(function() return ls:GetClass():GetFName() end)))
            out(f, "Name: " .. str(safe(function() return ls:GetFName() end)))
            out(f, "WorldAsset: " .. str(safe(function() return ls.WorldAsset:GetFullName() end)))
            out(f, "PackageName: " .. str(safe(function() return ls.PackageNameToLoad end)))
            out(f, "ShouldBeLoaded: " .. str(safe(function() return ls.bShouldBeLoaded end)))
            out(f, "ShouldBeVisible: " .. str(safe(function() return ls.bShouldBeVisible end)))
            out(f, "IsLoaded: " .. str(safe(function() return ls:IsLevelLoaded() end)))
            out(f, "IsVisible: " .. str(safe(function() return ls:IsLevelVisible() end)))
            local tr = safe(function() return ls.LevelTransform.Translation end)
            out(f, "LevelOffset: " .. vec(tr))
        end
    end
    local mgrs = FindAllOf("LevelManagerSubsystem") or {}
    out(f, "LevelManagerSubsystem instances: " .. #mgrs)
    f:close()
    print("[PortalLogger] streaming dump done\n")
end

local function dump_room()
    local f = open("PortalRoom.txt")
    if not f then return end
    local pl = player_loc()
    out(f, "Player location: " .. (pl and vec(pl) or "unknown"))
    out(f, string.format("Center %.0f, %.0f, %.0f  radius %.0f", ROOM_CENTER.X, ROOM_CENTER.Y, ROOM_CENTER.Z, ROOM_RADIUS))
    local rows = {}
    for _, a in ipairs(FindAllOf("Actor") or {}) do
        if a:IsValid() then
            local loc = safe(function() return a:K2_GetActorLocation() end)
            if type(loc) == "table" or type(loc) == "userdata" then
                local dx, dy, dz = loc.X - ROOM_CENTER.X, loc.Y - ROOM_CENTER.Y, loc.Z - ROOM_CENTER.Z
                local dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                if dist <= ROOM_RADIUS then
                    rows[#rows + 1] = {
                        dist = dist,
                        class = str(safe(function() return a:GetClass():GetFName() end)),
                        name = str(safe(function() return a:GetFName() end)),
                        loc = vec(loc),
                        yaw = str(safe(function() return string.format("%.1f", a:K2_GetActorRotation().Yaw) end)),
                    }
                end
            end
        end
    end
    table.sort(rows, function(x, y) return x.dist < y.dist end)
    out(f, "Actors in radius: " .. #rows)
    for _, r in ipairs(rows) do
        out(f, string.format("%7.0f | %s | %s | %s | yaw %s", r.dist, r.class, r.name, r.loc, r.yaw))
    end
    f:close()
    print("[PortalLogger] room dump done\n")
end

RegisterKeyBind(Key.F7, function() ExecuteInGameThread(dump_streaming) end)
RegisterKeyBind(Key.F8, function() ExecuteInGameThread(dump_room) end)
print("[PortalLogger] F7 = streaming levels, F8 = portal room actors\n")

-- F9: actors within 900 units of each Homeworld entrance pad, with the static mesh asset name.
-- Used to identify the portal "container" objects. Output: PortalContainers.txt
local function dump_containers()
    local f = open("PortalContainers.txt")
    if not f then return end
    local pads = {}
    for _, t in ipairs(FindAllOf("BP_Teleporter_HomeWorld_C") or {}) do
        if t:IsValid() then
            local id = str(safe(function() return t.MyTeleporterID end))
            if id:match("_Entrance$") then
                pads[#pads + 1] = { id = id, loc = t:K2_GetActorLocation() }
            end
        end
    end
    local actors = FindAllOf("Actor") or {}
    for _, pad in ipairs(pads) do
        out(f, "==== " .. pad.id .. " @ " .. vec(pad.loc))
        local rows = {}
        for _, a in ipairs(actors) do
            if a:IsValid() then
                local loc = safe(function() return a:K2_GetActorLocation() end)
                if type(loc) == "table" or type(loc) == "userdata" then
                    local dx, dy, dz = loc.X - pad.loc.X, loc.Y - pad.loc.Y, loc.Z - pad.loc.Z
                    local dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                    if dist <= 900 then
                        local mesh = safe(function() return a.StaticMeshComponent.StaticMesh:GetFName() end)
                        rows[#rows + 1] = { dist = dist,
                            class = str(safe(function() return a:GetClass():GetFName() end)),
                            name = str(safe(function() return a:GetFName() end)),
                            mesh = (mesh == "<err>") and "" or str(mesh),
                            loc = vec(loc),
                            yaw = str(safe(function() return string.format("%.1f", a:K2_GetActorRotation().Yaw) end)) }
                    end
                end
            end
        end
        table.sort(rows, function(x, y) return x.dist < y.dist end)
        for _, r in ipairs(rows) do
            out(f, string.format("%5.0f | %s | %s | %s | %s | yaw %s", r.dist, r.class, r.name, r.mesh, r.loc, r.yaw))
        end
    end
    f:close()
    print("[PortalLogger] containers dump done\n")
end
RegisterKeyBind(Key.F9, function() ExecuteInGameThread(dump_containers) end)

-- F10: every Lodestone portal container (any tier) within 3000 units of the room centre.
-- Output: PortalLodestones.txt
local function dump_lodestones()
    local f = open("PortalLodestones.txt")
    if not f then return end
    local n = 0
    for _, a in ipairs(FindAllOf("StaticMeshActor") or {}) do
        if a:IsValid() then
            local mesh = nil
            local comp = safe(function() return a.StaticMeshComponent end)
            if type(comp) == "userdata" and comp:IsValid() then
                local sm = safe(function() return comp.StaticMesh end)
                if type(sm) == "userdata" and sm:IsValid() then mesh = str(safe(function() return sm:GetFName() end)) end
            end
            if mesh == "SM_CraftedTeleporter_Lodestone" then
                local loc = safe(function() return a:K2_GetActorLocation() end)
                if type(loc) == "table" or type(loc) == "userdata" then
                    local dx, dy = loc.X - ROOM_CENTER.X, loc.Y - ROOM_CENTER.Y
                    if math.sqrt(dx*dx + dy*dy) <= ROOM_RADIUS then
                        n = n + 1
                        out(f, string.format("%s | %s | yaw %s", str(safe(function() return a:GetFName() end)), vec(loc),
                            str(safe(function() return string.format("%.1f", a:K2_GetActorRotation().Yaw) end))))
                    end
                end
            end
        end
    end
    out(f, "Lodestones found: " .. n)
    f:close()
    print("[PortalLogger] lodestone dump done\n")
end
RegisterKeyBind(Key.F10, function() ExecuteInGameThread(dump_lodestones) end)

