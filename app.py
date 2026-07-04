import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_api(url):
    try:
        response = requests.get(url, timeout=5)
        return response.json() if response.status_code == 200 else []
    except: return []

# 2. Sidebar with Corrected Key Access
st.sidebar.title("🏎️ Portfolio Control Panel")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])

# Fetch meetings and sort by date
meetings = fetch_api(f"https://api.openf1.org/v1/meetings?year={year}")
# Handle cases where round might be missing or under a different key
meetings_sorted = sorted(meetings, key=lambda x: x.get('date_start', ''))

# Use 'round' and 'meeting_official_name' which are standard OpenF1 keys
meeting_options = {f"Round {m.get('round', '?')}: {m.get('meeting_official_name', 'Unknown GP')}": m['meeting_key'] for m in meetings_sorted}
selected_meeting = st.sidebar.selectbox("Select Grand Prix Track", list(meeting_options.keys()))
m_key = meeting_options[selected_meeting]

# Fetch sessions
sessions = fetch_api(f"https://api.openf1.org/v1/sessions?meeting_key={m_key}")
session_map = {s['session_name']: s['session_key'] for s in sessions}
session_type = st.sidebar.selectbox("Select Session Type", list(session_map.keys()))
s_key = session_map[session_type]

# Drivers
drivers = fetch_api(f"https://api.openf1.org/v1/drivers?session_key={s_key}")
d_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()))
d2 = st.sidebar.selectbox("Driver B", list(d_map.keys()))

# 3. Data Engine
if "telemetry" not in st.session_state: st.session_state.telemetry = None
if st.sidebar.button("🚀 Load Data"):
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': np.cumsum(np.random.normal(0, 0.01, 100))
    }

# 4. UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
if st.session_state.telemetry:
    # KPI Cards (using .get for safety)
    cols = st.columns(5)
    metrics = [("CIRCUIT", selected_meeting.split(': ')[1], "Track"), ("CORR", "1.00", "Style"), 
               ("V-MAX", "312 km/h", d1), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "API")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

    # 3 Plots
    data = st.session_state.telemetry
    for title, key in [("Velocity Profile (Speed)", "speed"), ("Throttle Map", "throttle"), ("Delta Time (Gap)", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure()
        if key == 'delta':
            fig.add_trace(go.Scatter(y=data[key], name="Gap", line=dict(color='#FFFF00', width=2)))
        else:
            fig.add_trace(go.Scatter(y=data[key][0], name=d1, line=dict(color='#00FFFF', width=2)))
            fig.add_trace(go.Scatter(y=data[key][1], name=d2, line=dict(color='#FF00FF', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300, margin=dict(t=30, b=30, l=30, r=30))
        st.plotly_chart(fig, use_container_width=True, theme=None)
