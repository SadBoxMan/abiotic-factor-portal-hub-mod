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
    'Niagara_Portal_NightRDoor_2', 'Niagara_Portal_Redverse', 'Niagara_Portal_Rift', 'Niagara_Portal_Rift_BlueFade',
    'Niagara_Portal_Salem', 'Niagara_Portal_Shadowgate2', 'Niagara_Portal_SnowFlurry', 'Niagara_Portal_SunDisk',
    'Niagara_Portal_Tiny', 'Niagara_Portal_Torii'
)
$TestedDesigns = @('Niagara_Portal_Torii')   # looks confirmed working in game so far

function New-DesignItem([string]$name) {
    if ($name -eq 'Niagara_Portal') { $label = 'Default (game portal)' }
    else { $label = ($name -replace '^Niagara_Portal_', '') -replace '_', ' ' }
    if ($TestedDesigns -contains $name) { $label += '  (tested)' }
    [pscustomobject]@{ Label = $label; Path = "/Game/Particles/$name.$name" }
}
# Known arrival pads you can pick in the Destination drop-down (currently the three Anteverse worlds).
# You can also type any other pad ID by hand, e.g. one from your own world.
$KnownDestinations = @(
    # The three arrival pads: these drop you inside each Anteverse world.
    @{ Id = 'anteverse_a_start';    World = 'Far Garden';             Note = 'Anteverse A, arrival pad' },
    @{ Id = 'anteverse_b_start';    World = 'The Mycofields';         Note = 'Anteverse B, arrival pad' },
    @{ Id = 'anteverse_c_start';    World = "Village Den da'ko Yeer"; Note = 'Anteverse C, arrival pad' },
    # Other Anteverse pads found in the game. These are exit or entrance pads, so they send you to a different spot
    # (the Facility side, or a special exit inside the world). Handy for special cases; most mods want the arrival pads above.
    @{ Id = 'anteverse_a_entrance'; World = 'Far Garden';             Note = 'Anteverse A, entrance pad in the Facility' },
    @{ Id = 'anteverse_a_return';   World = 'Far Garden';             Note = 'Anteverse A, return pad (inactive by default)' },
    @{ Id = 'anteverse_early_exit'; World = 'Far Garden';             Note = 'Anteverse A, early exit (inactive by default)' },
    @{ Id = 'anteverse_b_entrance'; World = 'The Mycofields';         Note = 'Anteverse B, entrance pad in the Facility' },
    @{ Id = 'anteverse_c_entrance'; World = "Village Den da'ko Yeer"; Note = 'Anteverse C, entrance pad in the Facility' },
    @{ Id = 'anteverse_c_earlyexit'; World = "Village Den da'ko Yeer"; Note = 'Anteverse C, early exit' },
    @{ Id = 'AnteC_Shadow_ExitA';   World = "Village Den da'ko Yeer"; Note = 'Anteverse C, shadow exit A' },
    @{ Id = 'AnteC_Shadow_ExitB';   World = "Village Den da'ko Yeer"; Note = 'Anteverse C, shadow exit B' },
    @{ Id = 'AnteC_Shadow_ExitC';   World = "Village Den da'ko Yeer"; Note = 'Anteverse C, shadow exit C' },
    @{ Id = 'AnteC_Shadow_ExitD';   World = "Village Den da'ko Yeer"; Note = 'Anteverse C, shadow exit D' }
)
$DestWorldNames = @{}
foreach ($kd in $KnownDestinations) { $DestWorldNames[$kd.Id] = $kd.World }

$DesignItems = @($DesignNames | ForEach-Object { New-DesignItem $_ })
$DefaultPath = $DesignItems[0].Path

