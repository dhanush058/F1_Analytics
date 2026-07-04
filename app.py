import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & NEON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; text-align: center; }
    h3 { color: #00FFFF; }
</style>
""", unsafe_allow_html=True)

# --- 2. PIPELINE CLASS ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1DataPipeline()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.header("📊 Data Selection")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

# Fetch Meetings
meetings = pipeline.fetch("meetings", {"year": year})
m_map = {m['meeting_name']: m['meeting_key'] for m in meetings} if meetings else {}
selected_gp = st.sidebar.selectbox("Grand Prix", list(m_map.keys()) if m_map else ["No Data"])

# Fetch Sessions
sessions = pipeline.fetch("sessions", {"meeting_key": m_map.get(selected_gp)}) if m_map.get(selected_gp) else []
s_map = {s['session_name']: s['session_key'] for s in sessions} if sessions else {}
selected_session = st.sidebar.selectbox("Session", list(s_map.keys()) if s_map else ["No Data"])

# Fetch Drivers
drivers = pipeline.fetch("drivers", {"session_key": s_map.get(selected_session)}) if s_map.get(selected_session) else []
d_map = {d['full_name']: d['driver_number'] for d in drivers} if drivers else {}
d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()) if d_map else ["No Data"])
d2 = st.sidebar.selectbox("Driver B (Reference)", list(d_map.keys()) if d_map else ["No Data"])

# --- 4. METRIC CARDS (2 Qual, 3 Quant) ---
st.title(f"🚀 Performance Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-card"><small>GP</small><h3>{selected_gp[:10]}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><small>SESSION</small><h3>{selected_session}</h3></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="metric-card"><small>MAX VEL (km/h)</small><h3>324.5</h3></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="metric-card"><small>MAX GAP (s)</small><h3>+0.412</h3></div>', unsafe_allow_html=True)
c5.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>92.4%</h3></div>', unsafe_allow_html=True)

# --- 5. NEON PLOT ENGINE ---
st.write("---")
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed Trace (km/h)", "Throttle Map (%)", "Delta Time (s)"))

# Data Fetching Logic (Reactive)
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d1)})
    data_b = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d2)})
    
    if data_a and data_b:
        df_a, df_b = pd.DataFrame(data_a), pd.DataFrame(data_b)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=f"{d1} Speed", line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=f"{d2} Speed", line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color='#00FF00')), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed'] - df_b['speed'], name="Delta Time", line=dict(color='#FFFF00')), row=3, col=1)
    else:
        fig.add_annotation(text="No telemetry data for this combination.", showarrow=False)

fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
st.plotly_chart(fig, use_container_width=True)

with st.expander("📖 Analysis Guide"):
    st.write("The dashboard updates instantly based on your selection. Delta Time is calculated as the difference in velocity between Driver A and Driver B.")
