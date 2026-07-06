import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & NOTIFICATIONS ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Fastest Lap")

# Top-Middle Pop-up Notification for Recruiter
if "toast_shown" not in st.session_state:
    st.toast("⚠️ Recruiter Note: F1's API frequently blocks cloud IPs (DataNotLoadedError). Use the 'Simulation Mode' toggle in the right panel to test the dashboard's data processing logic and visualization capabilities if real data drops.", icon="🚨")
    st.session_state.toast_shown = True

# --- 2. API HELPER ---
@st.cache_data(ttl=3600)
def get_openf1(endpoint, params):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=12)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except Exception: 
        return pd.DataFrame()

# --- 3. SIDEBAR CONFIGURATION (Right Panel Concept) ---
st.sidebar.title("🏎️ Session Config")
st.sidebar.info("Toggle Simulation Mode if live API data is blocked by host.")
sim_mode = st.sidebar.checkbox("Simulation Mode", value=False)

year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

# Meetings (Filtering out Pre-Season Testing & Ordering chronologically)
meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    # Filter testing and ensure chronological order based on meeting key
    meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)]
    meetings = meetings.sort_values(by="meeting_key")
    
    selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]
else:
    st.error("API error: Could not fetch meetings.")
    st.stop()

# Sessions
sessions = get_openf1("sessions", {"meeting_key": m_key})
if not sessions.empty:
    selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
    s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]
else:
    st.error("API error: Could not fetch sessions.")
    st.stop()

# Drivers
drivers = get_openf1("drivers", {"session_key": s_key})
if not drivers.empty:
    drivers = drivers.dropna(subset=['full_name'])
    driver_names = drivers['full_name'].unique()
    d1 = st.sidebar.selectbox("Driver A", driver_names, index=0)
    d2 = st.sidebar.selectbox("Ref Driver", driver_names, index=min(1, len(driver_names)-1))
else:
    st.error("API error: Could not fetch drivers.")
    st.stop()

