# Native Windows command launcher. No Bash, GitHub CLI, downloads or disk cache.
# Invoke with & from PowerShell; the validated path is reused in that session.
$ErrorActionPreference = 'Stop'

function ConvertTo-NativeArgument([string]$Value) {
    # Windows CommandLineToArgvW / Python CRT quoting, including empty arguments.
    '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}

function New-PythonProcess([string]$Executable, [string[]]$Arguments, [bool]$Probe) {
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $info.Arguments = ($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.EnvironmentVariables['PYTHONUTF8'] = '1'
    $info.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $info.EnvironmentVariables['PYTHONDONTWRITEBYTECODE'] = '1'
    # Both legacy py and the newer Python install manager must stay offline.
    $info.EnvironmentVariables.Remove('PYLAUNCHER_ALLOW_INSTALL')
    $info.EnvironmentVariables['PYTHON_MANAGER_AUTOMATIC_INSTALL'] = 'false'
    # PowerShell pipelines do not reliably pass their output handles to .NET
    # child processes. Capture asynchronously and forward explicitly below.
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $info.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    return $process
}

function Test-Python([string]$Executable, [string[]]$Prefix = @()) {
    if (-not (Test-Path -LiteralPath $Executable -PathType Leaf)) { return $null }
    # App execution aliases can open the Store instead of running Python.
    if ($Executable -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return $null }
    $probe = New-PythonProcess $Executable ($Prefix + @('-I', '-X', 'utf8', '-c', 'import sys; print(sys.executable) if sys.version_info >= (3,9) else sys.exit(1)')) $true
    try {
        [void]$probe.Start()
        $output = $probe.StandardOutput.ReadToEndAsync()
        $errorOutput = $probe.StandardError.ReadToEndAsync()
        if (-not $probe.WaitForExit(3000)) {
            # PS5.1 lacks Process.Kill(entireProcessTree). This is timeout-only.
            & "$env:SystemRoot\System32\taskkill.exe" /PID $probe.Id /T /F *> $null
            return $null
        }
        $path = $output.Result.Trim()
        if ($probe.ExitCode -eq 0 -and [IO.Path]::IsPathRooted($path) -and (Test-Path -LiteralPath $path -PathType Leaf)) { return $path }
    } catch { return $null } finally { $probe.Dispose() }
    return $null
}

$python = $null
if ($env:EXOCORTEX_PYTHON) {
    # An explicit configured path is authoritative: do not silently choose another.
    $python = Test-Python $env:EXOCORTEX_PYTHON
} elseif ($env:EXOCORTEX_SESSION_PYTHON -and (Test-Path -LiteralPath $env:EXOCORTEX_SESSION_PYTHON -PathType Leaf)) {
    $python = $env:EXOCORTEX_SESSION_PYTHON
} else {
    foreach ($name in @('python.exe', 'python3.exe', 'py.exe')) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $command) { continue }
        $prefix = @()
        if ($name -eq 'py.exe') { $prefix = @('-3') }
        $python = Test-Python $command.Source $prefix
        if ($python) { break }
    }
}
if (-not $python) {
    [Console]::Error.WriteLine('EXOCORTEX_PYTHON_UNAVAILABLE: Python 3.9+ was not found in the configured path or PATH. Set EXOCORTEX_PYTHON to its executable. Stop here; do not scan disks or search for Bash/gh.')
    exit 2
}
$env:EXOCORTEX_SESSION_PYTHON = $python
$process = New-PythonProcess $python (@('-B', '-X', 'utf8', (Join-Path $PSScriptRoot 'command_runtime.py')) + @($args)) $false
try {
    [void]$process.Start()
    $output = $process.StandardOutput.ReadToEndAsync()
    $errorOutput = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $result = $process.ExitCode
    $previousEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        [Console]::Out.Write($output.Result)
        [Console]::Error.Write($errorOutput.Result)
    } finally { [Console]::OutputEncoding = $previousEncoding }
} catch {
    [Console]::Error.WriteLine('EXOCORTEX_PYTHON_UNAVAILABLE: The selected interpreter could not start. Clear EXOCORTEX_SESSION_PYTHON or correct EXOCORTEX_PYTHON; do not search unrelated tools.')
    $result = 2
} finally { $process.Dispose() }
exit $result
