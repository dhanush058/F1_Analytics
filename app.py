import streamlit as st
import numpy as np
import plotly.graph_objects as go

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. Resilient Data Manager
def get_mock_data():
    """Returns a hardcoded structure to keep the UI alive when API is restricted."""
    return {
        "meetings": [{"round": 1, "meeting_name": "Spain GP", "meeting_key": 100}],
        "sessions": [{"session_name": "Race", "session_key": 200}],
        "drivers": [{"full_name": "Lewis Hamilton", "driver_number": 44}, {"full_name": "Max Verstappen", "driver_number": 1}]
    }

# 3. Sidebar
st.sidebar.title("🏎️ Portfolio Control Panel")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
st.sidebar.warning("API Status: Restricted (Live Session Active)")
demo_mode = st.sidebar.toggle("Enable Fallback Mode", value=True)

# Load Mock Data
data = get_mock_data()
selected_meeting = st.sidebar.selectbox("Select Grand Prix", [m['meeting_name'] for m in data['meetings']])
selected_session = st.sidebar.selectbox("Select Session", [s['session_name'] for s in data['sessions']])
d1 = st.sidebar.selectbox("Driver A", [d['full_name'] for d in data['drivers']])
d2 = st.sidebar.selectbox("Driver B", [d['full_name'] for d in data['drivers']])

# 4. Rendering the "Unbreakable" UI
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

# KPI Cards
cols = st.columns(5)
metrics = [("CIRCUIT", selected_meeting, "Track"), ("STATUS", "Fallback Active", "System"), ("V-MAX", "312 km/h", "Telemetry"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "STABLE", "UI")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

# Plotting
st.write("### Velocity Profile")
fig = go.Figure(go.Scatter(y=np.random.normal(300, 10, 100), line=dict(color='#00FFFF')))
fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=300)
st.plotly_chart(fig, use_container_width=True)
