# Portal designs in the hub (CRD-044): designs.lua beside config.lua holds named designs; a portal's design = "Name" uses one, a path is
# still a game look. Checks: a design is drawn (look, height, scale, hidden parts, the mesh ring with only the lab's proven calls, collision
# off before the shape, our Geo ring loaded by name with GetAsset, tint = grey x RGB, scene, extra parameters, the pad's own look hidden for
# look = "none"); every portal at its look's height from LuciDin's sheet (docs/portal-heights.csv); unknown names and bad fields fall back
# with a log line; MHEs and manual portals inherit their portal's design, light and height (mheHeight there); the pak missing = the look
# stays, one log line per spawn, the pak never asked for; a game ring; designs.lua read again on NUMPAD 1; a BOM; client mode styles its
# own pads with its own designs; no new object scans, timers or watches; the shipped designs.lua; the height table = the sheet.
#   python test_hub_designs.py [path to a main.lua, default the repo's]
import sys, os, csv, tempfile
sys.path.insert(0, os.path.join(os.environ.get("TEMP", ""), "pylib"))   # lupa fallback (pip install --target %TEMP%\pylib lupa)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Cordona pylib"))   # lupa: <repo parent>\Cordona pylib first
import lupa

S = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(S, "..", "..", "..")
HUB = os.path.join(ROOT, "mod", "PortalHub", "Scripts")
MAIN = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HUB, "main.lua")
TMP = tempfile.mkdtemp(prefix="cordona-designs-")
PAK = os.path.join(TMP, "PortalHubLooks_P.utoc")

