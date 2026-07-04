import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

if "telemetry" not in st.session_state: st.session_state.telemetry = None

st.sidebar.title("🏎️ Portfolio Control Panel")
demo = st.sidebar.toggle("Enable Simulated Demo Mode")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])
track = st.sidebar.text_input("Track", "Melbourne")
d1 = st.sidebar.selectbox("Driver A", ["VER", "HAM", "NOR"])
d2 = st.sidebar.selectbox("Driver B", ["LEC", "RUS", "ALO"])

if st.sidebar.button("🚀 Load Data") or demo:
    # Sim data generator for the plots
    x = np.linspace(0, 100, 100)
    st.session_state.telemetry = {
        'speed': (np.sin(x/10)*50 + 300, np.sin(x/10 + 0.5)*50 + 300),
        'throttle': (np.random.uniform(0, 100, 100), np.random.uniform(0, 100, 100)),
        'rpm': (np.random.normal(12000, 500, 100), np.random.normal(12000, 500, 100))
    }

st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

if st.session_state.telemetry:
    # 5 KPI Cards
    cols = st.columns(5)
    metrics = [("CIRCUIT", "5,278 m", track), ("CORR", "1.00 r-Score", "Style: A vs B"), 
               ("V-MAX", "312 km/h", d1), ("GAP", "0.421 s", "Lap Delta"), ("INTEGRITY", "100%", "Authentic")]
    for i, col in enumerate(cols):
        col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

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
    st.warning("⚠️ API Error: No data available. Enable 'Simulated Demo Mode' to view charts.")
