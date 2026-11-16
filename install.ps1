# install.ps1 - Installs agyc into agy's bin folder or user PATH

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetDir = Join-Path $env:LOCALAPPDATA "agy\bin"

Write-Host "Installing agyc wrapper..." -ForegroundColor Cyan

if (Test-Path $TargetDir) {
    Copy-Item (Join-Path $ScriptDir "agyc.py") -Destination $TargetDir -Force
    Copy-Item (Join-Path $ScriptDir "agyc.cmd") -Destination $TargetDir -Force
    Copy-Item (Join-Path $ScriptDir "agyc.ps1") -Destination $TargetDir -Force
    Write-Host "Successfully installed agyc to: $TargetDir" -ForegroundColor Green
    Write-Host "Since $TargetDir is already in your PATH, you can now run 'agyc' from any terminal!" -ForegroundColor Green
} else {
    Write-Host "Could not find $TargetDir. Adding $ScriptDir to User PATH..." -ForegroundColor Yellow
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$ScriptDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$ScriptDir", "User")
        Write-Host "Added $ScriptDir to User PATH." -ForegroundColor Green
    } else {
        Write-Host "$ScriptDir is already in User PATH." -ForegroundColor Yellow
    }
}

Write-Host "`nInstallation complete! Try running:" -ForegroundColor Cyan
Write-Host "  agyc --agyc-help"
Write-Host "  agyc"
