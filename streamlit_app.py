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
    col1, col2 = st.columns([1, 5])
    
    with col1:
        st.subheader("Filter")
        artists = st.multiselect("Artist:", options=df['artist_name'].dropna().unique())
        venues = st.multiselect("Venue:", options=df['venue_name'].dropna().unique())
        cities = st.multiselect("Stadt:", options=df['city_name'].dropna().unique())
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
        if cities:
            filtered = filtered[filtered['city_name'].isin(cities)]
        if venues:
            filtered = filtered[filtered['venue_name'].isin(venues)]

        # Filter nach Jahr
        filtered = filtered[(filtered['event_date'].dt.year >= selected_years[0]) &
                            (filtered['event_date'].dt.year <= selected_years[1])]
    
        # If filtering removed all rows, show a helpful message and an empty table
        if filtered.empty:
            st.info("Keine Konzerte für die gewählten Filter.")
        else:
            # Group by date and location, separate artists and links
            grouped_data = []
            for (event_date, venue_name, city_name, country_name), group in filtered.groupby(['event_date', 'venue_name', 'city_name', 'country_name']):
                # Separate artist names and create links
                artists = []
                url = group['url'].iloc[0] if 'url' in group.columns and not group['url'].isna().all() else None
                for _, row in group.iterrows():
                    artist = row.get('artist_name')
                    if artist:
                        artists.append(artist)

                grouped_data.append({
                    'event_date': event_date,
                    'artists': artists,
                    'venue_name': venue_name,
                    'city_name': city_name,
                    'country_name': country_name,
                    'setlist': url
                })

            grouped_df = pd.DataFrame(grouped_data).sort_values("event_date", ascending=False)
            # Combine venue, city, country into one location column
            grouped_df['location'] = grouped_df.apply(lambda row: f"{row['venue_name']}, {row['city_name']}, {row['country_name']}", axis=1)

            # --- Latest Concert and Latest First-Time Artist ---
            st.subheader("Highlights")
            col_latest_concert, col_latest_artist = st.columns(2)

            # Latest concert
            with col_latest_concert:
                latest_concert = grouped_df.iloc[0]
                date_str = pd.to_datetime(latest_concert['event_date']).strftime("%d.%m.%Y")
                artists_str = ", ".join(latest_concert['artists']) if isinstance(latest_concert['artists'], (list, tuple)) else str(latest_concert['artists'])
                location_str = f"{latest_concert['venue_name']}, {latest_concert['city_name']}, {latest_concert['country_name']}"
                st.markdown("<div style='font-size:14px; color:#888; margin-bottom:4px;'>Letztes Konzert</div><div style='font-size:22px; font-weight:bold; margin-bottom:12px;'>{}</div>".format(artists_str), unsafe_allow_html=True)
                st.write(f"📅 {date_str}")
                st.write(f"📍 {location_str}")

            # Latest first-time artist (artist with only 1 appearance, most recent)
            with col_latest_artist:
                first_timers = filtered.groupby('artist_name').size().reset_index(name='count')
                first_timers = first_timers[first_timers['count'] == 1]
                if not first_timers.empty:
                    # Get the most recent first-timer
                    first_timer_names = first_timers['artist_name'].tolist()
                    recent_first_timers = filtered[filtered['artist_name'].isin(first_timer_names)].sort_values('event_date', ascending=False)
                    if not recent_first_timers.empty:
                        latest_first_timer = recent_first_timers.iloc[0]
                        date_str_ft = pd.to_datetime(latest_first_timer['event_date']).strftime("%d.%m.%Y")
                        location_str = f"{latest_first_timer['venue_name']}, {latest_first_timer['city_name']}, {latest_first_timer['country_name']}"
                        st.markdown("<div style='font-size:14px; color:#888; margin-bottom:4px;'>Letzter neuer Künstler</div><div style='font-size:22px; font-weight:bold; margin-bottom:12px;'>{}</div>".format(latest_first_timer['artist_name']), unsafe_allow_html=True)
                        st.write(f"📅 {date_str_ft}")
                        st.write(f"📍 {location_str}")
                else:
                    st.info("Alle Künstler wurden bereits besucht.")

            col_all_concerts, col_upcoming_concerts = st.columns(2)

            # All concerts table
            with col_all_concerts:
                st.subheader("Vergangene Konzerte")
                # Use grouped events (one row per date+location) for counts
                st.write(f"{len(grouped_df)} vergangene Konzerte")
                st.dataframe(grouped_df[['event_date', 'artists', 'location', 'setlist']], column_config={
                    "event_date": st.column_config.DateColumn("Date", format="localized", width="small"),
                    "artists": st.column_config.ListColumn("Artists", width="medium"),
                    "location": "Location",
                    "setlist": st.column_config.LinkColumn("Setlist", width="medium", display_text="Link"),
                }, hide_index=True, use_container_width=True, height=600)

            # Upcoming concerts table (empty for now)
            with col_upcoming_concerts:
                st.subheader("Kommende Konzerte")
                upcoming_df = pd.DataFrame(columns=['event_date', 'artists', 'location'])
                st.write(f"{len(upcoming_df)} kommende Konzerte")
                st.dataframe(upcoming_df, column_config={
                    "event_date": st.column_config.DateColumn("Date", format="localized", width="small"),
                    "artists": st.column_config.ListColumn("Artists", width="medium"),
                    "location": "Location",
                }, hide_index=True, use_container_width=True, height=600)

            col1, col2 = st.columns([1, 1])
            with col1:
               # --- Table: Anzahl Konzerte pro Artist ---
                artist_data = filtered.groupby('artist_name').size().reset_index(name='Attendances').sort_values('Attendances', ascending=False)
                st.subheader("Konzerte pro Artist")

                # Top-3 as metrics side-by-side with caption
                top_n = min(3, len(artist_data))
                if top_n > 0:
                    st.caption("Top 3")
                    top3 = artist_data.head(top_n)
                    cols = st.columns(top_n)
                    for i, (_, row) in enumerate(top3.iterrows()):
                        with cols[i]:
                            st.metric(label=str(row['artist_name']), value=int(row['Attendances']))

                # Remove top-3 from the table and show the rest with a caption
                rest = artist_data.iloc[top_n:]
                st.caption("Andere")
                if rest.empty:
                    st.info("Keine weiteren Künstler.")
                else:
                    st.dataframe(rest, column_config={
                        "artist_name": "Artist",
                        "Attendances": "Anzahl"
                    }, hide_index=True)

            with col2:
                 # --- Table: Anzahl Konzerte pro Venue ---
                venue_data = grouped_df.groupby('venue_name').size().reset_index(name='Attendances').sort_values('Attendances', ascending=False)
                st.subheader("Konzerte pro Venue")

                # Top-3 as metrics side-by-side with caption
                top_n = min(3, len(venue_data))
                if top_n > 0:
                    st.caption("Top 3")
                    top3 = venue_data.head(top_n)
                    cols = st.columns(top_n)
                    for i, (_, row) in enumerate(top3.iterrows()):
                        with cols[i]:
                            st.metric(label=str(row['venue_name']), value=int(row['Attendances']))

                # Remove top-3 from the table and show the rest with a caption
                rest = venue_data.iloc[top_n:]
                st.caption("Andere")
                if rest.empty:
                    st.info("Keine weiteren Venues.")
                else:
                    st.dataframe(rest, column_config={
                        "venue_name": "Artist",
                        "Attendances": "Anzahl"
                    }, hide_index=True)
              
            col1, col2 = st.columns([1, 1])

            with col1:
                # --- Table: Anzahl Konzerte pro Stadt ---
                city_data = grouped_df.groupby('city_name').size().reset_index(name='Attendances').sort_values('Attendances', ascending=False)
                st.subheader("Konzerte pro Stadt")

                # Top-3 as metrics side-by-side with caption
                top_n = min(3, len(city_data))
                if top_n > 0:
                    st.caption("Top 3")
                    top3 = city_data.head(top_n)
                    cols = st.columns(top_n)
                    for i, (_, row) in enumerate(top3.iterrows()):
                        with cols[i]:
                            st.metric(label=str(row['city_name']), value=int(row['Attendances']))

                # Remove top-3 from the table and show the rest with a caption
                rest = city_data.iloc[top_n:]
                st.caption("Andere")
                if rest.empty:
                    st.info("Keine weiteren Städte.")
                else:
                    st.dataframe(rest, column_config={
                        "city_name": "Stadt",
                        "Attendances": "Anzahl"
                    }, hide_index=True)


            with col2:
                # --- Table: Anzahl Konzerte pro Land ---
                country_data = grouped_df.groupby('country_name').size().reset_index(name='Attendances').sort_values('Attendances', ascending=False)
                st.subheader("Konzerte pro Land")

                # Top-3 as metrics side-by-side with caption
                top_n = min(3, len(country_data))
                if top_n > 0:
                    st.caption("Top 3")
                    top3 = country_data.head(top_n)
                    cols = st.columns(top_n)
                    for i, (_, row) in enumerate(top3.iterrows()):
                        with cols[i]:
                            st.metric(label=str(row['country_name']), value=int(row['Attendances']))

                # Remove top-3 from the table and show the rest with a caption
                rest = country_data.iloc[top_n:]
                st.caption("Andere")
                if rest.empty:
                    st.info("Keine weiteren Länder.")
                else:
                    st.dataframe(rest, column_config={
                        "country_name": "Land",
                        "Attendances": "Anzahl"
                    }, hide_index=True)

            # --- Chart: Anzahl Konzerte pro Jahr ---
            # Count unique events per year from grouped events
            grouped_df['year'] = pd.to_datetime(grouped_df['event_date']).dt.year
            chart_data = grouped_df.groupby('year').size().reset_index(name='Anzahl Konzerte')
            st.subheader("Konzerte pro Jahr")
            st.bar_chart(chart_data.set_index('year')['Anzahl Konzerte'])