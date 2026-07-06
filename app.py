import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. LIVE API WRAPPER
@st.cache_data(ttl=60) # Caches data for 60 seconds to keep it "live" but fast
def fetch_openf1(endpoint, params=None):
    base = "https://api.openf1.org/v1/"
    try:
        response = requests.get(base + endpoint, params=params, timeout=10)
        return pd.DataFrame(response.json()) if response.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# 2. UI & SELECTION
st.set_page_config(layout="wide", page_title="Live F1 Telemetry")
st.title("🏎️ Live F1 Telemetry Analysis")

# Sidebar selections
year = st.sidebar.selectbox("Year", [2026, 2025])
meetings = fetch_openf1("meetings", {"year": year})
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'])
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = fetch_openf1("sessions", {"meeting_key": m_key})
selected_s = st.sidebar.selectbox("Session", sessions['session_name'])
s_key = sessions[sessions['session_name'] == selected_s]['session_key'].iloc[0]

drivers = fetch_openf1("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'])
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'])

# 3. LIVE DATA PROCESSING
def get_driver_telemetry(name):
    d_num = drivers[drivers['full_name'] == name]['driver_number'].iloc[0]
    # Fetch car data for the last 1000 data points (approx 1 min of live data)
    tel = fetch_openf1("car_data", {"session_key": s_key, "driver_number": d_num})
    if not tel.empty:
        tel['date'] = pd.to_datetime(tel['date'])
        return tel.tail(1000)
    return pd.DataFrame()

# 4. PLOTTING
df_a, df_b = get_driver_telemetry(d1), get_driver_telemetry(d2)

if not df_a.empty and not df_b.empty:
    c1, c2, c3 = st.columns(3)
    c1.metric("Live Speed A", f"{df_a['speed'].iloc[-1]} km/h")
    c2.metric("Live Speed B", f"{df_b['speed'].iloc[-1]} km/h")
    c3.metric("Delta", f"{df_a['speed'].iloc[-1] - df_b['speed'].iloc[-1]:.1f} km/h")

    fig = make_subplots(rows=2, cols=1)
    fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
    fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
    fig.update_layout(template="plotly_dark", height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Waiting for live telemetry packets...")
