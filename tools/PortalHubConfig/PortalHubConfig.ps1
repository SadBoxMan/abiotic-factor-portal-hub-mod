# Portal Hub Config - a small dark-mode editor for Scripts\config.lua
# Pick a world and a look for each open portal-room slot, then Save. No install needed (Windows PowerShell + WinForms).
# Launch with PortalHubConfig.bat. Optional switches for testing: -ConfigPath <file>, -Screenshot <png>, -RoundTrip <out.lua>
param(
    [string]$ConfigPath,
    [string]$Screenshot,
    [string]$RoundTrip
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class DwmDark {
    [DllImport("dwmapi.dll")] public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int val, int size);
    [DllImport("uxtheme.dll", CharSet = CharSet.Unicode)] public static extern int SetWindowTheme(IntPtr hwnd, string app, string idlist);
}
"@
# colours for the dark drop-down menus
Add-Type -ReferencedAssemblies System.Windows.Forms, System.Drawing -TypeDefinition @"
using System.Drawing;
using System.Windows.Forms;
public class DarkColorTable : ProfessionalColorTable {
    static Color bg = Color.FromArgb(43, 43, 52);
    static Color accent = Color.FromArgb(91, 124, 250);
    static Color border = Color.FromArgb(58, 58, 70);
    public override Color ToolStripDropDownBackground { get { return bg; } }
    public override Color ImageMarginGradientBegin { get { return bg; } }
    public override Color ImageMarginGradientMiddle { get { return bg; } }
    public override Color ImageMarginGradientEnd { get { return bg; } }
    public override Color MenuBorder { get { return border; } }
    public override Color MenuItemBorder { get { return accent; } }
    public override Color MenuItemSelected { get { return accent; } }
    public override Color MenuItemSelectedGradientBegin { get { return accent; } }
    public override Color MenuItemSelectedGradientEnd { get { return accent; } }
}
"@

# ---------------------------------------------------------------- finding config.lua
# The editor lives in tools\PortalHubConfig, away from the mod it edits, so it has to locate the mod's Scripts\config.lua:
#   1. the path remembered from last time,  2. the installed mod in a Steam library's Abiotic Factor folder,
#   3. the copy of the mod next to this tool in the repo,  4. a file picker.
$SettingsFile = Join-Path $env:APPDATA 'PortalHubConfig\config-path.txt'
function Find-ConfigPath {
    if (Test-Path $SettingsFile) {
        $saved = (Get-Content $SettingsFile -Raw).Trim()
        if ($saved -and (Test-Path $saved)) { return $saved }
    }
    $rel = 'steamapps\common\AbioticFactor\AbioticFactor\Binaries\Win64\ue4ss\Mods\PortalHub\Scripts\config.lua'
    $libs = @()
    foreach ($steam in @("${env:ProgramFiles(x86)}\Steam", "$env:ProgramFiles\Steam")) {
        if (-not (Test-Path $steam)) { continue }
        $libs += $steam
        $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += ($m.Groups[1].Value -replace '\\\\', '\') }
        }
    }
    foreach ($lib in ($libs | Select-Object -Unique)) {
        $candidate = Join-Path $lib $rel
        if (Test-Path $candidate) { return $candidate }
    }
    $repoCopy = Join-Path $PSScriptRoot '..\..\mod\PortalHub\Scripts\config.lua'
    if (Test-Path $repoCopy) { return (Resolve-Path $repoCopy).Path }
    return $null
}
function Select-ConfigPath {
    $dlg = New-Object Windows.Forms.OpenFileDialog
    $dlg.Title = 'Find the Portal Hub mod''s config.lua (Mods\PortalHub\Scripts\config.lua)'
    $dlg.Filter = 'config.lua|config.lua|Lua files|*.lua'
    if ($dlg.ShowDialog() -eq 'OK') { return $dlg.FileName }
    return $null
}
function Save-ConfigPath([string]$path) {
    try {
        New-Item -ItemType Directory -Force (Split-Path $SettingsFile) | Out-Null
        Set-Content -Path $SettingsFile -Value $path -Encoding UTF8
    } catch { }
}
if (-not $ConfigPath) {
    $ConfigPath = Find-ConfigPath
    if (-not $ConfigPath -and -not $Screenshot -and -not $RoundTrip) { $ConfigPath = Select-ConfigPath }
    if (-not $ConfigPath) { Write-Host 'No config.lua found.'; return }
    if (-not $Screenshot -and -not $RoundTrip) { Save-ConfigPath $ConfigPath }
}

# ---------------------------------------------------------------- data
# The 12 portal-room slots. A-1, A-2 and B-3 are the game's own portals and are locked.
$Slots = @(
    @{ Id = 'A-1'; Locked = 'Stone Garden'; Dest = 'H_Garden_Entrance' },
    @{ Id = 'A-2'; Locked = 'Torii';        Dest = 'H_Japan_Entrance' },
    @{ Id = 'A-3' }, @{ Id = 'A-4' },
    @{ Id = 'B-1' }, @{ Id = 'B-2' },
    @{ Id = 'B-3'; Locked = 'Cabin';        Dest = 'H_Cabin_Entrance' },
    @{ Id = 'B-4' },
    @{ Id = 'C-1' }, @{ Id = 'C-2' }, @{ Id = 'C-3' }, @{ Id = 'C-4' }
)

$DesignNames = @(
    'Niagara_Portal', 'Niagara_Portal_Blueverse', 'Niagara_Portal_Botanical_Green', 'Niagara_Portal_Botanical_Red',
    'Niagara_Portal_Dark', 'Niagara_Portal_Door', 'Niagara_Portal_Fog', 'Niagara_Portal_Friendly',
    'Niagara_Portal_Friendly_Black', 'Niagara_Portal_Friendly_Blue', 'Niagara_Portal_Friendly_Brown',
    'Niagara_Portal_Friendly_Cyan', 'Niagara_Portal_Friendly_Glitched', 'Niagara_Portal_Friendly_Green',
    'Niagara_Portal_Friendly_Lime', 'Niagara_Portal_Friendly_Orange', 'Niagara_Portal_Friendly_Pink',
    'Niagara_Portal_Friendly_Purple', 'Niagara_Portal_Friendly_Red', 'Niagara_Portal_Friendly_White',
    'Niagara_Portal_Friendly_Yellow', 'Niagara_Portal_Garden', 'Niagara_Portal_Greenverse',
    'Niagara_Portal_NightRDoor_2', 'Niagara_Portal_Redverse', 'Niagara_Portal_Rift',
    'Niagara_Portal_Salem', 'Niagara_Portal_Shadowgate2', 'Niagara_Portal_SnowFlurry', 'Niagara_Portal_SunDisk',
    'Niagara_Portal_Tiny', 'Niagara_Portal_Torii'
)

# The named parts (Niagara emitters) of each look, read from the game's effect files. The Effects button lets you switch parts
# of a look off; the choice is saved in config.lua's hideEmitters table and applies to every portal that uses that look.
$DesignParts = @{
    'Niagara_Portal' = @('lightning1', 'lightning2', 'portalmap', 'smoke', 'smoke2')
    'Niagara_Portal_Blueverse' = @('lightning1', 'lightning2', 'portalmap', 'smoke', 'smoke2')
    'Niagara_Portal_Botanical_Green' = @('Ivy', 'portal')
    'Niagara_Portal_Botanical_Red' = @('Ivy', 'portal')
    'Niagara_Portal_Dark' = @('lightning1', 'lightning2', 'portalmap', 'smoke')
    'Niagara_Portal_Door' = @('portal', 'smoke', 'sparks')
    'Niagara_Portal_Fog' = @('lightning1', 'lightning2', 'portalmap', 'smoke', 'smoke2')
    'Niagara_Portal_Friendly' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Black' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Blue' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Brown' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Cyan' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Glitched' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Green' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Lime' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Orange' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Pink' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Purple' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Red' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_White' = @('portal', 'sparks')
    'Niagara_Portal_Friendly_Yellow' = @('portal', 'sparks')
    'Niagara_Portal_Garden' = @('portal', 'sparks', 'Vine1', 'Vine2', 'Vine3', 'Vine4', 'Vine5', 'Vine6', 'Vine7', 'Vine8')
    'Niagara_Portal_Greenverse' = @('lightning1', 'lightning2', 'portalmap', 'smoke', 'smoke2')
    'Niagara_Portal_NightRDoor_2' = @('leaves001', 'portal', 'sparks')
    'Niagara_Portal_Redverse' = @('lightning1', 'lightning2', 'portalmap', 'smoke', 'smoke2')
    'Niagara_Portal_Rift' = @('distortion', 'rift', 'smoke', 'sparks')
    'Niagara_Portal_Salem' = @('portal', 'sparks')
    'Niagara_Portal_Shadowgate2' = @('portal', 'sparks')
    'Niagara_Portal_SnowFlurry' = @('Blackhole', 'smoke', 'snowflakes', 'SnowParticle01', 'SnowParticle02', 'Swirl')
    'Niagara_Portal_SunDisk' = @('Blackhole', 'smoke', 'snowflakes', 'SnowParticle01', 'SnowParticle02', 'Swirl')
    'Niagara_Portal_Tiny' = @('lightning2', 'smoke', 'smoke2')
    'Niagara_Portal_Torii' = @('HangingParticulates', 'portal')
}

# Parts that can never be switched off (the portal itself), and what named parts are known to be.
$ProtectedParts = @('portal', 'portalmap')
$PartNotes = @{ 'Niagara_Portal_SnowFlurry' = @{ 'Swirl' = 'accretion disk' } }
# Looks that come out too large; they get an (Oversized) tag in the Base Portal list.
$OversizedLooks = @('Niagara_Portal_Door', 'Niagara_Portal_NightRDoor_2')

