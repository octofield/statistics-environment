@echo off
rem Portable environment for the USB stick (called by the launchers in the root folder).
rem Keep this file ASCII-only: cmd mis-parses multi-byte characters in batch files.
set "STAT_ROOT=%~dp0..\.."
pushd "%STAT_ROOT%"
set "STAT_ROOT=%CD%"
popd

set "WINPY_BASE="
for /d %%D in ("%STAT_ROOT%\WPy64-*") do set "WINPY_BASE=%%~fD"
if not defined WINPY_BASE (
    echo [ERROR] WinPython folder not found: %STAT_ROOT%\WPy64-*
    exit /b 1
)
call "%WINPY_BASE%\scripts\env.bat"

rem Python on Windows ignores HOME, so point every config/cache dir into WinPython\settings
set "MPLCONFIGDIR=%WINPY_BASE%\settings\.matplotlib"
set "JUPYTER_CONFIG_DIR=%WINPY_BASE%\settings\.jupyter"
set "JUPYTER_DATA_DIR=%WINPY_BASE%\settings\jupyter_data"
set "IPYTHONDIR=%WINPY_BASE%\settings\.ipython"
rem Never load packages from the exam PC's user site-packages
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
exit /b 0
