#!/usr/bin/env python3
"""
Improved Google Maps scraper that extracts data from JavaScript
Fixes address and phone number extraction issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import json

def setup_improved_driver():
    """Setup Chrome driver for improved scraping"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    chrome_options.add_experimental_option('prefs', {
        'intl.accept_languages': 'en-US,en'
    })
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {e}")
        return None

def extract_from_javascript(page_source):
    """Extract business data from JavaScript content"""
    businesses = []
    
    try:
        # Look for the main data array in JavaScript
        # Google Maps stores data in window.APP_INITIALIZATION_STATE or similar
        js_patterns = [
            r'window\.APP_INITIALIZATION_STATE\s*=\s*(\[.*?\]);',
            r'window\.APP_FLAGS\s*=.*?(\[.*?\]);',
            r'null,\s*"([^"]*)",\s*null,\s*null,\s*null,\s*\[null,\s*"([^"]*)",\s*"([^"]*)",\s*null,\s*null,\s*null,\s*null,\s*null,\s*"([^"]*)"\]',
        ]
        
        # Extract business information using regex patterns
        # Pattern for business names and addresses
        business_pattern = r'"([^"]+)",\s*null,\s*\[?"([^"]*)",\s*"([^"]*)",\s*"([^"]*)",\s*"([^"]*)"\]'
        matches = re.findall(business_pattern, page_source)
        
        # More specific patterns for the data we saw in debug
        address_pattern = r'"([^"]*\d+[^"]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Pkwy|Parkway|Circle|Cir|Court|Ct|Place|Pl)[^"]*)"'
        phone_pattern = r'"\+?1?[-.\s]?(\(\d{3}\)\s*\d{3}[-.\s]?\d{4}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})"'
        
        # Extract specific business data we can see in the HTML
        business_data_pattern = r'"([^"]*(?:Wraps?|wrap)[^"]*)",.*?"([^"]*\d+[^"]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Pkwy|Parkway|Circle|Cir|Court|Ct|Place|Pl)[^"]*)",.*?"(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})"'
        
        # Find all business-related data
        business_matches = re.findall(business_data_pattern, page_source, re.IGNORECASE)
        
        for match in business_matches:
            name, address, phone = match
            if name and len(name) > 2 and len(name) < 100:
                businesses.append({
                    'name': name.strip(),
                    'address': clean_address(address.strip()),
                    'phone': clean_phone(phone.strip()),
                    'rating': '',
                    'reviews': '',
                    'category': 'Vehicle wrapping service',
                    'website': '',
                    'hours': ''
                })
        
        # Alternative extraction method - look for structured data
        # Extract from the specific format we saw in the debug output
        structured_pattern = r'"([^"]*(?:Wraps?|wrap)[^"]*)"[^"]*"([^"]*\d+[^"]*(?:Century|Youngerman|NW|Presidents|Marvin)[^"]*)"[^"]*"([^"]*FL[^"]*)"[^"]*"(\(\d{3}\)\s*\d{3}-\d{4})"'
        structured_matches = re.findall(structured_pattern, page_source, re.IGNORECASE)
        
        for match in structured_matches:
            name, street, city_state, phone = match
            full_address = f"{street.strip()}, {city_state.strip()}"
            
            businesses.append({
                'name': name.strip(),
                'address': clean_address(full_address),
                'phone': clean_phone(phone.strip()),
                'rating': '',
                'reviews': '',
                'category': 'Vehicle wrapping service',
                'website': '',
                'hours': ''
            })
        
        # Remove duplicates based on name
        seen_names = set()
        unique_businesses = []
        for business in businesses:
            if business['name'] not in seen_names:
                seen_names.add(business['name'])
                unique_businesses.append(business)
        
        return unique_businesses
        
    except Exception as e:
        print(f"Error extracting from JavaScript: {e}")
        return []

def clean_address(address):
    """Clean and format address properly"""
    if not address:
        return ""
    
    # Remove extra characters and clean up
    address = re.sub(r'\s*·.*$', '', address)  # Remove everything after ·
    address = re.sub(r'\s*\(.*?\)', '', address)  # Remove parentheses content
    address = re.sub(r'\s+', ' ', address)  # Normalize spaces
    
    # Keep only the actual address part (before any extra info)
    address_parts = address.split(',')
    if len(address_parts) >= 2:
        # Keep street and city/state
        street = address_parts[0].strip()
        city_state = address_parts[1].strip()
        
        # Add suite/unit number if it exists
        suite_match = re.search(r'(#\d+|STE \d+|Suite \d+)', address)
        if suite_match:
            street += f" {suite_match.group(1)}"
        
        return f"{street}, {city_state}"
    
    return address.strip()

