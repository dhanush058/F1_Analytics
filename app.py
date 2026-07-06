import streamlit as st
import fastf1
import fastf1.utils
import fastf1.plotting
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Setup & Cache
cache_dir = './cache'
if not os.path.exists(cache_dir): os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

# 2. Sidebar Controls
st.sidebar.title("Configuration")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
gp = st.sidebar.selectbox("Grand Prix", schedule['EventName'].unique())

session_mapping = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3', 'Qualifying': 'Q', 'Race': 'R'}
selected_label = st.sidebar.selectbox("Session", list(session_mapping.keys()))
session_id = session_mapping[selected_label]

# Load session
session = fastf1.get_session(year, gp, session_id)
session.load()
drivers = session.results['FullName'].unique()
d1 = st.sidebar.selectbox("Driver A", drivers)
d2 = st.sidebar.selectbox("Ref Driver", drivers)

# 3. Data Processing
def get_fastest_lap(name):
    return session.laps.pick_driver(name).pick_fastest()

lap1, lap2 = get_fastest_lap(d1), get_fastest_lap(d2)

if isinstance(lap1, fastf1.core.Lap) and isinstance(lap2, fastf1.core.Lap):
    tel1, tel2 = lap1.get_telemetry().add_distance(), lap2.get_telemetry().add_distance()
    delta, ref_tel, comp_tel = fastf1.utils.delta_time(lap1, lap2)
    
    # 4. Metrics Row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("MAX VEL (A)", f"{tel1['Speed'].max():.0f} km/h", d1)
    c2.metric("MAX VEL (B)", f"{tel2['Speed'].max():.0f} km/h", d2)
    c3.metric("MAX GAP", f"{delta.abs().max():.3f} s")
    c4.metric("TRACK LEN", f"{session.get_circuit_info().length:.1f} m")
    c5.metric("LAPS", f"{lap1['LapNumber']}", f"{lap2['LapNumber']}")

    # 5. Neon Plots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Gap (s)", "Speed (km/h)", "Throttle (%)"))
    for row, data, name in [(1, delta, "Delta"), (2, "Speed", "Speed"), (3, "Throttle", "Throttle")]:
        fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta if row==1 else tel1[name], name=d1, line=dict(color='#00FFFF')), row=row, col=1)
        fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta if row==1 else tel2[name], name=d2, line=dict(color='#FF00FF')), row=row, col=1)
    
    fig.update_layout(height=800, template="plotly_dark", paper_bgcolor="#050505", plot_bgcolor="#050505")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Telemetry data unavailable for these selections.")
