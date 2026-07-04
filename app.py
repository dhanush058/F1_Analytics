import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

    def get_driver_telemetry(self, s_key, d_num):
        # STREAMING FETCH: No time-windowing to ensure data delivery
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
for col, label in zip([c1,c2,c3,c4,c5], ["GP", "Session", "Max Vel", "Max Gap", "Avg Thr"]):
    col.markdown(f'<div style="background:#0E1117; border:1px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;">{label}</div>', unsafe_allow_html=True)

# --- 4. PLOT ENGINE ---
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d1))
    data_b = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d2))
    
    if data_a and data_b:
        df_a, df_b = pd.DataFrame(data_a), pd.DataFrame(data_b)
        # Limit to 500 points for performance
        df_a, df_b = df_a.iloc[:500], df_b.iloc[:500] 
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed", "Throttle", "Delta"))
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle", line=dict(color='#00FF00')), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed'].values - df_b['speed'].values, name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Data stream empty for this session. Please select 2024 or 2025 data.")
