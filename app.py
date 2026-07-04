import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# 🎨 UI & THEME CONFIGURATION
# =========================================================
st.set_page_config(page_title="F1 Analytics Vault", layout="wide", page_icon="🏎️")

# CSS for F1 Look
st.markdown("""
    <style>
    .metric-card { background-color: #151922; border-left: 5px solid #FF0000; padding: 15px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# ⚙️ STATE MANAGEMENT & API
# =========================================================
if "telemetry" not in st.session_state:
    st.session_state.telemetry = None

@st.cache_data(ttl=3600)
def fetch_api(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except: return None

# =========================================================
# 🏎️ SIDEBAR & METADATA
# =========================================================
st.sidebar.title("🏎️ Control Panel")
year = st.sidebar.selectbox("Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Track", "Melbourne")
# Add your other dropdowns here...

# =========================================================
# 📊 DATA ENGINE (EXECUTES ONLY ONCE)
# =========================================================
if st.sidebar.button("🚀 Load / Refresh Data"):
    with st.spinner("Synchronizing with F1 Servers..."):
        # Resolve Session
        sessions = fetch_api(f"https://api.openf1.org/v1/sessions?year={year}")
        s_key = next((s['session_key'] for s in sessions if track.lower() in s['location'].lower()), None)
        
        if s_key:
            drivers = fetch_api(f"https://api.openf1.org/v1/drivers?session_key={s_key}")
            if drivers:
                d1, d2 = drivers[0]['driver_number'], drivers[1]['driver_number']
                laps = fetch_api(f"https://api.openf1.org/v1/laps?session_key={s_key}&driver_number={d1}")
                
                # Telemetry Logic (with mixed format)
                fastest = pd.DataFrame(laps).sort_values('lap_duration').iloc[0]
                start = pd.to_datetime(fastest['date_start'], format='mixed')
                end = start + pd.Timedelta(seconds=float(fastest['lap_duration']))
                t_filter = f"&date>={start.strftime('%Y-%m-%dT%H:%M:%S')}&date<={end.strftime('%Y-%m-%dT%H:%M:%S')}"
                
                a = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={d1}{t_filter}").json()
                b = requests.get(f"https://api.openf1.org/v1/car_data?session_key={s_key}&driver_number={d2}{t_filter}").json()
                st.session_state.telemetry = (pd.DataFrame(a), pd.DataFrame(b))
        else:
            st.sidebar.error("Session not found.")

# =========================================================
# 📈 FROZEN RENDER ENGINE (NO DIMMING)
# =========================================================
if st.session_state.telemetry is not None:
    df_a, df_b = st.session_state.telemetry
    
    # Metric Cards
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><h4>🏎️ Driver A</h4><p>Max Speed: {df_a["speed"].max():.0f} km/h</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><h4>🏎️ Driver B</h4><p>Max Speed: {df_b["speed"].max():.0f} km/h</p></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><h4>⏱️ Status</h4><p>Data Frozen/Synchronized</p></div>', unsafe_allow_html=True)
    
    # Plotly Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=df_a['speed'], name="Driver A Speed", line=dict(color='#00FFFF')))
    fig.add_trace(go.Scatter(y=df_b['speed'], name="Driver B Speed", line=dict(color='#FF00FF')))
    fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select parameters and click 'Load / Refresh Data' to begin analysis.")
