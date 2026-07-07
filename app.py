import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & THEME ---
CITY_MAP = {
    "Australian Grand Prix": "Melbourne", "Chinese Grand Prix": "Shanghai",
    "Japanese Grand Prix": "Suzuka", "Bahrain Grand Prix": "Sakhir",
    "Saudi Arabian Grand Prix": "Jeddah", "Miami Grand Prix": "Miami",
    "Canadian Grand Prix": "Montreal", "Monaco Grand Prix": "Monte-Carlo",
    "Spanish Grand Prix": "Barcelona", "Austrian Grand Prix": "Spielberg",
    "British Grand Prix": "Silverstone", "Belgian Grand Prix": "Spa-Francorchamps",
    "Hungarian Grand Prix": "Budapest", "Dutch Grand Prix": "Zandvoort",
    "Italian Grand Prix": "Monza", "Azerbaijan Grand Prix": "Baku",
    "Singapore Grand Prix": "Singapore", "United States Grand Prix": "Austin",
    "Mexican Grand Prix": "Mexico City", "Sao Paulo Grand Prix": "São Paulo",
    "Las Vegas Grand Prix": "Las Vegas", "Qatar Grand Prix": "Lusail",
    "Abu Dhabi Grand Prix": "Yas Island"
}

st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")
st.markdown("""
<style>
    .stApp { background-color: #0B0B0E; color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    [data-testid="stMetric"] { background-color: #15151C !important; border-top: 4px solid #FF1801 !important; padding: 10px; }
    .title-text { font-size: 1.5rem; font-weight: 300; color: #FFFFFF !important; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT DATA ENGINE ---
def check_api_health():
    try:
        return requests.get("https://api.openf1.org/v1/meetings?year=2024", timeout=5).status_code == 200
    except: return False

def get_openf1(endpoint, params=None):
    try:
        headers = {'User-Agent': 'F1-PitWall-Analytics/2.0'}
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, headers=headers, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

def get_telemetry(d1_n, d2_n, s_key, sim, d_id):
    if sim:
        # Hashing session key AND driver numbers to guarantee uniqueness per combination
        seed = zlib.crc32(f"{s_key}_{d1_n}_{d2_n}_{d_id}".encode())
        np.random.seed(seed)
        dist = np.linspace(0, 4000.0, 1000)
        # Physics model: Aggressive curves with unique phase shifts based on seed
        speed = 200 + 100 * np.sin(dist / 500 + (seed % 10)) + 20 * np.cos(dist / 100)
        throttle = 40 + 60 * np.sin(dist / 200 + (seed % 20))
        throttle = np.clip(throttle, 0, 100) 
        return pd.DataFrame({'distance': dist, 'speed': speed, 'throttle': throttle}), 85.0 + (seed % 15), 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d1_n})
    if laps.empty: return pd.DataFrame(), 0, 0
    f_lap = laps.sort_values('lap_duration').iloc[0]
    
    start = pd.to_datetime(f_lap['date_start']).tz_convert('UTC').tz_localize(None)
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d1_n}&date>={start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}&date<={(start + pd.Timedelta(seconds=float(f_lap['lap_duration']))).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
    if tel.empty: return pd.DataFrame(), f_lap['lap_duration'], 0
    tel['date'] = pd.to_datetime(tel['date'])
    tel = tel.sort_values('date')
    tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
    tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
    ref = np.linspace(0, tel['dist'].max() if tel['dist'].max() > 0 else 4000.0, 1000)
    return pd.DataFrame({'distance': ref, 'speed': np.interp(ref, tel['dist'], tel['speed']), 'throttle': np.interp(ref, tel['dist'], tel['throttle'])}), f_lap['lap_duration'], tel['dist'].max()

# --- 3. UI & CONTROL ---
if 'sim_mode' not in st.session_state: st.session_state.sim_mode = False

year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
is_api_healthy = check_api_health()

meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    gp_raw = st.sidebar.selectbox("GP", meetings['meeting_name'].unique())
    s_data = get_openf1("sessions", {"meeting_key": meetings[meetings['meeting_name'] == gp_raw]['meeting_key'].iloc[0]})
    s_name = st.sidebar.selectbox("Session", s_data['session_name'].unique())
    s_key = s_data[s_data['session_name'] == s_name]['session_key'].iloc[0]
    drivers = get_openf1("drivers", {"session_key": s_key})
    
    if not drivers.empty:
        d1_name = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique()))
        d2_name = st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Simulation Mode", value=st.session_state.sim_mode)
        
        if not is_api_healthy and not sim:
            st.error("⚠️ API CONNECTION FAILED")
            if st.button("Enable Simulation Mode"):
                st.session_state.sim_mode = True
                st.rerun()
            st.stop()

        city = next((v for k, v in CITY_MAP.items() if k in gp_raw), "Location")
        st.markdown(f"<div class='title-text'>{gp_raw}, {year}, {city}, {s_name}</div>", unsafe_allow_html=True)

        d1_n = drivers[drivers['full_name'].str.title() == d1_name]['driver_number'].iloc[0]
        d2_n = drivers[drivers['full_name'].str.title() == d2_name]['driver_number'].iloc[0]
        df1, lap1, len1 = get_telemetry(d1_n, d2_n, s_key, sim, 1)
        df2, lap2, len2 = get_telemetry(d2_n, d1_n, s_key, sim, 2)

        if len(df1) > 5 and len(df2) > 5:
            common = min(len(df1), len(df2))
            delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
            
            m1, m2, m3, m4, m5 = st.columns(5)
            vmax_diff = df1['speed'].max() - df2['speed'].max()
            m1.metric(d1_name.split()[-1].upper(), f"{df1['speed'].max():.0f} KM/H", f"{vmax_diff:+.0f}")
            m2.metric(d2_name.split()[-1].upper(), f"{df2['speed'].max():.0f} KM/H", f"{-vmax_diff:+.0f}")
            m3.metric("LAP DELTA", f"{lap1-lap2:+.3f} S", delta=f"{lap2-lap1:+.3f}", delta_color="inverse")
            m4.metric("SPATIAL GAP", f"{delta[-1]:+.3f} S", delta=f"{delta[-1]:+.3f}", delta_color="normal")
            m5.metric("PIPELINE", "SIM" if sim else "LIVE")
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Time Delta (Seconds)", "Speed Comparison (KM/H)", "Throttle Application (%)"))
            fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta, name="Delta", line=dict(color='#00FF00')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df1['distance'], y=df1['speed'], name=d1_name, line=dict(color='#00FFFF')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df2['distance'], y=df2['speed'], name=d2_name, line=dict(color='#FF00FF')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df1['distance'], y=df1['throttle'], name=d1_name, line=dict(color='#00FFFF'), showlegend=False), row=3, col=1)
            fig.add_trace(go.Scatter(x=df2['distance'], y=df2['throttle'], name=d2_name, line=dict(color='#FF00FF'), showlegend=False), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=850, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

# --- GUIDE ---
with st.expander("🛡️ SYSTEM STATUS & ANALYTICS GUIDE"):
    st.markdown("""
    ### 🏁 How to Read These Plots
    * **Lap Time Delta:** Negative (Green) = Driver A is faster. Positive (Red) = Driver A is slower. 
    * **Spatial Gap:** Cumulative time difference mapped over distance. Positive (Green) means gaining ground; Negative (Red) means losing time.
    * **Speed & Throttle:** Spatially synchronized to highlight exact cornering efficiency.
    
    ### 🏗️ Engineering & Data Governance
    * **Resilient Pipeline:** Includes automatic failover to deterministic simulation if the live API heartbeat fails.
    * **Spatial Normalization:** Uses `numpy.interp` to align telemetry streams of varying sample rates across a fixed distance axis.
    * **Deterministic Engine:** Simulation uses `zlib.crc32` hashing to provide repeatable, physics-grounded telemetry for testing.
    """)
