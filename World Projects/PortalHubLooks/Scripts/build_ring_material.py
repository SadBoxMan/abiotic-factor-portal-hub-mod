# Unreal Editor (headless) script: build Portal Hub's own "Geo" portal materials (CRD-043). CC0, our own graph.
#
# Run (the editor must not have this project open):
#   UnrealEditor-Cmd.exe "<this folder>\..\AbioticFactor.uproject" -run=PythonScript -Script="<this file>"
#       -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout
# Env: PH_OUT = report file (default: build_ring_material.txt next to this script); PH_HDR = the dummy cube map's .hdr
# (default: dummy_cube.hdr next to this script; written by this script if missing).
#
# What it makes (running it again rebuilds the master and the instances from scratch, keeps the label and the dummy):
#   /Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Geo   the master material (Masked, Unlit, Two Sided; Niagara sprite and mesh usage)
#   /Game/Mods/PortalHubLooks/Geo/MI_Geo<Type>_<Shape>         24 instances: 4 types (Con, Col, Ren, Pri; see STYLES) x
#                                                              6 shapes (Arch, Gothic, Square, Door, Round, Oval)
#   /Game/Mods/PortalHubLooks/PAL_PortalHubLooks               Primary Asset Label: chunk 120, labels its own folder only
#                                                              (Apply Recursively off, so referenced game paths stay out of the chunk)
#   /Game/Particles/RenderTargets/TC_Portal_Warehouse          a DUMMY cube map at the game's path (a tiny gradient of our own):
#                                                              the default scene. It cooks into chunk 0, which is never installed, so
#                                                              in game the reference finds the game's real Mall cube map.
# The first version's material (M_PortalHubLooks_Arch, round arch only) is left as it is: removing it is LuciDin's call.
#
# Modelled on the game's Night Realm arch (Masked, Unlit, PortalEdge (5, 0.771, 0), DistortionEdge (10, 0.924, 0), NoiseScale 1.863,
# NoiseScale2 2.818, PortalTexture = TC_Portal_Warehouse), but every part is worked out from the SURFACE, not the view direction:
#   * the shape is a distance field in real centimetres: the surface's size per UV is read from the pixel derivatives of the
#     (camera-relative) world position, so a tall, narrow arch keeps a round top round; any scale, any mesh;
#   * the swirl is noise in polar coordinates around the shape's centre, turning clockwise (seen from the front) with time; the
#     front is the side facing out from the pad on the lab's square C (FlipFront = 1: the plane's back side; LuciDin, 15 Nov);
#   * the back face is a true backside (TrueBack = 1: mirror image, swirl turning the other way, as seen from behind), or reads
#     the same as the front (TrueBack = 0);
#   * the scene is the cube map looked up with a direction from the surface plus an optional, side-aware parallax shift.
# LuciDin's shapes (15 Nov): Arched Door, Gothic Arch (pointed top), Square (1 m x 1 m), Door (first 2 m x 0.75 m, then 3 m tall x 1.75 m wide), Round (like a
# default portal), Oval (like a Friendly portal); each in four types (LuciDin, 15 Nov: Conchoidal, Colloform, Reniform, Prismatic; see STYLES). The sizes come from the mesh
# (the lab's mesh-ring scale; the lab sets each one's starting size); the material only takes the shape and its proportions.
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
MAT_NAME = "M_PortalHubLooks_Geo"
GEO_DIR = BASE + "/Geo"
PAL_NAME = "PAL_PortalHubLooks"
CHUNK = 120
CUBE_DIR = "/Game/Particles/RenderTargets"
CUBE_NAME = "TC_Portal_Warehouse"

eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary

