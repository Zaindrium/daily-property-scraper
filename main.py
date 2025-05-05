import os
import time
import json
import gspread
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import rowcol_to_a1

app = Flask(__name__)

# Google Sheets setup using environment variable
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.environ.get("GOOGLE_CREDENTIALS")
if not creds_json:
    raise ValueError("GOOGLE_CREDENTIALS environment variable not set")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Configuration
SHEET_NAME = 'Listing Tracker'
WORKSHEET_NAME = 'Property 24'
BASE_URL = "https://www.property24.com/for-sale/eastern-cape/port-elizabeth/1/p{}?sp=nr"

def find_listing_page(listing_id):
    for page in range(1, 50):  # check first 50 pages
        url = BASE_URL.format(page)
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Failed to load page {page}: Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup.find_all("a", href=True):
                if listing_id in tag["href"]:
                    return page
        except Exception as e:
            print(f"Error on page {page}: {e}")
        time.sleep(1)
    return "Not Found"

def run_scraper():
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)

        listing_id_idx = headers.index("Listing ID")
        page_number_idx = headers.index("Page Number")

        updates = []

        for row_num, record in enumerate(records, start=2):  # Start at row 2 to skip header
            listing_id = str(record["Listing ID"]).strip()

            if not listing_id:
                continue

            page_number = find_listing_page(listing_id)
            print(f"Listing {listing_id} found on page: {page_number}")
            cell_address = rowcol_to_a1(row_num, page_number_idx + 1)
            updates.append({
                'range': f"{WORKSHEET_NAME}!{cell_address}",
                'values': [[str(page_number)]]
            })

        # Batch update
        if updates:
            worksheet.spreadsheet.batch_update({
                'valueInputOption': 'RAW',
                'data': updates
            })

        print("✅ Scraper completed and data updated.")
        return True

    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        return False

@app.route('/trigger', methods=['GET'])
def trigger_scraper():
    success = run_scraper()
    return jsonify({"status": "success" if success else "error"})

if __name__ == '__main__':
    app.run(debug=True)