GAME = r'''
local Slots = require("slots")
local function obj(t) t.IsValid = function() return t.gone ~= true end; return t end
TELEPORTER = "/Game/Blueprints/Environment/Teleporters/BP_Teleporter_ParentBP.BP_Teleporter_ParentBP_C"
PADS, NEXT, CALLS, SCANS, FINDFIRST = {}, 0, {}, 0, 0
NOTIFY, HOOKS, KEYS = {}, {}, {}
LOADS, GETASSET = {}, {}
function NotifyOnNewObject(cls, fn) NOTIFY[cls] = NOTIFY[cls] or {}; table.insert(NOTIFY[cls], fn) end
function RegisterHook(name, fn) local id = 201 + #HOOKS; HOOKS[#HOOKS + 1] = { name = name, fn = fn, id = id }; return id, id end
function RegisterKeyBind(key, a, b) KEYS[key] = b or a end
function n_notify() local n = 0; for _, l in pairs(NOTIFY) do n = n + #l end; return n end
local function call(what) CALLS[#CALLS + 1] = what end

-- a material instance (dynamic): remembers what was set; reads back a colour per parameter like the game's
function mkmid(parent)
    local m = obj({ parent = parent, vec = {}, tex = {}, sc = {} })
    m.K2_GetVectorParameterValue = function(self, n) local g = GREY[n:ToString()] or 1.0; return { R = g, G = g, B = g, A = 1 } end
    m.SetVectorParameterValue = function(self, n, c) self.vec[n:ToString()] = c end
    m.SetTextureParameterValue = function(self, n, t) self.tex[n:ToString()] = t.path end
    m.SetScalarParameterValue = function(self, n, v) self.sc[n:ToString()] = v end
    return m
end
GREY = { PortalCenterColor = 0.5, PortalCenterColor2 = 1.0, PortalEdge = 4.0, DistortionEdge = 2.0 }
-- a component added to a pad
function mkcomp(pad)
    local c = obj({ pad = pad, steps = {} })
    local function step(s) table.insert(c.steps, s); call(s) end
    c.SetCollisionEnabled = function(self, v) if FAIL_COLLISION then error("no") end; c.collision = v; step("collision") end
    c.SetStaticMesh = function(self, m) c.mesh = m.path; step("mesh") end
    c.SetMaterial = function(self, i, m) c.mat = m; step("material") end
    c.K2_SetRelativeLocation = function(self, l) c.loc = { X = l.X, Y = l.Y, Z = l.Z } end
    c.K2_SetRelativeRotation = function(self, r) c.rot = { Pitch = r.Pitch, Yaw = r.Yaw, Roll = r.Roll } end
    c.SetRelativeScale3D = function(self, s) c.scale = { X = s.X, Y = s.Y, Z = s.Z } end
    c.K2_DestroyComponent = function(self) c.gone = true; step("destroyed") end
    return c
end
function mkpad(id, dest, x, y, z, replicated)
    local h = obj({ v = 1.0 })
    h.SetVolumeMultiplier = function(self, m) h.v = m end
    local pl = { assets = {}, hidden = {}, visible = true, RelativeLocation = { X = 0, Y = 0, Z = 158 } }
    pl.SetAsset = function(self, s) table.insert(self.assets, s.path) end
    pl.Activate = function() end
    pl.SetEmitterEnable = function(self, n, on) if not on then table.insert(self.hidden, n:ToString()) end end
    pl.K2_SetRelativeLocation = function(self, l) self.RelativeLocation = { X = l.X, Y = l.Y, Z = l.Z } end
    pl.SetRelativeScale3D = function(self, s) self.scale = { X = s.X, Y = s.Y, Z = s.Z } end
    pl.SetVisibility = function(self, v) self.visible = v end
    local p = obj({ MyTeleporterID = FName(id), DestinationTeleporterID = FName(dest), IsTeleporterActive = true, PortalHumLoop = h,
        replicated = replicated, OnRep_IsTeleporterActive = function() end, comps = {},
        K2_GetActorLocation = function() return { X = x, Y = y, Z = z } end,
        K2_GetActorRotation = function() return { Pitch = 0, Yaw = 0, Roll = 0 } end,
        ParticleLoop = pl,
        PointLight = obj({ Intensity = 1000, SetLightColor = function(self, c) self.color = c end, SetIntensity = function(self, i) self.Intensity = i end }) })
    p.AddComponentByClass = function(self, cls, manual, xf, deferred)
        assert(cls.path == "/Script/Engine.StaticMeshComponent" and manual == false and deferred == false and xf.Scale3D.X == 1, "bad AddComponentByClass")
        call("add"); local c = mkcomp(p); table.insert(p.comps, c); return c
    end
    NEXT = NEXT + 1
    local nm = "BP_Teleporter_ParentBP_C_" .. NEXT
    p.GetFName = function() return FName(nm) end
    p.K2_DestroyActor = function() if not p.replicated then p.gone = true end end
    p.SetActorHiddenInGame = function() end
    PADS[#PADS + 1] = p
    return p
end
function arrive(p) for _, fn in ipairs(NOTIFY[TELEPORTER] or {}) do fn(p) end; return p end
function host_pad(slot, dest, id)
    local loc = Slots.pose(Slots.byId[slot])
    return arrive(mkpad(id or ("hub_" .. slot:gsub("-", "")), dest, loc.X, loc.Y, loc.Z, true))
end
function find(id) for _, p in ipairs(PADS) do if p:IsValid() and p.MyTeleporterID:ToString() == id then return p end end end
function ring(id) local p = find(id); for _, c in ipairs(p.comps) do if not c.gone then return c end end end
function nring(id) local n = 0; for _, c in ipairs(find(id).comps) do if not c.gone then n = n + 1 end end; return n end
function height(id) return find(id).ParticleLoop.RelativeLocation.Z end
function look(id) local a = find(id).ParticleLoop.assets; return a[#a] end

mkpad("H_Garden_Entrance", "H_Garden_Start", -13115.2, 8391.4, 900, true)
mkpad("train_start", "None", 333725.9, 12323.6, 934.2, true)
mkpad("anteverse_a_start", "anteverse_early_exit", 119175.3, 330450.7, 2332.4, true)

local padClass = obj({ kind = "pad", path = TELEPORTER })
local homePad = obj({})
local meshClass = obj({ path = "/Script/Engine.StaticMeshComponent" })
local lib = obj({ CreateDynamicMaterialInstance = function(self, outer, parent, name, kind)
    assert(parent and parent.path and name:ToString() == "None" and kind == 0, "bad CreateDynamicMaterialInstance"); call("mid"); return mkmid(parent) end })
local geoLoaded = {}
local helpers = obj({ GetAsset = function(self, a)
    local pkg, name = a.PackageName:ToString(), a.AssetName:ToString()
    table.insert(GETASSET, pkg .. " | " .. name)
    if NO_PAK_CONTENT then return nil end
    geoLoaded[pkg .. "." .. name] = obj({ path = pkg .. "." .. name }); return geoLoaded[pkg .. "." .. name] end })
local gameAssets = {}
local baseFind, baseAll, baseFirst = StaticFindObject, FindAllOf, FindFirstOf
function StaticFindObject(p)
    if p == TELEPORTER then return padClass end
    if p == "/Script/Engine.StaticMeshComponent" then return meshClass end
    if p == "/Script/Engine.Default__KismetMaterialLibrary" then return lib end
    if p == "/Script/AssetRegistry.Default__AssetRegistryHelpers" then return helpers end
    if p:sub(1, 22) == "/Game/Mods/PortalHubLo" then return geoLoaded[p] end      -- only after GetAsset (LoadAsset finds nothing in our pak)
    if p:sub(1, 15) == "/Game/Particles" and p:find("/Materials/") then return gameAssets[p] end
    if p:sub(1, 15) == "/Game/Particles" or p == "/Engine/BasicShapes/Plane.Plane" then return obj({ path = p }) end
    return baseFind(p)
end
function LoadAsset(p) table.insert(LOADS, p); if p:find("/Materials/") and not MISSING_GAME_RING then gameAssets[p] = obj({ path = p }) end end
CONTROLLERS = { PC }
function FindAllOf(n)
    SCANS = SCANS + 1
    if n == "BP_Teleporter_ParentBP_C" then
        local out = {}
        for _, p in ipairs(PADS) do if p:IsValid() then out[#out + 1] = p end end
        return out
    end
    if n == "Abiotic_PlayerController_C" then return CONTROLLERS end
    return baseAll(n)
end
function FindFirstOf(n)
    FINDFIRST = FINDFIRST + 1
    if n == "BP_Teleporter_HomeWorld_C" then return homePad end
    if n == "Abiotic_PlayerController_C" then return CONTROLLERS[1] end
    return baseFirst(n)
end
WORLD.SpawnActor = function(self, cls, loc, rot) return mkpad("None", "None", loc.X, loc.Y, loc.Z, false) end
AUTH = true
PC.HasAuthority = function() return AUTH end
PC.IsLocalController = function() return true end
PAWN.CapsuleComponent = { GetScaledCapsuleHalfHeight = function() return 88 end }
'''

