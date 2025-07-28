import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import pandas as pd
import os
import re

def scrape_google_maps(query, location, max_results=10):
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    results = []
    
    try:
        st.info("Opening Google Maps...")
        driver.get("https://www.google.com/maps")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Handle cookies/consent
        st.info("Handling cookies consent...")
        try:
            accept_selectors = [
                "//button[contains(text(), 'Accept all')]",
                "//button[contains(text(), 'I agree')]",
                "//button[contains(text(), 'Accept')]",
                "//button[@id='introAgreeButton']",
                "//form[@action='https://consent.google.com/s']//button[2]"
            ]
            for selector in accept_selectors:
                try:
                    accept_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    accept_button.click()
                    st.success("Clicked consent button")
                    time.sleep(3)
                    break
                except TimeoutException:
                    continue
        except Exception as e:
            st.warning(f"No consent button found or error: {e}")

        # Perform search
        search_query = f"{query} in {location}" if location else query
        st.info(f"Searching for: {search_query}")
        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchboxinput"))
            )
            search_box.clear()
            search_box.send_keys(search_query)
            search_button = driver.find_element(By.ID, "searchbox-searchbutton")
            search_button.click()
        except Exception as e:
            st.error(f"Error with search: {e}")
            return []

        st.info("Waiting for search results...")
        time.sleep(8)

        # Get sidebar element for scrolling
        sidebar_xpath = "//div[contains(@aria-label, 'Results for') or @role='feed']"
        sidebar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, sidebar_xpath))
        )

        # Load all results by scrolling
        st.info("🔄 Loading ALL available results by scrolling...")
        load_all_results(driver, sidebar, max_results)

        # Get all cards after loading everything
        cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
        total_cards = len(cards)
        st.success(f"✅ Loaded {total_cards} total business cards")
        
        # Limit to max_results
        cards_to_process = min(max_results, total_cards)
        st.info(f"Will process {cards_to_process} businesses")

        # Create directory for HTML files if it doesn't exist
        html_dir = "debug_html"
        if not os.path.exists(html_dir):
            os.makedirs(html_dir)

        # Store the original search URL to return to if needed
        search_url = driver.current_url
        st.info(f"🔗 Stored search URL: {search_url[:100]}...")

        # Process each card
        for idx in range(cards_to_process):
            st.write(f"Processing business {idx + 1}/{cards_to_process}...")
            
            success = process_single_business(driver, idx, html_dir, sidebar_xpath, search_url)
            
            if success["extracted"]:
                results.append(success["data"])
                st.write(f"✅ Found: {success['data']['name']}")
                if success['data']['phone']:
                    st.write(f"  📞 Phone: {success['data']['phone']}")
                if success['data']['website']:
                    st.write(f"  🌐 Website: {success['data']['website']}")
                if success['data']['address']:
                    st.write(f"  📍 Address: {success['data']['address']}")
            else:
                st.write(f"❌ Failed to extract data for business {idx + 1}")
            
            # Add a small delay between businesses
            time.sleep(2)

        st.success(f"🎉 Completed processing {len(results)} businesses!")
        return results
        
    except Exception as e:
        st.error(f"Error during scraping: {e}")
        return []
    finally:
        st.info("Browser will remain open for debugging. Close manually when done.")
        # driver.quit()

