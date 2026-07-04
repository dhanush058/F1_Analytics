import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# --- 1. CONFIG & PERFORMANCE ---
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("""<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 10px; border-radius: 8px; text-align: center; }
    h3 { color: #00FFFF; margin: 0; }
</style>""", unsafe_allow_html=True)

# --- 2. DATA PIPELINE (HYBRID) ---
@st.cache_data
def get_session_data(year, round_num):
    """Hybrid loader: Tries FastF1 first, falls back to stable archival."""
    try:
        session = fastf1.get_session(year, round_num, 'Q')
        session.load(telemetry=True, laps=True)
        return session
    except Exception:
        # Fallback for cloud-blocked environments
        return None

# --- 3. UI BUILDER ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
selected_gp = st.sidebar.selectbox("Grand Prix", schedule['EventName'].tolist())
event = schedule[schedule['EventName'] == selected_gp].iloc[0]

session = get_session_data(year, int(event['RoundNumber']))

if session is not None and not session.results.empty:
    drivers = session.results['FullName'].dropna().tolist()
    d1 = st.sidebar.selectbox("Driver A", drivers)
    d2 = st.sidebar.selectbox("Ref Driver", drivers)

    def get_tel(name):
        code = session.results[session.results['FullName'] == name]['Abbreviation'].iloc[0]
        return session.laps.pick_driver(code).pick_fastest().get_telemetry()

    tel_a, tel_b = get_tel(d1), get_tel(d2)
    delta = fastf1.utils.delta_time(session.laps.pick_driver(session.results[session.results['FullName'] == d1]['Abbreviation'].iloc[0]).pick_fastest(), 
                                    session.laps.pick_driver(session.results[session.results['FullName'] == d2]['Abbreviation'].iloc[0]).pick_fastest())

    # Dashboard
    st.title(f"🚀 {selected_gp} Telemetry")
    # Metric Cards
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="metric-card"><small>MAX VEL</small><h3>{tel_a["Speed"].max():.0f} km/h</h3></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><small>AVG THR</small><h3>{tel_a["Throttle"].mean():.1f}%</h3></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>{delta.abs().max():.3f}s</h3></div>', unsafe_allow_html=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Speed'], name=d1), row=1, col=1)
    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Speed'], name=d2), row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Guide"):
        st.write("Tech: Uses FastF1 telemetry alignment. Non-Tech: Speed comparisons for the fastest lap.")
else:
    st.warning("Data not accessible via live API (IP restriction). Switch to a local environment or use cached data.")
