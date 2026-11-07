"""Read and edit the Portal Hub's config.lua without disturbing anything else in it.

The file is a plain Lua table that people also edit by hand, so it is never regenerated. It is parsed into a tree that
remembers where each value sits in the text, and saving replaces only the values that changed. Comments, spacing, key
order and keys this tool has never heard of all stay exactly as written, and saving with no changes gives the same bytes.

Python standard library only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from hubdata import DEFAULT_DESIGN, PROTECTED_PARTS, SLOT_IDS

LUA_RESERVED = {
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if", "in", "local", "nil",
    "not", "or", "repeat", "return", "then", "true", "until", "while",
}
NAME_RX = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NUMBER_RX = re.compile(r"-?(?:0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)")
HEADER = "-- Portal Hub configuration. Edit this file, or use PortalHubConfig.bat. Restart mods to apply.\n\nreturn {\n}\n"


class LuaError(Exception):
    """The text is not a Lua table this module can read."""


# ------------------------------------------------------------------ parser
@dataclass
class Node:
    kind: str                # "string", "number", "bool", "nil", "table", or "expr" (code this parser does not evaluate)
    start: int
    end: int
    value: object = None
    items: list = field(default_factory=list)      # tables only
    has_comment: bool = False                      # tables only: a comment sits somewhere inside

    def get(self, key):
        for it in self.items:
            if it.key == key:
                return it
        return None

    def positional(self):
        return [it.value for it in self.items if it.key is None]


@dataclass
class Item:
    key: object              # str for  key = v  and  ["key"] = v,  None for a positional value
    start: int               # start of the key (or of the value when positional)
    value: Node
    comma_end: int | None    # just past the comma after the value, if there is one
    key_end: int = 0         # end of the key text

    @property
    def end(self):
        return self.comma_end if self.comma_end is not None else self.value.end


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.saw_comment = False

    def skip(self):
        t, n = self.text, len(self.text)
        while self.pos < n:
            ch = t[self.pos]
            if ch in " \t\r\n":
                self.pos += 1
            elif t.startswith("--", self.pos):
                self.saw_comment = True
                self.pos += 2
                m = re.compile(r"\[(=*)\[").match(t, self.pos)
                if m:
                    close = t.find("]" + m.group(1) + "]", m.end())
                    self.pos = n if close < 0 else close + len(m.group(1)) + 2
                else:
                    nl = t.find("\n", self.pos)
                    self.pos = n if nl < 0 else nl + 1
            else:
                return

    def error(self, msg):
        line = self.text.count("\n", 0, self.pos) + 1
        raise LuaError(f"line {line}: {msg}")

    def find_return_table(self):
        """The table after the file's top-level  return ."""
        while True:
            self.skip()
            if self.pos >= len(self.text):
                self.error("no 'return { ... }' found")
            m = re.compile(r"return\b").match(self.text, self.pos)
            if m:
                self.pos = m.end()
                self.skip()
                if self.text[self.pos:self.pos + 1] != "{":
                    self.error("'return' is not followed by a table")
                return self.table()
            ch = self.text[self.pos]
            if ch in "\"'":
                self.string()
            else:
                self.pos += 1

    def string(self):
        t = self.text
        quote = t[self.pos]
        start = self.pos
        self.pos += 1
        out = []
        while True:
            if self.pos >= len(t) or t[self.pos] == "\n":
                self.error("unfinished string")
            ch = t[self.pos]
            if ch == quote:
                self.pos += 1
                return Node("string", start, self.pos, "".join(out))
            if ch == "\\":
                self.pos += 1
                esc = t[self.pos:self.pos + 1]
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(esc, esc))
            else:
                out.append(ch)
            self.pos += 1

    def skip_expr(self):
        """Step over code this parser does not evaluate, up to the next comma or closing brace at this depth."""
        t, start, depth = self.text, self.pos, 0
        while self.pos < len(t):
            ch = t[self.pos]
            if ch in "\"'":
                self.string()
                continue
            if t.startswith("--", self.pos):
                self.skip()
                continue
            if ch in "{([":
                depth += 1
            elif ch in "})]":
                if depth == 0:
                    break
                depth -= 1
            elif ch in ",;" and depth == 0:
                break
            self.pos += 1
        end = self.pos
        while end > start and t[end - 1] in " \t\r\n":
            end -= 1
        return Node("expr", start, end, t[start:end])

    def at_value_end(self):
        self.skip()
        return self.text[self.pos:self.pos + 1] in (",", ";", "}", "")

    def value(self):
        self.skip()
        t, start = self.text, self.pos
        ch = t[start:start + 1]
        if ch == "{":
            return self.table()
        if ch in ("\"", "'"):
            node = self.string()
        else:
            m = NUMBER_RX.match(t, start)
            word = NAME_RX.match(t, start)
            if m:
                self.pos = m.end()
                node = Node("number", start, m.end(), float(int(m.group(), 16)) if "x" in m.group().lower() else float(m.group()))
            elif word and word.group() in ("true", "false", "nil"):
                self.pos = word.end()
                w = word.group()
                node = Node("nil", start, word.end()) if w == "nil" else Node("bool", start, word.end(), w == "true")
            else:
                return self.skip_expr()
        end = self.pos
        if not self.at_value_end():            # e.g.  1000 * 2  or  "a" .. "b"
            self.pos = start
            return self.skip_expr()
        self.pos = end
        return node

    def table(self):
        t = self.text
        start = self.pos
        self.pos += 1
        node = Node("table", start, start)
        was_comment, self.saw_comment = self.saw_comment, False
        while True:
            self.skip()
            if self.pos >= len(t):
                self.error("table is never closed")
            ch = t[self.pos]
            if ch == "}":
                self.pos += 1
                break
            item_start = self.pos
            key, key_end = None, 0
            m = NAME_RX.match(t, self.pos)
            after = None
            if m:
                probe = Parser(t)
                probe.pos = m.end()
                probe.skip()
                if t[probe.pos:probe.pos + 1] == "=" and t[probe.pos:probe.pos + 2] != "==":
                    after = probe.pos + 1
                    key, key_end = m.group(), m.end()
            elif ch == "[" and t[self.pos + 1:self.pos + 2] in ("\"", "'"):
                self.pos += 1
                k = self.string()
                self.skip()
                if t[self.pos:self.pos + 1] != "]":
                    self.error("expected ] after a key")
                self.pos += 1
                key, key_end = k.value, self.pos
                self.skip()
                if t[self.pos:self.pos + 1] != "=":
                    self.error("expected = after a key")
                after = self.pos + 1
            if after is not None:
                self.pos = after
            value = self.value()
            self.skip()
            comma_end = None
            if t[self.pos:self.pos + 1] in (",", ";"):
                self.pos += 1
                comma_end = self.pos
            elif t[self.pos:self.pos + 1] != "}":
                self.error("expected , or } in a table")
            node.items.append(Item(key, item_start, value, comma_end, key_end))
        node.end = self.pos
        node.has_comment = self.saw_comment
        self.saw_comment = was_comment or self.saw_comment
        return node


