# Unreal Editor Python script: fix the SELECTED materials in bulk (matte, Masked or Opaque, Two Sided, optional no-glow, tidy graph).
#
# Why: materials created by importing an OBJ / FBX copy the file's settings. They often come out shiny, sometimes Translucent or Opaque
# when they should have holes (leaves, fences, grass, black-as-transparent textures), and earlier runs of a script can leave extra nodes
# behind. This script fixes all of that for every selected material in one go. Pick what you want in the settings just below.
#
# What it can and cannot change (checked against Unreal Engine 5.4.4):
#   * A material's Roughness, Specular and Metallic pin VALUES cannot be written from a script (Unreal marks them "protected" and does not
#     expose the input structs to Python). So the script does not try. Instead it
#       - turns on the material's own "Fully Rough" switch (Roughness is then 1 everywhere: no node, no wire),
#       - breaks the links from plain Constant nodes into Metallic, Specular and Roughness and deletes those nodes, so those pins go back
#         to Unreal's defaults (Metallic 0, Specular 0.5). At Roughness 1 a Specular of 0.5 gives no visible shine.
#     If you want Specular at exactly 0, either type 0 into the Specular pin in the material editor, or set SPECULAR_CONSTANT below
#     (that keeps ONE Constant node wired into Specular and edits it in place, it never adds a second).
#   * Blend mode, Two Sided and the Opacity Mask clip value are set directly on the material.
#   * With BLEND = "masked" the Opacity Mask must also be connected to something, so the script wires it for you (see MASK_FROM).
# Base Color is never touched. Running the script again is safe: it reuses and edits what it made before, and removes stray nodes.
#
# Status: run against Unreal Engine 5.4.4's real Python API in a headless editor, on duplicates of real imported materials: 75 checks pass
# (matte settings, wiring the mask from alpha and from black, re-running it, stray-node cleanup, emissive off, bad settings). It has not
# been run by hand in the editor window yet; if it errors there, send the Output Log line.
#
# How to use (editor only; it changes your project's assets, not the game):
#   1. Edit > Plugins: enable "Python Editor Script Plugin" and "Editor Scripting Utilities", restart the editor (one time).
#   2. In the Content Browser, select the materials to change (filter by type Material, then Ctrl+A). The defaults below suit cut-out
#      materials (Masked). For solid materials set BLEND = "opaque" and run it again on those. Solid and cut-out materials need
#      different settings, so run it once for each group.
#   3. Edit the settings just below, then Tools > Execute Python Script... and pick this file.
# Only Materials are changed. Material Instances are skipped with a warning: change their parent material instead.
# Afterwards, if thin edges of a masked material look too thick or too thin, adjust its "Opacity Mask Clip Value" (CLIP sets the first guess).

import unreal

# ---- Surface (shine) --------------------------------------------------------------------------------------------------------------------
MATTE = True               # True: apply the matte steps below. False: leave the surface exactly as it is.
FULLY_ROUGH = True         # turn on the material's own "Fully Rough" switch (Roughness 1 everywhere, no node needed)
UNWIRE_CONSTANTS = True    # break + delete plain Constant nodes wired into Metallic, Specular and Roughness (needs FULLY_ROUGH = True)
SPECULAR_CONSTANT = None   # None = leave Specular at Unreal's default (0.5). A number such as 0.0 = keep ONE Constant wired into
                           # Specular with that value (an existing one is edited in place, never duplicated)
EMISSIVE_OFF = False       # True: wire black into Emissive Color, to stop a material glowing on its own.
                           # Leave False for things that should glow (lights, screens, lava).

# ---- Transparency -----------------------------------------------------------------------------------------------------------------------
BLEND = "masked"           # "masked" = cut-out holes (leaves, fences, grass), "opaque" = solid. Never Translucent: it sorts badly.
MASK_FROM = "alpha"        # only for BLEND = "masked":  "alpha" = the texture's alpha channel is the mask,
                           #                             "black" = black pixels become transparent (for textures without alpha)
