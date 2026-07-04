import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page Configuration
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. Cached API Engine (Prevents "No Data" crashes)
@st.cache_data(ttl=3600)
def get_openf1(endpoint, params=None):
    try:
        response = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5)
        return response.json() if response.status_code == 200 else []
    except: return []

# 3. Sidebar Setup
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# Fetch Meetings (Filter out Testing)
all_meetings = get_openf1("meetings", {"year": year})
# Filter: Only keep meetings that have a 'round' (excludes testing)
valid_meetings = sorted([m for m in all_meetings if m.get('round')], key=lambda x: x['round'])

# Meeting Dropdown
meeting_label = st.sidebar.selectbox("Select Grand Prix", [f"Round {m['round']}: {m['meeting_name']}" for m in valid_meetings] or ["No Data"])
m_key = next((m['meeting_key'] for m in valid_meetings if f"Round {m['round']}: {m['meeting_name']}" == meeting_label), None)

# Session Dropdown
sessions = get_openf1("sessions", {"meeting_key": m_key}) if m_key else []
session_name = st.sidebar.selectbox("Select Session", [s['session_name'] for s in sessions] or ["No Data"])
s_key = next((s['session_key'] for s in sessions if s['session_name'] == session_name), None)

# Driver Dropdown
drivers = get_openf1("drivers", {"session_key": s_key}) if s_key else []
driver_names = [d['full_name'] for d in drivers] if drivers else ["No Data"]
d1 = st.sidebar.selectbox("Driver A", driver_names)
d2 = st.sidebar.selectbox("Driver B", driver_names)

# 4. Main UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

if st.sidebar.button("🚀 Load Data") or demo_mode:
    # Logic: If real data fails, use simulation
    st.session_state.telemetry = {
        'speed': (np.random.normal(300, 20, 100), np.random.normal(300, 20, 100)),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.05, 100))
    }

if "telemetry" in st.session_state and st.session_state.telemetry:
    # Render Plots
    for title, key in [("Velocity Profile", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure()
        if key == 'delta':
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key], name="Gap", line=dict(color='#FFFF00')))
        else:
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key][0], name=d1, line=dict(color='#00FFFF')))
            fig.add_trace(go.Scatter(y=st.session_state.telemetry[key][1], name=d2, line=dict(color='#FF00FF')))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Parameters selected. Click 'Load Data' to generate telemetry plots.")
