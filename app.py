import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

# --- 2. DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=15)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- 3. UI SIDEBAR ---
st.sidebar.title("Configuration")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = fetch_api("meetings", {"year": year})
meeting_map = {m['meeting_name']: m['meeting_key'] for m in meetings}
selected_gp = st.sidebar.selectbox("Grand Prix", list(meeting_map.keys()))

sessions = fetch_api("sessions", {"meeting_key": meeting_map[selected_gp]})
session_map = {s['session_name']: s['session_key'] for s in sessions}
selected_session = st.sidebar.selectbox("Session", list(session_map.keys()))

s_key = session_map[selected_session]
drivers = fetch_api("drivers", {"session_key": s_key})
driver_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()))
d2 = st.sidebar.selectbox("Ref Driver", list(driver_map.keys()))

# --- 4. DATA PROCESSING ---
def get_tel(name):
    d_num = driver_map[name]
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    valid = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
    if not valid: return pd.DataFrame()
    
    fastest = min(valid, key=lambda x: x['lap_duration'])
    tel = fetch_api("car_data", {"session_key": s_key, "driver_number": d_num})
    df = pd.DataFrame(tel)
    if df.empty or 'date' not in df.columns: return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'], utc=True, errors='coerce')
    return df[(df['date'] >= pd.to_datetime(fastest['date_start'], utc=True)) & 
              (df['date'] <= pd.to_datetime(fastest['date_end'], utc=True))]

# --- 5. MAIN APP ---
st.title("🏎️ F1 Telemetry Analysis")
if st.sidebar.button("Generate Analysis"):
    with st.spinner("Fetching data..."):
        df_a, df_b = get_tel(d1), get_tel(d2)

    if not df_a.empty and not df_b.empty:
        # Metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("MAX VEL A", f"{df_a['speed'].max():.0f} km/h")
        c2.metric("AVG THR A", f"{df_a['throttle'].mean():.0f}%")
        c3.metric("MAX GAP", f"{abs(df_a['speed'].max()-df_b['speed'].max()):.1f} km/h")
        c4.metric("GEAR A", f"{df_a['n_gear'].mode()[0]}")
        c5.metric("RPM A", f"{df_a['rpm'].mean():.0f}")

        # Plots
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle"), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed']-df_b['speed'], name="Delta"), row=3, col=1)
        fig.update_layout(template="plotly_dark", height=800)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📖 Guide"):
            st.write("This dashboard compares the fastest lap of two drivers. If 'No data found' appears, the API has not yet released telemetry for this session.")
    else:
        st.error("No telemetry data found for selected drivers.")