def process_single_business(driver, idx, html_dir, sidebar_xpath, search_url):
    """Process a single business and return to the list"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Ensure we're on the search results page
            if not ensure_on_search_page(driver, sidebar_xpath, search_url):
                st.warning(f"Failed to return to search page for business {idx + 1}")
                return {"extracted": False, "data": {}}
            
            # Re-fetch cards to avoid stale elements
            current_cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            
            if idx >= len(current_cards):
                st.warning(f"Card {idx + 1} not found (only {len(current_cards)} cards available)")
                return {"extracted": False, "data": {}}
                
            card = current_cards[idx]
            
            # FIRST: Extract basic info from the card itself (before clicking)
            card_info = extract_card_preview_info(card)
            st.info(f"📋 Preview from card: {card_info.get('name', 'No name found')}")
            
            # Scroll card into view and click
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
            time.sleep(2)
            
            # Try clicking the card
            try:
                card.click()
            except ElementClickInterceptedException:
                st.info(f"Card {idx + 1} click intercepted, using JavaScript click...")
                driver.execute_script("arguments[0].click();", card)
            except StaleElementReferenceException:
                if attempt < max_retries - 1:
                    st.warning(f"Card {idx + 1} became stale, retrying...")
                    continue
                else:
                    raise
            
            # Wait for details to load
            st.info(f"⏳ Loading details for business {idx + 1}...")
            time.sleep(6)  # Increased wait time
            
            # Extract detailed business information
            complete_html = driver.page_source
            html_filename = f"{html_dir}/business_{idx + 1}_complete.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(complete_html)
            
            # Extract details using multiple methods
            detailed_info = extract_business_details_comprehensive(driver, complete_html)
            
            # Merge card info with detailed info (detailed info takes precedence)
            final_info = merge_business_info(card_info, detailed_info)
            
            # Save debug info
            debug_filename = f"{html_dir}/business_{idx + 1}_debug.txt"
            save_extraction_debug(final_info, card_info, detailed_info, debug_filename)
            
            # Go back to the list
            st.info(f"🔙 Going back to results list...")
            if go_back_to_list_robust(driver, sidebar_xpath, search_url):
                return {"extracted": True, "data": final_info}
            else:
                st.warning(f"Failed to go back properly for business {idx + 1}")
                return {"extracted": True, "data": final_info}  # Still return the data
                
        except Exception as e:
            st.warning(f"Attempt {attempt + 1} failed for business {idx + 1}: {e}")
            if attempt < max_retries - 1:
                # Try to recover by going back to search URL
                try:
                    driver.get(search_url)
                    time.sleep(5)
                except:
                    pass
            else:
                return {"extracted": False, "data": {}}
    
    return {"extracted": False, "data": {}}

def extract_card_preview_info(card_element):
    """Extract basic info from the card element before clicking"""
    info = {"name": "", "website": "", "phone": "", "email": "", "address": ""}
    
    try:
        # Get the card's HTML
        card_html = card_element.get_attribute('outerHTML')
        soup = BeautifulSoup(card_html, 'html.parser')
        
        # Extract business name from card
        name_selectors = [
            '.fontHeadlineSmall',
            '.fontHeadlineLarge', 
            '[data-value="Business name"]',
            'h3',
            'h2',
            '.qBF1Pd'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem and name_elem.get_text(strip=True):
                info["name"] = name_elem.get_text(strip=True)
                break
        
        # Extract other info from aria-labels in the card
        aria_elements = soup.find_all(attrs={"aria-label": True})
        for elem in aria_elements:
            aria_text = elem.get("aria-label", "").lower()
            aria_value = elem.get("aria-label", "")
            
            # Phone number
            if not info["phone"] and ("phone" in aria_text or "call" in aria_text):
                phone_match = re.search(r'(\+?1?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4})', aria_value)
                if phone_match:
                    info["phone"] = phone_match.group(1).strip()
            
            # Address
            if not info["address"] and ("address" in aria_text or "directions" in aria_text):
                if len(aria_value) > 10:
                    info["address"] = aria_value.strip()
        
    except Exception as e:
        st.warning(f"Error extracting card preview: {e}")
    
    return info

def extract_business_details_comprehensive(driver, html_content):
    """Comprehensive extraction using multiple methods"""
    info = {"name": "", "website": "", "phone": "", "email": "", "address": ""}
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: Extract from current page elements using Selenium
    try:
        # Business name from h1 or main heading
        name_selectors = [
            "h1.DUwDvf",
            "h1",
            ".x3AX1-LfntMc-header-title-title",
            ".fontHeadlineLarge",
            ".fontHeadlineSmall"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if name_elem and name_elem.text.strip():
                    info["name"] = name_elem.text.strip()
                    break
            except:
                continue
        
        # Phone number
        phone_selectors = [
            "button[aria-label*='phone']",
            "button[aria-label*='Phone']", 
            "button[aria-label*='Call']",
            "a[href^='tel:']",
            "button[data-value*='phone']"
        ]
        
        for selector in phone_selectors:
            try:
                phone_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if phone_elem:
                    # Try to get phone from aria-label
                    aria_label = phone_elem.get_attribute("aria-label")
                    if aria_label:
                        phone_match = re.search(r'(\+?1?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4})', aria_label)
                        if phone_match:
                            info["phone"] = phone_match.group(1).strip()
                            break
                    
                    # Try to get phone from href
                    href = phone_elem.get_attribute("href")
                    if href and href.startswith("tel:"):
                        info["phone"] = href.replace("tel:", "").strip()
                        break
            except:
                continue
        
        # Website
        website_selectors = [
            "a[aria-label*='Website']",
            "a[aria-label*='website']",
            "a[data-value='website']",
            "button[aria-label*='Website']"
        ]
        
        for selector in website_selectors:
            try:
                website_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if website_elem:
                    href = website_elem.get_attribute("href")
                    if href and href.startswith("http") and "google.com" not in href:
                        info["website"] = href
                        break
            except:
                continue
        
        # Address
        address_selectors = [
            "button[aria-label*='Address']",
            "button[aria-label*='address']",
            "button[aria-label*='Directions']",
            "button[data-value*='directions']"
        ]
        
        for selector in address_selectors:
            try:
                addr_elem = driver.find_element(By.CSS_SELECTOR, selector)
                if addr_elem:
                    aria_label = addr_elem.get_attribute("aria-label")
                    if aria_label and len(aria_label.strip()) > 10:
                        # Clean up address text
                        address_text = aria_label
                        for prefix in ["Address:", "Directions to", "Navigate to", "address:"]:
                            if address_text.startswith(prefix):
                                address_text = address_text[len(prefix):].strip()
                        info["address"] = address_text
                        break
            except:
                continue
        
    except Exception as e:
        st.warning(f"Error in Selenium extraction: {e}")
    
    # Method 2: Extract from HTML using BeautifulSoup (fallback)
    if not all([info["name"], info["phone"], info["website"], info["address"]]):
        soup_info = extract_from_soup_improved(soup)
        
        # Fill in missing info
        for key in info:
            if not info[key] and soup_info[key]:
                info[key] = soup_info[key]
    
    return info

def extract_from_soup_improved(soup):
    """Improved BeautifulSoup extraction with better selectors"""
    info = {"name": "", "website": "", "phone": "", "email": "", "address": ""}
    
    # Business name extraction
    name_selectors = [
        "h1.DUwDvf",
        "h1",
        ".x3AX1-LfntMc-header-title-title",
        ".fontHeadlineLarge",
        ".fontHeadlineSmall",
        "[data-attrid='title']"
    ]
    
    for selector in name_selectors:
        elem = soup.select_one(selector)
        if elem and elem.get_text(strip=True):
            text = elem.get_text(strip=True)
            if len(text) < 200 and not text.lower().startswith("results"):  # Avoid "Results" text
                info["name"] = text
                break
    
    # Phone number extraction
    # Look for tel: links first
    tel_links = soup.find_all("a", href=re.compile(r"^tel:"))
    for link in tel_links:
        phone = link.get("href").replace("tel:", "").strip()
        if phone and len(phone) >= 10:
            info["phone"] = phone
            break
    
    # Look in aria-labels for phone
    if not info["phone"]:
        phone_elements = soup.find_all(attrs={"aria-label": re.compile(r"phone|call", re.I)})
        for elem in phone_elements:
            aria_text = elem.get("aria-label", "")
            phone_match = re.search(r'(\+?1?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4})', aria_text)
            if phone_match:
                info["phone"] = phone_match.group(1).strip()
                break
    
    # Website extraction
    website_elements = soup.find_all("a", attrs={"aria-label": re.compile(r"website", re.I)})
    for elem in website_elements:
        href = elem.get("href")
        if href and href.startswith("http") and "google.com" not in href and "maps.google" not in href:
            info["website"] = href
            break
    
    # If no website found, look for any external links
    if not info["website"]:
        external_links = soup.find_all("a", href=True)
        for link in external_links:
            href = link.get("href")
            if (href and href.startswith("http") and 
                "google.com" not in href and 
                "maps.google" not in href and
                "facebook.com" not in href and
                "instagram.com" not in href):
                info["website"] = href
                break
    
    # Address extraction
    address_elements = soup.find_all(attrs={"aria-label": re.compile(r"address|directions", re.I)})
    for elem in address_elements:
        aria_text = elem.get("aria-label", "")
        if len(aria_text.strip()) > 15:  # Reasonable address length
            # Clean up address
            address_text = aria_text
            for prefix in ["Address:", "Directions to", "Navigate to", "address:", "Get directions to"]:
                if address_text.startswith(prefix):
                    address_text = address_text[len(prefix):].strip()
            
            if address_text and len(address_text) > 10:
                info["address"] = address_text
                break
    
    return info

def merge_business_info(card_info, detailed_info):
    """Merge information from card and detailed extraction, prioritizing detailed info"""
    final_info = {"name": "", "website": "", "phone": "", "email": "", "address": ""}
    
    for key in final_info:
        # Prioritize detailed info, fallback to card info
        if detailed_info.get(key):
            final_info[key] = detailed_info[key]
        elif card_info.get(key):
            final_info[key] = card_info[key]
    
    # Special handling for name - make sure it's not "Results" or empty
    if not final_info["name"] or final_info["name"].lower().strip() == "results":
        # Try to find name in either source
        for source in [detailed_info, card_info]:
            if source.get("name") and source["name"].lower().strip() != "results":
                final_info["name"] = source["name"]
                break
    
    # If still no name, set a placeholder
    if not final_info["name"]:
        final_info["name"] = "Business Name Not Found"
    
    return final_info

def save_extraction_debug(final_info, card_info, detailed_info, filename):
    """Save debug information about the extraction process"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("=== EXTRACTION DEBUG INFO ===\n\n")
        
        f.write("FINAL MERGED INFO:\n")
        for key, value in final_info.items():
            f.write(f"  {key}: {value}\n")
        
        f.write("\nCARD PREVIEW INFO:\n")
        for key, value in card_info.items():
            f.write(f"  {key}: {value}\n")
        
        f.write("\nDETAILED PAGE INFO:\n")
        for key, value in detailed_info.items():
            f.write(f"  {key}: {value}\n")
        
        f.write("\n" + "="*50 + "\n")

