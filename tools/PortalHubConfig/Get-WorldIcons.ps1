# Downloads the portal-world icons from the Abiotic Factor wiki into .\icons (next to this script).
# The repository already includes these icons; run this only to refresh them or if the icons folder was deleted.
# Source: the wiki's Locations page, Portal Worlds section.
# To turn the icons off again: delete the icons folder, or set $ShowWorldIcons = $false at the top of PortalHubConfig.ps1.
param([string]$PageUrl = 'https://abioticfactor.wiki.gg/wiki/Locations')

$base = 'https://abioticfactor.wiki.gg'
$iconDir = Join-Path $PSScriptRoot 'icons'
New-Item -ItemType Directory -Force $iconDir | Out-Null

function Get-Slug([string]$name) { (($name.ToLowerInvariant()) -replace '[^a-z0-9]+', '-').Trim('-') }

Write-Host "Reading $PageUrl ..."
$html = (Invoke-WebRequest -Uri $PageUrl -UseBasicParsing -TimeoutSec 60 -UserAgent 'Mozilla/5.0 (PortalHubConfig fan tool)').Content
$start = $html.IndexOf('id="Portal_Worlds"')
if ($start -lt 0) { Write-Host 'Could not find the Portal Worlds section on the page.'; exit 1 }
$section = $html.Substring($start)
$next = [regex]::Match($section.Substring(20), '<h2')
if ($next.Success) { $section = $section.Substring(0, $next.Index + 20) }

$count = 0
foreach ($m in [regex]::Matches($section, '<a href="/wiki/[^"]*" title="([^"]+)"><img src="(/images/[^"?]+)')) {
    $title = [Net.WebUtility]::HtmlDecode($m.Groups[1].Value)
    $path = Join-Path $iconDir ((Get-Slug $title) + '.png')
    try {
        Invoke-WebRequest -Uri ($base + $m.Groups[2].Value) -OutFile $path -UseBasicParsing -TimeoutSec 60 -UserAgent 'Mozilla/5.0 (PortalHubConfig fan tool)'
        $count++
        Write-Host ("  {0,-30} -> {1}" -f $title, (Split-Path $path -Leaf))
    } catch { Write-Host "  could not download $title : $($_.Exception.Message)" }
}
Write-Host "$count icon(s) saved to $iconDir"

