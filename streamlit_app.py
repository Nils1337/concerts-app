import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_API_KEY"]  # sicher für private App
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- Streamlit layout ---
st.title("Meine Konzerte 🎵")
st.set_page_config(layout="wide")

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

    # --- Filters and Table Layout ---
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Filter")
        artists = st.multiselect("Artist:", options=df['artist_name'].dropna().unique())
        countries = st.multiselect("Land:", options=df['country_name'].dropna().unique())
        
        min_year = int(df['event_date'].dt.year.min())
        max_year = int(df['event_date'].dt.year.max())
        selected_years = st.slider("Jahr:", min_value=min_year, max_value=max_year, value=(min_year, max_year))
    
    with col2:
        filtered = df
        if artists:
            filtered = filtered[filtered['artist_name'].isin(artists)]
        if countries:
            filtered = filtered[filtered['country_name'].isin(countries)]

        # Filter nach Jahr
        filtered = filtered[(filtered['event_date'].dt.year >= selected_years[0]) &
                            (filtered['event_date'].dt.year <= selected_years[1])]
        
        st.subheader("Alle Konzerte")
        st.write(f"{len(filtered)} Konzerte gefunden")
        st.dataframe(filtered[['event_date', 'artist_name', 'venue_name', 'city_name', 'country_name', 'url']].sort_values("event_date", ascending=False), column_config={
            "event_date": st.column_config.DateColumn("Date", format="localized"),
            "artist_name": "Artist",
            "venue_name": "Venue",
            "city_name": "City",
            "country_name": "Country",
            "url": st.column_config.LinkColumn("Setlist", display_text="Link")
        })

        # --- Chart: Anzahl Konzerte pro Jahr ---
        filtered['year'] = filtered['event_date'].dt.year
        chart_data = filtered.groupby('year').size().reset_index(name='Anzahl Konzerte')
        st.subheader("Konzerte pro Jahr")
        st.bar_chart(chart_data.set_index('year')['Anzahl Konzerte'])

        # --- Table: Anzahl Konzerte pro Artist ---
        artist_data = filtered.groupby('artist_name').size().reset_index(name='Attendances').sort_values('Attendances', ascending=False)
        st.subheader("Konzerte pro Artist")
        st.dataframe(artist_data, column_config={
            "artist_name": "Artist",
            "Attendances": "Attendances"
        }, hide_index=True)