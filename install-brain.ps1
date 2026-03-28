# Cyrus Brain — Install Script (Windows)
# Run: powershell -ExecutionPolicy Bypass -File install-brain.ps1
#
# Installs Cyrus Brain + Hook + VS Code Companion Extension + Windows Service.
# Brain runs on the machine with VS Code + Claude Code.

param(
    [string]$InstallDir = "$env:USERPROFILE\.cyrus\brain"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Cyrus Brain Installer ===" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Create install directory
Write-Host "`n[1/6] Creating install directory: $InstallDir"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 2. Copy brain files
Write-Host "[2/6] Copying brain files..."
Copy-Item "$ScriptDir\cyrus_brain.py" "$InstallDir\" -Force
Copy-Item "$ScriptDir\cyrus_hook.py" "$InstallDir\" -Force
Copy-Item "$ScriptDir\cyrus_brain_service.py" "$InstallDir\" -Force
Copy-Item "$ScriptDir\requirements-brain.txt" "$InstallDir\" -Force

# Copy pre-built companion extension (check flat and subdirectory)
$VsixFile = Get-ChildItem "$ScriptDir\*.vsix" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $VsixFile) {
    $VsixFile = Get-ChildItem "$ScriptDir\cyrus-companion\*.vsix" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($VsixFile) {
    Copy-Item $VsixFile.FullName "$InstallDir\" -Force
    Write-Host "       Companion extension: $($VsixFile.Name)"
} else {
    Write-Host "       WARNING: No .vsix found in package." -ForegroundColor Red
}

# 3. Create virtual environment and install dependencies
Write-Host "[3/6] Setting up Python virtual environment..."
$VenvDir = "$InstallDir\venv"
if (-not (Test-Path "$VenvDir\Scripts\activate.ps1")) {
    python -m venv $VenvDir
}
& "$VenvDir\Scripts\pip.exe" install --upgrade pip -q
& "$VenvDir\Scripts\pip.exe" install -r "$InstallDir\requirements-brain.txt" -q

# 4. Install VS Code companion extension
Write-Host "[4/6] Installing VS Code companion extension..."
$VsixInDest = Get-ChildItem "$InstallDir\*.vsix" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($VsixInDest) {
    $CodeCmd = Get-Command code -ErrorAction SilentlyContinue
    if ($CodeCmd) {
        try {
            & code --install-extension $VsixInDest.FullName --force 2>&1 | Out-Null
            Write-Host "       Extension installed. Restart VS Code to activate." -ForegroundColor Green
        } catch {
            Write-Host "       WARNING: 'code' command failed. Extension will be installed on first brain launch." -ForegroundColor Yellow
        }
    } else {
        Write-Host "       'code' CLI not in PATH. Extension will be installed on first brain launch." -ForegroundColor Yellow
    }
} else {
    Write-Host "       WARNING: No .vsix file found in package." -ForegroundColor Red
}

# 5. Configure Claude Code hooks
Write-Host "[5/6] Configuring Claude Code hooks..."
$ClaudeDir = "$env:USERPROFILE\.claude"
New-Item -ItemType Directory -Force -Path $ClaudeDir | Out-Null
$HookPython = "$VenvDir\Scripts\python.exe" -replace '\\', '/'
$HookScript = "$InstallDir\cyrus_hook.py" -replace '\\', '/'

$HooksConfig = @{
    hooks = @{
        Stop = @(@{
            hooks = @(@{
                type    = "command"
                command = "$HookPython $HookScript"
                timeout = 5
            })
        })
        PreToolUse = @(@{
            hooks = @(@{
                type    = "command"
                command = "$HookPython $HookScript"
                timeout = 5
            })
        })
        PostToolUse = @(@{
            hooks = @(@{
                type    = "command"
                command = "$HookPython $HookScript"
                timeout = 5
            })
        })
        Notification = @(@{
            hooks = @(@{
                type    = "command"
                command = "$HookPython $HookScript"
                timeout = 5
            })
        })
        PreCompact = @(@{
            hooks = @(@{
                type    = "command"
                command = "$HookPython $HookScript"
                timeout = 5
            })
        })
    }
}

$SettingsFile = "$ClaudeDir\settings.json"
if (Test-Path $SettingsFile) {
    $Backup = "$SettingsFile.bak"
    Copy-Item $SettingsFile $Backup -Force
    Write-Host "       Backed up existing settings to: $Backup"
}
$HooksConfig | ConvertTo-Json -Depth 10 | Set-Content $SettingsFile -Encoding UTF8

# 6. Register startup task and start brain
Write-Host "[6/6] Registering Cyrus Brain startup task..."
$ServicePython = "$VenvDir\Scripts\python.exe"
$ServiceScript = "$InstallDir\cyrus_brain_service.py"

try {
    & "$ServicePython" "$ServiceScript" install 2>&1 | Write-Host
    Write-Host "       Brain is running and will auto-start on login." -ForegroundColor Green
} catch {
    Write-Host "       WARNING: Could not register startup task. Use start-brain.bat instead." -ForegroundColor Yellow
}

# Create fallback launch script (with one-time extension install)
$VsixName = if ($VsixInDest) { $VsixInDest.Name } else { "cyrus-companion.vsix" }
$LaunchScript = @"
@echo off
cd /d "$InstallDir"

REM One-time VS Code extension install (skips if already installed)
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

Write-Host "`n=== Installation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Brain installed to: $InstallDir"
Write-Host ""
Write-Host "Cyrus Brain is running in the background (auto-starts on login)."
Write-Host ""
Write-Host "  Stop/start:      python $ServiceScript stop|start" -ForegroundColor Yellow
Write-Host "  Fallback:        $InstallDir\start-brain.bat" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Restart VS Code (to activate companion extension)" -ForegroundColor Yellow
Write-Host "  2. On the voice machine, run install-voice and point it at this machine's IP" -ForegroundColor Yellow
Write-Host ""
