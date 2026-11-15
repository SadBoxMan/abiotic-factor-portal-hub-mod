# Unreal Editor (headless) script: build Portal Hub's own ring material, M_PortalHubLooks_Arch (CRD-043). CC0, our own graph.
#
# Run (the editor must not have this project open):
#   UnrealEditor-Cmd.exe "<this folder>\..\AbioticFactor.uproject" -run=PythonScript -Script="<this file>"
#       -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout
# Env: PH_OUT = report file (default: build_ring_material.txt next to this script); PH_HDR = the dummy cube map's .hdr
# (default: dummy_cube.hdr next to this script; written by this script if missing).
#
# What it makes (running it again rebuilds the material from scratch, keeps the label and the dummy):
#   /Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Arch  the material (Masked, Unlit, Two Sided; Niagara sprite and mesh usage)
#   /Game/Mods/PortalHubLooks/PAL_PortalHubLooks               Primary Asset Label: chunk 120, labels its own folder only
#                                                              (Apply Recursively off, so referenced game paths stay out of the chunk)
#   /Game/Particles/RenderTargets/TC_Portal_Warehouse          a DUMMY cube map at the game's path (a tiny gradient of our own):
#                                                              the material's default scene. It cooks into chunk 0, which is never
#                                                              installed, so in game the reference finds the game's real Mall cube map.
#
# Modelled on the game's Night Realm arch (M_Portal_Arch: Masked, Unlit, PortalEdge (5, 0.771, 0), DistortionEdge (10, 0.924, 0),
# NoiseScale 1.863, NoiseScale2 2.818, Radius (S) 0.236, PortalTexture = TC_Portal_Warehouse, arch-shaped mask), but every part is
# worked out from the SURFACE (UV), not from the view direction:
#   * the arch shape is a distance field in UV (no mask texture), so it can be resized and rounded live;
#   * the swirl is noise in polar UV coordinates turning with time (no noise texture), so it is fixed to the surface;
#   * on the back face (TwoSidedSign < 0) the UV x is mirrored, so one face reads the same from both sides;
#   * the scene is the cube map looked up with a direction built from UV plus an optional, side-aware parallax shift.
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("PH_OUT") or os.path.join(HERE, "build_ring_material.txt")
HDR = os.environ.get("PH_HDR") or os.path.join(HERE, "dummy_cube.hdr")
open(OUT, "w").close()


def log(*a):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(" ".join(str(x) for x in a) + "\n")


BASE = "/Game/Mods/PortalHubLooks"
MAT_DIR = BASE + "/Materials"
MAT_NAME = "M_PortalHubLooks_Arch"
PAL_NAME = "PAL_PortalHubLooks"
CHUNK = 120
CUBE_DIR = "/Game/Particles/RenderTargets"
CUBE_NAME = "TC_Portal_Warehouse"

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary

# ---- parameters (name, default) -------------------------------------------------------------------------------------------------
# Input names in the Custom node (no spaces) map to these parameter names.
SCALARS = [
    # input        parameter          default  what it does
    ("Radius",     "Radius (S)",      0.30),   # arch half width in UV (0..0.5); the lab's M / N "ring size"
    ("ArchHeight", "ArchHeight",      0.92),   # arch height in UV, bottom to top of the round
    ("ArchBottom", "ArchBottom",      0.98),   # UV v of the arch's foot (v = 0 top, 1 bottom)
    ("Round",      "Round",           0.0),    # 0 = arch, 1 = oval (blends between)
    ("EdgeWidth",  "EdgeWidth",       0.05),   # width of the glowing edge band, UV
    ("EdgePower",  "EdgePower",       2.0),    # how fast the edge glow fades inwards
    ("EdgeWobble", "EdgeWobble",      0.03),   # how much the noise frays the outline, UV
    ("EdgeFlicker","EdgeFlicker",     0.5),    # 0 = PortalEdge only, 1 = flickers towards DistortionEdge
    ("NoiseScale", "NoiseScale",      1.8632), # swirl noise size around the ring (game arch value)
    ("NoiseScale2","NoiseScale2",     2.8175), # swirl noise size from centre to edge (game arch value)
    ("SwirlSpeed", "SwirlSpeed",      0.35),   # turns of the swirl per second, roughly (radians / s)
    ("SwirlTwist", "SwirlTwist",      2.5),    # how much the swirl spirals (radians from centre to edge)
    ("Inflow",     "InflowSpeed",     0.4),    # how fast the noise flows towards the centre
    ("SwirlLow",   "SwirlLow",        0.35),   # noise level where PortalCenterColor2 starts
    ("SwirlHigh",  "SwirlHigh",       0.75),   # noise level where it is full
    ("SceneMix",   "SceneMix",        0.55),   # 0 = swirl only, 1 = scene only
    ("SwirlOver",  "SwirlOverScene",  0.7),    # how much the bright swirl covers the scene
    ("SceneZoom",  "SceneZoom",       0.8),    # field of view of the scene (bigger = wider)
    ("Parallax",   "SceneParallax",   0.35),   # 0 = flat picture, more = the scene shifts with the viewing angle (both sides)
    ("SceneYaw",   "SceneYaw",        0.0),    # turns the scene inside the cube map, degrees
    ("SceneBlur",  "SceneBlur",       0.0),    # cube map mip level (0 = sharp)
    ("SceneBright","SceneBright",     1.0),    # scene brightness
    ("DistMul",    "DistortMultiply", 0.1),    # how much the swirl bends the scene (game arch value)
    ("DistDist",   "DistortDistance", 0.8928), # extra bending towards the edge (game arch value)
    ("Brightness", "Brightness",      1.0),    # everything x this
]
VECTORS = [
    ("Center",     "PortalCenterColor",  (0.01, 0.0, 0.02, 1.0)),   # dark part of the swirl
    ("Center2",    "PortalCenterColor2", (0.5, 0.08, 0.0, 1.0)),    # bright part of the swirl
    ("Edge",       "PortalEdge",         (5.0, 0.771312, 0.0, 1.0)),  # edge glow (game arch value)
    ("DistEdge",   "DistortionEdge",     (10.0, 0.92422, 0.0, 1.0)),  # edge flicker colour (game arch value)
]

