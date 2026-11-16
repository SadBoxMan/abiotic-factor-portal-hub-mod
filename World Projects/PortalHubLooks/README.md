# PortalHubLooks: our own "Geo" portal materials (CRD-043)

A UE 5.4 project (same engine as the game, like World A-D) that cooks Portal Hub's own portal materials into a small patch pak,
`PortalHubLooks_P`, for `Content\Paks\~mods\`. Everything in it is ours and CC0; nothing from the game or any other mod is copied.

| What | Where |
|---|---|
| Project | `AbioticFactor.uproject` (the name must stay `AbioticFactor` so the pak mounts under the game's content) |
| Master material | `/Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Geo` |
| 24 instances | `/Game/Mods/PortalHubLooks/Geo/MI_Geo<Shape>_<Type>` (e.g. `MI_GeoArch_Col`): types Con (Conchoidal: swirl, opaque), Col (Colloform: swirl over a faint scene), Ren (Reniform: window, swirl still ripples it), Pri (Prismatic: window, no swirl, clearest); shapes Arch (arched door), Gothic (pointed arch), Square, Door, Round, Oval |
| Chunk label | `/Game/Mods/PortalHubLooks/PAL_PortalHubLooks`: chunk **120** (container id `bcced51e259b6887`), labels its own folder only, Apply Recursively **off** |
| Dummy scene | `/Game/Particles/RenderTargets/TC_Portal_Warehouse`: a tiny gradient cube map of our own, at the game's path. It is only the default scene while cooking: it cooks into chunk 0 (never installed), so in game the material finds the game's real Mall cube map |
| Build script | `Scripts/build_ring_material.py` (headless editor; makes the master, the 24 instances, the label and the dummy) |

## The material

Modelled on the game's Night Realm arch (Masked, Unlit, a swirl over the Mall scene, an orange edge), but our own graph: one
Custom (HLSL) node fed by parameters. Unlike the game's arch it is **Two Sided** and works everything out from the surface:

- **Shape** (`Shape` 0 arched door, 1 gothic arch, 2 rectangle, 3 round, 4 oval; `Pointed` for the gothic top) as a distance in real
  centimetres. The surface's size is read in the shader from the pixel derivatives of the camera-relative position, so the mesh's
  scale sets the size and a round top stays round on a tall, narrow arch. Square and Door are the same rectangle at different sizes.
- **Swirl**: noise on circles around the shape's centre, turning **clockwise** seen from the front (`SwirlSpeed`, negative =
  anticlockwise), `NoiseScale`, `NoiseScale2`, `SwirlTwist`, `InflowSpeed`, `SwirlLow` / `SwirlHigh`.
- **Front and back**: the front is the side facing out from the pad on the lab's square C, which is the plane's back side
  (`FlipFront` 1, default; LuciDin at Dunkel Forest's MHE); `TrueBack` 1 (default) = the other side is a true backside (mirror image,
  swirl turning the other way, as seen from behind); 0 = both sides read like the front.
- **Scene**: `PortalTexture` (any cube map), `SceneTint`, `SceneZoom`, `SceneYaw`, `SceneBlur`, `SceneBright`, `SceneMix`,
  `SwirlOverScene`, `DistortMultiply`, `DistortDistance`, and `SceneParallax` (0 = flat picture; more = the scene shifts with the view).
- **Colours**: `PortalCenterColor` (dark swirl), `PortalCenterColor2` (bright swirl), `PortalEdge` (edge glow), `DistortionEdge`
  (edge flicker), plus `EdgeWidth` / `EdgeWobble` (cm), `EdgePower`, `EdgeFlicker`, `Brightness`.
- Types: Con sets `SceneMix` 0; Col keeps the defaults; Ren sets `SceneMix` 1, `SwirlOverScene` 0 and a light ripple
  (`DistortMultiply` 0.03); Pri sets `SceneMix` 1, `SwirlOverScene` 0 and no ripple (`DistortMultiply` 0).

Usage: static meshes (always), Niagara sprites and Niagara mesh particles. Meant for a flat face (the engine plane); the lab puts it
on `/Engine/BasicShapes/Plane` stood up as "square C".

## Build and package

1. Close the editor on this project. Rebuild the assets (only needed after changing the script):
   `UnrealEditor-Cmd.exe "<this folder>\AbioticFactor.uproject" -run=PythonScript -Script="<this folder>\Scripts\build_ring_material.py" -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout`
   (report in `Scripts\build_ring_material.txt`).
2. Cook and package: `RunUAT.bat BuildCookRun -project="<this folder>\AbioticFactor.uproject" -noP4 -platform=Win64 -clientconfig=Shipping -cook -stage -pak -iostore -compressed -nocompileeditor -nocompile -unattended -utf8output`
   (under half a minute), or File > Package Project > Windows in the editor.
3. Take only `Saved\StagedBuilds\Windows\AbioticFactor\Content\Paks\pakchunk120-Windows.pak/.ucas/.utoc`, rename the three to
   `PortalHubLooks_P.*` and put them in the game's `Content\Paks\~mods\`. Never install `pakchunk0-*` or `global.*`. All three
   files are needed (the game loads assets only from IoStore containers; the `.pak` is the stub that mounts them).
4. Check the pak: `python tools\dev\read_utoc.py <...>\PortalHubLooks_P.utoc` must list only `Mods/PortalHubLooks/...`.

In game, assets from our pak are not in the game's asset registry, so UE4SS's `LoadAsset` finds nothing: load them by name with
`AssetRegistryHelpers:GetAsset({ PackageName, AssetName })` (as the hub loads World A-D and the lab loads these).
In the lab (`mod/PortalMaterialLab`, mesh mode) Shift + SCROLL LOCK steps through the 12 Geo rings.
Findings: `findings/own-ring-material-2026-11.md`.
