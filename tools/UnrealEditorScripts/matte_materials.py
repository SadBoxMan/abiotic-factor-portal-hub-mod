# Unreal Editor Python script: make the SELECTED materials matte and opaque (no shine).
#
# Why: materials made by importing an OBJ / FBX copy the file's specular values and often come out glossy, and sometimes Translucent.
# This script wires constants into the Metallic, Specular and Roughness inputs (replacing whatever was connected there) and sets the
# blend mode to Opaque (or Masked) with Two Sided on. Base Color and Opacity Mask connections are left exactly as they are.
#
# Status: tested in Unreal Engine 5.4 and working.
#
# How to use (editor only; it changes your project's assets, not the game):
#   1. Edit > Plugins: enable "Python Editor Script Plugin" and "Editor Scripting Utilities", restart the editor (one time).
#   2. In the Content Browser, select the materials to change (filter by type Material, then Ctrl+A).
#   3. Edit the settings just below if you like, then Tools > Execute Python Script... and pick this file.
# Materials that need cut-out transparency (leaves, fences): set MASKED = True and select just those. Masked materials still need
# their Opacity Mask wired in the graph (texture alpha, or a Desaturation node with a lowered Opacity Mask Clip Value).

import unreal

METALLIC = 0.0      # 0 = not metal
SPECULAR = 0.1      # low = less shine on non-metals (0.5 is the engine default)
ROUGHNESS = 0.95    # high = matte, 1.0 = completely rough
MASKED = False      # True: blend mode Masked instead of Opaque
TWO_SIDED = True

mel = unreal.MaterialEditingLibrary


def constant(material, value, x, y):
    node = mel.create_material_expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property('r', value)
    return node


changed = 0
for asset in unreal.EditorUtilityLibrary.get_selected_assets():
    if not isinstance(asset, unreal.Material):
        continue
    mel.connect_material_property(constant(asset, METALLIC, -600, 700), '', unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(constant(asset, SPECULAR, -600, 800), '', unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(constant(asset, ROUGHNESS, -600, 900), '', unreal.MaterialProperty.MP_ROUGHNESS)
    asset.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if MASKED else unreal.BlendMode.BLEND_OPAQUE)
    asset.set_editor_property('two_sided', TWO_SIDED)
    mel.recompile_material(asset)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    changed += 1
    unreal.log('matte: ' + asset.get_name())
unreal.log('matte_materials: %d material(s) updated' % changed)
