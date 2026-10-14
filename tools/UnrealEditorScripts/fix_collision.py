# Unreal Editor Python script: make the SELECTED static meshes walkable (collision follows their real surfaces).
#
# Why: importing an OBJ / FBX usually generates a "simple" collision shape, often a convex hull around the whole object. A convex hull
# has no hollow inside, so a room, a street or a building reads as one solid block you cannot enter. This script removes that generated
# collision and sets Collision Complexity to "Use Complex Collision As Simple", so the mesh's own triangles are the collision. It also ticks
# "Double Sided Geometry", because imported floors and walls are often one-sided and the character would otherwise fall into or hover over them.
#
# Status: written for Unreal Engine 5.4's Python API but not yet run in the editor (the project currently fixes collision by hand), so if it
# errors, set Collision Complexity by hand (Static Mesh Editor > Details > Collision Complexity) and report it.
#
# How to use (editor only; it changes your project's assets, not the game):
#   1. Edit > Plugins: enable "Python Editor Script Plugin" and "Editor Scripting Utilities", restart the editor (one time).
#   2. In the Content Browser, select the static meshes to fix.
#   3. Tools > Execute Python Script... and pick this file.
# Check the result with Show > Collision in the viewport (the wireframe should follow the walls, not a big box).
# Note: complex-as-simple is exact but heavier than simple shapes; for big levels you walk around inside it is the right trade.

import unreal

subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
fixed = 0
for asset in unreal.EditorUtilityLibrary.get_selected_assets():
    if not isinstance(asset, unreal.StaticMesh):
        continue
    subsystem.remove_collisions(asset)                     # drop the generated hull / box
    body = asset.get_editor_property('body_setup')
    body.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    try:                                                   # triangles then collide from both sides (imported floors are often one-sided)
        body.set_editor_property('double_sided_geometry', True)
    except Exception as err:
        unreal.log_warning('could not set Double Sided Geometry on %s: %s' % (asset.get_name(), err))
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    fixed += 1
    unreal.log('collision fixed: ' + asset.get_name())
unreal.log('fix_collision: %d static mesh(es) set to complex-as-simple' % fixed)
