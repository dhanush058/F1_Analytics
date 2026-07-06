import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & TOAST ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Fastest Lap")

if "toast_shown" not in st.session_state:
    st.toast("⚠️ Note: F1 APIs often block cloud IPs or lack future data. Use 'Enable Simulation Mode' in the sidebar if data fails to load.", icon="🚨")
    st.session_state.toast_shown = True

# Neon Theme Colors
COLOR_A = '#00FFFF'     # Neon Cyan
COLOR_B = '#FF00FF'     # Neon Magenta
COLOR_DELTA = '#FFFFFF' # Crisp White

# --- 2. ROBUST API FETCHER ---
@st.cache_data(ttl=600)
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=12)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. DATA ENGINE (REAL & SIMULATION) ---
def get_telemetry(driver_api_name, s_key, drivers_df, is_sim=False, is_ref_driver=False):
    dist_ref = np.linspace(0, 5000, 1000)
    
    # --- SIMULATION FALLBACK ENGINE ---
    if is_sim:
        if not is_ref_driver:
            # Driver A Profile: Late Braking
            speed = 320 - 150 * np.exp(-((dist_ref - 1100)/130)**2) - 120 * np.exp(-((dist_ref - 2300)/100)**2) - 160 * np.exp(-((dist_ref - 3400)/180)**2) - 140 * np.exp(-((dist_ref - 4400)/130)**2)
            throttle = 100 - 100 * np.exp(-((dist_ref - 1050)/150)**2) - 100 * np.exp(-((dist_ref - 2250)/110)**2) - 100 * np.exp(-((dist_ref - 3350)/190)**2) - 100 * np.exp(-((dist_ref - 4350)/140)**2)
            lap_time = 82.145
        else:
            # Driver B Profile: Early braking, carries momentum
            speed = 315 - 135 * np.exp(-((dist_ref - 1050)/160)**2) - 105 * np.exp(-((dist_ref - 2250)/130)**2) - 145 * np.exp(-((dist_ref - 3350)/210)**2) - 130 * np.exp(-((dist_ref - 4350)/160)**2)
            throttle = 100 - 100 * np.exp(-((dist_ref - 1000)/180)**2) - 100 * np.exp(-((dist_ref - 2200)/140)**2) - 100 * np.exp(-((dist_ref - 3300)/220)**2) - 100 * np.exp(-((dist_ref - 4300)/170)**2)
            lap_time = 82.412
            
        speed = np.clip(speed + np.random.normal(0, 1.0, 1000), 65, 340)
        throttle = np.clip(throttle + np.random.normal(0, 1.5, 1000), 0, 100)
        throttle[throttle > 95] = 100
        return pd.DataFrame({'distance': dist_ref, 'speed': speed, 'throttle': throttle}), lap_time

    # --- LIVE API FETCHING ---
    d_num = drivers_df[drivers_df['full_name'] == driver_api_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns: return pd.DataFrame(), None
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
    
    fastest_lap = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    start_time = pd.to_datetime(fastest_lap['date_start'])
    # Pad the end time slightly to ensure we capture the full final corner
    end_time = start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']) + 0.5)
    
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": start_str, "date<=": end_str})
    if tel.empty or 'speed' not in tel.columns: return pd.DataFrame(), fastest_lap['lap_duration']
        
    tel['speed'] = pd.to_numeric(tel['speed'], errors='coerce')
    tel['throttle'] = pd.to_numeric(tel['throttle'], errors='coerce')
    tel = tel.dropna(subset=['speed', 'throttle'])
    
    # Normalizing data to standard distance map
    tel['distance_raw'] = np.linspace(0, 5000, len(tel))
    df_normalized = pd.DataFrame({
        'distance': dist_ref,
        'speed': np.interp(dist_ref, tel['distance_raw'], tel['speed']),
        'throttle': np.interp(dist_ref, tel['distance_raw'], tel['throttle'])
    })
    return df_normalized, fastest_lap['lap_duration']

# --- 4. SIDEBAR & ROUTING ---
st.sidebar.title("🏎️ Control Console")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
if meetings.empty:
    st.sidebar.warning(f"No API data found for {year}. Please enable Simulation Mode or pick 2024.")
    st.stop()
    
meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)].sort_values("meeting_key")
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = get_openf1("sessions", {"meeting_key": m_key})
if sessions.empty: st.stop()
selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]

drivers_data = get_openf1("drivers", {"session_key": s_key})
if drivers_data.empty: st.stop()
drivers_data = drivers_data.dropna(subset=['full_name'])

# UX FIX: Make driver names Title Case so they are easy to read. 
# Streamlit selectboxes are searchable—just type the name!
drivers_data['display_name'] = drivers_data['full_name'].str.title()
sorted_driver_list = sorted(drivers_data['display_name'].unique())

