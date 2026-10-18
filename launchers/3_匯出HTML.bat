@echo off
rem Export notebooks to HTML. Drag .ipynb files onto this file, or double-click to pick one from exam\.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
"%PYTHON%" "%STAT_ROOT%\workspace\tools\export_html.py" %*
echo.
pause
