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
    h3 { color: #00FFFF; margin: 5px 0 0 0; font-size: 24px; }
    small { color: #888; font-weight: bold; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- 2. PIPELINE ---
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except:
            return []

    def get_fastest_lap_telemetry(self, s_key, d_num):
        laps = self.fetch("laps", {"session_key": s_key, "driver_number": d_num})
        # Strict validation ensuring data points contain valid timestamp boundaries
        valid_laps = [l for l in laps if l.get('lap_duration') and l.get('date_start') and l.get('date_end')]
        if not valid_laps: 
            return None
        
        # Pull minimum duration lap
        fastest = min(valid_laps, key=lambda x: x['lap_duration'])
        
        # Query car telemetry inside the boundary of that single lap
        return self.fetch("car_data", {
            "session_key": s_key, 
            "driver_number": d_num,
            "date>=": fastest['date_start'], 
            "date<=": fastest['date_end']
        })

pipeline = F1DataPipeline()

# --- 3. SIDEBAR MAPS & NAVIGATION ---
st.sidebar.header(" Bars Selection Panel")
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

# --- 4. DATA PROCESSING ---
df_a = pd.DataFrame()
df_b = pd.DataFrame()
max_vel_val = 0
avg_thr_val = 0
max_gap_val = 0

if d1 != "No Data" and d2 != "No Data" and selected_session != "No Data":
    s_key = s_map.get(selected_session)
    data_a = pipeline.get_fastest_lap_telemetry(s_key, d_map.get(d1))
    data_b = pipeline.get_fastest_lap_telemetry(s_key, d_map.get(d2))
    
    if data_a and data_b:
        df_a = pd.DataFrame(data_a)
        df_b = pd.DataFrame(data_b)
        
        # Ensure targeted columns are forced numerical
        for df in [df_a, df_b]:
            if 'speed' in df.columns: df['speed'] = pd.to_numeric(df['speed'], errors='coerce')
            if 'throttle' in df.columns: df['throttle'] = pd.to_numeric(df['throttle'], errors='coerce')
        
        # Calculate quantitative values safely
        if 'speed' in df_a.columns:
            max_vel_val = df_a['speed'].max()
        if 'throttle' in df_a.columns:
            avg_thr_val = df_a['throttle'].mean()
            
        if 'speed' in df_a.columns and 'speed' in df_b.columns:
            min_len = min(len(df_a), len(df_b))
            # Max speed gap conversion between drivers over the lap
            max_gap_val = abs(df_a['speed'].iloc[:min_len].values - df_b['speed'].iloc[:min_len].values).max()

# --- 5. 5-METRIC LAYOUT (2 Qual / 3 Quant) ---
st.title(f"🚀 Telemetry Analysis: {selected_gp}")
c1, c2, c3, c4, c5 = st.columns(5)

# Qual Cards
c1.markdown(f'<div class="metric-card"><small>Grand Prix</small><h3>{selected_gp[:12]}</h3></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="metric-card"><small>Session Type</small><h3>{selected_session[:12]}</h3></div>', unsafe_allow_html=True)

# Quant Cards
if not df_a.empty and not df_b.empty:
    c3.markdown(f'<div class="metric-card"><small>Max Vel (Driver A)</small><h3>{max_vel_val:.0f} km/h</h3></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>Avg Throttle (Driver A)</small><h3>{avg_thr_val:.1f} %</h3></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card"><small>Max Speed Gap</small><h3>{max_gap_val:.0f} km/h</h3></div>', unsafe_allow_html=True)
else:
    c3.markdown('<div class="metric-card"><small>Max Vel</small><h3>---</h3></div>', unsafe_allow_html=True)
    c4.markdown('<div class="metric-card"><small>Avg Throttle</small><h3>---</h3></div>', unsafe_allow_html=True)
    c5.markdown('<div class="metric-card"><small>Max Gap</small><h3>---</h3></div>', unsafe_allow_html=True)

# --- 6. NEON PLOT ENGINE ---
st.write("---")
if not df_a.empty and not df_b.empty:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed (km/h)", "Throttle (%)", "Velocity Delta (km/h)"))
    
    # Subplot 1: Speed Analysis
    fig.add_trace(go.Scatter(y=df_a['speed'], name=f"{d1} (Speed)", line=dict(color='#00FFFF', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_b['speed'], name=f"{d2} (Speed)", line=dict(color='#FF00FF', width=2)), row=1, col=1)
    
    # Subplot 2: Throttle Position
    if 'throttle' in df_a.columns:
        fig.add_trace(go.Scatter(y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color='#00FF00', width=1.5)), row=2, col=1)
    
    # Subplot 3: Precise Mathematical Delta Over Lap
    min_len = min(len(df_a), len(df_b))
    delta_series = df_a['speed'].iloc[:min_len].values - df_b['speed'].iloc[:min_len].values
    fig.add_trace(go.Scatter(y=delta_series, name="Delta Gap", line=dict(color='#FFFF00', width=1.5), fill='tozeroy'), row=3, col=1)
    
    fig.update_layout(template="plotly_dark", height=750, plot_bgcolor='#0E1117', paper_bgcolor='#0E1117')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Select a completed session (such as a 2024 or 2025 Qualifying session) to pull unique fastest-lap telemetry streams.")
