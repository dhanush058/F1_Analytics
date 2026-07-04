import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# 1. METADATA & DATA FETCHING (STATIC)
# =========================================================
@st.cache_data(ttl=600, show_spinner=False)
def fetch_api_json(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except: return None

def fetch_telemetry_safe(s_key, num_a, num_b):
    try:
        # Resolve fastest lap window
        laps = fetch_api_json(f"https://api.openf1.org/v1/laps?session_key={s_key}&driver_number={num_a}")
        if not laps: return None, None
        df_laps = pd.DataFrame(laps).dropna(subset=['lap_duration'])
        fastest = df_laps.loc[df_laps['lap_duration'].idxmin()]
        
        # Parse timestamp safely
        start_dt = pd.to_datetime(fastest['date_start'], format='mixed')
        end_dt = start_dt + pd.Timedelta(seconds=float(fastest['lap_duration']))
        t_filter = f"&date>={start_dt.strftime('%Y-%m-%dT%H:%M:%S')}&date<={end_dt.strftime('%Y-%m-%dT%H:%M:%S')}"
        
        # Fetch telemetry
        res_a = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={num_a}{t_filter}", timeout=10).json()
        res_b = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={num_b}{t_filter}", timeout=10).json()
        
        df_a, df_b = pd.DataFrame(res_a), pd.DataFrame(res_b)
        df_a['date'] = pd.to_datetime(df_a['date'], format='mixed')
        df_b['date'] = pd.to_datetime(df_b['date'], format='mixed')
        
        return df_a, df_b
    except: return None, None

# =========================================================
# 2. MAIN APP LAYOUT (NO FRAGMENTS = NO DIMMING)
# =========================================================
st.set_page_config(page_title="F1 Analytics", layout="wide")
st.title("🏎️ Formula 1 Analytics Vault")

# Selection Logic
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
# ... [Insert your existing Round/Driver selection logic here] ...

# Resolve Key
session_key = None 
sessions = fetch_api_json(f"https://api.openf1.org/v1/sessions?year={year}")
# ... [Insert your existing fuzzy match logic to set session_key] ...

# =========================================================
# 3. STATIC RENDER ENGINE
# =========================================================
if session_key:
    # Check status once
    s_info = fetch_api_json(f"https://api.openf1.org/v1/sessions?session_key={session_key}")
    status = s_info[0].get('status') if s_info else "unknown"
    
    if status == "finished":
        st.success("✅ Session Finalized: Data Loaded")
        df_a, df_b = fetch_telemetry_safe(session_key, driver_map[driver_a], driver_map[driver_b])
        # ... [Render Plotly charts] ...
    else:
        st.info(f"⏳ Session Status: {status}. Awaiting Finalization.")
        st.write("The telemetry will appear here once the session is marked as 'finished' on the server.")
else:
    st.error("Select a valid session to begin.")