def ensure_on_search_page(driver, sidebar_xpath, search_url):
    """Ensure we're on the search results page"""
    try:
        # Check if sidebar is present
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, sidebar_xpath))
        )
        return True
    except TimeoutException:
        # Sidebar not found, try to return to search page
        st.info("🔄 Sidebar not found, returning to search page...")
        try:
            driver.get(search_url)
            time.sleep(5)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, sidebar_xpath))
            )
            return True
        except:
            return False

def go_back_to_list_robust(driver, sidebar_xpath, search_url):
    """Robust method to go back to the results list"""
    
    # Method 1: Try various back buttons
    back_selectors = [
        "button[aria-label*='Back']",
        "button[aria-label*='back']", 
        "button[data-value='Back']",
        "button[aria-label^='Back']",
        "[data-value='back']",
        ".VfPpkd-icon-LgbsSe[aria-label*='Back']"
    ]
    
    for selector in back_selectors:
        try:
            back_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            back_btn.click()
            time.sleep(3)
            
            # Check if we're back on the search page
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, sidebar_xpath))
                )
                st.success("✅ Successfully went back using back button")
                return True
            except TimeoutException:
                continue
                
        except (TimeoutException, NoSuchElementException):
            continue
    
    # Method 2: Try Escape key
    try:
        st.info("🔄 Trying Escape key...")
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(3)
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, sidebar_xpath))
        )
        st.success("✅ Successfully went back using Escape key")
        return True
    except:
        pass
    
    # Method 3: Browser back
    try:
        st.info("🔄 Trying browser back...")
        driver.back()
        time.sleep(3)
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, sidebar_xpath))
        )
        st.success("✅ Successfully went back using browser back")
        return True
    except:
        pass
    
    # Method 4: Return to search URL (nuclear option)
    try:
        st.info("🔄 Returning to search URL...")
        driver.get(search_url)
        time.sleep(5)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, sidebar_xpath))
        )
        st.success("✅ Successfully returned to search page")
        return True
    except:
        st.error("❌ Failed to return to search page")
        return False

