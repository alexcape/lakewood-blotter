import json
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

URL = "https://p2c.lakewoodoh.net/dailybulletin.aspx"

def clean_address(raw_addr):
    # Removes "-BLK" so geocoders can read it (e.g., 15600-BLK Madison Ave -> 15600 Madison Ave)
    return re.sub(r'-BLK\s*', ' ', raw_addr)

def scrape_p2c():
    with sync_playwright() as p:
        # Launch a headless browser
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"Navigating to {URL}...")
        page.goto(URL, timeout=60000)
        
        # Wait for the specific data table to load on the page
        # P2C typically uses a class like 'Grid' or 'DataGrid'
        page.wait_for_selector('table', timeout=30000) 
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        incidents = []
        
        # NOTE: P2C tables are notoriously poorly formatted. 
        # These selectors target the typical table rows, but may need minor tweaking.
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for index, row in enumerate(rows):
                cols = row.find_all('td')
                
                # Check if it looks like a valid data row (requires at least a few columns)
                if len(cols) > 5:
                    try:
                        # Extract basic info based on typical P2C column orders
                        case_num = cols[0].text.strip()
                        charge = cols[3].text.strip()
                        
                        # The description column usually holds a massive block of text. 
                        # We extract it to parse out the date and address.
                        description = cols[1].text.strip()
                        
                        # Find the address (usually follows "at " and ends with "OH")
                        address_match = re.search(r'at (.*?, OH)', description)
                        raw_addr = address_match.group(1) if address_match else "Address Restricted"
                        
                        incident = {
                            "id": index,
                            "case_number": case_num,
                            "type": "Arrest" if "AR" in case_num else "Incident",
                            "charge": charge if charge else "General Incident",
                            "date_str": "See Details", # P2C embeds this dynamically
                            "raw_address": raw_addr,
                            "clean_address": clean_address(raw_addr) if raw_addr != "Address Restricted" else "",
                            "details": description,
                            "officer": cols[2].text.strip(),
                            "badge_color": "red" if "AR" in case_num else "blue"
                        }
                        
                        # Only add if it actually looks like a valid case
                        if incident["case_number"]:
                            incidents.append(incident)
                            
                    except Exception as e:
                        print(f"Skipped a row due to parsing error: {e}")
                        continue
        
        browser.close()
        
        # Save to a JSON file in the 'data' folder
        with open('data/blotter.json', 'w', encoding='utf-8') as f:
            json.dump(incidents, f, indent=4)
            
        print(f"Successfully scraped {len(incidents)} records.")

if __name__ == "__main__":
    scrape_p2c()