"""What the editor knows about the portal room: slots, portal looks, destinations.

Ported from PortalHubConfig.ps1. Destination names and order follow the wiki's list of portal worlds; pad IDs and looks
were matched to the game's data (DT_Levels and the teleporter dump).
"""

# The 12 portal-room slots, in room order. A = top level, B = middle, C = bottom. Three hold the game's own portals.
ROWS = "ABC"
SLOT_IDS = [f"{r}-{n}" for r in ROWS for n in (1, 2, 3, 4)]
LOCKED_SLOTS = {
    "A-1": ("Stone Garden", "H_Garden_Entrance"),
    "A-2": ("Torii", "H_Japan_Entrance"),
    "B-3": ("Cabin", "H_Cabin_Entrance"),
}
NO_ENTRY_SLOTS = ("A-1", "A-2", "B-3")      # marked with the no-entry sign. Remove a slot here to lift its mark.

DESIGN_NAMES = [
    "Niagara_Portal", "Niagara_Portal_Blueverse", "Niagara_Portal_Botanical_Green", "Niagara_Portal_Botanical_Red",
    "Niagara_Portal_Dark", "Niagara_Portal_Door", "Niagara_Portal_Fog", "Niagara_Portal_Friendly",
    "Niagara_Portal_Friendly_Black", "Niagara_Portal_Friendly_Blue", "Niagara_Portal_Friendly_Brown",
    "Niagara_Portal_Friendly_Cyan", "Niagara_Portal_Friendly_Glitched", "Niagara_Portal_Friendly_Green",
    "Niagara_Portal_Friendly_Lime", "Niagara_Portal_Friendly_Orange", "Niagara_Portal_Friendly_Pink",
    "Niagara_Portal_Friendly_Purple", "Niagara_Portal_Friendly_Red", "Niagara_Portal_Friendly_White",
    "Niagara_Portal_Friendly_Yellow", "Niagara_Portal_Garden", "Niagara_Portal_Greenverse",
    "Niagara_Portal_NightRDoor_2", "Niagara_Portal_Redverse", "Niagara_Portal_Rift",
    "Niagara_Portal_Salem", "Niagara_Portal_Shadowgate2", "Niagara_Portal_SnowFlurry", "Niagara_Portal_SunDisk",
    "Niagara_Portal_Tiny", "Niagara_Portal_Torii",
]

_LIGHTNING = ["lightning1", "lightning2", "portalmap", "smoke", "smoke2"]
_FRIENDLY = ["portal", "sparks"]
_SNOW = ["Blackhole", "smoke", "snowflakes", "SnowParticle01", "SnowParticle02", "Swirl"]
# The named parts (Niagara emitters) of each look, read from the game's effect files.
DESIGN_PARTS = {
    "Niagara_Portal": _LIGHTNING,
    "Niagara_Portal_Blueverse": _LIGHTNING,
    "Niagara_Portal_Botanical_Green": ["Ivy", "portal"],
    "Niagara_Portal_Botanical_Red": ["Ivy", "portal"],
    "Niagara_Portal_Dark": ["lightning1", "lightning2", "portalmap", "smoke"],
    "Niagara_Portal_Door": ["portal", "smoke", "sparks"],
    "Niagara_Portal_Fog": _LIGHTNING,
    "Niagara_Portal_Friendly": _FRIENDLY,
    "Niagara_Portal_Friendly_Black": _FRIENDLY,
    "Niagara_Portal_Friendly_Blue": _FRIENDLY,
    "Niagara_Portal_Friendly_Brown": _FRIENDLY,
    "Niagara_Portal_Friendly_Cyan": _FRIENDLY,
    "Niagara_Portal_Friendly_Glitched": _FRIENDLY,
    "Niagara_Portal_Friendly_Green": _FRIENDLY,
    "Niagara_Portal_Friendly_Lime": _FRIENDLY,
    "Niagara_Portal_Friendly_Orange": _FRIENDLY,
    "Niagara_Portal_Friendly_Pink": _FRIENDLY,
    "Niagara_Portal_Friendly_Purple": _FRIENDLY,
    "Niagara_Portal_Friendly_Red": _FRIENDLY,
    "Niagara_Portal_Friendly_White": _FRIENDLY,
    "Niagara_Portal_Friendly_Yellow": _FRIENDLY,
    "Niagara_Portal_Garden": ["portal", "sparks", "Vine1", "Vine2", "Vine3", "Vine4", "Vine5", "Vine6", "Vine7", "Vine8"],
    "Niagara_Portal_Greenverse": _LIGHTNING,
    "Niagara_Portal_NightRDoor_2": ["leaves001", "portal", "sparks"],
    "Niagara_Portal_Redverse": _LIGHTNING,
    "Niagara_Portal_Rift": ["distortion", "rift", "smoke", "sparks"],
    "Niagara_Portal_Salem": _FRIENDLY,
    "Niagara_Portal_Shadowgate2": _FRIENDLY,
    "Niagara_Portal_SnowFlurry": _SNOW,
    "Niagara_Portal_SunDisk": _SNOW,
    "Niagara_Portal_Tiny": ["lightning2", "smoke", "smoke2"],
    "Niagara_Portal_Torii": ["HangingParticulates", "portal"],
}
PROTECTED_PARTS = ("portal", "portalmap")        # can never be switched off
PART_NOTES = {"Niagara_Portal_SnowFlurry": {"Swirl": "accretion disk"}}
OVERSIZED_LOOKS = ("Niagara_Portal_Door", "Niagara_Portal_NightRDoor_2")

