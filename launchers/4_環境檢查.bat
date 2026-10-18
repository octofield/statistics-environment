@echo off
rem Check the exam environment: packages, statkit, CJK font, HTML export, AI extensions.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
"%PYTHON%" "%STAT_ROOT%\workspace\tools\check_env.py"
echo.
pause
