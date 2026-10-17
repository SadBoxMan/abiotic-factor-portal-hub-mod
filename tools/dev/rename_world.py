# Unreal Editor (headless) script: rename a copied world project's assets so every reference follows.
# Run by copy_world.ps1, which copies the project first and passes the names through environment variables:
#   PH_OLD   old world name, e.g. World_A      PH_NEW   new world name, e.g. World_B
#   PH_CHUNK chunk id for the new Primary Asset Label, e.g. 92
#   PH_OUT   file to write the report to
# Renames /Game/Mods/<old> to /Game/Mods/<new>, BP_<old>_Loader, <old>_L0 and PAL_<old>, fixes redirectors, sets the chunk id,
# saves, then checks that nothing still refers to the old name and that the loader points at the new map.
import os
import unreal

OLD, N, CHUNK, OUT = os.environ["PH_OLD"], os.environ["PH_NEW"], int(os.environ["PH_CHUNK"]), os.environ["PH_OUT"]
open(OUT, "w").close()


def log(*a):
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(" ".join(str(x) for x in a) + "\n")


eal = unreal.EditorAssetLibrary
at = unreal.AssetToolsHelpers.get_asset_tools()
reg = unreal.AssetRegistryHelpers.get_asset_registry()
reg.scan_paths_synchronous(["/Game/Mods"], True)
base = "/Game/Mods/" + N
log("rename_directory:", eal.rename_directory("/Game/Mods/" + OLD, base))
pairs = [("BP_" + OLD + "_Loader", "BP_" + N + "_Loader", base), (OLD + "_L0", N + "_L0", base + "/Maps"), ("PAL_" + OLD, "PAL_" + N, base)]
data = []
for old, new, folder in pairs:
    a = eal.load_asset(folder + "/" + old)
    log("load", old, a is not None)
    if a is not None:
        data.append(unreal.AssetRenameData(a, folder, new))
log("rename_assets:", at.rename_assets(data))
redirs = [eal.load_asset(p) for p in eal.list_assets("/Game", recursive=True, include_folder=False)
          if str(eal.find_asset_data(p).asset_class_path.asset_name) == "ObjectRedirector"]
log("redirectors found:", len(redirs))
if redirs:
    at.fixup_referencers(redirs)
pal = eal.load_asset(base + "/PAL_" + N)
rules = pal.get_editor_property("rules")
rules.set_editor_property("chunk_id", CHUNK)
pal.set_editor_property("rules", rules)
log("saved:", eal.save_directory("/Game", only_if_is_dirty=False, recursive=True))
log("asset paths still named", OLD, ":", [p for p in eal.list_assets("/Game", recursive=True, include_folder=False) if OLD in p])
opts = unreal.AssetRegistryDependencyOptions()
bad = []
for p in eal.list_assets(base, recursive=True, include_folder=False):
    pkg = p.split(".")[0]
    for d in (reg.get_dependencies(pkg, opts) or []):
        if OLD in str(d):
            bad.append(pkg + " -> " + str(d))
log("references to", OLD, ":", bad)
bp = eal.load_asset(base + "/BP_" + N + "_Loader")
cdo = unreal.get_default_object(bp.generated_class())
log("world_asset =", cdo.get_editor_property("world_asset"))
log("chunk id =", eal.load_asset(base + "/PAL_" + N).get_editor_property("rules").get_editor_property("chunk_id"))
log("DONE")