REWIRE_MASK = False        # True: replace an Opacity Mask connection that already exists (use it to switch a material to "black")
CLIP = 0.3333              # only for BLEND = "masked": Opacity Mask Clip Value. Mask values below this are cut away.
                           # For MASK_FROM = "black" try 0.05 to 0.1.
TWO_SIDED = True           # render both faces (needed for thin walls and leaves; harmless for solid meshes)

# ---- Tidiness ---------------------------------------------------------------------------------------------------------------------------
CLEAN_STRAYS = True        # delete unused Constant / Constant3Vector / Desaturation nodes (leftovers of earlier runs). Only unconnected
                           # nodes of those three kinds are removed, never anything that feeds the material.

mel = unreal.MaterialEditingLibrary
P = unreal.MaterialProperty
ALL_INPUTS = [getattr(P, name) for name in dir(P) if name.startswith('MP_') and not name.endswith('MAX')]
STRAY_KINDS = ('MaterialExpressionConstant', 'MaterialExpressionConstant3Vector', 'MaterialExpressionDesaturation')


def constant(material, value, x, y):
    node = mel.create_material_expression(material, unreal.MaterialExpressionConstant, x, y)
    node.set_editor_property('r', value)
    return node


def reachable_nodes(material):
    """Every expression that feeds one of the material's inputs, directly or through other nodes."""
    seen = set()
    queue = []
    for prop in ALL_INPUTS:
        try:
            node = mel.get_material_property_input_node(material, prop)
        except Exception:                                                   # noqa: BLE001  (an input this material type does not have)
            continue
        if node is not None:
            queue.append(node)
    while queue:
        node = queue.pop()
        if node in seen:
            continue
        seen.add(node)
        for upstream in mel.get_inputs_for_material_expression(material, node):
            if upstream is not None:            # an unconnected pin comes back as None; never hand None back to the library
                queue.append(upstream)
    return seen


def find_texture_node(material, start):
    """Walk back from a node through its inputs until a texture sample is found (or give up)."""
    if start is None:
        return None
    seen = set()
    queue = [start]
    while queue:
        node = queue.pop(0)
        if node in seen:
            continue
        seen.add(node)
        if isinstance(node, unreal.MaterialExpressionTextureSample):       # also covers texture-sample parameters
            return node
        for upstream in mel.get_inputs_for_material_expression(material, node):
            if upstream is not None:
                queue.append(upstream)
    return None


def first_texture_node(material):
    for prop in (P.MP_BASE_COLOR, P.MP_EMISSIVE_COLOR):
        found = find_texture_node(material, mel.get_material_property_input_node(material, prop))
        if found:
            return found
    return None


def make_matte(material):
    """Returns a short description of what was done."""
    done = []
    if FULLY_ROUGH:
        try:
            material.set_editor_property('fully_rough', True)
            done.append('fully rough')
        except Exception as err:                                            # noqa: BLE001
            unreal.log_warning('fix_materials: could not turn on Fully Rough for %s: %s' % (material.get_name(), err))
    if UNWIRE_CONSTANTS and FULLY_ROUGH:
        removed = 0
        for prop in (P.MP_METALLIC, P.MP_SPECULAR, P.MP_ROUGHNESS):
            if prop == P.MP_SPECULAR and SPECULAR_CONSTANT is not None:
                continue                                                    # that one is kept and edited below
            node = mel.get_material_property_input_node(material, prop)
            if node is not None and isinstance(node, unreal.MaterialExpressionConstant):
                mel.delete_material_expression(material, node)              # deleting the node breaks the link
                removed += 1
        if removed:
            done.append('%d constant link(s) broken' % removed)
    if SPECULAR_CONSTANT is not None:
        node = mel.get_material_property_input_node(material, P.MP_SPECULAR)
        if node is None:
            mel.connect_material_property(constant(material, SPECULAR_CONSTANT, -600, 800), '', P.MP_SPECULAR)
            done.append('specular %s' % SPECULAR_CONSTANT)
        elif isinstance(node, unreal.MaterialExpressionConstant):
            node.set_editor_property('r', SPECULAR_CONSTANT)                # edit the existing constant in place
            done.append('specular %s' % SPECULAR_CONSTANT)
        else:
            unreal.log_warning('fix_materials: Specular of %s is driven by another node (%s); left alone' % (material.get_name(), type(node).__name__))
    return done


