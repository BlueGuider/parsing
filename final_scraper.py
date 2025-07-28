#!/usr/bin/env python3
"""
Final Google Maps scraper with precise address and phone extraction
Fixes the specific issues: proper address extraction and clean phone numbers
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

def setup_final_driver():
    """Setup Chrome driver for final scraping"""
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

def extract_precise_data(page_source):
    """Extract business data with precise address and phone extraction"""
    businesses = []
    
    try:
        # Extract from the specific JavaScript data we saw in the debug
        # Look for the pattern that contains business information
        
        # Pattern 1: Extract from the main business data structure
        # This pattern matches the exact format we saw in the debug output
        pattern1 = r'"([^"]*(?:Wraps?|wrap)[^"]*)"[^{]*?"([^"]*\d+[^"]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Century|Youngerman|NW|Presidents|Marvin)[^"]*)"[^{]*?"([^"]*FL[^"]*\d{5}[^"]*)"[^{]*?"(\+1\d{10})"'
        matches1 = re.findall(pattern1, page_source, re.IGNORECASE | re.DOTALL)
        
        for match in matches1:
            name, street, city_state, phone = match
            businesses.append({
                'name': clean_business_name(name),
                'address': f"{street.strip()}, {city_state.strip()}",
                'phone': format_phone_number(phone),
                'rating': '',
                'reviews': '',
                'category': 'Vehicle wrapping service',
                'website': '',
                'hours': ''
            })
        
        # Pattern 2: Look for addresses and phones separately
        # Extract all potential addresses
        address_pattern = r'"([^"]*\d+[^"]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Century|Youngerman|NW|Presidents|Marvin|State Rd)[^"]*(?:,\s*[^"]*FL[^"]*\d{5})?[^"]*)"'
        addresses = re.findall(address_pattern, page_source, re.IGNORECASE)
        
        # Extract all potential phone numbers
        phone_pattern = r'"(\+1\d{10})"'
        phones = re.findall(phone_pattern, page_source)
        
        # Extract business names
        name_pattern = r'"([^"]*(?:Wraps?|wrap)[^"]*)"'
        names = re.findall(name_pattern, page_source, re.IGNORECASE)
        
        # Clean and filter the extracted data
        clean_addresses = []
        for addr in addresses:
            if is_valid_address(addr):
                clean_addresses.append(clean_address_final(addr))
        
        clean_phones = [format_phone_number(phone) for phone in phones]
        clean_names = [clean_business_name(name) for name in names if is_valid_business_name(name)]
        
        # Match names with addresses and phones
        for i, name in enumerate(clean_names[:10]):  # Limit to first 10 names
            address = clean_addresses[i] if i < len(clean_addresses) else ""
            phone = clean_phones[i] if i < len(clean_phones) else ""
            
            if name and (address or phone):
                businesses.append({
                    'name': name,
                    'address': address,
                    'phone': phone,
                    'rating': '',
                    'reviews': '',
                    'category': 'Vehicle wrapping service',
                    'website': '',
                    'hours': ''
                })
        
        # Remove duplicates
        seen_names = set()
        unique_businesses = []
        for business in businesses:
            if business['name'] not in seen_names and business['name']:
                seen_names.add(business['name'])
                unique_businesses.append(business)
        
        return unique_businesses
        
    except Exception as e:
        print(f"Error in precise extraction: {e}")
        return []

def extract_from_dom_elements(driver):
    """Extract data directly from DOM elements with precise parsing"""
    businesses = []
    
    try:
        # Wait for elements to load
        time.sleep(3)
        
        # Get all business containers
        containers = driver.find_elements(By.CSS_SELECTOR, '.hfpxzc, .Nv2PK, [data-result-index]')
        print(f"📋 Processing {len(containers)} business containers...")
        
        for i, container in enumerate(containers):
            try:
                # Get all text content
                full_text = container.text
                if not full_text or len(full_text) < 10:
                    continue
                
                # Split into lines and clean
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                # Extract business information
                business_info = parse_business_lines(lines)
                
                if business_info['name']:
                    businesses.append(business_info)
                    print(f"✅ Extracted: {business_info['name']}")
                    
            except Exception as e:
                print(f"⚠️ Error processing container {i}: {e}")
                continue
        
        return businesses
        
    except Exception as e:
        print(f"Error in DOM extraction: {e}")
        return []

def parse_business_lines(lines):
    """Parse business information from text lines"""
    business_info = {
        'name': '',
        'address': '',
        'phone': '',
        'rating': '',
        'reviews': '',
        'category': 'Vehicle wrapping service',
        'website': '',
        'hours': ''
    }
    
    if not lines:
        return business_info
    
    # First line is usually the business name
    business_info['name'] = clean_business_name(lines[0])
    
    # Look through remaining lines for address and phone
    for line in lines[1:]:
        line = line.strip()
        
        # Skip common non-address/phone lines
        if any(skip in line.lower() for skip in ['rating', 'review', 'star', 'open', 'close', 'hour', 'minute', 'directions', 'website', 'call', 'vehicle wrapping', 'service']):
            continue
        
        # Check if line is an address
        if is_address_line(line):
            if not business_info['address']:  # Only take the first valid address
                business_info['address'] = clean_address_final(line)
        
        # Check if line contains a phone number
        phone_match = re.search(r'\((\d{3})\)\s*(\d{3})[-.\s]?(\d{4})', line)
        if phone_match:
            if not business_info['phone']:  # Only take the first valid phone
                business_info['phone'] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
        
        # Extract rating
        rating_match = re.search(r'(\d+\.?\d*)\s*star', line.lower())
        if rating_match and not business_info['rating']:
            business_info['rating'] = rating_match.group(1)
        
        # Extract review count
        review_match = re.search(r'\((\d+)\)', line)
        if review_match and not business_info['reviews']:
            business_info['reviews'] = review_match.group(1)
    
    return business_info

def is_address_line(line):
    """Check if a line looks like an address"""
    if len(line) < 10 or len(line) > 150:
        return False
    
    # Must contain a number
    if not re.search(r'\d', line):
        return False
    
    # Check for address patterns
    address_indicators = [
        r'\d+\s+\w+.*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Pkwy|Parkway|Circle|Cir|Court|Ct|Place|Pl)\b',
        r'\d+\s+[NSEW]\s+\w+',  # Like "123 N Main St"
        r'\d+\s+W\s+State\s+Rd',  # Like "10388 W State Rd 84"
        r'\d+.*(?:Suite|STE|#)\s*\d+',  # Suite numbers
    ]
    
    for pattern in address_indicators:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    
    return False

def clean_address_final(address):
    """Final address cleaning with precise formatting"""
    if not address:
        return ""
    
    # Remove common prefixes and suffixes
    address = re.sub(r'^(Address:|Directions to|Navigate to|Located at)\s*', '', address, flags=re.IGNORECASE)
    
    # Remove everything after certain characters
    address = re.sub(r'\s*[·•]\s*.*$', '', address)  # Remove after bullet points
    address = re.sub(r'\s*\(.*?\)', '', address)  # Remove parentheses content
    address = re.sub(r'\s*\bHours?\b.*$', '', address, flags=re.IGNORECASE)  # Remove hours info
    address = re.sub(r'\s*\bOpen\b.*$', '', address, flags=re.IGNORECASE)  # Remove open info
    address = re.sub(r'\s*\bClosed?\b.*$', '', address, flags=re.IGNORECASE)  # Remove closed info
    
    # Normalize spaces
    address = re.sub(r'\s+', ' ', address).strip()
    
    # Ensure proper formatting
    if ',' not in address and re.search(r'\d{5}', address):
        # Try to split at the zip code
        zip_match = re.search(r'(.+?)(\d{5}.*)', address)
        if zip_match:
            street_part = zip_match.group(1).strip()
            zip_part = zip_match.group(2).strip()
            address = f"{street_part}, {zip_part}"
    
    return address

def format_phone_number(phone):
    """Format phone number properly"""
    if not phone:
        return ""
    
    # Extract only digits
    digits = re.sub(r'[^\d]', '', phone)
    
    # Remove leading 1 if present and we have 11 digits
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    
    # Must have exactly 10 digits
    if len(digits) != 10:
        return ""
    
    # Format as (XXX) XXX-XXXX
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

def clean_business_name(name):
    """Clean business name"""
    if not name:
        return ""
    
    # Remove common prefixes/suffixes
    name = re.sub(r'^\d+\.\s*', '', name)  # Remove numbering
    name = re.sub(r'\s*\(.*?\)', '', name)  # Remove parentheses
    name = re.sub(r'\s*[·•]\s*.*$', '', name)  # Remove after bullet points
    
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name

def is_valid_business_name(name):
    """Check if a name looks like a valid business name"""
    if not name or len(name) < 3 or len(name) > 100:
        return False
    
    # Must contain letters
    if not re.search(r'[a-zA-Z]', name):
        return False
    
    # Skip common non-business text
    skip_patterns = [
        r'^(open|closed|hours?|rating|review|star|phone|website|directions)$',
        r'^\d+\s*(star|review)',
        r'^vehicle wrapping service$',
    ]
    
    for pattern in skip_patterns:
        if re.match(pattern, name.lower()):
            return False
    
    return True

def is_valid_address(address):
    """Check if an address looks valid"""
    if not address or len(address) < 10:
        return False
    
    # Must contain a number and street type
    if not re.search(r'\d', address):
        return False
    
    street_types = ['Street', 'St', 'Avenue', 'Ave', 'Road', 'Rd', 'Boulevard', 'Blvd', 'Drive', 'Dr', 'Lane', 'Ln', 'Way', 'Court', 'Ct', 'Place', 'Pl']
    if not any(st in address for st in street_types):
        return False
    
    return True

def final_google_maps_search(query, max_results=50):
    """Final Google Maps search with precise extraction"""
    driver = setup_final_driver()
    if not driver:
        return []
    
    try:
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"🌐 Searching: {search_url}")
        
        driver.get(search_url)
        time.sleep(8)
        
        # Wait for results
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[role="main"]'))
            )
        except TimeoutException:
            print("❌ Search results didn't load")
            return []
        
        # Scroll to load more results
        print("📜 Loading more results...")
        for i in range(15):  # More scrolling for more results
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
        
        # Extract from DOM elements (more reliable than JavaScript parsing)
        businesses = extract_from_dom_elements(driver)
        
        return businesses[:max_results]
        
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return []
    
    finally:
        driver.quit()

def test_final_scraper():
    """Test the final scraper"""
    print("🎯 Testing Final Google Maps Scraper")
    print("=" * 50)
    
    query = "car wraps in Florida"
    print(f"🔍 Searching for: {query}")
    
    results = final_google_maps_search(query, max_results=25)
    
    if results:
        print(f"✅ Found {len(results)} businesses!")
        
        for i, business in enumerate(results, 1):
            print(f"\n📍 Business {i}:")
            print(f"   Name: {business['name']}")
            print(f"   Address: {business['address']}")
            print(f"   Phone: {business['phone']}")
            if business['rating']:
                print(f"   Rating: {business['rating']}")
            if business['reviews']:
                print(f"   Reviews: {business['reviews']}")
        
        # Quality metrics
        print(f"\n📊 Quality Metrics:")
        addresses_found = len([b for b in results if b['address']])
        phones_found = len([b for b in results if b['phone']])
        names_found = len([b for b in results if b['name']])
        
        print(f"   Valid names: {names_found}/{len(results)}")
        print(f"   Valid addresses: {addresses_found}/{len(results)}")
        print(f"   Valid phones: {phones_found}/{len(results)}")
        
        # Check for specific issues mentioned by user
        print(f"\n🔍 Issue Check:")
        for business in results:
            if business['phone'] and len(business['phone']) < 10:
                print(f"   ⚠️ Short phone detected: {business['phone']} for {business['name']}")
            if business['address'] and not re.search(r'\d+.*(?:Street|St|Avenue|Ave|Road|Rd)', business['address']):
                print(f"   ⚠️ Invalid address format: {business['address']} for {business['name']}")
        
        return True
    else:
        print("❌ No results found")
        return False

if __name__ == "__main__":
    test_final_scraper()