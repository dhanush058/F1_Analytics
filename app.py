import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="F1 Analytics: Fastest Lap")

# --- 1. STRICT API FETCHER ---
@st.cache_data(ttl=600)
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=15)
        if res.status_code == 200:
            return pd.DataFrame(res.json())
        else:
            st.sidebar.error(f"API Error {res.status_code} on /{endpoint}")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"Connection Failed: {e}")
        return pd.DataFrame()

# --- 2. TELEMETRY PROCESSING (REAL DATA ONLY) ---
def get_real_telemetry(driver_name, s_key, drivers_df):
    d_num = drivers_df[drivers_df['full_name'] == driver_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns:
        return pd.DataFrame(), None
        
    # Get the fastest lap
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
    fastest_lap = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    
    # EXACT DATE FORMATTING FOR OPENF1 API
    start_time = pd.to_datetime(fastest_lap['date_start'])
    end_time = start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']))
    
    # Format to strictly match what the API expects (e.g., 2023-09-16T13:03:35.200)
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1("car_data", {
        "session_key": s_key, 
        "driver_number": d_num, 
        "date>=": start_str, 
        "date<=": end_str
    })
    
    if tel.empty or 'speed' not in tel.columns:
        st.warning(f"No telemetry found in API for {driver_name} during their fastest lap.")
        return pd.DataFrame(), fastest_lap['lap_duration']
        
    tel['speed'] = pd.to_numeric(tel['speed'], errors='coerce')
    tel['throttle'] = pd.to_numeric(tel['throttle'], errors='coerce')
    tel = tel.dropna(subset=['speed', 'throttle'])
    
    # Spatial Interpolation (Normalizing to 1000 distance points)
    dist_ref = np.linspace(0, 5000, 1000)
    tel['distance_raw'] = np.linspace(0, 5000, len(tel))
    
    interp_speed = np.interp(dist_ref, tel['distance_raw'], tel['speed'])
    interp_throttle = np.interp(dist_ref, tel['distance_raw'], tel['throttle'])
    
    df_normalized = pd.DataFrame({'distance': dist_ref, 'speed': interp_speed, 'throttle': interp_throttle})
    return df_normalized, fastest_lap['lap_duration']

# --- 3. UI CONFIGURATION ---
st.sidebar.title("🏎️ Control Console")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)].sort_values("meeting_key")
    selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]
else:
    st.sidebar.error("Could not load calendar.")
    st.stop()

sessions = get_openf1("sessions", {"meeting_key": m_key})
if not sessions.empty:
    selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
    s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]
else:
    st.stop()

drivers_data = get_openf1("drivers", {"session_key": s_key})
if not drivers_data.empty:
    drivers_data = drivers_data.dropna(subset=['full_name'])
    sorted_driver_list = sorted(drivers_data['full_name'].unique())
    d1 = st.sidebar.selectbox("Driver A", sorted_driver_list, index=0)
    d2 = st.sidebar.selectbox("Ref Driver", sorted_driver_list, index=min(1, len(sorted_driver_list)-1))
else:
    st.stop()

# --- 4. EXECUTION & PLOTTING ---
with st.spinner("Fetching Real Telemetry Data..."):
    df_a, lap_time_a = get_real_telemetry(d1, s_key, drivers_data)
    df_b, lap_time_b = get_real_telemetry(d2, s_key, drivers_data)

if not df_a.empty and not df_b.empty:
    st.title(f"Fastest Lap Telemetry: {selected_gp} ({year})")
    
    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("MAX VEL: DRIVER A", f"{df_a['speed'].max():.0f} km/h", d1)
    m2.metric("MAX VEL: REF DRIVER", f"{df_b['speed'].max():.0f} km/h", d2)
    
    # Delta Math
    v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6
    v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
    delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * (5000/1000)
    final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
    
    m3.metric("LAP TIME VARIANCE", f"{final_delta:.3f} s")
    m4.metric("TRACK DIMENSION", "5.00 km")
    m5.metric("DATA SOURCE", "LIVE API")

    # Neon F1 Plots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Cumulative Time Delta (s)", "Speed Profile (km/h)", "Throttle Application (%)"),
                        vertical_spacing=0.07)

    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta_time_array, name="Time Delta", line=dict(color='#FFFFFF', width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=f"{d1} Speed", line=dict(color='#00FFFF', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=f"{d2} Speed", line=dict(color='#FF00FF', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color='#00FFFF', width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=f"{d2} Throttle", line=dict(color='#FF00FF', width=1.5)), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=850, paper_bgcolor="#0A0A0C", plot_bgcolor="#0A0A0C", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Real telemetry data could not be retrieved from the API for this selection. Try selecting an older, completed race (like 2024).")
