-- Mock of the UE4SS globals the Portal Hub uses, for running mod/PortalHub/Scripts/main.lua outside the game.
T = 0
os.clock = function() return T end
LOGS = {}
print = function(s) LOGS[#LOGS + 1] = (tostring(s):gsub("\n$", "")) end

local NameMT = { __index = { ToString = function(self) return self.s end }, __eq = function(a, b) return a.s == b.s end }
function FName(s) return setmetatable({ s = s }, NameMT) end
function FText(s) return setmetatable({ s = s }, NameMT) end

local function obj(t) t.IsValid = function() return true end; return t end

-- The level row struct. By default as the game has it since update v1.5.0 (27 October 2026): native LevelMetadata, plain field names, a
-- soft-object Level in place of LevelFileName, found through DT_Levels.RowStruct (and /Script/AbioticFactor.LevelMetadata). Set before
-- loading this file: LEGACY_LEVEL_STRUCT = true for the old Blueprint struct (suffixed names, LevelFileName, found by its path only);
-- NO_ROW_STRUCT = true for a table whose RowStruct cannot be read (the hub must fall back to the paths).
local NATIVE_FIELDS = { "ReleaseGroup", "Level", "LevelFXRow_Day", "LevelFXRow_Night", "SectorName", "bIsSublevel", "ResettablePortalWorld",
    "HasFacilityShakes", "IsVignette", "EntranceTeleporter" }
local LEGACY_FIELDS = { "ReleaseGroup_20_111881DD49BCE06B31F20780CAC09223", "LevelFileName_4_4189631446EDDBE4B5EAE69952F1577C",
    "LevelFXRow_Day_9_730F761F48B9E958F8502BB10C47C998", "LevelFXRow_Night_8_0062E3FB47C3AD2FA814B988D9F37B33",
    "SectorName_13_6D7367C44F16A1C849E2EA9A512F6777", "ResettablePortalWorld_17_A659D3914286BC7EF9F48A91F94DF901",
    "HasFacilityShakes_22_502FB08F4709B6E77A4C38888B81C87C", "IsVignette_24_2C59FABF4FD2F51E062A6796CCE089E7",
    "EntranceTeleporter_27_F0895895499D0F0E1F0BDBB347641DB8" }
LEVEL_FIELDS = LEGACY_LEVEL_STRUCT and LEGACY_FIELDS or NATIVE_FIELDS
SOFT_FIELDS = { Level = true }          -- soft-object fields: writing one from Lua crashes the game, so AddRow must never get one
LEVEL_STRUCT_PATH = LEGACY_LEVEL_STRUCT and "/Game/Blueprints/Data/LevelMetadata_Struct.LevelMetadata_Struct" or "/Script/AbioticFactor.LevelMetadata"
function F(short)
    for _, n in ipairs(LEVEL_FIELDS) do
        if n == short or (n:sub(1, #short + 1) == short .. "_" and n:sub(#short + 2, #short + 2):match("%d")) then return n end
    end
end
local levelStruct = obj({ ForEachProperty = function(self, cb) for _, n in ipairs(LEVEL_FIELDS) do cb({ GetFName = function() return FName(n) end }) end end,
    GetFullName = function() return "ScriptStruct " .. LEVEL_STRUCT_PATH end })

local function levelRow(file, day, night, sector, vig, entrance)
    local r = {}
    r[F("ReleaseGroup")] = 0
    if F("LevelFileName") then r[F("LevelFileName")] = FName(file) end
    r[F("LevelFXRow_Day")] = { RowName = FName(day) }; r[F("LevelFXRow_Night")] = { RowName = FName(night) }
    r[F("SectorName")] = FText(sector); r[F("IsVignette")] = vig; r[F("EntranceTeleporter")] = FName(entrance or "None")
    return r
end
LEVEL_ROWS = { office1 = levelRow("Facility_Office1", "office1", "Office1_Night", "The Office Sector", false) }
ADDED = {}
local dtLevels = obj({
    FindRow = function(self, name) return LEVEL_ROWS[name] end,
    AddRow = function(self, name, row)
        local known = {}
        for _, n in ipairs(LEVEL_FIELDS) do known[n] = true end
        for k, v in pairs(row) do
            assert(known[k], "AddRow: no field " .. tostring(k) .. " in the row struct")
            assert(not SOFT_FIELDS[k], "AddRow: a value for soft-object field " .. k .. " (would crash the game)")
        end
        LEVEL_ROWS[name] = row; ADDED[#ADDED + 1] = name
    end,
})
if not NO_ROW_STRUCT and not LEGACY_LEVEL_STRUCT then dtLevels.RowStruct = levelStruct end
FX_ROWS = { Intro = {}, HGarden = {}, office1 = {}, Office1_Night = {}, Weather_Fog = {}, Weather_Fog_Night = {}, SouthIsland = {} }
local dtFX = obj({ FindRow = function(self, name) return FX_ROWS[name] end })

TRANSITIONS, UPDATES = {}, 0
PC = obj({
    ActiveLevelFXName = FName("office1"), Day_FX_Row = { RowName = FName("Weather_Fog") }, Night_FX_Row = { RowName = FName("Weather_Fog_Night") },   -- LevelFXRowHandle structs
    ActiveWeatherFXName = FName("Weather_Fog"), DisableAutomaticFX = false,
    TransitionToNewEnvironmentFX = function(self, use, d, n, speed, title)
        assert(type(use) == "boolean" and d.DataTable ~= nil and n.DataTable ~= nil and type(speed) == "number" and getmetatable(title) == NameMT, "bad transition args")
        TRANSITIONS[#TRANSITIONS + 1] = d.RowName.s .. " / " .. n.RowName.s .. " / '" .. title.s .. "'"
        self.Day_FX_Row = { RowName = FName(d.RowName.s) }; self.Night_FX_Row = { RowName = FName(n.RowName.s) }
    end,
    UpdateToNewEnvironmentFX = function(self) UPDATES = UPDATES + 1 end,
})
-- ActiveLevelName is a string property: a Lua string is written, an FString-like object (with ToString) is read back
local strStore = { ActiveLevelName = FName("Facility_Office1") }
setmetatable(PC, {
    __index = function(_, k) return strStore[k] end,
    __newindex = function(t, k, v)
        if k == "ActiveLevelName" then assert(type(v) == "string", "ActiveLevelName must be written as a Lua string"); strStore[k] = FName(v)
        else rawset(t, k, v) end
    end,
})
LOC = { X = -10000, Y = 9000, Z = 300 }
PAWN = obj({
    K2_GetActorLocation = function() return { X = LOC.X, Y = LOC.Y, Z = LOC.Z } end,
    GetFName = function() return FName("Pawn_1") end,
    CharacterMovement = { StopMovementImmediately = function() end, SetMovementMode = function() end },
    K2_TeleportTo = function() return true end,
    K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end,
})
PC.Pawn = PAWN

local LEVEL = "/Game/Mods/CordonaTest/Maps/CordonaTest_L0"
local LS = obj({ PackageNameToLoad = FName(LEVEL), IsLevelVisible = function() return true end, GetWorldAssetPackageFName = function() return FName(LEVEL) end })
WORLD = obj({ StreamingLevels = { ForEach = function(self, fn) fn(1, { get = function() return LS end }) end }, SpawnActor = function() return nil end })
local MGR = obj({ IsNight = false, CurrentWeatherEvent = FName("Fog") })

function FindFirstOf(name)
    if name == "Abiotic_PlayerController_C" then return PC end
    if name == "DayNightManager_C" then return MGR end
    return nil
end
function FindAllOf(name)
    if name == "BP_CordonaTestLoader_C" then return { obj({ K2_GetActorLocation = function() return { X = 1100000, Y = 1300000, Z = 0 } end }) } end
    return {}
end
function StaticFindObject(path)
    if path == "/Game/Blueprints/DataTables/Environment/DT_Levels.DT_Levels" then return dtLevels end
    if path == LEVEL_STRUCT_PATH then return levelStruct end
    if path == "/Game/Blueprints/DataTables/Environment/DT_LevelFX.DT_LevelFX" then return dtFX end
    if path == "/Game/Mods/CordonaTest/BP_CordonaTestLoader.Default__BP_CordonaTestLoader_C" and LOADER_TITLE then return obj({ WorldTitle = FText(LOADER_TITLE) }) end
    return nil
end
function LoadAsset() end
-- RegisterHook hands out ids like UE4SS (a Blueprint function's pre and post id are the same); UnregisterHook records what it was given.
-- ModRef.OnUnload is what UE4SS calls just before Restart All Mods closes the Lua state (CRD-032).
HOOK_ID, HOOKED, UNHOOKED = 100, {}, {}
function RegisterHook(name) HOOK_ID = HOOK_ID + 1; HOOKED[#HOOKED + 1] = { name = name, id = HOOK_ID }; return HOOK_ID, HOOK_ID end
function UnregisterHook(name, pre, post) UNHOOKED[#UNHOOKED + 1] = { name = name, pre = pre, post = post } end
ModRef = {}
function NotifyOnNewObject() end
function RegisterKeyBind() end
Key = setmetatable({}, { __index = function(_, k) return k end })
ModifierKey = Key
-- GAME_THREAD > 0 while a callback runs "on the game thread" (CRD-032: at Restart All Mods main.lua itself runs on UE4SS's own thread)
GAME_THREAD = 0
function ExecuteInGameThread(fn) GAME_THREAD = GAME_THREAD + 1; local ok, err = pcall(fn); GAME_THREAD = GAME_THREAD - 1; if not ok then error(err, 0) end end
QUEUE = {}
function ExecuteWithDelay(ms, fn) QUEUE[#QUEUE + 1] = fn end
function pump() local q = QUEUE; QUEUE = {}; for _, fn in ipairs(q) do fn() end end

package.preload["UEHelpers"] = function() return { GetWorld = function() return WORLD end, FindOrAddFName = FName } end
CONFIG = {
    worlds = { cordonatest_start = { loaderAsset = "/Game/Mods/CordonaTest/BP_CordonaTestLoader", loaderClass = "BP_CordonaTestLoader_C",
        level = LEVEL, origin = { 1100000, 1300000, 0 }, arrive = { 0, 0, 0, 0 },
        lighting = { sun = 1.0, sunColor = { 1.0, 0.95, 0.85 }, sunPitch = -50, sky = 1.0 }, killZ = -3000 } },
    portals = { { slot = "A-3", name = "Test World", destination = "cordonatest_start" } },
}
package.preload["config"] = function() return CONFIG end