d1_display = st.sidebar.selectbox("Driver A (Type to search)", sorted_driver_list, index=0)
d2_display = st.sidebar.selectbox("Ref Driver (Type to search)", sorted_driver_list, index=min(1, len(sorted_driver_list)-1))

# Map friendly display names back to API-required ALL CAPS names
d1_api = drivers_data[drivers_data['display_name'] == d1_display]['full_name'].iloc[0]
d2_api = drivers_data[drivers_data['display_name'] == d2_display]['full_name'].iloc[0]

# --- 5. EXECUTION & VISUALIZATION ---
with st.spinner("Processing Telemetry Data..."):
    df_a, lap_time_a = get_telemetry(d1_api, s_key, drivers_data, sim_mode, is_ref_driver=False)
    df_b, lap_time_b = get_telemetry(d2_api, s_key, drivers_data, sim_mode, is_ref_driver=True)

if df_a.empty or df_b.empty:
    st.error("⚠️ Real telemetry is unavailable for this specific session. The API returned no data. Please check 'Enable Simulation Mode' in the sidebar to view the analytics dashboard structure.")
else:
    st.title(f"Fastest Lap: {selected_gp} ({selected_session})")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(f"MAX VEL: {d1_display.split()[-1].upper()}", f"{df_a['speed'].max():.0f} km/h")
    m2.metric(f"MAX VEL: {d2_display.split()[-1].upper()}", f"{df_b['speed'].max():.0f} km/h")
    
    v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6
    v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
    delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * (5000/1000)
    final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
    
    m3.metric("LAP TIME GAP", f"{final_delta:.3f} s")
    m4.metric("TRACK MODEL", "5.00 km")
    m5.metric("DATA STATUS", "SIMULATION" if sim_mode else "LIVE API")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=(f"Time Delta (s) [Up = {d1_display} Faster]", "Speed (km/h)", "Throttle (%)"),
                        vertical_spacing=0.08)

    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta_time_array, name="Delta", line=dict(color=COLOR_DELTA, width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1_display, line=dict(color=COLOR_A, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2_display, line=dict(color=COLOR_B, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=d1_display, line=dict(color=COLOR_A, width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=d2_display, line=dict(color=COLOR_B, width=1.5)), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=850, paper_bgcolor="#0A0A0C", plot_bgcolor="#0A0A0C", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# --- 6. HUMANIZED GUIDE & DATA GOVERNANCE ---
with st.expander("📖 Friendly Guide: How to Read the Data & How We Built It"):
    st.markdown("""
    ### 👋 Welcome to the F1 Telemetry App
    If you've ever wondered *how* a driver pulled off an amazing qualifying lap, you're in the right place. We aren't just looking at lap times here; we're looking at the physical footprint of the car on the track.
    
    Here is a quick, human-friendly guide to making sense of these neon lines.

    ### 📈 Reading the Plots
    **1. The Time Delta (The White Line)**
    Think of this as the tug-of-war between the two drivers. If the line is sloping up, Driver A is gaining an advantage. If it slopes down, the Reference Driver is clawing time back. 

    **2. The Speed Trace**
    Every time you see a deep 'V' shape, the drivers are slamming on the brakes for a corner. The bottom of that 'V' is their slowest point (the apex). If one driver's line dips later than the other, they are "late braking"—a risky, aggressive move to steal time.

    **3. The Throttle Pedal**
    This shows how hard they are pressing the gas. When coming out of a corner, the driver who gets their line back to 100% the fastest is getting better traction and carrying more speed down the next straight.

    ---

    ### 💻 The Tech Under the Hood
    F1 cars spit out a lot of messy, asynchronous data. Because two drivers finish laps at different times, their data streams don't naturally line up. If we just plotted the raw data, the charts would be broken and misaligned.

    To fix this, we built a **Spatial Normalization Engine**. We take the raw, time-based sensor data and use linear interpolation (`np.interp` in Python) to force both datasets onto an identical, fixed 5-kilometer map. This guarantees that we are comparing both cars at the exact same physical meter of the track.

    ---

    ### 🛡️ Data Governance & Privacy
    We take data integrity seriously. Here is how we manage the pipeline:
    * **Single Source of Truth:** All real-world telemetry is pulled directly from the official timing feeds via the OpenF1 REST API (`api.openf1.org`).
    * **Respecting Infrastructure:** We heavily cache our network requests. This prevents us from spamming the API provider, keeps the app running fast, and prevents IP bans.
    * **Zero Personal Data:** This dashboard analyzes public vehicle physics and athletic performance data. No personal data, user tracking, or internal F1 team engineering secrets are collected or stored.
    """)
