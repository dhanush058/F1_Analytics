import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Telemetry Pro")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; text-align: center; }
    h3 { color: #00FFFF; margin: 0; font-size: 24px; }
</style>
""", unsafe_allow_html=True)

# --- 2. PIPELINE CLASS ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

    def get_fastest_lap_telemetry(self, s_key, d_num):
        # Fetch laps and filter for those with valid time boundaries
        laps = self.fetch("laps", {"session_key": s_key, "driver_number": d_num})
        valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
        
        if not valid_laps: return None
        
        # Identify fastest lap
        fastest = min(valid_laps, key=lambda x: x['lap_duration'])
        
        # Query telemetry for that specific time window
        return self.fetch("car_data", {
            "session_key": s_key, 
            "driver_number": d_num,
            "date>=": fastest['date_start'], 
            "date<=": fastest['date_end']
        })

pipeline = F1DataPipeline()

# --- 3. SIDEBAR ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = pipeline.fetch("meetings", {"year": year})
m_map = {m['meeting_name']: m['meeting_key'] for m in meetings}
selected_gp = st.sidebar.selectbox("Grand Prix", list(m_map.keys()))

sessions = pipeline.fetch("sessions", {"meeting_key": m_map.get(selected_gp)})
s_map = {s['session_name']: s['session_key'] for s in sessions}
selected_session = st.sidebar.selectbox("Session", list(s_map.keys()))

drivers = pipeline.fetch("drivers", {"session_key": s_map.get(selected_session)})
d_map = {d['full_name']: d['driver_number'] for d in drivers}
d1 = st.sidebar.selectbox("Driver A", list(d_map.keys()))
d2 = st.sidebar.selectbox("Ref Driver", list(d_map.keys()))

# --- 4. DATA FETCHING ---
df_a, df_b = None, None
if d1 and d2 and selected_session:
    data_a = pipeline.get_fastest_lap_telemetry(s_map[selected_session], d_map[d1])
    data_b = pipeline.get_fastest_lap_telemetry(s_map[selected_session], d_map[d2])
    if data_a and data_b:
        df_a, df_b = pd.DataFrame(data_a), pd.DataFrame(data_b)

# --- 5. METRICS & PLOTS ---
st.title(f"🚀 Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="metric-card"><small>GP</small><h3>{selected_gp[:10]}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><small>SESSION</small><h3>{selected_session[:10]}</h3></div>', unsafe_allow_html=True)

if df_a is not None and df_b is not None:
    c3.markdown(f'<div class="metric-card"><small>MAX VEL</small><h3>{df_a["speed"].max():.0f} km/h</h3></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>{df_a["throttle"].mean():.1f} %</h3></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>{abs(df_a["speed"].max() - df_b["speed"].max()):.0f} km/h</h3></div>', unsafe_allow_html=True)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed", "Throttle", "Delta"))
    fig.add_trace(go.Scatter(y=df_a['speed'], name=d1), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_b['speed'], name=d2), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle A"), row=2, col=1)
    
    min_len = min(len(df_a), len(df_b))
    delta = df_a['speed'].iloc[:min_len].values - df_b['speed'].iloc[:min_len].values
    fig.add_trace(go.Scatter(y=delta, name="Delta", fill='tozeroy'), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Data not available for this fastest lap. Please select a different session.")
