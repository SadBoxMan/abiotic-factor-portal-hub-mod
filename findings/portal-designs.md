# Portal designs

Values for the design field in config.lua (Niagara particle systems found in the game's files; not all verified).

```lua
design = "/Game/Particles/Niagara_Portal.Niagara_Portal"
design = "/Game/Particles/Niagara_Portal_Blueverse.Niagara_Portal_Blueverse"
design = "/Game/Particles/Niagara_Portal_Botanical_Green.Niagara_Portal_Botanical_Green"
design = "/Game/Particles/Niagara_Portal_Botanical_Red.Niagara_Portal_Botanical_Red"
design = "/Game/Particles/Niagara_Portal_Dark.Niagara_Portal_Dark"
design = "/Game/Particles/Niagara_Portal_Door.Niagara_Portal_Door"
design = "/Game/Particles/Niagara_Portal_Fog.Niagara_Portal_Fog"
design = "/Game/Particles/Niagara_Portal_Friendly.Niagara_Portal_Friendly"
design = "/Game/Particles/Niagara_Portal_Friendly_Black.Niagara_Portal_Friendly_Black"
design = "/Game/Particles/Niagara_Portal_Friendly_Blue.Niagara_Portal_Friendly_Blue"
design = "/Game/Particles/Niagara_Portal_Friendly_Brown.Niagara_Portal_Friendly_Brown"
design = "/Game/Particles/Niagara_Portal_Friendly_Cyan.Niagara_Portal_Friendly_Cyan"
design = "/Game/Particles/Niagara_Portal_Friendly_Glitched.Niagara_Portal_Friendly_Glitched"
design = "/Game/Particles/Niagara_Portal_Friendly_Green.Niagara_Portal_Friendly_Green"
design = "/Game/Particles/Niagara_Portal_Friendly_Lime.Niagara_Portal_Friendly_Lime"
design = "/Game/Particles/Niagara_Portal_Friendly_Orange.Niagara_Portal_Friendly_Orange"
design = "/Game/Particles/Niagara_Portal_Friendly_Pink.Niagara_Portal_Friendly_Pink"
design = "/Game/Particles/Niagara_Portal_Friendly_Purple.Niagara_Portal_Friendly_Purple"
design = "/Game/Particles/Niagara_Portal_Friendly_Red.Niagara_Portal_Friendly_Red"
design = "/Game/Particles/Niagara_Portal_Friendly_White.Niagara_Portal_Friendly_White"
design = "/Game/Particles/Niagara_Portal_Friendly_Yellow.Niagara_Portal_Friendly_Yellow"
design = "/Game/Particles/Niagara_Portal_Garden.Niagara_Portal_Garden"
design = "/Game/Particles/Niagara_Portal_Greenverse.Niagara_Portal_Greenverse"
design = "/Game/Particles/Niagara_Portal_NightRDoor_2.Niagara_Portal_NightRDoor_2"
design = "/Game/Particles/Niagara_Portal_Redverse.Niagara_Portal_Redverse"
design = "/Game/Particles/Niagara_Portal_Rift.Niagara_Portal_Rift"
design = "/Game/Particles/Niagara_Portal_Salem.Niagara_Portal_Salem"
design = "/Game/Particles/Niagara_Portal_Shadowgate2.Niagara_Portal_Shadowgate2"
design = "/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"
design = "/Game/Particles/Niagara_Portal_SunDisk.Niagara_Portal_SunDisk"
design = "/Game/Particles/Niagara_Portal_Tiny.Niagara_Portal_Tiny"
design = "/Game/Particles/Niagara_Portal_Torii.Niagara_Portal_Torii"
```



## Tuning notes (from in-game testing)
- `Niagara_Portal_Rift_BlueFade` fades away after a moment, so it is left out of the editor's list.
- Too big (resize via `designScales` in config.lua): `Door`, `NightRDoor_2` (oversized); `Salem`, `Shadowgate2`, `SnowFlurry` (slightly oversized).
- `SnowFlurry` also has an accretion-disk part. Its named parts are Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02 and Swirl;
  switch one off with `hideEmitters` in config.lua.

## Effects (parts) and sizing - what works
- Every look is made of named parts (Niagara emitters), e.g. SnowFlurry = Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02, Swirl.
  The editor's Effects button lists them per look; unticked parts are saved in config.lua's hideEmitters (untested in game).
- Resizing the effect's component (scale / width / height / designScales) is applied without error but showed no visible change on the Door
  look. The sprite-based looks size their sprites with a fixed `SpriteSize` inside each emitter and expose no size parameter or owner-scale
  input, so the component's scale has nothing to act on. It may still affect mesh-based parts (e.g. the SM_Portal mesh in the Friendly looks).
- Material swap: SetVariableMaterial("User.PortalTexture", material) works on looks that expose that parameter: Default Portal, Blueverse,
  Greenverse, Redverse, Dark, Fog, SnowFlurry, SunDisk, Tiny. It is accepted but ignored by the others.

## Colour and effect experiments (in-game results)
- Pad light colour (`PointLight:SetLightColor`) works on every look and visibly tints the portal and its surroundings. Now a config option: `lightColor`, `lightBrightness`.
- Effect colour: only the Rift looks declare a colour setting (`User.Color`); setting it was accepted but no visible change was seen. Every other look has colours baked in.
- Overlay: spawning a second Niagara effect on a hub portal (e.g. SnowFlurry with only Swirl on) works. Spawned standalone effects are owned by the world settings
  object and must be removed with K2_DestroyComponent.
- Level streaming from Lua: `LevelStreamingDynamic:LoadLevelInstance(world, levelName, location, rotation, outSuccess, nameOverride, class, tempPackage)` exists;
  `outSuccess` is an OUT parameter and must be passed as a table ({}). A trailing nil does not count as an argument.

## Level streaming from Lua (tested)
- `LevelStreamingDynamic:LoadLevelInstance` has the signature (WorldContextObject, LevelName: Str, Location, Rotation, bOutSuccess: Bool OUT,
  OptionalLevelNameOverride: Str, OptionalLevelStreamingClass: Class, bLoadAsTempPackage: Bool) -> LevelStreamingDynamic (UE4SS counts the return value, so 9).
  The out flag must be passed as a table ({}). The game's own `LevelStreamingCustom:LoadStreamLevel(WorldContext, LevelName, bMakeVisibleAfterLoad,
  bShouldBlockOnLoad, bSuccess OUT, bAlreadyLoaded OUT)` takes the level name the same way.
- Every call that passes a text argument failed inside UE4SS 3.0.1's `push_strproperty` with an empty error, with empty and non-empty strings and with
  and without the class argument. No level was streamed in (LevelStreamingDynamic count stayed at 59). So loading a level by name from Lua is NOT yet
  possible with plain Lua strings; whether an FString value can be passed is the open question.
