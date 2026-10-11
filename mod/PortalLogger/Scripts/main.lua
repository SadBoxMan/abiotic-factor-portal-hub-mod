-- PortalLogger: dumps every teleporter actor so we can copy real values for the Dunkeltaler portal.
-- Press F6 in game (stand in the Facility) to dump. Output goes to UE4SS.log and PortalLogger.txt.

local out_path = "PortalLogger.txt"

local function safe(fn)
    local ok, v = pcall(fn)
    if ok then return v end
    return "<err>"
end

local function str(v)
    if v == nil then return "nil" end
    local t = type(v)
    if t == "userdata" then
        local ok, s = pcall(function() return v:ToString() end)
        if ok then return s end
        return "<userdata>"
    end
    return tostring(v)
end

local function log(f, line)
    print("[PortalLogger] " .. line .. "\n")
    f:write(line .. "\n")
end

local function dump()
    local f = io.open(out_path, "w")
    if not f then print("[PortalLogger] cannot open output file\n") return end
    local actors = FindAllOf("BP_Teleporter_ParentBP_C") or {}
    log(f, "Teleporters found: " .. #actors)
    for _, a in ipairs(actors) do
        if a:IsValid() then
            local loc = safe(function() return a:K2_GetActorLocation() end)
            local rot = safe(function() return a:K2_GetActorRotation() end)
            log(f, "----")
            log(f, "Class: " .. str(safe(function() return a:GetClass():GetFName() end)))
            log(f, "Name: " .. str(safe(function() return a:GetFName() end)))
            log(f, "FullName: " .. str(safe(function() return a:GetFullName() end)))
            log(f, "MyTeleporterID: " .. str(safe(function() return a.MyTeleporterID end)))
            log(f, "DestinationTeleporterID: " .. str(safe(function() return a.DestinationTeleporterID end)))
            log(f, "IsTeleporterActive: " .. str(safe(function() return a.IsTeleporterActive end)))
            log(f, "RequiredDLC: " .. str(safe(function() return a.RequiredDLC.RowName end)))
            log(f, "RequiredWorldFlag: " .. str(safe(function() return a.RequiredWorldFlag.RowName end)))
            log(f, "Location: " .. str(safe(function() return string.format("%.1f, %.1f, %.1f", loc.X, loc.Y, loc.Z) end)) .. " (type " .. type(loc) .. ")")
            log(f, "Rotation: " .. str(safe(function() return string.format("P=%.1f Y=%.1f R=%.1f", rot.Pitch, rot.Yaw, rot.Roll) end)))
            local lvl = safe(function() return a:GetLevel():GetFullName() end)
            log(f, "Level: " .. str(lvl))
        end
    end
    f:close()
    print("[PortalLogger] done\n")
end

RegisterKeyBind(Key.F6, function() ExecuteInGameThread(dump) end)
print("[PortalLogger] loaded - press F6 in game to dump teleporters\n")

require("streaming")

