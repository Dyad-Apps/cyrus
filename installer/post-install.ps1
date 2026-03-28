# Cyrus Brain — Post-Install Script (run by Inno Setup after file extraction)
# Creates venv, installs deps, configures hooks, registers service, installs extension.

param(
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = "Continue"
$VenvDir = "$InstallDir\venv"

# ── 1. Python venv + dependencies ────────────────────────────────────────────

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    # Try common install locations
    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($c in $Candidates) {
        if (Test-Path $c) { $PythonCmd = $c; break }
    }
}
if (-not $PythonCmd) {
    Write-Error "Python not found. Please install Python 3.10+ and re-run the installer."
    exit 1
}

if (-not (Test-Path "$VenvDir\Scripts\activate.ps1")) {
    & $PythonCmd -m venv $VenvDir
}
& "$VenvDir\Scripts\pip.exe" install --upgrade pip -q
& "$VenvDir\Scripts\pip.exe" install -r "$InstallDir\requirements-brain.txt" -q

# ── 2. Configure Claude Code hooks ──────────────────────────────────────────

$ClaudeDir = "$env:USERPROFILE\.claude"
New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
$HookPython = "$VenvDir\Scripts\python.exe" -replace '\\', '/'
$HookScript = "$InstallDir\cyrus_hook.py" -replace '\\', '/'

$HookCmd = "$HookPython $HookScript"
$HookEntry = @(@{ hooks = @(@{ type = "command"; command = $HookCmd; timeout = 5 }) })

$SettingsFile = "$ClaudeDir\settings.json"

# Merge with existing settings instead of overwriting
$Settings = @{}
if (Test-Path $SettingsFile) {
    Copy-Item $SettingsFile "$SettingsFile.bak" -Force
    try {
        $Settings = Get-Content $SettingsFile -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        $Settings = @{}
    }
}
if (-not $Settings.ContainsKey("hooks")) {
    $Settings["hooks"] = @{}
}
foreach ($hookEvent in @("Stop", "PreToolUse", "PostToolUse", "Notification", "PreCompact")) {
    $Settings["hooks"][$hookEvent] = $HookEntry
}

$Settings | ConvertTo-Json -Depth 10 | Set-Content $SettingsFile -Encoding UTF8

# ── 3. Register startup task and start brain ────────────────────────────────

$ServicePython = "$VenvDir\Scripts\python.exe"
$ServiceScript = "$InstallDir\cyrus_brain_service.py"

& "$ServicePython" "$ServiceScript" install 2>&1 | Write-Host

# ── 4. Create fallback launch script ────────────────────────────────────────

$VsixFile = Get-ChildItem "$InstallDir\*.vsix" -ErrorAction SilentlyContinue | Select-Object -First 1
$VsixName = if ($VsixFile) { $VsixFile.Name } else { "cyrus-companion.vsix" }

$LaunchScript = @"
@echo off
cd /d "$InstallDir"

REM One-time VS Code extension install
where code >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    code --list-extensions 2>nul | findstr /i "cyrus-companion" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        if exist "$InstallDir\$VsixName" (
            echo Installing Cyrus Companion extension...
            code --install-extension "$InstallDir\$VsixName" --force
            echo Please restart VS Code to activate the extension.
        )
    )
)

echo Starting Cyrus Brain
"$VenvDir\Scripts\python.exe" cyrus_brain.py %*
pause
"@
Set-Content -Path "$InstallDir\start-brain.bat" -Value $LaunchScript

# ── 5. Install VS Code companion extension ──────────────────────────────────

$CodeCmd = Get-Command code -ErrorAction SilentlyContinue
if ($CodeCmd -and $VsixFile) {
    try {
        & code --install-extension $VsixFile.FullName --force 2>&1 | Out-Null
    } catch {
        # Will be installed on first brain launch via start-brain.bat
    }
}
