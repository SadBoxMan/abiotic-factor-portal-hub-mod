# Nexus page text for Portal Hub 1.0

For LuciDin to paste into the Nexus page (CRD-015). Nexus's description editor uses BBCode: the headings and lists below map to its
toolbar (or paste as plain text and format there). Change any wording you like; this file is a draft, not the page.

**Mod name:** Portal Hub (Cordona Corporations)

**Summary (one line):** Turns the Office Sector portal room into a real hub: fill its nine empty slots with portals to any of the game's
worlds, choose how each world's exits behave, and set it all up in a config editor.

---

## Description

**Cordona Corporations Portal Hub** turns the portal room in the Office Sector into a real hub. Extra portals fill the room's nine empty
slots, and each one can lead to any of the game's portal worlds, with its own look, light colour and brightness.

**What it does**
- Up to nine extra portals in the portal room, each to a world of your choice (the DLC areas excepted).
- **Exit modes** per portal: leave a world the game's way, always back to the hub, per player (dynamic), or through a **Manual Hub Exit**.
- **Manual Hub Exits**: an extra exit portal inside a world that always leads back to the hub (one in every portal world, placed by hand),
  with a **Failsafe Exit** in the portal room for worlds that have no hub portal.
- The portal hum gets quieter as you add portals (or set it yourself).
- **Config editor** (Windows): click a slot, pick a world, look, light and exit mode, then save. It checks your install too.
- Starts **blank**: you choose the portals. Or grab one of the author's **preset packs** (optional files): Pack 1 Demo, Pack 2 Story,
  Pack 3 Builder Worlds, Pack 4 Custom Worlds.
- **2.0 teaser** (in Pack 4): four small custom worlds (unsupported in 1.0), a first look at connecting worlds that are not in the game.

**Requirements**
- Abiotic Factor v1.5.0
- [UE4SS for Abiotic Factor](https://www.nexusmods.com/abioticfactor/mods/35), 1.25.0 or later

**Install:** install UE4SS, copy the zip's `AbioticFactor` folder into your game folder, and add `PortalHub : 1` to
`ue4ss\Mods\mods.txt` above `Keybinds : 1`. The README in the zip has every step, the exit modes and the known issues.

**Keys:** NUMPAD 1 respawns the hub portals, NUMPAD 2 removes them. That's all.

**Multiplayer (experimental):** the host's hub runs the portals for everyone; joining players don't need the mod for the game's own
worlds. Tested in two two-player sessions so far, so please report what you see.

**The config editor is an unsigned exe.** Windows may warn about it (More info > Run anyway). Its full Python source is included.

**Known issues:** see the README. In short: the **hub** exit mode and the true-exit buffs option are not tried in game yet; on very rare
occasions UE4SS stops all delayed actions (restart the game); custom worlds are a preview.

**Credits**
- By SadBoxMan (LuciDin), made with the help of Claude Code.
- Runs on UE4SS by the UE4SS team. Abiotic Factor by Deep Field Games; this mod is not made or endorsed by them.
- The world pictures in the editor are the game developers' art (from the Abiotic Factor wiki), shown for recognition only.

**Licence:** CC0 1.0 (public domain). Take it apart, change it, reuse it; credit welcome, not required. The project is on GitHub.

---

**File descriptions (Files tab):** Main file, Portal Hub 1.0.0: the hub and the config editor (blank, no portals of its own). Optional
files, one per preset pack: Pack 1 Demo (the flagship sample), Pack 2 Story, Pack 3 Builder Worlds, Pack 4 Custom Worlds (with the 2.0
teaser worlds). Upload only the packs that were built.
