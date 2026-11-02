#!/bin/bash

# ==========================================
#            XRP Robot Setup (Mac)
# ==========================================

# 設置顏色變數，讓輸出更清晰
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 確保腳本在當前目錄執行 (相當於 Windows 的 cd /d "%~dp0")
cd "$(dirname "$0")" || exit

echo -e "${YELLOW}==========================================${NC}"
echo -e "${YELLOW}            XRP Robot Setup               ${NC}"
echo -e "${YELLOW}==========================================${NC}"
echo ""

# ------------------------------------------------
# 1. Checking Python environment
# ------------------------------------------------
echo -e "[1/3] Checking Python environment..."

# 定義我們需要的具體版本命令
TARGET_PY="python3.10"

# 檢查是否已安裝 python3.10
if command -v $TARGET_PY &> /dev/null; then
    PY_VERSION=$($TARGET_PY --version)
    echo -e "${GREEN}Found Python: $PY_VERSION${NC}"
else
    echo -e "${RED}Python 3.10 NOT found!${NC}"
    echo ""
    echo "We need to install Python 3.10."
    echo "---------------------------------------------------"
    echo "Plan A: Install via Homebrew (Recommended)"
    echo "---------------------------------------------------"
    echo ""

    read -p "Do you want to start installation? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 1
    fi

    # ------------------------------------------------
    # 2. Plan A: Homebrew Installation
    # ------------------------------------------------
    echo ""
    echo "[Plan A] Checking Homebrew..."

    if ! command -v brew &> /dev/null; then
        echo -e "${RED}[ERROR] Homebrew is not installed.${NC}"
        echo "Please install Homebrew first by visiting https://brew.sh/"
        echo "Or install Python 3.10 manually from https://www.python.org/downloads/macos/"
        exit 1
    fi

    echo "Installing python@3.10 via Homebrew..."
    brew install python@3.10

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}[SUCCESS] Python 3.10 installed successfully!${NC}"
    else
        echo -e "${RED}[ERROR] Homebrew failed to install Python.${NC}"
        exit 1
    fi
fi

# ------------------------------------------------
# 3. Creating Virtual Environment (Venv)
# ------------------------------------------------
echo ""
echo -e "[2/3] Checking Virtual Environment (.venv)..."

if [ -d ".venv" ]; then
    echo "Virtual environment already exists."
else
    echo "Creating virtual environment..."
    $TARGET_PY -m venv .venv
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Failed to create venv.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Virtual environment created.${NC}"
fi

# ------------------------------------------------
# 4. Installing Dependencies (Requirements)
# ------------------------------------------------
echo ""
echo -e "[3/3] Installing Requirements..."

REQ_FILE=""
if [ -f "requirements.txt" ]; then
    REQ_FILE="requirements.txt"
elif [ -f "Software/requirements.txt" ]; then
    REQ_FILE="Software/requirements.txt"
elif [ -f "requirement.txt" ]; then
    REQ_FILE="requirement.txt"
fi

CHINA_CHOICE=""
if [[ "$1" == "--china" || "$2" == "--china" ]]; then
    CHINA_CHOICE="y"
elif [[ "$1" == "--default" || "$2" == "--default" ]]; then
    CHINA_CHOICE="n"
elif [ -n "$XRP_CHINA_MIRROR" ]; then
    if [ "$XRP_CHINA_MIRROR" = "1" ]; then
        CHINA_CHOICE="y"
    else
        CHINA_CHOICE="n"
    fi
fi

if [ -z "$CHINA_CHOICE" ]; then
    echo ""
    read -r -p "Are you located in China? Use Tsinghua PyPI mirror? [y/N]: " CHINA_CHOICE
fi

PIP_INDEX_OPT=""
if [[ "$CHINA_CHOICE" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}[INFO] Configuring Tsinghua PyPI mirror...${NC}"
    ./.venv/bin/pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple > /dev/null 2>&1
    PIP_INDEX_OPT="-i https://pypi.tuna.tsinghua.edu.cn/simple"
else
    echo -e "${YELLOW}[INFO] Retaining default PyPI index.${NC}"
fi

if [ -n "$REQ_FILE" ]; then
    echo "Installing libraries from $REQ_FILE..."
    ./.venv/bin/pip install --upgrade pip $PIP_INDEX_OPT > /dev/null 2>&1
    ./.venv/bin/pip install $PIP_INDEX_OPT -r "$REQ_FILE"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}==========================================${NC}"
        echo -e "${GREEN}            [SUCCESS] Setup Complete!     ${NC}"
        echo -e "${GREEN}==========================================${NC}"
        echo "To run your script manually, use:"
        echo "./.venv/bin/python your_script.py"
    else
        echo ""
        echo -e "${RED}[ERROR] Failed to install requirements.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}[WARNING] requirements.txt not found.${NC}"
fi

# 保持視窗開啟 (如果是雙擊執行的話)
if [ -t 0 ]; then
    read -r -p "Press enter to exit..."
fi
