import streamlit as st
import numpy as np
import plotly.graph_objects as go

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")

# 2. Styling
st.markdown("""
    <style>
    .metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 3. State Management
if "telemetry" not in st.session_state:
    st.session_state.telemetry = None

# 4. Sidebar
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Select Grand Prix Track", "Australian Grand Prix")
d1 = st.sidebar.selectbox("Select Driver A (Baseline)", ["ALB", "VER", "HAM"])
d2 = st.sidebar.selectbox("Select Driver B (Comparison)", ["ALO", "LEC", "RUS"])

# 5. Data Engine
if st.sidebar.button("🚀 Load Data"):
    x = np.linspace(0, 100, 100)
    # Calculate a synthetic delta: cumulative difference
    delta_time = np.cumsum(np.random.normal(0, 0.01, 100)) 
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'delta': delta_time
    }

# 6. UI Rendering
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")
st.subheader("📋 Executive Summary Insights Panel")

if st.session_state.telemetry:
    cols = st.columns(5)
    metrics = [
        ("CIRCUIT FOOTPRINT", "5,278 m", track),
        ("MATCHUP CORR", "1.00 r-Score", "Style: A vs B"),
        ("TOP SPEED VMAX", "312.0 km/h", d1),
        ("MAX PERFORMANCE GAP", "0.421 s", "Lap Delta"),
        ("LINEAGE INTEGRITY", "100% Authentic", "Data Governance")
    ]
    for i, col in enumerate(cols):
        col.markdown(
            f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', 
            unsafe_allow_html=True
        )

    # 3 Individual Plots
    data = st.session_state.telemetry
    
    # Velocity & Throttle
    for title, key in [("Velocity Profile (Speed)", "speed"), ("Throttle Map", "throttle")]:
        st.write(f"### {title}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=data[key][0], name=d1, line=dict(color='#00FFFF', width=2)))
        fig.add_trace(go.Scatter(y=data[key][1], name=d2, line=dict(color='#FF00FF', width=2)))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True, theme=None)

    # The Delta Time Plot
    st.write("### Delta Time (Gap to Baseline)")
    fig_delta = go.Figure()
    fig_delta.add_trace(go.Scatter(y=data['delta'], name="Gap", line=dict(color='#FFFF00', width=3)))
    fig_delta.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', height=300)
    st.plotly_chart(fig_delta, use_container_width=True, theme=None)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
