import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
import os
import locale

# Set UTF-8 encoding to handle international characters
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Try to set a UTF-8 locale
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except locale.Error:
        pass  # Use system default

def setup_driver():
    """Setup Chrome driver with options suitable for VPS environments"""
    chrome_options = Options()
    
    # Essential headless options for VPS
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-translate")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Window size and user agent
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Language settings
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en',
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2
    })
    
    # Try different Chrome binary locations
    chrome_binaries = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable", 
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium"
    ]
    
    binary_found = False
    for binary in chrome_binaries:
        if os.path.exists(binary):
            chrome_options.binary_location = binary
            binary_found = True
            print(f"Using Chrome binary: {binary}")
            break
    
    if not binary_found:
        print("Warning: No Chrome binary found, using system default")
    
    try:
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Set additional properties to avoid detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        return driver
    except Exception as e:
        print(f"webdriver-manager failed: {e}")
        # Fallback: try without webdriver-manager
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e2:
            if 'st' in globals():
                st.error(f"Failed to setup Chrome driver: {str(e)}")
                st.error(f"Fallback also failed: {str(e2)}")
                st.info("Please ensure Chrome/Chromium is installed on your system")
            else:
                print(f"Failed to setup Chrome driver: {str(e)}")
                print(f"Fallback also failed: {str(e2)}")
            return None

def search_google_maps(query, max_results=50):
    """
    Search Google Maps and extract business information
    Enhanced with precise address and phone extraction
    """
    driver = setup_driver()
    if not driver:
        return []
    
    results = []
    
    try:
        # Construct Google Maps search URL with English interface
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        driver.get(search_url)
        
        # Wait for the page to load
        time.sleep(8)
        
        # Wait for search results to appear
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
            )
        except TimeoutException:
            st.warning("Search results didn't load properly")
            return []
        
        # Scroll to load more results
        st.info(f"📜 Loading more results...")
        for i in range(15):  # More scrolling for more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # Get all business containers
        containers = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc, .Nv2PK, [data-result-index]')
        st.info(f"📋 Processing {len(containers)} business containers...")
        
        # Process each container
        for i, container in enumerate(containers[:max_results]):
            try:
                # Get all text content
                full_text = container.text
                if not full_text or len(full_text) < 10:
                    continue
                
                # Split into lines and clean
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                # Extract business information
                business_info = parse_business_lines_improved(lines)
                
                if business_info['name']:
                    results.append(business_info)
                    st.info(f"✅ Extracted: {business_info['name']}")
                    
            except Exception as e:
                st.warning(f"⚠️ Error processing container {i}: {e}")
                continue
        
    except Exception as e:
        st.error(f"Error during scraping: {str(e)}")
    
    finally:
        driver.quit()
    
    return results

def parse_business_lines_improved(lines):
    """Parse business information from text lines with improved accuracy"""
    business_info = {
        'name': '',
        'rating': '',
        'reviews': '',
        'category': '',
        'address': '',
        'phone': '',
        'website': '',
        'hours': ''
    }
    
    if not lines:
        return business_info
    
    # First line is usually the business name
    business_info['name'] = clean_business_name_improved(lines[0])
    
    # Look through remaining lines for data
    for line in lines[1:]:
        line = line.strip()
        
        # Skip common non-data lines
        if any(skip in line.lower() for skip in ['directions', 'website', 'call', 'suggest an edit']):
            continue
        
        # Extract rating and reviews from patterns like "4.8(82)" or "4.8 (82)"
        rating_review_match = re.search(r'(\d+\.?\d*)\s*\((\d+)\)', line)
        if rating_review_match and not business_info['rating']:
            business_info['rating'] = rating_review_match.group(1)
            business_info['reviews'] = rating_review_match.group(2)
            continue
        
        # Check if line is an address
        if is_address_line_improved(line):
            if not business_info['address']:
                business_info['address'] = clean_address_improved(line)
            continue
        
        # Check if line contains a phone number
        phone_match = re.search(r'\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})', line)
        if phone_match and not business_info['phone']:
            business_info['phone'] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
            continue
        
        # Check for category/type (but not if it's hours or other info)
        if not business_info['category'] and len(line) < 50:
            if any(cat in line.lower() for cat in ['vehicle wrapping', 'car detailing', 'sign shop', 'auto', 'wrap']):
                business_info['category'] = line
    
    return business_info

