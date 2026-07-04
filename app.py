import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Config & State
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

if "telemetry" not in st.session_state: st.session_state.telemetry = None
if "demo_mode" not in st.session_state: st.session_state.demo_mode = False

# 2. Sidebar Command Center
st.sidebar.title("🏎️ Portfolio Control Panel")
st.session_state.demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode", value=st.session_state.demo_mode)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# Data Fetching
@st.dialog("API Unavailable")
def error_dialog():
    st.warning("API connection failed. Switching to Simulation Mode will allow you to continue.")
    if st.button("Load Simulation Data"):
        st.session_state.demo_mode = True
        st.rerun()

# Logic to populate meetings
meetings_sorted = []
if not st.session_state.demo_mode:
    try:
        response = requests.get(f"https://api.openf1.org/v1/meetings?year={year}", timeout=3)
        if response.status_code == 200:
            data = response.json()
            meetings_sorted = sorted([m for m in data if m.get('round')], key=lambda x: x['round'])
    except: error_dialog()

if meetings_sorted:
    meeting_options = {f"Round {m['round']}: {m.get('meeting_name', 'GP')}": m['meeting_key'] for m in meetings_sorted}
    selected_meeting = st.sidebar.selectbox("Select Track", list(meeting_options.keys()))
    m_key = meeting_options[selected_meeting]
else:
    selected_meeting = "SIMULATED TRACK"
    m_key = None

# 3. UI Rendering (The Frozen Skeleton)
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    # Logic to populate data
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

if st.session_state.telemetry:
    # 5 KPI Cards
    cols = st.columns(5)
    metrics = [("CIRCUIT", selected_meeting.split(': ')[-1][:10], "Location"), ("CORR", "1.00", "Style"), 
               ("V-MAX", "312 km/h", "DRIVER A"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "Status")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

    # Plots
    for title, key in [("Velocity Profile (Speed)", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure()
        if key == 'delta':
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key], name="Gap", line=dict(color='#FFFF00', width=2)))
        else:
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key][0], name="A", line=dict(color='#00FFFF', width=2)))
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key][1], name="B", line=dict(color='#FF00FF', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
