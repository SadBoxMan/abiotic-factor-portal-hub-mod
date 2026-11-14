-- Cordona Probe (CRD-020, dev only, not shipped): answers the open questions of findings/in-game-config-research.md.
--   1. Which save is loaded: AbioticGameInstance.ActiveWorldSaveName and AbioticFunctionLibrary:GetSaveSubfolderName(), logged at
--      mod load, when a Homeworld pad appears (at once and after the hub's 4 s spawn delay) and on the survey key ].
--   2. A console in the portal room: DELETE spawns a Button_Generic in front of the player (ButtonAlwaysPowered, ShouldSave = false) with a
--      custom ButtonName, and hooks InteractWith_A; each press steps the name ("press 1", "press 2", ...) and shows a message.
--   3. Multiplayer: the survey also lists, with network roles, the probe buttons near the player and every hub pad (hub_*), so a host and
--      a client can compare what they see. It also lists every pad in the portal room, whatever its ID, with its look (particle
--      asset) and its hum volume on this machine, so a client can tell whether the host's pads, IDs and looks reached it (CRD-023).
--   ] = identity + network survey (read-only)   DELETE = spawn the probe button (host only); press again to remove it
-- Keys (CRD-023): the survey was on F11, the game's fullscreen toggle; ] (UE4SS Key.OEM_SIX, US layout) carries only a debug-only game
-- binding (DebugCycleCultureBack), accepted by the author. DELETE is the game's "clear keybind" key inside the Controls menu only; kept.

local UEHelpers = require("UEHelpers")

local BUTTON_ASSET = "/Game/Blueprints/Environment/Switches/Button_Generic"
local BUTTON_CLASS = BUTTON_ASSET .. ".Button_Generic_C"
local HOMEWORLD_CLASS = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_HomeWorld.BP_Teleporter_HomeWorld_C"
local FUNC_LIB = "/Script/AbioticFactor.Default__AbioticFunctionLibrary"
local NAME_PREFIX = "Cordona console"
local SPAWN_AHEAD = 150          -- units in front of the player
local NEAR_M = 40                -- the survey lists Button_Generic actors this close to the player
local ROOM = { X = -12850, Y = 8250, Z = -400 }   -- roughly the middle of the portal room (slots.lua)
local SPAWN_DELAY_MS = 4000      -- the hub's own delay before it spawns its portals
local HOOKS = { "InteractWith_A", "InteractWith_A_LocalFX", "OnRep_Activated", "TriggerButtonWithoutUser" }
local ROLE_NAMES = { [0] = "None", [1] = "SimulatedProxy", [2] = "AutonomousProxy", [3] = "Authority" }

local probe = { buttons = {}, presses = 0, hooked = {}, notes = {} }

local function log(msg) print("[CordonaProbe] " .. msg .. "\n") end

local function valid(o) return o ~= nil and type(o) ~= "number" and type(o) ~= "string" and type(o) ~= "boolean" and o:IsValid() end

local function str(v)            -- an FString / FText / FName (or a Lua value) as plain text
    if v == nil then return "nil" end
    local t = type(v)
    if t == "string" or t == "number" or t == "boolean" then return tostring(v) end
    local ok, s = pcall(function() return v:ToString() end)
    if ok then return tostring(s) end
    return "<" .. t .. ">"
end

-- On a host every player has a controller, so the first one found may be a client's: pick the one this machine controls.
local function player_controller()
    local first, n = nil, 0
    for _, pc in ipairs(FindAllOf("Abiotic_PlayerController_C") or {}) do
        if valid(pc) then
            n = n + 1
            first = first or pc
            local ok, isLocal = pcall(function() return pc:IsLocalController() end)
            if ok and isLocal == true then return pc, n end
        end
    end
    if first then return first, n end
    local pc = FindFirstOf("Abiotic_PlayerController_C")
    if valid(pc) then return pc, 1 end
    return nil, 0
end