res = []
def check(n, c, d=""):
    res.append(bool(c)); print(("PASS  " if c else "FAIL  ") + n + (("   -> " + str(d)) if d and not c else ""))

def lua_path(p): return p.replace("\\", "/")

HUBS = []
class Hub:
    def __init__(self, portals, designs=None, pak=True, mhe="{}", before="", bom=False):
        HUBS.append(self)
        self.dfile = os.path.join(TMP, "designs%d.lua" % len(HUBS))
        if designs is not None:
            with open(self.dfile, "wb") as f:
                f.write((b"\xef\xbb\xbf" if bom else b"") + designs.encode("utf-8"))
        pak_path = PAK if pak else os.path.join(TMP, "nothing-here.utoc")
        if pak and not os.path.exists(PAK):
            open(PAK, "wb").close()
        self.L = L = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.g = L.globals()
        L.execute("package.path = [[%s\\?.lua;]] .. package.path" % HUB)
        L.execute(open(os.path.join(S, "hub_mock.lua"), encoding="utf-8").read())
        L.execute("CONFIG.worlds = {}")
        L.execute("CONFIG.portals = %s" % portals)
        L.execute('package.preload["manual_exits"] = function() return %s end' % mhe)
        L.execute('package.preload["designs"] = function() return {} end')          # never the shipped file (tests give their own)
        L.execute('PORTALHUB_DESIGNS_PATH = [[%s]]; PORTALHUB_LOOKS_PAK = [[%s]]; PORTALHUB_MHE_PATH = [[%s/none.lua]]'
                  % (lua_path(self.dfile), lua_path(pak_path), lua_path(TMP)))
        L.execute(GAME)
        if before:
            L.execute(before)
        L.execute(open(MAIN, encoding="utf-8").read())
        self.pump()
    def ev(self, x): return self.L.eval(x)
    def ex(self, x): self.L.execute(x)
    def pump(self, n=6):
        for _ in range(n): self.L.execute("pump()")
    def logs(self, since=0): return [self.g.LOGS[i] for i in range(since + 1, len(self.g.LOGS) + 1)]
    def n(self): return len(self.g.LOGS)
    def has(self, text, since=0): return any(text in l for l in self.logs(since))
    def count(self, text, since=0): return sum(text in l for l in self.logs(since))
    def write(self, designs):
        with open(self.dfile, "w", encoding="utf-8", newline="\n") as f:
            f.write(designs)

