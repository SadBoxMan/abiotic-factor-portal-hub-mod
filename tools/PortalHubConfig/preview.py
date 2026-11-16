"""The scale preview's maths (CRD-044): how big a design's portal is next to the player, and where both go in a preview box.

No Tkinter here, so the tests can check it directly. Sizes in metres; the pad's base is taken as the floor the player stands on.
A ring's size is exact (it is the mesh ring's own scale). A game look's size is an estimate (hubdata.look_size), so the preview says so.
"""
from dataclasses import dataclass

import hubdata as hd


@dataclass
class Extent:
    width: float        # metres
    height: float       # metres
    centre: float       # metres above the pad: where the look (and the ring) sits
    exact: bool         # True for a ring (its own size), False for a game look (an estimate)
    what: str           # one line for the preview's caption

    @property
    def bottom(self):
        return self.centre - self.height / 2

    @property
    def top(self):
        return self.centre + self.height / 2


def design_height(d):
    """The height (cm) the hub puts this design at: its own, else the ring rule for look = "none", else the look's sheet height."""
    if d.height is not None:
        return d.height
    if d.look == "none" and d.ring:
        w, h = ring_dims(d)
        return h * 50 + hd.RING_LIFT_CM
    return hd.LOOK_HEIGHTS.get(d.look, hd.GAME_LOOK_HEIGHT)


def ring_dims(d):
    return tuple(d.size) if d.size else hd.ring_size(d.ring)


def extent(d):
    """The portal's outline for a design (luaconfig.Design): the ring if it has one, else the look (scaled, Friendly only)."""
    centre = design_height(d) / 100.0
    if d.ring:
        w, h = ring_dims(d)
        return Extent(w, h, centre, True, f"ring {w:.2f} x {h:.2f} m (exact)")
    w, h = hd.look_size(d.look)
    if d.scale and d.look in hd.SCALABLE_LOOKS:
        w, h = w * d.scale[1], h * d.scale[2]           # the look's Y is its width, Z its height (the pad faces along X)
    return Extent(w, h, centre, False, f"look about {w:.2f} x {h:.2f} m (estimate)")


@dataclass
class Layout:
    scale: float        # pixels per metre
    floor: float        # y of the floor (pixels)
    person: tuple       # (x of the feet's centre, y of the head's top, height in pixels)
    portal: tuple       # (x0, y0, x1, y1) of the portal's outline
    pad: tuple          # (x0, x1) of the pad's base on the floor


PERSON_W = 0.6          # metres the silhouette takes sideways
GAP = 0.45              # metres between the player and the pad's edge
PAD_EXTRA = 0.25        # the pad's base reaches this far past the portal on each side (drawing only)


def layout(ext, player_cm, box_w, box_h, margin=14, top_room=26):
    """Fit the player and the portal side by side, to one scale, in a box of box_w x box_h pixels (top_room left free for labels)."""
    player = player_cm / 100.0
    need_h = max(player, ext.top, 0.5) + 0.25
    need_w = PERSON_W + GAP + PAD_EXTRA * 2 + max(ext.width, 0.3)
    s = min((box_h - margin - top_room) / need_h, (box_w - 2 * margin) / need_w)
    floor = box_h - margin
    feet_x = margin + s * PERSON_W / 2
    px0 = margin + s * (PERSON_W + GAP + PAD_EXTRA)
    px1 = px0 + s * ext.width
    portal = (px0, floor - s * ext.top, px1, floor - s * ext.bottom)
    person = (feet_x, floor - s * player, s * player)
    pad = (px0 - s * PAD_EXTRA, px1 + s * PAD_EXTRA)
    return Layout(s, floor, person, portal, pad)


def ratio_text(ext, player_cm):
    """The portal's height against the player's, in words."""
    r = ext.height / (player_cm / 100.0)
    return f"{r:.2f} x the player's height" + ("" if ext.exact else " (estimate)")
