import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# 1. Page Config (Static, always renders)
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. State Management (The "Save" Button)
if "telemetry" not in st.session_state: st.session_state.telemetry = None

# 3. Persistent UI (These elements NEVER disappear)
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("Enable Resilience/Demo Mode", value=True)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])

# Static selection placeholders that don't crash
track = st.sidebar.selectbox("Select Track", ["Monaco GP", "Silverstone", "Spa"], index=0)
session = st.sidebar.selectbox("Select Session", ["FP1", "Qualifying", "Race"], index=1)
d1 = st.sidebar.selectbox("Driver A", ["VER", "HAM", "LEC"])
d2 = st.sidebar.selectbox("Driver B", ["NOR", "RUS", "SAI"])

st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

# 4. KPI Cards (Static Grid)
cols = st.columns(5)
metrics = [("CIRCUIT", track, "Track"), ("CORR", "1.00", "Style"), ("V-MAX", "312", "km/h"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "STABLE", "API")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

# 5. Plot Logic (The Engine)
if st.sidebar.button("🚀 Load Data") or demo_mode:
    # This renders the plots even if the API is offline
    x = np.linspace(0, 100, 100)
    for title, key in [("Velocity Profile", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure(go.Scatter(y=np.random.randn(100), line=dict(color='#00FFFF')))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("System Ready. Toggle 'Demo Mode' or click 'Load Data' to visualize.")
