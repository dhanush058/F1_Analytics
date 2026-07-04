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

# --- 2. PIPELINE ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

    def get_fastest_lap_telemetry(self, s_key, d_num):
        laps = self.fetch("laps", {"session_key": s_key, "driver_number": d_num})
        # Keep only laps with valid timing
        valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
        if not valid_laps: return None
        fastest = min(valid_laps, key=lambda x: x['lap_duration'])
        return self.fetch("car_data", {
            "session_key": s_key, "driver_number": d_num,
            "date>": fastest['date_start'], "date<": fastest['date_end']
        })

pipeline = F1DataPipeline()

# --- 3. SIDEBAR ---
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

# --- 4. METRIC CARDS (2 Qual / 3 Quant) ---
st.title(f"🚀 Fastest Lap Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-card"><small>GP</small><h3>{selected_gp[:10]}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><small>SESSION</small><h3>{selected_session[:10]}</h3></div>', unsafe_allow_html=True)

data_a = pipeline.get_fastest_lap_telemetry(s_map.get(selected_session), d_map.get(d1)) if d1 != "No Data" else None
if data_a:
    df = pd.DataFrame(data_a)
    c3.markdown(f'<div class="metric-card"><small>MAX VEL</small><h3>{df["speed"].max():.0f} km/h</h3></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>{df["throttle"].mean():.1f} %</h3></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>--.---</h3></div>', unsafe_allow_html=True)
else:
    for c in [c3, c4, c5]: c.markdown('<div class="metric-card"><small>DATA</small><h3>N/A</h3></div>', unsafe_allow_html=True)

# --- 5. PLOT ENGINE ---
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.get_fastest_lap_telemetry(s_map.get(selected_session), d_map.get(d1))
    data_b = pipeline.get_fastest_lap_telemetry(s_map.get(selected_session), d_map.get(d2))
    
    if data_a and data_b:
        df_a, df_b = pd.DataFrame(data_a), pd.DataFrame(data_b)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed", "Throttle", "Delta"))
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle A", line=dict(color='#00FF00')), row=2, col=1)
        # Fix: align lengths
        min_len = min(len(df_a), len(df_b))
        delta = df_a['speed'].iloc[:min_len].values - df_b['speed'].iloc[:min_len].values
        fig.add_trace(go.Scatter(y=delta, name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Telemetry data unavailable for this specific driver/session combination.")
