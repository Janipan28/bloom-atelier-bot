@echo off
cd /d "%~dp0"

if not exist .venv (
    echo Creating virtual environment...
    py -m venv .venv
)

call .venv\Scripts\activate

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Starting Telegram order button bot...
python bot.py

pause
