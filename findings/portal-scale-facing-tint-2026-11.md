# Portal look scale, facing and grey tint (CRD-042, 14-15 November 2026)

Answers LuciDin's requests of 14 November (via CRD-039): "research altering the scale (X/Y and both) as well as the billboarding" and
"a Grayscale version of the portals that RGB values can be passed on to (test Friendly and Default first)". Follows
[`portal-looks-deep-dive-2026-11.md`](portal-looks-deep-dive-2026-11.md) (CRD-039) and [`portal-designs-2026-11.md`](portal-designs-2026-11.md).

Sources: the cooked game files of 21 August 2026 (Niagara systems and materials converted to JSON with UAssetGUI's command line and
the v9.1 mappings; nothing extracted into the repo), the 6 November UE4SS object dump, and in-game runs on the beta install (v1.5.0)
on 14-15 November with new lab keys (section 6). Everything here uses game assets only; nothing was written to a save.

## 1. Short answers

| Question | Answer |
|---|---|
| Scale a look per pad, X / Y / both? | **Only Friendly's 14 looks** (their ring is a 3D mesh): `ParticleLoop:SetRelativeScale3D` scales them per axis. Every other look's ring is a flat sprite of fixed size and ignores the scale (in game). |
| Make any ring any size, per axis? | **Yes, with a "mesh ring"** (section 4): the ring material drawn on a plain 3D shape added to the pad. Scales per axis far past the window, game assets only (in game). |
| Turn a look per pad? | **Door, NightRDoor_2, Torii and Garden turn** with `ParticleLoop:K2_SetRelativeRotation` (in game). The rest don't visibly (Default and the window looks, Salem, Shadowgate2, Rift, Botanical, Friendly). |
| Stop the billboarding (camera-facing)? | **Friendly: yes, but per look, not per pad**: writing its ring renderer's `FacingMode` to `Default` (a run-time edit of the loaded look) stops it facing the camera, and it then turns like Garden (in game). **Default's window: no**: it faces the camera in all five facing modes, so its turn does not come from the renderer setting. |
| Grey look tinted by any RGB, per pad? | **Yes, on the window looks** (in game): put an instance of a game ring material (Friendly White, Friendly, Garden, Torii, Salem, Shadowgate2, Shadowgate Blue, Botanical Green / Red, Door, Night Realm) into the pad's `User.PortalTexture` and set its colours. All 11 took a tint. Also yes on the mesh ring. |
| Ring size inside a window? | Every ring material has `Radius (S)`: per pad it shrinks the round rings and grows them **up to the window's square**, where they are cropped (in game). Door and Night Realm don't change (their cut-out is a shape texture). |
| Front and back? | Door's ring material is two-sided; Night Realm's is front only (in game, matches the cooked files). A mesh-ring **back face** (a second shape, back to back) gives any ring a back, but Night Realm's swirl then runs out of step front to back: fixing that needs our own material (proposal 6). |

## 2. What each look is made of (cooked files)

Ring part per look: renderer kind, alignment / facing. All rings are local-space, GPU-simulated emitters.

| Look | Ring | Kind | Facing (renderer) | Scales per pad | Turns per pad (in game) |
|---|---|---|---|---|---|
| Default, Blueverse, Greenverse, Redverse, Dark, Fog | `portalmap` (material from `User.PortalTexture`) | sprite | CustomAlignment / CustomFacingVector, but faces the camera in game in every mode | no | no |
| Friendly (14 colours) | `Portal`, mesh `SM_Portal` | mesh | CameraPosition (read in game) | **yes, per axis** | no (yes once its facing is `Default`, for the whole look) |
| Garden | `portal` | sprite | CustomAlignment / CustomFacingVector | no | **yes** (U also tilted it) |
| Torii | `portal` | sprite | CustomAlignment / CustomFacingVector | no | **yes** |
| Door | `portal` (`M_WorldPortal_Warehouse`) | sprite | CustomAlignment / CustomFacingVector | no | **yes** (one facing mode turned it on the vertical axis only) |
| Night Realm (`NightRDoor_2`) | `portal` (`M_Portal_Arch`) | sprite | CustomAlignment / CustomFacingVector | no | **yes** |
| Salem, Shadowgate2 | `portal` | sprite | CustomAlignment / CustomFacingVector | no | no (unexplained: same settings as Garden) |
| Botanical Green / Red | `portal` | sprite | CustomAlignment / FaceCamera | no | no |
| Rift | `rift` | sprite | Unaligned / FaceCamera | no | no |
| SnowFlurry, SunDisk | `Blackhole` mesh + `Swirl` sprites | mesh + sprite | (mesh raw in the files) | not tested | no |
| Tiny | no ring (lightning, smoke) | sprite | - | no | no |

