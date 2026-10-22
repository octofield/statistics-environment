@echo off
rem Start JupyterLab (backup option). ASCII-only on purpose.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
echo Starting JupyterLab, a browser window will open.
echo DO NOT close this window - closing it stops JupyterLab.
"%PYTHON%" -m jupyterlab --notebook-dir="%STAT_ROOT%\workspace"
pause
