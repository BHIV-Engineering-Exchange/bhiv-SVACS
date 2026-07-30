import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base URL for Wikimedia Commons API
WIKI_API_URL = "https://commons.wikimedia.org/w/api.php"

# Map exactly the 35 classes to their respective Wikimedia Categories
CATEGORIES_MAP = {
    "Cruise Ship": "Category:Cruise_ships",
    "Passenger Ferry": "Category:Ferries",
    "Container Ship": "Category:Container_ships",
    "Bulk Carrier": "Category:Bulk_carriers",
    "Oil Tanker": "Category:Oil_tankers",
    "Chemical Tanker": "Category:Chemical_tankers",
    "LNG Carrier": "Category:LNG_tankers",
    "LPG Carrier": "Category:LPG_tankers",
    "Fishing Vessel": "Category:Fishing_vessels",
    "Fishing Trawler": "Category:Trawlers",
    "Tug Boat": "Category:Tugboats",
    "Pilot Boat": "Category:Pilot_boats",
    "Patrol Boat": "Category:Patrol_boats",
    "Naval Vessel": "Category:Naval_ships",
    "Coast Guard Vessel": "Category:Coast_guard_vessels",
    "Research Vessel": "Category:Research_vessels",
    "Offshore Support Vessel": "Category:Offshore_support_vessels",
    "Platform Supply Vessel": "Category:Platform_supply_vessels",
    "Anchor Handling Tug Supply": "Category:Anchor_handling_tug_supply_vessels",
    "Drill Ship": "Category:Drillships",
    "Jack-up Rig": "Category:Jackup_rigs",
    "Dredger": "Category:Dredgers",
    "Cable Layer": "Category:Cable_ships",
    "Fire Boat": "Category:Fireboats",
    "Landing Craft": "Category:Landing_craft",
    "Ro-Ro Ship": "Category:Roll-on/roll-off_ships",
    "RoPax Ferry": "Category:Ro-pax_ferries",
    "Vehicle Carrier": "Category:Vehicle_carriers",
    "General Cargo Ship": "Category:General_cargo_ships",
    "Mega Yacht": "Category:Motor_yachts",
    "Icebreaker": "Category:Icebreakers",
    "Barge": "Category:Barges",
    "Hovercraft": "Category:Hovercraft",
    "Rescue Vessel": "Category:Rescue_vessels",
    "Training Ship": "Category:Training_ships"
}

HEADERS = {
    "User-Agent": "SVACS-Vessel-Classifier/1.0 (https://github.com/svacs; dataset-engineering)"
}

def get_images_in_category(category_name, max_images=2000):
    images = []
    gcmcontinue = None

    while len(images) < max_images:
        params = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": category_name,
            "gcmnamespace": 6,  # 6 corresponds to files/images
            "gcmlimit": 500,    # Max allowed per request
            "prop": "imageinfo",
            "iiprop": "url",
        }
        if gcmcontinue:
            params["gcmcontinue"] = gcmcontinue

        try:
            response = requests.get(WIKI_API_URL, params=params, headers=HEADERS)
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "imageinfo" in page_info:
                    url = page_info["imageinfo"][0]["url"]
                    if url.lower().endswith(('.jpg', '.jpeg', '.png')):
                        images.append(url)
            
            if "continue" in data and "gcmcontinue" in data["continue"]:
                gcmcontinue = data["continue"]["gcmcontinue"]
                time.sleep(1) # Rate limiting respect
            else:
                break
                
        except Exception as e:
            logging.error(f"Error fetching category {category_name}: {str(e)}")
            break
            
    return images[:max_images]

def download_image(url, save_dir, filename):
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=10)
        if response.status_code == 200:
            file_path = os.path.join(save_dir, filename)
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        logging.error(f"Failed to download {url}: {str(e)}")
    return False

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset", "classifier"))
    os.makedirs(base_dir, exist_ok=True)
    
    total_downloaded = 0
    target_per_class = 2000 # Configurable limit

    for vessel_class, wiki_category in CATEGORIES_MAP.items():
        class_dir = os.path.join(base_dir, vessel_class)
        os.makedirs(class_dir, exist_ok=True)
        
        logging.info(f"Fetching URLs for {vessel_class} from {wiki_category}...")
        image_urls = get_images_in_category(wiki_category, max_images=target_per_class)
        logging.info(f"Found {len(image_urls)} images for {vessel_class}. Starting download...")
        
        count = 0
        for i, url in enumerate(image_urls):
            filename = f"{vessel_class.replace(' ', '_')}_{i:05d}.jpg"
            if os.path.exists(os.path.join(class_dir, filename)):
                continue # Skip existing
                
            if download_image(url, class_dir, filename):
                count += 1
                total_downloaded += 1
                
            if count % 100 == 0 and count > 0:
                logging.info(f"Downloaded {count} / {len(image_urls)} for {vessel_class}...")
                
            time.sleep(0.1) # Gentle rate limiting
            
        logging.info(f"Completed {vessel_class}: downloaded {count} new images.")

    logging.info(f"Scraping complete! Total new images downloaded: {total_downloaded}")

if __name__ == "__main__":
    main()