local function player()
    local pc = player_controller()
    if not pc then return nil end
    local ok, pawn = pcall(function() return pc.Pawn end)
    if ok and valid(pawn) then return pawn end
    return nil
end

local function screen(pawn, msg)
    if pawn then pcall(function() pawn:Client_DisplayWarningMessage(FText(msg), { R = 0.4, G = 1.0, B = 0.6, A = 1.0 }, false) end) end
end

local function role_of(actor)
    local lr, rr = nil, nil
    pcall(function() lr = actor:GetLocalRole() end)
    if lr == nil then pcall(function() lr = actor.Role end) end
    pcall(function() rr = actor:GetRemoteRole() end)
    if rr == nil then pcall(function() rr = actor.RemoteRole end) end
    local rep = nil
    pcall(function() rep = actor:GetIsReplicated() end)
    if rep == nil then pcall(function() rep = actor.bReplicates end) end
    local function nm(r) if type(r) == "number" then return (ROLE_NAMES[r] or "?") .. "(" .. r .. ")" end return str(r) end
    return "role=" .. nm(lr) .. " remote=" .. nm(rr) .. " replicates=" .. str(rep)
end

local function has_authority(actor)
    local ok, a = pcall(function() return actor:HasAuthority() end)
    if ok then return a end
    return nil
end

local function loc_text(actor)
    local ok, s = pcall(function() local l = actor:K2_GetActorLocation(); return string.format("%.0f, %.0f, %.0f", l.X, l.Y, l.Z) end)
    if ok then return s end
    return "?"
end

local function metres(a, b) return math.sqrt((a.X - b.X) ^ 2 + (a.Y - b.Y) ^ 2 + (a.Z - b.Z) ^ 2) / 100 end

------------------------------------------------------------------------------------------------------------------------
-- 1. Save identity

local function game_instance()
    local gi = nil
    pcall(function() gi = UEHelpers.GetGameInstance() end)
    if valid(gi) then return gi, "UEHelpers" end
    gi = FindFirstOf("AbioticGameInstance")
    if valid(gi) then return gi, "FindFirstOf" end
    return nil, "none"
end

local function log_identity(when)
    local gi, how = game_instance()
    local active = "no game instance"
    if gi then
        local ok, v = pcall(function() return gi.ActiveWorldSaveName end)
        active = ok and ("'" .. str(v) .. "'") or ("read failed: " .. tostring(v))
    end
    local sub = "library not found"
    local lib = StaticFindObject(FUNC_LIB)
    if valid(lib) then
        local ok, v = pcall(function() return lib:GetSaveSubfolderName() end)
        sub = ok and ("'" .. str(v) .. "'") or ("call failed: " .. tostring(v))
    end
    local pawn = player()
    local auth = pawn and str(has_authority(pawn)) or "no player"
    local giName = gi and (function() local ok, n = pcall(function() return gi:GetFullName() end); return ok and n or "?" end)() or "-"
    log("identity (" .. when .. "): ActiveWorldSaveName=" .. active .. "  GetSaveSubfolderName=" .. sub ..
        "  player HasAuthority=" .. auth .. "  game instance via " .. how .. ": " .. giName)
    return active, sub
end

------------------------------------------------------------------------------------------------------------------------
-- 2. The probe button

local function is_ours(btn)
    for i = #probe.buttons, 1, -1 do
        local b = probe.buttons[i]
        if not valid(b) then table.remove(probe.buttons, i)
        elseif b == btn then return true
        else
            local ok, same = pcall(function() return b:GetFullName() == btn:GetFullName() end)
            if ok and same then return true end
        end
    end
    return false
end

local function name_of(btn)
    local ok, v = pcall(function() return btn.ButtonName end)
    if ok then return str(v) end
    return "?"
end