def is_address_line_improved(line):
    """Check if a line looks like an address with improved patterns"""
    if len(line) < 10 or len(line) > 150:
        return False
    
    # Must contain a number
    if not re.search(r'\d', line):
        return False
    
    # Skip lines that are clearly not addresses
    skip_patterns = [
        r'^\d+\.?\d*\s*\(',  # Ratings like "4.8(82)"
        r'open|close|hour|minute|am|pm',
        r'star|review|rating',
        r'vehicle wrapping|car detailing|sign shop'
    ]
    
    for pattern in skip_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return False
    
    # Check for address patterns
    address_indicators = [
        r'\d+\s+\w+.*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Pkwy|Parkway|Circle|Cir|Court|Ct|Place|Pl)\b',
        r'\d+\s+[NSEW]\s+\w+',  # Like "123 N Main St"
        r'\d+\s+W\s+State\s+Rd',  # Like "10388 W State Rd 84"
        r'\d+.*(?:Suite|STE|#)\s*\d+',  # Suite numbers
        r'\d+.*,.*FL\s+\d{5}',  # Florida addresses with zip
    ]
    
    for pattern in address_indicators:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    return False

def clean_address_improved(address):
    """Clean address with improved precision"""
    if not address:
        return ""
    
    # Remove everything after · character (common in Google Maps)
    address = re.sub(r'\s*·.*$', '', address)
    
    # Remove hours information
    address = re.sub(r'\s*(?:Open|Closed|Closes|Opens).*$', '', address, flags=re.IGNORECASE)
    
    # Remove phone numbers that might be mixed in
    address = re.sub(r'\s*\(\d{3}\)\s*\d{3}[-.\s]?\d{4}.*$', '', address)
    
    # Remove extra parentheses content (but keep suite numbers)
    if not re.search(r'#\d+|Suite|STE', address):
        address = re.sub(r'\s*\([^)]*\)', '', address)
    
    # Normalize spaces
    address = re.sub(r'\s+', ' ', address).strip()
    
    return address

def clean_business_name_improved(name):
    """Clean business name with improved accuracy"""
    if not name:
        return ""
    
    # Remove rating information that might be attached
    name = re.sub(r'\s*\d+\.?\d*\s*\(\d+\).*$', '', name)
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^\d+\.\s*', '', name)  # Remove numbering
    name = re.sub(r'\s*[·•]\s*.*$', '', name)  # Remove after bullet points
    
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

# Legacy function removed - using improved version above

# Streamlit UI
st.title("🗺️ Google Maps Business Scraper")
st.write("Extract business information from Google Maps (International Version)")

# Input section
query = st.text_input("Enter search query (e.g., 'restaurants in Berlin'):")
max_results = st.slider("Maximum results to scrape:", min_value=10, max_value=100, value=50)

if st.button("Start Scraping"):
    if query:
        st.info("🔍 Searching Google Maps... This may take a few minutes.")
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Perform the search
        status_text.text("Setting up browser...")
        progress_bar.progress(10)
        
        status_text.text("Searching Google Maps...")
        progress_bar.progress(30)
        
        results = search_google_maps(query, max_results)
        
        progress_bar.progress(90)
        status_text.text("Processing results...")
        
        if results:
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Clean up the data
            df = df.fillna('')
            
            progress_bar.progress(100)
            status_text.text(f"✅ Found {len(results)} businesses!")
            
            # Display results
            st.success(f"Successfully scraped {len(results)} businesses!")
            
            # Show preview
            st.subheader("📊 Results Preview")
            st.dataframe(df.head(10))
            
            # Download options
            st.subheader("💾 Download Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV download
                csv = df.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="📄 Download as CSV",
                    data=csv,
                    file_name=f"google_maps_results_{query.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Excel download
                excel_buffer = pd.ExcelWriter('temp_results.xlsx', engine='openpyxl')
                df.to_excel(excel_buffer, index=False)
                excel_buffer.close()
                
                with open('temp_results.xlsx', 'rb') as f:
                    excel_data = f.read()
                
                st.download_button(
                    label="📊 Download as Excel",
                    data=excel_data,
                    file_name=f"google_maps_results_{query.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Clean up temp file
                os.remove('temp_results.xlsx')
            
            # Statistics
            st.subheader("📈 Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Results", len(results))
            
            with col2:
                rated_businesses = len([r for r in results if r.get('rating')])
                st.metric("With Ratings", rated_businesses)
            
            with col3:
                with_phone = len([r for r in results if r.get('phone')])
                st.metric("With Phone", with_phone)
            
            with col4:
                with_address = len([r for r in results if r.get('address')])
                st.metric("With Address", with_address)
        
        else:
            progress_bar.progress(100)
            status_text.text("❌ No results found")
            st.error("No results found. Please try a different search query or check your internet connection.")
    
    else:
        st.warning("Please enter a search query.")

# Instructions
with st.expander("ℹ️ How to use"):
    st.write("""
    1. **Enter a search query**: Type what you're looking for (e.g., "restaurants in Berlin", "hotels in Munich")
    2. **Set maximum results**: Choose how many results you want to scrape (10-100)
    3. **Click 'Start Scraping'**: The tool will search Google Maps and extract business information
    4. **Download results**: Get your data as CSV or Excel file
    
    **Note**: This tool works internationally and handles different languages and locales.
    """)

# Footer
st.markdown("---")
st.markdown("🌍 **International Google Maps Scraper** - Works worldwide with proper locale handling")
