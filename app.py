import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PIPELINE WITH TIME-FILTERING ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1DataPipeline()

st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

# --- 2. SIDEBAR (Reactive Selection) ---
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

# --- 3. FASTEST LAP LOGIC ---
def get_fastest_lap_telemetry(s_key, d_num):
    laps = pipeline.fetch("laps", {"session_key": s_key, "driver_number": d_num})
    if not laps: return None
    # Find lap with minimum duration
    fastest = min([l for l in laps if l.get('lap_duration')], key=lambda x: x['lap_duration'])
    # Fetch telemetry for that specific time range
    return pipeline.fetch("car_data", {
        "session_key": s_key, 
        "driver_number": d_num,
        "date>": fastest['date_start'],
        "date<": fastest['date_end']
    })

# --- 4. PLOTTING ---
st.title(f"🚀 Fastest Lap Analysis: {selected_gp}")
# Metrics row as requested
c1, c2, c3, c4, c5 = st.columns(5)
# (Assuming logic to calculate these from the fetched DF)
for c, txt in zip([c1,c2,c3,c4,c5], ["GP", "Status", "Max Vel", "Max Gap", "Avg Thr"]):
    c.markdown(f'<div style="background:#0E1117; border:2px solid #00FFFF; padding:10px; border-radius:5px; text-align:center;">{txt}</div>', unsafe_allow_html=True)

if d1 != "No Data" and d2 != "No Data":
    data_a = get_fastest_lap_telemetry(s_map[selected_session], d_map[d1])
    data_b = get_fastest_lap_telemetry(s_map[selected_session], d_map[d2])
    
    if data_a and data_b:
        df_a, df_b = pd.DataFrame(data_a), pd.DataFrame(data_b)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=f"{d1} Speed", line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed'] - df_b['speed'].values[:len(df_a)], name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=700)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Fastest lap data not found for selected combination.")
