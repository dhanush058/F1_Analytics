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
        background-color: #15151C !important;
        border: 1px solid #2A2A35 !important;
        border-top: 4px solid #FF1801 !important;
        border-radius: 4px !important;
        padding: 10px 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricLabel"] { 
        color: #8E8E9F !important; font-family: 'Courier New', monospace !important; 
        font-size: 0.75rem !important; text-transform: uppercase !important; letter-spacing: 1px !important;
    }
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; font-family: 'Courier New', monospace !important; 
        font-size: 1.35rem !important; font-weight: 800 !important; 
    }
    h1, h2, h3, h4 { font-family: 'Courier New', monospace !important; color: #FFFFFF !important; letter-spacing: 1px !important; }
</style>
""", unsafe_allow_html=True)

COLOR_A, COLOR_B, COLOR_DELTA, COLOR_BG = '#00FFFF', '#FF00FF', '#00FF00', '#0B0B0E'

# --- 2. ROBUST API FETCHER ---
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    headers = {"User-Agent": "F1-Telemetry-Dashboard/1.0", "Accept": "application/json"}
    try:
        res = requests.get(base_url + endpoint, params=params, headers=headers, timeout=45)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- 3. DATA ENGINE ---
def get_telemetry(driver_api_name, s_key, drivers_df, track_name, session_name, year, is_sim=False, driver_id=1):
    if is_sim:
        track_uid = f"{year}_{track_name}_{s_key}"
        driver_uid = f"{year}_{track_name}_{s_key}_{driver_api_name}_{driver_id}"
        track_seed = zlib.crc32(track_uid.encode('utf-8')) & 0xffffffff
        driver_seed = zlib.crc32(driver_uid.encode('utf-8')) & 0xffffffff
        np.random.seed(track_seed)
        dist_ref = np.linspace(0, 4000.0, 1000)
        np.random.seed(driver_seed)
        speed = np.full(1000, 290.0 + (driver_seed % 6) - 3)
        throttle = np.full(1000, 100.0)
        return pd.DataFrame({'distance': dist_ref, 'speed': speed, 'throttle': throttle}), 90.0, 4000.0

    try:
        d_num = int(drivers_df[drivers_df['full_name'] == driver_api_name]['driver_number'].iloc[0])
    except: return pd.DataFrame(), None, 0

    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), None, 0
    fastest_lap = laps.loc[laps['lap_duration'].idxmin()]
    
    start_time = pd.to_datetime(fastest_lap['date_start']).tz_convert('UTC').tz_localize(None)
    start_str = (start_time - pd.Timedelta(seconds=0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    end_str = (start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']) + 0.5)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d_num}&date>={start_str}&date<={end_str}")
    if tel.empty: return pd.DataFrame(), fastest_lap['lap_duration'], 0
        
    tel['speed'] = pd.to_numeric(tel['speed'], errors='coerce')
    tel['throttle'] = pd.to_numeric(tel['throttle'], errors='coerce')
    tel = tel.dropna(subset=['speed', 'throttle', 'date']).sort_values('date')
    tel['dt'] = pd.to_datetime(tel['date']).diff().dt.total_seconds().fillna(0.0)
    tel['distance_raw'] = ((tel['speed'] / 3.6) * tel['dt']).cumsum()
    
    track_length = tel['distance_raw'].max()
    dist_ref = np.linspace(0, track_length if track_length > 0 else 4000.0, 1000)
    
    return pd.DataFrame({
        'distance': dist_ref,
        'speed': np.interp(dist_ref, tel['distance_raw'], tel['speed']),
        'throttle': np.interp(dist_ref, tel['distance_raw'], tel['throttle'])
    }), fastest_lap['lap_duration'], track_length

# --- 4. CONTROL & DISPLAY ---
st.sidebar.title("🏎️ Control Console")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]
    sessions = get_openf1("sessions", {"meeting_key": m_key})
    if not sessions.empty:
        selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
        s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]
        drivers_data = get_openf1("drivers", {"session_key": s_key})
        
        if not drivers_data.empty:
            d1_display = st.sidebar.selectbox("Driver A", sorted(drivers_data['full_name'].str.title().unique()), index=0)
            d2_display = st.sidebar.selectbox("Ref Driver", sorted(drivers_data['full_name'].str.title().unique()), index=1)
            d1_api = drivers_data[drivers_data['full_name'].str.title() == d1_display]['full_name'].iloc[0]
            d2_api = drivers_data[drivers_data['full_name'].str.title() == d2_display]['full_name'].iloc[0]

            with st.spinner("Analyzing..."):
                df_a, lap_a, len_a = get_telemetry(d1_api, s_key, drivers_data, selected_gp, selected_session, year, sim_mode, driver_id=1)
                df_b, lap_b, len_b = get_telemetry(d2_api, s_key, drivers_data, selected_gp, selected_session, year, sim_mode, driver_id=2)

            if not df_a.empty and not df_b.empty and len(df_a) > 1 and len(df_b) > 1:
                st.markdown(f"## F1 TELEMETRY ANALYSIS\n#### {selected_gp} — {selected_session}")
                
                # Spatial Gap Calculation
                common_len = min(len(df_a), len(df_b))
                v_a, v_b = df_a['speed'].values[:common_len] / 3.6, df_b['speed'].values[:common_len] / 3.6
                delta_arr = np.cumsum((1 / v_b) - (1 / v_a)) * (max(len_a, len_b)/common_len)
                
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("VMAX — A", f"{df_a['speed'].max():.0f} KM/H")
                m2.metric("VMAX — B", f"{df_b['speed'].max():.0f} KM/H")
                m3.metric("LAP TIME DELTA", f"{abs(lap_a - lap_b):.3f} S")
                m4.metric("MAX SPATIAL GAP", f"{abs(delta_arr[-1]):.3f} S")
                m5.metric("PIPELINE", "SIM" if sim_mode else "LIVE")
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
                fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1_display, line=dict(color=COLOR_A)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2_display, line=dict(color=COLOR_B)), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_a['distance'][:common_len], y=delta_arr, name="Time Delta", line=dict(color=COLOR_DELTA)), row=2, col=1)
                fig.update_layout(template="plotly_dark", height=700)
                st.plotly_chart(fig, use_container_width=True)
            else: st.error("⚠️ Telemetry offline. Check Simulation Mode.")
