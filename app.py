import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_api(url):
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else []
    except: return []

st.sidebar.title("🏎️ Portfolio Control Panel")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])

# 1. Fetch and Validate Meetings
meetings = fetch_api(f"https://api.openf1.org/v1/meetings?year={year}")
# Filter for valid meetings with round numbers
valid_meetings = [m for m in meetings if m.get('round') is not None]
meetings_sorted = sorted(valid_meetings, key=lambda x: x['round'])

# 2. Build Options (Safe)
if meetings_sorted:
    meeting_options = {f"Round {m['round']}: {m.get('meeting_name', 'Unknown')}": m['meeting_key'] for m in meetings_sorted}
    selected_meeting = st.sidebar.selectbox("Select Grand Prix Track", list(meeting_options.keys()))
    m_key = meeting_options[selected_meeting]
else:
    st.sidebar.error("No meetings found for this year.")
    m_key = None

# 3. Sessions (Safe)
if m_key:
    sessions = fetch_api(f"https://api.openf1.org/v1/sessions?meeting_key={m_key}")
    session_map = {s['session_name']: s['session_key'] for s in sessions}
    session_type = st.sidebar.selectbox("Select Session Type", list(session_map.keys()) or ["None"])
    s_key = session_map.get(session_type)
else:
    s_key = None

# 4. Drivers (Safe)
if s_key:
    drivers = fetch_api(f"https://api.openf1.org/v1/drivers?session_key={s_key}")
    d_map = {d['full_name']: d['driver_number'] for d in drivers}
    d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()) or ["None"])
    d2 = st.sidebar.selectbox("Driver B", list(d_map.keys()) or ["None"])
else:
    d1, d2 = None, None

# 5. Data Engine
if "telemetry" not in st.session_state: st.session_state.telemetry = None
if st.sidebar.button("🚀 Load Data") and d1 and d2:
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

# 6. Render
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
if st.session_state.telemetry:
    # ... (Keep your existing plotting logic here)
    st.success("Data Loaded.")
else:
    st.info("Select parameters and click 'Load Data' to begin.")
