# start.sh - Shell script for Linux/Mac
#!/bin/bash

echo "🎵 Starting Ultimate Music Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs downloads cache temp

# Check if .env exists
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "📝 Creating .env from template..."
        cp .env.template .env
        echo "⚠️  Please edit .env file with your bot tokens!"
        read -p "Press Enter after editing .env file..."
    else
        echo "❌ .env.template not found!"
        exit 1
    fi
fi

# Start the bot
echo "🚀 Starting bot..."
python run.py
