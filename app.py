import streamlit as st
import fastf1
import fastf1.utils
import fastf1.plotting
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Cache Setup (Prevents NotADirectoryError)
cache_dir = './cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

st.set_page_config(layout="wide")
st.title("🏎️ FastF1 2026 Telemetry Analysis")

# 2. UI Inputs
year = st.sidebar.number_input("Year", min_value=2024, max_value=2026, value=2026)
gp = st.sidebar.text_input("GP Name", "Australian")
session_type = st.sidebar.selectbox("Session", ['R', 'Q'])

if st.sidebar.button("Analyze"):
    with st.spinner("Loading telemetry..."):
        session = fastf1.get_session(year, gp, session_type)
        session.load()
        
        # Get Fastest Laps
        drivers = session.results['FullName'].tolist()
        d1 = st.sidebar.selectbox("Driver A", drivers)
        d2 = st.sidebar.selectbox("Ref Driver", drivers)
        
        lap1 = session.laps.pick_driver(d1).pick_fastest()
        lap2 = session.laps.pick_driver(d2).pick_fastest()
        
        tel1 = lap1.get_telemetry().add_distance()
        tel2 = lap2.get_telemetry().add_distance()
        
        # Calculate Delta
        delta, ref_tel, comp_tel = fastf1.utils.delta_time(lap1, lap2)
        
        # 3. Plotting with Plotly
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            subplot_titles=("Gap (s)", "Speed (km/h)", "Throttle (%)"))
        
        # Delta Plot
        fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta, name="Delta"), row=1, col=1)
        
        # Speed Plot
        fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Speed'], name=d1), row=2, col=1)
        fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Speed'], name=d2), row=2, col=1)
        
        # Throttle Plot
        fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], name=d1), row=3, col=1)
        fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], name=d2), row=3, col=1)
        
        fig.update_layout(height=900, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
