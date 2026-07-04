import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. INITIALIZATION ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
# Initialize these to None so the NameError never happens
d1 = d2 = selected_session = selected_gp = "No Data" 
s_map = d_map = {}

class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

    def get_driver_telemetry(self, s_key, d_num):
        return self.fetch("car_data", {"session_key": s_key, "driver_number": d_num})

pipeline = F1DataPipeline()

# --- 2. SIDEBAR ---
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

# --- 3. METRICS ---
st.title(f"🚀 Telemetry Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;"><small>GP</small><h3>{selected_gp[:8]}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;"><small>SESSION</small><h3>{selected_session[:8]}</h3></div>', unsafe_allow_html=True)
c3.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;"><small>STATUS</small><h3>LIVE</h3></div>', unsafe_allow_html=True)
c4.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;"><small>MAX VEL</small><h3>---</h3></div>', unsafe_allow_html=True)
c5.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;"><small>DELTA</small><h3>---</h3></div>', unsafe_allow_html=True)

# --- 4. PLOT ENGINE ---
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d1))
    data_b = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d2))
    
    if data_a and data_b:
        df_a = pd.json_normalize(data_a).iloc[:500]
        df_b = pd.json_normalize(data_b).iloc[:500]
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle", line=dict(color='#00FF00')), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed'].values - df_b['speed'].values[:len(df_a)], name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Data stream unavailable for this selection. Try 2024 or 2025.")
