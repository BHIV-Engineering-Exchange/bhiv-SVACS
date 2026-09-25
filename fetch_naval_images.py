"""
fetch_naval_images.py — Sources verified images for the 11 Indian Naval
vessel classes/ships from Wikimedia Commons, with a provenance manifest.

This is a fresh, standalone script — NOT a modification of the earlier
scrape_wikimedia.py, which had an unresolved bug returning 0 results even
when its underlying API logic was manually verified to work. This script
uses that same verified two-step (search -> imageinfo) approach directly,
kept deliberately simple to avoid inheriting the earlier bug.

Usage:
    python fetch_naval_images.py

Output:
    maritime_knowledge/images/<vessel_id>/img_1.jpg, img_2.jpg, ...
    maritime_knowledge/images/PROVENANCE_MANIFEST.json
"""

import hashlib
import json
import os
import time

import requests

WIKI_API_URL = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "SVACS-Naval-Knowledge-Pack/1.0 (internal dataset curation)"}
OUTPUT_DIR = "maritime_knowledge/images"
IMAGES_PER_CLASS = 5

# vessel_id must match indian_naval_knowledge_pack.json's vessel_id field
SEARCH_TERMS = {
    "IN-KOLKATA": "INS Kolkata destroyer",
    "IN-VISAKHAPATNAM": "INS Visakhapatnam destroyer",
    "IN-TALWAR": "INS Talwar frigate",
    "IN-DELHI": "INS Delhi destroyer India",
    "IN-SHIVALIK": "INS Shivalik frigate",
    "IN-NILGIRI": "INS Nilgiri frigate",
    "IN-KAMORTA": "INS Kamorta corvette",
    "IN-VIKRANT": "INS Vikrant aircraft carrier",
    "IN-VIKRAMADITYA": "INS Vikramaditya aircraft carrier",
    "IN-ARIHANT": "INS Arihant submarine",
    "IN-KALVARI": "INS Kalvari submarine",
}


def search_and_get_images(term, limit=10, max_retries=4):
    """Single combined request: search + imageinfo together, avoiding the
    separate title-matching round-trip that silently dropped results
    when tried as two steps."""
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": term,
        "gsrnamespace": 6, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
    }

    for attempt in range(max_retries):
        r = requests.get(WIKI_API_URL, params=params, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  Rate limited (429) — waiting {wait}s before retry ({attempt + 1}/{max_retries})...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            info = page.get("imageinfo")
            if not info:
                continue
            url = info[0].get("url", "")
            if not url.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            meta = info[0].get("extmetadata", {})
            license_name = meta.get("LicenseShortName", {}).get("value", "Unknown")
            artist = meta.get("Artist", {}).get("value", "Unknown")
            results.append({
                "title": page.get("title"),
                "url": url,
                "license": license_name,
                "artist": artist,
            })
        return results

    print(f"  Gave up after {max_retries} retries due to repeated rate limiting.")
    return []


def download(url, dest_path):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(r.content)
    return hashlib.sha256(r.content).hexdigest()


def main():
    manifest = []
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for vessel_id, term in SEARCH_TERMS.items():
        print(f"[{vessel_id}] Searching: '{term}' ...")
        infos = search_and_get_images(term, limit=IMAGES_PER_CLASS * 2)[:IMAGES_PER_CLASS]

        if not infos:
            print(f"  !! No usable images found for {vessel_id} — flagging as gap")
            manifest.append({"vessel_id": vessel_id, "search_term": term, "images": [], "status": "GAP — no images found"})
            time.sleep(3)
            continue

        class_dir = os.path.join(OUTPUT_DIR, vessel_id)
        os.makedirs(class_dir, exist_ok=True)

        vessel_entry = {"vessel_id": vessel_id, "search_term": term, "images": [], "status": "OK"}
        for i, info in enumerate(infos, start=1):
            ext = os.path.splitext(info["url"])[1] or ".jpg"
            dest = os.path.join(class_dir, f"img_{i}{ext}")
            try:
                sha256 = download(info["url"], dest)
                print(f"  Saved img_{i}{ext} — license={info['license']}")
                vessel_entry["images"].append({
                    "file": dest.replace("\\", "/"),
                    "source_title": info["title"],
                    "source_url": info["url"],
                    "license": info["license"],
                    "artist": info["artist"],
                    "sha256": sha256,
                })
            except Exception as e:
                print(f"  FAILED to download {info['url']}: {e}")
            time.sleep(0.5)

        manifest.append(vessel_entry)
        time.sleep(3)

    manifest_path = os.path.join(OUTPUT_DIR, "PROVENANCE_MANIFEST.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    total_images = sum(len(v["images"]) for v in manifest)
    gaps = [v["vessel_id"] for v in manifest if v["status"] != "OK"]
    print(f"\nDone. {total_images} images downloaded across {len(manifest)} classes.")
    if gaps:
        print(f"Gaps (no images found): {gaps}")
    print(f"Provenance manifest written to: {manifest_path}")


if __name__ == "__main__":
    main()