def plain(node):
    """A Node as plain Python data, or raises LuaError if it holds code. Tables become lists when all positional, else dicts."""
    if node.kind == "expr":
        raise LuaError("not a plain value")
    if node.kind != "table":
        return node.value
    if all(it.key is None for it in node.items):
        return [plain(it.value) for it in node.items]
    return {it.key: plain(it.value) for it in node.items}


# ------------------------------------------------------------------ text edits
class Edits:
    """Collects changes against the original text and applies them together, last first, so offsets stay valid."""

    def __init__(self, text):
        self.text = text
        self.nl = "\r\n" if text.count("\r\n") * 2 > text.count("\n") else "\n"
        self.spans = []
        self.pending = {}
        self.closers = {}

    def replace(self, start, end, new):
        self.spans.append((start, end, new))

    def line_start(self, pos):
        return self.text.rfind("\n", 0, pos) + 1

    def line_end(self, pos):
        """The offset just past the line's newline."""
        nl = self.text.find("\n", pos)
        return len(self.text) if nl < 0 else nl + 1

    def indent_at(self, pos):
        ls = self.line_start(pos)
        return re.match(r"[ \t]*", self.text[ls:pos]).group()

    def alone_on_lines(self, start, end):
        """True if only whitespace or a trailing comment shares the lines of start..end."""
        before = self.text[self.line_start(start):start]
        rest = self.text[end:self.line_end(end)]
        return not before.strip() and (not rest.strip() or rest.strip().startswith("--"))

    def remove_item(self, table, item):
        if self.alone_on_lines(item.start, item.end):
            self.replace(self.line_start(item.start), self.line_end(item.end), "")
            return
        self.pending.setdefault(id(table), (table, []))[1].append(item)

    def flush_removals(self):
        """Fields that share a line with others. Done together, so neighbours going at once don't collide."""
        for table, gone in self.pending.values():
            kept_before = False
            for i, item in enumerate(table.items):
                if not any(item is g for g in gone):
                    kept_before = True
                elif kept_before:                       # { a, b }  ->  { a }, and any trailing comma stays
                    self.replace(table.items[i - 1].value.end, item.value.end, "")
                elif i + 1 < len(table.items):          # { a, b }  ->  { b }
                    self.replace(item.start, table.items[i + 1].start, "")
                else:
                    self.replace(item.start, item.end, "")
        self.pending = {}

    def add_item(self, table, new, before=None, indent=None):
        """Add  new  (one Lua field, no trailing comma) to a table, keeping its layout."""
        multiline = "\n" in self.text[table.start:table.end]
        if before is not None and not self.text[self.line_start(before.start):before.start].strip():
            pad = self.indent_at(before.start)
            self.replace(self.line_start(before.start), self.line_start(before.start), f"{pad}{new},{self.nl}")
        elif not table.items and not multiline:
            pad = indent if indent is not None else self.indent_at(table.start)
            self.replace(table.start + 1, table.start + 1, f"{self.nl}{pad}    {new},")
            self.closers[table.end - 1] = f"{self.nl}{pad}"
        elif table.items and not multiline:
            last = table.items[-1]
            if last.comma_end is None:
                self.replace(last.value.end, last.value.end, f", {new}")
            else:
                self.replace(last.comma_end, last.comma_end, f" {new},")
        elif table.items:
            last = table.items[-1]
            if last.comma_end is None:
                self.replace(last.value.end, last.value.end, ",")
            pad = self.indent_at(last.start)
            at = self.line_end(last.end)
            self.replace(at, at, f"{pad}{new},{self.nl}")
        else:
            pad = self.indent_at(table.end - 1) + "    "
            at = self.line_start(table.end - 1)
            self.replace(at, at, f"{pad}{new},{self.nl}")

    def set_field(self, table, key, new):
        """Set, add or (new is None) remove one  key = value  field of a table."""
        item = table.get(key)
        if item is None:
            if new is not None:
                self.add_item(table, f"{key} = {new}")
        elif new is None:
            self.remove_item(table, item)
        elif self.text[item.value.start:item.value.end] != new:
            self.replace(item.value.start, item.value.end, new)

    def result(self):
        self.flush_removals()
        for pos, text in self.closers.items():       # after the fields added to a table that was {}
            self.replace(pos, pos, text)
        self.closers = {}
        out, last = [], 0
        for start, end, new in sorted(self.spans, key=lambda s: (s[0], s[1])):
            if start < last:
                raise LuaError("two edits overlap")
            out.append(self.text[last:start])
            out.append(new)
            last = end
        out.append(self.text[last:])
        return "".join(out)