# hideEmitters block <-> hashtable (look path -> parts switched off). Returns $null if the block uses a layout this can't read.
function Get-HideMap([string]$inner) {
    $map = @{}
    if ($null -eq $inner) { return $map }
    $clean = [regex]::Replace($inner, '(?m)^\s*--.*$', '')
    foreach ($m in [regex]::Matches($clean, '\[\s*"([^"]+)"\s*\]\s*=\s*\{([^{}]*)\}')) {
        $names = @([regex]::Matches($m.Groups[2].Value, '"([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Where-Object { $ProtectedParts -notcontains $_ })
        if ($names.Count -gt 0) { $map[$m.Groups[1].Value] = $names }
    }
    if ($map.Count -eq 0 -and $clean.Trim()) { return $null }
    return $map
}
function ConvertTo-HideInner($map) {
    $keys = @($map.Keys | Sort-Object)
    if ($keys.Count -eq 0) { return "`r`n    " }
    $lines = foreach ($k in $keys) { '        ["' + $k + '"] = { ' + (($map[$k] | ForEach-Object { '"' + $_ + '"' }) -join ', ') + ' },' }
    return "`r`n" + ($lines -join "`r`n") + "`r`n    "
}

function New-DesignItem([string]$name) {
    if ($name -eq 'Niagara_Portal') { $label = 'Default Portal' }       # the plain look is simply called Niagara_Portal in the game
    else { $label = ($name -replace '^Niagara_Portal_', '') -replace '_', ' ' }
    
    if ($OversizedLooks -contains $name) { $label += '  (Oversized)' }
    [pscustomobject]@{ Label = $label; Path = "/Game/Particles/$name.$name" }
}
# Known arrival pads you can pick in the Destination drop-down: one entrance per portal world (the pad that puts you
# INSIDE the world), taken from the wiki's list of portal worlds and matched to the game's data (DT_Levels + teleporter dump).
# Left out on purpose: Temple of Stone, Torii and Winter Cabin (the hub's own portals; Garden and Torii are DLC-gated),
# and exit / return / Facility-side pads. You can still type any other pad ID by hand, e.g. one from your own world.
# Look = the portal look the game uses for that world's entrance in the Facility (picked automatically when you choose the world).
#   From the game's data for Far Garden, Flathill, The Train, Furniture Store, The Mycofields, Voussoir, Village Den da'ko Yeer,
#   Shadowgate, Praetorium, GATE Arch, Rise and Dunkeltaler Forest. Canaan (Salem) and The Night Realm (NightRDoor_2) are
#   inferred from names. The rest have no particle-style entrance pad in the data, so they use the plain game portal.
# Listed in the wiki's progression order. Group = the heading shown in the drop-down; Icon = file name (without .png) in .\icons.
$KnownDestinations = @(
    @{ Group = 'Story';             Id = 'anteverse_a_start';  World = 'Far Garden';                 Icon = 'far-garden'; Look = 'Niagara_Portal' },
    @{ Group = 'Story';             Id = 'fog_start';          World = 'Flathill';                   Icon = 'flathill'; Look = 'Niagara_Portal_Fog' },
    @{ Group = 'Story';             Id = 'train_start';        World = 'The Train';                  Icon = 'the-train'; Look = 'Niagara_Portal' },
    @{ Group = 'Story';             Id = 'warehouse_start';    World = 'Furniture Store';            Icon = 'furniture-store'; Look = 'Niagara_Portal_Door' },
    @{ Group = 'Story';             Id = 'anteverse_b_start';  World = 'The Mycofields';             Icon = 'the-mycofields'; Look = 'Niagara_Portal' },
    @{ Group = 'Story';             Id = 'nightrealm_start_A'; World = 'The Night Realm';            Icon = 'the-night-realm'; Look = 'Niagara_Portal_NightRDoor_2' },
    @{ Group = 'Story';             Id = 'salem_begin';        World = 'Canaan';                     Icon = 'canaan'; Look = 'Niagara_Portal_Salem' },
    @{ Group = 'Story';             Id = 'alps_start';         World = 'Voussoir';                   Icon = 'voussoir'; Look = 'Niagara_Portal_SnowFlurry' },
    @{ Group = 'Story';             Id = 'anteverse_c_start';  World = "Village Den da'ko Yeer";     Icon = 'village-den-da-ko-yeer'; Look = 'Niagara_Portal_Blueverse' },
    @{ Group = 'Story';             Id = 'shadowgate_start';   World = 'Shadowgate';                 Icon = 'shadowgate'; Look = 'Niagara_Portal_Shadowgate2' },
    @{ Group = 'Story';             Id = 'INQ_Entrance';       World = 'Praetorium';                 Icon = 'praetorium'; Look = 'Niagara_Portal_Friendly' },
    @{ Group = 'Story';             Id = 'wall_start';         World = 'GATE Arch Defense Facility'; Icon = 'gate-arch-defense-facility'; Look = 'Niagara_Portal' },
    @{ Group = 'Story';             Id = 'island_start';       World = 'Albatross';                  Icon = 'albatross'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Major)';  Id = 'rise_start';         World = 'Rise';                       Icon = 'rise'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Major)';  Id = 'V_Snowglobe_Start';  World = 'North Pole';                 Icon = 'north-pole'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Major)';  Id = 'signal_start';       World = 'Dunkeltaler Forest';         Icon = 'dunkeltaler-forest'; Look = 'Niagara_Portal_Friendly_Red' },
    @{ Group = 'Optional (Major)';  Id = 'VWinter_Start';      World = 'Royal Range (IS-0083)';      Icon = 'royal-range'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Minor)';  Id = 'mirrorworld_start';  World = 'The World in the Mirror';    Icon = 'the-world-in-the-mirror'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Minor)';  Id = 'tile_entrance';      World = 'The Pool Room';              Icon = 'the-pool-room'; Look = 'Niagara_Portal' },
    @{ Group = 'Optional (Minor)';  Id = 'DistantShore';       World = 'Some Distant Shore';         Icon = 'some-distant-shore'; Look = 'Niagara_Portal' }
)
# The two DLC areas (Temple of Stone / Garden and Torii / Japan) can not be used as destinations: their entrance pads are DLC-gated
# in the game and a hub portal would bypass that. Matching is case-insensitive.
$DlcPads = @('H_Garden_Start', 'H_Garden_Entrance', 'H_Japan_Start', 'H_Japan_Entrance')
$KnownById = @{}
$DestWorldNames = @{}
foreach ($kd in $KnownDestinations) { $KnownById[$kd.Id] = $kd; $DestWorldNames[$kd.Id] = $kd.World }

# ---------------------------------------------------------------- world icons (optional)
# Small world icons shown to the left of the "Enabled" column, following the destination you pick. They are the wiki's
# portal-world icons (https://abioticfactor.wiki.gg/wiki/Locations#Portal_Worlds), kept in .\icons; Get-WorldIcons.ps1 re-downloads them.
# To turn the icons OFF: set $ShowWorldIcons = $false below, or just delete the icons folder (the column then disappears).
$ShowWorldIcons = $true
$IconSize = 28
$IconDir = Join-Path $PSScriptRoot 'icons'
$UseIcons = $ShowWorldIcons -and (Test-Path $IconDir) -and [bool](Get-ChildItem $IconDir -Filter '*.png' -ErrorAction SilentlyContinue)
$script:iconCache = @{}
function Get-WorldIcon([string]$slug) {
    if (-not $UseIcons -or -not $slug) { return $null }
    if ($script:iconCache.ContainsKey($slug)) { return $script:iconCache[$slug] }
    $bmp = $null
    $path = Join-Path $IconDir ($slug + '.png')
    if (Test-Path $path) {
        $src = [Drawing.Image]::FromFile($path)
        try {
            $bmp = New-Object Drawing.Bitmap($IconSize, $IconSize)
            $g = [Drawing.Graphics]::FromImage($bmp)
            $g.InterpolationMode = 'HighQualityBicubic'; $g.SmoothingMode = 'HighQuality'; $g.PixelOffsetMode = 'HighQuality'
            $g.DrawImage($src, 0, 0, $IconSize, $IconSize); $g.Dispose()
        } finally { $src.Dispose() }       # the cached copy is in memory, so the file is not left locked
    }
    $script:iconCache[$slug] = $bmp
    return $bmp
}
function Get-IconForDestination([string]$id) {
    $kd = $KnownById[$id.Trim()]
    if ($kd) { return (Get-WorldIcon $kd.Icon) }
    return $null
}

$DesignItems = @($DesignNames | ForEach-Object { New-DesignItem $_ })
$DefaultPath = $DesignItems[0].Path

# ---------------------------------------------------------------- config.lua read / write
# Returns each top-level { ... } table inside $text as a string (nested braces are kept inside their table).
function Get-LuaTopTables([string]$text) {
    $res = New-Object Collections.ArrayList; $depth = 0; $start = -1
    for ($i = 0; $i -lt $text.Length; $i++) {
        $ch = $text[$i]
        if ($ch -eq '{') { if ($depth -eq 0) { $start = $i }; $depth++ }
        elseif ($ch -eq '}') { $depth--; if ($depth -eq 0 -and $start -ge 0) { [void]$res.Add($text.Substring($start, $i - $start + 1)); $start = -1 } }
    }
    return ,$res.ToArray()
}

# Returns the text between the braces of  `key = { ... }`  (comments inside included), or $null if the key is absent.
function Get-LuaBlockInner([string]$text, [string]$key) {
    $m = [regex]::Match($text, '(?m)^\s*' + [regex]::Escape($key) + '\s*=\s*\{')
    if (-not $m.Success) { return $null }
    $start = $m.Index + $m.Length
    $depth = 1
    for ($i = $start; $i -lt $text.Length; $i++) {
        if ($text[$i] -eq '{') { $depth++ }
        elseif ($text[$i] -eq '}') { $depth--; if ($depth -eq 0) { return $text.Substring($start, $i - $start) } }
    }
    return $null
}

function Read-HubConfig([string]$path) {
    # Blocks = the size and emitter tables, kept verbatim so saving from the editor never wipes hand-tuned values.
    $result = @{ Header = $null; HumMode = 'dynamic'; HumFloor = 15; HumManual = 50; Portals = @{}; Blocks = @{} }
    if (-not (Test-Path $path)) { return $result }
    $text = [IO.File]::ReadAllText($path)
    $idx = $text.IndexOf('return {')
    if ($idx -gt 0) { $result.Header = $text.Substring(0, $idx).TrimEnd() }
    $body = if ($idx -ge 0) { $text.Substring($idx) } else { $text }
    foreach ($bk in 'hideEmitters', 'worlds') {
        $inner = Get-LuaBlockInner $body $bk
        if ($null -ne $inner) { $result.Blocks[$bk] = $inner }
    }
    $body = [regex]::Replace($body, '(?m)^\s*--.*$', '')        # drop commented-out lines
    $m = [regex]::Match($body, 'humFloor\s*=\s*([0-9.]+)')
    if ($m.Success) { $result.HumFloor = [math]::Round([double]::Parse($m.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture) * 100) }
    $m = [regex]::Match($body, 'humManual\s*=\s*([0-9.]+)')
    if ($m.Success) { $result.HumManual = [math]::Round([double]::Parse($m.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture) * 100) }
    $m = [regex]::Match($body, 'humMode\s*=\s*"(\w+)"')
    if ($m.Success -and @('dynamic', 'manual', 'default') -contains $m.Groups[1].Value) { $result.HumMode = $m.Groups[1].Value }
    $pInner = Get-LuaBlockInner $body 'portals'
    $entryTexts = if ($null -ne $pInner) { @(Get-LuaTopTables $pInner) } else { @() }
    foreach ($entryText in $entryTexts) {
        $fields = @{}
        foreach ($f in [regex]::Matches($entryText, '(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"')) {
            $fields[$f.Groups[1].Value] = ($f.Groups[2].Value -replace '\\(["\\])', '$1')
        }
        $lm = [regex]::Match($entryText, '\blightColor\s*=\s*\{([^{}]*)\}')
        if ($lm.Success) {
            $nums = @([regex]::Matches($lm.Groups[1].Value, '[0-9]*\.?[0-9]+') | ForEach-Object { [double]::Parse($_.Value, [Globalization.CultureInfo]::InvariantCulture) })
            if ($nums.Count -ge 3) {
                $b = $nums[0..2] | ForEach-Object { [int][math]::Round([math]::Min(1.0, [math]::Max(0.0, $_)) * 255) }
                $fields['lightHex'] = ('#{0:X2}{1:X2}{2:X2}' -f $b[0], $b[1], $b[2])
            }
        }
        $bm = [regex]::Match($entryText, '\blightBrightness\s*=\s*([0-9.]+)')
        if ($bm.Success) { $fields['lightBright'] = $bm.Groups[1].Value }
        if ($fields.slot) { $result.Portals[$fields.slot] = $fields }
    }
    return $result
}

function ConvertTo-LuaString([string]$s) { '"' + ($s -replace '\\', '\\' -replace '"', '\"') + '"' }

function ConvertTo-Fraction([int]$percent) { ([double]$percent / 100).ToString('0.##', [Globalization.CultureInfo]::InvariantCulture) }

