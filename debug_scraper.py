#!/usr/bin/env python3
"""
Debug version of the scraper to troubleshoot issues
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
from bs4 import BeautifulSoup
import time
import re

def setup_debug_driver():
    """Setup Chrome driver for debugging"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=en-US")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"❌ Failed to setup Chrome driver: {e}")
        return None

def debug_google_maps_search():
    """Debug Google Maps search"""
    print("🔍 Debug: Starting Google Maps search...")
    
    driver = setup_debug_driver()
    if not driver:
        return
    
    try:
        query = "car wraps in Florida"
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        print(f"🌐 URL: {search_url}")
        
        driver.get(search_url)
        print("✅ Page loaded")
        
        # Wait and check page title
        time.sleep(5)
        print(f"📄 Page title: {driver.title}")
        
        # Check if we're on the right page
        current_url = driver.current_url
        print(f"🔗 Current URL: {current_url}")
        
        # Look for common elements
        print("\n🔍 Looking for page elements...")
        
        # Check for main container
        try:
            main = driver.find_element(By.CSS_SELECTOR, '[role="main"]')
            print("✅ Found main container")
        except:
            print("❌ No main container found")
        
        # Check for search results
        selectors_to_check = [
            '.hfpxzc',
            '[data-result-index]',
            '[role="article"]',
            '.Nv2PK',
            '.m6QErb',
            '[role="feed"]'
        ]
        
        for selector in selectors_to_check:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            print(f"   {selector}: {len(elements)} elements")
        
        # Get page source and check content
        page_source = driver.page_source
        print(f"\n📄 Page source length: {len(page_source)} characters")
        
        # Save page source for inspection
        with open('debug_page_source.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print("💾 Page source saved to debug_page_source.html")
        
        # Check for specific text patterns
        if "No results found" in page_source:
            print("❌ Page contains 'No results found'")
        elif "results" in page_source.lower():
            print("✅ Page contains 'results' text")
        
        # Try to find any business-like content
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Look for text that might be business names
        all_text = soup.get_text()
        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
        
        print(f"\n📝 Found {len(lines)} non-empty text lines")
        
        # Look for lines that might be business names
        potential_businesses = []
        for line in lines:
            if len(line) > 5 and len(line) < 100:
                # Check if it contains words that might be business names
                if any(word in line.lower() for word in ['wrap', 'vinyl', 'graphics', 'design', 'auto']):
                    potential_businesses.append(line)
        
        print(f"🏢 Found {len(potential_businesses)} potential business-related lines:")
        for i, business in enumerate(potential_businesses[:10]):
            print(f"   {i+1}. {business}")
        
        # Check if we need to accept cookies or handle popups
        cookie_selectors = [
            'button[aria-label*="Accept"]',
            'button[aria-label*="agree"]',
            '[aria-label*="cookie"]',
            '.VfPpkd-LgbsSe[data-value="Accept all"]'
        ]
        
        for selector in cookie_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"🍪 Found cookie consent: {selector}")
                try:
                    elements[0].click()
                    print("✅ Clicked cookie consent")
                    time.sleep(2)
                    break
                except:
                    print("❌ Failed to click cookie consent")
        
    except Exception as e:
        print(f"❌ Error during debug: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_google_maps_search()