# A tint for each look: used for the ring on a slot card, so a board of portals reads at a glance.
LOOK_TINTS = {
    "Niagara_Portal": "#b9a6ff", "Niagara_Portal_Blueverse": "#6fa8ff", "Niagara_Portal_Botanical_Green": "#6fd67f",
    "Niagara_Portal_Botanical_Red": "#ff7a6b", "Niagara_Portal_Dark": "#8c7aa8", "Niagara_Portal_Door": "#ffc27a",
    "Niagara_Portal_Fog": "#c3cbd6", "Niagara_Portal_Friendly": "#9fd8ff", "Niagara_Portal_Friendly_Black": "#8d8d9b",
    "Niagara_Portal_Friendly_Blue": "#6fa8ff", "Niagara_Portal_Friendly_Brown": "#c49a6c",
    "Niagara_Portal_Friendly_Cyan": "#6fe8e8", "Niagara_Portal_Friendly_Glitched": "#ff6fd8",
    "Niagara_Portal_Friendly_Green": "#6fd67f", "Niagara_Portal_Friendly_Lime": "#c4f06a",
    "Niagara_Portal_Friendly_Orange": "#ffa24d", "Niagara_Portal_Friendly_Pink": "#ff9ad5",
    "Niagara_Portal_Friendly_Purple": "#c58cff", "Niagara_Portal_Friendly_Red": "#ff6b6b",
    "Niagara_Portal_Friendly_White": "#f2f2f2", "Niagara_Portal_Friendly_Yellow": "#ffe86a",
    "Niagara_Portal_Garden": "#7fdc9a", "Niagara_Portal_Greenverse": "#6fd67f", "Niagara_Portal_NightRDoor_2": "#7c8cff",
    "Niagara_Portal_Redverse": "#ff6b6b", "Niagara_Portal_Rift": "#d76fff", "Niagara_Portal_Salem": "#ffb36b",
    "Niagara_Portal_Shadowgate2": "#9a8cc4", "Niagara_Portal_SnowFlurry": "#b8e4ff", "Niagara_Portal_SunDisk": "#ffd36b",
    "Niagara_Portal_Tiny": "#b9a6ff", "Niagara_Portal_Torii": "#ff8f8f",
}


def design_path(name):
    return f"/Game/Particles/{name}.{name}"


def design_name(path):
    return path.rsplit(".", 1)[-1]


def design_label(name):
    if name == "Niagara_Portal":
        return "Default Portal"
    label = name.replace("Niagara_Portal_", "").replace("_", " ")
    return label + "  (Oversized)" if name in OVERSIZED_LOOKS else label


DEFAULT_DESIGN = design_path(DESIGN_NAMES[0])
DESIGNS = [(design_label(n), design_path(n)) for n in DESIGN_NAMES]

