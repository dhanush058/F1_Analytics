import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="F1 Fastest Lap Analysis")

# Top-Middle Notification for Recruiter
st.toast("🚨 Note: Live API data may be blocked by hosting providers. Enable 'Simulation Mode' to view telemetry profiles.", icon="⚠️")

# --- API HELPERS ---
@st.cache_data(ttl=3600)
def fetch_data(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.title("Configuration")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)

# Select GP and Session
meetings = fetch_data("meetings", {"year": 2026})
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = fetch_data("sessions", {"meeting_key": m_key})
selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]

# Select Drivers
drivers = fetch_data("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'].unique())
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'].unique())

# --- DATA PROCESSING ENGINE ---
def get_fastest_lap_telemetry(driver_name, s_key):
    if sim_mode:
        # Generate stable mock data for demonstration
        dist = np.linspace(0, 5000, 500)
        return pd.DataFrame({'distance': dist, 'speed': 250 + 50*np.sin(dist/200), 'throttle': 50 + 50*np.sin(dist/500)}), 85.0
    
    d_num = drivers[drivers['full_name'] == driver_name]['driver_number'].iloc[0]
    
    # 1. Get Fastest Lap
    laps = fetch_data("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), None
    fastest = laps.loc[laps['lap_duration'].idxmin()]
    
    # 2. Query Telemetry within lap time boundaries
    start = fastest['date_start']
    end = pd.to_datetime(start) + pd.Timedelta(seconds=fastest['lap_duration'])
    
    tel = fetch_data("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": start, "date<=": end.isoformat()})
    if tel.empty: return pd.DataFrame(), fastest['lap_duration']
    
    # Normalize for plotting
    tel['distance'] = np.linspace(0, 5000, len(tel))
    return tel, fastest['lap_duration']

# Fetch
df_a, lap_a = get_fastest_lap_telemetry(d1, s_key)
df_b, lap_b = get_fastest_lap_telemetry(d2, s_key)

# --- VISUALIZATION ---
if not df_a.empty and not df_b.empty:
    st.title(f"Fastest Lap Analysis: {selected_gp}")
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Max Speed A", f"{df_a['speed'].max():.0f} km/h")
    c2.metric("Max Speed B", f"{df_b['speed'].max():.0f} km/h")
    c3.metric("Lap Time A", f"{lap_a:.3f} s")
    c4.metric("Lap Time B", f"{lap_b:.3f} s")

    # Plot
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Time Delta", "Speed (km/h)", "Throttle (%)"))
    
    # Delta (interpolation required for matching distance arrays)
    delta = np.interp(df_a['distance'], df_b['distance'], df_b['speed']) - df_a['speed']
    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta, name="Delta"), row=1, col=1)
    
    # Speed & Throttle
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=d1), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=d2), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=800)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Telemetry data not found for these drivers in this session.")