Part names read capitalised in game (`Portal`, `Sparks`, `PortalMap`) while the cooked files say `portal_0`: compare in lower case.
`FacingMode` is a one-byte `EnumProperty` on both renderer classes (mesh 0 Default, 1 Velocity, 2 CameraPosition, 3 CameraPlane; sprite
0 FaceCamera, 1 FaceCameraPlane, 2 CustomFacingVector, 3 FaceCameraPosition, 4 FaceCameraDistanceBlend).

Materials: `M_Portal_Shapes_Master` is cooked for Niagara sprites and meshes; Friendly, Friendly White, Garden, Torii, Salem,
Shadowgate2, Shadowgate Blue and the Botanicals carry their own static permutation; Door's `M_WorldPortal_Warehouse` and 12 of the 13
Friendly colours share a parent's. The 13 coloured Friendly materials differ only in `PortalCenterColor`, `PortalCenterColor2`,
`PortalEdge` (and a few noise textures). Ring sizes (`Radius (S)`): Night Realm 0.24, Friendly 0.35, Garden / Torii / Botanical 0.37,
Door 0.40, Salem / Shadowgate 0.58. The plain window `M_WorldPortal` has no colour or radius setting.

## 3. Grey tint (window looks)

How (all calls proven in game): `KismetMaterialLibrary:CreateDynamicMaterialInstance(pad, ring material, None, 0)`, then
`ParticleLoop:SetVariableMaterial("User.PortalTexture", instance)` (after any `SetAsset`), then read the ring's own colours
(`K2_GetVectorParameterValue` on `PortalCenterColor`, `PortalCenterColor2`, `PortalEdge`), turn each to its grey level
(0.2126 R + 0.7152 G + 0.0722 B) and set `grey x RGB` with `SetVectorParameterValue`. Friendly White's grey levels: centre 0.109,
centre 2 1.000, edge 4.837. Night Realm takes the tint through its edge colour only. `PortalTexture` on the instance changes the
scene inside the ring (`PortalImage` on the plain window); `Radius (S)` its size, up to the square.

Tested in game on B-1 (Default) and its MHE, and on the other window looks (LuciDin): every ring drew in the window and took every tint.
The tinted ring has the window's facing (it faces the camera), not Friendly's.

