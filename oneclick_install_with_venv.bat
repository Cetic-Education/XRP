echo off
echo "Building venv in current, please ensure python can be used in command line \nVenv will be installed at current bat location, press y to continue process"
choice /c YN /M "press Y to continue process, N to exit" /t 10 /d N
@if %errorlevel% == 2 exit
@if %errorlevel% == 1 goto next
pause
exit
:next
if exist %~dp0.venv (
    echo ".venv exist, installing requirement" 
    goto requirement
) else (
    echo "Building venv"
    python -m venv %~dp0.venv)
:requirement
if exist %~dp0requirements.txt (
    echo "Requirements.txt exist, installing"
    %~dp0.venv\Scripts\pip install -r %~dp0requirements.txt)^
else (echo "Requirements.txt not exist, exiting")

:last
exit