# One entrance per portal world: the pad that puts you inside it. Left out on purpose: Temple of Stone, Torii and Winter
# Cabin (the hub's own portals; Garden and Torii are DLC-gated) and exit, return and Facility-side pads.
# look = the portal look the game uses for that world's entrance in the Facility, picked when the world is chosen.
DESTINATIONS = [
    # group, pad id, world, icon, look
    ("Story", "anteverse_a_start", "Far Garden", "far-garden", "Niagara_Portal"),
    ("Story", "fog_start", "Flathill", "flathill", "Niagara_Portal_Fog"),
    ("Story", "train_start", "The Train", "the-train", "Niagara_Portal"),
    ("Story", "warehouse_start", "Furniture Store", "furniture-store", "Niagara_Portal_Door"),
    ("Story", "anteverse_b_start", "The Mycofields", "the-mycofields", "Niagara_Portal"),
    ("Story", "nightrealm_start_A", "The Night Realm", "the-night-realm", "Niagara_Portal_NightRDoor_2"),
    ("Story", "salem_begin", "Canaan", "canaan", "Niagara_Portal_Salem"),
    ("Story", "alps_start", "Voussoir", "voussoir", "Niagara_Portal_SnowFlurry"),
    ("Story", "anteverse_c_start", "Village Den da'ko Yeer", "village-den-da-ko-yeer", "Niagara_Portal_Blueverse"),
    ("Story", "shadowgate_start", "Shadowgate", "shadowgate", "Niagara_Portal_Shadowgate2"),
    ("Story", "INQ_Entrance", "Praetorium", "praetorium", "Niagara_Portal_Friendly"),
    # The Botanical Wing (in Fragments) is on the story path: the end of its future half gives the Motion Module recipe needed to
    # finish Fragments, which unlocks Albatross. Its two halves are linked by the game's own red and green portals. No wiki icon
    # for either. Looks: green for the present half, red for the future half (the author's choice).
    # The future half is the game's Divarication (V_BOTANICAL), a required story area: it sits just above Albatross (author, 9 November).
    ("Story", "botanical_present_01", "Botanical Wing (Present)", "botanical-wing-present", "Niagara_Portal_Botanical_Green"),
    ("Story", "wall_start", "GATE Arch Defense Facility", "gate-arch-defense-facility", "Niagara_Portal"),
    ("Story", "botanical_future_01", "Botanical Wing (Future)", "botanical-wing-future", "Niagara_Portal_Botanical_Red"),
    ("Story", "island_start", "Albatross", "albatross", "Niagara_Portal"),
    ("Optional (Major)", "rise_start", "Rise", "rise", "Niagara_Portal"),
    ("Optional (Major)", "V_Snowglobe_Start", "North Pole", "north-pole", "Niagara_Portal"),
    ("Optional (Major)", "signal_start", "Dunkeltaler Forest", "dunkeltaler-forest", "Niagara_Portal_Friendly_Red"),
    ("Optional (Major)", "VWinter_Start", "Royal Range (IS-0083)", "royal-range", "Niagara_Portal"),
    ("Optional (Minor)", "mirrorworld_start", "The World in the Mirror", "the-world-in-the-mirror", "Niagara_Portal"),
    ("Optional (Minor)", "tile_entrance", "The Pool Room", "the-pool-room", "Niagara_Portal"),
    ("Optional (Minor)", "DistantShore", "Some Distant Shore", "some-distant-shore", "Niagara_Portal"),
]
KNOWN_BY_ID = {d[1]: d for d in DESTINATIONS}

# Their entrance pads are DLC-gated in the game and a hub portal would bypass that. Matched case-insensitively.
DLC_PADS = {"h_garden_start", "h_garden_entrance", "h_japan_start", "h_japan_entrance"}


def is_dlc(pad):
    return pad.strip().lower() in DLC_PADS


# Hub Exits (CRD-012): what a base-game world's own exits do for a hub portal leading to it. exitMode (top of config.lua) is the
# default for every portal and takes modes 1-3; exits on a portal overrides it and is the only way to pick mode 4. Numbers 1-4 work too.
EXIT_MODES = ["game", "hub", "dynamic", "manual"]
GLOBAL_EXIT_MODES = EXIT_MODES[:3]
DEFAULT_EXIT_MODE = "game"
EXIT_MODE_HELP = {
    "game": "The world's exits are the game's: the hub portal only takes players in.",
    "hub": "The world's exits take everyone to the hub portal, however they came in.",
    "dynamic": "Per player: came in through the hub portal, leave to it; came the game's way, leave the game's way.",
    "manual": "The hub portal leads to the world's Manual Hub Exit (MHE), which always leads back. The world's own exits stay the game's.",
}


def exit_mode(v):
    """A mode name from a config value ("hub", "HUB", 2 or 2.0), or None if it is not one."""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int) and not isinstance(v, bool):
        return EXIT_MODES[v - 1] if 1 <= v <= 4 else None
    if isinstance(v, str) and v.lower() in EXIT_MODES:
        return v.lower()
    return None


def home_title(pad):
    """The game's homes key their MHE by their start pad (H_Cabin_Start): a readable name, or None."""
    if pad.startswith("H_") and pad.endswith("_Start") and len(pad) > 8:
        return pad[2:-6] + " (home)"
    return None


LIGHT_PRESETS = [("Red", "#FF2020"), ("Orange", "#FF8A1A"), ("Yellow", "#FFE81A"), ("Green", "#2EE65C"),
                 ("Blue", "#2A6BFF"), ("Indigo", "#4B2AB5"), ("Violet", "#A030FF")]
