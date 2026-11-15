# Portal looks deep dive: mixing, window pictures, recolouring (CRD-039, 14 November 2026)

Answers LuciDin's three questions after CRD-037 ([`portal-designs-2026-11.md`](portal-designs-2026-11.md)), with the end goal he set:
**can players have their own portal pictures and fine-tune how portals look, and how far does it go** (decides any extras for 1.0).

Sources: the cooked game files of 21 August 2026 (`Modding Tools\Abiotic\PAK Assets`, read as name tables and, for the Niagara
systems, converted to JSON with UAssetGUI's command line and the v9.1 mappings; nothing extracted into the repo); the UE4SS object dump
of 6 November (what Lua can call); and an in-game run on CordonaCorp the same evening with new lab keys (`mod/PortalMaterialLab`, see
section 6). Caveat: the pak copy predates v1.5.0; the in-game results are on v1.5.0.31876.

## 1. Short answers

| Question | Answer |
|---|---|
| Mix parts of two looks on one pad? | **Yes, by overlay** (proven in game): a second look attached to the pad, with the parts not wanted switched off, can be moved and (mesh parts only) scaled to fit. **No other way**: the engine has no call that adds, removes or swaps one part inside a look at run time. |
| How is the picture in a portal made? | A **static cube map** (six images of a place, captured once in the editor; `TextureCube` assets under `/Game/Particles/RenderTargets/`), drawn by a "sphere" material. Never live. Door's Mall picture is `TC_Portal_Warehouse` in `M_WorldPortal_Warehouse`. |
| Can a picture be changed, or our own used? | **Window looks: yes, per pad** (proven in game: Default and the Cabin's Blueverse showed other worlds' pictures). Any cube map works, including ones no game portal uses (Alps, Torii, OrangeGlow). Our own picture = our own cube map cooked into a small `~mods` pak (as Worlds A-D ship): the hub-side call is proven, the cooking step is not tried yet. **Door, Night Realm and every other look: no, not per pad** (tested in game). |
| Can other looks be recoloured? | **Not per pad** (tested in game on Friendly Red, Garden, Torii, Door: every call accepted, nothing changed). Their colours are material settings fixed inside each look's own file, and the game's effect component exposes no material slots to override (0 slots; `SetMaterial` ignored). Left untested: editing the look's asset itself, which would recolour every pad with that look. The pad light (`lightColor`, already in the hub) stays the only per-pad tint. |
| Why `User.Color` was dropped | Only the three Rift looks declare it. October's test set it (x6) on every hub portal and nothing visible changed. The cooked files can't show whether a part reads it (user parameters read by scripts are not stored by name per part; the same is true of Burst's `User.Color01`). No Rift pad was in the room tonight, so it was not retried: **untested**, low value (Rift is one look). |

## 2. What a look is made of (from the cooked files)

Every look is one Niagara system with named parts (emitters); each part draws one material, either a flat **sprite** or a 3D **mesh**.
The part that matters for pictures and colour is the ring. It falls into three kinds:

| Kind | Looks | Ring material | Picture | Colour |
|---|---|---|---|---|
| **Window** | Default (`Niagara_Portal`), Blueverse, Greenverse, Redverse, Dark, Fog | `portalmap` sprite draws whatever material is in the user parameter `User.PortalTexture` (default `M_WorldPortal`) | cube map in `PortalImage` of that material: **set from the pad**, per pad | `M_WorldPortal` has no colour setting (only picture, ripple, mask) |
| **Opaque** (picture baked) | all 14 Friendly, Garden, Torii, Botanical Green / Red, Door, Night Realm (`NightRDoor_2`) | fixed in the look's file: instances of `M_Portal_Shapes_Master` (Friendly, Garden, Torii, Botanicals, Door) or `M_Portal_Arch_Master` (Night Realm) | a cube map in the material's `PortalTexture`, fixed: Friendly = Far Garden (`TC_Portal_Anteverse_A`), Garden / Torii / Botanicals = `TC_Portal_Torii`, Door and Night Realm = the Mall (`TC_Portal_Warehouse`). In Door it is the main image; in the swirl looks a faint layer under the swirl | `PortalCenterColor`, `PortalCenterColor2` (and `PortalEdge`), fixed per look |
| **Opaque** (no picture) | Salem, Shadowgate2, Rift; SnowFlurry, SunDisk; Tiny | Salem / Shadowgate2: Shapes-master instances without a cube map; Rift: `M_Portal_Rift`; SnowFlurry / SunDisk: a black-hole mesh (`M_BlackHole_SnowPortal` / `_SunDisk`) | none. SnowFlurry and SunDisk **declare** `User.PortalTexture` but no part draws it (setting it does nothing). Tiny binds it to its **lightning** sprites, not a window | Salem / Shadowgate2: `PortalCenterColor` / `2`; Rift: `ColorMultiplier` (+ `User.Color`); black holes: `InnerColor` / `OuterColor`; all fixed |

The Friendly ring is a mesh (`SM_Portal`) turned to face the player inside the effect; Garden's and Torii's rings are sprites with a fixed
facing (that is why the DLC portals don't follow the player). Facing is part of the look, not the pad (section 5).

The game's own pad pictures: Facility.umap references `M_WorldPortal_HCabin`, `_AnteA`, `_Fog` and `_Offices`; the vignette maps
reference `M_WorldPortal_Offices` (return pads), Village Den `_AnteC`. **The Cabin entrance shows the cabin scene by default** (LuciDin,
in game), while the pad's `PortalTexture` Blueprint variable reads `none`: the level sets the window on the effect directly. CRD-037's
"Cabin = Blueverse + ice-blue light + Cabin window" is confirmed.

## 3. Per-look table

"Pad" = changeable per pad from the hub. "Asset" = only by editing the look's own file at run time (untested; changes every pad with that
look). Mix = overlay results (section 4).

| Look | Picture: source | Colour inputs | Recolourable how | Can mix with |
|---|---|---|---|---|
| Default (`Niagara_Portal`) | pad (`User.PortalTexture` -> `PortalImage`), **proven** | none on the window | pad light only | any overlay (proven on other pads) |
| Blueverse | pad, **proven** (Cabin entrance) | none on the window | pad light only | any overlay |
| Greenverse, Redverse, Dark, Fog | pad (same parts as Default; not run, same binding) | none on the window | pad light only | any overlay |
| Friendly (14 colours) | baked: Far Garden cube map (faint) | `PortalCenterColor` / `2`, `PortalEdge` (baked per colour) | pad: **no** (tested, Friendly Red); asset: untested | any overlay, **proven** on Friendly Red (Garden vines, SnowFlurry swirl, Night Realm leaves, Friendly sparks) |
| Garden | baked: Torii cube map | `PortalCenterColor` / `2` | pad: **no** (tested); asset: untested | any overlay |
| Torii | baked: Torii cube map | `PortalCenterColor` / `2` | pad: **no** (tested); asset: untested | any overlay |
| Botanical Green / Red | baked: Torii cube map | `PortalCenterColor` / `2` | pad: no (same as Garden); asset: untested | any overlay |
| Door | baked: **the Mall** | `PortalEdge` etc.; no centre colour | pad: **no** (tested, B-4: picture would not change); asset: untested | any overlay |
| Night Realm (`NightRDoor_2`) | baked: the Mall | arch settings, no colour | pad: no; asset: untested | any overlay |
| Salem, Shadowgate2 | none | `PortalCenterColor` / `2` | pad: no; asset: untested | any overlay |
| Rift | none | `ColorMultiplier`; `User.Color` (unclear) | pad: `User.Color` untested tonight (no visible change in October); asset: untested | any overlay |
| SnowFlurry, SunDisk | none (declared, unused) | black hole `InnerColor` / `OuterColor` | pad: no; asset: untested | any overlay; as an overlay its swirl moves but does not scale |
| Tiny | none (its "window" parameter feeds the lightning) | none | pad light only | any overlay |

## 4. Mixing: every route

| Route | Verdict | Why |
|---|---|---|
| Second effect on the pad (`NiagaraFunctionLibrary:SpawnSystemAttached` to the pad's effect, then `SetEmitterEnable(part, false)` for the parts not wanted) | **Possible, proven in game** (14 Nov, A-3) | Garden vines, SnowFlurry swirl, Torii petals, Night Realm leaves and Friendly sparks each showed on the Friendly Red ring. Removed cleanly with `K2_DestroyComponent`. |
| Fitting the overlay: `K2_SetRelativeLocation` / `SetRelativeScale3D` on it | **Possible, proven** | Moves work for attached parts. Scale works on **mesh parts** (Garden's vines, per axis too), not on **sprites** (SnowFlurry swirl). Torii's petals did not follow either (they stay where they spawned in the world). LuciDin's Garden-vines-on-Friendly-Red fit: up 40 cm, sideways 10 cm (Y), width x1.0-1.1. |
| Switching parts of the pad's own look off (`SetEmitterEnable`) | **Possible, in the hub today** (`hideEmitters`) | Same call; per look today, a per-portal version is easy. |
| Adding, removing or swapping one part inside a running look | **Impossible** | The engine's NiagaraComponent API (object dump: every NiagaraComponent and NiagaraFunctionLibrary function) has no such call; `SetAsset` swaps the whole look. Parts are compiled into the look's scripts. |
| Putting one look's ring material on another look's part (`SetMaterial`) | **Impossible per pad** (tested) | The component reports 0 material slots and ignores `SetMaterial` (index 1 and 2 on Friendly Red, 0 on Garden). |
| Putting one look's picture into a window look | **Possible, proven** | Section 5. |

## 5. Pictures, colour, height and facing: what the hub can do

| Feature | Possible? | How (hub) | Proven |
|---|---|---|---|
| Picture per portal, window looks | **yes** | `KismetMaterialLibrary:CreateDynamicMaterialInstance(pad, M_WorldPortal or the pad's window material, None, 0)`, `SetTextureParameterValue("PortalImage", cube map)`, then `ParticleLoop:SetVariableMaterial("User.PortalTexture", instance)` after `SetAsset`. Or simply put a ready instance (`M_WorldPortal_HCabin`, `_AnteA`, `_Fog`, `_Offices`, `_AnteC`) in `User.PortalTexture`. | in game, 14 Nov (B-1 Default, Cabin entrance) |
| Our own picture | **likely** | a `TextureCube` cooked into a small pak in `~mods` (UE 5.4 project, like Worlds A-D), loaded by path and put in `PortalImage`. Making a cube map: a scene capture in the editor, or six images imported as a cube. | hub call proven; the cooked pak not tried (a small test card) |
| Picture on Door / Night Realm / Friendly / others | **no per pad** | baked in the look's material | tested in game (Door, Garden, Torii, Friendly Red) |
| Ring colour, opaque looks | **no per pad** | colours are fixed material settings inside each look | tested in game |
| Ring colour, window looks | no (no colour setting on the window) | pad light (`lightColor`) tints the whole portal | tested (B-1) |
| Look height | **yes, per pad** | `ParticleLoop:K2_SetRelativeLocation({X, Y, Z}, false, {}, true)` (only the look moves; base, trigger, light stay). Blueprint default 158 cm above the pad; the game's Stone Garden pad uses 138.3 cm. LuciDin's picks: Friendly Red 108 cm, Default 118 cm, Botanical Red 138 cm, Door 158 cm (he sets a height per look later, on his 1.0 checklist) | in game, 14 Nov |
| Overlay (mixing) | **yes, per pad** | `overlay = { design, keep or off = { parts }, offset = { x, y, z }, scale = { x, y, z } }` per portal; client mode styles it locally like the look | in game, 14 Nov |
| Facing (billboarding) | **no per pad** | fixed in each look. Fixed facing: Garden, Torii, Salem, Shadowgate2, Door, Night Realm, the window looks' window. Facing the player: Friendly's mesh ring, the lightning, SnowFlurry's snow, the Botanical rings and ivy. Fixed-facing looks turn with the pad. | desk (renderer settings); LuciDin's observation |
| Recolour, re-picture or re-face a look for every pad (edit the look's asset at run time) | untested | write the renderer's `Material` / `OverrideMaterials` on the loaded system and `ReinitializeSystem`; may not take in a cooked build | - |
| **Everything above, without limits** | **yes, as our own looks** | our own Niagara systems (copies of the game's with our colours, our cube maps, fixed facing, sizes) cooked into a `~mods` pak and named as a `design` like any game look | not tried; 2.0-sized work (UE 5.4 project or the Mod Editor) |

## 6. In-game run (14 November, CordonaCorp, beta install with the lab added for the run)

Lab keys added for this card (CRD-039; the lab never ships): `/` look survey (read-only: look, `PortalTexture`, light, material slots, the
effect's place on its pad), SCROLL LOCK material instance, U `SetMaterial`, `.` colour, `,` picture, L overlay, O / P up / down (overlay,
or with no overlay the pad's own look), LEFT / RIGHT sideways, M / N scale, I scale axis. Keys checked against the game's input config
(`pakchunk0-Windows.pak`: J, K, T, Y, H, Up and Down are taken; F9 is a debug screenshot; F6 / F8 belong to PortalLogger, PAUSE to the
hub's dev keys), LuciDin's own rebinds, and every key our mods bind. Each key logged its untried native call first; none crashed.
Test: `tools/dev/tests/test_lab_looks.py` (81 checks).

| Block | Pad | Result |
|---|---|---|
| 1 | A-3 Friendly Red | effect reports 0 material slots; `CreateDynamicMaterialInstance` on it returns nothing; a separate instance put on with `SetMaterial` (index 1, 2): accepted, **no visible change** in colour or picture |
| 2 | B-1 Default | **picture changes** (Mall, Flathill, Offices, Far Garden); colour no change (as expected) |
| 3 | Cabin entrance (Blueverse) | **picture changes** (cabin scene -> Flathill); `PortalTexture` variable reads none |
| 3 | Stone Garden, Torii entrances | no visible change |
| 4 | B-4 Door | the Mall picture would not change |
| 5 | A-3 overlays | vines, swirl, leaves, sparks shown; moves work; mesh vines scale (per axis), sprites don't; Torii petals don't follow |
| height | A-3, B-1, B-2, B-4 | look moves up / down per pad; final picks above |

No `Ref was not function`, no Lua error. Nothing written to a save; LuciDin's `config.lua` (his own B-4 change, Door) and
`manual_exits.lua` (3544b049) untouched by the session.

## 7. Proposals (sent to the dispatcher; none is a card yet)

1. **Hub: per-look effect height** (LuciDin's 1.0 checklist item "Portal Height"): a height per look in the per-world looks table
   (`looks.lua` of CRD-037) applied after `SetAsset`, with config override per portal; editor field.
2. **Hub: window picture** for the six window looks (`picture = "TC_..."` or a ready `M_WorldPortal_*`), per portal and in the looks
   table; the Cabin (B-3) look then gets its real window. Editor: a picture drop-down shown only for window looks.
3. **Hub: overlay** per portal (design, parts, offset, scale) with an editor picker; mesh parts scale, sprites don't.
4. **Test card: our own cube map** cooked into a `~mods` pak and shown in a window look (proves "your own pictures" end to end).
5. Later (2.0): **our own looks** as a cooked Niagara pak (recolour, re-picture and fixed facing for any look).
6. Optional desk/lab follow-up: run-time asset edit of a look's ring material (global recolour) and Rift's `User.Color`, if still wanted.
