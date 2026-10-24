@echo off
rem Import the exam notebook given by the teacher into exam\ (keeps the file name), add the setup cell and open it.
rem Drag the .ipynb onto this file, or double-click to pick it (the dialog opens in Downloads).
call "%~dp0workspace\tools\env.bat" || (pause & exit /b 1)
set "ELECTRON_RUN_AS_NODE="
"%PYTHON%" "%STAT_ROOT%\workspace\tools\import_exam.py" --open %*
echo.
pause
