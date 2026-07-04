import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. INITIALIZATION (Prevents NameError) ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
d1 = d2 = "No Data" 
s_map = d_map = {}

class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

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

# --- 3. PLOT ENGINE ---
st.title(f"🚀 Telemetry Analysis: {selected_gp}")

if d1 != "No Data" and d2 != "No Data":
    # Using the 'car_data' endpoint correctly
    data_a = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d1)})
    data_b = pipeline.fetch("car_data", {"session_key": s_map.get(selected_session), "driver_number": d_map.get(d2)})
    
    if data_a and data_b:
        df_a = pd.DataFrame(data_a)
        df_b = pd.DataFrame(data_b)
        
        # DEBUG: Print columns to console so you can see exactly what key to use
        # st.write(df_a.columns) 
        
        # OpenF1 'car_data' often uses 'value' or 'speed'. We check for common ones.
        target_col = 'value' if 'value' in df_a.columns else 'speed'
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a[target_col].iloc[:500], name=d1), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b[target_col].iloc[:500], name=d2), row=1, col=1)
        
        fig.update_layout(template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("No telemetry data found for this selection. Try a different session.")
