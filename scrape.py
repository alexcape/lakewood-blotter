import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://p2c.lakewoodoh.net/dailybulletin.aspx"

def clean_address(raw_addr):
    return re.sub(r'-BLK\s*', ' ', raw_addr)

def scrape_p2c():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"Navigating to {URL}...")
        page.goto(URL, timeout=60000)
        page.wait_for_selector('table', timeout=30000) 
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        incidents = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for index, row in enumerate(rows):
                cols = row.find_all('td')
                
                if len(cols) > 5:
                    try:
                        raw_case_text = cols[0].text.strip()
                        
                        # Fix #1 & #2: Look for 'LW' or 'AR' followed by numbers
                        case_match = re.search(r'(LW|AR)\s*\d+', raw_case_text)
                        if not case_match:
                            continue
                            
                        case_num = case_match.group(0)
                        charge = cols[3].text.strip()
                        description = cols[1].text.strip()
                        
# Fix #3: Clean up the description
                        description = re.sub(r'^(?:Society\s+)?VICTIM of\s+', '', description, flags=re.IGNORECASE)
                        
                        # Extract the Date and Time (P2C usually formats it like "on 22:44, 7/7/2026" or "between... and 01:10, 7/7/2026")
                        date_match = re.search(r'(\d{1,2}:\d{2}),?\s*(\d{1,2}/\d{1,2}/\d{4})', description)
                        if date_match:
                            time_str = date_match.group(1)
                            date_str = date_match.group(2)
                            # Combine into a sortable string (e.g., "7/7/2026 22:44")
                            raw_datetime = f"{date_str} {time_str}"
                        else:
                            raw_datetime = ""

                        address_match = re.search(r'at (.*?, OH)', description)
                        raw_addr = address_match.group(1) if address_match else "Address Restricted"
                        
                        incident = {
                            "id": index,
                            "case_number": case_num,
                            "type": "Arrest" if "AR" in case_num else "Incident",
                            "charge": charge if charge else "General Incident",
                            "raw_datetime": raw_datetime, 
                            "raw_address": raw_addr,
                            "clean_address": clean_address(raw_addr) if raw_addr != "Address Restricted" else "",
                            "details": description,
                            "officer": cols[2].text.strip(),
                            "badge_color": "red" if "AR" in case_num else "blue"
                        }
                        
                        incidents.append(incident)
                            
                    except Exception as e:
                        print(f"Skipped a row due to parsing error: {e}")
                        continue
        
        browser.close()
        
        with open('data/blotter.json', 'w', encoding='utf-8') as f:
            json.dump(incidents, f, indent=4)
            
        print(f"Successfully scraped {len(incidents)} records.")

if __name__ == "__main__":
    scrape_p2c()
