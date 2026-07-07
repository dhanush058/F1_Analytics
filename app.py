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
    [data-testid="stMetric"] { background-color: #15151C !important; border-top: 4px solid #FF1801 !important; padding: 15px; }
    .title-text { font-size: 1.5rem; font-weight: 300; color: #FFFFFF !important; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT DATA ENGINE ---
def get_openf1(endpoint, params=None):
    try:
        headers = {'User-Agent': 'F1-PitWall-Analytics/2.0'}
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, headers=headers, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

def get_fastest_lap_telemetry(d_num, s_key, sim, d_id, offset=0):
    if sim:
        seed = zlib.crc32(f"{s_key}_{d_num}_{d_id}".encode())
        np.random.seed(seed + offset)
        dist = np.linspace(0, 4000.0, 1000)
        speed = 280 + 40 * np.sin(dist/400 + offset) + 20 * np.sin(dist/150)
        throttle = np.clip(50 + 50 * np.sin(dist/300 + offset), 0, 100)
        return pd.DataFrame({'distance': dist, 'speed': speed, 'throttle': throttle}), 85.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), 0, 0
    f_lap = laps.sort_values('lap_duration').iloc[0]
    
    start = pd.to_datetime(f_lap['date_start']).tz_convert('UTC').tz_localize(None)
    end = start + pd.Timedelta(seconds=float(f_lap['lap_duration']))
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d_num}&date>={start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}&date<={end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
    
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
        d1_name = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique()))
        d2_name = st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Simulation Mode")
        
        d1_n = drivers[drivers['full_name'].str.title() == d1_name]['driver_number'].iloc[0]
        d2_n = drivers[drivers['full_name'].str.title() == d2_name]['driver_number'].iloc[0]
        
        df1, lap1, len1 = get_fastest_lap_telemetry(d1_n, s_key, sim, 1, 0)
        df2, lap2, len2 = get_fastest_lap_telemetry(d2_n, s_key, sim, 2, 5)

        common = min(len(df1), len(df2))
        delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
        vmax_diff = df1['speed'].max() - df2['speed'].max()

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(d1_name.split()[-1].upper(), f"{df1['speed'].max():.0f} KM/H", f"{vmax_diff:+.0f}")
        m2.metric(d2_name.split()[-1].upper(), f"{df2['speed'].max():.0f} KM/H", f"{-vmax_diff:+.0f}")
        m3.metric("LAP DELTA", f"{lap1-lap2:+.3f} S", delta=f"{lap2-lap1:+.3f}", delta_color="inverse")
        m4.metric("SPATIAL GAP", f"{delta[-1]:+.3f} S", delta=f"{delta[-1]:+.3f}", delta_color="normal")
        m5.metric("PIPELINE", "SIM" if sim else "LIVE")

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Time Delta", "Speed Comparison (KM/H)", "Throttle Application (%)"))
        fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta, name="Delta", line=dict(color='#00FF00')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df1['distance'], y=df1['speed'], name=d1_name, line=dict(color='#00FFFF')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df2['distance'], y=df2['speed'], name=d2_name, line=dict(color='#FF00FF')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df1['distance'], y=df1['throttle'], name=d1_name, line=dict(color='#00FFFF'), showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df2['distance'], y=df2['throttle'], name=d2_name, line=dict(color='#FF00FF'), showlegend=False), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=850)
        st.plotly_chart(fig, use_container_width=True)

# --- GUIDE ---
with st.expander("🛡️ SYSTEM STATUS & ANALYTICS GUIDE"):
    st.markdown("""
    ### 🧠 Data Interpretation
    - **Lap Time Delta:** Green indicates Driver A is faster. Red indicates they are slower.
    - **Spatial Gap:** Indicates net gain/loss over the track length.
    - **Normalization:** Telemetry is resampled using linear interpolation across a shared 4km distance axis.
    """)
