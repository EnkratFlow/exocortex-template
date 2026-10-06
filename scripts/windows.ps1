# Run the shared installer/updater on native Windows using Git for Windows.
param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet('install', 'update')][string]$Action,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments
)
$ErrorActionPreference = 'Stop'
$template = (Split-Path $PSScriptRoot -Parent).Replace('\', '/')

# Bash: an explicit EXOCORTEX_BASH wins. Otherwise look beside git.exe (full
# Git for Windows), then common Git for Windows and PortableGit locations,
# then PATH. MinGit ships no Bash at all, and System32/WindowsApps bash.exe is
# WSL, which cannot run these scripts against Windows paths.
function Test-GitBash([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    return $Path -notmatch '(?i)[\\/](System32|SysWOW64|WindowsApps)[\\/]'
}
$bashCandidates = @()
if ($env:EXOCORTEX_BASH) {
    if (-not (Test-GitBash $env:EXOCORTEX_BASH)) { throw "EXOCORTEX_BASH does not name a Git Bash executable: $env:EXOCORTEX_BASH" }
    $bash = $env:EXOCORTEX_BASH
} else {
    $git = Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($git) {
        $gitParent = Split-Path $git.Source -Parent
        $bashCandidates += (Join-Path (Split-Path $gitParent -Parent) 'bin\bash.exe')
        $bashCandidates += (Join-Path (Split-Path (Split-Path $gitParent -Parent) -Parent) 'bin\bash.exe')
    }
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:ProgramW6432)) {
        if ($root) { $bashCandidates += (Join-Path $root 'Git\bin\bash.exe') }
    }
    if ($env:LOCALAPPDATA) {
        $bashCandidates += (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe')
        $bashCandidates += (Join-Path $env:LOCALAPPDATA 'PortableGit\bin\bash.exe')
    }
    if ($env:USERPROFILE) {
        $bashCandidates += (Join-Path $env:USERPROFILE 'PortableGit\bin\bash.exe')
        $bashCandidates += (Join-Path $env:USERPROFILE 'scoop\apps\git\current\bin\bash.exe')
    }
    $bashCandidates += @(Get-Command bash.exe -CommandType Application -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
    $bash = $bashCandidates | Where-Object { Test-GitBash $_ } | Select-Object -First 1
}
if (-not $bash) {
    throw 'Git Bash was not found. MinGit does not include Bash. Install Git for Windows or PortableGit from https://git-scm.com/download/win, or set EXOCORTEX_BASH to its bin\bash.exe.'
}

# Python: Git Bash's python3 is often the Microsoft Store alias, which prints
# "Python was not found" instead of running. Resolve a real Python 3.9+ here
# (EXOCORTEX_PYTHON, then python.exe, python3.exe, py -3) and pass its
# absolute path to the scripts.
function Resolve-Python([string]$Executable, [string[]]$Prefix = @()) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    if ($Executable -match '(?i)[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }
    $env:PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
    try {
        $found = & $Executable @Prefix -I -c 'import sys; print(sys.executable) if sys.version_info >= (3,9) else sys.exit(1)' 2>$null
    } catch { return $null }
    if ($LASTEXITCODE -ne 0 -or -not $found) { return $null }
    $found = ($found | Select-Object -Last 1).Trim()
    if ([IO.Path]::IsPathRooted($found) -and (Test-Path -LiteralPath $found -PathType Leaf)) { return $found }
    return $null
}
$python = $null
if ($env:EXOCORTEX_PYTHON) {
    $python = Resolve-Python $env:EXOCORTEX_PYTHON
    if (-not $python) { throw "EXOCORTEX_PYTHON is not a working Python 3.9+: $env:EXOCORTEX_PYTHON" }
} else {
    foreach ($name in @('python.exe', 'python3.exe', 'py.exe')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command) { continue }
        $prefix = @(); if ($name -eq 'py.exe') { $prefix = @('-3') }
        $python = Resolve-Python $command.Source $prefix
        if ($python) { break }
    }
}
if (-not $python) {
    throw 'Python 3.9+ was not found. The Microsoft Store "python" alias does not count. Install Python from https://www.python.org/downloads/windows/ or set EXOCORTEX_PYTHON to python.exe.'
}

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
$oldPython = $env:EXOCORTEX_PYTHON
$env:EXOCORTEX_PYTHON = Convert-ToBashPath $python
try {
    if ($Action -eq 'update') {
        & $bash --noprofile --norc "$template/scripts/safe-update.sh" --template $templateBash --candidate-digest $digest @forward
        $result = $LASTEXITCODE
    } else {
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
    }
} finally {
    $env:EXOCORTEX_PYTHON = $oldPython
}
exit $result
