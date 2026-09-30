# Run the shared installer/updater on native Windows using Git for Windows.
param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('install', 'update')][string]$Action,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
)
$ErrorActionPreference = 'Stop'
$template = (Split-Path $PSScriptRoot -Parent).Replace('\', '/')
$git = (Get-Command git.exe -ErrorAction Stop).Source
$gitParent = Split-Path $git -Parent
$candidates = @(
    (Join-Path (Split-Path $gitParent -Parent) 'bin\bash.exe'),
    (Join-Path (Split-Path (Split-Path $gitParent -Parent) -Parent) 'bin\bash.exe')
)
$bash = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $bash) { throw 'Git for Windows Bash was not found beside git.exe. Install Git for Windows first.' }
$algorithm = [System.Security.Cryptography.SHA256]::Create()
try {
    $digest = [BitConverter]::ToString($algorithm.ComputeHash([System.IO.File]::ReadAllBytes("$template/SHA256SUMS"))).Replace('-', '').ToLowerInvariant()
} finally { $algorithm.Dispose() }
function Convert-ToBashPath([string]$value) {
    $value = $value.Replace('\', '/')
    if ($value -match '^([A-Za-z]):/') {
        return '/' + $Matches[1].ToLowerInvariant() + $value.Substring(2)
    }
    return $value
}
$templateBash = Convert-ToBashPath $template
$forward = @()
$pathValue = $false
foreach ($argument in $Arguments) {
    if ($pathValue) { $argument = Convert-ToBashPath $argument }
    $forward += $argument
    $pathValue = $argument -in @('--template', '--backup-dir', '--reconciliation-plan', '--capability')
}
if ($Action -eq 'update') {
    & $bash --noprofile --norc "$template/scripts/safe-update.sh" --template $templateBash --candidate-digest $digest @forward
    exit $LASTEXITCODE
}
$oldSource = $env:EXOCORTEX_LOCAL_SOURCE
$oldDigest = $env:EXOCORTEX_CANDIDATE_DIGEST
try {
    $env:EXOCORTEX_LOCAL_SOURCE = $template
    $env:EXOCORTEX_CANDIDATE_DIGEST = $digest
    & $bash --noprofile --norc "$template/install.sh" @forward
    $result = $LASTEXITCODE
} finally {
    $env:EXOCORTEX_LOCAL_SOURCE = $oldSource
    $env:EXOCORTEX_CANDIDATE_DIGEST = $oldDigest
}
exit $result
