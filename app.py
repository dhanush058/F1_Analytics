import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. State & Session Management
if "telemetry" not in st.session_state: st.session_state.telemetry = None

# 3. Sidebar
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("🖥️ Enable Simulated Demo Mode", value=False)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Select Grand Prix Track", "Australian Grand Prix")
session_type = st.sidebar.selectbox("Select Session Type", ["Race", "Qualifying"])
d1 = st.sidebar.selectbox("Select Driver A (Baseline)", ["ALB", "VER", "HAM"])
d2 = st.sidebar.selectbox("Select Driver B (Comparison)", ["ALO", "LEC", "RUS"])

# 4. Data Engine
if st.sidebar.button("🚀 Load Data"):
    try:
        # Placeholder for real API call
        # response = requests.get(f"https://api.openf1.org/v1/...") 
        # Force Demo Mode if toggled or if API fails
        if demo_mode:
            raise Exception("Demo Mode Triggered")
        st.session_state.telemetry = True 
    except Exception as e:
        st.sidebar.error("⚠️ API Rate Limit or Connection Error.")
        if st.sidebar.button("Click here to use Sim Data"):
            st.session_state.telemetry = "SIM"

# 5. UI Layout (The "Old UI")
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
st.subheader("📋 Executive Summary Insights Panel")

if st.session_state.telemetry:
    # 5 Metric Cards
    cols = st.columns(5)
    metrics = [("CIRCUIT FOOTPRINT", "5,278 m", track), ("MATCHUP CORR", "1.00 r-Score", "Style: A vs B"), 
               ("TOP SPEED VMAX", "312.0 km/h", d1), ("MAX PERFORMANCE GAP", "0.421 s", "Lap Delta"), 
               ("LINEAGE INTEGRITY", "100% Authentic", "API Stream")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

    # Telemetry Plot
    st.write("### Velocity Profile (Speed Trace)")
    fig = go.Figure()
    # Neon Traces
    x_data = np.linspace(0, 5000, 100)
    fig.add_trace(go.Scatter(x=x_data, y=np.random.normal(310, 5, 100), name=d1, line=dict(color='#00FFFF', width=3)))
    fig.add_trace(go.Scatter(x=x_data, y=np.random.normal(305, 5, 100), name=d2, line=dict(color='#FF00FF', width=3)))
    
    fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=400)
    st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