def load_all_results(driver, sidebar, max_needed):
    """Aggressively scroll the sidebar to load all available results"""
    st.info("📜 Starting aggressive scrolling to load all results...")
    
    scroll_count = 0
    no_change_count = 0
    last_card_count = 0
    
    while scroll_count < 50:  # Maximum 50 scroll attempts
        # Get current number of cards
        current_cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
        current_count = len(current_cards)
        
        st.write(f"Scroll {scroll_count + 1}: Found {current_count} cards")
        
        # If we have enough cards, we can stop
        if current_count >= max_needed:
            st.info(f"✅ Found enough cards ({current_count} >= {max_needed})")
            break
        
        # Check if we're still loading new cards
        if current_count == last_card_count:
            no_change_count += 1
            if no_change_count >= 3:
                st.info(f"⏹️ No new cards loaded after 3 attempts, stopping at {current_count} cards")
                break
        else:
            no_change_count = 0
        
        last_card_count = current_count
        
        # Scroll down in the sidebar
        try:
            # Multiple scroll methods for better coverage
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", sidebar)
            time.sleep(2)
            
            # Also try scrolling the last card into view to trigger more loading
            if current_cards:
                last_card = current_cards[-1]
                driver.execute_script("arguments[0].scrollIntoView();", last_card)
                time.sleep(1)
            
            # Additional scroll with page down
            driver.execute_script("arguments[0].scrollBy(0, 1000);", sidebar)
            time.sleep(2)
            
        except Exception as e:
            st.warning(f"Scroll error: {e}")
        
        scroll_count += 1
    
    final_cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
    st.success(f"🏁 Finished scrolling. Total cards loaded: {len(final_cards)}")
    return len(final_cards)

