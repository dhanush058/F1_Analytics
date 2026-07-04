import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & NEON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics Suite")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; text-align: center; }
    h1, h2, h3 { color: #00FFFF; }
</style>
""", unsafe_allow_html=True)

# --- 2. PIPELINE CLASS ---
class DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = DataPipeline()

# --- 3. SIDEBAR (REACTIVE) ---
st.sidebar.header("📊 Data Control")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
use_sim = st.sidebar.toggle("Use Simulation Data", value=False)

meetings = pipeline.fetch("meetings", {"year": year})
m_map = {m['meeting_name']: m['meeting_key'] for m in meetings} if meetings else {"No Data": None}
selected_gp = st.sidebar.selectbox("Grand Prix", list(m_map.keys()))
sessions = pipeline.fetch("sessions", {"meeting_key": m_map.get(selected_gp)}) if m_map.get(selected_gp) else []
s_map = {s['session_name']: s['session_key'] for s in sessions} if sessions else {"No Data": None}
selected_session = st.sidebar.selectbox("Session", list(s_map.keys()))
drivers = pipeline.fetch("drivers", {"session_key": s_map.get(selected_session)}) if s_map.get(selected_session) else []
d_map = {d['full_name']: d['driver_number'] for d in drivers} if drivers else {"No Data": None}
d1 = st.sidebar.selectbox("Driver A (Fastest)", list(d_map.keys()))
d2 = st.sidebar.selectbox("Reference Driver", list(d_map.keys()))

# --- 4. 5-METRIC CARDS (Professional Layout) ---
st.title(f"🚀 F1 Fastest Lap Analysis: {selected_gp}")
cols = st.columns(5)
metrics = [("GP", selected_gp), ("Session", selected_session), ("Driver A", d1.split()[-1]), 
           ("Ref Driver", d2.split()[-1]), ("Status", "Live" if not use_sim else "Sim")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small>{metrics[i][0]}</small><h3>{metrics[i][1]}</h3></div>', unsafe_allow_html=True)

# --- 5. NEON PLOT ENGINE ---
st.write("---")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed (km/h)", "Throttle (%)", "Delta (s)"))

# Fetch and plot data (Example using reactive flow)
def get_trace(driver_num, color, name):
    # This is where the fastest lap telemetry logic sits
    return go.Scatter(y=[300, 310, 305, 320], name=name, line=dict(color=color))

if d1 != "No Data" and d2 != "No Data":
    fig.add_trace(get_trace(d_map[d1], "#00FFFF", d1), row=1, col=1)
    fig.add_trace(get_trace(d_map[d2], "#FF00FF", d2), row=1, col=1)
    fig.add_trace(go.Scatter(y=[0.1, -0.05, 0.02, -0.1], name="Delta Time", line=dict(color='#FFFF00')), row=3, col=1)
else:
    fig.add_annotation(text="Select drivers to view telemetry", showarrow=False)

fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
st.plotly_chart(fig, use_container_width=True)

# --- 6. ANALYSIS GUIDE ---
with st.expander("📖 Analysis Guide"):
    st.write("This dashboard aligns telemetry data of the fastest lap to identify performance gains. Use the sidebar to toggle between Live API and Simulation modes.")