def switch_emissive_off(material):
    black = unreal.LinearColor(0.0, 0.0, 0.0, 1.0)
    node = mel.get_material_property_input_node(material, P.MP_EMISSIVE_COLOR)
    if isinstance(node, unreal.MaterialExpressionConstant3Vector):
        node.set_editor_property('constant', black)                         # edit the one made earlier, do not add another
        return
    node = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -600, 1000)
    node.set_editor_property('constant', black)
    mel.connect_material_property(node, '', P.MP_EMISSIVE_COLOR)


def wire_opacity_mask(material):
    """Connect the Opacity Mask. Returns 'kept' (already connected), 'no texture' (nothing to wire) or 'wired'."""
    if mel.get_material_property_input_node(material, P.MP_OPACITY_MASK) is not None and not REWIRE_MASK:
        return 'kept'
    tex = first_texture_node(material)
    if tex is None:
        unreal.log_warning('fix_materials: no texture found in %s; Masked is set, but connect its Opacity Mask by hand' % material.get_name())
        return 'no texture'
    if MASK_FROM == "black":
        desat = mel.create_material_expression(material, unreal.MaterialExpressionDesaturation, -300, 1100)
        mel.connect_material_expressions(tex, 'RGB', desat, 'Input')
        mel.connect_material_property(desat, '', P.MP_OPACITY_MASK)
    else:
        mel.connect_material_property(tex, 'A', P.MP_OPACITY_MASK)
    return 'wired'


def remove_stray_nodes(material):
    """Delete unused Constant / Constant3Vector / Desaturation nodes. Expressions are named <Class>_<number> inside the material."""
    keep = reachable_nodes(material)
    base = material.get_path_name()
    removed = 0
    limit = mel.get_num_material_expressions(material) + 40
    for kind in STRAY_KINDS:
        for index in range(limit):
            node = unreal.find_object(None, '%s:%s_%d' % (base, kind, index))
            if node is not None and unreal.SystemLibrary.is_valid(node) and node not in keep:       # is_valid: skip nodes already deleted
                mel.delete_material_expression(material, node)
                removed += 1
    return removed


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
        notes = []
        if MATTE:
            notes += make_matte(asset)
        if EMISSIVE_OFF:
            switch_emissive_off(asset)
            notes.append('emissive off')
        asset.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE)
        asset.set_editor_property('two_sided', TWO_SIDED)
        notes.append(BLEND)
        if masked:
            asset.set_editor_property('opacity_mask_clip_value', CLIP)
            result = wire_opacity_mask(asset)
            notes.append('mask ' + result)
            if result == 'no texture':
                unwired.append(asset.get_name())
        if CLEAN_STRAYS:
            removed = remove_stray_nodes(asset)
            if removed:
                notes.append('%d stray node(s) removed' % removed)
        mel.recompile_material(asset)
        unreal.EditorAssetLibrary.save_loaded_asset(asset)
        changed += 1
        unreal.log('fix_materials: %s (%s)' % (asset.get_name(), ', '.join(notes)))
    if not_materials:
        unreal.log_warning('fix_materials: skipped %d selected asset(s) that are not Materials (Material Instances? change their parent '
                           'material instead): %s' % (len(not_materials), ', '.join(not_materials)))
    if unwired:
        unreal.log_warning('fix_materials: %d masked material(s) have no texture to build an Opacity Mask from: %s' % (len(unwired), ', '.join(unwired)))
    unreal.log('fix_materials: %d material(s) updated' % changed)


main()
