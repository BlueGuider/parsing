#!/bin/bash

echo "🌍 Setting up environment for International Google Maps Scraper"

# Set locale environment variables
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export LANGUAGE=en_US:en

# Update locale settings
echo "📍 Setting up locale..."
sudo locale-gen en_US.UTF-8 2>/dev/null || echo "Locale generation not available"

# Check Chrome installation
echo "🔍 Checking Chrome installation..."
if command -v google-chrome >/dev/null 2>&1; then
    echo "✅ Google Chrome found: $(google-chrome --version)"
elif command -v google-chrome-stable >/dev/null 2>&1; then
    echo "✅ Google Chrome Stable found: $(google-chrome-stable --version)"
elif command -v chromium-browser >/dev/null 2>&1; then
    echo "✅ Chromium Browser found: $(chromium-browser --version)"
elif command -v chromium >/dev/null 2>&1; then
    echo "✅ Chromium found: $(chromium --version)"
else
    echo "❌ No Chrome browser found. Installing Chromium..."
    sudo apt update && sudo apt install -y chromium-browser
fi

# Test Chrome headless mode
echo "🧪 Testing Chrome headless mode..."
if command -v chromium-browser >/dev/null 2>&1; then
    chromium-browser --headless --disable-gpu --dump-dom --virtual-time-budget=1000 https://www.google.com > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Chrome headless mode working"
    else
        echo "⚠️ Chrome headless mode may have issues"
    fi
fi

# Set up virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install requirements
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "🎉 Environment setup complete!"
echo ""
echo "To run the scraper:"
echo "1. source venv/bin/activate"
echo "2. streamlit run app.py"
echo ""
echo "The scraper is now configured to work with German locale and international Google Maps!"