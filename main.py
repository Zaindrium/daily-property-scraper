import os
import time
import gspread
from flask import Flask, jsonify
from oauth2client.service_account import ServiceAccountCredentials
from scraper import get_page_number_for_property24
from gspread.utils import rowcol_to_a1

app = Flask(__name__)

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

# Configuration
SHEET_NAME = 'Your Google Sheet Name Here'
WORKSHEET_NAME = 'Property 24'

def run_scraper():
    try:
        spreadsheet = client.open(SHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        records = worksheet.get_all_records()
        headers = worksheet.row_values(1)

        listing_id_idx = headers.index("Listing ID")
        suburb_idx = headers.index("Suburb")
        page_number_idx = headers.index("Page Number")

        updates = []

        for row_num, record in enumerate(records, start=2):  # Start at row 2 to skip header
            listing_id = str(record["Listing ID"]).strip()
            suburb = str(record["Suburb"]).strip()

            if not listing_id or not suburb:
                continue

            result = get_page_number_for_property24(listing_id, suburb)

            cell_address = rowcol_to_a1(row_num, page_number_idx + 1)
            updates.append({
                'range': f"{WORKSHEET_NAME}!{cell_address}",
                'values': [[str(result)]]
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