Per-pad colour on a Friendly look's own ring stays impossible with game assets (CRD-039: `SetMaterial` ignored). What our own look would
need: a copy of the Friendly system whose ring material is bound to a user parameter (like the window's `User.PortalTexture`) or exposes
a `User.` colour, cooked into a `~mods` pak (not built).

## 4. The mesh ring (game assets only)

The window's square is fixed, so the ring material is drawn on a `StaticMeshComponent` added to the pad. Built one untried call per
press, all now proven: `pad:AddComponentByClass(StaticMeshComponent, false, identity transform, false)`, place it at the effect
(`K2_SetRelativeLocation` / `K2_SetRelativeRotation` from `ParticleLoop`'s), `SetCollisionEnabled(0)` **before** a shape is on it
(`SM_Portal` has collision; the ring must never block the pad), `SetStaticMesh(shape)`, `SetMaterial(0, ring instance)`.
Remove with `K2_DestroyComponent`. Plain static meshes need no material usage flag.

| What | Result (in game) |
|---|---|
| Ring material on `SM_Portal` | draws ring and centre; tint, scene (`PortalTexture`) and per-axis scale all work; the size limit is far past the window, "well above what players would reasonably edit" (LuciDin) |
| Door's scene | **changes per pad** on the mesh ring (impossible on Door's own look, CRD-039) |
| Rectangular area | `SM_Portal` is oval and cuts Door's corners; the engine's `/Engine/BasicShapes/Plane` (also `/Game/StarterContent/Shapes/Shape_Plane`) gives a square. Stand it up by **roll**, never pitch 90 (gimbal lock: the back face crossed the front as an X and the arch lay on its side). For the Night Realm arch the right standing is roll +90, yaw +90 ("square C") |
| Back face | a second component at yaw + 180, same shape and instance (follows tints and pictures); works; Night Realm's swirl runs out of step front to back (its material is front-only and view-based) |
| Every other ring type | "worked well" (LuciDin) |

## 5. Verdicts per feature and what the hub and editor would need

| Feature | Verdict | Hub (`mod/PortalHub`) | Editor (`tools/PortalHubConfig`) |
|---|---|---|---|
| Scale, Friendly looks | per pad, per axis | `scale = { x, y, z }` per portal: `ParticleLoop:SetRelativeScale3D` after `SetAsset` | a scale row shown for Friendly looks only |
| Scale, any ring | per pad, per axis, via the mesh ring | the mesh ring (below) | as below |
| Turn, Door / Night Realm / Torii / Garden | per pad | `turn = degrees` per portal: `ParticleLoop:K2_SetRelativeRotation` | a turn field for those four looks |
| Friendly facing off | per look only (asset edit) | a hub-wide switch per look, written once at load (affects every pad with that look, game restart to undo) | probably not worth an editor control |
| Grey tint in a window | per pad | `ring = "M_Portal_Garden"`, `tint = { r, g, b }`, optional `ringSize`, per portal on a window look | ring picker + colour picker, window looks only |
| Mesh ring | per pad, game assets only | `meshRing = { ring, tint, shape = "oval" / "square", scale = { x, y }, back = true, picture }` per portal; collision off before the shape; on a client, styled locally like the look | a "custom ring" panel: ring, colour, shape, size X / Y, back face, scene |
| Two-sided Night Realm in step | needs our own material | - | - |

Keys used by the lab are dev only; any hub build ships only NUMPAD 1 / 2 (CRD-015 rule).

## 6. Lab keys and runs (dev only, `mod/PortalMaterialLab`)

`[` (new, `Key.OEM_FOUR`; the game binds it only to the debug `DebugCycleCulture`) switches the look keys between four modes:
**overlay** (CRD-039, unchanged), **own** (M / N scale and LEFT / RIGHT turn the nearest pad's own look on the axis I picks, O / P
height, SCROLL LOCK resets, `/` lists its renderers, U writes the ring's next facing mode and the next U restarts the effect),
**tint** (SCROLL LOCK next grey ring in a window look, `.` tint, `,` scene, M / N ring size) and **mesh** (SCROLL LOCK builds the mesh
ring in four steps then steps the ring material, `.` `,` M / N LEFT / RIGHT O / P as above, L shape, U back face, Shift + U removes it).
Test `tools/dev/tests/test_lab_scale_facing_tint.py` (115 checks).

Runs on 14-15 November, beta install with the lab added and removed again: parts 1-4 (scale, turn, facing, tint), ring size, mesh ring,
shapes, back face. No crash, no `Ref was not function`, nothing written to a save. One heavy stutter right after a load (game freezes
of about 1 s and 3.5 s, just after the game's autosave and while worlds A-D streamed in, before any lab key); its UE4SS log was
overwritten by a relaunch, so it is unexplained, seen once. LuciDin's `config.lua` changed only by his own edits; `manual_exits.lua`
(3544b049) untouched; `mods.txt` restored to 6da3ae86 and the lab folder removed afterwards.

## 7. Proposals (sent to the dispatcher; none is a card yet)

1. **Hub: Friendly scale** per portal (per axis), editor row for Friendly looks.
2. **Hub: turn** per portal for Door, Night Realm, Torii, Garden.
3. **Hub: grey-tinted ring in window looks** (`ring`, `tint`, `ringSize`), editor ring + colour pickers.
4. **Hub: mesh ring** per portal (ring, tint, oval / square, size X / Y, back face, scene incl. Door), editor panel. Proven parts only;
   the biggest of the four and the most flexible.
5. Optional: hub-wide "Friendly facing off" per look (asset edit at load).
6. **Our own ring material** (Opus, high; LuciDin asked for it): a two-sided, surface-based copy of the arch (and later other rings)
   cooked into a `~mods` pak, so a mesh ring shows front and back in step. Proves "our own look material" end to end.