def portals(*items): return "{ " + ", ".join(items) + " }"
def P(slot, dest, design=None, extra=""):
    d = "" if design is None else (", design = %s" % ('"%s"' % design))
    return '{ slot = "%s", name = "%s", destination = "%s"%s%s }' % (slot, dest, dest, d, extra)
FR = "/Game/Particles/Niagara_Portal_Friendly_Red.Niagara_Portal_Friendly_Red"
DESIGNS = r'''
return {
    ["Cordona Arch"] = { look = "none", ring = "Arch_Col", tint = { 0.5, 0.25, 1.0 }, height = 130, mheHeight = 150, scene = "TC_Portal_Alps",
        params = { SwirlSpeed = -0.35 } },
    ["Big Red"] = { look = "Niagara_Portal_Friendly_Red", scale = { 1.5, 1.2, 1.3 }, hide = { "sparks", "portal" } },
    ["Garden Ring"] = { look = "Niagara_Portal_Blueverse", ring = "M_Portal_Garden", size = { 2.5, 2.5 } },
    ["Ringless"] = { look = "none" },
    ["Broken"] = { look = "Niagara Portal!", ring = "Spiral_Big", height = "tall", scale = { 1, 2 } },
    ["Tall Door"] = { look = "none", ring = "Door_Pri" },
}
'''

print("=== a design with our Geo ring, look hidden")
h = Hub(portals(P("A-3", "anteverse_a_start", "Cordona Arch")), DESIGNS)
check("the hub logs how many saved designs it read", h.has("6 saved design(s) in designs.lua"), h.logs()[:12])
check("one ring component on the portal", h.ev("nring('hub_A3')") == 1)
check("ring steps in the lab's proven order: add, collision off, plane, material instance, material",
      list(h.ev("CALLS").values())[:5] == ["add", "collision", "mesh", "mid", "material"], list(h.ev("CALLS").values()))
check("collision switched off (0) before any shape", h.ev("ring('hub_A3').steps[1]") == "collision" and h.ev("ring('hub_A3').collision") == 0)
check("the shape is the engine plane", h.ev("ring('hub_A3').mesh") == "/Engine/BasicShapes/Plane.Plane")
check("our Geo ring loaded by name with GetAsset (package and asset)",
      list(h.ev("GETASSET").values()) == ["/Game/Mods/PortalHubLooks/Geo/MI_GeoArch_Col | MI_GeoArch_Col"], list(h.ev("GETASSET").values()))
check("its material instance comes from that Geo ring", h.ev("ring('hub_A3').mat.parent.path") == "/Game/Mods/PortalHubLooks/Geo/MI_GeoArch_Col.MI_GeoArch_Col")
check("stood up as square C (pitch 0, yaw 90, roll 90)", h.ev("ring('hub_A3').rot.Yaw == 90 and ring('hub_A3').rot.Roll == 90 and ring('hub_A3').rot.Pitch == 0"))
check("sized from the Arch shape: 1 x 2 m (scale X = width, Y = height)", h.ev("ring('hub_A3').scale.X == 1 and ring('hub_A3').scale.Y == 2 and ring('hub_A3').scale.Z == 1"))
check("look and ring at the design's height (130 cm)", h.ev("height('hub_A3')") == 130 and h.ev("ring('hub_A3').loc.Z") == 130)
check("tint = grey level x RGB on all four colours",
      h.ev("ring('hub_A3').mat.vec.PortalEdge.R") == 2.0 and h.ev("ring('hub_A3').mat.vec.PortalEdge.B") == 4.0
      and h.ev("ring('hub_A3').mat.vec.DistortionEdge.G") == 0.5 and h.ev("ring('hub_A3').mat.vec.PortalCenterColor.R") == 0.25)
