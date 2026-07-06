import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide", page_title="F1 Analytics")

# --- UI NOTIFICATION ---
# Use toast for a clean, professional notification at the top
if "toast_shown" not in st.session_state:
    st.toast("⚠️ Recruiter Note: F1 API restrictions may affect live data. Use 'Simulation Mode' to verify dashboard logic.", icon="🚨")
    st.session_state.toast_shown = True

# --- API HELPER ---
@st.cache_data(ttl=3600)
def get_openf1(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("Configuration")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)

year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = get_openf1("meetings", {"year": year})

# Filter out "Testing" sessions
if not meetings.empty:
    meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False)]
    selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]
else:
    st.error("No meeting data found.")
    st.stop()

sessions = get_openf1("sessions", {"meeting_key": m_key})
selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]

drivers = get_openf1("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'].unique())
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'].unique())

# --- DATA PROCESSING ---
def get_fastest_lap_telemetry(driver_name, s_key):
    if sim_mode:
        # Unique simulation per driver to avoid identical plots
        seed = hash(driver_name) % 1000
        np.random.seed(seed)
        dist = np.linspace(0, 5000, 500)
        return pd.DataFrame({'distance': dist, 'speed': 250 + 50*np.sin(dist/200 + seed), 'throttle': 50 + 40*np.sin(dist/500 + seed)}), 85.0
    
    d_num = drivers[drivers['full_name'] == driver_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), None
    
    fastest = laps.loc[laps['lap_duration'].idxmin()]
    start = fastest['date_start']
    end = pd.to_datetime(start) + pd.Timedelta(seconds=fastest['lap_duration'])
    
    tel = get_openf1("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": start, "date<=": end.isoformat()})
    if tel.empty: return pd.DataFrame(), fastest['lap_duration']
    
    tel['distance'] = np.linspace(0, 5000, len(tel))
    return tel, fastest['lap_duration']

df_a, lap_a = get_fastest_lap_telemetry(d1, s_key)
df_b, lap_b = get_fastest_lap_telemetry(d2, s_key)

# --- VISUALIZATION ---
if not df_a.empty and not df_b.empty:
    st.title(f"Fastest Lap: {selected_gp}")
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Max Speed A", f"{df_a['speed'].max():.0f} km/h")
    c2.metric("Max Speed B", f"{df_b['speed'].max():.0f} km/h")
    c3.metric("Lap Time Diff", f"{abs(lap_a - lap_b):.3f} s")

    fig = make_subplots(rows=2, cols=1, subplot_titles=("Speed (km/h)", "Throttle (%)"))
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=d1, line=dict(color='#00FFFF')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=d2, line=dict(color='#FF00FF')), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Telemetry data not found. Please enable 'Simulation Mode'.")
