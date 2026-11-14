# Portal designs: how they work, what each world uses, the Cabin, MHEs (CRD-037, 14 November 2026)

Research only (no code changed). Answers LuciDin's four "Last Call" design items before 1.0. Sources: `mod/PortalHub/Scripts/main.lua`,
`config.lua`, `slots.lua`, `manual_exits.lua`; `tools/PortalHubConfig/hubdata.py`, `PortalHubConfig.py`; the older note
[`portal-designs.md`](portal-designs.md); the proof-of-concept's per-pad design dump `PortalDesigns.txt` (written by `mod/PortalPoC`'s
`dump_designs`, 10 October 2026, in the game's `Binaries\Win64`, every teleporter in the Facility with its particle system, `PortalTexture`,
light colour); the UE4SS object dump of 6 November (`ue4ss_backup_2026-11-10_pre-fresh-install\ue4ss\UE4SS_ObjectDump.txt`); and the
names inside the cooked game files (`PAK Assets`, read as text only). No in-game run was needed.

Caveat: `PortalDesigns.txt` predates the v1.5.0 update. The game's own pads did not change in the later object dump (same actors, same
Niagara systems loaded), but the per-pad values have not been read again since.

## 1. How portal looks work today

### 1.1 What a "look" is in the game

A teleporter (`BP_Teleporter_ParentBP`, child `BP_Teleporter_HomeWorld`) has these visual parts, all components of the pad actor:

| Part | Component / variable | What sets it |
|---|---|---|
| Particle effect ("the look") | `ParticleLoop` (NiagaraComponent), its asset a `NiagaraSystem` under `/Game/Particles/Niagara_Portal*` | set per pad in the map |
| Window image inside the ring | the Niagara user parameter `User.PortalTexture` (a material) | the Blueprint calls `SetVariableMaterial("User.PortalTexture", PortalTexture)` from its own `PortalTexture` variable (a MaterialInterface); default material `M_WorldPortal` |
| Pad light | `PointLight` (PointLightComponent), `LightColor` | set per pad in the map |
| Hum | `PortalHumLoop` (AudioComponent), `portal_loop_default`; `QuieterPortal` flag | Blueprint |
| Label | `DestText` (TextRenderComponent) | Blueprint (shows the IDs) |

The window materials: `M_WorldPortal` (master: a ray-traced sphere showing a cube map `PortalImage`, default texture `T_WorldPortal`, with
`T_Nebula` and a ripple) and six instances that each put a destination's cube map into `PortalImage`:

| Material instance | Cube map | Destination it pictures |
|---|---|---|
| `M_WorldPortal_HCabin` | `TC_H_Cabin` | the Cabin |
| `M_WorldPortal_AnteA` | `TC_Portal_Anteverse_A` | Far Garden |
| `M_WorldPortal_AnteC` | `TC_Portal_Anteverse_A` (the same cube map as AnteA) | Village Den da'ko Yeer, by its name |
| `M_WorldPortal_Fog` | `TC_Portal_Fog` | Flathill |
| `M_WorldPortal_Warehouse` | `TC_Portal_Warehouse` | Furniture Store |
| `M_WorldPortal_Offices` | `TC_Portal_Offices` | the Facility offices (return pads) |

Cube maps with no instance: `TC_Portal_Alps` (Voussoir), `TC_Portal_Torii`, plus test ones (`TC_OfficeDesat`, `TC_OrangeGlow`, `TC_Vehicular*`,
`TC_ZagTest`). Which pads really carry these materials is **not known**: the PoC dump read `PortalTexture` as invalid on every pad (maybe the
read was wrong, maybe the materials are set elsewhere). See the optional survey in section 3.