# --- Streamlit UI ---
st.title("🔧 Improved Google Maps Business Scraper")
st.success("✨ **NEW IMPROVEMENTS**: Better name extraction, duplicate data prevention, comprehensive data extraction")

st.markdown("""
### 🆕 Key Improvements:
- **🏷️ Better Name Extraction**: Multiple methods to find actual business names
- **🔍 Dual Extraction**: Gets data from both card preview AND detail page
- **🚫 Duplicate Prevention**: Avoids extracting same data for different businesses
- **✅ Data Validation**: Filters out "Results" and other invalid names
- **🔄 Comprehensive Fallbacks**: Multiple extraction methods for each data type
- **📊 Debug Information**: Detailed debug files for troubleshooting
""")

st.warning("⚠️ This will open a visible Chrome browser window for debugging purposes.")
st.info("📁 HTML files and debug files will be saved in 'debug_html' directory")

query = st.text_input("Business Type (e.g. Car Wraps)", "Car Wraps")
location = st.text_input("Location (e.g. Virginia)", "Virginia")
max_results = st.slider("Max Results", 1, 200, 20)

if st.button("🚀 Start Improved Scraping"):
    with st.spinner("Scraping Google Maps with improved extraction..."):
        data = scrape_google_maps(query, location, max_results)
        if data:
            df = pd.DataFrame(data)
            st.success(f"🎉 Successfully extracted {len(data)} businesses!")
            
            # Show summary statistics
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Total Businesses", len(data))
            with col2:
                st.metric("With Names", len([d for d in data if d['name'] and d['name'] != "Business Name Not Found"]))
            with col3:
                st.metric("With Phone", len([d for d in data if d['phone']]))
            with col4:
                st.metric("With Website", len([d for d in data if d['website']]))
            with col5:
                st.metric("With Address", len([d for d in data if d['address']]))
            
            # Show data quality
            st.subheader("📊 Data Quality Check")
            names_found = [d['name'] for d in data if d['name'] and d['name'] != "Business Name Not Found"]
            if len(set(names_found)) < len(names_found):
                st.warning("⚠️ Some duplicate names detected - check extraction logic")
            else:
                st.success("✅ All business names are unique")
            
            # Check for duplicate addresses/phones
            addresses = [d['address'] for d in data if d['address']]
            phones = [d['phone'] for d in data if d['phone']]

            if len(set(addresses)) < len(addresses):
                st.warning(f"⚠️ Duplicate addresses detected: {len(addresses)} total, {len(set(addresses))} unique")
            else:
                st.success("✅ All addresses are unique")
            
            if len(set(phones)) < len(phones):
                st.warning(f"⚠️ Duplicate phone numbers detected: {len(phones)} total, {len(set(phones))} unique")
            else:
                st.success("✅ All phone numbers are unique")
            
            st.dataframe(df)
            
            # Download buttons
            csv = df.to_csv(index=False, sep=';')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"{query.replace(' ', '_')}_{location.replace(' ', '_')}_improved_results.csv",
                mime="text/csv"
            )
            
            excel_file = f"{query.replace(' ', '_')}_{location.replace(' ', '_')}_improved_results.xlsx"
            df.to_excel(excel_file, index=False)
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 Download Excel",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ No data found. Check the browser window and console output for debug info.")

