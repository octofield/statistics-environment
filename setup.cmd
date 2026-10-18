@echo off
rem Statistics exam environment - setup wizard.
rem Double-click this file. It removes the "downloaded from the internet" mark from this folder
rem (so PowerShell is allowed to run the scripts) and opens the setup wizard. No admin rights needed.
set "SETUP_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -LiteralPath $env:SETUP_DIR -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue"
start "" powershell -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%~dp0setup\Setup-Wizard.ps1"
