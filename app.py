import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=15)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- UI ---
st.title("🏎️ F1 Premium Telemetry")
# (Keep your selectors here as they were)
# ... meetings, sessions, drivers ...

# --- DEFENSIVE DATA ENGINE ---
def get_tel(name):
    d_num = driver_map[name]
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    
    # 1. Inspect data before processing
    if not laps: 
        st.error(f"DEBUG: API returned 0 laps for {name}.")
        return pd.DataFrame()
        
    valid_laps = [l for l in laps if isinstance(l.get('lap_duration'), (int, float))]
    
    if not valid_laps:
        st.error(f"DEBUG: No valid lap durations found for {name}.")
        return pd.DataFrame()
    
    fastest = min(valid_laps, key=lambda x: x['lap_duration'])
    
    tel = fetch_api("car_data", {"session_key": s_key, "driver_number": d_num})
    df = pd.DataFrame(tel)
    
    # 2. Hard check on 'date' column existence
    if df.empty or 'date' not in df.columns:
        st.error(f"DEBUG: Car data empty or missing date column for {name}.")
        return pd.DataFrame()
    
    # 3. Force conversion with logging
    try:
        df['date'] = pd.to_datetime(df['date'], utc=True)
        start = pd.to_datetime(fastest['date_start'], utc=True)
        end = pd.to_datetime(fastest['date_end'], utc=True)
        return df[(df['date'] >= start) & (df['date'] <= end)]
    except Exception as e:
        st.error(f"DEBUG: Date conversion failed: {e}")
        return pd.DataFrame()

# --- EXECUTION ---
if st.sidebar.button("Generate Analysis"):
    df_a = get_tel(d1)
    df_b = get_tel(d2)
    
    if not df_a.empty and not df_b.empty:
        # Plotting...
        pass
