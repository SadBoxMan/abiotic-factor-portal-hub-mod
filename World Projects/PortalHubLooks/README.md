# PortalHubLooks: our own portal ring materials (CRD-043)

A UE 5.4 project (same engine as the game, like World A-D) that cooks Portal Hub's own ring material into a small patch pak,
`PortalHubLooks_P`, for `Content\Paks\~mods\`. Everything in it is ours and CC0; nothing from the game or any other mod is copied.

| What | Where |
|---|---|
| Project | `AbioticFactor.uproject` (the name must stay `AbioticFactor` so the pak mounts under the game's content) |
| Material | `/Game/Mods/PortalHubLooks/Materials/M_PortalHubLooks_Arch` |
| Chunk label | `/Game/Mods/PortalHubLooks/PAL_PortalHubLooks`: chunk **120** (container id `bcced51e259b6887`), labels its own folder only, Apply Recursively **off** |
| Dummy scene | `/Game/Particles/RenderTargets/TC_Portal_Warehouse`: a tiny gradient cube map of our own, at the game's path. It is only the material's default scene while cooking: it cooks into chunk 0 (never installed), so in game the material finds the game's real Mall cube map |
| Build script | `Scripts/build_ring_material.py` (headless editor; makes the material, the label and the dummy) |

## The material

Modelled on the game's Night Realm arch (Masked, Unlit, an arch shape, a swirl over the Mall scene, an orange edge), but our own
graph: one Custom (HLSL) node fed by parameters. Unlike the game's arch it is **Two Sided** and works everything out from the
surface (UV), so one face reads the same from both sides:

- the arch is a distance field in UV (no mask texture): `Radius (S)` (half width), `ArchHeight`, `ArchBottom`, `Round` (0 arch, 1 oval);
- the swirl is noise on circles around the centre, turning with time (no noise texture): `NoiseScale`, `NoiseScale2`, `SwirlSpeed`,
  `SwirlTwist`, `InflowSpeed`, `SwirlLow` / `SwirlHigh`;
- on the back face the UV x is mirrored (`TwoSidedSign`);
- the scene is `PortalTexture` (any cube map) looked up from UV, with `SceneZoom`, `SceneYaw`, `SceneBlur`, `SceneBright`, `SceneMix`,
  `SwirlOverScene`, `DistortMultiply`, `DistortDistance`, and `SceneParallax` (0 = flat picture; more = the scene shifts with the
  viewing angle, worked out per side);
- colours: `PortalCenterColor` (dark swirl), `PortalCenterColor2` (bright swirl), `PortalEdge` (edge glow), `DistortionEdge` (edge
  flicker), plus `EdgeWidth`, `EdgePower`, `EdgeWobble`, `EdgeFlicker`, `Brightness`.

Usage: static meshes (always), Niagara sprites and Niagara mesh particles.

## Build and package

1. Close the editor on this project. Rebuild the assets (only needed after changing the script):
   `UnrealEditor-Cmd.exe "<this folder>\AbioticFactor.uproject" -run=PythonScript -Script="<this folder>\Scripts\build_ring_material.py" -unattended -nosplash -nullrhi -nosound -NoSourceControl -stdout`
   (report in `Scripts\build_ring_material.txt`).
2. Cook and package: `RunUAT.bat BuildCookRun -project="<this folder>\AbioticFactor.uproject" -noP4 -platform=Win64 -clientconfig=Shipping -cook -stage -pak -iostore -compressed -nocompileeditor -nocompile -unattended -utf8output`
   (about half a minute), or File > Package Project > Windows in the editor.
3. Take only `Saved\StagedBuilds\Windows\AbioticFactor\Content\Paks\pakchunk120-Windows.pak/.ucas/.utoc`, rename the three to
   `PortalHubLooks_P.*` and put them in the game's `Content\Paks\~mods\`. Never install `pakchunk0-*` or `global.*`.
4. Check the pak: `python tools\dev\read_utoc.py <...>\PortalHubLooks_P.utoc` must list only `Mods/PortalHubLooks/...` (two files).

In the lab (`mod/PortalMaterialLab`, mesh mode) the material is the ring after the game's arch; Shift + SCROLL LOCK swaps the two.
Findings: `findings/own-ring-material-2026-11.md`.
