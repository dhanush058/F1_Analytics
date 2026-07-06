import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Live Analytics")

# --- SIDEBAR: RECRUITER NOTIFICATION ---
st.sidebar.title("Configuration")
with st.sidebar.expander("⚠️ System Status", expanded=True):
    st.warning("Live API data may be blocked by F1 hosting restrictions. If plots fail, enable 'Simulation Mode' to view telemetry profiles.")

use_sim = st.sidebar.checkbox("Enable Simulation Mode", value=False)

# --- DATA ENGINE ---
@st.cache_data(ttl=60)
def fetch_openf1(endpoint, params=None):
    base = "https://api.openf1.org/v1/"
    try:
        response = requests.get(base + endpoint, params=params, timeout=5)
        return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- SELECTIONS ---
meetings = fetch_openf1("meetings", {"year": 2026})
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'])
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = fetch_openf1("sessions", {"meeting_key": m_key})
s_key = sessions['session_key'].iloc[0]

drivers = fetch_openf1("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'])
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'])

# --- MOCK ENGINE (Ensures Standout Visuals) ---
def get_data(name):
    if use_sim:
        # Generate unique telemetry profiles based on driver name seed
        seed = sum([ord(c) for c in name])
        np.random.seed(seed)
        x = np.linspace(0, 5000, 1000)
        speed = 200 + 100 * np.sin(x/200) + np.random.normal(0, 5, 1000)
        throttle = 50 + 50 * np.sin(x/500)
        return pd.DataFrame({'speed': speed, 'throttle': throttle})
    
    # Live fetch logic
    d_num = drivers[drivers['full_name'] == name]['driver_number'].iloc[0]
    tel = fetch_openf1("car_data", {"session_key": s_key, "driver_number": d_num})
    return tel[['speed', 'throttle']] if not tel.empty else pd.DataFrame()

# --- MAIN DASHBOARD ---
df_a, df_b = get_data(d1), get_data(d2)

if not df_a.empty and not df_b.empty:
    st.title(f"Telemetry: {d1} vs {d2}")
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Max Speed A", f"{df_a['speed'].max():.0f} km/h")
    c2.metric("Max Speed B", f"{df_b['speed'].max():.0f} km/h")
    c3.metric("Speed Delta", f"{abs(df_a['speed'].max() - df_b['speed'].max()):.1f} km/h")

    # Neon Plots
    fig = make_subplots(rows=2, cols=1, subplot_titles=("Speed Profile", "Throttle Response"))
    fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_a['throttle'], name=d1, line=dict(color='#00FFFF')), row=2, col=1)
    fig.add_trace(go.Scatter(y=df_b['throttle'], name=d2, line=dict(color='#FF00FF')), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, paper_bgcolor="#050505")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("No data available. Enable 'Simulation Mode' to generate telemetry.")
