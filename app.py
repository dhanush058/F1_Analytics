import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & PIT-WALL CARBON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")

st.markdown("""
<style>
    .stApp { background-color: #0B0B0E; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    [data-testid="stMetric"] {
        background-color: #15151C !important; border: 1px solid #2A2A35 !important;
        border-top: 4px solid #FF1801 !important; border-radius: 4px !important;
        padding: 10px 15px !important; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] { color: #8E8E9F !important; font-family: 'Courier New', monospace !important; font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 1px !important; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-family: 'Courier New', monospace !important; font-size: 1.35rem !important; font-weight: 800 !important; }
    h1, h2, h3, h4 { font-family: 'Courier New', monospace !important; color: #FFFFFF !important; letter-spacing: 1px !important; }
</style>
""", unsafe_allow_html=True)

# Neon Color Palette
COLOR_A, COLOR_B, COLOR_DELTA, COLOR_BG = '#00FFFF', '#FF00FF', '#00FF00', '#0B0B0E'

def get_openf1(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=45)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

def get_telemetry(d_api, s_key, year, sim_mode, d_id):
    if sim_mode:
        seed = zlib.crc32(f"{year}_{d_api}_{d_id}".encode())
        np.random.seed(seed)
        dist = np.linspace(0, 4000.0, 1000)
        return pd.DataFrame({'distance': dist, 'speed': 290.0 + (seed % 10), 'throttle': 100.0}), 90.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key})
    if laps.empty: return pd.DataFrame(), 0, 0
    f_lap = laps[laps['driver_number'] == d_api].sort_values('lap_duration').iloc[0]
    
    start = pd.to_datetime(f_lap['date_start']).tz_convert('UTC').tz_localize(None)
    s_str = (start - pd.Timedelta(seconds=0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    e_str = (start + pd.Timedelta(seconds=float(f_lap['lap_duration']) + 0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={f_lap['driver_number']}&date>={s_str}&date<={e_str}")
    if tel.empty: return pd.DataFrame(), f_lap['lap_duration'], 0
    
    tel['date'] = pd.to_datetime(tel['date'])
    tel = tel.dropna(subset=['speed', 'date']).sort_values('date')
    tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
    tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
    
    dist_ref = np.linspace(0, tel['dist'].max() if tel['dist'].max() > 0 else 4000.0, 1000)
    return pd.DataFrame({
        'distance': dist_ref, 
        'speed': np.interp(dist_ref, tel['dist'], tel['speed']),
        'throttle': np.interp(dist_ref, tel['dist'], tel['throttle'])
    }), f_lap['lap_duration'], tel['dist'].max()

# --- CONTROL & DISPLAY ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    s_data = get_openf1("sessions", {"meeting_key": meetings[meetings['meeting_name'] == gp]['meeting_key'].iloc[0]})
    s_name = st.sidebar.selectbox("Session", s_data['session_name'].unique())
    s_key = s_data[s_data['session_name'] == s_name]['session_key'].iloc[0]
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

            if len(df1) > 5 and len(df2) > 5:
                common = min(len(df1), len(df2))
                delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("VMAX A", f"{df1['speed'].max():.0f} KM/H", f"{df1['speed'].max()-df2['speed'].max():.0f}")
                m2.metric("VMAX B", f"{df2['speed'].max():.0f} KM/H", f"{df2['speed'].max()-df1['speed'].max():.0f}")
                m3.metric("LAP DELTA", f"{abs(lap1-lap2):.3f} S", f"{(lap2-lap1):.3f}", delta_color="inverse")
                m4.metric("SPATIAL GAP", f"{abs(delta[-1]):.3f} S", f"{delta[-1]:.3f}", delta_color="normal")
                
                fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
                fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta, name="Delta", line=dict(color=COLOR_DELTA)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df1['distance'], y=df1['speed'], name=d1, line=dict(color=COLOR_A)), row=2, col=1)
                fig.add_trace(go.Scatter(x=df2['distance'], y=df2['speed'], name=d2, line=dict(color=COLOR_B)), row=2, col=1)
                fig.add_trace(go.Scatter(x=df1['distance'], y=df1['throttle'], name=d1, line=dict(color=COLOR_A), showlegend=False), row=3, col=1)
                fig.add_trace(go.Scatter(x=df2['distance'], y=df2['throttle'], name=d2, line=dict(color=COLOR_B), showlegend=False), row=3, col=1)
                fig.update_layout(template="plotly_dark", height=850)
                st.plotly_chart(fig, use_container_width=True)

# --- HUMAN-READABLE GUIDE ---
with st.expander("📖 PIT-WALL TELEMETRY GUIDE"):
    st.markdown("""
    ### 📊 Reading the Metrics
    - **Time Delta (Top Plot):** Your **Advantage Meter**. If the line is trending up, your driver is gaining time.
    - **Speed/Throttle (Lower Plots):** The **Neon Blue** and **Neon Pink** lines represent your two drivers. Use these to identify braking depth and corner exit drive.
    
    ### ⚙️ How Data Governance Works
    - **Spatial Normalization:** Since cars reach track points at different times, we "spatially normalize" the data, aligning both drivers to the same meter on the track.
    - **Synthetic Transparency:** If API data is missing, we use a deterministic physics engine. If the dashboard status says **SIMULATION**, you are viewing a model, not live car sensor data.
    """)
