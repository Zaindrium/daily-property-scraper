import os
import time
import gspread
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Sheet setup
sheet = client.open("Listing Tracker").worksheet("Property 24")
listing_ids = sheet.col_values(1)[1:]  # skip header
sheet.update_cell(1, 2, "Page Number")  # write header for page numbers

# Constants
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
        for i, lid in enumerate(listing_ids, start=2):  # start from row 2
            page_number = find_listing_page(lid)
            print(f"{lid} found on page {page_number}")
            sheet.update_cell(i, 2, str(page_number))
        return True
    except Exception as e:
        print(f"Scraper failed: {e}")
        return False

# Flask app
app = Flask(__name__)

@app.route('/trigger', methods=['GET'])
def trigger_scraper():
    success = run_scraper()
    return jsonify({"status": "success" if success else "error"})

if __name__ == '__main__':
    app.run(debug=True)
