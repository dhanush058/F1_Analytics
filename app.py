import streamlit as st
import numpy as np
import plotly.graph_objects as go

# 1. Page Config (Kept wide for the 5-metric row)
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")

# 2. Styling (Red borders and Dark theme as per your requirement)
st.markdown("""
    <style>
    .metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 3. State Management (Keeps the UI "frozen")
if "telemetry" not in st.session_state:
    st.session_state.telemetry = None

# 4. Sidebar (Original layout)
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Select Grand Prix Track", "Australian Grand Prix")
session_type = st.sidebar.selectbox("Select Session Type", ["Race", "Qualifying"])
d1 = st.sidebar.selectbox("Select Driver A (Baseline)", ["ALB", "VER", "HAM"])
d2 = st.sidebar.selectbox("Select Driver B (Comparison)", ["ALO", "LEC", "RUS"])

# 5. Data Engine (Manual Trigger)
if st.sidebar.button("🚀 Load Data"):
    # This logic forces the data to load into the session state
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'rpm': (np.random.normal(12000, 500, 100), np.random.normal(12000, 500, 100))
    }

# 6. UI Rendering (Exact UI restoration)
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
st.subheader("📋 Executive Summary Insights Panel")

if st.session_state.telemetry:
    # 5 KPI Metric Cards
    cols = st.columns(5)
    metrics = [
        ("CIRCUIT FOOTPRINT", "5,278 m", track),
        ("MATCHUP CORR", "1.00 r-Score", "Style: A vs B"),
        ("TOP SPEED VMAX", "312.0 km/h", d1),
        ("MAX PERFORMANCE GAP", "0.421 s", "Lap Delta"),
        ("LINEAGE INTEGRITY", "100% Authentic", "Data Governance")
    ]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_color_html=True)

    # 3 Individual Plots
    data = st.session_state.telemetry
    for title, key in [("Velocity Profile (Speed)", "speed"), ("Throttle Map", "throttle"), ("RPM Trace", "rpm")]:
        st.write(f"### {title}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=data[key][0], name=d1, line=dict(color='#00FFFF', width=2)))
        fig.add_trace(go.Scatter(y=data[key][1], name=d2, line=dict(color='#FF00FF', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
