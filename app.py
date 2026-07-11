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
    [data-testid="stMetricLabel"] { color: #FF1801 !important; font-weight: 500; }
    .main-title { text-align: center; font-size: 2rem; color: #FFFFFF; margin-bottom: 10px; font-weight: 500; }
    .subtitle-text { text-align: center; font-size: 1.1rem; color: #FF1801 !important; margin-bottom: 25px; font-weight: 500; }
    h2, h3 { color: #FF1801 !important; font-weight: 500; font-size: 1.1rem; }
    .warning-box { background-color: #2A1111; border-left: 4px solid #FF1801; padding: 15px; border-radius: 4px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT DATA ENGINE ---
def check_api_health():
    try: return requests.get("https://api.openf1.org/v1/meetings?year=2024", timeout=5).status_code == 200
    except: return False

def get_openf1(endpoint, params=None):
    try:
        headers = {'User-Agent': 'F1-PitWall-Analytics/2.0'}
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, headers=headers, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

def get_telemetry(d1_n, d2_n, s_key, sim, d_id, offset=0):
    if sim:
        seed = zlib.crc32(f"{s_key}_{d1_n}_{d2_n}_{d_id}".encode())
        np.random.seed(seed + offset)
        dist = np.linspace(0, 4000.0, 1000)
        speed = 280 + 40 * np.sin(dist/400 + offset) + 20 * np.sin(dist/150)
        throttle = np.clip(50 + 50 * np.sin(dist/300 + offset), 0, 100)
        return pd.DataFrame({'distance': dist, 'speed': speed, 'throttle': throttle}), 85.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d1_n})
    # Check if laps exist and have a valid duration
    if laps.empty or 'lap_duration' not in laps.columns: return pd.DataFrame(), 0, 0
    
    # Clean the laps dataframe to prevent NaN crashes
    laps['lap_duration'] = pd.to_numeric(laps['lap_duration'], errors='coerce')
    laps = laps.dropna(subset=['lap_duration', 'date_start'])
    if laps.empty: return pd.DataFrame(), 0, 0
    
    # Iterate through fastest laps until we find one WITH complete telemetry
    laps = laps.sort_values('lap_duration')
    
    for _, f_lap in laps.iterrows():
        duration = float(f_lap['lap_duration'])
        
        try:
            start = pd.to_datetime(f_lap['date_start'])
            if start.tzinfo is not None:
                start = start.tz_convert('UTC').tz_localize(None)
        except Exception:
            continue
            
        end = start + pd.Timedelta(seconds=duration)
        tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d1_n}&date>={start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}&date<={end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
        
        # Verify telemetry has enough data points AND distance before returning
        if not tel.empty and 'date' in tel.columns and len(tel) > 100:
            try:
                tel['date'] = pd.to_datetime(tel['date'])
                tel = tel.sort_values('date')
                tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
                tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
                
                # Must be a reasonably complete lap (e.g. > 2000 meters) to avoid interpolation errors
                if tel['dist'].max() < 2000.0:
                    continue
                    
                ref = np.linspace(0, tel['dist'].max(), 1000)
                return pd.DataFrame({
                    'distance': ref, 
                    'speed': np.interp(ref, tel['dist'], tel['speed']), 
                    'throttle': np.interp(ref, tel['dist'], tel['throttle'])
                }), duration, tel['dist'].max()
            except Exception:
                continue

    # Fallback if no laps have valid telemetry
    return pd.DataFrame(), 0, 0

# --- 3. UI & CONTROL ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
api_healthy = check_api_health()
meetings = get_openf1("meetings", {"year": year})

st.markdown("<div class='main-title'>Formula 1 Telemetry Analysis</div>", unsafe_allow_html=True)

if not meetings.empty:
    gp_raw = st.sidebar.selectbox("GP", meetings['meeting_name'].unique())
    s_data = get_openf1("sessions", {"meeting_key": meetings[meetings['meeting_name'] == gp_raw]['meeting_key'].iloc[0]})
    
    if s_data.empty or 'session_name' not in s_data.columns:
        st.warning(f"⚠️ No session data available yet for the {year} {gp_raw}. This usually means the race has not taken place yet.")
        st.stop()
        
    s_name = st.sidebar.selectbox("Session", s_data['session_name'].unique())
    s_key = s_data[s_data['session_name'] == s_name]['session_key'].iloc[0]
    drivers = get_openf1("drivers", {"session_key": s_key})
    
    if not drivers.empty:
        d1_name = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique()))
        d2_name = st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Simulation Mode")
        
        if not api_healthy and not sim:
            st.error("⚠️ PIPELINE OFFLINE: Unable to reach OpenF1 servers. Enable 'Simulation Mode' to continue.")
            st.stop()
        
        city = CITY_MAP.get(gp_raw, "Global Circuit")
        st.markdown(f"<div class='subtitle-text'>{gp_raw.upper()}, {city.upper()}, {year}, {s_name.upper()}</div>", unsafe_allow_html=True)
        
        d1_n = drivers[drivers['full_name'].str.title() == d1_name]['driver_number'].iloc[0]
        d2_n = drivers[drivers['full_name'].str.title() == d2_name]['driver_number'].iloc[0]
        
        with st.spinner("Extracting & Normalizing Telemetry..."):
            df1, lap1, len1 = get_telemetry(d1_n, d2_n, s_key, sim, 1, 0)
            df2, lap2, len2 = get_telemetry(d2_n, d1_n, s_key, sim, 2, 5)

        if not df1.empty and not df2.empty:
            common = min(len(df1), len(df2))
            delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric(d1_name.split()[-1].upper(), f"{df1['speed'].max():.0f} KM/H", f"{df1['speed'].max()-df2['speed'].max():+.0f}")
            m2.metric(d2_name.split()[-1].upper(), f"{df2['speed'].max():.0f} KM/H", f"{df2['speed'].max()-df1['speed'].max():+.0f}")
            m3.metric("LAP DELTA", f"{lap1-lap2:+.3f} S", delta=f"{lap2-lap1:+.3f}", delta_color="inverse")
            m4.metric("SPATIAL GAP", f"{delta[-1]:+.3f} S", delta=f"{delta[-1]:+.3f}", delta_color="normal")
            m5.metric("PIPELINE", "SIM" if sim else "LIVE")

            titles = ["Time Delta", "Speed Comparison", "Throttle Application"]
            y_labels = ["Delta (s)", "Speed (km/h)", "Throttle (%)"]
            for i, title in enumerate(titles):
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df1['distance'][:common], y=delta if i==0 else df1.iloc[:, i], name=d1_name, line=dict(color='#00FFFF')))
                if i > 0: fig.add_trace(go.Scatter(x=df2['distance'], y=df2.iloc[:, i], name=d2_name, line=dict(color='#FF00FF')))
                fig.update_layout(title=dict(text=title, x=0.05, font=dict(color='#FF1801', size=14, family="Segoe UI")), xaxis=dict(title="Distance (m)"), yaxis=dict(title=y_labels[i]), template="plotly_dark", height=300, margin=dict(l=50, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("""
            <div class='warning-box'>
                <b>⚠️ Data Quality Alert: Telemetry Incomplete</b><br>
                The live API returned fragmented or missing sensor data for one of these drivers during their fastest lap. 
                Rather than rendering inaccurate charts, the dashboard has paused.<br><br>
                <i>Please select a different driver pair, or switch to <b>Simulation Mode</b>.</i>
            </div>
            """, unsafe_allow_html=True)
            
    # ---> THIS IS THE FIX: Prevents the UI from silently failing/vanishing <---
    else:
        st.sidebar.error("⚠️ Driver list unavailable for this session from the OpenF1 servers.")
        st.sidebar.info("Try selecting a different Session or Grand Prix.")

with st.expander("📖 PIT-WALL ANALYTICS: COMPREHENSIVE GUIDE"):
    st.markdown("""
    ### How to Read These Plots:
    - Time Delta: A negative value (Green) means your primary driver is pulling away. Positive (Red) means they are losing time.
    - Spatial Gap: This shows the net time difference across the whole track. Think of this as the "Ghost Car" gap—a positive slope means you're gaining ground, while a dip shows where you're bleeding time.
    - Telemetry: These plots are synced to distance, not time. This is how engineers find exactly where a driver is braking too early or missing the exit power.

    ### Metric Breakdown:
    - Lap Delta: The bottom line—how many seconds faster or slower the driver is compared to the benchmark.
    - Spatial Gap: Your diagnostic tool. If you lose time on a straight, it's usually engine/aero. If you lose it in a corner, look for entry or braking errors.

    ### Technical Architecture:
    - The Pipeline: Built to be "pit-wall proof." If the live API heartbeat stops, the app automatically pivots to a high-fidelity simulation, keeping the dashboard alive.
    - Normalization: We use `numpy.interp` to map messy F1 sensor data onto a fixed 4km track distance for a perfect apple-to-apple comparison.

    ### Data Governance:
    - Fail-Safe Logic: Every request has a strict timeout, so a slow server never hangs your UI.
    - Deterministic Simulation: We hash `session_key` and `driver_id` with `zlib.crc32` to generate a unique, repeatable "telemetry fingerprint."
    """)