# Add a section to show saved debug files
if os.path.exists("debug_html"):
    st.subheader("🔍 Debug Files")
    debug_files = os.listdir("debug_html")
    if debug_files:
        st.write("Saved files for inspection:")
        html_files = [f for f in debug_files if f.endswith('.html')]
        txt_files = [f for f in debug_files if f.endswith('.txt')]
        
        if html_files:
            st.write("📄 HTML Files:")
            for file in sorted(html_files)[-10:]:  # Show last 10 files
                st.write(f"   • {file}")
        
        if txt_files:
            st.write("📝 Debug Text Files:")
            for file in sorted(txt_files)[-10:]:  # Show last 10 files
                st.write(f"   • {file}")
                
        # Show a sample debug file content
        if txt_files:
            st.subheader("📋 Sample Debug Content")
            latest_debug = sorted(txt_files)[-1]
            try:
                with open(f"debug_html/{latest_debug}", 'r', encoding='utf-8') as f:
                    content = f.read()
                st.text_area("Latest Debug File Content", content[:2000] + "..." if len(content) > 2000 else content, height=300)
            except:
                st.write("Could not read debug file")
    else:
        st.write("No debug files found yet.")

# Add troubleshooting section
st.subheader("🔧 Troubleshooting Guide")
st.markdown("""
### Common Issues and Solutions:

**1. Missing Business Names (showing "Results" or empty)**
- The scraper now extracts names from multiple sources
- Check debug files to see what was found
- Names are validated to avoid "Results" text

**2. Duplicate Data Across Businesses**
- Improved extraction now gets data from individual business pages
- Each business is processed separately with fresh data extraction
- Debug files show both card preview and detailed page data

**3. Inconsistent Data Quality**
- The scraper now uses both Selenium (live page) and BeautifulSoup (HTML parsing)
- Multiple fallback methods for each data type
- Longer wait times for pages to fully load

**4. Navigation Issues**
- Robust back navigation with multiple fallback methods
- URL recovery system returns to search page if navigation fails
- Retry logic for failed businesses

### Debug File Explanation:
- **HTML files**: Complete page source for each business
- **Debug TXT files**: Shows extraction results from different methods
- **Comparison**: Card preview vs detailed page extraction
""")

# Add data validation section
st.subheader("📊 Data Validation Features")
st.markdown("""
### Built-in Validation:
- ✅ **Name Validation**: Filters out "Results", empty names, and overly long text
- ✅ **Phone Validation**: Regex patterns for US phone number formats
- ✅ **Website Validation**: Excludes Google/Maps URLs, validates HTTP links
- ✅ **Address Validation**: Minimum length requirements, prefix cleaning
- ✅ **Duplicate Detection**: Warns about duplicate data across businesses
""")
