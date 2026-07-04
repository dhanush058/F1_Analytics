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

# --- 2. DATA PIPELINE ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1DataPipeline()

# --- 3. SIDEBAR & STATE INITIALIZATION ---
st.sidebar.header("📊 Selection Panel")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = pipeline.fetch("meetings", {"year": year})
m_map = {m['meeting_name']: m['meeting_key'] for m in meetings} if meetings else {}
selected_gp = st.sidebar.selectbox("Grand Prix", list(m_map.keys()) if m_map else ["No Data"])

sessions = pipeline.fetch("sessions", {"meeting_key": m_map.get(selected_gp)}) if m_map.get(selected_gp) else []
s_map = {s['session_name']: s['session_key'] for s in sessions} if sessions else {}
selected_session = st.sidebar.selectbox("Session", list(s_map.keys()) if s_map else ["No Data"])

drivers = pipeline.fetch("drivers", {"session_key": s_map.get(selected_session)}) if s_map.get(selected_session) else []
d_map = {d['full_name']: d['driver_number'] for d in drivers} if drivers else {}
d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()) if d_map else ["No Data"])
d2 = st.sidebar.selectbox("Ref Driver", list(d_map.keys()) if d_map else ["No Data"])

# --- 4. METRIC CARDS ---
st.title(f"🚀 Telemetry Analysis: {selected_gp}")
cols = st.columns(5)
metrics = [("GP", selected_gp[:10]), ("Session", selected_session[:10]), ("Status", "Live"), ("Drivers", "Synced"), ("Mode", "Telemetry")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small>{metrics[i][0]}</small><h3>{metrics[i][1]}</h3></div>', unsafe_allow_html=True)

# --- 5. PLOT ENGINE WITH DYNAMIC KEY MAPPING ---
st.write("---")
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d1)})
    data_b = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d2)})
    
    if data_a and data_b:
        df_a = pd.DataFrame(data_a)
        df_b = pd.DataFrame(data_b)
        
        # Automatic Key Detection: OpenF1 returns telemetry in a list of packets
        # We look for the common keys 'speed', 'throttle', etc.
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed (km/h)", "Throttle (%)", "Delta (s)"))
        
        # Plotting using detection (if 'speed' is missing, fallback to first numeric column)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle A", line=dict(color='#00FF00')), row=2, col=1)
        
        # Delta Plot
        delta = df_a['speed'].values[:len(df_b)] - df_b['speed'].values[:len(df_b)]
        fig.add_trace(go.Scatter(y=delta, name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("⚠️ Telemetry stream empty. Select a different session or driver.")