# ------------------------------------------------------------------ formatting
def fmt_num(n):
    s = f"{float(n):.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def lua_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_nums(vals):
    return "{ " + ", ".join(fmt_num(v) for v in vals) + " }"


def lua_key(k):
    if NAME_RX.fullmatch(k) and k not in LUA_RESERVED:
        return k
    return "[" + lua_string(k) + "]"


def hex_to_rgb(h):
    return [int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]


def rgb_to_hex(rgb):
    b = [int(round(min(1.0, max(0.0, c)) * 255)) for c in rgb[:3]]
    return "#{:02X}{:02X}{:02X}".format(*b)


# ------------------------------------------------------------------ the model
@dataclass
class Portal:
    slot: str
    name: str = ""
    destination: str = ""
    design: str = DEFAULT_DESIGN
    light_hex: str = ""
    brightness: float = 1.0
    enabled: bool = True
    item: Item | None = None            # where it sits in the file; None for a portal added in the editor
    extras: list = field(default_factory=list)      # names of other fields in the entry, kept as written

    def snapshot(self):
        return (self.name, self.destination, self.design, self.light_hex.upper(), round(self.brightness, 3))


@dataclass
class World:
    id: str = ""
    asset: str = ""
    cls: str = ""
    level: str = ""
    origin: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    arrive: list | None = None          # optional: None leaves it out, the hub then uses 0, 0, 0, 0
    item: Item | None = None
    raw: bool = False                   # holds something this tool can't edit: kept as written, shown read-only
    extras: list = field(default_factory=list)
    class_auto: bool = False            # the class still follows the Blueprint name
    bad: str = ""                       # a number box holds something that isn't a number

    def snapshot(self):
        return (self.id, self.asset, self.cls, self.level, list(self.origin), None if self.arrive is None else list(self.arrive))


