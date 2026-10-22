@echo off
rem Start portable VS Code (AI features disabled). ASCII-only on purpose.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
rem Built on a Mac: install the bundled VS Code extensions (offline) on the first run
"%PYTHON%" "%STAT_ROOT%\workspace\tools\finish_setup.py"
rem If inherited (e.g. started from another VS Code), this makes Code.exe run as plain Node and exit
set "ELECTRON_RUN_AS_NODE="
rem Rebuild the language pack cache with the current drive letter, so the UI is Chinese on the first start
"%PYTHON%" "%STAT_ROOT%\workspace\tools\vscode_locale.py" "%STAT_ROOT%\VSCode\data"
rem Open the index notebook too (found by wildcard so this file stays ASCII-only)
set "INDEX="
for %%F in ("%STAT_ROOT%\workspace\00_*.ipynb") do set "INDEX=%%~fF"
echo Starting VS Code... (first start on a new PC may take ~10 seconds)
start "" "%STAT_ROOT%\VSCode\Code.exe" --disable-extension GitHub.copilot --disable-extension GitHub.copilot-chat "%STAT_ROOT%\workspace" "%INDEX%"
