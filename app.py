import streamlit as st
import requests
import pandas as pd

# 1. Setup Data Fetching
@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    url = f"https://api.openf1.org/v1/{endpoint}"
    response = requests.get(url, params=params)
    return response.json() if response.status_code == 200 else []

st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.title("🏎️ Premium F1 Live Analytics")

# 2. Hierarchical Selection Flow
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = fetch_api("meetings", {"year": year})
meeting_map = {m['meeting_name']: m['meeting_key'] for m in meetings}
selected_gp = st.sidebar.selectbox("Grand Prix", list(meeting_map.keys()))

# Only proceed if we have a meeting_key
if selected_gp:
    m_key = meeting_map[selected_gp]
    sessions = fetch_api("sessions", {"meeting_key": m_key})
    session_map = {s['session_name']: s['session_key'] for s in sessions}
    
    if session_map:
        selected_session = st.sidebar.selectbox("Session", list(session_map.keys()))
        s_key = session_map[selected_session]
        
        # Only fetch drivers once we have a valid s_key
        drivers = fetch_api("drivers", {"session_key": s_key})
        if drivers:
            driver_map = {d['full_name']: d['driver_number'] for d in drivers}
            d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()))
            d2 = st.sidebar.selectbox("Ref Driver", list(driver_map.keys()))
            
            if st.sidebar.button("Generate Analysis"):
                st.success(f"Analyzing {d1} vs {d2}...")
                # Your plotting logic goes here
        else:
            st.sidebar.warning("No driver data available for this session.")
    else:
        st.sidebar.warning("No sessions found for this GP.")