Niagara systems that take `User.PortalTexture` (the lab's in-game test): Default Portal, Blueverse, Greenverse, Redverse, Dark, Fog, SnowFlurry,
SunDisk, Tiny. The others ignore it (colours and images baked in).

### 1.2 What the hub does

| Where | What |
|---|---|
| `config.lua`, per portal | `design` = a Niagara system's full path (optional); `lightColor = { r, g, b }` (0 to 1); `lightBrightness` (multiplier of the pad's own intensity). |
| `config.lua`, global | `hideEmitters = { [design path] = { "part", ... } }`: parts switched off, **per look, for every portal using it** (never `portal` / `portalmap`). |
| `main.lua` `DEFAULT_DESIGN` (line 17) | `/Game/Particles/Niagara_Portal.Niagara_Portal`, used when a portal has no `design`. **The hub has no per-world default**: every portal without a `design` in config.lua gets the plain look, whatever its world. |
| `main.lua` `apply_design` (line 381) | `StaticFindObject(path)`, else `LoadAsset(path)`; then `ParticleLoop:SetAsset(sys, true)`, `Activate(true)`; then `SetEmitterEnable(part, false)` for each hidden part. It never sets `User.PortalTexture`. |
| `main.lua` `apply_light` (line 411) | only when `lightColor` or `lightBrightness` is given: `PointLight:SetLightColor({R,G,B,A=1}, true)` (sRGB flag on) and `SetIntensity(Intensity * brightness)`. Otherwise the pad keeps the Blueprint's light. |

Who gets which look:

| Pad | Look | Light |
|---|---|---|
| Hub portal in a slot (`spawn_entry`) | its config `design`, else `DEFAULT_DESIGN` | its config light |
| Mode-4 manual portal (`spawn_manual`, the portal's own MHE) | the hub portal's `design` | the hub portal's light |
| **Standalone MHE** (`spawn_mhes`, line ~2208) | **always `DEFAULT_DESIGN`** | Blueprint default |
| Failsafe Exit | hidden | - |
| Custom world arrival pad, vignette exit pad, DLC test pad | `DEFAULT_DESIGN` | Blueprint default |
| Client mode (`style_host_pad`) | the client's own `design` + light, on a host portal in a slot whose destination matches the client's entry; MHEs and manual portals are not styled on a client (they keep the Blueprint look there) | same |

Looks are local component settings: a host's look never reaches a client (CRD-027).

### 1.3 What the editor does

`hubdata.py` holds every look the editor offers (`DESIGN_NAMES`, 32 systems; `Rift_BlueFade` left out because it fades), each look's named
parts (`DESIGN_PARTS`, read from the effect files), the ring tint on a slot card (`LOOK_TINTS`, hand-picked hex), `OVERSIZED_LOOKS` (Door,
NightRDoor_2, labelled "(Oversized)"), and per world a **look** (column 5 of `DESTINATIONS`). Picking a world in a slot writes that look as
the portal's `design` (`PortalHubConfig.py` ~line 1244); the light is not set from the world. The PORTAL LOOK drop-down changes it; Effects
edits `hideEmitters`; PAD LIGHT offers "Default" (writes nothing), the seven `LIGHT_PRESETS` and a colour picker (stored as hex, written as
0-1 floats).

### 1.4 How the designs were made

All by hand, from the game's own files; nothing is generated at run time:

- the list of systems: the asset names under `Content/Particles` (`portal-designs.md`);
- the parts of each: the emitter names inside each effect file;
- each world's look: the PoC's design dump (`PortalDesigns.txt`, the Facility-side entrance pad of each world) where an entrance exists;
  where none exists (Night Realm, Canaan), by name (`NightRDoor_2`, `Salem` exist as systems, but no Facility pad in the dump uses them);
- the editor's ring tints and light presets: picked by eye.

Stale parts of the old `portal-designs.md`: it still mentions `designScales`, `scale`, `width`, `height` and `User.Color`; none of these is read by
the hub any more (sizing had no visible effect; only `hideEmitters`, `lightColor`, `lightBrightness` remain).

## 2. Every portal world and its look

"Game's entrance" = the Facility pad that leads into the world, from `PortalDesigns.txt` (light as the game's 0-255 colour, then as the
config's 0-1 value). The game's ordinary pads all carry `255,61,252`, the Blueprint's default light; a world with its own colour is marked.
**Hub default** is the same for every row today: `Niagara_Portal` unless config.lua names a design (section 1.2).

| # | World (pad id) | Editor look now | Game's entrance: look, light | Suggestion (LuciDin decides) |
|---|---|---|---|---|
| 1 | Far Garden (`anteverse_a_start`) | **Default** | `Niagara_Portal`, default light | Greenverse (or Default + the AnteA window, if the survey shows the game uses it) |
| 2 | Flathill (`fog_start`) | Fog | Fog, `255,233,254` (1.00, 0.91, 1.00) | keep Fog; take the game's light |
| 3 | The Train (`train_start`) | **Default** | `Niagara_Portal`, default light | Friendly Orange |
| 4 | Furniture Store (`warehouse_start`) | Door (oversized) | Door, default light | keep Door |
| 5 | The Mycofields (`anteverse_b_start`) | **Default** | `Niagara_Portal`, default light | Friendly Lime |
| 6 | The Night Realm (`nightrealm_start_A`) | NightRDoor_2 (oversized) | no Facility entrance in the dump | keep |
| 7 | Canaan (`salem_begin`) | Salem | no Facility entrance in the dump | keep |
| 8 | Voussoir (`alps_start`) | SnowFlurry | SnowFlurry, default light | keep |
| 9 | Village Den da'ko Yeer (`anteverse_c_start`) | Blueverse | Blueverse, `103,246,255` (0.40, 0.96, 1.00) | keep; take the game's light |
| 10 | Shadowgate (`shadowgate_start`) | Shadowgate2 | Shadowgate2, `145,0,255` (0.57, 0.00, 1.00) | keep; take the game's light |
| 11 | Praetorium (`INQ_Entrance`) | Friendly | Friendly (`INQ_EarlyReturn`), `255,229,99` (1.00, 0.90, 0.39) | keep; take the game's light |
| 12 | Botanical Wing (Present) (`botanical_present_01`) | Botanical Green | Botanical Green, `33,255,0` (0.13, 1.00, 0.00) | keep; take the game's light |
| 13 | GATE Arch Defense Facility (`wall_start`) | **Default** | `Niagara_Portal`, default light | Dark |
| 14 | Botanical Wing (Future) (`botanical_future_01`) | Botanical Red | Botanical Red, `255,74,0` (1.00, 0.29, 0.00) | keep; take the game's light |
| 15 | Albatross (`island_start`) | **Default** | `Fracture_Exit`: no particle system | SunDisk |
| 16 | Rise (`rise_start`) | **Default** | `Niagara_Portal`, default light | Friendly Purple |
| 17 | North Pole (`V_Snowglobe_Start`) | **Default** | no Facility entrance in the dump | Friendly White |
| 18 | Dunkeltaler Forest (`signal_start`) | Friendly Red | Friendly Red, `255,39,57` (1.00, 0.15, 0.22) | keep; take the game's light |
| 19 | Royal Range (IS-0083) (`VWinter_Start`) | **Default** | no Facility entrance in the dump | Friendly Blue |
| 20 | The World in the Mirror (`mirrorworld_start`) | **Default** | `mirrorworld_entrance`: no particle system, light 0,0,0 (the mirror is the portal) | Friendly Glitched |
| 21 | The Pool Room (`tile_entrance`) | **Default** | no Facility entrance in the dump | Friendly Cyan |
| 22 | Some Distant Shore (`DistantShore`) | **Default** | no Facility entrance in the dump | Rift |
| H | Cabin (home, `H_Cabin_Start`) | not a destination (B-3) | Blueverse, `160,206,255` (0.63, 0.81, 1.00) | Blueverse + that light |
| H | Stone Garden (home, DLC) | not a destination (A-1) | Garden, default light | Garden |
| H | Torii (home, DLC) | not a destination (A-2) | Torii, default light | Torii |

**Still on "default" in the editor: 11 worlds** (Far Garden, The Train, The Mycofields, GATE Arch Defense Facility, Albatross, Rise, North Pole,
Royal Range, The World in the Mirror, The Pool Room, Some Distant Shore). **In the hub: all 22** whenever config.lua has no `design`.

The suggestions keep every world's look different from its neighbours on the story list and avoid the oversized and fading looks. The lights
in "take the game's light" are the game's own colours for those entrances; worlds with the default light would keep the pad's own light
(no `lightColor`) unless LuciDin picks one. Unused looks after the suggestions: Friendly (plain, Praetorium's), Friendly Black, Brown, Green,
Pink, Yellow, Redverse, Tiny.

Other game pads with their own looks (not destinations; for ideas): the Sydyk shortcut pads (Friendly, `255,249,150`), the overgrowth pair
`fusion_overgrowth` / `plant_overgrowth` (Greenverse, `26,255,98`), `shadowgate_start` inside Shadowgate (Dark), a few unnamed pads
(Friendly, `236,224,107`).

## 3. The Cabin entrance (B-3)

From the PoC dump (`BP_Teleporter_HomeWorld_C_6`, `H_Cabin_Entrance` -> `H_Cabin_Start`, gated by the story flag `SnowglobeComplete`):

| Part | Value |
|---|---|
| Particle system | `/Game/Particles/Niagara_Portal_Blueverse.Niagara_Portal_Blueverse` (the Cabin's start pad uses it too) |
| Pad light | `160,206,255`, a pale ice blue: in config terms `lightColor = { 0.63, 0.81, 1.00 }`; it is the only entrance in the Facility with this colour |
| Hum | `portal_loop_default`, `QuieterPortal = true` (all three home portals) |
| Window material | `PortalTexture` read as invalid. The game has `M_WorldPortal_HCabin` (cube map `TC_H_Cabin`), clearly made for this portal; whether the pad uses it is not proven |

So the Cabin's design is **Blueverse with an ice-blue light**, probably with the Cabin window. Its neighbours for comparison: Stone Garden =
Garden, Torii = Torii (both with the default light).

**Optional survey** (only if LuciDin wants the window settled; not needed for the design defaults): extend the probe's existing survey key `]`
(`mod/CordonaProbe`, already lists every pad in the portal room with its look) to also log `PortalTexture` and `PointLight.LightColor` for each
pad. No new key. Read-only. Run it in the portal room on CordonaCorp or Mod Testing:

| Key | Run it in | What it logs |
|---|---|---|
| `]` (probe survey, extended) | the portal room, CordonaCorp or Mod Testing | per pad: ID, destination, look, `PortalTexture` (material path), light colour; for B-3 this shows whether the Cabin uses `M_WorldPortal_HCabin` |

Nothing installed for it yet; installing asks the dispatcher first, and the `manual_exits.lua` question (installed 14 Nov North Pole spot vs
the repo's 13 Nov one) goes to LuciDin before any install.

## 4. MHEs and "always the parent portal's design"

### 4.1 Today

| MHE kind | Leads to | Look today |
|---|---|---|
| Mode-4 manual portal (`hub_A3_manual`, ...) | its hub portal | the hub portal's design and light (already "the parent's") |
| Standalone MHE, world has a hub portal (`first[w]`) | that first hub portal | **`DEFAULT_DESIGN`, default light** |
| Standalone MHE, world has no hub portal | the Failsafe Exit | **`DEFAULT_DESIGN`, default light** |
| Home MHE (`H_<X>_Start` key) | the game's `H_<X>_Entrance` | **`DEFAULT_DESIGN`, default light** (none recorded yet) |

### 4.2 What the request needs

"Parent portal" = the portal the MHE leads back to: the first hub portal to that world; for a home, the game's own home portal; for a world
not in the config, the portal that world *would* get.

| Need | How |
|---|---|
| **Data:** a per-world default look the hub can read without config.lua | a new shipped module `mod/PortalHub/Scripts/looks.lua` (like `slots.lua`, open for players to edit): `[arrival pad id] = { design = "...", lightColor = { r, g, b } }` for the 22 worlds and the 3 homes (section 2, once LuciDin has picked). This is also item 1's "default go-to design for portals that are otherwise undefined". |
| Hub portal look | `design = p.design or Looks[dest].design or DEFAULT_DESIGN`, light likewise (config wins, then the world's default). Custom worlds have no entry (`DEFAULT_DESIGN`), unless their loader Blueprint later gets a `Design` setting. |
| Standalone MHE look | in `spawn_mhes`: the entry behind `first[w]` (its design and light, as resolved above), else `Looks[w]`, else `DEFAULT_DESIGN`; then `apply_light`. Needs `first` to keep the entry, not only its id. |
| Home MHE | `Looks["H_<X>_Start"]`, or read the game's `H_<X>_Entrance` pad's `ParticleLoop.Asset` and light at spawn (a live copy; the Facility pads are always loaded). The table is simpler and testable; the live read follows the game if it changes. |
| Client mode | a client could style MHE pads too (they are `hub_mhe_<world>`, found by ID), with the same resolution from its own config and `looks.lua`. Optional; today a client sees MHEs with the Blueprint look. |
| Hub's main-chunk locals | 13 free (limit 200). Use one at most: `local Looks = require("looks")`, or none by putting it in an existing table (`state.looks`). New helpers as table fields (as `state.unregister_hook`, `DLC.*`). |
| Packaging and install check | add `looks.lua` to the release builder's allowlist (`tools/release/build_release.py`) and to `install_check.py`'s `HUB_SCRIPTS` (main.lua will `require` it; a missing file must fail soft: `pcall(require, "looks")`, empty table). |
| Editor | `hubdata.DESTINATIONS`' look column becomes the same data: either the editor reads `looks.lua` beside `config.lua` (like `manual_exits.lua`) with `hubdata` as fallback, or a test fails when the two disagree. Picking a world could also set the default light. Open choice for LuciDin: keep writing `design` into every entry (as now), or write it only when it differs from the world's default (leaner configs that follow later default changes). The HUB EXITS tab could show each MHE's look. |
| Tests | `test_hub_exits.py` / a new `test_hub_looks.py`: standalone MHE takes the hub portal's design and light; with no hub portal, the `looks.lua` default; home MHE the home's; config design wins over `looks.lua`; missing `looks.lua` falls back to `DEFAULT_DESIGN`; a client styles MHEs (if built). Editor: look table agrees with `looks.lua`. |

The shipped presets are unaffected (their entries already name a design); blank installs gain the per-world looks.

## 5. Revisit: possible improvements (for LuciDin; none needed for 1.0)

| Idea | Note |
|---|---|
| Window image (`User.PortalTexture`) | a `texture` field per look: the hub would call `ParticleLoop:SetVariableMaterial(FName("User.PortalTexture"), material)` after `SetAsset` (the lab proved it works on 9 looks). Ready-made: the 6 `M_WorldPortal_*` instances. Worth it after the survey shows the game's own use. A world with only a cube map (Voussoir, Torii) would need a dynamic material instance (untested). |
| Per-portal hidden parts | `hideEmitters` is per look, global. A per-portal `hide = { ... }` would let two portals share a look but differ. |
| Oversized looks | Door and NightRDoor_2 cannot be shrunk (sprite sizes are fixed inside the emitters). They are the game's own looks for those worlds, so keep them, labelled. |
| Old note | `findings/portal-designs.md` still describes `designScales` and sizing; mark it superseded by this note when the build lands. |