# --- 4. TELEMETRY & LAP LOGIC ---
def get_fastest_lap_telemetry(driver_name, s_key, gp_name, session_name):
    # SIMULATION MODE: Generates unique, accurate-looking curves for each driver/track combination
    if sim_mode:
        seed_string = f"{driver_name}_{gp_name}_{session_name}"
        seed = sum(ord(c) for c in seed_string)
        np.random.seed(seed)
        
        distance = np.linspace(0, 5000, 800)
        # Create a unique track profile
        base_speed = 200 + 40 * np.sin(distance / 300) + 50 * np.cos(distance / 150 + seed)
        speed = np.clip(base_speed + np.random.normal(0, 3, 800), 70, 345)
        
        # Throttle tied to speed acceleration zones
        throttle = np.clip(((speed - 80) / 265) * 100 + np.random.normal(0, 8, 800), 0, 100)
        throttle = np.where(throttle > 88, 100, throttle) # Simulating full throttle
        
        mock_lap_time = 85.0 + np.random.uniform(-1.5, 1.5)
        return pd.DataFrame({'distance': distance, 'speed': speed, 'throttle': throttle}), mock_lap_time

    # LIVE API MODE: Specific Fastest Lap Retrieval
    d_num = drivers[drivers['full_name'] == driver_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns:
        return pd.DataFrame(), None
        
    # Find shortest lap
    laps['lap_duration'] = pd.to_numeric(laps['lap_duration'], errors='coerce')
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
        
    fastest = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    start_time = pd.to_datetime(fastest['date_start'])
    end_time = start_time + pd.Timedelta(seconds=fastest['lap_duration'])
    
    # Query car data strictly within the boundaries of the fastest lap
    car_data = get_openf1("car_data", {
        "session_key": s_key, 
        "driver_number": d_num, 
        "date>=": start_time.isoformat(), 
        "date<=": end_time.isoformat()
    })
    
    if car_data.empty: return pd.DataFrame(), fastest['lap_duration']
        
    # Process Telemetry
    car_data['speed'] = pd.to_numeric(car_data['speed'], errors='coerce')
    car_data['throttle'] = pd.to_numeric(car_data['throttle'], errors='coerce')
    car_data = car_data.dropna(subset=['speed', 'throttle'])
    
    if not car_data.empty:
        car_data['distance'] = np.linspace(0, 5000, len(car_data)) # Normalize for plotting
        
    return car_data, fastest['lap_duration']

with st.spinner("Analyzing fastest laps..."):
    df_a, lap_time_a = get_fastest_lap_telemetry(d1, s_key, selected_gp, selected_session)
    df_b, lap_time_b = get_fastest_lap_telemetry(d2, s_key, selected_gp, selected_session)

# --- 5. DASHBOARD & PLOTTING ---
if not df_a.empty and not df_b.empty:
    st.title(f"Fastest Lap Analysis: {selected_gp}")
    
    # 5 Metric Cards (3 Quant, 2 Qual/Info)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("MAX VEL", f"{df_a['speed'].max():.0f} km/h", d1)
    c2.metric("MAX VEL", f"{df_b['speed'].max():.0f} km/h", d2)
    
    # Calculate Max Spatial Gap (Time Delta Peak)
    x_len = min(len(df_a), len(df_b))
    dist = df_a['distance'].iloc[:x_len].values
    s_a = np.where(df_a['speed'].iloc[:x_len].values < 1, 1, df_a['speed'].iloc[:x_len].values) / 3.6 # m/s
    s_b = np.where(df_b['speed'].iloc[:x_len].values < 1, 1, df_b['speed'].iloc[:x_len].values) / 3.6 # m/s
    
    # Mathematical integration to find delta time over distance
    d_dist = dist[1] - dist[0] if len(dist) > 1 else 1
    t_a = np.cumsum(d_dist / s_a)
    t_b = np.cumsum(d_dist / s_b)
    delta_time = t_b - t_a
    
    max_gap = np.max(np.abs(delta_time))
    c3.metric("MAX SPATIAL GAP", f"{max_gap:.3f} s")
    c4.metric("TRACK LEN", "~5.0 km", selected_gp)
    c5.metric("FASTEST LAP", f"{lap_time_a:.3f}s" if lap_time_a else "N/A", d1)

    # Plots (Neon F1 Theme)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Time Delta (s) [Ref - Driver A]", "Speed (km/h)", "Throttle (%)"),
                        vertical_spacing=0.06)
    
    # Row 1: Delta
    fig.add_trace(go.Scatter(x=dist, y=delta_time, name="Delta (s)", line=dict(color='white')), row=1, col=1)
    
    # Row 2: Speed
    fig.add_trace(go.Scatter(x=dist, y=s_a * 3.6, name=d1, line=dict(color='#00FFFF')), row=2, col=1)
    fig.add_trace(go.Scatter(x=dist, y=s_b * 3.6, name=d2, line=dict(color='#FF00FF')), row=2, col=1)
    
    # Row 3: Throttle (Norris lines will clearly show now due to proper interpolation length)
    fig.add_trace(go.Scatter(x=dist, y=df_a['throttle'].iloc[:x_len], name=d1, line=dict(color='#00FFFF'), showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=dist, y=df_b['throttle'].iloc[:x_len], name=d2, line=dict(color='#FF00FF'), showlegend=False), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=900, paper_bgcolor="#050505", plot_bgcolor="#050505", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Incomplete lap telemetry for this combination. Please enable 'Simulation Mode' in the sidebar.")

# --- 6. GUIDE ---
with st.expander("📖 Telemetry Guide & Methodology"):
    st.write("""
    * **Time Delta Plot:** Calculates the cumulative time difference through mathematical integration of speed over distance. A climbing line means Driver A is gaining time.
    * **Throttle Execution:** Identifies exactly when a driver transitions from braking to throttle. A steeper throttle curve indicates higher confidence and grip on corner exit.
    * **Braking Zones:** Sharp, immediate drops in the speed trace indicate heavy braking. The bottom of the 'V' shape is the corner apex speed.
    """)