# ---------------------------------------------------------------- config.lua read / write
function Read-HubConfig([string]$path) {
    $result = @{ Header = $null; HumMode = 'dynamic'; HumFloor = 15; HumManual = 50; Portals = @{} }
    if (-not (Test-Path $path)) { return $result }
    $text = [IO.File]::ReadAllText($path)
    $idx = $text.IndexOf('return {')
    if ($idx -gt 0) { $result.Header = $text.Substring(0, $idx).TrimEnd() }
    $body = if ($idx -ge 0) { $text.Substring($idx) } else { $text }
    $body = [regex]::Replace($body, '(?m)^\s*--.*$', '')        # drop commented-out lines
    $m = [regex]::Match($body, 'humFloor\s*=\s*([0-9.]+)')
    if ($m.Success) { $result.HumFloor = [math]::Round([double]::Parse($m.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture) * 100) }
    $m = [regex]::Match($body, 'humManual\s*=\s*([0-9.]+)')
    if ($m.Success) { $result.HumManual = [math]::Round([double]::Parse($m.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture) * 100) }
    $m = [regex]::Match($body, 'humMode\s*=\s*"(\w+)"')
    if ($m.Success -and @('dynamic', 'manual', 'default') -contains $m.Groups[1].Value) { $result.HumMode = $m.Groups[1].Value }
    foreach ($entry in [regex]::Matches($body, '\{\s*slot\s*=[^{}]*\}')) {
        $fields = @{}
        foreach ($f in [regex]::Matches($entry.Value, '(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"')) {
            $fields[$f.Groups[1].Value] = ($f.Groups[2].Value -replace '\\(["\\])', '$1')
        }
        if ($fields.slot) { $result.Portals[$fields.slot] = $fields }
    }
    return $result
}

function ConvertTo-LuaString([string]$s) { '"' + ($s -replace '\\', '\\' -replace '"', '\"') + '"' }

function ConvertTo-Fraction([int]$percent) { ([double]$percent / 100).ToString('0.##', [Globalization.CultureInfo]::InvariantCulture) }

