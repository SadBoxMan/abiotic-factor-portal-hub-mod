# Copy a test world project under a new name (headless; the editor must not have either project open).
#   powershell -ExecutionPolicy Bypass -File tools\dev\copy_world.ps1 -Source "World Projects\World A\World_A" -OldName World_A `
#       -Target "World Projects\World E\World_E" -NewName World_E -Chunk 95
# Copies Config, Scripts, Content\Mods and the .uproject (not Saved/Intermediate), points the config at the new map and folder,
# then runs rename_world.py in a headless editor and prints its report.
param(
    [Parameter(Mandatory)] [string] $Source,
    [Parameter(Mandatory)] [string] $OldName,
    [Parameter(Mandatory)] [string] $Target,
    [Parameter(Mandatory)] [string] $NewName,
    [Parameter(Mandatory)] [int] $Chunk,
    [string] $Editor = "C:\Users\$env:USERNAME\Games\UE5\UE_5.4\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
)
$ErrorActionPreference = "Stop"
if (Test-Path $Target) { throw "$Target already exists; remove it first (send it to the Recycle Bin)." }
$enc = New-Object Text.UTF8Encoding($false)
New-Item -ItemType Directory -Force "$Target\Content" | Out-Null
Copy-Item "$Source\Config" "$Target\Config" -Recurse
if (Test-Path "$Source\Scripts") { Copy-Item "$Source\Scripts" "$Target\Scripts" -Recurse }
Copy-Item "$Source\Content\Mods" "$Target\Content\Mods" -Recurse
[IO.File]::WriteAllText("$Target\AbioticFactor.uproject", [IO.File]::ReadAllText("$Source\AbioticFactor.uproject").Replace($OldName, $NewName), $enc)
foreach ($ini in "DefaultEngine.ini", "DefaultGame.ini") {
    $f = "$Target\Config\$ini"
    $t = [IO.File]::ReadAllText($f).Replace("/Game/Mods/$OldName/Maps/${OldName}_L0", "/Game/Mods/$NewName/Maps/${NewName}_L0").Replace("/Game/Mods/$OldName", "/Game/Mods/$NewName")
    [IO.File]::WriteAllText($f, $t, $enc)
}
$report = Join-Path $env:TEMP "rename_$NewName.txt"
$env:PH_OLD = $OldName; $env:PH_NEW = $NewName; $env:PH_CHUNK = "$Chunk"; $env:PH_OUT = $report
$proj = (Resolve-Path "$Target\AbioticFactor.uproject").Path
$script = Join-Path $PSScriptRoot "rename_world.py"
$p = Start-Process -FilePath $Editor -ArgumentList @("`"$proj`"", "-run=PythonScript", "-Script=`"$script`"", "-unattended", "-nosplash", "-nullrhi", "-nosound", "-NoSourceControl", "-stdout") -PassThru -NoNewWindow -RedirectStandardOutput "$report.log"
if (-not $p.WaitForExit(600000)) { Stop-Process -Id $p.Id -Force; throw "the editor did not finish within 10 minutes" }
Get-Content $report