HLSL = r"""
struct PHLNoise {
    float h(float3 p) { p = frac(p * 0.3183099 + 0.1); p *= 17.0; return frac(p.x * p.y * p.z * (p.x + p.y + p.z)); }
    float n3(float3 x) {
        float3 i = floor(x); float3 f = frac(x); f = f * f * (3.0 - 2.0 * f);
        return lerp(lerp(lerp(h(i + float3(0, 0, 0)), h(i + float3(1, 0, 0)), f.x),
                         lerp(h(i + float3(0, 1, 0)), h(i + float3(1, 1, 0)), f.x), f.y),
                    lerp(lerp(h(i + float3(0, 0, 1)), h(i + float3(1, 0, 1)), f.x),
                         lerp(h(i + float3(0, 1, 1)), h(i + float3(1, 1, 1)), f.x), f.y), f.z);
    }
    float fbm(float3 p) { return (0.5 * n3(p) + 0.25 * n3(p * 2.03 + 7.1) + 0.125 * n3(p * 4.01 + 3.7)) / 0.875; }
};
PHLNoise nz;
float side = Side < 0.0 ? -1.0 : 1.0;
float x = (UV.x - 0.5) * side;          /* mirrored on the back face: one face reads the same from both sides */
float y = UV.y;                         /* 0 top, 1 bottom */
float t = Time;
/* shape: arch (box + half circle) blended with an oval, as a distance in UV (negative inside) */
float R = max(Radius, 0.01);
float vt = ArchBottom - ArchHeight;
float cy = vt + R;
float2 q = float2(abs(x), y);
float dC = length(q - float2(0.0, cy)) - R;
float dB = max(q.x - R, max(cy - q.y, q.y - ArchBottom));
float dArch = min(dC, dB);
float midY = (vt + ArchBottom) * 0.5;
float hy = max(ArchHeight * 0.5, 0.01);
float2 pn = float2(x / R, (y - midY) / hy);
float dEll = (length(pn) - 1.0) * min(R, hy);
float d = lerp(dArch, dEll, saturate(Round));
/* swirl: noise on circles around the centre, turning with time, so it is fixed to the surface and seamless */
float r = length(pn);
float a = atan2(pn.y, pn.x) + t * SwirlSpeed + r * SwirlTwist;
float3 sp = float3(cos(a) * NoiseScale, sin(a) * NoiseScale, r * NoiseScale2 - t * Inflow);
float n = nz.fbm(sp);
float n2 = nz.fbm(sp * 1.7 + float3(3.1, 1.3, t * 0.37));
d += (n2 - 0.5) * EdgeWobble;
float inside = d < 0.0 ? 1.0 : 0.0;
float depth = saturate(-d / max(EdgeWidth, 0.001));
/* scene: direction from UV, shifted by the view in the face's own frame (x mirrored, normal towards the viewer on both sides) */
float3 c = CamT;
c.x *= side;
c.z = max(abs(c.z), 0.2);
float3 dir = float3(x * SceneZoom, (0.5 - y) * SceneZoom, 1.0);
dir.xy += Parallax * (-c.xy / c.z);
dir.xy += (n - 0.5) * DistMul * (1.0 + r * DistDist);
dir = normalize(dir);
float sy = sin(SceneYaw * 0.0174533);
float cyw = cos(SceneYaw * 0.0174533);
float3 cd = float3(dir.z, dir.x, dir.y);            /* cube space: X forward, Y right, Z up */
cd.xy = float2(cd.x * cyw - cd.y * sy, cd.x * sy + cd.y * cyw);
float3 scene = PortalTex.SampleLevel(PortalTexSampler, cd, SceneBlur).rgb * SceneBright;
/* colour: swirl over the scene, glowing edge */
float sw = smoothstep(SwirlLow, SwirlHigh, n);
float3 swirl = lerp(Center.rgb, Center2.rgb, sw);
float3 col = lerp(swirl, scene, saturate(SceneMix * (1.0 - sw * SwirlOver)));
float edge = pow(1.0 - depth, max(EdgePower, 0.1));
float3 edgeCol = lerp(Edge.rgb, DistEdge.rgb, saturate(n2 * EdgeFlicker));
col = col * (1.0 - edge) + edgeCol * edge;
return float4(col * Brightness, inside);
"""


