import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. PERMANENT CONFIG
st.set_page_config(layout="wide")
st.title("🏎️ F1 Performance Analysis: Fastest Lap Delta")

# 2. SIDEBAR (Reactive Selections)
st.sidebar.header("Data Selection")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
# Assuming API structure for meeting/session list...
selected_gp = st.sidebar.selectbox("Grand Prix", ["Australian GP", "Spanish GP"])
selected_session = st.sidebar.selectbox("Session", ["Race", "Qualifying"])
use_sim_data = st.sidebar.toggle("Use Simulation Data", value=False)

st.sidebar.write("---")
d1 = st.sidebar.selectbox("Driver A (Fastest Lap)", ["Verstappen", "Hamilton"])
d2 = st.sidebar.selectbox("Reference Driver", ["Norris", "Leclerc"])

# 3. METRIC CARDS (Always visible)
cols = st.columns(4)
cols[0].metric("Mode", "Simulation" if use_sim_data else "Live API")
cols[1].metric("Year", year)
cols[2].metric("Fastest Lap (A)", "1:24.320")
cols[3].metric("Delta (A vs Ref)", "-0.150s")

# 4. ANALYSIS ENGINE (Reactive Plotting)
st.write("### Analysis: Fastest Lap Telemetry")

# Logic to fetch fastest lap telemetry for Driver A and compare to Ref
# This runs automatically when any sidebar selection changes
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                    subplot_titles=("Speed (km/h)", "Throttle (%)", "Delta Time (s)"))

# Placeholder for Data Fetching logic
# In a real build, here you filter the car_data for the fastest lap ID
fig.add_trace(go.Scatter(y=[300, 315, 310, 320], name=f"{d1} Speed"), row=1, col=1)
fig.add_trace(go.Scatter(y=[100, 100, 95, 100], name=f"{d1} Throttle"), row=2, col=1)
fig.add_trace(go.Scatter(y=[-0.1, -0.05, 0, 0.05], name="Delta Time", line=dict(color='yellow')), row=3, col=1)

fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
st.plotly_chart(fig, use_container_width=True)

# 5. ANALYSIS GUIDE (Always visible)
with st.expander("📊 How to interpret this analysis"):
    st.write("""
    - **Speed Trace:** Compares the velocity of the two drivers throughout the fastest lap.
    - **Throttle Map:** Identifies acceleration patterns and braking points.
    - **Delta Time:** A negative value indicates Driver A is faster at that specific distance interval.
    """)
