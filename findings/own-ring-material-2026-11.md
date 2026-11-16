# Our own portal material: the "Geo" portals (CRD-043, 15 November 2026)

Answers LuciDin's requests "let's do our own version to fix the rotation bug" (14-15 Nov, via CRD-042) and "We need the data from the
'Custom Portal' research to make a lab that I can use to create these custom looks in-game" (15 Nov). Follows
[`portal-scale-facing-tint-2026-11.md`](portal-scale-facing-tint-2026-11.md) (CRD-042: the mesh ring) and
[`portal-looks-deep-dive-2026-11.md`](portal-looks-deep-dive-2026-11.md) (CRD-039).

Everything here is our own work (CC0): our own material graph, cooked from our own UE 5.4 project into our own `~mods` pak. The game's
files were only read (the cooked materials' parameter names and imports, through UAssetGUI); the game's textures are referenced by
path, never copied. Tested in game on the beta install (v1.5.0) on 15 November with LuciDin; nothing written to a save, no crash, no
`Ref was not function`.

## 1. Short answers

| Question | Answer |
|---|---|
| Can we cook our own portal material and use it in game? | **Yes.** `PortalHubLooks_P` (chunk 120) loads beside the game's content; the lab puts its materials on the mesh ring. |
| Two-sided? | **Yes**, one face: TwoSided on, and everything worked out from the surface, so no back-face mesh is needed. The back is a **true backside** (mirror image, swirl turning the other way, the other half of the scene), as the game's Door. |
| Swirl locked to the surface? | **Yes.** Noise in polar coordinates around the shape's centre, turning **clockwise** seen from the front (the side facing out from the pad). The game's Night Realm arch swirls with the view instead (CRD-042). |
| Tintable? | **Yes**, through `PortalCenterColor`, `PortalCenterColor2`, `PortalEdge` and `DistortionEdge` (the lab's grey x RGB scheme). Adding `DistortionEdge` to the lab's tint also made **the game's Night Realm fringe** follow the colour (it stayed gold before). |
| Scene changeable? | **Yes**, any cube map in `PortalTexture`, seen **as through a window into a sphere** behind the portal (the idea of the game's Door window, our own maths): moving past the portal shows other parts of the scene with depth; from behind, the other half. |
| Shapes and sizes? | **6 shapes x 4 types = 24 "Geo" portals** (section 3). The shape is worked out in real centimetres from the mesh's own size, so any scale keeps its proportions. |
| One file instead of .pak / .ucas / .utoc? | **No** (LuciDin's question): the game loads assets only from IoStore containers (`.utoc` / `.ucas`), mounted through a same-named `.pak` stub (339 bytes). Ship the three as one unit. One pak set can hold any amount of our content if it is cooked from one project (section 5). |
| Ships in 1.0? | **Yes, LuciDin, 15 Nov: "Ship in 1.0"** (the release plan had our own paks in 2.0). Needs a hub build first (section 7). |

## 2. The project and the pak

| What | Where / value |
|---|---|
| Project | `World Projects/PortalHubLooks/AbioticFactor.uproject` (UE 5.4.4, Blueprint-only; the name must stay `AbioticFactor` so the pak mounts under the game's content) |
| Build script | `World Projects/PortalHubLooks/Scripts/build_ring_material.py` (headless editor; makes everything below; README in the project folder) |
| Master material | `/Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Geo`: Masked, Unlit, Two Sided, clip 0.3333; usage static mesh (always), Niagara sprites, Niagara mesh particles; one Custom (HLSL) node fed by 27 scalar, 5 vector and 1 texture parameters |
| Instances | `/Game/Mods/PortalHubLooks/Geo/MI_Geo<Shape>_<Type>` (24; names shape first, LuciDin: "Arch_Col") |
| Chunk label | `PAL_PortalHubLooks`: chunk **120**, labels its own folder, **Apply Recursively off** |
| Container id | `bcced51e259b6887` (CityHash64 of `pakchunk120-windows`; no clash with 90-94) |
| Pak | `PortalHubLooks_P.pak/.ucas/.utoc`, 26 files, all `/Game/Mods/PortalHubLooks/...`; copies in `World Projects/Builds/` (git-ignored, not committed) |
| Dummy | `/Game/Particles/RenderTargets/TC_Portal_Warehouse` in the project: a tiny gradient cube map of our own at the game's path, the default scene while cooking. Apply Recursively off sends it to chunk 0 (never installed), so in game the reference finds the game's real Mall cube map |

**Cook and package** (about 20 s): rebuild the assets with the script (headless, editor closed), then
`RunUAT BuildCookRun -project=... -platform=Win64 -clientconfig=Shipping -cook -stage -pak -iostore -compressed -nocompileeditor -nocompile`;
take only `Saved/StagedBuilds/Windows/AbioticFactor/Content/Paks/pakchunk120-Windows.*`, rename to `PortalHubLooks_P.*`, check with
`tools/dev/read_utoc.py` (only `Mods/PortalHubLooks/...`), install into `Content/Paks/~mods/` **with the game closed** (a mounted pak
cannot be swapped safely). Never `pakchunk0-*` or `global.*`.

**Loading in game:** our assets are not in the game's asset registry, so UE4SS's `LoadAsset` silently loads nothing (first run: "not
found"). `AssetRegistryHelpers:GetAsset({ PackageName, AssetName })` loads them by name (the hub already does this for World A-D's
loaders). The lab logs `LoadAsset`'s result, then uses `GetAsset` (in game: "loaded with GetAsset").

## 3. The Geo portals

**Shapes** (`Shape`): arched door (0), gothic arch (1, `Pointed` 0..1, 1 = equilateral), rectangle (2: Square and Door), round (3),
oval (4). The surface's size is read in the shader from the pixel derivatives of the camera-relative world position (exact on a flat
face), so the shape knows its real width and height: a 1.75 x 3 m door keeps a round top round, and M / N rescale without distortion.
Starting sizes (the lab's mesh-ring scale, in metres = the engine Plane's scale):

| Shape | Width x height | Note |
|---|---|---|
| Arch, Gothic | 1.0 x 2.0 | |
| Square | 1.0 x 1.0 | LuciDin |
| Door | 1.75 x 3.0 | LuciDin (first 0.75 x 2) |
| Round | 1.8 x 1.8 | first guess at a default portal; not resized in the run |
| Oval | 1.4 x 2.0 | first guess at a Friendly portal; not resized in the run |

**Types** (LuciDin's names), from opaque to clear:

| Type | Instance suffix | Swirl | Scene | Settings |
|---|---|---|---|---|
| Conchoidal | `_Con` | yes | none (as Friendly) | `SceneMix` 0 |
| Colloform | `_Col` | yes | faint, behind the swirl | master defaults (`SceneMix` 0.55, `SwirlOverScene` 0.7) |
| Reniform | `_Ren` | ripples the scene | clearer | `SceneMix` 1, `SwirlOverScene` 0, `DistortMultiply` 0.03 |
| Prismatic | `_Pri` | none | clearest | `SceneMix` 1, `SwirlOverScene` 0, `DistortMultiply` 0 |

**Front and back:** on the lab's "square C" plane the side facing out from the pad is the plane's back side, so `FlipFront` (1)
mirrors the material to make that side the front (clockwise, scene not mirrored; LuciDin at Dunkel Forest's MHE). `TrueBack` (1) makes
the other side a true backside; with `TrueBack` 0 both sides read like the front and look into the scene the same way.

**Scene:** from the eye through each pixel to the inside wall of a sphere behind the portal (`SphereDepth` 100 cm behind, `SphereRadius`
400 cm), the cube map looked up towards that wall point; the eye comes from the camera-relative position and the surface's own axes
(no tangent-space convention). `SceneParallax` blends a flat picture (0) and the sphere (1, default). The game's own windows do the same
kind of thing (their cooked materials import the engine's `RayTracedSphere` with `SpherePosition` / `Radius`).

## 4. In-game runs (15 November, beta install, lab and pak added for the card)

| Run | Finding | Fix (commit) |
|---|---|---|
| 1 | first arch "not found": `LoadAsset` loads nothing from our pak | load by name with `GetAsset` (388e3db) |
| 1 | the old portal hid the ring; mesh ring copied the effect's turn | PAUSE hides the pad's own look (73782ac); the ring faces the pad's own angle (388e3db) |
| 1 | finer scaling wanted | Shift + M / N x1.01 (388e3db) |
| 2 | arch upright on square C; swirls alike front and back; tint and scene work; Night Realm fringe stays gold | back as a true backside, clockwise, Geo family, `DistortionEdge` in the tint (3e6b87f) |
| 3 | a glowing seam across the arch | the top's circle no longer cut at the springing line (837db42) |
| 3 | Door 3 m x 1.75 m | lab size (9ebbf49) |
| 4 | the outward face swirled anticlockwise | `FlipFront` (5eb7a44) |
| 5 | Night Realm fringe now tints; four types wanted | Con / Col / Ren / Pri (033af77) |
| 6 | scene "a bit stiff"; names shape first | sphere window, `MI_Geo<Shape>_<Type>` (90b8751) |
| 7 | the back shows the same view as the front | eye and sphere flip with the side (fc9f911) |
| 8 | all 24 work, Ren and Pri included; the back shows the other half | (done) |

The first material (`M_PortalHubLooks_Arch`, round arch only) was deleted at the end (LuciDin: "Delete it").

## 5. One pak set, three files

Answered for LuciDin (via the dispatcher): the three files cannot become one. In a cooked UE 5.4 IoStore game, packages load only
through the IoStore loader from `.utoc` / `.ucas`, and the engine mounts those through the `.pak` of the same name (a 339-byte stub here,
as for World A-D); a pak cooked without IoStore would carry the assets in the old format, which a shipped IoStore game does not load
(not tested: an optional proof would be a second copy under chunk 121 with IoStore off). One set can hold any amount of our own content
if it is cooked from one project whose labels share a chunk id: the looks, our own cube maps, later our own Niagara looks.

**LuciDin's pak rulings (15 Nov):** World A-D **stay four separate pak sets** (no merging). Our own Portal Hub content (the Geo looks,
later our own cube maps and looks) goes in **one shared set**, `PortalHubLooks_P` (chunk 120). The **main mod is one download**: the
Lua mod plus this content pak set together; custom worlds are separate downloads; the config editor stays its own zip.

## 6. For the look-design lab LuciDin wants next

Live on a dynamic instance of any Geo portal (one `SetScalarParameterValue` / `SetVectorParameterValue` / `SetTextureParameterValue`
each, all proven in the lab's tint, picture and ring-size keys):

| Group | Parameters (defaults) |
|---|---|
| Shape | `Shape` (0-4), `Pointed` (1), `EdgeWidth` (6 cm), `EdgePower` (2), `EdgeWobble` (3 cm), `EdgeFlicker` (0.5) |
| Swirl | `SwirlSpeed` (0.35, negative = anticlockwise), `SwirlTwist` (2.5), `InflowSpeed` (0.4), `NoiseScale` (1.863), `NoiseScale2` (2.818), `SwirlLow` / `SwirlHigh` (0.35 / 0.75) |
| Scene | `PortalTexture` (any `TC_*`), `SceneTint` (white), `SceneMix`, `SwirlOverScene`, `SceneParallax` (1), `SphereDepth` (100 cm), `SphereRadius` (400 cm), `SceneYaw` (0 deg), `SceneBlur` (0), `SceneBright` (1), `SceneZoom` (flat picture only), `DistortMultiply`, `DistortDistance` |
| Colour | `PortalCenterColor`, `PortalCenterColor2`, `PortalEdge`, `DistortionEdge`, `Brightness` (1) |
| Sides | `TrueBack` (1), `FlipFront` (1) |
| Size | the mesh ring's scale (metres); height, turn as CRD-042 |

Fixed in the material (a rebuild and recook to change): the shapes' maths, the noise pattern, the Masked / Unlit / Two Sided setup, the
usage flags, the set of parameters. A designer picks a Geo instance as the starting point and changes any of the above per portal, so a
looks table can store "instance + changed parameters".

## 7. What the Portal Designer (hub + editor) needs

LuciDin's order (15 Nov): no more portal-customization additions for now (scope held); the next cards are a **Portal Designer** (hub +
editor) and a **stills lab** card; the Geo rings ship in 1.0.

**Parameters a designer should expose** (the rest stay at the instance's values):

| Control | Parameter(s) | Notes |
|---|---|---|
| Look | the Geo instance `<Shape>_<Type>` | 24 choices; the starting point |
| Size | mesh-ring scale X / Y (metres) | start from section 3's table; height and turn as CRD-041 / CRD-042 |
| Colours | `PortalCenterColor`, `PortalCenterColor2`, `PortalEdge`, `DistortionEdge` | the grey x RGB scheme, or four free colours |
| Scene | `PortalTexture` (a `TC_*` cube map), `SceneYaw` | Ren / Pri / Col only (Con shows none) |
| Scene depth | `SphereDepth`, `SphereRadius` | advanced; defaults 100 / 400 cm |
| Swirl | `SwirlSpeed` (sign = direction), `SwirlTwist` | Con / Col / Ren |
| Gothic top | `Pointed` | Gothic only |
| Glow | `Brightness`, `EdgeWidth` | optional |

**Loading rule:** load a Geo instance with `AssetRegistryHelpers:GetAsset({ PackageName = "/Game/Mods/PortalHubLooks/Geo/MI_Geo<Shape>_<Type>",
AssetName = "MI_Geo<Shape>_<Type>" })` (FNames made with `UEHelpers.FindOrAddFName`), never only `LoadAsset` (it loads nothing from our
pak); then `KismetMaterialLibrary:CreateDynamicMaterialInstance(pad, instance, None, 0)` per portal and set the parameters on that.

**Pak fallback:** if the instance cannot be loaded (pak missing, or a client without it), keep the pad's own look (do not hide it, do
not add the mesh ring), log one line naming the missing pak, and carry on. The editor can warn when `PortalHubLooks_P.*` is not in
`Content\Paks\~mods\` (an install check like CRD-019's).

**Hub side:**
- Ship `PortalHubLooks_P.pak/.ucas/.utoc` in the 1.0 main download (`~mods`), the release builder's allowlist and checks extended to it.
- Per portal in `config.lua`: `geo = { look = "Arch_Col", size = { w, h }, tint = { r, g, b }, scene = "TC_...", ... }` (any section 6
  parameter), drawn as CRD-042's mesh ring: `AddComponentByClass(StaticMeshComponent)`, collision off **before** the shape, the engine
  Plane at square C's turn in the pad's own frame, `SetMaterial` with a dynamic instance of the Geo instance loaded by `GetAsset`, the
  pad's own look hidden (`SetVisibility(false)`, proven by PAUSE). MHEs inherit their portal's look (CRD-041 rule).
- On a client, drawn locally like the look (client mode); a pak missing on a client = the plain look, logged.
- Editor: a Geo panel (type, shape, size, colours, scene).
- Mind the hub's 13 free main-chunk locals (CRD-033): put it in a table.

## 8. Lab keys (dev only, `mod/PortalMaterialLab`; tests `tools/dev/tests/test_lab_own_ring.py`, 88 checks)

Mesh mode (`[`): Shift + SCROLL LOCK steps through the 24 Geo portals (shape by shape, Con / Col / Ren / Pri; on the engine Plane as
square C, at the shape's starting size); PAUSE hides / shows the pad's own look (Shift + U brings it back too); the ring faces the pad's
own angle. Every mode: Shift + M / N scale x1.01 (M / N stay x1.1). Keys checked against the game's input config (Scroll Lock, Pause, M,
N have no game binding; Shift alone is sprint), LuciDin's Input.ini (no rebinds) and our mods (the hub's PAUSE is a DEV_KEYS key, off in
the install and cut from the package). The lab picks the nearest pad within 15 m; a mesh ring stays on its pad until Shift + U.

## 9. Install state at the end of the card

Added to the beta install for the card: `Content/Paks/~mods/PortalHubLooks_P.*` and `Mods/PortalMaterialLab/` (with
`portal-heights.csv`) plus the line `PortalMaterialLab : 1` in `mods.txt` (6da3ae86 before, c6e83975 with it). At the end both
**stay installed and attached** for the stills lab card (LuciDin: "Leave it attached"; the dispatcher hands the install on): removing
the lab later = deleting that one line (bytes back to 6da3ae86). LuciDin's
`config.lua` (213495f9), `manual_exits.lua` (3544b049) and the hub's `main.lua` (1f4fa7af) were never touched. Install record: the
dispatcher's notes folder, `crd043-install.md`.

## 10. Open

- Round and Oval starting sizes are guesses: size them against a default and a Friendly portal in the lab (the log keeps the scale).
- Picking the pad the player looks at (a line trace) instead of the nearest: a lab follow-up, untried call.
- Two players: not tested (a client needs the pak too; the hub build decides how a missing pak shows).