def lc(v):
    return unreal.LinearColor(v[0], v[1], v[2], v[3])


def make_hdr(path, w=64, h=32):
    # a tiny lat-long Radiance .hdr (RGBE, uncompressed scanlines): dark violet below, warm glow above. Our own, CC0.
    def rgbe(r, g, b):
        import math
        m = max(r, g, b)
        if m < 1e-32:
            return bytes((0, 0, 0, 0))
        e = math.frexp(m)[1]
        s = 256.0 / (2.0 ** e)
        return bytes((int(r * s), int(g * s), int(b * s), e + 128))
    rows = []
    for j in range(h):
        k = j / (h - 1.0)                     # 0 top, 1 bottom
        row = b"".join(rgbe(0.9 * (1 - k) + 0.05, 0.35 * (1 - k) + 0.02, 0.1 + 0.25 * k) for i in range(w))
        rows.append(row)
    head = b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n" % (h, w)
    with open(path, "wb") as f:
        f.write(head + b"".join(rows))


# ---- dummy cube map at the game's path ------------------------------------------------------------------------------------------
cube_path = CUBE_DIR + "/" + CUBE_NAME
cube = eal.load_asset(cube_path) if eal.does_asset_exist(cube_path) else None
if cube is None:
    if not os.path.exists(HDR):
        make_hdr(HDR)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", HDR)
    task.set_editor_property("destination_path", CUBE_DIR)
    task.set_editor_property("destination_name", CUBE_NAME)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    at.import_asset_tasks([task])
    cube = eal.load_asset(cube_path)
log("dummy cube:", cube_path, type(cube).__name__ if cube is not None else "MISSING")
if not isinstance(cube, unreal.TextureCube):
    log("STOP: the dummy is not a TextureCube")
    raise SystemExit(1)

# ---- material (rebuilt from scratch) ------------------------------------------------------------------------------------------------
mat_path = MAT_DIR + "/" + MAT_NAME
if eal.does_asset_exist(mat_path):
    log("old material deleted:", eal.delete_asset(mat_path))
mat = at.create_asset(MAT_NAME, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
log("material created:", mat is not None)
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("two_sided", True)
mat.set_editor_property("opacity_mask_clip_value", 0.3333)
mat.set_editor_property("used_with_niagara_sprites", True)
mat.set_editor_property("used_with_niagara_mesh_particles", True)


def node(cls, x, y):
    e = mel.create_material_expression(mat, cls, x, y)
    if e is None:
        raise RuntimeError("could not create " + cls.__name__)
    return e


custom = node(unreal.MaterialExpressionCustom, 0, 0)
custom.set_editor_property("code", HLSL)
custom.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT4)
custom.set_editor_property("description", "PortalHubLooks arch (surface-locked)")
names = ["UV", "Time", "Side", "CamT", "PortalTex"] + [s[0] for s in SCALARS] + [v[0] for v in VECTORS]
inputs = []
for nm in names:
    ci = unreal.CustomInput()
    ci.set_editor_property("input_name", nm)
    inputs.append(ci)
custom.set_editor_property("inputs", inputs)


