import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page & State Init
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

if "demo_mode" not in st.session_state: st.session_state.demo_mode = False
if "telemetry" not in st.session_state: st.session_state.telemetry = None

# 2. Sidebar Controls
st.sidebar.title("🏎️ Portfolio Control Panel")
st.session_state.demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode", value=st.session_state.demo_mode)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# Data Fetching Logic
def get_data(endpoint, params=None):
    try:
        url = f"https://api.openf1.org/v1/{endpoint}"
        return requests.get(url, params=params, timeout=5).json()
    except: return []

# 3. Dynamic Selection Chain
meetings = get_data("meetings", {"year": year})
meetings = sorted([m for m in meetings if m.get('round')], key=lambda x: x['round'])

meeting_map = {f"Round {m['round']}: {m['meeting_name']}": m['meeting_key'] for m in meetings}
selected_meeting = st.sidebar.selectbox("Select Track", list(meeting_map.keys()) or ["None"])
m_key = meeting_map.get(selected_meeting)

sessions = get_data("sessions", {"meeting_key": m_key}) if m_key else []
session_map = {s['session_name']: s['session_key'] for s in sessions}
session_name = st.sidebar.selectbox("Select Session", list(session_map.keys()) or ["None"])
s_key = session_map.get(session_name)

drivers = get_data("drivers", {"session_key": s_key}) if s_key else []
driver_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_map.keys()) or ["None"])
d2 = st.sidebar.selectbox("Driver B", list(driver_map.keys()) or ["None"])

# 4. Action Trigger
if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    # This is where your API logic for car_data goes
    st.session_state.telemetry = True # Placeholder for actual data

# 5. UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

if st.session_state.telemetry:
    # Metrics
    cols = st.columns(5)
    metrics = [("CIRCUIT", selected_meeting, "Meeting"), ("CORR", "1.00", "Style"), ("V-MAX", "312", "km/h"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "Status")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)
    
    # Plots
    for title in ["Velocity Profile (Speed)", "Throttle Map", "Delta Time (Gap)"]:
        st.write(f"### {title}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