class HubConfig:
    def __init__(self, path=None, text=None):
        self.path = path
        if text is None:
            if path and os.path.exists(path):
                with open(path, "rb") as f:
                    raw = f.read()
                if raw.startswith(b"\xef\xbb\xbf"):
                    raw = raw[3:]                    # a BOM is dropped on the next save (the hub's Lua won't take one)
                text = raw.decode("utf-8")
            else:
                text = HEADER
        self.text = text
        self.root = Parser(text).find_return_table()
        self._read()

    # ------------- reading
    def _read(self):
        r = self.root
        self.hum_mode = "dynamic"
        self.hum_floor = 15
        self.hum_manual = 50
        it = r.get("humMode")
        if it and it.value.kind == "string" and it.value.value in ("dynamic", "manual", "default"):
            self.hum_mode = it.value.value
        for key, attr in (("humFloor", "hum_floor"), ("humManual", "hum_manual")):
            it = r.get(key)
            if it and it.value.kind == "number":
                setattr(self, attr, int(round(it.value.value * 100)))
        self._orig_hum = (self.hum_mode, self.hum_floor, self.hum_manual)
        self._read_hide()
        self._read_worlds()
        self._read_portals()
        self._read_hub_exits()

    def _read_hide(self):
        self.hide = {}
        self.hide_editable = True
        it = self.root.get("hideEmitters")
        if it:
            try:
                data = plain(it.value)
                if data == []:
                    data = {}
                if not isinstance(data, dict):
                    raise LuaError("not a map")
                for k, v in data.items():
                    names = [v] if isinstance(v, str) else v
                    if not isinstance(k, str) or not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                        raise LuaError("not a map of lists")
                    names = [n for n in names if n not in PROTECTED_PARTS]
                    if names:
                        self.hide[k] = names
            except LuaError:
                self.hide = {}
                self.hide_editable = False
        self._orig_hide = {k: list(v) for k, v in self.hide.items()}

    def _world_from(self, item):
        w = World(id=str(item.key), item=item)
        t = item.value
        if t.kind != "table":
            w.raw = True
            return w
        got = {}
        for sub in t.items:
            if sub.key in ("loaderAsset", "loaderClass", "level") and sub.value.kind == "string":
                got[sub.key] = sub.value.value
            elif sub.key in ("origin", "arrive") and sub.value.kind == "table":
                vals = [v.value for v in sub.value.positional()]
                if all(isinstance(v, float) for v in vals) and len(vals) == len(sub.value.items):
                    got[sub.key] = vals
            elif sub.key is not None:
                w.extras.append(sub.key)
            else:
                w.raw = True
        origin = got.get("origin")
        arrive = got.get("arrive")
        ok = {"loaderAsset", "loaderClass", "level", "origin"} <= set(got) and len(origin) == 3
        ok = ok and (t.get("arrive") is None or (arrive is not None and len(arrive) in (3, 4)))
        if not ok or w.raw:
            w.raw = True
            w.extras = []
            return w
        w.asset, w.cls, w.level = got["loaderAsset"], got["loaderClass"], got["level"]
        w.origin = list(origin)
        w.arrive = None if arrive is None else (list(arrive) + [0.0])[:4]
        return w

    def _read_worlds(self):
        self.worlds = []
        self.worlds_editable = True
        self._orig_worlds = {}
        it = self.root.get("worlds")
        if not it:
            return
        if it.value.kind != "table" or any(sub.key is None for sub in it.value.items):
            self.worlds_editable = False
            return
        for sub in it.value.items:
            w = self._world_from(sub)
            self.worlds.append(w)
            self._orig_worlds[id(sub)] = w.snapshot()

    def _read_portals(self):
        self.portals = {}
        self._orig_portals = {}
        it = self.root.get("portals")
        if not it or it.value.kind != "table":
            return
        for sub in it.value.items:
            t = sub.value
            if t.kind != "table":
                continue
            s = t.get("slot")
            if not s or s.value.kind != "string" or s.value.value not in SLOT_IDS or s.value.value in self.portals:
                continue                # left in the file as it is; the hub logs and skips such entries
            p = Portal(slot=s.value.value, item=sub)
            known = {"slot"}
            for key, attr in (("name", "name"), ("destination", "destination"), ("design", "design")):
                f = t.get(key)
                if f and f.value.kind == "string":
                    setattr(p, attr, f.value.value)
                    known.add(key)
            f = t.get("lightColor")
            if f and f.value.kind == "table":
                nums = [v.value for v in f.value.positional() if v.kind == "number"]
                if len(nums) >= 3:
                    p.light_hex = rgb_to_hex(nums)
                    known.add("lightColor")
            f = t.get("lightBrightness")
            if f and f.value.kind == "number":
                p.brightness = f.value.value
                known.add("lightBrightness")
            p.extras = [x.key for x in t.items if x.key not in known and x.key is not None]
            self.portals[p.slot] = p
            self._orig_portals[p.slot] = p.snapshot()

    def _read_hub_exits(self):
        self.hub_exits = {}
        self.hub_exits_editable = True
        self.hub_exit_buff = None
        it = self.root.get("hubExitBuff")
        if it and it.value.kind == "bool":
            self.hub_exit_buff = it.value.value
        self._orig_buff = self.hub_exit_buff
        it = self.root.get("hubExits")
        if it:
            try:
                data = plain(it.value)
                if data == []:
                    data = {}
                if not isinstance(data, dict):
                    raise LuaError("not a map")
                for k, spots in data.items():
                    if not isinstance(spots, list) or not all(self._good_spot(s) for s in spots):
                        raise LuaError("not a list of spots")
                    if spots:
                        self.hub_exits[k] = [(list(s) + [0.0])[:4] for s in spots]
            except LuaError:
                self.hub_exits = {}
                self.hub_exits_editable = False
        self._orig_exits = {k: [list(s) for s in v] for k, v in self.hub_exits.items()}

    @staticmethod
    def _good_spot(s):
        return isinstance(s, list) and len(s) in (3, 4) and all(isinstance(v, float) for v in s)

    # ------------- writing
    def render(self):
        """The file's text with the model's changes applied. No changes gives back the original text."""
        e = Edits(self.text)
        self._write_hum(e)
        self._write_hide(e)
        self._write_worlds(e)
        self._write_hub_exits(e)
        self._write_portals(e)
        return e.result()

    def _write_hum(self, e):
        mode0, floor0, manual0 = self._orig_hum
        if self.hum_mode != mode0:
            e.set_field(self.root, "humMode", f'"{self.hum_mode}"')
        if self.hum_floor != floor0:
            e.set_field(self.root, "humFloor", fmt_num(self.hum_floor / 100))
        if self.hum_manual != manual0:
            e.set_field(self.root, "humManual", fmt_num(self.hum_manual / 100))

    def _block(self, e, key):
        """The table of a top-level block. If it is missing, returns None and the caller adds it whole."""
        it = self.root.get(key)
        return it.value if it and it.value.kind == "table" else None

    def _write_hide(self, e):
        if not self.hide_editable or self.hide == self._orig_hide:
            return
        block = self._block(e, "hideEmitters")

        def line(k):
            return f"{lua_key(k)} = {{ " + ", ".join(lua_string(n) for n in self.hide[k]) + " }"

        if block is None:
            self._add_block(e, "hideEmitters", [line(k) for k in sorted(self.hide)])
            return
        for k in self._orig_hide:
            item = block.get(k)
            if k not in self.hide:
                e.remove_item(block, item)
            elif self.hide[k] != self._orig_hide[k]:
                e.replace(item.start, item.value.end, line(k))
        for k in sorted(self.hide):
            if k not in self._orig_hide:
                e.add_item(block, line(k))

    def _add_block(self, e, key, lines, comment=()):
        """Add a whole top-level block, just above  portals  when there is one."""
        pad = "    "
        nl = e.nl
        body = f"{pad}{key} = {{{nl}" + "".join(f"{pad}{pad}{ln},{nl}" for ln in lines) + f"{pad}}},{nl}{nl}"
        text = "".join(f"{pad}{c}{nl}" for c in comment) + body
        anchor = self.root.get("portals")
        if anchor:
            at = e.line_start(anchor.start)
            e.replace(at, at, text)
        else:
            e.add_item(self.root, f"{key} = {{{nl}" + "".join(f"{pad}{pad}{ln},{nl}" for ln in lines) + f"{pad}}}", indent="")

    def world_text(self, w):
        pad = "            "
        nl = "\n"
        out = [f"{lua_key(w.id)} = {{"]
        out.append(f"{pad}loaderAsset = {lua_string(w.asset)},")
        out.append(f"{pad}loaderClass = {lua_string(w.cls)},")
        out.append(f"{pad}level       = {lua_string(w.level)},")
        out.append(f"{pad}origin      = {lua_nums(w.origin)},")
        if w.arrive is not None:
            out.append(f"{pad}arrive      = {lua_nums(w.arrive)},")
        out.append("        }")
        return nl.join(out)

    def _write_worlds(self, e):
        if not self.worlds_editable:
            return
        block = self._block(e, "worlds")
        keep = {id(w.item) for w in self.worlds if w.item is not None}
        if block is not None:
            for sub in block.items:
                if id(sub) not in keep:
                    e.remove_item(block, sub)
        new_worlds = [self.world_text(w).replace("\n", e.nl) for w in self.worlds if w.item is None]
        if block is None:
            if new_worlds:
                self._add_block(e, "worlds", new_worlds)
        else:
            for text in new_worlds:
                e.add_item(block, text)
        for w in self.worlds:
            if w.item is None:
                continue
            if not w.raw and w.snapshot() != self._orig_worlds[id(w.item)]:
                t = w.item.value
                orig = self._orig_worlds[id(w.item)]
                if w.id != orig[0]:
                    e.replace(w.item.start, w.item.key_end, lua_key(w.id))
                for key, new, old in (("loaderAsset", w.asset, orig[1]), ("loaderClass", w.cls, orig[2]), ("level", w.level, orig[3])):
                    if new != old:
                        e.set_field(t, key, lua_string(new))
                if w.origin != orig[4]:
                    e.set_field(t, "origin", lua_nums(w.origin))
                if w.arrive != orig[5]:
                    e.set_field(t, "arrive", None if w.arrive is None else lua_nums(w.arrive))

    def _write_hub_exits(self, e):
        if self.hub_exit_buff != self._orig_buff:
            value = None if self.hub_exit_buff is None else ("true" if self.hub_exit_buff else "false")
            if self.root.get("hubExitBuff"):
                e.set_field(self.root, "hubExitBuff", value)
            elif value is not None:
                self._add_top_line(e, f"hubExitBuff = {value},    -- see the hubExits note")
        if not self.hub_exits_editable or self.hub_exits == self._orig_exits:
            return

        def line(k):
            return f"{lua_key(k)} = {{ " + ", ".join(lua_nums(s) for s in self.hub_exits[k]) + " }"

        block = self._block(e, "hubExits")
        if block is None:
            self._add_block(e, "hubExits", [line(k) for k in sorted(self.hub_exits)],
                            ("-- Hub exits: extra pads inside a world that lead back to the hub, by destination pad ID.",
                             "-- Each spot is { x, y, z, yaw } in absolute world coordinates."))
            return
        for k in self._orig_exits:
            item = block.get(k)
            if k not in self.hub_exits:
                e.remove_item(block, item)
            elif self.hub_exits[k] != self._orig_exits[k]:
                e.replace(item.value.start, item.value.end, line(k).split(" = ", 1)[1])
        for k in sorted(self.hub_exits):
            if k not in self._orig_exits:
                e.add_item(block, line(k))

    def _add_top_line(self, e, text):
        anchor = self.root.get("portals")
        at = e.line_start(anchor.start) if anchor else e.line_start(self.root.end - 1)
        e.replace(at, at, f"    {text}{e.nl}{e.nl}")

    def _portal_text(self, p):
        parts = [f"slot = {lua_string(p.slot)}", f"name = {lua_string(p.name)}", f"destination = {lua_string(p.destination)}"]
        if p.design and p.design != DEFAULT_DESIGN:
            parts.append(f"design = {lua_string(p.design)}")
        if p.light_hex:
            parts.append(f"lightColor = {lua_nums(hex_to_rgb(p.light_hex))}")
        if abs(p.brightness - 1.0) > 0.0001:
            parts.append(f"lightBrightness = {fmt_num(p.brightness)}")
        return "{ " + ", ".join(parts) + " }"

    def _write_portals(self, e):
        block = self._block(e, "portals")
        active = {s: p for s, p in self.portals.items() if p.enabled}
        if block is None:
            if active:
                self._add_block(e, "portals", [self._portal_text(active[s]) for s in SLOT_IDS if s in active])
            return
        existing = [p for p in self.portals.values() if p.item is not None]
        for p in existing:
            if not p.enabled:
                e.remove_item(block, p.item)
            elif p.snapshot() != self._orig_portals[p.slot]:
                self._edit_portal(e, p)
        order = [s for s in SLOT_IDS]
        placed = sorted((p for p in existing if p.enabled), key=lambda p: order.index(p.slot))
        for s in order:
            p = active.get(s)
            if p is None or p.item is not None:
                continue
            after = next((q.item for q in placed if order.index(q.slot) > order.index(s)), None)
            e.add_item(block, self._portal_text(p), before=after)

    def _edit_portal(self, e, p):
        t = p.item.value
        o = self._orig_portals[p.slot]
        if p.name != o[0]:
            e.set_field(t, "name", lua_string(p.name))
        if p.destination != o[1]:
            e.set_field(t, "destination", lua_string(p.destination))
        if p.design != o[2]:
            e.set_field(t, "design", None if p.design == DEFAULT_DESIGN else lua_string(p.design))
        if p.light_hex.upper() != o[3]:
            e.set_field(t, "lightColor", lua_nums(hex_to_rgb(p.light_hex)) if p.light_hex else None)
        if round(p.brightness, 3) != o[4]:
            e.set_field(t, "lightBrightness", None if abs(p.brightness - 1.0) < 0.0001 else fmt_num(p.brightness))

    # ------------- saving
    def is_dirty(self):
        return self.render() != self.text

    def changed_on_disk(self):
        """True if the file no longer holds what was loaded (edited by hand, or by another copy of this tool)."""
        if not self.path or not os.path.exists(self.path):
            return False
        with open(self.path, "rb") as f:
            raw = f.read()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return raw != self.text.encode("utf-8")

    def save(self, path=None):
        """Check the new text reads back, keep the old file as .bak, then write UTF-8 without a BOM."""
        path = path or self.path
        text = self.render()
        Parser(text).find_return_table()         # never replace a good file with one that won't parse
        data = text.encode("utf-8")
        if os.path.exists(path):
            with open(path, "rb") as f:
                old = f.read()
            with open(path + ".bak", "wb") as f:
                f.write(old)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
