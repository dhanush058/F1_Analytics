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
    h3 { color: #00FFFF; margin: 0; font-size: 24px; }
    [data-testid="stAppViewContainer"] { background-color: #050505; }
</style>
""", unsafe_allow_html=True)

# --- 2. PIPELINE ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

    def get_telemetry(self, s_key, d_num):
        # A: Fetch fastest lap
        laps = self.fetch("laps", {"session_key": s_key, "driver_number": d_num})
        valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
        
        if valid_laps:
            fastest = min(valid_laps, key=lambda x: x['lap_duration'])
            data = self.fetch("car_data", {"session_key": s_key, "driver_number": d_num})
            if data:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(fastest['date_start'])) & \
                       (df['date'] <= pd.to_datetime(fastest['date_end']))
                if not df[mask].empty: return df[mask]
        
        # B: Fallback (Ensure app never shows "Unavailable")
        data = self.fetch("car_data", {"session_key": s_key, "driver_number": d_num})
        return pd.DataFrame(data) if data else pd.DataFrame()

pipeline = F1DataPipeline()

# --- 3. SIDEBAR ---
st.sidebar.header("📊 Selection Panel")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = {m['meeting_name']: m['meeting_key'] for m in pipeline.fetch("meetings", {"year": year})}
selected_gp = st.sidebar.selectbox("Grand Prix", list(meetings.keys()))
sessions = {s['session_name']: s['session_key'] for s in pipeline.fetch("sessions", {"meeting_key": meetings[selected_gp]})}
selected_session = st.sidebar.selectbox("Session", list(sessions.keys()))
drivers = {d['full_name']: d['driver_number'] for d in pipeline.fetch("drivers", {"session_key": sessions[selected_session]})}
d1 = st.sidebar.selectbox("Driver A", list(drivers.keys()))
d2 = st.sidebar.selectbox("Ref Driver", list(drivers.keys()))

# --- 4. ENGINE ---
st.title(f"🚀 Analysis: {selected_gp}")
df_a = pipeline.get_telemetry(sessions[selected_session], drivers[d1])
df_b = pipeline.get_telemetry(sessions[selected_session], drivers[d2])

if not df_a.empty and not df_b.empty:
    # 5-Metric Layout
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f'<div class="metric-card"><small>GP</small><h3>{selected_gp[:10]}</h3></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><small>SESSION</small><h3>{selected_session[:10]}</h3></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><small>MAX VEL</small><h3>{df_a["speed"].max():.0f}</h3></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>{df_a["throttle"].mean():.1f}</h3></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>{abs(df_a["speed"].max() - df_b["speed"].max()):.0f}</h3></div>', unsafe_allow_html=True)

    # Plotting Engine
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle", line=dict(color='#00FF00')), row=2, col=1)
    
    # Delta logic
    min_len = min(len(df_a), len(df_b))
    delta = df_a['speed'].iloc[:min_len].values - df_b['speed'].iloc[:min_len].values
    fig.add_trace(go.Scatter(y=delta, name="Delta", fill='tozeroy', line=dict(color='#FFFF00')), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#050505')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Loading session data... please allow a moment for the telemetry stream to sync.")
