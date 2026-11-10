# Unreal Editor Python script: fix the SELECTED materials in bulk (matte surface, Opaque or Masked, Two Sided, optional no-glow).
#
# Why: materials created by importing an OBJ / FBX copy the file's settings. They often come out shiny (specular above 0, low roughness),
# sometimes Translucent (which sorts badly and looks ghostly), and textures that need holes (leaves, fences, grass) are not masked. This
# script fixes all of that for every selected material in one go. Pick what you want in the settings just below:
#   * MATTE:  wires constants into Metallic, Specular and Roughness (replacing whatever was connected there), so nothing is shiny.
#   * BLEND:  "opaque" for solid things, "masked" for cut-out transparency. With "masked" the script also connects the Opacity Mask for
#             you (MASK_FROM = "alpha": the texture's alpha channel; "black": black pixels become transparent).
#   * TWO_SIDED and EMISSIVE_OFF: see the settings.
# Base Color is never touched, and an Opacity Mask that is already connected is left alone, so running the script twice is harmless (it only
# leaves a few unused constant nodes behind).
#
# Status: the matte / opaque part is tested in Unreal Engine 5.4 and working. The Masked part (blend mode and Opacity Mask wiring) is written
# for the 5.4 Python API but has not been run in the editor yet; if it errors, send the Output Log line.
#
# How to use (editor only; it changes your project's assets, not the game):
#   1. Edit > Plugins: enable "Python Editor Script Plugin" and "Editor Scripting Utilities", restart the editor (one time).
#   2. In the Content Browser, select the materials to change (filter by type Material, then Ctrl+A). Solid and cut-out materials need
#      different settings, so run it once for each group.
#   3. Edit the settings just below, then Tools > Execute Python Script... and pick this file.
# Only Materials are changed. Material Instances are skipped with a warning: change their parent material instead.
# Afterwards, if thin edges of a masked material look too thick or too thin, adjust its "Opacity Mask Clip Value" (CLIP sets the first guess).

import unreal

# ---- Surface (shine) --------------------------------------------------------------------------------------------------------------------
MATTE = True            # True: wire the three constants below. False: leave Metallic, Specular and Roughness exactly as they are.
METALLIC = 0.0          # 0 = not metal (wood, stone, cloth, plastic), 1 = bare metal
SPECULAR = 0.0          # 0 = no highlight at all. The engine default is 0.5; imported materials often arrive above 0
ROUGHNESS = 1.0         # 1 = completely matte, 0 = mirror. Real surfaces are usually 0.4 to 0.9
EMISSIVE_OFF = False    # True: also wire black into Emissive Color, to stop a material glowing on its own.
                        # Leave False for things that should glow (lights, screens, lava).

# ---- Transparency -----------------------------------------------------------------------------------------------------------------------
BLEND = "opaque"        # "opaque" = solid, "masked" = cut-out holes (leaves, fences, grass). Never Translucent: it sorts badly.
MASK_FROM = "alpha"     # only for BLEND = "masked":  "alpha" = the texture's alpha channel is the mask,
                        #                             "black" = black pixels become transparent (for textures without alpha)
CLIP = 0.3333           # only for BLEND = "masked": Opacity Mask Clip Value. Mask values below this are cut away.
                        # For MASK_FROM = "black" try 0.05 to 0.1.
TWO_SIDED = True        # render both faces (needed for thin walls and leaves; harmless for solid meshes)

mel = unreal.MaterialEditingLibrary


def constant(material, value, x, y):
    node = mel.create_material_expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property('r', value)
    return node


def make_matte(material):
    mel.connect_material_property(constant(material, METALLIC, -600, 700), '', unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(constant(material, SPECULAR, -600, 800), '', unreal.MaterialProperty.MP_SPECULAR)
    mel.connect_material_property(constant(material, ROUGHNESS, -600, 900), '', unreal.MaterialProperty.MP_ROUGHNESS)


def switch_emissive_off(material):
    black = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -600, 1000)
    black.set_editor_property('constant', unreal.LinearColor(0.0, 0.0, 0.0, 1.0))
    mel.connect_material_property(black, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)


def find_texture_node(material, node, seen, depth=0):
    """Walk back from a node through its inputs until a texture sample is found (or give up)."""
    if node is None or depth > 8 or node in seen:
        return None
    seen.add(node)
    if isinstance(node, unreal.MaterialExpressionTextureSample):       # also covers texture-sample parameters
        return node
    for upstream in mel.get_inputs_for_material_expression(material, node):
        found = find_texture_node(material, upstream, seen, depth + 1)
        if found:
            return found
    return None


def first_texture_node(material):
    for prop in (unreal.MaterialProperty.MP_BASE_COLOR, unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        start = mel.get_material_property_input_node(material, prop)
        found = find_texture_node(material, start, set())
        if found:
            return found
    return None


def wire_opacity_mask(material):
    """Connect the Opacity Mask. Returns 'kept' (already connected), 'no texture' (nothing to wire) or 'wired'."""
    if mel.get_material_property_input_node(material, unreal.MaterialProperty.MP_OPACITY_MASK) is not None:
        unreal.log('fix_materials: %s already has an Opacity Mask connected; left as it is' % material.get_name())
        return 'kept'
    tex = first_texture_node(material)
    if tex is None:
        unreal.log_warning('fix_materials: no texture found in %s; Masked is set, but connect its Opacity Mask by hand' % material.get_name())
        return 'no texture'
    if MASK_FROM == "black":
        desat = mel.create_material_expression(material, unreal.MaterialExpressionDesaturation, -300, 1100)
        mel.connect_material_expressions(tex, 'RGB', desat, 'Input')
        mel.connect_material_property(desat, '', unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        mel.connect_material_property(tex, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    return 'wired'


def main():
    if BLEND not in ("opaque", "masked"):
        raise ValueError('fix_materials: BLEND must be "opaque" or "masked", not %r' % (BLEND,))
    if MASK_FROM not in ("alpha", "black"):
        raise ValueError('fix_materials: MASK_FROM must be "alpha" or "black", not %r' % (MASK_FROM,))
    masked = (BLEND == "masked")
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        unreal.log_warning('fix_materials: nothing is selected. Select materials in the Content Browser first.')
        return
    changed = 0
    not_materials = []
    unwired = []
    for asset in selected:
        if not isinstance(asset, unreal.Material):
            not_materials.append(asset.get_name())
            continue
        if MATTE:
            make_matte(asset)
        if EMISSIVE_OFF:
            switch_emissive_off(asset)
        asset.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
        asset.set_editor_property('two_sided', TWO_SIDED)
        if masked:
            asset.set_editor_property('opacity_mask_clip_value', CLIP)
            if wire_opacity_mask(asset) == 'no texture':
                unwired.append(asset.get_name())
        mel.recompile_material(asset)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        changed += 1
        unreal.log('fix_materials: ' + asset.get_name())
    if not_materials:
        unreal.log_warning('fix_materials: skipped %d selected asset(s) that are not Materials (Material Instances? change their parent '
                           'material instead): %s' % (len(not_materials), ', '.join(not_materials)))
    if unwired:
        unreal.log_warning('fix_materials: %d masked material(s) have no texture to build an Opacity Mask from: %s' % (len(unwired), ', '.join(unwired)))
    unreal.log('fix_materials: %d material(s) updated (%s%s%s)' % (
        changed, BLEND, ', matte' if MATTE else '', ', emissive off' if EMISSIVE_OFF else ''))


main()
