import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & DATA ENGINE ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("<style>.metric-card { background: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; }</style>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- 2. SIDEBAR SELECTION FLOW ---
st.sidebar.title("Configuration")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = fetch_api("meetings", {"year": year})
meeting_map = {m['meeting_name']: m['meeting_key'] for m in meetings}
selected_gp = st.sidebar.selectbox("Grand Prix", list(meeting_map.keys()))

# Session Select
sessions = fetch_api("sessions", {"meeting_key": meeting_map[selected_gp]})
session_map = {s['session_name']: s['session_key'] for s in sessions}
selected_session = st.sidebar.selectbox("Session", list(session_map.keys()))

# Driver Select
s_key = session_map[selected_session]
drivers = fetch_api("drivers", {"session_key": s_key})
driver_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()))
d2 = st.sidebar.selectbox("Ref Driver", list(driver_map.keys()))

# --- 3. DATA PROCESSING ---
def get_fastest_lap_tel(d_name, s_key):
    d_num = driver_map[d_name]
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start')]
    if not valid_laps: return pd.DataFrame()
    fastest = min(valid_laps, key=lambda x: x['lap_duration'])
    tel = fetch_api("car_data", {"session_key": s_key, "driver_number": d_num})
    df = pd.DataFrame(tel)
    if df.empty: return df
    df['date'] = pd.to_datetime(df['date'])
    return df[(df['date'] >= pd.to_datetime(fastest['date_start'])) & 
              (df['date'] <= pd.to_datetime(fastest['date_end']))]

# --- 4. MAIN DASHBOARD ---
if st.sidebar.button("Generate Analysis"):
    with st.spinner("Processing telemetry..."):
        df_a, df_b = get_fastest_lap_tel(d1, s_key), get_fastest_lap_tel(d2, s_key)

    if not df_a.empty and not df_b.empty:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f'<div class="metric-card">MAX VEL A<h3>{df_a["speed"].max():.0f}</h3></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card">AVG THR A<h3>{df_a["throttle"].mean():.0f}%</h3></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card">MAX GAP<h3>{abs(df_a["speed"].max()-df_b["speed"].max()):.1f}</h3></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card">GEAR A<h3>{df_a["n_gear"].mode()[0]}</h3></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-card">RPM A<h3>{df_a["rpm"].mean():.0f}</h3></div>', unsafe_allow_html=True)

        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle"), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed']-df_b['speed'], name="Speed Delta"), row=3, col=1)
        fig.update_layout(template="plotly_dark", height=800)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📖 Guide"):
            st.write("This dashboard pulls live telemetry from the OpenF1 API. Metrics are calculated based on the fastest completed lap.")
    else:
        st.error("No telemetry data found for selected session.")