check("scene: the cube map into PortalTexture", h.ev("ring('hub_A3').mat.tex.PortalTexture") == "/Game/Particles/RenderTargets/TC_Portal_Alps.TC_Portal_Alps")
check("an extra number parameter is set", h.ev("ring('hub_A3').mat.sc.SwirlSpeed") == -0.35)
check("look = none: the pad's own look is hidden once the ring is on", h.ev("find('hub_A3').ParticleLoop.visible") is False)
check("the log names the design and its ring", h.has("design 'Cordona Arch': ring MI_GeoArch_Col, 1.00 x 2.00 m"), [l for l in h.logs() if "ring" in l])
check("the player's height is logged once for the editor's preview (capsule x 2)", h.count("player capsule: half height 88.0 cm, so the player stands 176.0 cm tall") == 1)
h.ex("KEYS.NUM_ONE()"); h.pump()
check("NUMPAD 1: the respawned portal gets its ring again (one per pad)", h.ev("nring('hub_A3')") == 1)
check("... the Geo ring is not loaded a second time (kept for the session)", len(list(h.ev("GETASSET").values())) == 1)
check("... and the player height line stays a once-per-load line", h.count("player capsule:") == 1)

print("=== plain looks and other designs")
h = Hub(portals(P("A-3", "anteverse_a_start", FR), P("A-4", "train_start"), P("B-1", "anteverse_a_start", "Big Red"),
                P("B-2", "train_start", "Garden Ring"), P("B-4", "train_start", "Tall Door")), DESIGNS)
check("a plain path: no ring, its look", h.ev("nring('hub_A3')") == 0 and h.ev("look('hub_A3')") == FR)
check("a plain Friendly Red sits at LuciDin's height for it (108 cm)", h.ev("height('hub_A3')") == 108)
check("no design at all: the default look at its sheet height (128 cm)",
      h.ev("look('hub_A4')") == "/Game/Particles/Niagara_Portal.Niagara_Portal" and h.ev("height('hub_A4')") == 128)
check("a look-only design: its look, no ring", h.ev("look('hub_B1')") == FR and h.ev("nring('hub_B1')") == 0)
check("... at the look's sheet height when it sets none (108 cm)", h.ev("height('hub_B1')") == 108)
check("... with its look scale X, Y, Z", h.ev("find('hub_B1').ParticleLoop.scale.X == 1.5 and find('hub_B1').ParticleLoop.scale.Y == 1.2 and find('hub_B1').ParticleLoop.scale.Z == 1.3"))
check("... its hidden parts switched off, but never the portal part", list(h.ev("find('hub_B1').ParticleLoop.hidden").values()) == ["sparks"],
      list(h.ev("find('hub_B1').ParticleLoop.hidden").values()))
check("a game ring: loaded from the game's materials (LoadAsset), on the plane at the design's size", h.ev("nring('hub_B2')") == 1
      and "/Game/Particles/Materials/M_Portal_Garden.M_Portal_Garden" in list(h.ev("LOADS").values())
      and h.ev("ring('hub_B2').scale.X") == 2.5)
check("... with a look kept (not none), the look stays visible", h.ev("find('hub_B2').ParticleLoop.visible") is True)
check("... and the ring sits at the look's height (Blueverse 128)", h.ev("ring('hub_B2').loc.Z") == 128)
check("a ring-only design with no height: the ring stands 28 cm above the pad (Door 3 m: centre 178)", h.ev("height('hub_B4')") == 178
      and h.ev("ring('hub_B4').scale.Y") == 3)

print("=== names and fields that can't be used")
h = Hub(portals(P("A-3", "train_start", "Nobody"), P("A-4", "train_start", "Ringless"), P("B-1", "train_start", "Broken")), DESIGNS)
check("an unknown design name: logged, the default look", h.has("design 'Nobody' is not in designs.lua; using the default look")
      and h.ev("look('hub_A3')") == "/Game/Particles/Niagara_Portal.Niagara_Portal")
check("look = none with no ring: logged, the default look stays visible", h.has("design 'Ringless' hides the look") and h.ev("find('hub_A4').ParticleLoop.visible") is True)
check("bad fields are named in the log and ignored", h.has("design 'Broken': ignored what can't be read: look, height, scale, ring"),
      [l for l in h.logs() if "Broken" in l])