def clean_phone(phone):
    """Clean and format phone number properly"""
    if not phone:
        return ""
    
    # Remove all non-digit characters except + and parentheses
    digits_only = re.sub(r'[^\d+()]', '', phone)
    
    # Check if it's a valid phone number (at least 10 digits)
    digit_count = len(re.sub(r'[^\d]', '', digits_only))
    if digit_count < 10:
        return ""
    
    # Format phone number
    if phone.startswith('(') and ')' in phone:
        return phone  # Already formatted
    elif digit_count == 10:
        digits = re.sub(r'[^\d]', '', phone)
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif digit_count == 11 and phone.startswith('1'):
        digits = re.sub(r'[^\d]', '', phone)[1:]  # Remove leading 1
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    
    return phone

def improved_google_maps_search(query, max_results=50):
    """Improved Google Maps search with better data extraction"""
    driver = setup_improved_driver()
    if not driver:
        return []
    
    results = []
    
    try:
        # Construct search URL
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"🌐 Searching: {search_url}")
        
        driver.get(search_url)
        time.sleep(8)  # Give more time for JavaScript to load
        
        # Wait for results to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
            )
        except TimeoutException:
            print("❌ Search results didn't load")
            return []
        
        # Scroll to load more results
        print("📜 Scrolling to load more results...")
        for i in range(10):  # Scroll multiple times
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
        
        # Get page source and extract data
        page_source = driver.page_source
        print(f"📄 Page source length: {len(page_source)} characters")
        
        # Extract businesses from JavaScript
        businesses = extract_from_javascript(page_source)
        
        if not businesses:
            # Fallback: try to extract from visible elements
            print("🔄 Trying fallback extraction...")
            businesses = extract_from_elements(driver)
        
        return businesses[:max_results]
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []
    
    finally:
        driver.quit()

def extract_from_elements(driver):
    """Fallback method to extract from visible DOM elements"""
    businesses = []
    
    try:
        # Look for business cards
        elements = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc, .Nv2PK, [data-result-index]')
        print(f"🔍 Found {len(elements)} potential business elements")
        
        for element in elements:
            try:
                # Get all text from the element
                text = element.text
                if not text or len(text) < 10:
                    continue
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                if len(lines) < 2:
                    continue
                
                # First line is usually the business name
                name = lines[0]
                
                # Look for address and phone in the text
                address = ""
                phone = ""
                
                for line in lines[1:]:
                    # Check if line looks like an address
                    if re.search(r'\d+.*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way)', line, re.IGNORECASE):
                        address = line
                    # Check if line looks like a phone number
                    elif re.search(r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}', line):
                        phone = line
                
                if name and (address or phone):
                    businesses.append({
                        'name': name,
                        'address': clean_address(address),
                        'phone': clean_phone(phone),
                        'rating': '',
                        'reviews': '',
                        'category': 'Vehicle wrapping service',
                        'website': '',
                        'hours': ''
                    })
                    
            except Exception as e:
                continue
        
        return businesses
        
    except Exception as e:
        print(f"Error in fallback extraction: {e}")
        return []

def test_improved_scraper():
    """Test the improved scraper"""
    print("🚀 Testing Improved Google Maps Scraper")
    print("=" * 50)
    
    query = "car wraps in Florida"
    print(f"🔍 Searching for: {query}")
    
    results = improved_google_maps_search(query, max_results=20)
    
    if results:
        print(f"✅ Found {len(results)} businesses!")
        
        for i, business in enumerate(results, 1):
            print(f"\n📍 Business {i}:")
            print(f"   Name: {business['name']}")
            print(f"   Address: {business['address']}")
            print(f"   Phone: {business['phone']}")
            print(f"   Category: {business['category']}")
        
        # Test the specific issues mentioned
        print(f"\n📊 Quality Check:")
        addresses_found = len([b for b in results if b['address']])
        phones_found = len([b for b in results if b['phone']])
        print(f"   Addresses extracted: {addresses_found}/{len(results)}")
        print(f"   Phone numbers extracted: {phones_found}/{len(results)}")
        
        # Check for the specific examples mentioned
        florida_car_wrap = next((b for b in results if 'Florida Car Wrap' in b['name']), None)
        if florida_car_wrap:
            print(f"\n🎯 Florida Car Wrap example:")
            print(f"   Address: {florida_car_wrap['address']}")
            print(f"   Phone: {florida_car_wrap['phone']}")
        
        return True
    else:
        print("❌ No results found")
        return False

if __name__ == "__main__":
    test_improved_scraper()