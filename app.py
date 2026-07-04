import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. DATA ENGINE ---
BASE_URL = "https://api.openf1.org/v1"

@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- 2. FASTEST LAP LOGIC ---
def get_fastest_lap_tel(driver_name, s_key, all_drivers):
    d_num = next(d['driver_number'] for d in all_drivers if d['full_name'] == driver_name)
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    
    # Filter out laps with no duration/dates
    valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
    if not valid_laps: return pd.DataFrame()
    
    fastest = min(valid_laps, key=lambda x: x['lap_duration'])
    
    # Fetch telemetry for the whole session and slice in Pandas
    tel = fetch_api("car_data", {"session_key": s_key, "driver_number": d_num})
    df = pd.DataFrame(tel)
    if df.empty: return df
    
    df['date'] = pd.to_datetime(df['date'])
    start = pd.to_datetime(fastest['date_start'])
    end = pd.to_datetime(fastest['date_end'])
    
    return df[(df['date'] >= start) & (df['date'] <= end)]

# --- 3. UI ---
# (Keep your existing selection UI here...)
# When generating plots:
if st.button("Generate Analysis"):
    drivers = fetch_api("drivers", {"session_key": s_key})
    df_a = get_fastest_lap_tel(d1, s_key, drivers)
    df_b = get_fastest_lap_tel(d2, s_key, drivers)

    if not df_a.empty and not df_b.empty:
        # Metrics: Calculate safely
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("MAX VEL (A)", f"{df_a['speed'].max():.0f} km/h")
        c2.metric("AVG THR (A)", f"{df_a['throttle'].mean():.0f}%")
        # Delta: Resample to compare A and B by time-index if possible, or simple max diff
        c3.metric("MAX GAP", f"{abs(df_a['speed'].max() - df_b['speed'].max()):.1f} km/h")
        c4.metric("GEAR (A)", f"{df_a['n_gear'].mode()[0]}")
        c5.metric("RPM (A)", f"{df_a['rpm'].mean():.0f}")

        # Plots
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name="Speed A"), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle A"), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['rpm'], name="RPM A"), row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)
