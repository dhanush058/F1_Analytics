import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 1. Error Dialog
@st.dialog("API Rate Limit Exceeded")
def show_error_dialog():
    st.warning("The OpenF1 API is currently limited. Would you like to switch to Simulated Demo Mode to view the dashboard?")
    if st.button("Load Simulation"):
        st.session_state.demo_mode = True
        st.rerun()

# 2. State & Session
if "telemetry" not in st.session_state: st.session_state.telemetry = None
if "demo_mode" not in st.session_state: st.session_state.demo_mode = False

# 3. Sidebar
st.sidebar.title("🏎️ Portfolio Control Panel")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024, 2023])

# Data Logic
try:
    meetings = requests.get(f"https://api.openf1.org/v1/meetings?year={year}", timeout=3).json()
    valid = [m for m in meetings if m.get('round') is not None]
    meetings_sorted = sorted(valid, key=lambda x: x['round'])
    
    if not meetings_sorted: raise Exception("No Data")
    
    meeting_options = {f"Round {m['round']}: {m.get('meeting_name', 'GP')}": m['meeting_key'] for m in meetings_sorted}
    selected_meeting = st.sidebar.selectbox("Select Grand Prix Track", list(meeting_options.keys()))
    m_key = meeting_options[selected_meeting]
    
    # [Rest of your session/driver fetching code here...]
    
except Exception:
    if not st.session_state.demo_mode:
        show_error_dialog()

# 4. Simulation Engine
if st.session_state.demo_mode or st.sidebar.button("🚀 Load Data"):
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

# 5. UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
if st.session_state.telemetry:
    # 5 KPI Cards & 3 Plots as previously established...
    st.success("Telemetry Data Loaded.")
    # Plotting code here...
else:
    st.info("Select parameters and click 'Load Data' to begin.")