local function button_state(btn)
    local parts = {}
    for _, k in ipairs({ "Activated", "ButtonDisabled", "ButtonAlwaysPowered", "ShouldSave", "ToggleSwitch", "OneTimeUse", "ButtonCooldown" }) do
        local ok, v = pcall(function() return btn[k] end)
        parts[#parts + 1] = k .. "=" .. (ok and str(v) or "?")
    end
    return table.concat(parts, " ")
end

local function hook_cb(fname)
    return function(self, a, b)
        local btn = nil
        pcall(function() btn = self:get() end)
        if not valid(btn) then return end
        local ours = is_ours(btn)
        local name = name_of(btn)
        if not ours and name:sub(1, #NAME_PREFIX) ~= NAME_PREFIX then return end     -- someone else's button: ignore
        local who = "-"
        pcall(function() local c = a and a:get(); if valid(c) then who = c:GetFName():ToString() end end)
        log("hook " .. fname .. " fired on " .. (ours and "our" or "a replicated probe") .. " button '" .. name .. "' (arg1=" .. who ..
            ", HasAuthority=" .. str(has_authority(btn)) .. ", " .. role_of(btn) .. ")")
        if fname ~= "InteractWith_A" or not ours then return end
        probe.presses = probe.presses + 1
        local newName = NAME_PREFIX .. ": press " .. probe.presses
        local ok, err = pcall(function() btn.ButtonName = FText(newName) end)
        log("  press " .. probe.presses .. ": ButtonName set to '" .. newName .. "' -> " .. (ok and ("reads back '" .. name_of(btn) .. "'") or ("failed: " .. tostring(err))) ..
            "; " .. button_state(btn))
        local char = nil
        pcall(function() char = a and a:get() end)
        if valid(char) then screen(char, "Cordona console pressed (" .. probe.presses .. ")") end
    end
end

-- probe.hooked[f] holds the ids RegisterHook returned (true if it returned none), so unload can take each hook off (CRD-032)
local function install_hooks()
    if not valid(StaticFindObject(BUTTON_CLASS)) then return false end
    for _, f in ipairs(HOOKS) do
        if not probe.hooked[f] then
            local ok, pre, post = pcall(RegisterHook, BUTTON_CLASS .. ":" .. f, hook_cb(f))
            if ok then
                probe.hooked[f] = (type(pre) == "number" and type(post) == "number") and { pre, post } or true
                log("hooked " .. f)
            else
                log("hook " .. f .. " failed: " .. tostring(pre))
            end
        end
    end
    return true
end

-- Restart All Mods closes this Lua state; ModRef.OnUnload runs just before. UE4SS drops a Blueprint function's hooks only with the mod that
-- hooked it first, so each hook is taken off here (UnregisterHook on a Blueprint function only marks the callback as gone).
local function unregister_hooks()
    local n = 0
    for f, ids in pairs(probe.hooked) do
        if type(ids) == "table" then
            local ok, err = pcall(UnregisterHook, BUTTON_CLASS .. ":" .. f, ids[1], ids[2])
            if ok then n = n + 1 else log("unloading: " .. f .. " hook could not be unregistered: " .. tostring(err):match("^[^\r\n]*")) end
        end
    end
    probe.hooked = {}
    log("unloading: " .. n .. " hook(s) unregistered")
end

local function remove_buttons()
    local n = 0
    for _, b in ipairs(probe.buttons) do
        if valid(b) then pcall(function() b:K2_DestroyActor() end); n = n + 1 end
    end
    probe.buttons = {}
    return n
end

local function spawn_button()
    log("DELETE pressed: spawn the probe button")
    local pawn = player()
    if not pawn then log("no player") return end
    if has_authority(pawn) == false then
        log("this machine is a client: the button is spawned by the host only (a client's own copy would not reach the server)")
        screen(pawn, "Probe: the button is host only")
        return
    end
    local world = UEHelpers.GetWorld()
    if not valid(world) then log("no world") return end
    local cls = StaticFindObject(BUTTON_CLASS)
    if not valid(cls) then
        pcall(LoadAsset, BUTTON_ASSET)
        cls = StaticFindObject(BUTTON_CLASS)
    end
    if not valid(cls) then log("Button_Generic class not found, even after LoadAsset") return end
    remove_buttons()
    local okL, here = pcall(function() return pawn:K2_GetActorLocation() end)
    local okR, rot = pcall(function() return pawn:K2_GetActorRotation() end)
    if not (okL and okR) then log("cannot read the player's position") return end
    local yaw = rot.Yaw
    local r = math.rad(yaw)
    local at = { X = here.X + math.cos(r) * SPAWN_AHEAD, Y = here.Y + math.sin(r) * SPAWN_AHEAD, Z = here.Z }
    log(string.format("player at %.0f, %.0f, %.0f (yaw %.1f), %.1f m from the portal room's middle; spawning at %.0f, %.0f, %.0f",
        here.X, here.Y, here.Z, yaw, metres(here, ROOM), at.X, at.Y, at.Z))
    local okS, btn = pcall(function() return world:SpawnActor(cls, at, { Pitch = 0.0, Yaw = yaw + 180.0, Roll = 0.0 }) end)
    if not okS or not valid(btn) then log("SpawnActor failed: " .. tostring(btn)) return end
    probe.buttons[#probe.buttons + 1] = btn
    probe.presses = 0
    log("spawned " .. str(btn:GetFullName()) .. "; defaults: name '" .. name_of(btn) .. "', " .. button_state(btn))
    local sets = {
        { "ButtonAlwaysPowered", function() btn.ButtonAlwaysPowered = true end },
        { "ShouldSave", function() btn.ShouldSave = false end },
        { "ButtonDisabled", function() btn.ButtonDisabled = false end },
        { "ButtonName", function() btn.ButtonName = FText(NAME_PREFIX .. ": press 0") end },
    }
    for _, s in ipairs(sets) do
        local ok, err = pcall(s[2])
        if not ok then log("  setting " .. s[1] .. " failed: " .. tostring(err)) end
    end
    log("  after setting: name '" .. name_of(btn) .. "', " .. button_state(btn) .. ", " .. role_of(btn))
    install_hooks()
    screen(pawn, "Probe button spawned: look at it, then interact")
end

------------------------------------------------------------------------------------------------------------------------
-- 3. Network survey (read-only)

local function survey()
    log("---- ]: identity and network survey")
    log_identity("survey key ]")
    install_hooks()
    local pawn = player()
    local here = nil
    if pawn then
        pcall(function() here = pawn:K2_GetActorLocation() end)
        log("player " .. str(pawn:GetFName()) .. " at " .. loc_text(pawn) .. ", " .. role_of(pawn) ..
            (here and string.format(", %.1f m from the portal room's middle", metres(here, ROOM)) or ""))
    end
    local n, near = 0, 0
    for _, b in ipairs(FindAllOf("Button_Generic_C") or {}) do
        if valid(b) then
            n = n + 1
            local name = name_of(b)
            local okB, bl = pcall(function() return b:K2_GetActorLocation() end)
            local d = (here and okB) and metres(here, bl) or nil
            if (d and d <= NEAR_M) or name:sub(1, #NAME_PREFIX) == NAME_PREFIX then
                near = near + 1
                log(string.format("  button '%s' at %s%s, ours=%s, HasAuthority=%s, %s; %s", name, loc_text(b),
                    d and string.format(" (%.1f m)", d) or "", str(is_ours(b)), str(has_authority(b)), role_of(b), button_state(b)))
            end
        end
    end
    log("  " .. n .. " Button_Generic actor(s) in the world, " .. near .. " listed (probe name or within " .. NEAR_M .. " m)")
    local _, pcs = player_controller()
    log("  " .. pcs .. " player controller(s) on this machine")
    local pads, perId, room = 0, {}, 0
    for _, t in ipairs(FindAllOf("BP_Teleporter_ParentBP_C") or {}) do
        if valid(t) then
            local okI, id = pcall(function() return t.MyTeleporterID:ToString() end)
            if not okI then id = "?" end
            local okP, pl = pcall(function() return t:K2_GetActorLocation() end)
            local inRoom = okP and metres(pl, ROOM) <= NEAR_M
            if id:sub(1, 4) == "hub_" then
                pads = pads + 1
                perId[id] = (perId[id] or 0) + 1
                log("  hub pad " .. id .. " at " .. loc_text(t) .. ", HasAuthority=" .. str(has_authority(t)) .. ", " .. role_of(t))
            end
            if id:sub(1, 4) == "hub_" or inRoom then
                room = room + 1
                local dest, active, hidden, look, hum = "?", "?", "?", "?", "?"
                pcall(function() dest = t.DestinationTeleporterID:ToString() end)
                pcall(function() active = str(t.IsTeleporterActive) end)
                pcall(function() hidden = str(t.bHidden) end)
                pcall(function() local a = t.ParticleLoop.Asset; if valid(a) then look = a:GetFName():ToString() else look = "none" end end)
                pcall(function() local h = t.PortalHumLoop; if valid(h) then hum = string.format("%.3f", h.VolumeMultiplier) end end)
                log(string.format("  pad '%s' -> '%s' at %s: active=%s hidden=%s look=%s hum=%s, %s", id, dest, loc_text(t), active, hidden, look, hum, role_of(t)))
            end
        end
    end
    log("  " .. room .. " pad(s) listed with look and hum (hub_ IDs, or within " .. NEAR_M .. " m of the portal room's middle)")
    local dup = {}
    for id, c in pairs(perId) do if c > 1 then dup[#dup + 1] = id .. " x" .. c end end
    table.sort(dup)
    log("  " .. pads .. " hub pad(s)" .. (#dup > 0 and ("; more than one with the same ID: " .. table.concat(dup, ", ")) or "; no duplicate IDs"))
    log("  hooks installed: " .. (function() local t = {}; for _, f in ipairs(HOOKS) do if probe.hooked[f] then t[#t + 1] = f end end; return #t > 0 and table.concat(t, ", ") or "none (class not loaded yet)" end)())
    log("---- survey done")
    screen(pawn, "Probe survey logged")
end

------------------------------------------------------------------------------------------------------------------------

-- Nothing touches the game from the mod loader's own thread: on a Restart All Mods the button class is already loaded, and
-- registering its hooks (and reading the game instance) straight from here froze the game on 9 November. The hub does the same:
-- its hook is only ever registered on the game thread.
ExecuteInGameThread(function()
    log_identity("mod load")
    install_hooks()
end)

NotifyOnNewObject(HOMEWORLD_CLASS, function()
    if probe.pendingHomeworld then return end
    probe.pendingHomeworld = true
    ExecuteInGameThread(function() log_identity("a Homeworld pad appeared") end)
    ExecuteWithDelay(SPAWN_DELAY_MS, function()
        probe.pendingHomeworld = false
        ExecuteInGameThread(function() log_identity("portal-spawn time, " .. SPAWN_DELAY_MS .. " ms after the Homeworld pad"); install_hooks() end)
    end)
end)

-- Keys kept clear of the hub and lab (the lab's INSERT is CRD-012's Hub Exit preview) and of the game's F11 (fullscreen): ] and DELETE only.
RegisterKeyBind(Key.OEM_SIX, function() ExecuteInGameThread(survey) end)
RegisterKeyBind(Key.DEL, function() ExecuteInGameThread(function()
    local n = remove_buttons()
    if n > 0 then log("DELETE pressed: removed " .. n .. " probe button(s)") else spawn_button() end
end) end)
if not pcall(function() ModRef.OnUnload = unregister_hooks end) then log("unload callback not available in this UE4SS") end
log("keys: ] = identity + network survey (read-only), DELETE = spawn the probe button (host only) / press again to remove it")
