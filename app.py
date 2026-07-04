import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 1. State Init
if "demo_mode" not in st.session_state: st.session_state.demo_mode = False

# 2. Sidebar Command Center
st.sidebar.title("🏎️ Portfolio Control Panel")
st.session_state.demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode", value=st.session_state.demo_mode)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# 3. Fail-Safe Data Fetching
def get_dropdown_data(endpoint, key_filter=None):
    try:
        data = requests.get(f"https://api.openf1.org/v1/{endpoint}", timeout=3).json()
        if not data: raise Exception
        return data
    except:
        # Hardcoded fallback to keep UI from dying
        if "drivers" in endpoint: return [{"full_name": "VERSTAPPEN", "driver_number": 1}, {"full_name": "HAMILTON", "driver_number": 44}]
        return []

# Fetch Data
meetings = get_dropdown_data("meetings")
meeting_names = [f"Round {m.get('round', '?')}: {m.get('meeting_name', 'GP')}" for m in meetings] if meetings else ["No Data Available"]
selected_meeting = st.sidebar.selectbox("Select Track", meeting_names)

sessions = get_dropdown_data("sessions")
selected_session = st.sidebar.selectbox("Select Session", [s['session_name'] for s in sessions] if sessions else ["No Data"])

drivers = get_dropdown_data("drivers")
driver_names = [d['full_name'] for d in drivers] if drivers else ["No Data"]
d1 = st.sidebar.selectbox("Driver A", driver_names)
d2 = st.sidebar.selectbox("Driver B", driver_names)

# 4. Rendering Trigger
if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    # Logic to build dashboard
    st.success("Telemetry Data Ready")
    # ... your existing plot code ...
else:
    st.info("Select parameters and click 'Load Data' to begin.")
