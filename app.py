import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & THEME ---
# Mapping GP names to their host cities
CITY_MAP = {
    "Australian Grand Prix": "Melbourne",
    "Chinese Grand Prix": "Shanghai",
    "Japanese Grand Prix": "Suzuka",
    "Bahrain Grand Prix": "Sakhir",
    "Saudi Arabian Grand Prix": "Jeddah",
    "Miami Grand Prix": "Miami",
    "Canadian Grand Prix": "Montreal",
    "Monaco Grand Prix": "Monte-Carlo",
    "Spanish Grand Prix": "Barcelona",
    "Austrian Grand Prix": "Spielberg",
    "British Grand Prix": "Silverstone",
    "Belgian Grand Prix": "Spa-Francorchamps",
    "Hungarian Grand Prix": "Budapest",
    "Dutch Grand Prix": "Zandvoort",
    "Italian Grand Prix": "Monza",
    "Azerbaijan Grand Prix": "Baku",
    "Singapore Grand Prix": "Singapore",
    "United States Grand Prix": "Austin",
    "Mexican Grand Prix": "Mexico City",
    "Sao Paulo Grand Prix": "São Paulo",
    "Las Vegas Grand Prix": "Las Vegas",
    "Qatar Grand Prix": "Lusail",
    "Abu Dhabi Grand Prix": "Yas Island"
}

st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")
st.markdown("""
<style>
    .stApp { background-color: #0B0B0E; color: #FFFFFF; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    [data-testid="stMetric"] { background-color: #15151C !important; border-top: 4px solid #FF1801 !important; padding: 15px; }
    .title-box { padding: 5px; border-left: 5px solid #FF1801; margin-bottom: 25px; padding-left: 15px; }
    h1 { font-family: 'Inter', sans-serif !important; font-weight: 800; font-size: 2.5rem; letter-spacing: -0.05em; color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA FETCHING ---
def get_openf1(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=45)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

def get_telemetry(d_num, s_key, year, sim, d_id):
    if sim:
        seed = zlib.crc32(f"{year}_{d_num}_{d_id}".encode())
        np.random.seed(seed)
        dist = np.linspace(0, 4000.0, 1000)
        return pd.DataFrame({'distance': dist, 'speed': 290.0+(seed%10), 'throttle': 100.0}), 90.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), 0, 0
    f_lap = laps.sort_values('lap_duration').iloc[0]
    
    start = pd.to_datetime(f_lap['date_start']).tz_convert('UTC').tz_localize(None)
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d_num}&date>={start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}&date<={(start + pd.Timedelta(seconds=float(f_lap['lap_duration']))).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
    if tel.empty: return pd.DataFrame(), f_lap['lap_duration'], 0
    
    tel['date'] = pd.to_datetime(tel['date'])
    tel = tel.sort_values('date')
    tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
    tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
    
    ref = np.linspace(0, tel['dist'].max() if tel['dist'].max() > 0 else 4000.0, 1000)
    return pd.DataFrame({'distance': ref, 'speed': np.interp(ref, tel['dist'], tel['speed']), 'throttle': np.interp(ref, tel['dist'], tel['throttle'])}), f_lap['lap_duration'], tel['dist'].max()

# --- 3. UI & CONTROL ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    gp_raw = st.sidebar.selectbox("GP", meetings['meeting_name'].unique())
    s_data = get_openf1("sessions", {"meeting_key": meetings[meetings['meeting_name'] == gp_raw]['meeting_key'].iloc[0]})
    s_name = st.sidebar.selectbox("Session", s_data['session_name'].unique())
    s_key = s_data[s_data['session_name'] == s_name]['session_key'].iloc[0]
    drivers = get_openf1("drivers", {"session_key": s_key})
    
    if not drivers.empty:
        d1, d2 = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique())), st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Simulation Mode")

        # Determine City
        city = next((v for k, v in CITY_MAP.items() if k in gp_raw), "Unknown City")
        st.markdown(f"<div class='title-box'><h1>{gp_raw} {year} | {city} | {s_name}</h1></div>", unsafe_allow_html=True)

        d1_n = drivers[drivers['full_name'].str.title()==d1]['driver_number'].iloc[0]
        d2_n = drivers[drivers['full_name'].str.title()==d2]['driver_number'].iloc[0]
        df1, lap1, len1 = get_telemetry(d1_n, s_key, year, sim, 1)
        df2, lap2, len2 = get_telemetry(d2_n, s_key, year, sim, 2)

        if len(df1) > 5 and len(df2) > 5:
            common = min(len(df1), len(df2))
            delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
            
            m1, m2, m3, m4, m5 = st.columns(5)
            lap_diff = lap1 - lap2
            m1.metric("VMAX A", f"{df1['speed'].max():.0f} KM/H")
            m2.metric("VMAX B", f"{df2['speed'].max():.0f} KM/H")
            m3.metric("LAP DELTA", f"{lap_diff:+.3f} S", delta=f"{-lap_diff:+.3f}", delta_color="inverse")
            m4.metric("SPATIAL GAP", f"{delta[-1]:+.3f} S", delta=f"{delta[-1]:+.3f}", delta_color="normal")
            m5.metric("PIPELINE", "SIM" if sim else "LIVE API")
            
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
            fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta, name="Delta", line=dict(color='#00FF00')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df1['distance'], y=df1['speed'], name=d1, line=dict(color='#00FFFF')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df2['distance'], y=df2['speed'], name=d2, line=dict(color='#FF00FF')), row=2, col=1)
            fig.add_trace(go.Scatter(x=df1['distance'], y=df1['throttle'], name=d1, line=dict(color='#00FFFF'), showlegend=False), row=3, col=1)
            fig.add_trace(go.Scatter(x=df2['distance'], y=df2['throttle'], name=d2, line=dict(color='#FF00FF'), showlegend=False), row=3, col=1)
            fig.update_layout(template="plotly_dark", height=850)
            st.plotly_chart(fig, use_container_width=True)

# --- GUIDE ---
with st.expander("📖 PIT-WALL ANALYTICS GUIDE"):
    st.markdown("""
    ### 🧠 How to Read These Metrics
    - **Lap Time Delta:** A **negative value (Green)** means Driver A is faster. A **positive value (Red)** means they are slower.
    - **Spatial Gap:** The cumulative time difference between drivers. **Positive (Green)** means Driver A is gaining time against the Reference driver; **Negative (Red)** means they are losing ground.
    - **Spatial Normalization:** Since cars cross the finish line at different times, we map data to **distance** so that we compare both drivers at the exact same physical meter on the track.
    - **Pipeline Status:** Indicates if you are viewing live race telemetry or our physics-based **Simulation Mode**.
    """)
