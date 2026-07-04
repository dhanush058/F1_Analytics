import streamlit as st
import numpy as np
import plotly.graph_objects as go
import requests

# 1. Page Config
st.set_page_config(page_title="F1 Analytics Vault", layout="wide")
st.markdown("""<style>.metric-card { background-color: #0E1117; border: 1px solid #FF0000; padding: 15px; border-radius: 10px; text-align: center; }</style>""", unsafe_allow_html=True)

# 2. Sidebar with persistent state
st.sidebar.title("🏎️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle("Enable Simulated Demo Mode")
year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024])

# 3. Data Fetching
def get_data(endpoint, params=None):
    try: return requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=3).json()
    except: return []

meetings = get_data("meetings", {"year": year})
meeting_options = {f"Round {m.get('round')}: {m.get('meeting_name', 'GP')}": m['meeting_key'] for m in meetings if m.get('round')}
selected_meeting = st.sidebar.selectbox("Select Track", list(meeting_options.keys()) or ["Waiting for Data..."])

# 4. ALWAYS RENDER THE UI
st.markdown("# 🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER")

# KPI Cards (Always visible)
cols = st.columns(5)
metrics = [("CIRCUIT", "---", "Track"), ("CORR", "1.00", "Style"), ("V-MAX", "---", "Speed"), ("GAP", "---", "Delta"), ("INTEGRITY", "LIVE", "API")]
for i, col in enumerate(cols):
    col.markdown(f'<div class="metric-card"><small style="color:red">{metrics[i][0]}</small><h3>{metrics[i][1]}</h3><small>{metrics[i][2]}</small></div>', unsafe_allow_html=True)

# 5. Conditional Plotting
if st.sidebar.button("🚀 Load Data") or demo_mode:
    # Generate data
    x = np.linspace(0, 100, 100)
    data = {'speed': np.sin(x/10)*50 + 300, 'throttle': np.random.uniform(0, 100, 100), 'delta': np.cumsum(np.random.normal(0, 0.01, 100))}
    
    # Render Plots
    for title, key in [("Velocity Profile", "speed"), ("Throttle Map", "throttle"), ("Delta Time", "delta")]:
        st.write(f"### {title}")
        fig = go.Figure(go.Scatter(y=data[key], line=dict(color='#00FFFF')))
        fig.update_layout(template="plotly_dark", plot_bgcolor='#0E1117', height=300)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select parameters and click 'Load Data' to begin.")
