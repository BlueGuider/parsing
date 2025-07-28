# 🌍 International Google Maps Business Scraper

A robust, language-agnostic Google Maps scraper designed to work seamlessly across different locales and VPS environments, including German servers.

## ✨ Features

- **🌐 International Support**: Works with German, English, and other locales
- **🔧 VPS-Optimized**: Configured for headless operation on virtual private servers
- **📊 Multiple Export Formats**: CSV and Excel download options
- **🎯 Smart Extraction**: Handles different languages and interface layouts
- **⚡ Auto-Setup**: Automatic Chrome driver management with webdriver-manager
- **🛡️ Robust Error Handling**: Graceful fallbacks and detailed error reporting

## 🚀 Quick Start

### 1. Environment Setup

Run the automated setup script:
```bash
chmod +x setup_environment.sh
./setup_environment.sh
```

### 2. Manual Setup (if needed)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test the scraper
python test_scraper.py
```

### 3. Run the Application

```bash
source venv/bin/activate
streamlit run app.py
```

## 🔧 Language & Locale Issues Fixed

### Problem
The original scraper failed on German VPS due to:
- ❌ Language-specific Google Maps interface
- ❌ Missing locale configuration
- ❌ Chrome browser setup issues
- ❌ Encoding problems with international characters

### Solution
- ✅ **Multi-language selectors**: Handles German, English, and other interfaces
- ✅ **UTF-8 encoding**: Proper character encoding for international text
- ✅ **Chrome language forcing**: Forces English interface for consistency
- ✅ **Robust browser detection**: Multiple Chrome/Chromium binary paths
- ✅ **Webdriver auto-management**: Automatic ChromeDriver installation

## 📋 Requirements

- Python 3.7+
- Chrome/Chromium browser
- Internet connection
- Virtual environment (recommended)

### System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3-venv python3-pip chromium-browser

# Or install Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update && sudo apt install -y google-chrome-stable
```

## 🎯 Usage

1. **Enter Search Query**: Type what you're looking for (e.g., "restaurants in Berlin")
2. **Set Maximum Results**: Choose between 10-100 results
3. **Start Scraping**: Click the button and wait for results
4. **Download Data**: Export as CSV or Excel

### Example Queries
- `restaurants in Berlin`
- `hotels in Munich`
- `car repair shops in Hamburg`
- `bakeries near Frankfurt`

## 📊 Extracted Data

The scraper extracts the following information:
- **Name**: Business name
- **Rating**: Star rating (e.g., 4.5)
- **Reviews**: Number of reviews
- **Category**: Business type/category
- **Address**: Full address
- **Phone**: Phone number (if available)
- **Website**: Website URL (if available)
- **Hours**: Operating hours (if available)

## 🛠️ Technical Details

### Chrome Configuration
- Headless mode for VPS compatibility
- Language set to English for consistent interface
- Optimized for server environments
- Multiple browser binary detection

### Locale Handling
- UTF-8 encoding enforcement
- Multiple locale fallbacks
- International character support
- German VPS compatibility

### Extraction Strategy
- Multiple CSS selector approaches
- Language-agnostic pattern matching
- Robust error handling and retries
- Smart duplicate detection

## 🧪 Testing

Run the test suite to verify everything works:
```bash
python test_scraper.py
```

Expected output:
```
🌍 International Google Maps Scraper - Test Suite
============================================================
🧪 Testing Chrome driver setup...
✅ Chrome driver setup successful!
✅ Successfully navigated to Google

🔍 Testing Google Maps search...
Searching for: restaurants in Berlin
✅ Found 5 results!
🎉 All tests passed! The scraper is working correctly.
```

## 🐛 Troubleshooting

### Chrome/Chromium Issues
```bash
# Check if Chrome is installed
which google-chrome || which chromium-browser

# Install Chromium
sudo apt install chromium-browser

# Test headless mode
chromium-browser --headless --dump-dom https://www.google.com
```

### Locale Issues
```bash
# Check current locale
locale

# Generate UTF-8 locale
sudo locale-gen en_US.UTF-8

# Set environment variables
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
```

### Permission Issues
```bash
# Make scripts executable
chmod +x setup_environment.sh
chmod +x test_scraper.py
```

### Network Issues
- Ensure internet connectivity
- Check firewall settings
- Verify Google Maps is accessible

## 📁 Project Structure

```
├── app.py                    # Main Streamlit application
├── test_scraper.py          # Test suite
├── setup_environment.sh     # Environment setup script
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── venv/                   # Virtual environment (created after setup)
```

## 🔄 Updates from Original Version

### Major Improvements
1. **International Compatibility**: Removed US-specific assumptions
2. **Language Agnostic**: Works with German and other locales
3. **VPS Optimization**: Headless Chrome with proper flags
4. **Auto Driver Management**: webdriver-manager integration
5. **Better Error Handling**: Comprehensive error messages and fallbacks
6. **UTF-8 Support**: Proper encoding for international characters
7. **Multiple Browser Support**: Chrome, Chromium, and snap installations

### Code Changes
- Added `webdriver-manager` for automatic ChromeDriver setup
- Implemented multiple Chrome binary detection
- Added UTF-8 encoding configuration
- Enhanced CSS selectors for different languages
- Improved error handling and fallback mechanisms

## 🌟 Success Metrics

After implementing these fixes:
- ✅ **German VPS Compatibility**: Works on German servers
- ✅ **Multi-language Support**: Handles different Google Maps interfaces
- ✅ **Robust Setup**: Automatic environment configuration
- ✅ **Better Data Quality**: Improved extraction accuracy
- ✅ **Error Resilience**: Graceful handling of failures

## 📞 Support

If you encounter issues:
1. Run `python test_scraper.py` to diagnose problems
2. Check the troubleshooting section above
3. Ensure all system dependencies are installed
4. Verify Chrome/Chromium installation

## 📄 License

This project is provided as-is for educational purposes. Please respect Google's Terms of Service and rate limits when using this scraper.
