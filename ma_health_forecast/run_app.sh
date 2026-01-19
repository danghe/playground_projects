#!/bin/bash

# M&A Forecast "Smart Runner" for Mac/Linux
# 1. Checks for Python3
# 2. Creates virtual environment (.venv) if missing or broken
# 3. Installs dependencies
# 4. Runs the app

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "==================================================="
echo "   M&A Health Forecast - Launcher"
echo "==================================================="

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 could not be found."
    echo "Please install Python 3 from https://www.python.org/"
    exit 1
fi

# 2. Check/Create Virtual Environment
NEEDS_CREATION=0
if [ -d ".venv" ]; then
    if [ ! -f ".venv/bin/activate" ]; then
        echo ">> Detected invalid virtual environment (likely copied from Windows)."
        NEEDS_CREATION=1
    fi
else
    NEEDS_CREATION=1
fi

if [ $NEEDS_CREATION -eq 1 ]; then
    echo ">> Creating fresh virtual environment..."
    python3 -m venv --clear .venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        exit 1
    fi
    echo ">> Virtual environment created."
fi

# 3. Install Dependencies
echo ">> Checking and installing dependencies (deal-radar/yfinance)..."
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    # Show output for transparency
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
    echo ">> Dependencies are ready."
else
    echo "WARNING: requirements.txt not found."
fi

# 4. Run App
echo ">> Starting application..."
echo "---------------------------------------------------"
echo "Open your browser to: http://127.0.0.1:5000"
echo "---------------------------------------------------"
python app.py
