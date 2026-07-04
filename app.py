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

# 3. Dynamic Selection Chain
def fetch_api(endpoint, params=None):
    try: return requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5).json()
    except: return []

# Fetch Meetings
meetings = fetch_api("meetings", {"year": year})
valid_meetings = sorted([m for m in meetings if m.get('round')], key=lambda x: x['round'])

# Sidebar Selectors
selected_meeting = st.sidebar.selectbox("Select Track", [f"Round {m['round']}: {m['meeting_name']}" for m in valid_meetings] or ["No Data"])
m_key = next((m['meeting_key'] for m in valid_meetings if f"Round {m['round']}: {m['meeting_name']}" == selected_meeting), None)

sessions = fetch_api("sessions", {"meeting_key": m_key}) if m_key else []
selected_session = st.sidebar.selectbox("Select Session", [s['session_name'] for s in sessions] or ["No Data"])
s_key = next((s['session_key'] for s in sessions if s['session_name'] == selected_session), None)

drivers = fetch_api("drivers", {"session_key": s_key}) if s_key else []
driver_list = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(driver_list.keys()) or ["None"])
d2 = st.sidebar.selectbox("Driver B", list(driver_list.keys()) or ["None"])

# 4. Action Trigger (The Engine)
if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

# 5. UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

if st.session_state.telemetry:
    # 5 Metric Cards
    cols = st.columns(5)
    metrics = [("CIRCUIT", selected_meeting, "Meeting"), ("CORR", "1.00", "Style"), ("V-MAX", "312", "km/h"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "Status")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)
    
    # 3 Plots
    for title, key in [("Velocity Profile", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure()
        # Keep neon colors
        fig.add_trace(go.Scatter(y=st.session_state.telemetry[key][0] if key != 'delta' else st.session_state.telemetry[key], name=d1, line=dict(color='#00FFFF', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
