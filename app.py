import streamlit as st
import fastf1
import fastf1.utils
import fastf1.plotting
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Setup Cache
cache_dir = './cache'
if not os.path.exists(cache_dir): os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

st.set_page_config(layout="wide")
st.title("🏎️ F1 Telemetry Analysis")

# --- 1. SELECTION FLOW ---
col1, col2, col3 = st.columns(3)
with col1:
    year = st.selectbox("Year", [2026, 2025, 2024])
    # Fetch events for the year
    schedule = fastf1.get_event_schedule(year)
    gp = st.selectbox("Grand Prix", schedule['EventName'].unique())
with col2:
    session_name = st.selectbox("Session", ['FP1', 'FP2', 'FP3', 'Q', 'R'])
with col3:
    # Load session once selection is made
    session = fastf1.get_session(year, gp, session_name)
    session.load()
    drivers = session.results['FullName'].unique()
    d1 = st.selectbox("Driver A", drivers)
    d2 = st.selectbox("Ref Driver", drivers)

# --- 2. DATA PROCESSING ---
def get_lap(driver_name):
    driver_laps = session.laps.pick_driver(driver_name)
    return driver_laps.pick_fastest()

lap1 = get_lap(d1)
lap2 = get_lap(d2)

# Check if laps are valid to prevent AttributeError
if isinstance(lap1, fastf1.core.Lap) and isinstance(lap2, fastf1.core.Lap):
    tel1 = lap1.get_telemetry().add_distance()
    tel2 = lap2.get_telemetry().add_distance()
    delta, ref_tel, comp_tel = fastf1.utils.delta_time(lap1, lap2)
    
    # --- 3. PLOTTING ---
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Gap (s)", "Speed (km/h)", "Throttle (%)"))
    
    fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta, name="Delta"), row=1, col=1)
    fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Speed'], name=d1), row=2, col=1)
    fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Speed'], name=d2), row=2, col=1)
    fig.add_trace(go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], name=d1), row=3, col=1)
    fig.add_trace(go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], name=d2), row=3, col=1)
    
    fig.update_layout(height=800, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("One or both drivers do not have a completed valid lap for this session.")

# --- 4. GUIDE ---
with st.expander("📖 Reading the Telemetry"):
    st.write("""
    - **Delta:** Time difference. Positive means the reference driver is ahead.
    - **Speed:** Velocity profile. Braking points and apex speeds are clearly visible.
    - **Throttle:** Shows how aggressively drivers get back on power.
    """)
