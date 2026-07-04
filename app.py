import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. ROBUST DATA FETCHING ---
BASE_URL = "https://api.openf1.org/v1"

@st.cache_data(ttl=3600)
def fetch_data(endpoint, params=None):
    res = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    return res.json() if res.status_code == 200 else []

# --- 2. UI LAYOUT ---
st.set_page_config(layout="wide")
st.title("🏎️ F1 Live Telemetry")

year = st.sidebar.selectbox("Year", [2026, 2025])
meetings = fetch_data("meetings", {"year": year})
meeting_map = {m['meeting_name']: m['meeting_key'] for m in meetings}
selected_gp = st.sidebar.selectbox("Grand Prix", list(meeting_map.keys()))

# Get Sessions
sessions = fetch_data("sessions", {"meeting_key": meeting_map[selected_gp]})
session_map = {s['session_name']: s['session_key'] for s in sessions}
selected_session = st.sidebar.selectbox("Session", list(session_map.keys()))

# Get Drivers
drivers = fetch_data("drivers", {"session_key": session_map[selected_session]})
driver_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()))
d2 = st.sidebar.selectbox("Ref Driver", list(driver_map.keys()))

# --- 3. EXECUTION ---
if st.button("Generate Dashboard"):
    with st.spinner("Fetching live telemetry..."):
        # Fetching Telemetry
        tel_a = fetch_data("car_data", {"session_key": session_map[selected_session], "driver_number": driver_map[d1]})
        tel_b = fetch_data("car_data", {"session_key": session_map[selected_session], "driver_number": driver_map[d2]})
        
        if tel_a and tel_b:
            df_a, df_b = pd.DataFrame(tel_a), pd.DataFrame(tel_b)
            
            # Dashboard Metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Max Speed A", f"{df_a['speed'].max()} km/h")
            col2.metric("Max Speed B", f"{df_b['speed'].max()} km/h")
            
            # Plot
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=df_a['speed'], name=d1))
            fig.add_trace(go.Scatter(y=df_b['speed'], name=d2))
            fig.update_layout(template="plotly_dark", title="Speed Comparison")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("No telemetry records found for these drivers in this session.")