check("... the portal still spawns with the default look and no ring", h.ev("nring('hub_B1')") == 0 and h.ev("look('hub_B1')") == "/Game/Particles/Niagara_Portal.Niagara_Portal")
h = Hub(portals(P("A-3", "train_start", "Cordona Arch")), "return { oops = ")
check("a broken designs.lua: logged, no designs, the portal gets the default look", h.has("designs.lua can't be read") and h.ev("nring('hub_A3')") == 0
      and h.ev("look('hub_A3')") == "/Game/Particles/Niagara_Portal.Niagara_Portal")
h = Hub(portals(P("A-3", "train_start", "Cordona Arch")), None)
check("no designs.lua at all: no error, 0 designs, the default look", h.has("0 saved design(s)") and h.ev("nring('hub_A3')") == 0)
h = Hub(portals(P("A-3", "train_start", "Cordona Arch")), DESIGNS, bom=True)
check("a designs.lua saved with a BOM is still read", h.ev("nring('hub_A3')") == 1)

print("=== MHEs and manual portals inherit their portal's design")
MHE = '{ anteverse_a_start = { 119300, 330300, 2300, 90 }, train_start = { 334000, 12000, 900, 0 }, H_Cabin_Start = { 1, 2, 3, 0 } }'
h = Hub(portals(P("A-3", "anteverse_a_start", "Cordona Arch", ', lightColor = { 1, 0.5, 0 }'), P("A-4", "train_start", "Big Red", ', exits = "manual"')), DESIGNS, mhe=MHE)
check("the standalone MHE leads to its hub portal", h.ev("find('hub_mhe_anteverse_a_start').DestinationTeleporterID:ToString()") == "hub_A3")
check("... and takes its design: the Geo ring, look hidden", h.ev("nring('hub_mhe_anteverse_a_start')") == 1
      and h.ev("find('hub_mhe_anteverse_a_start').ParticleLoop.visible") is False)
check("... at the design's mheHeight (150 cm, the Door rule)", h.ev("height('hub_mhe_anteverse_a_start')") == 150)
check("... with its portal's pad light", h.ev("find('hub_mhe_anteverse_a_start').PointLight.color.G") == 0.5)
check("a mode-4 manual portal (that portal's MHE) takes the portal's design, scale and height",
      h.ev("look('hub_A4_manual')") == FR and h.ev("find('hub_A4_manual').ParticleLoop.scale.X") == 1.5 and h.ev("height('hub_A4_manual')") == 108)
check("an MHE with no hub portal (home or failsafe-bound): the default look at its sheet height",
      h.ev("look('hub_mhe_H_Cabin_Start')") == "/Game/Particles/Niagara_Portal.Niagara_Portal" and h.ev("height('hub_mhe_H_Cabin_Start')") == 128
      and h.ev("nring('hub_mhe_H_Cabin_Start')") == 0)
h = Hub(portals(P("A-3", "anteverse_a_start", FR)), DESIGNS, mhe=MHE)
check("an MHE behind a plain-look portal inherits that look and its height", h.ev("look('hub_mhe_anteverse_a_start')") == FR
      and h.ev("height('hub_mhe_anteverse_a_start')") == 108)

print("=== the pak is missing")
h = Hub(portals(P("A-3", "train_start", "Cordona Arch"), P("A-4", "train_start", "Tall Door"), P("B-1", "train_start", "Garden Ring")), DESIGNS, pak=False)
check("no Geo ring is added and our pak is never asked for (no GetAsset)", h.ev("nring('hub_A3')") == 0 and h.ev("nring('hub_A4')") == 0
      and len(list(h.ev("GETASSET").values())) == 0)
check("the pads keep their look (not hidden): the default look shows", h.ev("find('hub_A3').ParticleLoop.visible") is True
      and h.ev("look('hub_A3')") == "/Game/Particles/Niagara_Portal.Niagara_Portal")
check("one line names the missing pak, not one per pad", h.count("PortalHubLooks_P (.pak / .ucas / .utoc) is not in Content\\Paks\\~mods") == 1)
check("a game ring still works without our pak", h.ev("nring('hub_B1')") == 1)
n = h.n(); h.ex("KEYS.NUM_ONE()"); h.pump()
check("after NUMPAD 1 the line comes once more (once per spawn)", h.count("is not in Content\\Paks\\~mods", n) == 1)
h = Hub(portals(P("A-3", "train_start", "Cordona Arch")), DESIGNS, before="NO_PAK_CONTENT = true")
check("pak files there but the ring won't load: logged, no ring, look kept", h.has("could not be loaded from PortalHubLooks_P") and h.ev("nring('hub_A3')") == 0
      and h.ev("find('hub_A3').ParticleLoop.visible") is True)