function Write-HubConfig([string]$path, $header, [string]$humMode, [int]$humFloorPct, [int]$humManualPct, $portalList) {
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
    [void]$sb.AppendLine('    portals = {')
    foreach ($p in $portalList) {
        $line = '        { slot = ' + (ConvertTo-LuaString $p.slot) + ', name = ' + (ConvertTo-LuaString $p.name) + ', destination = ' + (ConvertTo-LuaString $p.destination)
        if ($p.design -and $p.design -ne $DefaultPath) { $line += ', design = ' + (ConvertTo-LuaString $p.design) }
        [void]$sb.AppendLine($line + ' },')
    }
    [void]$sb.AppendLine('    },')
    [void]$sb.AppendLine('}')
    if (Test-Path $path) { Copy-Item $path ($path + '.bak') -Force }
    [IO.File]::WriteAllText($path, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
}

$cfg = Read-HubConfig $ConfigPath

if ($RoundTrip) {
    $list = @($cfg.Portals.Keys | Sort-Object | ForEach-Object { $p = $cfg.Portals[$_]; @{ slot = $p.slot; name = $p.name; destination = $p.destination; design = $p.design } })
    Write-HubConfig $RoundTrip $cfg.Header $cfg.HumMode $cfg.HumFloor $cfg.HumManual $list
    return
}

# ---------------------------------------------------------------- theme
function C([string]$hex) { [Drawing.ColorTranslator]::FromHtml($hex) }
$colBg = C '#17171c'; $colPanel = C '#202027'; $colInput = C '#2b2b34'; $colBorder = C '#3a3a46'
$colFg = C '#e8e8ee'; $colMuted = C '#8d8d9b'; $colAccent = C '#5b7cfa'; $colLocked = C '#7a7a88'

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
function New-DestControl([string]$text) {
    # A text box you can type any pad ID into, plus a button that opens a dark menu of known arrival pads.
    # (Built by hand because Windows draws a disabled editable ComboBox light grey, which breaks dark mode.)
    $panel = New-Object Windows.Forms.Panel
    $panel.Dock = 'Fill'; $panel.Margin = New-Object Windows.Forms.Padding(2, 5, 8, 5); $panel.BackColor = $colInput
    $tb = New-Object Windows.Forms.TextBox
    $tb.Text = $text; $tb.Font = $fontBase; $tb.BackColor = $colInput; $tb.ForeColor = $colFg
    $tb.BorderStyle = 'FixedSingle'; $tb.Dock = 'Fill'
    $btn = New-Object Windows.Forms.Button
    $btn.Text = [string][char]0x25BE; $btn.FlatStyle = 'Flat'; $btn.Dock = 'Right'; $btn.Width = 30
    $btn.BackColor = $colInput; $btn.ForeColor = $colFg; $btn.FlatAppearance.BorderSize = 1; $btn.FlatAppearance.BorderColor = $colBorder
    $btn.TabStop = $false
    $panel.Controls.Add($tb)      # added first so the button docks to the right edge and the text box fills the rest
    $panel.Controls.Add($btn)
    # The pop-up is a scrolling dark list (about 8 rows visible), so it keeps working when many worlds are listed.
    $rowH = 26; $visibleRows = 8
    $list = New-Object Windows.Forms.ListBox
    $list.DrawMode = 'OwnerDrawFixed'; $list.ItemHeight = $rowH; $list.BorderStyle = 'None'; $list.IntegralHeight = $false
    $list.BackColor = $colInput; $list.ForeColor = $colFg; $list.Font = $fontBase
    foreach ($kd in $KnownDestinations) { [void]$list.Items.Add($kd.Id) }
    $list.Size = New-Object Drawing.Size(640, ([math]::Min([math]::Max($list.Items.Count, 1), $visibleRows) * $rowH + 2))
    $list.Add_HandleCreated({ [void][DwmDark]::SetWindowTheme($list.Handle, 'DarkMode_Explorer', $null) }.GetNewClosure())
    $list.Add_DrawItem({
        param($s, $e)
        if ($e.Index -lt 0) { return }
        $id = [string]$s.Items[$e.Index]
        $hot = (($e.State -band [Windows.Forms.DrawItemState]::Selected) -ne 0)
        $b1 = New-Object Drawing.SolidBrush($(if ($hot) { $colAccent } else { $colInput }))
        $b2 = New-Object Drawing.SolidBrush($colFg)
        $b3 = New-Object Drawing.SolidBrush($(if ($hot) { $colFg } else { $colMuted }))
        $e.Graphics.FillRectangle($b1, $e.Bounds)
        $e.Graphics.DrawString($id, $e.Font, $b2, ($e.Bounds.X + 6), ($e.Bounds.Y + 4))
        $info = $KnownDestinations | Where-Object { $_.Id -eq $id } | Select-Object -First 1
        if ($info) { $e.Graphics.DrawString(($info.World + '  (' + $info.Note + ')'), $e.Font, $b3, ($e.Bounds.X + 200), ($e.Bounds.Y + 4)) }
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
        if ($i -lt 0) { return }
        $id = [string]$list.Items[$i]
        $tb.Text = $id
        $nb = $panel.Tag      # picking a known world fills the Name box if it is still empty
        if ($nb -and -not $nb.Text.Trim() -and $DestWorldNames.ContainsKey($id)) { $nb.Text = $DestWorldNames[$id] }
        $drop.Close()
    }.GetNewClosure()
    $list.Add_MouseMove({ param($s, $e) $i = $s.IndexFromPoint($e.Location); if ($i -ge 0 -and $s.SelectedIndex -ne $i) { $s.SelectedIndex = $i } })
    $list.Add_MouseUp($choose)
    $list.Add_KeyDown({ param($s, $e) if ($e.KeyCode -eq 'Return') { & $choose } }.GetNewClosure())
    $btn.Add_Click({
        $cur = $list.Items.IndexOf($tb.Text.Trim())
        $list.SelectedIndex = $cur
        $drop.Show($btn, (New-Object Drawing.Point(0, $btn.Height)))
        $list.Focus() | Out-Null
    }.GetNewClosure())
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
$form.ClientSize = New-Object Drawing.Size(1040, 690)
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
$grid.ColumnCount = 5
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 64)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Absolute', 84)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 32)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 28)))
[void]$grid.ColumnStyles.Add((New-Object Windows.Forms.ColumnStyle('Percent', 40)))

$rowIndex = 0
function Add-GridRow($controls, [int]$height) {
    [void]$grid.RowStyles.Add((New-Object Windows.Forms.RowStyle('Absolute', $height)))
    for ($i = 0; $i -lt $controls.Count; $i++) { if ($controls[$i]) { $grid.Controls.Add($controls[$i], $i, $script:rowIndex) } }
    $script:rowIndex++
}
$grid.RowCount = 0
$grid.Add_HandleCreated({ [void][DwmDark]::SetWindowTheme($grid.Handle, 'DarkMode_Explorer', $null) })    # dark scrollbar
Add-GridRow @((New-Label 'Slot' $fontBold $colMuted), (New-Label 'Enabled' $fontBold $colMuted), (New-Label 'Name' $fontBold $colMuted), (New-Label 'Destination pad ID' $fontBold $colMuted), (New-Label 'Portal look' $fontBold $colMuted)) 30

$script:rows = @()
foreach ($s in $Slots) {
    $slotLabel = New-Label $s.Id $fontBold $colFg
    if ($s.Locked) {
        $enabled = New-Label 'Locked' $fontBase $colLocked
        $name = New-Label ('Game portal: ' + $s.Locked) $fontBase $colLocked
        $dest = New-Label $s.Dest $fontBase $colLocked
        $look = New-Label 'Fixed by the game' $fontBase $colLocked
        Add-GridRow @($slotLabel, $enabled, $name, $dest, $look) 38
        continue
    }
    $existing = $cfg.Portals[$s.Id]
    $chk = New-Object Windows.Forms.CheckBox
    $chk.Text = ''; $chk.Dock = 'Fill'; $chk.CheckAlign = 'MiddleCenter'; $chk.BackColor = [Drawing.Color]::Transparent
    $chk.Checked = [bool]$existing
    $nameBox = New-TextBox ($(if ($existing) { $existing.name } else { '' }))
    $destBox = New-DestControl ($(if ($existing) { $existing.destination } else { '' }))
    $destBox.Tag = $nameBox
    $combo = New-DesignCombo ($(if ($existing -and $existing.design) { $existing.design } else { $DefaultPath }))
    $row = [pscustomobject]@{ Slot = $s.Id; Check = $chk; Name = $nameBox; Dest = $destBox; Combo = $combo }
    $apply = {
        param($r)
        $on = $r.Check.Checked
        $r.Name.Enabled = $on; $r.Dest.Enabled = $on; $r.Combo.Enabled = $on
    }
    $chk.Tag = $row
    $chk.Add_CheckedChanged({ param($s2, $e2) $r = $s2.Tag; $on = $r.Check.Checked; $r.Name.Enabled = $on; $r.Dest.Enabled = $on; $r.Combo.Enabled = $on })
    & $apply $row
    $script:rows += $row
    Add-GridRow @($slotLabel, $chk, $nameBox, $destBox, $combo) 42
}

# Filler row: when the window is taller than the rows, the spare height goes here instead of stretching the last slot row.
[void]$grid.RowStyles.Add((New-Object Windows.Forms.RowStyle('Percent', 100)))
$grid.RowCount = $script:rowIndex + 1

# hover help on the column headers
$tips = @{
    'Slot'               = 'Which container in the portal room the portal sits in. A = top level, B = middle, C = bottom; 1-4 run around the room.'
    'Enabled'            = 'Tick to put a portal in this slot. Unticked slots stay empty.'
    'Name'               = 'Optional label. Only shown in the mod''s log; it does not need to match anything in the game.'
    'Destination pad ID' = 'The arrival pad the portal sends players to (its MyTeleporterID). Must match exactly. Pick a known world or type your own.'
    'Portal look'        = 'The particle effect of the portal. Purely visual.'
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
$status = New-Object Windows.Forms.Label
$status.AutoSize = $false; $status.Size = New-Object Drawing.Size(520, 34); $status.Location = New-Object Drawing.Point(510, 48)
$status.TextAlign = 'MiddleLeft'; $status.ForeColor = $colMuted
$status.Text = 'Config: ' + $ConfigPath
$footer.Controls.AddRange(@($humTitle, $modeCombo, $humLabel, $hum, $humHint, $btnSave, $btnReload, $btnFolder, $status))
$footer.Add_Resize({ $status.Width = [math]::Max(200, $footer.ClientSize.Width - 530) })

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
        $list += @{ slot = $r.Slot; name = $nm; destination = $dest; design = $r.Combo.SelectedItem.Path }
    }
    try {
        $mode = $modeCombo.SelectedItem.Value
        if ($script:humVals.ContainsKey($mode)) { $script:humVals[$mode] = [int]$hum.Value }
        Write-HubConfig $ConfigPath $cfg.Header $mode $script:humVals.dynamic $script:humVals.manual $list
        $status.ForeColor = C '#7be09a'
        $status.Text = "Saved $($list.Count) portal(s). In game press Ctrl+O, then click Restart All Mods."
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
    $form.Close(); return
}
[void]$form.ShowDialog()




