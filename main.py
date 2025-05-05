from flask import Flask
import gspread
from gspread.utils import rowcol_to_a1
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json

app = Flask(__name__)

def run_scraper():
    # Load service account from environment variable
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = json.loads(os.environ['GSPREAD_KEY'])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # Open the correct sheet and worksheet
    spreadsheet = client.open('Paginator')
    worksheet = spreadsheet.worksheet('Private Property')

    # Read data
    data = worksheet.get_all_values()
    headers = data[0]
    rows = data[1:]

    root_url_idx = headers.index("Root URL")
    listing_id_idx = headers.index("Listing ID")

    # Ensure a "Page Number" column exists
    if "Page Number" not in headers:
        worksheet.update_cell(1, len(headers) + 1, "Page Number")
        page_number_idx = len(headers)
    else:
        page_number_idx = headers.index("Page Number")

    from collections import defaultdict
    grouped_listings = defaultdict(list)
    for row in rows:
        root_url = row[root_url_idx].strip()
        listing_id = row[listing_id_idx].strip()
        if root_url and listing_id:
            grouped_listings[root_url].append(listing_id)

    def get_listing_pages(url, listing_ids, max_pages=50):
        found = {}
        try:
            response = requests.get(f"{url}?page=1", timeout=10)
            if response.status_code != 200:
                return {lid: "Invalid URL or 404" for lid in listing_ids}
        except:
            return {lid: "Invalid URL format" for lid in listing_ids}

        for page in range(1, max_pages + 1):
            full_url = f"{url}?page={page}"
            try:
                res = requests.get(full_url, timeout=10)
                if res.status_code != 200:
                    break

                soup = BeautifulSoup(res.text, 'html.parser')
                html_text = soup.prettify()

                for lid in listing_ids:
                    if lid in found:
                        continue
                    if re.search(re.escape(lid), html_text, re.IGNORECASE):
                        found[lid] = page

                if all(lid in found for lid in listing_ids):
                    break
            except Exception as e:
                return {lid: f"Error: {str(e)}" for lid in listing_ids}

        for lid in listing_ids:
            if lid not in found:
                found[lid] = "Not Found"
        return found

    # Build lookup to update correct rows
    listing_to_row = {}
    for idx, row in enumerate(rows):
        lid = row[listing_id_idx].strip()
        if lid:
            listing_to_row[lid] = idx + 2

    # Process each group
    for root_url, listing_ids in grouped_listings.items():
        results = get_listing_pages(root_url, listing_ids)
        from gspread.utils import rowcol_to_a1

# Collect all cell updates
updates = []

for lid, result in results.items():
    row_num = listing_to_row.get(lid)
    if row_num:
        cell_label = rowcol_to_a1(row_num, page_number_idx + 1)
        updates.append({
            'range': cell_label,
            'values': [[str(result)]]
        })

# Perform one batch update instead of one-by-one writes
if updates:
    worksheet.batch_update([
        {
            "range": update['range'],
            "majorDimension": "ROWS",
            "values": update['values']
        } for update in updates
    ])

    print("✅ Scraper completed.")

@app.route('/')
def trigger_scraper():
    run_scraper()
    return "✅ Scraper completed successfully"

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Use Render's assigned port
    app.run(host='0.0.0.0', port=port)
