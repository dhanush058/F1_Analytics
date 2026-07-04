import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ROBUST DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=15)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- 2. FIXED DATA PROCESSING ---
def get_fastest_lap_tel(d_name, s_key, all_drivers):
    d_num = next(d['driver_number'] for d in all_drivers if d['full_name'] == d_name)
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    
    # Validate laps data
    valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
    if not valid_laps: return pd.DataFrame()
    
    fastest = min(valid_laps, key=lambda x: x['lap_duration'])
    
    # Fetch telemetry
    tel = fetch_api("car_data", {"session_key": s_key, "driver_number": d_num})
    df = pd.DataFrame(tel)
    
    # FIX: Check if dataframe is empty before converting dates
    if df.empty or 'date' not in df.columns:
        return pd.DataFrame()
    
    # FIX: Use utc=True to avoid timezone-naive/aware mixed errors
    df['date'] = pd.to_datetime(df['date'], utc=True)
    
    start = pd.to_datetime(fastest['date_start'], utc=True)
    end = pd.to_datetime(fastest['date_end'], utc=True)
    
    return df[(df['date'] >= start) & (df['date'] <= end)]

# --- 3. UI LAYOUT ---
# (Ensure your meeting/session/driver selection logic remains here)

if st.sidebar.button("Generate Analysis"):
    drivers = fetch_api("drivers", {"session_key": s_key})
    df_a = get_fastest_lap_tel(d1, s_key, drivers)
    df_b = get_fastest_lap_tel(d2, s_key, drivers)

    if not df_a.empty and not df_b.empty:
        # Display Metrics...
        # Display Plots...
        pass
    else:
        st.error("No telemetry records found. The session may be incomplete or data is unavailable.")
