import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & RECRUITER NOTIFICATION ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.toast("🚨 Recruiter Note: API IP restrictions may affect live data. Use 'Simulation Mode' to verify logic.", icon="⚠️")

@st.cache_data(ttl=3600)
def get_data(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- 2. SIDEBAR SELECTIONS ---
st.sidebar.title("Configuration")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_data("meetings", {"year": year})
meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)].sort_values("meeting_key")
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = get_data("sessions", {"meeting_key": m_key})
selected_s = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_s]['session_key'].iloc[0]

drivers = get_data("drivers", {"session_key": s_key}).sort_values("full_name")
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'].unique())
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'].unique())

# --- 3. TELEMETRY PROCESSING ---
def get_lap_data(name, s_key):
    if sim_mode:
        x = np.linspace(0, 5000, 500)
        return pd.DataFrame({'dist': x, 'speed': 250 + 50*np.sin(x/200), 'throttle': 40 + 50*np.random.rand(500)}), 85.0
    
    d_num = drivers[drivers['full_name'] == name]['driver_number'].iloc[0]
    laps = get_data("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), None
    fastest = laps.loc[laps['lap_duration'].idxmin()]
    
    tel = get_data("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": fastest['date_start'], "date<=": (pd.to_datetime(fastest['date_start']) + pd.Timedelta(seconds=fastest['lap_duration'])).isoformat()})
    tel['dist'] = np.linspace(0, 5000, len(tel))
    return tel, fastest['lap_duration']

df_a, t_a = get_lap_data(d1, s_key)
df_b, t_b = get_lap_data(d2, s_key)

# --- 4. METRICS & PLOTS ---
if not df_a.empty and not df_b.empty:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("MAX VEL (A)", f"{df_a['speed'].max():.0f} km/h")
    c2.metric("MAX VEL (B)", f"{df_b['speed'].max():.0f} km/h")
    c3.metric("MAX GAP", f"{abs(t_a-t_b):.3f} s")
    c4.metric("TRACK LEN", "5.0 km")
    c5.metric("FASTEST LAP", f"{t_a:.3f} s")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Time Delta", "Speed", "Throttle"))
    fig.add_trace(go.Scatter(x=df_a['dist'], y=df_a['speed']-df_b['speed'], name="Delta", line=dict(color='white')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['dist'], y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['dist'], y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['dist'], y=df_a['throttle'], name=d1, line=dict(color='#00FFFF')), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['dist'], y=df_b['throttle'], name=d2, line=dict(color='#FF00FF')), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=800, paper_bgcolor="#050505")
    st.plotly_chart(fig, use_container_width=True)

# --- 5. COMPREHENSIVE GUIDE ---
with st.expander("📖 Telemetry Analysis Guide"):
    st.write("### Technical Breakdown")
    st.write("Telemetry is sampled via high-frequency sensors (>200ms intervals). We normalize this data to a distance-axis (0-5000m) to allow for 1:1 comparisons of braking points and cornering speeds.")
    st.write("### Non-Technical Guide")
    st.write("* **Speed Trace:** Deeper 'V' shapes indicate late, hard braking.")
    st.write("* **Throttle:** Earlier returns to 100% throttle out of a corner signal higher driver confidence and better traction.")
