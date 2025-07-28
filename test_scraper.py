#!/usr/bin/env python3
"""
Test script for the International Google Maps Scraper
This script tests the scraper functionality without the Streamlit interface
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import setup_driver, search_google_maps
import pandas as pd

def test_driver_setup():
    """Test if Chrome driver can be set up properly"""
    print("🧪 Testing Chrome driver setup...")
    driver = setup_driver()
    
    if driver:
        print("✅ Chrome driver setup successful!")
        try:
            driver.get("https://www.google.com")
            print("✅ Successfully navigated to Google")
            driver.quit()
            return True
        except Exception as e:
            print(f"❌ Failed to navigate to Google: {e}")
            driver.quit()
            return False
    else:
        print("❌ Failed to setup Chrome driver")
        return False

def test_google_maps_search():
    """Test Google Maps search functionality"""
    print("\n🔍 Testing Google Maps search...")
    
    # Test with car wraps query to match user's use case
    test_query = "car wraps in Florida"
    print(f"Searching for: {test_query}")
    
    try:
        results = search_google_maps(test_query, max_results=15)
        
        if results:
            print(f"✅ Found {len(results)} results!")
            
            # Display sample results
            for i, result in enumerate(results[:5], 1):
                print(f"\n📍 Result {i}:")
                print(f"   Name: {result.get('name', 'N/A')}")
                print(f"   Rating: {result.get('rating', 'N/A')}")
                print(f"   Reviews: {result.get('reviews', 'N/A')}")
                print(f"   Category: {result.get('category', 'N/A')}")
                print(f"   Address: {result.get('address', 'N/A')}")
                print(f"   Phone: {result.get('phone', 'N/A')}")
            
            # Test address and phone extraction quality
            addresses_found = len([r for r in results if r.get('address')])
            phones_found = len([r for r in results if r.get('phone')])
            print(f"\n📊 Quality metrics:")
            print(f"   Addresses found: {addresses_found}/{len(results)}")
            print(f"   Phone numbers found: {phones_found}/{len(results)}")
            
            return True
        else:
            print("❌ No results found")
            return False
            
    except Exception as e:
        print(f"❌ Error during search: {e}")
        return False

def main():
    """Main test function"""
    print("🌍 International Google Maps Scraper - Test Suite")
    print("=" * 60)
    
    # Test 1: Driver setup
    driver_ok = test_driver_setup()
    
    if driver_ok:
        # Test 2: Google Maps search
        search_ok = test_google_maps_search()
        
        if search_ok:
            print("\n🎉 All tests passed! The scraper is working correctly.")
            print("\nYou can now run the full application with:")
            print("streamlit run app.py")
        else:
            print("\n⚠️ Search test failed. Check your internet connection and Google Maps access.")
    else:
        print("\n❌ Driver setup failed. Please check Chrome/Chromium installation.")
        print("\nTroubleshooting tips:")
        print("1. Install Chrome: sudo apt install google-chrome-stable")
        print("2. Or install Chromium: sudo apt install chromium-browser")
        print("3. Make sure the browser is accessible in PATH")

if __name__ == "__main__":
    main()