h = Hub(portals(P("A-3", "train_start", "Cordona Arch")), DESIGNS, before="FAIL_COLLISION = true")
check("collision can't be switched off: the component is removed again, look kept", h.ev("nring('hub_A3')") == 0
      and h.ev("find('hub_A3').comps[1].gone") is True and h.ev("find('hub_A3').ParticleLoop.visible") is True and h.has("ring removed again"))

print("=== designs.lua is read again when the portals spawn")
h = Hub(portals(P("A-3", "train_start", "Mine")), 'return { Mine = { look = "Niagara_Portal_Friendly_Red" } }')
check("before: the design's look", h.ev("look('hub_A3')") == FR)
h.write('return { Mine = { look = "none", ring = "Round_Pri" } }')
n = h.n(); h.ex("KEYS.NUM_ONE()"); h.pump()
check("NUMPAD 1 after an edit: 'designs.lua changed' and the new design is drawn", h.has("designs.lua changed (1 design(s))", n) and h.ev("nring('hub_A3')") == 1
      and h.ev("ring('hub_A3').scale.X") == 1.8)
n = h.n(); h.ex("KEYS.NUM_ONE()"); h.pump()
check("unchanged on the next NUMPAD 1: no re-read line", not h.has("designs.lua changed", n))

print("=== client mode: this player's own designs on the host's portals")
h = Hub(portals(P("A-3", "anteverse_a_start", "Cordona Arch")), DESIGNS, before="AUTH = false")
check("a client spawns no pads of its own", h.ev("find('hub_A3')") is None)
h.ex("host_pad('A-3', 'anteverse_a_start')"); h.pump(); h.pump()
check("the host's portal in that slot gets this player's design: ring on, look hidden", h.ev("nring('hub_A3')") == 1 and h.ev("find('hub_A3').ParticleLoop.visible") is False)
check("... at the design's height", h.ev("height('hub_A3')") == 130)
h.ex("host_pad('A-4', 'train_start')"); h.pump(); h.pump()
check("... once per pad: the ring is not added twice", h.ev("nring('hub_A3')") == 1)
h = Hub(portals(P("A-3", "anteverse_a_start", "Cordona Arch")), DESIGNS, pak=False, before="AUTH = false")
h.ex("host_pad('A-3', 'anteverse_a_start')"); h.pump(); h.pump()
check("a client without the pak: the host's portal keeps its look, logged", h.ev("nring('hub_A3')") == 0
      and h.ev("find('hub_A3').ParticleLoop.visible") is True and h.has("is not in Content\\Paks\\~mods"))

print("=== no new object scans, timers or watches")
base = Hub(portals(P("A-3", "train_start", FR), P("A-4", "anteverse_a_start", FR)), DESIGNS, mhe=MHE)
des = Hub(portals(P("A-3", "train_start", "Cordona Arch"), P("A-4", "anteverse_a_start", "Big Red")), DESIGNS, mhe=MHE)
check("designs add no FindAllOf / FindFirstOf calls", base.ev("SCANS") == des.ev("SCANS") and base.ev("FINDFIRST") == des.ev("FINDFIRST"),
      (base.ev("SCANS"), des.ev("SCANS"), base.ev("FINDFIRST"), des.ev("FINDFIRST")))
check("no new delayed actions or watches", base.ev("GAME_DELAYS") == des.ev("GAME_DELAYS") and base.ev("n_notify()") == des.ev("n_notify()"))
check("no ExecuteWithDelay anywhere (game-thread delays only, CRD-032)", des.ev("ASYNC_DELAYS") == 0)
s0, s1 = base.ev("SCANS"), des.ev("SCANS")
for x in (base, des):
    for _ in range(4):
        x.ex("T = T + 1"); x.pump()
