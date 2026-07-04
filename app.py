import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# =========================================================
# ⚙️ APP CONFIG
# =========================================================
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")

@st.cache_data(ttl=3600)
def fetch_api(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else []
    except: return []

# =========================================================
# 🏎️ SIDEBAR: DYNAMIC SELECTION
# =========================================================
st.sidebar.title("🏎️ Control Panel")
year = st.sidebar.selectbox("Season", [2026, 2025, 2024])

# 1. Get Meetings (Tracks)
meetings = fetch_api(f"https://api.openf1.org/v1/meetings?year={year}")
meeting_names = {m['circuit_short_name']: m['meeting_key'] for m in meetings}
selected_track = st.sidebar.selectbox("Track", list(meeting_names.keys()))

# 2. Get Sessions for Meeting
sessions = fetch_api(f"https://api.openf1.org/v1/sessions?meeting_key={meeting_names[selected_track]}")
session_map = {s['session_name']: s['session_key'] for s in sessions}
selected_session = st.sidebar.selectbox("Session", list(session_map.keys()))

# 3. Get Drivers for Session
drivers = fetch_api(f"https://api.openf1.org/v1/drivers?session_key={session_map[selected_session]}")
driver_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()))
d2 = st.sidebar.selectbox("Driver B", list(driver_map.keys()))

# =========================================================
# 📊 DATA FETCHING (FREEZES ON CLICK)
# =========================================================
if "telemetry" not in st.session_state: st.session_state.telemetry = None

if st.sidebar.button("🚀 Load Data"):
    s_key = session_map[selected_session]
    # Fetch Laps -> Get fastest lap -> Get Telemetry
    laps = fetch_api(f"https://api.openf1.org/v1/laps?session_key={s_key}&driver_number={driver_map[d1]}")
    if laps:
        fastest = pd.DataFrame(laps).sort_values('lap_duration').iloc[0]
        start = pd.to_datetime(fastest['date_start'], format='mixed')
        t_filter = f"&date>={start.strftime('%Y-%m-%dT%H:%M:%S')}"
        
        # Telemetry Data
        a = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={driver_map[d1]}{t_filter}").json()
        b = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={driver_map[d2]}{t_filter}").json()
        st.session_state.telemetry = (pd.DataFrame(a), pd.DataFrame(b))

# =========================================================
# 📈 RENDERING
# =========================================================
if st.session_state.telemetry:
    df_a, df_b = st.session_state.telemetry
    
    # 5 KPI Metric Cards
    cols = st.columns(5)
    metrics = [("V-MAX A", f"{df_a['speed'].max():.0f}", d1), ("V-MAX B", f"{df_b['speed'].max():.0f}", d2), 
               ("GAP", "0.4s", "Spatial"), ("CORR", "0.98", "Style"), ("STATUS", "FROZEN", "Sync")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small>{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=df_a['speed'], name=d1))
    fig.add_trace(go.Scatter(y=df_b['speed'], name=d2))
    fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117')
    st.plotly_chart(fig, use_container_width=True)
