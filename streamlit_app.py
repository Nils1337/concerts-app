import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_API_KEY"]  # sicher für private App
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Streamlit layout ---
st.title("Meine Konzerte 🎵")

# --- Fetch data ---
def get_setlists():
    response = supabase.table("Setlist").select("*").execute()
    return pd.DataFrame(response.data)

df = get_setlists()

if df.empty:
    st.info("Keine Setlists gefunden")
else:
    # Datumsformat
    df['event_date'] = pd.to_datetime(df['event_date'], errors='coerce')

    # --- Filter ---
    artists = st.multiselect("Filter Artist:", options=df['artist_name'].dropna().unique())
    countries = st.multiselect("Filter Land:", options=df['country_name'].dropna().unique())
    
    filtered = df
    if artists:
        filtered = filtered[filtered['artist_name'].isin(artists)]
    if countries:
        filtered = filtered[filtered['country_name'].isin(countries)]
    
    st.write(f"{len(filtered)} Konzerte gefunden")
    st.dataframe(filtered[['event_date', 'artist_name', 'venue_name', 'city_name', 'country_name']].sort_values("event_date"), column_config={
        "event_date": st.column_config.DateColumn("Date", format="localized"),
        "artist_name": "Artist",
        "venue_name": "Venue",
        "city_name": "City",
        "country_name": "Country"
    })

    # --- Chart: Anzahl Konzerte pro Jahr ---
    filtered['year'] = filtered['event_date'].dt.year
    chart_data = filtered.groupby('year').size().reset_index(name='Anzahl Konzerte')
    st.bar_chart(chart_data.set_index('year')['Anzahl Konzerte'])