# ---- parameters (Custom node input, parameter name, default) ----------------------------------------------------------------
# Lengths are in centimetres (the surface's own size, read in the shader).
SCALARS = [
    ("Shape",      "Shape",           0.0),    # 0 arched door, 1 gothic (pointed) arch, 2 rectangle (square, door), 3 round, 4 oval
    ("Pointed",    "Pointed",         1.0),    # gothic only: 0 = round top, 1 = equilateral pointed arch
    ("TrueBack",   "TrueBack",        1.0),    # 1 = the back face is a true backside (mirror image), 0 = reads like the front
    ("FlipFront",  "FlipFront",       1.0),    # 1 = the portal's front is the plane's BACK side: on the lab's "square C" plane that is
                                               # the side facing out from the pad (LuciDin, 15 Nov, at Dunkel Forest's MHE); 0 = plane front
    ("EdgeWidth",  "EdgeWidth",       6.0),    # width of the glowing edge band, cm
    ("EdgePower",  "EdgePower",       2.0),    # how fast the edge glow fades inwards
    ("EdgeWobble", "EdgeWobble",      3.0),    # how much the noise frays the outline, cm (the shape is inset by this)
    ("EdgeFlicker","EdgeFlicker",     0.5),    # 0 = PortalEdge only, 1 = flickers towards DistortionEdge
    ("NoiseScale", "NoiseScale",      1.8632), # swirl noise size around the ring (game arch value)
    ("NoiseScale2","NoiseScale2",     2.8175), # swirl noise size from centre to edge (game arch value)
    ("SwirlSpeed", "SwirlSpeed",      0.35),   # radians per second, clockwise seen from the front (negative = anticlockwise)
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
    ("Center",     "PortalCenterColor",  (0.01, 0.0, 0.02, 1.0)),     # dark part of the swirl
    ("Center2",    "PortalCenterColor2", (0.5, 0.08, 0.0, 1.0)),      # bright part of the swirl
    ("Edge",       "PortalEdge",         (5.0, 0.771312, 0.0, 1.0)),  # edge glow (game arch value)
    ("DistEdge",   "DistortionEdge",     (10.0, 0.92422, 0.0, 1.0)),  # edge flicker colour (game arch value)
    ("SceneTint",  "SceneTint",          (1.0, 1.0, 1.0, 1.0)),       # scene x this
]
SHAPES = [("Arch", 0.0), ("Gothic", 1.0), ("Square", 2.0), ("Door", 2.0), ("Round", 3.0), ("Oval", 4.0)]
# Four types (LuciDin, 15 Nov), from opaque swirl to clear window:
#   Con  Conchoidal  swirl, opaque: no scene (as the Friendly portals show none)
#   Col  Colloform   swirl over a faint scene (the first "Swirl" style)
#   Ren  Reniform    window: clearer scene, the swirl still ripples it (the first "Window" style)
#   Pri  Prismatic   window: no swirl, no ripple, the clearest scene
STYLES = {
    "Con": {"SceneMix": 0.0},
    "Col": {},
    "Ren": {"SceneMix": 1.0, "SwirlOverScene": 0.0, "DistortMultiply": 0.03, "DistortDistance": 0.5},
    "Pri": {"SceneMix": 1.0, "SwirlOverScene": 0.0, "DistortMultiply": 0.0, "DistortDistance": 0.0},
}

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
float t = Time;
/* the surface's size in cm per whole UV range, from pixel derivatives of the camera-relative position (exact on a flat face) */
float3 P = WPos;
float2 duvx = ddx(UV); float2 duvy = ddy(UV);
float3 dpx = ddx(P); float3 dpy = ddy(P);
float det = duvx.x * duvy.y - duvx.y * duvy.x;
float W = 100.0; float H = 100.0;
if (abs(det) > 1e-12) {
    W = length((dpx * duvy.y - dpy * duvx.y) / det);
    H = length((dpy * duvx.x - dpx * duvy.x) / det);
}
W = max(W, 1.0); H = max(H, 1.0);
/* back face: true backside (as seen from behind) or the front's reading */
float side = Side < 0.0 ? -1.0 : 1.0;
float fx = (TrueBack > 0.5 ? 1.0 : side) * (FlipFront > 0.5 ? -1.0 : 1.0);   /* FlipFront: mirror, so the plane's back side reads as the front */
float x = (UV.x - 0.5) * W * fx;      /* cm from the centre line, + right */
float y = UV.y * H;                    /* cm from the top */
/* shape: a distance in cm, negative inside */
float inset = max(EdgeWobble, 0.0) + 1.0;
float hw = max(W * 0.5 - inset, 1.0);
float top = inset; float bot = H - inset;
float hh = max((bot - top) * 0.5, 1.0);
float cyMid = H * 0.5;
float2 q = float2(abs(x), y);
int s = (int)round(Shape);
float d;
float pw = hw; float ph = hh;
if (s == 0 || s == 1) {
    float R = hw;
    float o = (s == 1) ? saturate(Pointed) * R : 0.0;
    float apex = sqrt(R * R + 2.0 * R * o);
    float cy = top + apex;
    /* the top's circle is NOT cut at the springing line (cutting both parts there left a zero-distance seam inside: a glowing,
       frayed line across the arch, in game 15 Nov); it reaches into the box, cut only at the foot */
    float dC = max(length(float2(q.x + o, q.y - cy)) - (R + o), q.y - bot);
    float dB = max(q.x - hw, max(cy - q.y, q.y - bot));
    d = min(dC, dB);
} else if (s == 2) {
    d = max(q.x - hw, max(top - q.y, q.y - bot));
} else if (s == 3) {
    float r0 = min(hw, hh);
    d = length(float2(q.x, q.y - cyMid)) - r0;
    pw = r0; ph = r0;
} else {
    d = (length(float2(q.x / hw, (q.y - cyMid) / hh)) - 1.0) * min(hw, hh);
}
/* swirl: noise on circles around the centre, turning clockwise seen from the front (y grows downwards) */
float2 pn = float2(x / pw, (y - cyMid) / ph);
float r = length(pn);
float a = atan2(pn.y, pn.x) - t * SwirlSpeed + r * SwirlTwist;
float3 sp = float3(cos(a) * NoiseScale, sin(a) * NoiseScale, r * NoiseScale2 - t * Inflow);
float n = nz.fbm(sp);
float n2 = nz.fbm(sp * 1.7 + float3(3.1, 1.3, t * 0.37));
d += (n2 - 0.5) * 2.0 * EdgeWobble;
float inside = d < 0.0 ? 1.0 : 0.0;
float depth = saturate(-d / max(EdgeWidth, 0.1));
/* scene: direction from the surface (longer side = 1), shifted by the view in the face's own frame */
float L = max(W, H);
float3 c = CamT;
c.x *= fx;
c.z = max(abs(c.z), 0.2);
float3 dir = float3(x / L * SceneZoom, (cyMid - y) / L * SceneZoom, 1.0);
dir.xy += Parallax * (-c.xy / c.z);
dir.xy += (n - 0.5) * DistMul * (1.0 + r * DistDist);
dir = normalize(dir);
float syw = sin(SceneYaw * 0.0174533);
float cyw = cos(SceneYaw * 0.0174533);
float3 cd = float3(dir.z, dir.x, dir.y);            /* cube space: X forward, Y right, Z up */
cd.xy = float2(cd.x * cyw - cd.y * syw, cd.x * syw + cd.y * cyw);
float3 scene = PortalTex.SampleLevel(PortalTexSampler, cd, SceneBlur).rgb * SceneBright * SceneTint.rgb;
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
    import math

    def rgbe(r, g, b):
        m = max(r, g, b)
        if m < 1e-32:
            return bytes((0, 0, 0, 0))
        e = math.frexp(m)[1]
        s = 256.0 / (2.0 ** e)
        return bytes((int(r * s), int(g * s), int(b * s), e + 128))
    rows = []
    for j in range(h):
        k = j / (h - 1.0)                     # 0 top, 1 bottom
        rows.append(b"".join(rgbe(0.9 * (1 - k) + 0.05, 0.35 * (1 - k) + 0.02, 0.1 + 0.25 * k) for i in range(w)))
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