check("tracker ticks: the same scans with designs as without", base.ev("SCANS") - s0 == des.ev("SCANS") - s1, (base.ev("SCANS") - s0, des.ev("SCANS") - s1))
src = open(MAIN, encoding="utf-8").read()
block = src[src.index("-- Portal designs (CRD-044"):src.index("-- Custom worlds -------")]
check("the design code calls no FindAllOf / FindFirstOf / ExecuteWithDelay / NotifyOnNewObject",
      not any(w in block for w in ("FindAllOf", "FindFirstOf", "ExecuteWithDelay", "NotifyOnNewObject", "LoopAsync", "RegisterKeyBind")))

print("=== what the editor writes, the hub reads")
sys.path.insert(0, os.path.join(ROOT, "tools", "PortalHubConfig"))
from luaconfig import Design, DesignsFile   # noqa: E402
df = DesignsFile(os.path.join(TMP, "editor-made.lua"))
df.add(Design(name="Every Field", look="Niagara_Portal_Friendly_Cyan", ring="Oval_Ren", size=[1.5, 2.25], tint_hex="#3366FF",
              scene="TC_H_Cabin", scale=[1.2, 1.1, 1.3], height=115, mhe_height=125, hide=["sparks"]))
df.add(Design(name='Odd "name" here', look="none", ring="M_Portal_Torii"))
h = Hub(portals(P("A-3", "anteverse_a_start", "Every Field"), P("A-4", "train_start", 'Odd \\"name\\" here')), df.render(),
        mhe='{ anteverse_a_start = { 119300, 330300, 2300, 90 } }')
check("an editor-written designs.lua: every field read, nothing ignored", not h.has("ignored what can't be read") and not h.has("is not in designs.lua"),
      [l for l in h.logs() if "design" in l][:8])
check("... ring, size, tint, scene, look scale, height, hidden part all drawn",
      h.ev("nring('hub_A3')") == 1 and h.ev("ring('hub_A3').scale.X") == 1.5 and h.ev("ring('hub_A3').scale.Y") == 2.25
      and abs(h.ev("ring('hub_A3').mat.vec.PortalCenterColor2.B") - 1.0) < 1e-9 and h.ev("ring('hub_A3').mat.tex.PortalTexture").endswith("TC_H_Cabin")
      and h.ev("find('hub_A3').ParticleLoop.scale.Z") == 1.3 and h.ev("height('hub_A3')") == 115
      and list(h.ev("find('hub_A3').ParticleLoop.hidden").values()) == ["sparks"])
check("... the look stays visible under the ring (look is not none)", h.ev("find('hub_A3').ParticleLoop.visible") is True)
check("... its MHE at mheHeight", h.ev("height('hub_mhe_anteverse_a_start')") == 125)
check("a name with quotes round-trips from the editor to the hub", h.ev("nring('hub_A4')") == 1)

print("=== the shipped designs.lua and the height sheet")
shipped = open(os.path.join(HUB, "designs.lua"), "rb").read()
check("designs.lua: no BOM, LF line ends", not shipped.startswith(b"\xef\xbb\xbf") and b"\r\n" not in shipped)
h = Hub(portals(P("A-3", "train_start", "Cordona Arch"), P("A-4", "train_start", "Big Friendly Red"), P("B-1", "train_start", "Mall Door")),
        shipped.decode("utf-8"))
check("every shipped example resolves with nothing ignored", not h.has("ignored what can't be read") and not h.has("is not in designs.lua"), h.logs()[:20])
check("... and they draw (two rings, one scaled look)", h.ev("nring('hub_A3')") == 1 and h.ev("nring('hub_B1')") == 1 and h.ev("find('hub_A4').ParticleLoop.scale.X") == 1.3)
rows = {r["look"]: float(r["LuciDin's height cm"]) for r in csv.DictReader(open(os.path.join(ROOT, "docs", "portal-heights.csv"), encoding="utf-8"))}
import re
t = block[block.index("Designs.HEIGHTS = {"):block.index("}", block.index("Designs.HEIGHTS = {"))]   # Designs is a local of main.lua: read the source
lua_h = {k: float(v) for k, v in re.findall(r"(\w+) = (\d+)", t)}
check("the hub's height table is LuciDin's sheet (all 32 looks, same cm)", {k: float(v) for k, v in lua_h.items()} == rows,
      sorted(set(rows.items()) ^ set((k, float(v)) for k, v in lua_h.items())))

print("\n%d/%d passed" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
