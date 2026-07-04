import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# --- 1. CONFIG ---
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

# --- 2. HYBRID LOADER ---
def fetch_session_data(year, round_num):
    """Attempt live load; fallback to local CSV if IP blocked."""
    try:
        session = fastf1.get_session(year, round_num, 'Q')
        session.load(telemetry=True, laps=True)
        return session, "LIVE"
    except Exception:
        # Fallback path: looking for data/YYYY_Round_Q.csv
        file_path = f"data/{year}_{round_num}_Q.csv"
        if os.path.exists(file_path):
            return pd.read_csv(file_path), "ARCHIVE"
        return None, "ERROR"

# --- 3. UI & ENGINE ---
st.title("🚀 F1 Telemetry Analysis")

# Sidebar
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
selected_gp = st.sidebar.selectbox("Grand Prix", schedule['EventName'].tolist())
round_num = int(schedule[schedule['EventName'] == selected_gp]['RoundNumber'].iloc[0])

# Execution
session_data, mode = fetch_session_data(year, round_num)

if mode == "ERROR":
    st.error("Live API blocked and no archive found. Please upload a CSV to /data.")
else:
    if mode == "LIVE":
        st.info("⚡ Live API Mode Active")
        drivers = session_data.results['FullName'].dropna().tolist()
        d1 = st.sidebar.selectbox("Driver A", drivers)
        d2 = st.sidebar.selectbox("Ref Driver", drivers)
        
        # Extract telemetry
        c1 = session_data.results[session_data.results['FullName'] == d1]['Abbreviation'].iloc[0]
        c2 = session_data.results[session_data.results['FullName'] == d2]['Abbreviation'].iloc[0]
        lap_a = session_data.laps.pick_driver(c1).pick_fastest().get_telemetry()
        lap_b = session_data.laps.pick_driver(c2).pick_fastest().get_telemetry()
        delta = fastf1.utils.delta_time(session_data.laps.pick_driver(c1).pick_fastest(), 
                                        session_data.laps.pick_driver(c2).pick_fastest())
    else:
        st.warning("⚠️ Archived Mode: Data is pre-loaded.")
        # Logic for reading columns from your CSV...
        lap_a, lap_b = session_data, session_data 

    # Plotting Logic
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=lap_a['Distance'], y=lap_a['Speed'], name="Driver A"), row=1, col=1)
    fig.add_trace(go.Scatter(x=lap_b['Distance'], y=lap_b['Speed'], name="Ref Driver"), row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

# --- 4. EXPLANATION GUIDE ---
with st.expander("📖 Architecture Guide"):
    st.write("**Tech:** Implements a hybrid data pipeline. It defaults to the FastF1 live feed (local) and falls back to static CSV archives (cloud) to bypass IP-based scraping restrictions.")
    st.write("**Non-Tech:** This dashboard visualizes driver performance metrics. If you see 'Archived Mode', the live feed is unavailable due to infrastructure security policies.")