# ---- master material (rebuilt from scratch; instances first, they depend on it) --------------------------------------------------
for p in (eal.list_assets(GEO_DIR, recursive=True, include_folder=False) if eal.does_directory_exist(GEO_DIR) else []):
    eal.delete_asset(p.split(".")[0])   # every instance in the Geo folder (also the first MI_Geo<Shape>_<Swirl|Window> names)
mat_path = MAT_DIR + "/" + MAT_NAME
if eal.does_asset_exist(mat_path):
    log("old master deleted:", eal.delete_asset(mat_path))
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
custom.set_editor_property("description", "PortalHubLooks Geo (surface-locked)")
names = ["UV", "Time", "Side", "CamT", "WPos", "PortalTex"] + [s[0] for s in SCALARS] + [v[0] for v in VECTORS]
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


y = -1800
wire(node(unreal.MaterialExpressionTextureCoordinate, -900, y), "UV"); y += 120
wire(node(unreal.MaterialExpressionTime, -900, y), "Time"); y += 120
wire(node(unreal.MaterialExpressionTwoSidedSign, -900, y), "Side"); y += 120
camv = node(unreal.MaterialExpressionCameraVectorWS, -1200, y)
tr = node(unreal.MaterialExpressionTransform, -900, y)
tr.set_editor_property("transform_source_type", unreal.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD)
tr.set_editor_property("transform_type", unreal.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
log("camera -> transform:", mel.connect_material_expressions(camv, "", tr, ""))
wire(tr, "CamT"); y += 160
wp = node(unreal.MaterialExpressionWorldPosition, -900, y)
try:
    wp.set_editor_property("world_position_shader_offset", unreal.WorldPositionIncludedOffsets.WPT_CAMERA_RELATIVE)
    log("world position: camera relative")
except Exception as ex:   # older enum names: fall back to the default (absolute) and say so
    log("world position: camera-relative option not set (" + str(ex) + "); absolute world position used")
wire(wp, "WPos"); y += 160
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

# ---- 24 instances: type x shape -------------------------------------------------------------------------------------------------
made = []
for shape, sval in SHAPES:
    for style, over in STYLES.items():
        name = "MI_Geo" + style + "_" + shape
        mi = at.create_asset(name, GEO_DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, mat)
        mel.set_material_instance_scalar_parameter_value(mi, "Shape", sval)
        for k, v in over.items():
            mel.set_material_instance_scalar_parameter_value(mi, k, v)
        mel.update_material_instance(mi)
        eal.save_asset(GEO_DIR + "/" + name, only_if_is_dirty=False)
        made.append(name + " (Shape " + str(sval) + (", " + ", ".join("%s %s" % kv for kv in over.items()) if over else "") + ")")
log("instances:", len(made))
for m in made:
    log("  ", m)

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
