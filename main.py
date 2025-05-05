from flask import Flask
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from scraper import get_page_number_for_property24

app = Flask(__name__)

# Root route to confirm app is running
@app.route('/')
def home():
    return "✅ Property24 Scraper is live. Visit /trigger to run the update."

# Main trigger route
@app.route('/trigger')
def run_scraper():
    try:
        # Authorize Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        # Open Google Sheet
        sheet = client.open("Listings Page Tracker").worksheet("Property 24")
        data = sheet.get_all_records()

        # Prepare header and column indexes
        header = sheet.row_values(1)
        id_index = header.index("Listing ID")
        page_index = header.index("Page No.") if "Page No." in header else len(header) + 1
        if page_index == len(header) + 1:
            sheet.update_cell(1, page_index + 1, "Page No.")

        # Collect results
        results = {}
        for i, row in enumerate(data):
            listing_id = str(row["Listing ID"]).strip()
            if not listing_id:
                continue
            page_number = get_page_number_for_property24(listing_id)
            results[listing_id] = page_number
            print(f"✅ {listing_id} found on page {page_number}")
            sheet.update_cell(i + 2, page_index + 1, page_number)

        return "✅ Scraping complete and sheet updated."

    except Exception as e:
        print(f"❌ Error: {e}")
        return f"❌ Error: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
