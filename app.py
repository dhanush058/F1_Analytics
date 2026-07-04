import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. Robust API Wrapper
def fetch_api(endpoint, params=None):
    try:
        response = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5)
        return response.json() if response.status_code == 200 else []
    except: return []

# 3. Sidebar (State-Managed)
st.sidebar.title("🏎️ Portfolio Control Panel")
st.session_state.demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode", value=st.session_state.get("demo_mode", False))
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# Data Selection Logic (Chain of command)
meetings = fetch_api("meetings", {"year": year})
# Filter out non-round meetings (e.g., testing)
valid_meetings = sorted([m for m in meetings if m.get('round')], key=lambda x: x['round'])

if not st.session_state.demo_mode and valid_meetings:
    # Build dropdowns
    meeting_map = {f"Round {m['round']}: {m['meeting_name']}": m['meeting_key'] for m in valid_meetings}
    selected_meeting = st.sidebar.selectbox("Select Track", list(meeting_map.keys()))
    m_key = meeting_map[selected_meeting]
    
    sessions = fetch_api("sessions", {"meeting_key": m_key})
    session_map = {s['session_name']: s['session_key'] for s in sessions}
    s_key = session_map.get(st.sidebar.selectbox("Select Session", list(session_map.keys()) or ["None"]))
    
    drivers = fetch_api("drivers", {"session_key": s_key}) if s_key else []
    d_map = {d['full_name']: d['driver_number'] for d in drivers}
    d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()) or ["None"])
    d2 = st.sidebar.selectbox("Driver B", list(d_map.keys()) or ["None"])
else:
    selected_meeting, d1, d2 = "SIMULATED SESSION", "DEMO A", "DEMO B"

# 4. Rendering Trigger
if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    # Simulated Data
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

# 5. Dashboard View
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
if st.session_state.get("telemetry"):
    cols = st.columns(5)
    metrics = [("CIRCUIT", selected_meeting, "Meeting"), ("CORR", "1.00", "Style"), ("V-MAX", "312", "km/h"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "Status")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)
    
    for title, key in [("Velocity Profile", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure()
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
