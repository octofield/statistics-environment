@echo off
rem Check the exam environment: packages, statkit, CJK font, HTML export, AI extensions.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
rem Built on a Mac: install the bundled VS Code extensions (offline) on the first run
"%PYTHON%" "%STAT_ROOT%\workspace\tools\finish_setup.py"
"%PYTHON%" "%STAT_ROOT%\workspace\tools\check_env.py"
echo.
pause
