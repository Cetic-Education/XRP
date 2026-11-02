@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ===================================================
echo           XRP One-Click Venv Installation          
echo ===================================================
echo.

if "%1"=="--help" goto :show_help
if "%1"=="-h" goto :show_help

:: 1. Handle confirmation (skip if called with --yes, --china, or --default)
set "SKIP_CONFIRM=0"
if "%1"=="--yes" set "SKIP_CONFIRM=1"
if "%2"=="--yes" set "SKIP_CONFIRM=1"
if "%3"=="--yes" set "SKIP_CONFIRM=1"
if "%1"=="--china" set "SKIP_CONFIRM=1"
if "%2"=="--china" set "SKIP_CONFIRM=1"
if "%3"=="--china" set "SKIP_CONFIRM=1"
if "%1"=="--default" set "SKIP_CONFIRM=1"
if "%2"=="--default" set "SKIP_CONFIRM=1"
if "%3"=="--default" set "SKIP_CONFIRM=1"

if "%SKIP_CONFIRM%"=="0" (
    echo This script will set up a Python virtual environment in:
    echo %~dp0.venv
    echo.
    set "CONFIRM_IN=n"
    set /p "CONFIRM_IN=Do you want to continue? [y/N]: "
    if /i not "!CONFIRM_IN!"=="y" (
        echo Operation cancelled by user.
        exit /b 0
    )
)

:: 2. Check or Create Virtual Environment
if exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Virtual environment already exists.
) else (
    echo [INFO] Creating virtual environment .venv...
    python -m venv "%~dp0.venv"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment. Ensure Python is installed.
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
)

:: 3. Mirror Selection
set "PIP_MIRROR_OPT="
set "CHINA_MODE="

if "%1"=="--china" set "CHINA_MODE=Y"
if "%2"=="--china" set "CHINA_MODE=Y"
if "%3"=="--china" set "CHINA_MODE=Y"
if "%1"=="--default" set "CHINA_MODE=N"
if "%2"=="--default" set "CHINA_MODE=N"
if "%3"=="--default" set "CHINA_MODE=N"
if not defined CHINA_MODE if defined XRP_CHINA_MIRROR (
    if "%XRP_CHINA_MIRROR%"=="1" set "CHINA_MODE=Y"
    if "%XRP_CHINA_MIRROR%"=="0" set "CHINA_MODE=N"
)

if not defined CHINA_MODE (
    echo.
    set "USER_MIRROR_IN=n"
    set /p "USER_MIRROR_IN=Are you located in China? Use Tsinghua PyPI mirror? [y/N]: "
    if /i "!USER_MIRROR_IN!"=="y" (
        set "CHINA_MODE=Y"
    ) else (
        set "CHINA_MODE=N"
    )
)

if "%CHINA_MODE%"=="Y" (
    echo [INFO] Configuring Tsinghua PyPI mirror...
    "%~dp0.venv\Scripts\pip" config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
    set "PIP_MIRROR_OPT=-i https://pypi.tuna.tsinghua.edu.cn/simple"
) else (
    echo [INFO] Retaining default PyPI index.
)

:: 4. Locate requirements.txt
set "REQ_PATH="
if exist "%~dp0requirements.txt" set "REQ_PATH=%~dp0requirements.txt"
if exist "%~dp0Software\requirements.txt" set "REQ_PATH=%~dp0Software\requirements.txt"
if exist "%~dp0..\requirements.txt" set "REQ_PATH=%~dp0..\requirements.txt"

if defined REQ_PATH (
    echo [INFO] Installing requirements from !REQ_PATH!...
    "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip !PIP_MIRROR_OPT! >nul 2>&1
    "%~dp0.venv\Scripts\pip" install !PIP_MIRROR_OPT! -r "!REQ_PATH!"
    if !errorlevel! equ 0 (
        echo.
        echo [SUCCESS] Dependencies installed successfully!
    ) else (
        echo.
        echo [ERROR] Failed to install dependencies.
        exit /b 1
    )
) else (
    echo [WARNING] requirements.txt not found.
)

exit /b 0

:show_help
echo Usage: oneclick_install_with_venv.bat [--china ^| --default] [--yes]
exit /b 0
