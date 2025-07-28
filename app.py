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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    # Set language to English to ensure consistent interface
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    
    # Try different Chrome binary locations
    chrome_binaries = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable", 
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium"
    ]
    
    for binary in chrome_binaries:
        if os.path.exists(binary):
            chrome_options.binary_location = binary
            break
    
    try:
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        # Fallback: try without webdriver-manager
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e2:
            st.error(f"Failed to setup Chrome driver: {str(e)}")
            st.error(f"Fallback also failed: {str(e2)}")
            st.info("Please ensure Chrome/Chromium is installed on your system")
            return None

def search_google_maps(query, max_results=50):
    """
    Search Google Maps and extract business information
    Enhanced to work with different languages and locales
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
        time.sleep(5)
        
        # Multiple selectors to handle different languages and layouts
        result_selectors = [
            '[data-result-index]',
            '[role="article"]',
            '.hfpxzc',
            '[jsaction*="pane"]'
        ]
        
        results_found = False
        for selector in result_selectors:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                results_found = True
                break
            except TimeoutException:
                continue
        
        if not results_found:
            st.warning("No results found or page didn't load properly")
            return []
        
        # Scroll to load more results
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 5
        
        while scroll_attempts < max_scroll_attempts:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # Check if we've loaded more content
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            
            last_height = new_height
            scroll_attempts += 1
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Multiple approaches to find business listings
        business_elements = []
        
        # Method 1: Look for data-result-index elements
        business_elements.extend(soup.find_all(attrs={'data-result-index': True}))
        
        # Method 2: Look for article elements (common in Maps)
        business_elements.extend(soup.find_all('div', {'role': 'article'}))
        
        # Method 3: Look for elements with specific classes
        business_elements.extend(soup.find_all('div', class_=re.compile(r'hfpxzc|Nv2PK|tH5CWc')))
        
        # Remove duplicates
        seen_elements = set()
        unique_elements = []
        for elem in business_elements:
            elem_text = elem.get_text()[:100]  # First 100 chars as identifier
            if elem_text not in seen_elements:
                seen_elements.add(elem_text)
                unique_elements.append(elem)
        
        for element in unique_elements[:max_results]:
            try:
                business_info = extract_business_info(element)
                if business_info and business_info.get('name'):
                    results.append(business_info)
            except Exception as e:
                st.warning(f"Error extracting business info: {str(e)}")
                continue
        
    except Exception as e:
        st.error(f"Error during scraping: {str(e)}")
    
    finally:
        driver.quit()
    
    return results

def extract_business_info(element):
    """
    Extract business information from a Google Maps result element
    Enhanced to handle different languages and formats
    """
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
    
    try:
        # Extract business name - multiple selectors for different layouts
        name_selectors = [
            '[data-value="Name"]',
            '.qBF1Pd',
            '.DUwDvf',
            'h3',
            '.fontHeadlineSmall'
        ]
        
        for selector in name_selectors:
            name_elem = element.select_one(selector)
            if name_elem:
                business_info['name'] = name_elem.get_text().strip()
                break
        
        # If no name found with CSS selectors, try text-based approach
        if not business_info['name']:
            text_content = element.get_text()
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            if lines:
                business_info['name'] = lines[0]
        
        # Extract rating - look for patterns like "4.5" or "4,5" (German format)
        rating_pattern = r'(\d+[.,]\d+)'
        rating_text = element.get_text()
        rating_match = re.search(rating_pattern, rating_text)
        if rating_match:
            business_info['rating'] = rating_match.group(1).replace(',', '.')
        
        # Extract number of reviews - patterns for different languages
        review_patterns = [
            r'(\d+)\s*(?:reviews?|Bewertungen?|recensioni?|avis?)',
            r'\((\d+)\)',
            r'(\d+)\s*\('
        ]
        
        for pattern in review_patterns:
            review_match = re.search(pattern, rating_text, re.IGNORECASE)
            if review_match:
                business_info['reviews'] = review_match.group(1)
                break
        
        # Extract category/type
        category_selectors = [
            '.W4Efsd:nth-of-type(1) .W4Efsd:nth-of-type(1)',
            '.W4Efsd span',
            '.fontBodyMedium'
        ]
        
        for selector in category_selectors:
            category_elem = element.select_one(selector)
            if category_elem:
                category_text = category_elem.get_text().strip()
                # Skip if it's a rating or review count
                if not re.match(r'^\d+[.,]\d+', category_text) and not re.match(r'^\(\d+\)', category_text):
                    business_info['category'] = category_text
                    break
        
        # Extract address - look for address-like patterns
        address_patterns = [
            r'\d+.*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Straße|Str|Platz)',
            r'\d+.*\d{5}',  # Postal code pattern
        ]
        
        text_lines = element.get_text().split('\n')
        for line in text_lines:
            line = line.strip()
            for pattern in address_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    business_info['address'] = line
                    break
            if business_info['address']:
                break
        
        # Extract phone number
        phone_pattern = r'(\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9})'
        phone_match = re.search(phone_pattern, element.get_text())
        if phone_match:
            business_info['phone'] = phone_match.group(1)
        
        # Extract website (if visible)
        website_elem = element.select_one('a[href*="http"]')
        if website_elem:
            href = website_elem.get('href')
            if href and not 'google.com' in href:
                business_info['website'] = href
        
    except Exception as e:
        st.warning(f"Error extracting specific business info: {str(e)}")
    
    return business_info

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
