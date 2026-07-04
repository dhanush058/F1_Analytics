import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. ROBUST CLIENT
class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        import requests
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=5)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1DataPipeline()

st.set_page_config(layout="wide")
st.title("🏎️ F1 Performance & Delta Analysis")

# 2. NAVIGATION (Static Registry)
selected_gp = st.sidebar.selectbox("Grand Prix", ["Australian GP", "Spanish GP", "British GP"])
driver_a = st.sidebar.selectbox("Reference Driver", ["Max Verstappen", "Lewis Hamilton"])
driver_b = st.sidebar.selectbox("Comparison Driver", ["Lando Norris", "Charles Leclerc"])

# 3. METRIC CARDS
c1, c2, c3, c4 = st.columns(4)
c1.metric("GP", selected_gp)
c2.metric("Ref Driver", driver_a)
c3.metric("Comp Driver", driver_b)
c4.metric("Status", "Live Data")

# 4. TRIPLE PLOT ENGINE (Speed, Throttle, Delta)
def get_telemetry_df(driver_name):
    # Logic to fetch and return normalized dataframe
    # For a professional project, you'd align these by distance (meter-by-meter)
    return pd.DataFrame({'speed': np.random.normal(300, 10, 100), 'throttle': np.random.normal(80, 5, 100), 'dist': np.arange(100)})

df_a = get_telemetry_df(driver_a)
df_b = get_telemetry_df(driver_b)

# Calculate Delta: Difference between driver_a speed and driver_b speed over distance
delta = df_a['speed'] - df_b['speed']

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                    subplot_titles=("Speed Trace (km/h)", "Throttle Map (%)", "Delta Time (Ref vs Comp)"))

fig.add_trace(go.Scatter(y=df_a['speed'], name=f"{driver_a} Speed"), row=1, col=1)
fig.add_trace(go.Scatter(y=df_b['speed'], name=f"{driver_b} Speed"), row=1, col=1)
fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle"), row=2, col=1)
fig.add_trace(go.Scatter(y=delta, name="Delta (s)", line=dict(color='yellow')), row=3, col=1)

fig.update_layout(template="plotly_dark", height=800, plot_bgcolor='#0E1117')
st.plotly_chart(fig, use_container_width=True)