function Write-HubConfig([string]$path, $header, [string]$humMode, [int]$humFloorPct, [int]$humManualPct, $portalList, $blocks) {
    if (-not $header) { $header = '-- Portal Hub configuration. Edit this file, or use PortalHubConfig.bat. Restart mods to apply.' }
    $sb = New-Object Text.StringBuilder
    [void]$sb.AppendLine($header)
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('return {')
    [void]$sb.AppendLine('    -- Hub portal volume (the looping hum of the portals in the portal room):')
    [void]$sb.AppendLine('    --   "dynamic"  unchanged with the game''s 3 base portals, then an equal step down per added portal, reaching')
    [void]$sb.AppendLine('    --              humFloor when every open slot is filled.')
    [void]$sb.AppendLine('    --   "manual"   every hub portal uses humManual.')
    [void]$sb.AppendLine('    --   "default"  leave the game''s volume alone.')
    [void]$sb.AppendLine('    humMode = "' + $humMode + '",')
    [void]$sb.AppendLine('    humFloor = ' + (ConvertTo-Fraction $humFloorPct) + ',    -- dynamic: lowest volume, 0 to 1')
    [void]$sb.AppendLine('    humManual = ' + (ConvertTo-Fraction $humManualPct) + ',    -- manual: volume, 0 to 1')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('    -- Parts of a portal effect to switch off, by look. Example: hide the "Swirl" part (the accretion disk) of the SnowFlurry look:')
    [void]$sb.AppendLine('    --   ["/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry"] = { "Swirl" },')
    [void]$sb.AppendLine('    -- SnowFlurry parts: Blackhole, smoke, snowflakes, SnowParticle01, SnowParticle02, Swirl.  The portal part of a look can never be switched off.')
    $hideInner = if ($blocks -and $null -ne $blocks['hideEmitters']) { $blocks['hideEmitters'] } else { "`r`n    " }
    [void]$sb.AppendLine('    hideEmitters = {' + $hideInner + '},')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('    -- Custom worlds: worlds that ship their own pak. A world is loaded by spawning its "loader" actor Blueprint, and a')
    [void]$sb.AppendLine('    -- teleporter pad with the world''s id is spawned at origin + arrive, so a hub portal can use that id as its destination.')
    [void]$sb.AppendLine('    -- Example (remove the leading -- to use):')
    [void]$sb.AppendLine('    --   mymod_start = { loaderAsset = "/Game/Mods/MyWorld/BP_MyWorldLoader", loaderClass = "BP_MyWorldLoader_C",')
    [void]$sb.AppendLine('    --     level = "/Game/Mods/MyWorld/Maps/MyWorld_L0", origin = { 1000000, 1200000, 0 }, arrive = { 700, -350, 30, -27 } },')
    [void]$sb.AppendLine('    -- loaderAsset / loaderClass: the loader actor in the pak.  level: the map it streams (used to see when it is ready).')
    [void]$sb.AppendLine('    -- origin: where the loader is spawned (far from the Facility).  arrive: the arrival pad, relative to origin: x, y, z (floor) and yaw.')
    $worldsInner = if ($blocks -and $null -ne $blocks['worlds']) { $blocks['worlds'] } else { "`r`n    " }
    [void]$sb.AppendLine('    worlds = {' + $worldsInner + '},')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('    portals = {')
    foreach ($p in $portalList) {
        $line = '        { slot = ' + (ConvertTo-LuaString $p.slot) + ', name = ' + (ConvertTo-LuaString $p.name) + ', destination = ' + (ConvertTo-LuaString $p.destination)
        if ($p.design -and $p.design -ne $DefaultPath) { $line += ', design = ' + (ConvertTo-LuaString $p.design) }
        if ($p.lightHex -match '^#[0-9A-Fa-f]{6}$') {
            $rgb = 1..5 | Where-Object { $_ % 2 -eq 1 } | ForEach-Object { [Convert]::ToInt32($p.lightHex.Substring($_, 2), 16) / 255.0 }
            $line += ', lightColor = { ' + (($rgb | ForEach-Object { $_.ToString('0.###', [Globalization.CultureInfo]::InvariantCulture) }) -join ', ') + ' }'
        }
        $bv = 0.0
        if ($p.lightBright -and [double]::TryParse([string]$p.lightBright, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$bv) -and [math]::Abs($bv - 1.0) -gt 0.0001) {
            $line += ', lightBrightness = ' + $bv.ToString('0.###', [Globalization.CultureInfo]::InvariantCulture)
        }
        [void]$sb.AppendLine($line + ' },')
    }
    [void]$sb.AppendLine('    },')
    [void]$sb.AppendLine('}')
    if (Test-Path $path) { Copy-Item $path ($path + '.bak') -Force }
    [IO.File]::WriteAllText($path, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
}

# ---------------------------------------------------------------- custom worlds (config.lua's  worlds = { id = { ... } }  block)
$LuaReserved = @('and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function', 'goto', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then', 'true', 'until', 'while')
function Format-Num([double]$n) { $n.ToString('0.###', [Globalization.CultureInfo]::InvariantCulture) }
$NumRx = '-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'

# One world entry -> an editable item. If the entry is not exactly the five known fields (an unknown field, a trailing comment,
# a missing value) it is kept as written (Raw) and shown read-only, so nothing a person typed by hand is ever lost.
function ConvertFrom-WorldEntry([string]$id, [string]$inside, [string]$raw) {
    $item = [pscustomobject]@{ Id = $id; Asset = ''; Class = ''; Level = ''; Origin = @(0, 0, 0); Arrive = @(0, 0, 0, 0); Raw = $raw; ClassAuto = $false; Bad = '' }
    $left = $inside
    $str = @{}
    foreach ($f in [regex]::Matches($inside, '\b(loaderAsset|loaderClass|level)\s*=\s*"((?:[^"\\]|\\.)*)"')) {
        $str[$f.Groups[1].Value] = ($f.Groups[2].Value -replace '\\(["\\])', '$1')
        $left = $left.Replace($f.Value, '')
    }
    $nums = @{}
    foreach ($key in 'origin', 'arrive') {
        $mm = [regex]::Match($inside, '\b' + $key + '\s*=\s*\{([^{}]*)\}')
        if ($mm.Success) {
            $vals = @([regex]::Matches($mm.Groups[1].Value, $NumRx) | ForEach-Object { [double]::Parse($_.Value, [Globalization.CultureInfo]::InvariantCulture) })
            $leftover = [regex]::Replace($mm.Groups[1].Value, $NumRx, '') -replace '[\s,]', ''
            if (-not $leftover) { $nums[$key] = $vals }
            $left = $left.Replace($mm.Value, '')
        }
    }
    $clean = $str.ContainsKey('loaderAsset') -and $str.ContainsKey('loaderClass') -and $str.ContainsKey('level') `
        -and $nums.ContainsKey('origin') -and $nums['origin'].Count -eq 3 `
        -and $nums.ContainsKey('arrive') -and ($nums['arrive'].Count -eq 3 -or $nums['arrive'].Count -eq 4) `
        -and -not ($left -replace '[\s,]', '')
    if ($clean) {
        $item.Asset = $str['loaderAsset']; $item.Class = $str['loaderClass']; $item.Level = $str['level']
        $item.Origin = @($nums['origin'])
        $a = @($nums['arrive']); if ($a.Count -eq 3) { $a += 0.0 }
        $item.Arrive = $a
        $item.Raw = $null
    }
    return $item
}

# Reads the worlds block. Whole-line comments are kept (Notes) and written back first. If anything other than entries sits in
# the block, Editable is $false and the block is saved exactly as it was.
function Get-WorldList([string]$inner) {
    $res = @{ Items = @(); Notes = @(); Editable = $true }
    if ($null -eq $inner) { return $res }
    $notes = New-Object Collections.ArrayList
    $body = New-Object Text.StringBuilder
    foreach ($line in ($inner -split "\r?\n")) {
        if ($line -match '^\s*--') { [void]$notes.Add($line.Trim()) } else { [void]$body.AppendLine($line) }
    }
    $res.Notes = @($notes)
    $text = $body.ToString()
    $keyRx = [regex]'(?:\["(?<q>[^"]+)"\]|(?<id>[A-Za-z_][A-Za-z0-9_]*))\s*=\s*\{'
    $items = New-Object Collections.ArrayList
    $rest = New-Object Text.StringBuilder
    $pos = 0
    while ($pos -lt $text.Length) {
        $m = $keyRx.Match($text, $pos)
        if (-not $m.Success) { [void]$rest.Append($text.Substring($pos)); break }
        [void]$rest.Append($text.Substring($pos, $m.Index - $pos))
        $start = $m.Index + $m.Length; $depth = 1; $j = $start
        while ($j -lt $text.Length) {
            $ch = $text[$j]
            if ($ch -eq '{') { $depth++ } elseif ($ch -eq '}') { $depth--; if ($depth -eq 0) { break } }
            $j++
        }
        if ($depth -ne 0) { $res.Editable = $false; return $res }
        $id = if ($m.Groups['q'].Success) { $m.Groups['q'].Value } else { $m.Groups['id'].Value }
        [void]$items.Add((ConvertFrom-WorldEntry $id $text.Substring($start, $j - $start) $text.Substring($m.Index, $j - $m.Index + 1)))
        $pos = $j + 1
    }
    if ($rest.ToString() -replace '[\s,]', '') { $res.Editable = $false }
    $res.Items = @($items)
    return $res
}

function ConvertTo-WorldsInner($items, $notes) {
    $lines = @()
    foreach ($n in @($notes)) { $lines += '        ' + $n }
    foreach ($w in @($items)) {
        if ($w.Raw) { $r = $w.Raw.TrimEnd(); if (-not $r.EndsWith(',')) { $r += ',' }; $lines += '        ' + $r; continue }
        $key = if ($w.Id -match '^[A-Za-z_][A-Za-z0-9_]*$' -and $LuaReserved -notcontains $w.Id) { $w.Id } else { '["' + $w.Id + '"]' }
        $lines += '        ' + $key + ' = {'
        $lines += '            loaderAsset = ' + (ConvertTo-LuaString $w.Asset) + ','
        $lines += '            loaderClass = ' + (ConvertTo-LuaString $w.Class) + ','
        $lines += '            level       = ' + (ConvertTo-LuaString $w.Level) + ','
        $lines += '            origin      = { ' + (($w.Origin | ForEach-Object { Format-Num $_ }) -join ', ') + ' },'
        $lines += '            arrive      = { ' + (($w.Arrive | ForEach-Object { Format-Num $_ }) -join ', ') + ' },'
        $lines += '        },'
    }
    if ($lines.Count -eq 0) { return "`r`n    " }
    return "`r`n" + ($lines -join "`r`n") + "`r`n    "
}

$cfg = Read-HubConfig $ConfigPath
$script:hideMap = Get-HideMap $cfg.Blocks['hideEmitters']
$script:hideEditable = ($null -ne $script:hideMap)
if (-not $script:hideEditable) { $script:hideMap = @{} }
$wl = Get-WorldList $cfg.Blocks['worlds']
$script:worlds = @($wl.Items); $script:worldNotes = @($wl.Notes); $script:worldsEditable = $wl.Editable
function Test-UserWorld([string]$id) { foreach ($w in $script:worlds) { if ($w.Id -ceq $id) { return $true } }; return $false }
function Get-BlocksForSave {
    $b = @{}; foreach ($k in $cfg.Blocks.Keys) { $b[$k] = $cfg.Blocks[$k] }
    if ($script:hideEditable) { $b['hideEmitters'] = ConvertTo-HideInner $script:hideMap }
    if ($script:worldsEditable) { $b['worlds'] = ConvertTo-WorldsInner $script:worlds $script:worldNotes }
    return $b
}

if ($RoundTrip) {
    $list = @($cfg.Portals.Keys | Sort-Object | ForEach-Object { $p = $cfg.Portals[$_]; @{ slot = $p.slot; name = $p.name; destination = $p.destination; design = $p.design; lightHex = $p.lightHex; lightBright = $p.lightBright } })
    Write-HubConfig $RoundTrip $cfg.Header $cfg.HumMode $cfg.HumFloor $cfg.HumManual $list (Get-BlocksForSave)
    return
}

# ---------------------------------------------------------------- theme
function C([string]$hex) { [Drawing.ColorTranslator]::FromHtml($hex) }
$colBg = C '#17171c'; $colPanel = C '#202027'; $colInput = C '#2b2b34'; $colBorder = C '#3a3a46'
$colFg = C '#e8e8ee'; $colMuted = C '#8d8d9b'; $colAccent = C '#5b7cfa'; $colLocked = C '#7a7a88'; $colBad = C '#5a2a30'

$fontBase = New-Object Drawing.Font('Segoe UI', 9.5)
$fontBold = New-Object Drawing.Font('Segoe UI Semibold', 9.5)
$fontTitle = New-Object Drawing.Font('Segoe UI Semibold', 15)

function New-Label([string]$text, $font, $color) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Font = $font; $l.ForeColor = $color; $l.AutoSize = $false
    $l.Dock = 'Fill'; $l.TextAlign = 'MiddleLeft'; $l.BackColor = [Drawing.Color]::Transparent
    return $l
}
function New-TextBox([string]$text) {
    $t = New-Object Windows.Forms.TextBox
    $t.Text = $text; $t.Font = $fontBase; $t.BackColor = $colInput; $t.ForeColor = $colFg
    $t.BorderStyle = 'FixedSingle'; $t.Dock = 'Fill'; $t.Margin = New-Object Windows.Forms.Padding(2, 5, 8, 5)
    return $t
}
function Get-EffectsText([string]$designPath) {
    $n = 0
    if ($script:hideMap.ContainsKey($designPath)) { $n = @($script:hideMap[$designPath]).Count }
    if ($n -gt 0) { return "Effects ($n off)" }
    return 'Effects'
}
function Update-EffectButtons {
    foreach ($r in $script:rows) { $r.Fx.Text = Get-EffectsText $r.Combo.SelectedItem.Path }
}

# Dark dialog: one checkbox per named part of a look (ticked = part is on). OK saves the choice for that look.
function Show-EffectsDialog([string]$designPath, [string]$designLabel) {
    $name = $designPath -replace '^.*\.', ''
    $parts = @($DesignParts[$name])
    if (-not $parts.Count -or -not $parts[0]) { [void][Windows.Forms.MessageBox]::Show("No named parts were found for this look.", 'Effects'); return }
    $hidden = @(); if ($script:hideMap.ContainsKey($designPath)) { $hidden = @($script:hideMap[$designPath]) }
    $dlg = New-Object Windows.Forms.Form
    $dlg.Text = 'Effects - ' + $designLabel; $dlg.StartPosition = 'CenterParent'; $dlg.FormBorderStyle = 'FixedDialog'
    $dlg.MaximizeBox = $false; $dlg.MinimizeBox = $false; $dlg.ShowInTaskbar = $false
    $dlg.BackColor = $colBg; $dlg.ForeColor = $colFg; $dlg.Font = $fontBase
    $dlg.ClientSize = New-Object Drawing.Size(420, (150 + 28 * $parts.Count))
    $dlg.Add_HandleCreated({ $v = 1; [void][DwmDark]::DwmSetWindowAttribute($dlg.Handle, 20, [ref]$v, 4) }.GetNewClosure())
    $head = New-Object Windows.Forms.Label
    $head.Text = "Tick the parts of this look you want ON. Unticked parts are switched off for every portal that uses it."
    $head.ForeColor = $colMuted; $head.Location = New-Object Drawing.Point(18, 14); $head.Size = New-Object Drawing.Size(384, 44)
    $dlg.Controls.Add($head)
    $boxes = @()
    $y = 66
    foreach ($p in $parts) {
        $cb = New-Object Windows.Forms.CheckBox
        $cb.Tag = $p
        $suffix = ''
        if ($ProtectedParts -contains $p) { $suffix = '  (always on)' }
        elseif ($PartNotes.ContainsKey($name) -and $PartNotes[$name].ContainsKey($p)) { $suffix = '  (' + $PartNotes[$name][$p] + ')' }
        $cb.Text = $p + $suffix
        $cb.Checked = ($ProtectedParts -contains $p) -or ($hidden -notcontains $p)
        if ($ProtectedParts -contains $p) { $cb.Enabled = $false }
        $cb.ForeColor = $colFg; $cb.AutoSize = $true
        $cb.Location = New-Object Drawing.Point(26, $y); $y += 28
        $dlg.Controls.Add($cb); $boxes += $cb
    }
    $note = New-Object Windows.Forms.Label
    $note.Text = 'Part names come from the game''s effect file. Untested: the game may ignore switching a part off.'
    $note.ForeColor = $colMuted; $note.Location = New-Object Drawing.Point(18, ($y + 6)); $note.Size = New-Object Drawing.Size(384, 36)
    $dlg.Controls.Add($note)
    $ok = New-Object Windows.Forms.Button; $cancel = New-Object Windows.Forms.Button; $all = New-Object Windows.Forms.Button
    foreach ($b in $ok, $cancel, $all) {
        $b.FlatStyle = 'Flat'; $b.Font = $fontBold; $b.Height = 32; $b.Width = 96; $b.ForeColor = $colFg
        $b.BackColor = $colInput; $b.FlatAppearance.BorderColor = $colBorder; $b.Top = $dlg.ClientSize.Height - 48
    }
    $ok.Text = 'OK'; $ok.Left = 206; $ok.BackColor = $colAccent; $ok.FlatAppearance.BorderColor = $colAccent; $ok.DialogResult = 'OK'
    $cancel.Text = 'Cancel'; $cancel.Left = 310; $cancel.DialogResult = 'Cancel'
    $all.Text = 'All on'; $all.Left = 18
    $all.Add_Click({ foreach ($b in $boxes) { $b.Checked = $true } }.GetNewClosure())
    $dlg.Controls.AddRange(@($ok, $cancel, $all)); $dlg.AcceptButton = $ok; $dlg.CancelButton = $cancel
    if ($script:ShotMode) { return $dlg }       # screenshot mode: hand the form back instead of showing it
    if ($dlg.ShowDialog($form) -eq 'OK') {
        $off = @($boxes | Where-Object { -not $_.Checked } | ForEach-Object { $_.Tag })
        if ($off.Count -gt 0) { $script:hideMap[$designPath] = $off } else { $script:hideMap.Remove($designPath) }
        Update-EffectButtons
        Update-SaveState
    }
}

# ---------------------------------------------------------------- custom worlds dialog
# Checks every world in the list. Errors block Apply; warnings (origins that may overlap) are shown but allowed.
function Get-WorldProblems($items) {
    $out = @()
    for ($i = 0; $i -lt $items.Count; $i++) {
        $w = $items[$i]; $err = @(); $warn = @()
        if ($w.Raw) { $out += [pscustomobject]@{ Errors = @(); Warnings = @() }; continue }
        $id = [string]$w.Id
        if (-not $id) { $err += 'Enter a world ID.' }
        elseif ($id -notmatch '^[A-Za-z0-9_\-]+$') { $err += 'The world ID can use letters, numbers, _ and - only.' }
        elseif ($id -like 'hub_*') { $err += 'IDs starting with hub_ are reserved for the hub''s own portals.' }
        elseif ($KnownById.Keys -contains $id) { $err += 'That ID is one of the game''s own pads; pick your own.' }
        else {
            for ($k = 0; $k -lt $items.Count; $k++) { if ($k -ne $i -and [string]$items[$k].Id -ieq $id) { $err += 'Another world already uses this ID.'; break } }
        }
        if ([string]$w.Asset -notmatch '^/[A-Za-z0-9_/\-]+[A-Za-z0-9_\-]$') { $err += 'Loader Blueprint: enter its package path, like /Game/Mods/MyWorld/BP_MyWorldLoader (no dots, no spaces).' }
        if ([string]$w.Class -notmatch '^[A-Za-z0-9_]+_C$') { $err += 'Loader class should end in _C, like BP_MyWorldLoader_C.' }
        if ([string]$w.Level -notmatch '^/[A-Za-z0-9_/\-]+[A-Za-z0-9_\-]$') { $err += 'Level: enter the map''s package path, like /Game/Mods/MyWorld/Maps/MyWorld_L0.' }
        if ($w.Bad) { $err += $w.Bad }
        else {
            $ox = [double]$w.Origin[0]; $oy = [double]$w.Origin[1]; $oz = [double]$w.Origin[2]
            if ([math]::Max([math]::Abs($ox), [math]::Abs($oy)) -lt 500000) { $warn += 'This origin is close to the Facility''s own levels. Use a far one (1,000,000 or more).' }
            for ($k = 0; $k -lt $items.Count; $k++) {
                if ($k -eq $i -or $items[$k].Raw) { continue }
                $d = [math]::Sqrt([math]::Pow($ox - [double]$items[$k].Origin[0], 2) + [math]::Pow($oy - [double]$items[$k].Origin[1], 2) + [math]::Pow($oz - [double]$items[$k].Origin[2], 2))
                $other = $(if ($items[$k].Id) { $items[$k].Id } else { 'another world' })
                if ($d -lt 1) { $err += "Same origin as '$other': the two worlds would load on top of each other." }
                elseif ($d -lt 100000) { $warn += ("Only {0:N0} units from '{1}'. Worlds bigger than that would overlap." -f $d, $other) }
            }
        }
        $out += [pscustomobject]@{ Errors = $err; Warnings = $warn }
    }
    return $out
}
function Get-NextOrigin($items, $skip) {
    $x = $null; $y = 1200000.0
    foreach ($w in $items) { if ($w.Raw -or [object]::ReferenceEquals($w, $skip)) { continue }; if ($null -eq $x -or [double]$w.Origin[0] -gt $x) { $x = [double]$w.Origin[0]; $y = [double]$w.Origin[1] } }
    if ($null -eq $x) { return @(1000000.0, 1200000.0, 0.0) }
    return @(($x + 200000.0), $y, 0.0)
}
function Update-WorldsButton {
    $n = @($script:worlds).Count
    if ($script:worldsEditable) { $btnWorlds.Text = "Custom worlds ($n)" } else { $btnWorlds.Text = 'Custom worlds (view)' }
}

function Show-WorldsDialog {
    if (-not $script:worldsEditable) {
        [void][Windows.Forms.MessageBox]::Show("The worlds section of config.lua uses a layout this editor can't read, so it is left exactly as written. Edit it in config.lua.", 'Custom worlds')
        return
    }
    $work = New-Object Collections.ArrayList
    foreach ($w in $script:worlds) { [void]$work.Add([pscustomobject]@{ Id = $w.Id; Asset = $w.Asset; Class = $w.Class; Level = $w.Level; Origin = @($w.Origin); Arrive = @($w.Arrive); Raw = $w.Raw; ClassAuto = $false; Bad = '' }) }
    $st = @{ Index = -1; Guard = $false; Problems = @() }
    $colWarn = C '#f5b563'; $colErr = C '#ff9b9b'; $colOk = C '#7be09a'

    $dlg = New-Object Windows.Forms.Form
    $dlg.Text = 'Custom worlds'; $dlg.StartPosition = 'CenterParent'; $dlg.FormBorderStyle = 'FixedDialog'
    $dlg.MaximizeBox = $false; $dlg.MinimizeBox = $false; $dlg.ShowInTaskbar = $false
    $dlg.BackColor = $colBg; $dlg.ForeColor = $colFg; $dlg.Font = $fontBase
    $dlg.ClientSize = New-Object Drawing.Size(900, 700)
    $dlg.Add_HandleCreated({ $v = 1; [void][DwmDark]::DwmSetWindowAttribute($dlg.Handle, 20, [ref]$v, 4) }.GetNewClosure())

    $title2 = New-Object Windows.Forms.Label
    $title2.Text = 'Custom worlds'; $title2.Font = $fontTitle; $title2.ForeColor = $colFg; $title2.AutoSize = $true; $title2.Location = New-Object Drawing.Point(20, 14)
    $sub2 = New-Object Windows.Forms.Label
    $sub2.Text = 'Connect a world that ships its own pak. Each world gets an ID; a hub portal uses that ID as its destination.'
    $sub2.ForeColor = $colMuted; $sub2.AutoSize = $true; $sub2.Location = New-Object Drawing.Point(22, 48)
    $dlg.Controls.AddRange(@($title2, $sub2))

    # --- left: the list of worlds
    $list = New-Object Windows.Forms.ListBox
    $list.DrawMode = 'OwnerDrawFixed'; $list.ItemHeight = 34; $list.BorderStyle = 'None'; $list.IntegralHeight = $false
    $list.BackColor = $colInput; $list.ForeColor = $colFg; $list.Font = $fontBase
    $list.Location = New-Object Drawing.Point(20, 84); $list.Size = New-Object Drawing.Size(236, 500)
    $list.Add_HandleCreated({ [void][DwmDark]::SetWindowTheme($list.Handle, 'DarkMode_Explorer', $null) }.GetNewClosure())
    $btnAdd = New-Button 'Add world' $true;  $btnAdd.Width = 114; $btnAdd.Location = New-Object Drawing.Point(20, 594)
    $btnDel = New-Button 'Remove' $false;    $btnDel.Width = 114; $btnDel.Location = New-Object Drawing.Point(142, 594)
    $dlg.Controls.AddRange(@($list, $btnAdd, $btnDel))

    # --- right: the form, in three tidy groups
    $right = New-Object Windows.Forms.Panel
    $right.Location = New-Object Drawing.Point(284, 84); $right.Size = New-Object Drawing.Size(596, 540); $right.BackColor = $colBg
    $dlg.Controls.Add($right)
    $fontSmall = New-Object Drawing.Font('Segoe UI', 8.5)
    $mkHead = { param($t, $y) $l = New-Object Windows.Forms.Label; $l.Text = $t; $l.Font = $fontBold; $l.ForeColor = $colAccent; $l.AutoSize = $true; $l.Location = New-Object Drawing.Point(0, $y); $right.Controls.Add($l) }.GetNewClosure()
    $mkCap = { param($t, $x, $y) $l = New-Object Windows.Forms.Label; $l.Text = $t; $l.ForeColor = $colFg; $l.AutoSize = $true; $l.Location = New-Object Drawing.Point($x, $y); $right.Controls.Add($l) }.GetNewClosure()
    $mkHint = { param($t, $x, $y) $l = New-Object Windows.Forms.Label; $l.Text = $t; $l.Font = $fontSmall; $l.ForeColor = $colMuted; $l.AutoSize = $false; $l.Size = New-Object Drawing.Size(580, 18); $l.Location = New-Object Drawing.Point($x, $y); $right.Controls.Add($l) }.GetNewClosure()
    $mkBox = {
        param($x, $y, $w)
        $t = New-Object Windows.Forms.TextBox
        $t.Font = $fontBase; $t.BackColor = $colInput; $t.ForeColor = $colFg; $t.BorderStyle = 'FixedSingle'
        $t.Location = New-Object Drawing.Point($x, $y); $t.Width = $w
        $right.Controls.Add($t); return $t
    }.GetNewClosure()

    & $mkHead 'IDENTITY' 0
    & $mkCap 'World ID' 0 24
    $tbId = & $mkBox 0 44 300
    & $mkHint 'You choose this. A hub portal''s destination must be exactly this text. Letters, numbers, _ and - only.' 0 72

    & $mkHead 'LOADER AND LEVEL' 106
    & $mkCap 'Loader Blueprint (package path)' 0 130
    $tbAsset = & $mkBox 0 150 580
    & $mkHint 'The Blueprint in your pak that streams your map in, e.g. /Game/Mods/MyWorld/BP_MyWorldLoader' 0 178
    & $mkCap 'Loader class' 0 206
    $tbClass = & $mkBox 0 226 300
    & $mkHint 'Filled in for you: the Blueprint''s name plus _C.' 316 230
    & $mkCap 'Level (map package path)' 0 264
    $tbLevel = & $mkBox 0 284 580
    & $mkHint 'Your map, e.g. /Game/Mods/MyWorld/Maps/MyWorld_L0. Used to tell when the level has finished loading.' 0 312

    & $mkHead 'PLACEMENT' 348
    & $mkCap 'Origin  (x, y, z)' 0 372
    $numBoxes = @()
    foreach ($k in 0..2) { $b = & $mkBox ($k * 120) 392 108; $b.TextAlign = 'Center'; $numBoxes += $b }
    $btnSuggest = New-Button 'Suggest an origin' $false; $btnSuggest.Width = 150; $btnSuggest.Height = 28; $btnSuggest.Location = New-Object Drawing.Point(390, 390)
    $right.Controls.Add($btnSuggest)
    & $mkHint 'Where the world is loaded. Keep it far from the Facility, and different for every world.' 0 420
    & $mkCap 'Arrival pad  (x, y, floor z, yaw)' 0 448
    foreach ($k in 0..3) { $b = & $mkBox ($k * 120) 468 108; $b.TextAlign = 'Center'; $numBoxes += $b }
    & $mkHint 'The pad players arrive at and return through, relative to the origin. Yaw is the way it faces.' 0 496
    $msg = New-Object Windows.Forms.Label
    $msg.AutoSize = $false; $msg.Location = New-Object Drawing.Point(0, 524); $msg.Size = New-Object Drawing.Size(590, 16); $msg.ForeColor = $colMuted
    $right.Controls.Add($msg)
    $empty = New-Object Windows.Forms.Label
    $empty.Text = "No custom worlds yet.`r`n`r`nClick Add world to connect a world from your own pak. The test-world walkthrough shows how to build one: docs/test-world-walkthrough.html"
    $empty.ForeColor = $colMuted; $empty.AutoSize = $false; $empty.Location = New-Object Drawing.Point(284, 100); $empty.Size = New-Object Drawing.Size(560, 90)
    $dlg.Controls.Add($empty)
    $inputs = @($tbId, $tbAsset, $tbClass, $tbLevel) + $numBoxes + @($btnSuggest)

    # --- bottom bar
    $note = New-Object Windows.Forms.Label
    $note.Text = 'Applied changes are written to config.lua when you press Save in the main window.'
    $note.ForeColor = $colMuted; $note.Font = $fontSmall; $note.AutoSize = $true; $note.Location = New-Object Drawing.Point(20, 664)
    $btnApply = New-Button 'Apply' $true; $btnApply.Width = 110; $btnApply.Location = New-Object Drawing.Point(660, 654)
    $btnCancel = New-Button 'Cancel' $false; $btnCancel.Width = 110; $btnCancel.Location = New-Object Drawing.Point(780, 654); $btnCancel.DialogResult = 'Cancel'
    $dlg.Controls.AddRange(@($note, $btnApply, $btnCancel)); $dlg.CancelButton = $btnCancel

    # --- behaviour
    $refreshUi = {
        $st.Problems = @(Get-WorldProblems @($work))
        $list.Invalidate()
        $has = ($work.Count -gt 0)
        $empty.Visible = (-not $has); $right.Visible = $has; $btnDel.Enabled = ($st.Index -ge 0)
        $errCount = 0; foreach ($p in $st.Problems) { if (@($p.Errors).Count -gt 0) { $errCount++ } }
        $btnApply.Enabled = ($errCount -eq 0)
        if ($errCount -eq 0) { $btnApply.BackColor = $colAccent; $btnApply.ForeColor = $colFg } else { $btnApply.BackColor = $colInput; $btnApply.ForeColor = $colMuted }
        if ($st.Index -ge 0 -and $st.Index -lt $work.Count) {
            $w = $work[$st.Index]; $p = $st.Problems[$st.Index]
            if ($w.Raw) { $msg.ForeColor = $colMuted; $msg.Text = 'This entry uses a layout the editor can''t read. It is kept exactly as written; edit it in config.lua.' }
            elseif (@($p.Errors).Count -gt 0) { $msg.ForeColor = $colErr; $msg.Text = [string]$p.Errors[0] }
            elseif (@($p.Warnings).Count -gt 0) { $msg.ForeColor = $colWarn; $msg.Text = [string]$p.Warnings[0] }
            else { $msg.ForeColor = $colOk; $msg.Text = 'Looks good.' }
        } else { $msg.Text = '' }
    }.GetNewClosure()
    $load = {
        $st.Guard = $true
        $i = $st.Index
        if ($i -ge 0 -and $i -lt $work.Count) {
            $w = $work[$i]
            $tbId.Text = [string]$w.Id; $tbAsset.Text = [string]$w.Asset; $tbClass.Text = [string]$w.Class; $tbLevel.Text = [string]$w.Level
            foreach ($k in 0..2) { $numBoxes[$k].Text = Format-Num $w.Origin[$k] }
            foreach ($k in 0..3) { $numBoxes[3 + $k].Text = Format-Num $w.Arrive[$k] }
            foreach ($c in $inputs) { $c.Enabled = (-not $w.Raw) }
        } else { foreach ($c in $inputs) { $c.Text = ''; $c.Enabled = $false } }
        $st.Guard = $false
        & $refreshUi
    }.GetNewClosure()
    $list.Add_DrawItem({
        param($s, $e)
        if ($e.Index -lt 0) { return }
        $w = $work[$e.Index]
        $hot = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
        $b1 = New-Object Drawing.SolidBrush($(if ($hot) { $colAccent } else { $colInput }))
        $b2 = New-Object Drawing.SolidBrush($colFg); $b3 = New-Object Drawing.SolidBrush($(if ($hot) { $colFg } else { $colMuted }))
        $e.Graphics.FillRectangle($b1, $e.Bounds)
        $label = $(if ($w.Id) { [string]$w.Id } else { '(new world)' })
        $dot = $colOk; $p = $null
        if ($e.Index -lt $st.Problems.Count) { $p = $st.Problems[$e.Index] }
        if ($w.Raw) { $dot = $colMuted } elseif ($p -and @($p.Errors).Count -gt 0) { $dot = $colErr } elseif ($p -and @($p.Warnings).Count -gt 0) { $dot = $colWarn }
        $bd = New-Object Drawing.SolidBrush($dot)
        $e.Graphics.FillEllipse($bd, ($e.Bounds.X + 10), ($e.Bounds.Y + 13), 8, 8)
        $e.Graphics.DrawString($label, $e.Font, $b2, ($e.Bounds.X + 28), ($e.Bounds.Y + 3))
        $sub = $(if ($w.Raw) { 'kept as written' } elseif ($w.Level) { ($w.Level -replace '^.*/', '') } else { 'not finished' })
        $e.Graphics.DrawString($sub, $fontSmall, $b3, ($e.Bounds.X + 28), ($e.Bounds.Y + 18))
        $b1.Dispose(); $b2.Dispose(); $b3.Dispose(); $bd.Dispose()
    }.GetNewClosure())
    $list.Add_SelectedIndexChanged({ if ($st.Guard) { return }; $st.Index = $list.SelectedIndex; & $load }.GetNewClosure())

    $edited = {
        if ($st.Guard -or $st.Index -lt 0 -or $st.Index -ge $work.Count) { return }
        $w = $work[$st.Index]
        $w.Id = $tbId.Text.Trim(); $w.Asset = $tbAsset.Text.Trim(); $w.Level = $tbLevel.Text.Trim(); $w.Class = $tbClass.Text.Trim()
        $vals = @(); $bad = ''
        foreach ($nb in $numBoxes) {
            $v = 0.0
            if ([double]::TryParse($nb.Text.Trim(), [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$v)) { $vals += $v } else { $bad = 'Origin and arrival values must be numbers.'; $vals += 0.0 }
        }
        $w.Bad = $bad
        if (-not $bad) { $w.Origin = @($vals[0..2]); $w.Arrive = @($vals[3..6]) }
        & $refreshUi
    }.GetNewClosure()
    foreach ($c in @($tbId, $tbAsset, $tbLevel) + $numBoxes) { $c.Add_TextChanged($edited) }
    $tbClass.Add_TextChanged({ if (-not $st.Guard -and $st.Index -ge 0) { $work[$st.Index].ClassAuto = $false }; & $edited }.GetNewClosure())
    # typing the Blueprint's path fills in its class (name + _C) until you edit the class yourself
    $tbAsset.Add_TextChanged({
        if ($st.Guard -or $st.Index -lt 0) { return }
        $w = $work[$st.Index]
        if (-not $w.Class -or $w.ClassAuto) {
            $seg = ($tbAsset.Text.Trim() -replace '^.*/', '')
            $st.Guard = $true; $tbClass.Text = $(if ($seg) { $seg + '_C' } else { '' }); $st.Guard = $false
            $w.Class = $tbClass.Text; $w.ClassAuto = [bool]$seg
            & $edited
        }
    }.GetNewClosure())

    $btnSuggest.Add_Click({
        if ($st.Index -lt 0) { return }
        $o = Get-NextOrigin @($work) $work[$st.Index]
        $st.Guard = $true; foreach ($k in 0..2) { $numBoxes[$k].Text = Format-Num $o[$k] }; $st.Guard = $false
        $work[$st.Index].Origin = @($o); $work[$st.Index].Bad = ''
        & $edited
    }.GetNewClosure())
    $btnAdd.Add_Click({
        $base = 'myworld_start'; $n = 1; $id = $base
        while (@($work | Where-Object { $_.Id -ieq $id }).Count -gt 0) { $n++; $id = "myworld${n}_start" }
        $o = Get-NextOrigin @($work) $null
        [void]$work.Add([pscustomobject]@{ Id = $id; Asset = ''; Class = ''; Level = ''; Origin = @($o); Arrive = @(0.0, 0.0, 0.0, 0.0); Raw = $null; ClassAuto = $true; Bad = '' })
        $list.Items.Add($id) | Out-Null
        $st.Guard = $true; $list.SelectedIndex = $work.Count - 1; $st.Guard = $false
        $st.Index = $work.Count - 1; & $load
        [void]$tbId.Focus(); $tbId.SelectAll()
    }.GetNewClosure())
    $btnDel.Add_Click({
        $i = $st.Index
        if ($i -lt 0 -or $i -ge $work.Count) { return }
        $id = [string]$work[$i].Id
        if (-not $script:ShotMode) {
            $users = @($script:rows | Where-Object { $_.Check.Checked -and $_.Dest.Input.Text.Trim() -ceq $id } | ForEach-Object { $_.Slot })
            $q = "Remove the world '$id'?"
            if ($users.Count -gt 0) { $q += "`r`n`r`nPortal " + ($users -join ', ') + " still leads to it. That portal will have nothing to load until you pick another destination." }
            if ([Windows.Forms.MessageBox]::Show($q, 'Remove world', 'YesNo', 'Question') -ne 'Yes') { return }
        }
        $work.RemoveAt($i); $list.Items.RemoveAt($i)
        $st.Index = [math]::Min($i, $work.Count - 1)
        $st.Guard = $true; $list.SelectedIndex = $st.Index; $st.Guard = $false
        & $load
    }.GetNewClosure())
    $btnApply.Add_Click({
        $script:worlds = @($work | ForEach-Object { $_ })
        Update-WorldsButton
        foreach ($r in $script:rows) {
            $t = $r.Dest.Input.Text.Trim()
            $r.Dest.Input.ReadOnly = ($t -eq '' -or $KnownById.ContainsKey($t) -or (Test-UserWorld $t))
        }
        $dlg.DialogResult = 'OK'; $dlg.Close()
    }.GetNewClosure())

    foreach ($w in $work) { [void]$list.Items.Add([string]$w.Id) }
    if ($work.Count -gt 0) { $list.SelectedIndex = 0; $st.Index = 0 }
    & $load
    if ($script:ShotMode) { return $dlg }
    [void]$dlg.ShowDialog($form)
}

# Light colour: a drop-down of rainbow presets. "Default" leaves the pad's own light colour alone; "Custom" opens a colour picker.
$LightPresets = @(
    [pscustomobject]@{ Label = 'Default'; Hex = ''; Kind = 'none' },
    [pscustomobject]@{ Label = 'Red';     Hex = '#FF2020'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Orange';  Hex = '#FF8A1A'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Yellow';  Hex = '#FFE81A'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Green';   Hex = '#2EE65C'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Blue';    Hex = '#2A6BFF'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Indigo';  Hex = '#4B2AB5'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Violet';  Hex = '#A030FF'; Kind = 'preset' },
    [pscustomobject]@{ Label = 'Custom';  Hex = ''; Kind = 'custom' }
)
function Get-LightHex($combo) {
    $it = $combo.SelectedItem
    if (-not $it) { return '' }
    if ($it.Kind -eq 'custom') { return [string]$combo.Tag.CustomHex }
    return [string]$it.Hex
}
function New-LightCombo([string]$hex) {
    $cb = New-Object Windows.Forms.ComboBox
    $cb.DropDownStyle = 'DropDownList'; $cb.FlatStyle = 'Flat'; $cb.Font = $fontBase
    $cb.BackColor = $colInput; $cb.ForeColor = $colFg; $cb.Dock = 'Fill'
    $cb.Margin = New-Object Windows.Forms.Padding(2, 5, 4, 5)
    $cb.DrawMode = 'OwnerDrawFixed'; $cb.ItemHeight = 24; $cb.DropDownHeight = 260
    $cb.DisplayMember = 'Label'
    foreach ($p in $LightPresets) { [void]$cb.Items.Add($p) }
    $cb.Tag = @{ CustomHex = ''; Previous = 0; Guard = $false }
    $idx = 0
    if ($hex -match '^#[0-9A-Fa-f]{6}$') {
        $hit = $LightPresets | Where-Object { $_.Kind -eq 'preset' -and $_.Hex -ieq $hex } | Select-Object -First 1
        if ($hit) { $idx = [array]::IndexOf($LightPresets, $hit) }
        else { $idx = $LightPresets.Count - 1; $cb.Tag.CustomHex = $hex.ToUpper() }
    }
    $cb.SelectedIndex = $idx
    $cb.Tag.Previous = $idx
    $cb.Add_DrawItem({
        param($s, $e)
        if ($e.Index -lt 0) { return }
        $item = $s.Items[$e.Index]
        $hot = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
        $b1 = New-Object Drawing.SolidBrush($(if ($hot) { $colAccent } else { $colInput }))
        $b2 = New-Object Drawing.SolidBrush($colFg)
        $e.Graphics.FillRectangle($b1, $e.Bounds)
        $show = ''
        if ($item.Kind -eq 'preset') { $show = $item.Hex }
        elseif ($item.Kind -eq 'custom' -and $s.Tag.CustomHex) { $show = $s.Tag.CustomHex }
        $x = $e.Bounds.X + 6
        if ($show) {
            $sw = New-Object Drawing.SolidBrush([Drawing.ColorTranslator]::FromHtml($show))
            $e.Graphics.FillRectangle($sw, $x, $e.Bounds.Y + 5, 14, 14); $sw.Dispose()
            $x += 20
        }
        $text = $item.Label
        if ($item.Kind -eq 'custom' -and $s.Tag.CustomHex) { $text = 'Custom ' + $s.Tag.CustomHex }
        $e.Graphics.DrawString($text, $e.Font, $b2, $x, ($e.Bounds.Y + 3))
        $b1.Dispose(); $b2.Dispose()
    })
    $cb.Add_SelectedIndexChanged({
        param($s2, $e2)
        if ($s2.Tag.Guard) { return }
        if ($s2.SelectedIndex -ge 0 -and $s2.SelectedItem.Kind -eq 'custom') {
            # Custom: open the colour picker; cancelling puts the previous choice back
            $dlg = New-Object Windows.Forms.ColorDialog
            $dlg.FullOpen = $true; $dlg.AnyColor = $true
            if ($s2.Tag.CustomHex -match '^#[0-9A-Fa-f]{6}$') { $dlg.Color = [Drawing.ColorTranslator]::FromHtml($s2.Tag.CustomHex) }
            if ($dlg.ShowDialog($form) -eq 'OK') {
                $s2.Tag.CustomHex = ('#{0:X2}{1:X2}{2:X2}' -f $dlg.Color.R, $dlg.Color.G, $dlg.Color.B)
                $s2.Tag.Previous = $s2.SelectedIndex
                $s2.Invalidate()
            } else {
                $s2.Tag.Guard = $true; $s2.SelectedIndex = $s2.Tag.Previous; $s2.Tag.Guard = $false
            }
        } else { $s2.Tag.Previous = $s2.SelectedIndex }
    })
    return $cb
}
function New-DestControl([string]$text) {
    # A text box you can type any pad ID into, plus a button that opens a dark menu of known arrival pads.
    # (Built by hand because Windows draws a disabled editable ComboBox light grey, which breaks dark mode.)
    $panel = New-Object Windows.Forms.Panel
    $panel.Dock = 'Fill'; $panel.Margin = New-Object Windows.Forms.Padding(2, 5, 8, 5); $panel.BackColor = $colInput
    $tb = New-Object Windows.Forms.TextBox
    $tb.Text = $text; $tb.Font = $fontBase; $tb.BackColor = $colInput; $tb.ForeColor = $colFg
    $tb.BorderStyle = 'FixedSingle'; $tb.Dock = 'Fill'
    # A listed world (or an empty row) is chosen from the list; only "Custom Destination" lets you type an ID.
    $tb.ReadOnly = ($text -eq '' -or $KnownById.ContainsKey($text) -or (Test-UserWorld $text)); $tb.BackColor = $colInput
    $btn = New-Object Windows.Forms.Button
    $btn.Text = [string][char]0x25BE; $btn.FlatStyle = 'Flat'; $btn.Dock = 'Right'; $btn.Width = 30
    $btn.BackColor = $colInput; $btn.ForeColor = $colFg; $btn.FlatAppearance.BorderSize = 1; $btn.FlatAppearance.BorderColor = $colBorder
    $btn.TabStop = $false
    $panel.Controls.Add($tb)      # added first so the button docks to the right edge and the text box fills the rest
    $panel.Controls.Add($btn)
    # The pop-up is a scrolling dark list (about 8 rows visible), so it keeps working when many worlds are listed.
    $rowH = 26; $visibleRows = 10
    $list = New-Object Windows.Forms.ListBox
    $list.DrawMode = 'OwnerDrawFixed'; $list.ItemHeight = $rowH; $list.BorderStyle = 'None'; $list.IntegralHeight = $false
    $list.BackColor = $colInput; $list.ForeColor = $colFg; $list.Font = $fontBase
    # group headings (Story / Optional ...) are inserted as non-selectable rows. Rebuilt each time the menu opens, so worlds
    # added in the Custom worlds dialog show up straight away.
    $fillList = {
        $list.Items.Clear()
        $lastGroup = $null
        foreach ($kd in $KnownDestinations) {
            if ($kd.Group -ne $lastGroup) { [void]$list.Items.Add([pscustomobject]@{ Header = $kd.Group; Id = $null }); $lastGroup = $kd.Group }
            [void]$list.Items.Add([pscustomobject]@{ Header = $null; Id = $kd.Id })
        }
        $mine = @($script:worlds | Where-Object { -not $_.Raw -and $_.Id })
        if ($mine.Count -gt 0) {
            [void]$list.Items.Add([pscustomobject]@{ Header = 'Your worlds'; Id = $null })
            foreach ($w in $mine) { [void]$list.Items.Add([pscustomobject]@{ Header = $null; Id = [string]$w.Id }) }
        }
        # last entry: type any pad ID yourself (an existing pad that is not listed)
        [void]$list.Items.Add([pscustomobject]@{ Header = 'Custom'; Id = $null })
        [void]$list.Items.Add([pscustomobject]@{ Header = $null; Id = '__custom__' })
        $list.Size = New-Object Drawing.Size(640, ([math]::Min([math]::Max($list.Items.Count, 1), $visibleRows) * $rowH + 2))
    }.GetNewClosure()
    & $fillList
    $list.Add_HandleCreated({ [void][DwmDark]::SetWindowTheme($list.Handle, 'DarkMode_Explorer', $null) }.GetNewClosure())
    $list.Add_DrawItem({
        param($s, $e)
        if ($e.Index -lt 0) { return }
        $item = $s.Items[$e.Index]
        if ($item.Header) {
            $bh = New-Object Drawing.SolidBrush($colPanel); $bt = New-Object Drawing.SolidBrush($colAccent)
            $e.Graphics.FillRectangle($bh, $e.Bounds)
            $e.Graphics.DrawString($item.Header.ToUpper(), $fontBold, $bt, ($e.Bounds.X + 6), ($e.Bounds.Y + 4))
            $bh.Dispose(); $bt.Dispose(); return
        }
        $id = [string]$item.Id
        $hot = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
        $b1 = New-Object Drawing.SolidBrush($(if ($hot) { $colAccent } else { $colInput }))
        $b2 = New-Object Drawing.SolidBrush($colFg)
        $b3 = New-Object Drawing.SolidBrush($(if ($hot) { $colFg } else { $colMuted }))
        $e.Graphics.FillRectangle($b1, $e.Bounds)
        if ($id -eq '__custom__') {
            $e.Graphics.DrawString('Custom Destination', $e.Font, $b2, ($e.Bounds.X + 14), ($e.Bounds.Y + 4))
            $e.Graphics.DrawString('type the pad ID of your own world', $e.Font, $b3, ($e.Bounds.X + 270), ($e.Bounds.Y + 4))
        } else {
            $info = $KnownById[$id]
            if ($info) { $e.Graphics.DrawString($info.World, $e.Font, $b2, ($e.Bounds.X + 14), ($e.Bounds.Y + 4)) }
            elseif (Test-UserWorld $id) { $e.Graphics.DrawString($id, $e.Font, $b2, ($e.Bounds.X + 14), ($e.Bounds.Y + 4)) }
            if ($info -or -not (Test-UserWorld $id)) { $e.Graphics.DrawString($id, $e.Font, $b3, ($e.Bounds.X + 270), ($e.Bounds.Y + 4)) }
            else { $e.Graphics.DrawString('custom world', $e.Font, $b3, ($e.Bounds.X + 270), ($e.Bounds.Y + 4)) }
        }
        $b1.Dispose(); $b2.Dispose(); $b3.Dispose()
    })
    $listHost = New-Object Windows.Forms.ToolStripControlHost($list)
    $listHost.AutoSize = $false; $listHost.Size = $list.Size
    $listHost.Margin = New-Object Windows.Forms.Padding(0); $listHost.Padding = New-Object Windows.Forms.Padding(0)
    $drop = New-Object Windows.Forms.ToolStripDropDown
    $drop.Padding = New-Object Windows.Forms.Padding(1); $drop.BackColor = $colBorder
    $drop.Renderer = New-Object Windows.Forms.ToolStripProfessionalRenderer((New-Object DarkColorTable))
    [void]$drop.Items.Add($listHost)
    $choose = {
        $i = $list.SelectedIndex
        if ($i -lt 0 -or $list.Items[$i].Header) { return }
        $id = [string]$list.Items[$i].Id
        $tgt = $panel.Tag
        if ($id -eq '__custom__') {
            # Custom Destination: clear the row's world and let the user type any pad ID
            $tb.ReadOnly = $false; $tb.BackColor = $colInput; $tb.Text = ''
            if ($tgt) { $tgt.Name.Text = ''; $tgt.Combo.SelectedIndex = 0 }
            $drop.Close(); [void]$tb.Focus(); return
        }
        $tb.ReadOnly = $true; $tb.BackColor = $colInput
        $tb.Text = $id
        # picking a world from the list sets the Name box and the portal look to that world's defaults
        if ($tgt -and $KnownById.ContainsKey($id)) {
            $tgt.Name.Text = $KnownById[$id].World
            $want = "/Game/Particles/$($KnownById[$id].Look).$($KnownById[$id].Look)"
            foreach ($it in $tgt.Combo.Items) { if ($it.Path -eq $want) { $tgt.Combo.SelectedItem = $it; break } }
        } elseif ($tgt -and (Test-UserWorld $id)) {
            $tgt.Name.Text = $id         # one of your own worlds: the portal's name starts as its ID (rename it freely)
        }
        $drop.Close()
    }.GetNewClosure()
    $list.Add_MouseMove({ param($s, $e) $i = $s.IndexFromPoint($e.Location); if ($i -ge 0 -and -not $s.Items[$i].Header -and $s.SelectedIndex -ne $i) { $s.SelectedIndex = $i } })
    $list.Add_MouseUp($choose)
    $list.Add_KeyDown({ param($s, $e) if ($e.KeyCode -eq 'Return') { & $choose } }.GetNewClosure())
    $btn.Add_Click({
        & $fillList
        $listHost.Size = $list.Size
        $cur = -1
        for ($k = 0; $k -lt $list.Items.Count; $k++) { if ($list.Items[$k].Id -eq $tb.Text.Trim()) { $cur = $k; break } }
        $list.SelectedIndex = $cur
        $drop.Show($btn, (New-Object Drawing.Point(0, $btn.Height)))
        $list.Focus() | Out-Null
    }.GetNewClosure())
    $tb.Add_Click({ if ($tb.ReadOnly -and $panel.Enabled) { $btn.PerformClick() } }.GetNewClosure())
    Add-Member -InputObject $panel -NotePropertyName Input -NotePropertyValue $tb
    Add-Member -InputObject $panel -NotePropertyName Drop -NotePropertyValue $drop
    Add-Member -InputObject $panel -NotePropertyName List -NotePropertyValue $list
    Add-Member -InputObject $panel -NotePropertyName Button -NotePropertyValue $btn
    return $panel
}
function New-DesignCombo([string]$selectedPath) {
    $cb = New-Object Windows.Forms.ComboBox
    $cb.DropDownStyle = 'DropDownList'; $cb.FlatStyle = 'Flat'; $cb.Font = $fontBase
    $cb.BackColor = $colInput; $cb.ForeColor = $colFg; $cb.Dock = 'Fill'
    $cb.Margin = New-Object Windows.Forms.Padding(2, 5, 8, 5)
    $cb.DrawMode = 'OwnerDrawFixed'; $cb.ItemHeight = 24; $cb.DropDownHeight = 340
    $cb.DisplayMember = 'Label'
    foreach ($d in $DesignItems) { [void]$cb.Items.Add($d) }
    $match = $DesignItems | Where-Object { $_.Path -eq $selectedPath } | Select-Object -First 1
    if (-not $match -and $selectedPath) {      # a custom path from a hand-edited config: keep it
        $match = [pscustomobject]@{ Label = 'Custom: ' + $selectedPath; Path = $selectedPath }
        [void]$cb.Items.Add($match)
    }
    if (-not $match) { $match = $DesignItems[0] }
    $cb.SelectedItem = $match
    $cb.Add_DrawItem({
        param($s, $e)
        if ($e.Index -lt 0) { return }
        $selected = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
        $back = if ($selected) { $colAccent } else { $colInput }
        $b1 = New-Object Drawing.SolidBrush($back); $b2 = New-Object Drawing.SolidBrush($colFg)
        $e.Graphics.FillRectangle($b1, $e.Bounds)
        $e.Graphics.DrawString($s.Items[$e.Index].Label, $e.Font, $b2, ($e.Bounds.X + 5), ($e.Bounds.Y + 3))
        $b1.Dispose(); $b2.Dispose()
    })
    return $cb
}

# ---------------------------------------------------------------- form
$form = New-Object Windows.Forms.Form
$form.Text = 'Portal Hub Config'
$form.StartPosition = 'CenterScreen'
$form.ClientSize = New-Object Drawing.Size(1290, 690)
$form.MinimumSize = New-Object Drawing.Size(900, 560)
$form.BackColor = $colBg; $form.ForeColor = $colFg; $form.Font = $fontBase
$form.Add_HandleCreated({ $v = 1; [void][DwmDark]::DwmSetWindowAttribute($form.Handle, 20, [ref]$v, 4) })

$header = New-Object Windows.Forms.Panel
$header.Dock = 'Top'; $header.Height = 78; $header.BackColor = $colBg
$title = New-Object Windows.Forms.Label
$title.Text = 'Portal Hub'; $title.Font = $fontTitle; $title.ForeColor = $colFg; $title.AutoSize = $true
$title.Location = New-Object Drawing.Point(20, 12)
$sub = New-Object Windows.Forms.Label
$sub.Text = "Choose which world each portal-room slot leads to and how its portal looks. The three game portals are locked."
$sub.Font = $fontBase; $sub.ForeColor = $colMuted; $sub.AutoSize = $true; $sub.Location = New-Object Drawing.Point(22, 46)
$header.Controls.AddRange(@($title, $sub))

$footer = New-Object Windows.Forms.Panel
$footer.Dock = 'Bottom'; $footer.Height = 96; $footer.BackColor = $colPanel

$grid = New-Object Windows.Forms.TableLayoutPanel
$grid.Dock = 'Fill'; $grid.AutoScroll = $true; $grid.BackColor = $colBg
$grid.Padding = New-Object Windows.Forms.Padding(16, 0, 16, 8)
$grid.ColumnCount = 9
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 64)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', $(if ($UseIcons) { 44 } else { 0 }))))   # world icon column (0 wide when icons are off)
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 84)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 32)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 28)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 40)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 112)))  # Effects
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 168)))  # Light colour
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 80)))   # Light brightness

$rowIndex = 0
function Add-GridRow($controls, [int]$height) {
    [void]$grid.RowStyles.Add((New-Object Windows.Forms.RowStyle('Absolute', $height)))
    for ($i = 0; $i -lt $controls.Count; $i++) { if ($controls[$i]) { $grid.Controls.Add($controls[$i], $i, $script:rowIndex) } }
    $script:rowIndex++
}
$grid.RowCount = 0
$grid.Add_HandleCreated({ [void][DwmDark]::SetWindowTheme($grid.Handle, 'DarkMode_Explorer', $null) })    # dark scrollbar
Add-GridRow @((New-Label 'Slot' $fontBold $colMuted), $null, (New-Label 'Enabled' $fontBold $colMuted), (New-Label 'Name' $fontBold $colMuted), (New-Label 'Destination pad ID' $fontBold $colMuted), (New-Label 'Base Portal' $fontBold $colMuted), (New-Label 'Effects' $fontBold $colMuted), (New-Label 'Light' $fontBold $colMuted), (New-Label 'Bright' $fontBold $colMuted)) 30

$script:rows = @()
foreach ($s in $Slots) {
    $slotLabel = New-Label $s.Id $fontBold $colFg
    if ($s.Locked) {
        $enabled = New-Label 'Locked' $fontBase $colLocked
        $name = New-Label ('Game portal: ' + $s.Locked) $fontBase $colLocked
        $dest = New-Label $s.Dest $fontBase $colLocked
        $look = New-Label 'Fixed by the game' $fontBase $colLocked
        Add-GridRow @($slotLabel, $null, $enabled, $name, $dest, $look, $null, $null, $null) 38
        continue
    }
    $existing = $cfg.Portals[$s.Id]
    $chk = New-Object Windows.Forms.CheckBox
    $chk.Text = ''; $chk.Dock = 'Fill'; $chk.CheckAlign = 'MiddleCenter'; $chk.BackColor = [Drawing.Color]::Transparent
    $chk.Checked = [bool]$existing
    $nameBox = New-TextBox ($(if ($existing) { $existing.name } else { '' }))
    $destBox = New-DestControl ($(if ($existing) { $existing.destination } else { '' }))
    $combo = New-DesignCombo ($(if ($existing -and $existing.design) { $existing.design } else { $DefaultPath }))
    # world icon: follows whatever destination ID is in the box; hidden while the row is unticked
    $pic = $null
    if ($UseIcons) {
        $pic = New-Object Windows.Forms.PictureBox
        $pic.Dock = 'Fill'; $pic.SizeMode = 'CenterImage'; $pic.BackColor = [Drawing.Color]::Transparent
        $pic.Image = Get-IconForDestination ($(if ($existing) { $existing.destination } else { '' }))
        $destBox.Input.Add_TextChanged({ param($s2, $e2) $pic.Image = Get-IconForDestination $s2.Text }.GetNewClosure())
    }
    $destBox.Tag = @{ Name = $nameBox; Combo = $combo }
    $fxBtn = New-Object Windows.Forms.Button
    $fxBtn.FlatStyle = 'Flat'; $fxBtn.Font = $fontBase; $fxBtn.Dock = 'Fill'; $fxBtn.Margin = New-Object Windows.Forms.Padding(2, 5, 2, 5)
    $fxBtn.BackColor = $colInput; $fxBtn.ForeColor = $colFg; $fxBtn.FlatAppearance.BorderColor = $colBorder
    $fxBtn.Text = Get-EffectsText $combo.SelectedItem.Path
    $lightCtl = New-LightCombo ($(if ($existing -and $existing.lightHex) { [string]$existing.lightHex } else { '' }))
    $brightBox = New-Object Windows.Forms.NumericUpDown
    $brightBox.DecimalPlaces = 1; $brightBox.Increment = 0.1; $brightBox.Minimum = 0.1; $brightBox.Maximum = 20; $brightBox.Value = 1.0
    if ($existing -and $existing.lightBright) { try { $bv = [decimal]::Parse([string]$existing.lightBright, [Globalization.CultureInfo]::InvariantCulture); $brightBox.Value = [math]::Min([decimal]20, [math]::Max([decimal]0.1, $bv)) } catch { } }
    $brightBox.BackColor = $colInput; $brightBox.ForeColor = $colFg; $brightBox.BorderStyle = 'FixedSingle'
    $brightBox.Dock = 'Fill'; $brightBox.Margin = New-Object Windows.Forms.Padding(2, 7, 4, 7); $brightBox.TextAlign = 'Center'
    $row = [pscustomobject]@{ Slot = $s.Id; Check = $chk; Name = $nameBox; Dest = $destBox; Combo = $combo; Pic = $pic; Fx = $fxBtn; Light = $lightCtl; Bright = $brightBox }
    $apply = {
        param($r)
        $on = $r.Check.Checked
        $r.Name.Enabled = $on; $r.Dest.Enabled = $on; $r.Combo.Enabled = $on; $r.Fx.Enabled = $on; $r.Light.Enabled = $on; $r.Bright.Visible = $on
        if ($r.Pic) { $r.Pic.Visible = $on }
    }
    $chk.Tag = $row
    $chk.Add_CheckedChanged({ param($s2, $e2) $r = $s2.Tag; $on = $r.Check.Checked; if (-not $on) { $r.Name.Text = ''; $r.Dest.Input.Text = ''; $r.Dest.Input.ReadOnly = $true; $r.Combo.SelectedIndex = 0; $r.Light.SelectedIndex = 0; $r.Bright.Value = 1.0 }; $r.Name.Enabled = $on; $r.Dest.Enabled = $on; $r.Combo.Enabled = $on; $r.Fx.Enabled = $on; $r.Light.Enabled = $on; $r.Bright.Visible = $on; if ($r.Pic) { $r.Pic.Visible = $on } })
    & $apply $row
    $script:rows += $row
    $fxBtn.Tag = $row
    $fxBtn.Add_Click({ param($s2, $e2) $r = $s2.Tag; Show-EffectsDialog $r.Combo.SelectedItem.Path $r.Combo.SelectedItem.Label })
    $combo.Add_SelectedIndexChanged({ Update-EffectButtons })
    $destBox.Input.Add_TextChanged({ Update-SaveState })
    
    $chk.Add_CheckedChanged({ Update-SaveState })
    Add-GridRow @($slotLabel, $pic, $chk, $nameBox, $destBox, $combo, $fxBtn, $lightCtl, $brightBox) 42
}

# Filler row: when the window is taller than the rows, the spare height goes here instead of stretching the last slot row.
[void]$grid.RowStyles.Add((New-Object Windows.Forms.RowStyle('Percent', 100)))
$grid.RowCount = $script:rowIndex + 1

# hover help on the column headers
$tips = @{
    'Slot'               = 'Which container in the portal room the portal sits in. A = top level, B = middle, C = bottom; 1-4 run around the room.'
    'Enabled'            = 'Tick to put a portal in this slot. Unticked slots stay empty.'
    'Name'               = 'Optional label. Only shown in the mod''s log; it does not need to match anything in the game.'
    'Destination pad ID' = 'The arrival pad the portal sends players to (its MyTeleporterID). Must match exactly. Pick a world from the list, or choose Custom Destination at the bottom to type any pad ID (not the two DLC areas).'
    'Base Portal'        = 'The base look of the portal (its particle effect). Purely visual.'
    'Effects'            = 'Switch parts of this look on or off (for example the accretion disk of SnowFlurry). Applies to every portal that uses the look.'
    'Light'              = 'The colour of the pad''s own light: a rainbow preset, or Custom for any colour. It tints the surroundings and how the portal looks, and works with every look. Default leaves it alone.'
    'Bright'             = 'Brightness of that light in steps of 0.1: 1.0 = the game''s normal brightness, 2.0 = twice as bright, 0.5 = half.'
}
$toolTip = New-Object Windows.Forms.ToolTip
$toolTip.InitialDelay = 300; $toolTip.AutoPopDelay = 12000
foreach ($ctl in $grid.Controls) { if ($tips.ContainsKey($ctl.Text)) { $toolTip.SetToolTip($ctl, $tips[$ctl.Text]) } }

# footer controls
$humTitle = New-Object Windows.Forms.Label
$humTitle.Text = 'Hub portal volume'; $humTitle.ForeColor = $colFg; $humTitle.AutoSize = $true
$humTitle.Location = New-Object Drawing.Point(20, 17)

# volume mode drop-down (dark, owner-drawn like the design drop-down)
$modeItems = @(
    [pscustomobject]@{ Label = 'Dynamic (scales with portals added)'; Value = 'dynamic' },
    [pscustomobject]@{ Label = 'Manual (one fixed volume)'; Value = 'manual' },
    [pscustomobject]@{ Label = 'Default (leave the game as is)'; Value = 'default' }
)
$modeCombo = New-Object Windows.Forms.ComboBox
$modeCombo.DropDownStyle = 'DropDownList'; $modeCombo.FlatStyle = 'Flat'; $modeCombo.Font = $fontBase
$modeCombo.BackColor = $colInput; $modeCombo.ForeColor = $colFg
$modeCombo.DrawMode = 'OwnerDrawFixed'; $modeCombo.ItemHeight = 24; $modeCombo.DisplayMember = 'Label'
$modeCombo.Location = New-Object Drawing.Point(150, 12); $modeCombo.Width = 280
foreach ($mi in $modeItems) { [void]$modeCombo.Items.Add($mi) }
$modeCombo.SelectedItem = ($modeItems | Where-Object { $_.Value -eq $cfg.HumMode } | Select-Object -First 1)
$modeCombo.Add_DrawItem({
    param($s, $e)
    if ($e.Index -lt 0) { return }
    $selected = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
    $back = if ($selected) { $colAccent } else { $colInput }
    $b1 = New-Object Drawing.SolidBrush($back); $b2 = New-Object Drawing.SolidBrush($colFg)
    $e.Graphics.FillRectangle($b1, $e.Bounds)
    $e.Graphics.DrawString($s.Items[$e.Index].Label, $e.Font, $b2, ($e.Bounds.X + 5), ($e.Bounds.Y + 3))
    $b1.Dispose(); $b2.Dispose()
})

$humLabel = New-Object Windows.Forms.Label
$humLabel.ForeColor = $colFg; $humLabel.AutoSize = $true; $humLabel.Location = New-Object Drawing.Point(450, 17)
$hum = New-Object Windows.Forms.NumericUpDown
$hum.Minimum = 0; $hum.Maximum = 100
$hum.BackColor = $colInput; $hum.ForeColor = $colFg; $hum.Location = New-Object Drawing.Point(590, 13); $hum.Width = 64
$hum.BorderStyle = 'FixedSingle'
$humHint = New-Object Windows.Forms.Label
$humHint.ForeColor = $colMuted; $humHint.AutoSize = $true; $humHint.Location = New-Object Drawing.Point(668, 10)
$humHint.MaximumSize = New-Object Drawing.Size(350, 0)      # wrap onto a second line instead of running off the window

# The number box shows the floor in Dynamic mode and the fixed volume in Manual mode; each mode remembers its own value.
$script:humVals = @{ dynamic = [int]$cfg.HumFloor; manual = [int]$cfg.HumManual }
$script:humPrior = $null
function Set-HumControls {
    $mode = $modeCombo.SelectedItem.Value
    if ($script:humPrior -and $script:humVals.ContainsKey($script:humPrior)) { $script:humVals[$script:humPrior] = [int]$hum.Value }
    $script:humPrior = $mode
    $isNumeric = $script:humVals.ContainsKey($mode)
    $humLabel.Visible = $isNumeric; $hum.Visible = $isNumeric
    switch ($mode) {
        'dynamic' { $humLabel.Text = 'Lowest volume (%)'; $humHint.Text = 'Each added portal lowers the hub hum evenly, down to this level.' }
        'manual'  { $humLabel.Text = 'Volume (%)'; $humHint.Text = 'Every hub portal uses this volume.' }
        default   { $humHint.Text = 'Portal volume is left exactly as the game sets it.' }
    }
    if ($isNumeric) { $hum.Value = [math]::Min(100, [math]::Max(0, [decimal]$script:humVals[$mode])) }
    $humHint.Location = New-Object Drawing.Point($(if ($isNumeric) { 668 } else { 450 }), $(if ($isNumeric) { 10 } else { 17 }))
}
$modeCombo.Add_SelectedIndexChanged({ Set-HumControls })
Set-HumControls

function New-Button([string]$text, [bool]$primary) {
    $b = New-Object Windows.Forms.Button
    $b.Text = $text; $b.FlatStyle = 'Flat'; $b.Font = $fontBold; $b.Height = 34; $b.Width = 150
    $b.ForeColor = $colFg; $b.FlatAppearance.BorderSize = 1
    if ($primary) { $b.BackColor = $colAccent; $b.FlatAppearance.BorderColor = $colAccent }
    else { $b.BackColor = $colInput; $b.FlatAppearance.BorderColor = $colBorder }
    return $b
}
$btnSave = New-Button 'Save to config' $true
$btnSave.Location = New-Object Drawing.Point(20, 48)
$btnReload = New-Button 'Reload from file' $false
$btnReload.Location = New-Object Drawing.Point(180, 48)
$btnFolder = New-Button 'Open config folder' $false
$btnFolder.Location = New-Object Drawing.Point(340, 48)
$btnWorlds = New-Button 'Custom worlds' $false
$btnWorlds.Location = New-Object Drawing.Point(500, 48)
$btnWorlds.Add_Click({ Show-WorldsDialog })
Update-WorldsButton
$status = New-Object Windows.Forms.Label
$status.AutoSize = $false; $status.Size = New-Object Drawing.Size(520, 34); $status.Location = New-Object Drawing.Point(670, 48)
$status.TextAlign = 'MiddleLeft'; $status.ForeColor = $colMuted
$status.Text = 'Config: ' + $ConfigPath
$footer.Controls.AddRange(@($humTitle, $modeCombo, $humLabel, $hum, $humHint, $btnSave, $btnReload, $btnFolder, $btnWorlds, $status))
$footer.Add_Resize({ $status.Width = [math]::Max(200, $footer.ClientSize.Width - 690) })
# Saving is blocked while any ticked portal has no valid destination pad ID: the Save button greys out, the empty field turns
# red and the status line names the slot(s). Unticking the portal (or entering an ID) clears it.
$script:statusWarn = $false
function Update-SaveState {
    if (-not $btnSave -or -not $script:rows) { return }
    $bad = @(); $badDlc = @()
    foreach ($r in $script:rows) {
        $needs = $r.Check.Checked -and ($r.Dest.Input.Text.Trim() -notmatch '^[A-Za-z0-9_\-]+$')
        $dlc = $r.Check.Checked -and ($DlcPads -contains $r.Dest.Input.Text.Trim())     # DLC areas are not allowed
        $shade = if ($needs -or $dlc) { $colBad } else { $colInput }
        $r.Dest.BackColor = $shade; $r.Dest.Input.BackColor = $shade
        if ($needs) { $bad += $r.Slot }
        if ($dlc) { $badDlc += $r.Slot }
    }
    $btnSave.Enabled = ($bad.Count -eq 0 -and $badDlc.Count -eq 0)
    if ($bad.Count -gt 0) {
        $btnSave.BackColor = $colInput; $btnSave.ForeColor = $colMuted
        $script:statusWarn = $true
        $status.ForeColor = C '#ff9b9b'
        $status.Text = "Can't save yet: " + ($bad -join ', ') + $(if ($bad.Count -eq 1) { ' is' } else { ' are' }) + " enabled but has no valid destination pad ID (letters, numbers, _ and - only). Enter one, or untick the portal."
    } elseif ($badDlc.Count -gt 0) {
        $btnSave.BackColor = $colInput; $btnSave.ForeColor = $colMuted
        $script:statusWarn = $true
        $status.ForeColor = C '#ff9b9b'
        $status.Text = "Can't save yet: " + ($badDlc -join ', ') + $(if ($badDlc.Count -eq 1) { ' uses' } else { ' use' }) + " a DLC area (Temple of Stone or Torii) as its destination, which isn't allowed. Pick another destination."
    } else {
        $btnSave.BackColor = $colAccent; $btnSave.ForeColor = $colFg
        if ($script:statusWarn) { $script:statusWarn = $false; $status.ForeColor = $colMuted; $status.Text = 'Config: ' + $ConfigPath }
    }
}
Update-SaveState

$btnSave.Add_Click({
    $list = @()
    foreach ($r in $script:rows) {
        if (-not $r.Check.Checked) { continue }
        $dest = $r.Dest.Input.Text.Trim()
        if ($dest -notmatch '^[A-Za-z0-9_\-]+$') {
            $status.ForeColor = C '#ff7b7b'
            $status.Text = "Slot $($r.Slot): enter the destination pad ID (letters, numbers, _ and - only)."
            return
        }
        $nm = $r.Name.Text.Trim(); if (-not $nm) { $nm = $(if ($DestWorldNames.ContainsKey($dest)) { $DestWorldNames[$dest] } else { $dest }) }
        $list += @{ slot = $r.Slot; name = $nm; destination = $dest; design = $r.Combo.SelectedItem.Path; lightHex = (Get-LightHex $r.Light); lightBright = ($r.Bright.Value.ToString('0.0', [Globalization.CultureInfo]::InvariantCulture)) }
    }
    try {
        $mode = $modeCombo.SelectedItem.Value
        if ($script:humVals.ContainsKey($mode)) { $script:humVals[$mode] = [int]$hum.Value }
        Write-HubConfig $ConfigPath $cfg.Header $mode $script:humVals.dynamic $script:humVals.manual $list (Get-BlocksForSave)
        $status.ForeColor = C '#7be09a'
        $wn = @($script:worlds).Count
        $status.Text = "Saved $($list.Count) portal(s)" + $(if ($wn -gt 0) { " and $wn custom world(s)" } else { '' }) + ". In game press Ctrl+O, then click Restart All Mods."
    } catch {
        $status.ForeColor = C '#ff7b7b'
        $status.Text = 'Could not save: ' + $_.Exception.Message
    }
})
$btnReload.Add_Click({
    $form.Close()
    Start-Process powershell -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-ConfigPath', "`"$ConfigPath`"")
})
$btnFolder.Add_Click({ Start-Process explorer.exe -ArgumentList ('/select,"' + $ConfigPath + '"') })

$form.Controls.Add($grid)
$form.Controls.Add($footer)
$form.Controls.Add($header)
$grid.BringToFront()

if ($Screenshot) {
    $form.Show(); [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 400; [Windows.Forms.Application]::DoEvents()
    $bmp = New-Object Drawing.Bitmap($form.Width, $form.Height)
    $form.DrawToBitmap($bmp, (New-Object Drawing.Rectangle(0, 0, $form.Width, $form.Height)))
    $bmp.Save($Screenshot, [Drawing.Imaging.ImageFormat]::Png)
    # also capture the destination pop-up of the first open row
    $first = $script:rows[0].Dest
    $first.Drop.Show($first.Button, (New-Object Drawing.Point(0, $first.Button.Height)))
    [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 300; [Windows.Forms.Application]::DoEvents()
    $lb = New-Object Drawing.Bitmap($first.List.Width, $first.List.Height)
    $first.List.DrawToBitmap($lb, (New-Object Drawing.Rectangle(0, 0, $first.List.Width, $first.List.Height)))
    $lb.Save(($Screenshot -replace '\.png$', '_dropdown.png'), [Drawing.Imaging.ImageFormat]::Png)
    # and the Effects dialog for the SnowFlurry look
    $first.Drop.Close()
    $script:hideMap['/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry'] = @('Blackhole')
    $script:ShotMode = $true
    $dlgForm = Show-EffectsDialog '/Game/Particles/Niagara_Portal_SnowFlurry.Niagara_Portal_SnowFlurry' 'SnowFlurry'
    $dlgForm.Show($form); [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 300; [Windows.Forms.Application]::DoEvents()
    $db = New-Object Drawing.Bitmap($dlgForm.Width, $dlgForm.Height)
    $dlgForm.DrawToBitmap($db, (New-Object Drawing.Rectangle(0, 0, $dlgForm.Width, $dlgForm.Height)))
    $db.Save(($Screenshot -replace '\.png$', '_effects.png'), [Drawing.Imaging.ImageFormat]::Png)
    $dlgForm.Close()
    # and the Custom worlds dialog (first world selected, then a second one with problems)
    $wd = Show-WorldsDialog
    if ($wd) {
        $wd.Show($form); [Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 300; [Windows.Forms.Application]::DoEvents()
        $wb = New-Object Drawing.Bitmap($wd.Width, $wd.Height)
        $wd.DrawToBitmap($wb, (New-Object Drawing.Rectangle(0, 0, $wd.Width, $wd.Height)))
        $wb.Save(($Screenshot -replace '\.png$', '_worlds.png'), [Drawing.Imaging.ImageFormat]::Png)
        $wd.Close()
    }
    $wd = Show-WorldsDialog
    if ($wd) {
        $wd.Show($form); [Windows.Forms.Application]::DoEvents()
        $addBtn = $wd.Controls | Where-Object { $_.Text -eq 'Add world' }
        $addBtn.PerformClick(); [Windows.Forms.Application]::DoEvents()
        $rp = $wd.Controls | Where-Object { $_ -is [Windows.Forms.Panel] } | Select-Object -First 1
        $tbs = @($rp.Controls | Where-Object { $_ -is [Windows.Forms.TextBox] })
        $tbs[1].Text = '/Game/Mods/Hello/BP_HelloLoader'; [Windows.Forms.Application]::DoEvents()
        $tbs[3].Text = '/Game/Mods/Hello/Maps/Hello_L0'; [Windows.Forms.Application]::DoEvents()
        $tbs[4].Text = '1100000'; [Windows.Forms.Application]::DoEvents()    # same x as the first world: too close
        Start-Sleep -Milliseconds 300; [Windows.Forms.Application]::DoEvents()
        Write-Host ('autofill class: ' + $tbs[2].Text)
        $wb = New-Object Drawing.Bitmap($wd.Width, $wd.Height)
        $wd.DrawToBitmap($wb, (New-Object Drawing.Rectangle(0, 0, $wd.Width, $wd.Height)))
        $wb.Save(($Screenshot -replace '\.png$', '_worlds2.png'), [Drawing.Imaging.ImageFormat]::Png)
        $wd.Close()
    }
    $form.Close(); return
}
[void]$form.ShowDialog()




























