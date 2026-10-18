@echo off
rem Create a new exam notebook (exam\<id>_<name>_<exam>.ipynb) from the clean template and open it.
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
set "ELECTRON_RUN_AS_NODE="
"%PYTHON%" "%STAT_ROOT%\workspace\tools\new_exam.py" --open || pause
timeout /t 3 >nul
