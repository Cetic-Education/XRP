@echo off
setlocal enabledelayedexpansion

:: switch to the script directory
cd /d "%~dp0"

echo ==========================================
echo            XRP Robot Setup         
echo ==========================================
echo.

:: ------------------------------------------------
:: 1. Checking Python environment
:: ------------------------------------------------
echo [1/3] Checking Python environment...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set "PY_VERSION=%%i"
    echo Found Python: !PY_VERSION!
    
    echo !PY_VERSION! | findstr /b "3.10" >nul
    if !errorlevel! neq 0 (
        echo [WARNING] Python version is not 3.10. 
    ) else (
        echo Version check passed [3.10.x].
    )
    goto :check_venv
)

echo Python NOT found!
echo.
echo We need to install Python 3.10.
echo ---------------------------------------------------
echo Plan A: Install via Winget (Microsoft Store)
echo Plan B: Download directly from Python.org
echo ---------------------------------------------------
echo.

choice /c YN /M "Do you want to start installation? Please confirm you are launched this script as Administrator. " /t 15 /d N
if %errorlevel% neq 1 exit

:: ------------------------------------------------
:: 2. Plan A: Winget Installation
:: ------------------------------------------------
echo.
echo [Plan A] Trying Winget...
winget install -e --id Python.Python.3.10 --scope machine --accept-source-agreements --accept-package-agreements

if %errorlevel% equ 0 goto :install_success

echo.
echo [Plan A Failed] Winget could not install Python.
echo.

:: ------------------------------------------------
:: 3. Plan B: Direct Download Installation (Fallback)
:: ------------------------------------------------
:plan_b
echo [Plan B] Attempting direct download from Python.org...

:: Setting download URL (Python 3.10.11 stable version)
set "PY_URL=https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
set "INSTALLER=python_installer.exe"

echo Downloading %PY_URL%...
curl -L -o %INSTALLER% %PY_URL%

if not exist %INSTALLER% (
    echo.
    echo [ERROR] Download failed. Please check internet connection.
    echo You must install Python 3.10 manually.
    pause
    exit
)

echo.
echo Installing Python silently...
echo -------------------------------------------------------
echo [ACTION REQUIRED] Please click 'Yes' if UAC prompt appears.
echo -------------------------------------------------------

:: [KEY FIX] Ensure this command is on the same line, do not break it
call %INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed or cancelled.
    echo Please try running this script as Administrator.
    del %INSTALLER%
    pause
    exit
)

:: Cleaning up installer
del %INSTALLER%

:install_success
echo.
echo ========================================================
echo [IMPORTANT] Python 3.10 installed successfully!
echo.
echo Windows requires a restart of the terminal to update PATH.
echo Please CLOSE this window and RUN this script again.
echo ========================================================
pause
exit

:: ------------------------------------------------
:: 4. Creating Virtual Environment (Venv)
:: ------------------------------------------------
:check_venv
echo.
echo [2/3] Checking Virtual Environment (.venv)...

if exist ".venv" (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit
    )
    echo Virtual environment created.
)

:: ------------------------------------------------
:: 5. Installing Dependencies (Requirements)
:: ------------------------------------------------
:install_reqs
echo.
echo [3/3] Installing Requirements...

set "REQ_FILE="
if exist "requirements.txt" set "REQ_FILE=requirements.txt"
if exist "requirement.txt" set "REQ_FILE=requirement.txt"

if defined REQ_FILE (
    echo Installing libraries from !REQ_FILE!...
    .venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    .venv\Scripts\pip install -r !REQ_FILE!
    
    if !errorlevel! equ 0 (
        echo.
        echo [SUCCESS] Setup Complete!
    ) else (
        echo.
        echo [ERROR] Failed to install requirements.
    )
) else (
    echo [WARNING] requirements.txt not found.
)

pause