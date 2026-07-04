import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(layout="wide")

class F1DataPipeline:
    def fetch(self, endpoint, params=None):
        try:
            res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
            return res.json() if res.status_code == 200 else []
        except: return []

pipeline = F1DataPipeline()

# --- SIDEBAR ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
# ... (Use your existing meeting/session/driver maps here) ...

# --- FIXED PLOT ENGINE ---
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.fetch("car_data", {"session_key": s_map[selected_session], "driver_number": d_map[d1]})
    data_b = pipeline.fetch("car_data", {"session_key": s_map[selected_session], "driver_number": d_map[d2]})
    
    if data_a and data_b:
        # CONVERSION: The API returns data points. We must extract the value.
        # Ensure we are looking at the 'value' key if it exists, or the dictionary itself.
        df_a = pd.DataFrame(data_a)
        df_b = pd.DataFrame(data_b)
        
        # If 'value' is nested (common in OpenF1), extract it:
        # This assumes the API returns [{'value': 300, 'date': '...'}, ...]
        # If the API returns direct values, remove the .apply block.
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        
        # Plotting - access the correct column name
        fig.add_trace(go.Scatter(y=df_a['value'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['value'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        
        fig.update_layout(template="plotly_dark", height=700)
        st.plotly_chart(fig, use_container_width=True)
