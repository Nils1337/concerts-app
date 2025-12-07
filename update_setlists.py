import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SETLIST_API_KEY = os.environ["SETLISTFM_API_KEY"]
USERNAME = os.environ["SETLISTFM_USERNAME"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_API_KEY"]

SETLIST_HEADERS = {
    "x-api-key": SETLIST_API_KEY,
    "Accept": "application/json"
}

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_all_setlists():
    """Fetches all 'attended' setlists using pagination."""
    results = []
    page = 1

    while True:
        url = f"https://api.setlist.fm/rest/1.0/user/{USERNAME}/attended?page={page}"
        r = requests.get(url, headers=SETLIST_HEADERS)

        if r.status_code != 200:
            print(f"Error fetching page {page}: {r.text}")
            break

        data = r.json()
        setlists = data.get("setlist", [])
        if not setlists:
            break

        results.extend(setlists)

        # For testing, stop after first page
        break

        # Stop when all pages are fetched
        if page >= data.get("total", 0) / data.get("itemsPerPage", 1):
            break

        page += 1

    return results


def upsert_setlist(setlist):
    """Insert or update a setlist in Supabase using the client library."""
    setlist_id = setlist.get("id")

    # Flattened fields
    artist = setlist.get("artist", {}).get("name")
    venue = setlist.get("venue", {}).get("name")
    city = setlist.get("venue", {}).get("city", {}).get("name")
    country = setlist.get("venue", {}).get("city", {}).get("country", {}).get("name")
    date_str = setlist.get("eventDate")
    url = setlist.get("url")

    try:
        event_date = datetime.strptime(date_str, "%d-%m-%Y").date().isoformat()
    except:
        event_date = None

    payload = {
        "id": setlist_id,
        "artist_name": artist,
        "venue_name": venue,
        "city_name": city,
        "country_name": country,
        "event_date": event_date,
        "url": url,
        "raw": setlist
    }

    # Upsert with Supabase client
    try:
        supabase.table("Setlist").upsert(payload, on_conflict="id").execute()
        print(f"Upserted {setlist_id}")
    except Exception as e:
        print(f"Exception for {setlist_id}: {e}")


if __name__ == "__main__":
    print("Fetching setlists...")
    all_setlists = fetch_all_setlists()
    print(f"Found {len(all_setlists)} setlists.")

    print(f"First setlist: {all_setlists[0]}")
    for s in all_setlists:
        upsert_setlist(s)

    print("Done.")
