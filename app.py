import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="F1 Analytics")

# --- UI NOTIFICATION ---
if "toast_shown" not in st.session_state:
    st.toast("⚠️ Live API note: F1 data may be restricted. Enable 'Simulation' if live plots remain empty.", icon="🚨")
    st.session_state.toast_shown = True

# --- API HELPER ---
@st.cache_data(ttl=60)
def get_data(endpoint, params):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- SIDEBAR ---
st.sidebar.title("Configuration")
sim_mode = st.sidebar.checkbox("Simulation Mode", value=False)

# Setup Selections
meetings = get_data("meetings", {"year": 2026})
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'])
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = get_data("sessions", {"meeting_key": m_key})
s_key = sessions['session_key'].iloc[0]

drivers = get_data("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'])
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'])

# --- DATA PROCESSING ---
def get_telemetry(name):
    if sim_mode:
        x = np.linspace(0, 5000, 1000)
        return pd.DataFrame({'distance': x, 'speed': 250 + 50*np.sin(x/300), 'throttle': 50 + 50*np.sin(x/600)})
    
    d_num = drivers[drivers['full_name'] == name]['driver_number'].iloc[0]
    df = get_data("car_data", {"session_key": s_key, "driver_number": d_num})
    if not df.empty:
        df['distance'] = np.linspace(0, 5000, len(df)) # Normalizing for distance axis
    return df

df_a = get_telemetry(d1)
df_b = get_telemetry(d2)

# --- PLOTTING ---
if not df_a.empty and not df_b.empty:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Time Delta (s)", "Speed (km/h)", "Throttle (%)"))
    
    # Delta Plot (Calculated as difference in speed mapped to distance)
    delta = df_a['speed'] - df_b['speed']
    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta, name="Delta", line=dict(color='white')), row=1, col=1)
    
    # Speed & Throttle
    for trace_data, row, col_name in [(df_a, 2, 'speed'), (df_b, 2, 'speed'), (df_a, 3, 'throttle'), (df_b, 3, 'throttle')]:
        fig.add_trace(go.Scatter(x=trace_data['distance'], y=trace_data[col_name], name=d1 if 'df_a' in str(trace_data) else d2), row=row, col=1)

    fig.update_layout(template="plotly_dark", height=800, paper_bgcolor="#050505")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Data not available. Please toggle Simulation Mode.")

# --- GUIDE ---
with st.expander("📖 How to Read Telemetry"):
    st.write("- **Time Delta:** Positive values indicate Driver A is faster; negative means Ref Driver is faster.")
    st.write("- **Speed Plot:** Sharp drops indicate braking zones; higher mid-corner speed shows better grip.")
    st.write("- **Throttle:** Measures how early a driver gets back on power. Earlier full-throttle application on exit usually equates to a faster lap.")
