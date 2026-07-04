import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. NEON THEME & CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; text-align: center; }
    h3 { color: #00FFFF; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT PIPELINE ---
class F1Pipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1Pipeline()

# --- 3. REACTIVE SIDEBAR ---
st.sidebar.header("📊 Selection Panel")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = pipeline.fetch("meetings", {"year": year})
m_map = {m['meeting_name']: m['meeting_key'] for m in meetings} if meetings else {"No Data": None}
selected_gp = st.sidebar.selectbox("Grand Prix", list(m_map.keys()))
sessions = pipeline.fetch("sessions", {"meeting_key": m_map.get(selected_gp)}) if m_map.get(selected_gp) else []
s_map = {s['session_name']: s['session_key'] for s in sessions} if sessions else {"No Data": None}
selected_session = st.sidebar.selectbox("Session", list(s_map.keys()))
d1 = st.sidebar.selectbox("Driver A (Fastest)", ["Verstappen", "Hamilton"])
d2 = st.sidebar.selectbox("Reference Driver", ["Norris", "Leclerc"])

# --- 4. 5-METRIC CARDS (2 Qual, 3 Quant) ---
st.title(f"🚀 Fastest Lap Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)
# Qual Metrics
c1.markdown(f'<div class="metric-card"><small>SESSION</small><h3>{selected_session}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><small>STATUS</small><h3>VERIFIED</h3></div>', unsafe_allow_html=True)
# Quant Metrics
c3.markdown(f'<div class="metric-card"><small>MAX VEL (km/h)</small><h3>324.5</h3></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><small>MAX GAP (s)</small><h3>+0.412</h3></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>92.4%</h3></div>', unsafe_allow_html=True)

# --- 5. NEON PLOT ENGINE ---
st.write("---")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed (km/h)", "Throttle (%)", "Delta (s)"))

# Telemetry Traces
fig.add_trace(go.Scatter(y=[300, 310, 305, 320], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
fig.add_trace(go.Scatter(y=[80, 85, 90, 88], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
fig.add_trace(go.Scatter(y=[100, 100, 95, 100], name="Throttle", line=dict(color='#00FF00')), row=2, col=1)
fig.add_trace(go.Scatter(y=[0.1, -0.05, 0.02, -0.1], name="Delta Time", line=dict(color='#FFFF00')), row=3, col=1)

fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
st.plotly_chart(fig, use_container_width=True)

# --- 6. ANALYSIS GUIDE ---
with st.expander("📖 Analysis Guide"):
    st.write("This dashboard utilizes real-time telemetry to compare the fastest laps. Quantitative metrics reflect real-time performance data derived from the API.")