def wire(src, inp):
    ok = mel.connect_material_expressions(src, "", custom, inp)
    if not ok:
        log("  connect FAILED:", inp)
    return ok


y = -1600
wire(node(unreal.MaterialExpressionTextureCoordinate, -900, y), "UV"); y += 120
wire(node(unreal.MaterialExpressionTime, -900, y), "Time"); y += 120
wire(node(unreal.MaterialExpressionTwoSidedSign, -900, y), "Side"); y += 120
camv = node(unreal.MaterialExpressionCameraVectorWS, -1200, y)
tr = node(unreal.MaterialExpressionTransform, -900, y)
tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
log("camera -> transform:", mel.connect_material_expressions(camv, "", tr, ""))
wire(tr, "CamT"); y += 160
tex = node(unreal.MaterialExpressionTextureObjectParameter, -900, y)
tex.set_editor_property("parameter_name", "PortalTexture")
tex.set_editor_property("texture", cube)
tex.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
wire(tex, "PortalTex"); y += 200
for inp, pname, val in SCALARS:
    p = node(unreal.MaterialExpressionScalarParameter, -900, y)
    p.set_editor_property("parameter_name", pname)
    p.set_editor_property("default_value", val)
    wire(p, inp); y += 90
for inp, pname, val in VECTORS:
    p = node(unreal.MaterialExpressionVectorParameter, -900, y)
    p.set_editor_property("parameter_name", pname)
    p.set_editor_property("default_value", lc(val))
    wire(p, inp); y += 160

rgb = node(unreal.MaterialExpressionComponentMask, 400, -60)
for ch, on in (("r", True), ("g", True), ("b", True), ("a", False)):
    rgb.set_editor_property(ch, on)
alpha = node(unreal.MaterialExpressionComponentMask, 400, 80)
for ch, on in (("r", False), ("g", False), ("b", False), ("a", True)):
    alpha.set_editor_property(ch, on)
log("custom -> rgb:", mel.connect_material_expressions(custom, "", rgb, ""))
log("custom -> alpha:", mel.connect_material_expressions(custom, "", alpha, ""))
log("emissive:", mel.connect_material_property(rgb, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR))
log("opacity mask:", mel.connect_material_property(alpha, "", unreal.MaterialProperty.MP_OPACITY_MASK))
mel.recompile_material(mat)
log("saved material:", eal.save_asset(mat_path, only_if_is_dirty=False))

# ---- primary asset label: chunk 120, own folder only --------------------------------------------------------------------------------
pal_path = BASE + "/" + PAL_NAME
pal = eal.load_asset(pal_path) if eal.does_asset_exist(pal_path) else None
if pal is None:
    fac = unreal.DataAssetFactory()
    fac.set_editor_property("data_asset_class", unreal.PrimaryAssetLabel)
    pal = at.create_asset(PAL_NAME, BASE, unreal.PrimaryAssetLabel, fac)
rules = pal.get_editor_property("rules")
rules.set_editor_property("chunk_id", CHUNK)
rules.set_editor_property("priority", 1)
rules.set_editor_property("apply_recursively", False)
rules.set_editor_property("cook_rule", unreal.PrimaryAssetCookRule.ALWAYS_COOK)
pal.set_editor_property("rules", rules)
pal.set_editor_property("label_assets_in_my_directory", True)
pal.set_editor_property("is_runtime_label", True)
log("saved label:", eal.save_asset(pal_path, only_if_is_dirty=False))

# ---- report ------------------------------------------------------------------------------------------------------------------------
m = eal.load_asset(mat_path)
log("material:", mat_path)
for prop in ("blend_mode", "shading_model", "two_sided", "opacity_mask_clip_value", "used_with_niagara_sprites",
             "used_with_niagara_mesh_particles"):
    log("  ", prop, "=", m.get_editor_property(prop))
log("  scalar parameters:", [str(n) for n in mel.get_scalar_parameter_names(m)])
log("  vector parameters:", [str(n) for n in mel.get_vector_parameter_names(m)])
log("  texture parameters:", [str(n) for n in mel.get_texture_parameter_names(m)])
log("  expressions:", mel.get_num_material_expressions(m))
r2 = eal.load_asset(pal_path).get_editor_property("rules")
log("label:", pal_path, "chunk", r2.get_editor_property("chunk_id"), "recursive", r2.get_editor_property("apply_recursively"),
    "cook", r2.get_editor_property("cook_rule"))
log("assets:", eal.list_assets("/Game", recursive=True, include_folder=False))
log("DONE")
