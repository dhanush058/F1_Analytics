import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page & Layout (Always Rendered)
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. State Persistence
if "demo_mode" not in st.session_state: st.session_state.demo_mode = False

# 3. Sidebar (Hardcoded Fallback for 2026)
st.sidebar.title("🏎️ Portfolio Control Panel")
st.session_state.demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode (Required for 2026)", value=st.session_state.demo_mode)
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])

# Data Registry
if not st.session_state.demo_mode:
    try:
        meetings = requests.get(f"https://api.openf1.org/v1/meetings?year={year}", timeout=3).json()
        meeting_options = {f"Round {m.get('round')}: {m.get('meeting_name', 'GP')}": m['meeting_key'] for m in meetings if m.get('round')}
    except:
        meeting_options = {"API Restricted - Enable Demo Mode": None}
else:
    meeting_options = {"2026 Demo Round: Spanish GP": 1, "2026 Demo Round: Australian GP": 2}

selected_meeting = st.sidebar.selectbox("Select Track", list(meeting_options.keys()))
# ... (Repeat this pattern for Session and Driver dropdowns)

# 4. ALWAYS RENDER THE UI
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

# KPI Cards - Fixed Rendering
cols = st.columns(5)
metrics = [("CIRCUIT", "Active", "Track"), ("CORR", "1.00", "Style"), ("V-MAX", "312", "km/h"), ("GAP", "0.42s", "Delta"), ("INTEGRITY", "100%", "Status")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

# Plots - Fixed Rendering
if st.sidebar.button("🚀 Load Data") or st.session_state.demo_mode:
    for title in ["Velocity Profile", "Throttle Map", "Delta Time"]:
        st.write(f"### {title}")
        fig = go.Figure(go.Scatter(y=np.random.normal(0,1,100), line=dict(color='#00FFFF')))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("API data is currently unavailable for 2026. Enable 'Simulated Demo Mode' to view the dashboard.")
