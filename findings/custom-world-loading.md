# Loading a custom level from Lua: the loader-actor technique

`LevelStreamingDynamic:LoadLevelInstance` and the game's own `LevelStreamingCustom:LoadStreamLevel` cannot be called from Lua in UE4SS 3.0.1:
any call that passes a text argument fails inside `push_strproperty` (see portal-designs.md). The way around it is to avoid passing text at all.

## The technique
1. **Ship a small "loader" actor Blueprint in the world's pak.** Its job is to stream the custom level in. The level path is baked into the
   Blueprint, so Lua never has to pass a text argument.
2. **Find the Blueprint class using names only:** `AssetRegistryHelpers:GetAsset({ PackageName = FName(...), AssetName = FName(...) })`.
   FName values pass fine from Lua.
3. **Spawn the loader** with `world:SpawnActor(class, location, rotation)` at a far-away "origin", so the level cannot overlap anything.
4. **Wait for the level** by polling `world.StreamingLevels` for the entry whose `PackageNameToLoad:ToString()` equals the map path (reading text works;
   only passing it in fails), calling `GameplayStatics:FlushLevelStreaming(world)` every few ticks, until `IsLevelVisible()` is true.
5. **Send the player** to a point at `origin + localSpawn`.

## What this means for the hub
- The hub can already send a player to any teleporter pad. If the hub spawns a teleporter pad at `origin + localSpawn` (facing into the world), a hub
  portal can point at it like at any arrival pad, and the existing return routing works unchanged.
- Per-world data a config would need: loader asset path and class, level path, origin, local spawn (x, y, z, yaw).
- Open choice: load at world start, on approach, or on first use (the pad-use hook cannot wait, so on-use needs a pre-trigger or a loading screen).

## Where the pak must go (tested)
- On this Steam install the game mounts patch paks only from the top level of `AbioticFactor/Content/Paks`. A pak placed in a `~mods` subfolder was
  never mounted: the game log lists "Found Pak file ... attempting to mount" only for the files directly in `Paks`, and no session log ever mentioned `~mods`.
  Put the `_P` triplet (`.pak`, `.ucas`, `.utoc`) straight into `Content/Paks`.
- The hub's log says exactly this when it happens: `the world's pak is not installed (no <LoaderClass>)`, and the hub portals to that world stay off.

## Status
Tested in game with a real, finished world pak: the hub spawned the loader, waited for the level to become visible, spawned the arrival pad at
`origin + arrive`, switched the hub portal on, and the portal put the player in the right spot. The hub's `worlds` config section drives it.

## Public sources for each building block
- Spawning an actor class from Lua: UE4SS Lua API, `UWorld:SpawnActor(UClass, FVector, FRotator)`
  <https://docs.ue4ss.com/dev/lua-api/classes/uworld.html> (it must be the Blueprint's generated class, the `_C` one, not the asset).
- Loading a Blueprint asset by path from Lua: UE4SS `LoadAsset`, game thread only
  <https://docs.ue4ss.com/lua-api/global-functions/loadasset.html>, then `StaticFindObject("<package>.<ClassName>_C")`.
- Name-only asset lookup (the fallback the hub also tries): Unreal `UAssetRegistryHelpers::GetAsset(FAssetData)`
  <https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/AssetData/GetAsset>.
- Streaming a level from a Blueprint (what a loader actor does inside the pak): the **Load Level Instance (by Name)** node, which loads a level at a world
  location and rotation and does not need the level to be in a persistent map's Levels list (the map must be listed in Packaging > "List of Maps to Include")
  <https://dev.epicgames.com/documentation/unreal-engine/BlueprintAPI/LevelStreaming/LoadLevelInstance_byName>. Epic's "Loading and Unloading Levels Using Blueprints" covers only Load Stream Level, which does need a registered sublevel
  <https://dev.epicgames.com/documentation/unreal-engine/loading-and-unloading-levels-using-blueprints-in-unreal-engine>.
- Waiting for a streamed level: `ULevelStreaming` (the streaming object, with `PackageNameToLoad` and a visibility query)
  <https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/ULevelStreaming> and the blocking `UWorld::FlushLevelStreaming`
  <https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UWorld/FlushLevelStreaming>.
- Patch-pak packaging and the `_P` naming: the community guide linked from the README.
Notes: the documentation does not show the asset-registry call being made from Lua, which is why the hub tries `LoadAsset` first. Every piece above is
ordinary, documented Unreal / UE4SS functionality; the loader actor is simply a Blueprint that uses Epic's documented level-streaming nodes.

