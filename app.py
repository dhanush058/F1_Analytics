import streamlit as st
import fastf1
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Cache setup
cache_dir = './cache'
if not os.path.exists(cache_dir): os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

st.set_page_config(layout="wide", page_title="F1 Telemetry Dashboard")
st.title("🏎️ F1 Telemetry Analysis")

# Sidebar
st.sidebar.title("Configuration")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
gp = st.sidebar.selectbox("Grand Prix", schedule['EventName'].unique())
session_mapping = {'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3', 'Qualifying': 'Q', 'Race': 'R'}
selected_label = st.sidebar.selectbox("Session", list(session_mapping.keys()))
session_id = session_mapping[selected_label]

# Data Loading with Error Handling
@st.cache_data(ttl=3600)
def load_session_data(year, gp, session_id):
    try:
        session = fastf1.get_session(year, gp, session_id)
        session.load(telemetry=True, laps=True)
        return session
    except Exception as e:
        return str(e)

with st.spinner("Loading telemetry..."):
    result = load_session_data(year, gp, session_id)

if isinstance(result, str):
    st.error(f"Network Access Error: The server could not connect to the F1 API. "
             "This is common on cloud platforms. (Error: {result})")
elif result.laps is None or len(result.laps) == 0:
    st.error("Session loaded, but no telemetry data is currently available in the API.")
else:
    session = result
    drivers = session.results['FullName'].unique()
    d1 = st.sidebar.selectbox("Driver A", drivers)
    d2 = st.sidebar.selectbox("Ref Driver", drivers)
    
    lap1 = session.laps.pick_driver(d1).pick_fastest()
    lap2 = session.laps.pick_driver(d2).pick_fastest()
    
    if hasattr(lap1, 'get_telemetry'):
        tel1, tel2 = lap1.get_telemetry().add_distance(), lap2.get_telemetry().add_distance()
        delta, ref_tel, comp_tel = fastf1.utils.delta_time(lap1, lap2)
        
        # Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Max Speed A", f"{tel1['Speed'].max():.0f} km/h")
        c2.metric("Max Speed B", f"{tel2['Speed'].max():.0f} km/h")
        c3.metric("Max Gap", f"{delta.abs().max():.3f} s")
        
        # Plots
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta, name="Delta", line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Speed'], name=d1, line=dict(color='#00FFFF')), row=2, col=1)
        fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Speed'], name=d2, line=dict(color='#FF00FF')), row=2, col=1)
        fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], name=d1, line=dict(color='#00FFFF')), row=3, col=1)
        fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], name=d2, line=dict(color='#FF00FF')), row=3, col=1)
        
        fig.update_layout(height=800, template="plotly_dark", paper_bgcolor="#050505")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Fastest lap data incomplete.")
