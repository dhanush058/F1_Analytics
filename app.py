import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ API HELPERS
# =========================================================
@st.cache_data(ttl=3600)
def fetch_api_json(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except: return None

# =========================================================
# 🏎️ APP LAYOUT & STATE
# =========================================================
st.set_page_config(page_title="F1 Analytics", layout="wide")
st.title("🏎️ Formula 1 Analytics Vault")

# Initialize Session State to lock data in memory (no dimming/flicker)
if "telemetry" not in st.session_state:
    st.session_state.telemetry = None

# Sidebar Controls
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Track Name", "Melbourne")

# =========================================================
# 🌐 METADATA RESOLVER
# =========================================================
session_key = None
sessions = fetch_api_json(f"https://api.openf1.org/v1/sessions?year={year}")

if sessions:
    for s in sessions:
        if track.lower() in str(s.get('location', '')).lower():
            session_key = s.get('session_key')
            st.sidebar.success(f"Session found: {s.get('session_name')}")
            break
else:
    st.sidebar.error("API unreachable.")

# =========================================================
# 📊 DATA ENGINE (EXECUTES ONLY ONCE)
# =========================================================
if session_key and st.sidebar.button("Load Data"):
    with st.spinner("Fetching data..."):
        drivers = fetch_api_json(f"https://api.openf1.org/v1/drivers?session_key={session_key}")
        if drivers:
            d1, d2 = drivers[0]['driver_number'], drivers[1]['driver_number']
            laps = fetch_api_json(f"https://api.openf1.org/v1/laps?session_key={session_key}&driver_number={d1}")
            
            if laps:
                fastest = pd.DataFrame(laps).sort_values('lap_duration').iloc[0]
                start = pd.to_datetime(fastest['date_start'], format='mixed')
                end = start + pd.Timedelta(seconds=float(fastest['lap_duration']))
                t_filter = f"&date>={start.strftime('%Y-%m-%dT%H:%M:%S')}&date<={end.strftime('%Y-%m-%dT%H:%M:%S')}"
                
                res_a = requests.get(f"https://api.openf1.org/v1/car_data?session_key={session_key}&driver_number={d1}{t_filter}").json()
                res_b = requests.get(f"https://api.openf1.org/v1/car_data?session_key={session_key}&driver_number={d2}{t_filter}").json()
                
                st.session_state.telemetry = (pd.DataFrame(res_a), pd.DataFrame(res_b))

# =========================================================
# 📈 FROZEN RENDER ENGINE
# =========================================================
if st.session_state.telemetry is not None:
    df_a, df_b = st.session_state.telemetry
    st.write("Dashboard Rendered - Frozen State Active")
    
    # Plotting code using df_a and df_b...
else:
    st.info("Select track and click 'Load Data' to begin.")
