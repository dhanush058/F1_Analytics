import streamlit as st
import fastf1
import fastf1.plotting
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & CACHING ---
# Cache data to prevent redundant API calls and speed up your dashboard
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")

# --- 2. DATA PIPELINE ---
def get_lap_data(year, gp, session_name, driver_code):
    session = fastf1.get_session(year, gp, session_name)
    session.load()
    # Pick the fastest lap for the driver
    lap = session.laps.pick_driver(driver_code).pick_fastest()
    return lap.get_telemetry()

# --- 3. UI ---
st.title("🚀 Fastest Lap Telemetry")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
gp = st.sidebar.text_input("Grand Prix (e.g., 'Bahrain')", "Bahrain")
session_name = st.sidebar.selectbox("Session", ['FP1', 'FP2', 'FP3', 'Q', 'R'])
d1 = st.sidebar.text_input("Driver A Code (e.g., 'NOR')", "NOR")
d2 = st.sidebar.text_input("Driver B Code (e.g., 'VER')", "VER")

# --- 4. ENGINE ---
if st.button("Analyze"):
    try:
        df_a = get_lap_data(year, gp, session_name, d1)
        df_b = get_lap_data(year, gp, session_name, d2)
        
        # Plotting
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed", "Throttle", "Delta"))
        fig.add_trace(go.Scatter(x=df_a['Distance'], y=df_a['Speed'], name=d1), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_b['Distance'], y=df_b['Speed'], name=d2), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_a['Distance'], y=df_a['Throttle'], name=f"{d1} Throttle"), row=2, col=1)
        
        # Delta calculation using FastF1's built-in alignment
        delta = fastf1.utils.delta_time(df_a, df_b)
        fig.add_trace(go.Scatter(x=df_a['Distance'], y=delta, name="Delta"), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error: {e}. Please ensure the GP name and Driver codes are correct.")
