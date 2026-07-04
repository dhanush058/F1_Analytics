import streamlit as st
import fastf1
import fastf1.plotting
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- 1. CONFIG & THEME ---
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 10px; border-radius: 8px; text-align: center; }
    h3 { color: #00FFFF; margin: 0; font-size: 20px; }
    [data-testid="stAppViewContainer"] { background-color: #050505; color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)

# --- 2. DYNAMIC SELECTORS ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
events = fastf1.get_event_schedule(year)
selected_gp = st.sidebar.selectbox("Grand Prix", events['EventName'].tolist())

# Load Session
try:
    session = fastf1.get_session(year, selected_gp, 'Q')
    session.load(telemetry=True, laps=True)
    driver_list = session.results['FullName'].dropna().tolist()
    d1 = st.sidebar.selectbox("Driver A", driver_list)
    d2 = st.sidebar.selectbox("Ref Driver", driver_list)
except:
    st.error("Session data not yet available for this event.")
    st.stop()

# --- 3. DATA ENGINE ---
def get_fastest_lap(name):
    driver_data = session.results[session.results['FullName'] == name]
    if driver_data.empty: return None
    code = driver_data['Abbreviation'].iloc[0]
    return session.laps.pick_driver(code).pick_fastest()

lap_a = get_fastest_lap(d1)
lap_b = get_fastest_lap(d2)

if lap_a is not None and lap_b is not None:
    tel_a, tel_b = lap_a.get_telemetry(), lap_b.get_telemetry()
    delta_time = fastf1.utils.delta_time(lap_a, lap_b)

    # --- 4. DASHBOARD ---
    st.title(f"🚀 {selected_gp} Qualifying Analysis")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(f'<div class="metric-card"><small>MAX VEL</small><h3>{tel_a["Speed"].max():.0f} km/h</h3></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>{delta_time.abs().max():.3f} s</h3></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><small>AVG THROTTLE</small><h3>{tel_a["Throttle"].mean():.1f}%</h3></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>SECTOR 1</small><h3>{lap_a["Sector1Time"].total_seconds():.2f}s</h3></div>', unsafe_allow_html=True)
    c5.markdown(f'<div class="metric-card"><small>SECTOR 2</small><h3>{lap_a["Sector2Time"].total_seconds():.2f}s</h3></div>', unsafe_allow_html=True)

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed", "Throttle", "Delta"))
    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Speed'], name=d1), row=1, col=1)
    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Speed'], name=d2), row=1, col=1)
    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Throttle'], name=f"{d1} Throttle"), row=2, col=1)
    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=delta_time, name="Delta (s)"), row=3, col=1)
    fig.update_layout(template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Quick Guide"):
        st.write("**Non-Tech:** This compares two drivers on their best lap. 'Delta' shows who is ahead over the course of the lap.")
        st.write("**Tech:** We use FastF1 telemetry alignment. Delta is calculated by normalizing position over distance.")
else:
    st.warning("Telemetry not found for selected drivers.")
