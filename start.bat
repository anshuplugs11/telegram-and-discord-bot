# start.bat - Batch script for Windows
@echo off
echo 🎵 Starting Ultimate Music Bot...

REM Check if virtual environment exists
if not exist "venv\" (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install/update requirements
echo 📥 Installing requirements...
pip install -r requirements.txt

REM Create necessary directories
if not exist "logs\" mkdir logs
if not exist "downloads\" mkdir downloads
if not exist "cache\" mkdir cache
if not exist "temp\" mkdir temp

REM Check if .env exists
if not exist ".env" (
    if exist ".env.template" (
        echo 📝 Creating .env from template...
        copy .env.template .env
        echo ⚠️  Please edit .env file with your bot tokens!
        pause
    ) else (
        echo ❌ .env.template not found!
        pause
        exit /b 1
    )
)

REM Start the bot
echo 🚀 Starting bot...
python run.py

pause
