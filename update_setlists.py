import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import time
from bs4 import BeautifulSoup

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
        url = f"https://api.setlist.fm/rest/1.0/user/{USERNAME}/attended?p={page}"
        r = requests.get(url, headers=SETLIST_HEADERS)

        if r.status_code != 200:
            print(f"Error fetching page {page}: {r.text}")
            break

        data = r.json()
        setlists = data.get("setlist", [])
        if not setlists:
            break

        results.extend(setlists)

        # Stop when all pages are fetched
        if page >= data.get("total", 0) / data.get("itemsPerPage", 1):
            break

        page += 1
        time.sleep(1)

    return results


def fetch_upcoming_concerts():
    response = requests.get(f"https://setlist.fm/attended/{USERNAME}")
    if response.status_code != 200:
        print(f"Error fetching upcoming setlists: {response.text}")
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    upcoming = []

    upcoming_div = soup.find('div', class_='userAttendancesAndNote')
    setlist_el = upcoming_div.find_all('li', class_='setlist')
    
    for el in setlist_el:
        artist = el.find('div', class_='content').find('a').find('strong').string
        
        location_string = el.find('div', class_='content').find('span', class_='subline').find('span').string
        location_parts = [part.strip() for part in location_string.split(',')]
        venue = location_parts[0] if len(location_parts) > 0 else None
        city = location_parts[1] if len(location_parts) > 1 else None
        country = location_parts[2] if len(location_parts) > 2 else None
        href = el.find('div', class_='content').find('a')['href']
        url = "https://setlist.fm" + href.lstrip('.')

        for i, value in enumerate(el.find('span', class_='smallDateBlock').stripped_strings):
            if (i == 0):
                month = value
            elif (i == 1):
                day = value
            elif (i == 2):
                year = value

        date_str = f"{day} {month} {year}"
        date = datetime.strptime(date_str, "%d %b %Y").date()

        payload = {
            "artist_name": artist,
            "venue_name": venue,
            "city_name": city,
            "country_name": country,
            "event_date": date.isoformat(),
            "url": url,
        }
        upcoming.append(payload)

    return upcoming


def upsert_setlists(setlists):

    # Replace records from setlist.fm
    for setlist in all_setlists:
        """Replace a setlist in Supabase to keep data exactly in sync with setlist.fm."""
        setlist_id = setlist.get("id")

        # Flattened fields
        artist = setlist.get("artist", {}).get("name")
        venue = setlist.get("venue", {}).get("name")
        city = setlist.get("venue", {}).get("city", {}).get("name")
        country = setlist.get("venue", {}).get("city", {}).get("country", {}).get("name")
        date_str = setlist.get("eventDate")
        url = setlist.get("url")
        city_lat = setlist.get("venue", {}).get("city", {}).get("coords", {}).get("lat")
        city_long = setlist.get("venue", {}).get("city", {}).get("coords", {}).get("long")
        
        try:
            event_date = datetime.strptime(date_str, "%d-%m-%Y").date().isoformat()
        except:
            event_date = None

        payload = {
            "id": setlist_id,
            "artist_name": artist,
            "venue_name": venue,
            "city_name": city,
            "city_lat": city_lat,
            "city_long": city_long,
            "country_name": country,
            "event_date": event_date,
            "url": url,
            "raw": setlist
        }

        # Delete existing record and insert new one to keep data exactly in sync
        try:
            supabase.table("Setlist").delete().eq("id", setlist_id).execute()
            supabase.table("Setlist").insert(payload).execute()
            print(f"Replaced {setlist_id}")
        except Exception as e:
            print(f"Exception for {setlist_id}: {e}")
    
    # Get IDs from setlist.fm
    setlist_fm_ids = set(s.get("id") for s in all_setlists)

    # Get all IDs from Supabase
    existing_records = supabase.table("Setlist").select("id").execute()
    supabase_ids = set(record["id"] for record in existing_records.data)

    # Delete records in Supabase that are not in setlist.fm
    ids_to_delete = supabase_ids - setlist_fm_ids
    for setlist_id in ids_to_delete:
        try:
            supabase.table("Setlist").delete().eq("id", setlist_id).execute()
            print(f"Deleted {setlist_id}")
        except Exception as e:
            print(f"Exception deleting {setlist_id}: {e}")


def upsert_upcoming_concerts(upcoming_concerts):
    try:
        supabase.table("Upcoming").delete().neq("id", 0).execute()
    except Exception as e:
        print(f"Exception deleting existing upcoming concerts: {e}")

    i = 0
    for upcoming in upcoming_concerts:
        try:
            supabase.table("Upcoming").insert(upcoming).execute()
            i += 1
        except Exception as e:
            print(f"Exception for {upcoming}: {e}")
    
    print(f"Inserted {i} upcoming concerts.")



if __name__ == "__main__":
    print("Fetching setlists...")
    all_setlists = fetch_all_setlists()
    print(f"Found {len(all_setlists)} setlists.")
    upsert_setlists(all_setlists)

    print("Fetching upcoming concerts...")
    upcoming_concerts = fetch_upcoming_concerts()
    print(f"Found {len(upcoming_concerts)} upcoming concerts.")
    upsert_upcoming_concerts(upcoming_concerts)

    print("Done.")
