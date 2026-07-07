import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & PIT-WALL CARBON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")

# --- 2. ROBUST API FETCHER ---
def get_openf1(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=45)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- 3. DATA ENGINE ---
def get_telemetry(d_api, s_key, year, sim_mode, d_id):
    if sim_mode:
        seed = zlib.crc32(f"{year}_{d_api}_{d_id}".encode())
        np.random.seed(seed)
        dist = np.linspace(0, 4000.0, 1000)
        return pd.DataFrame({'distance': dist, 'speed': 290.0 + (seed % 10)}), 90.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key})
    if laps.empty: return pd.DataFrame(), 0, 0
    f_lap = laps[laps['driver_number'] == d_api].sort_values('lap_duration').iloc[0]
    
    start = pd.to_datetime(f_lap['date_start']).tz_convert('UTC').tz_localize(None)
    s_str = (start - pd.Timedelta(seconds=0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    e_str = (start + pd.Timedelta(seconds=float(f_lap['lap_duration']) + 0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={f_lap['driver_number']}&date>={s_str}&date<={e_str}")
    if tel.empty: return pd.DataFrame(), f_lap['lap_duration'], 0
    
    # CRITICAL FIX: Convert strings to datetime to support .diff()
    tel['date'] = pd.to_datetime(tel['date'])
    tel = tel.dropna(subset=['speed', 'date']).sort_values('date')
    
    # Calculate time delta and distance
    tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
    tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
    
    dist_ref = np.linspace(0, tel['dist'].max() if tel['dist'].max() > 0 else 4000.0, 1000)
    return pd.DataFrame({
        'distance': dist_ref, 
        'speed': np.interp(dist_ref, tel['dist'], tel['speed'])
    }), f_lap['lap_duration'], tel['dist'].max()

# --- 4. CONTROL & DISPLAY ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    s_key = get_openf1("sessions", {"meeting_key": meetings[meetings['meeting_name'] == gp]['meeting_key'].iloc[0]})['session_key'].iloc[0]
    drivers = get_openf1("drivers", {"session_key": s_key})
    
    if not drivers.empty:
        d1 = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique()))
        d2 = st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Enable Simulation Mode")

        if st.sidebar.button("Run Analysis"):
            d1_num = drivers[drivers['full_name'].str.title()==d1]['driver_number'].iloc[0]
            d2_num = drivers[drivers['full_name'].str.title()==d2]['driver_number'].iloc[0]
            df1, lap1, len1 = get_telemetry(d1_num, s_key, year, sim, 1)
            df2, lap2, len2 = get_telemetry(d2_num, s_key, year, sim, 2)

            if not df1.empty and not df2.empty and len(df1) > 5:
                # Math for Spatial Gap
                common = min(len(df1), len(df2))
                v1, v2 = df1['speed'].values[:common]/3.6, df2['speed'].values[:common]/3.6
                delta = np.cumsum((1 / np.maximum(v2, 1)) - (1 / np.maximum(v1, 1))) * (max(len1, len2)/common)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("VMAX A", f"{df1['speed'].max():.0f} KM/H")
                m2.metric("VMAX B", f"{df2['speed'].max():.0f} KM/H")
                m3.metric("LAP DELTA", f"{abs(lap1-lap2):.3f} S", f"{(lap2-lap1):.3f}", delta_color="inverse")
                m4.metric("SPATIAL GAP", f"{abs(delta[-1]):.3f} S", f"{delta[-1]:.3f}", delta_color="normal")
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
                fig.add_trace(go.Scatter(x=df1['distance'], y=df1['speed'], name=d1), row=1, col=1)
                fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta, name="Time Delta"), row=2, col=1)
                st.plotly_chart(fig, use_container_width=True)
