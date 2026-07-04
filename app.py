import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. LIVE DATA ENGINE (Cloud-Friendly)
@st.cache_data(ttl=3600)
def get_live_data(year, round_num, session_type):
    # OpenF1 endpoint is designed for cloud access
    url = f"https://api.openf1.org/v1/sessions?year={year}&round_number={round_num}&session_type={session_type}"
    session = requests.get(url).json()
    if not session: return None
    
    session_key = session[0]['session_key']
    # Fetch telemetry for a driver
    tel_url = f"https://api.openf1.org/v1/car_data?session_key={session_key}"
    response = requests.get(tel_url).json()
    return pd.DataFrame(response)

# 2. UI
st.title("🚀 F1 Live Analytics")
year = st.sidebar.selectbox("Year", [2026])
round_num = st.sidebar.number_input("Round Number", 1, 24, 1)
df = get_live_data(year, round_num, 'Qualifying')

if df is not None and not df.empty:
    st.success("Live data successfully ingested.")
    # Plotting
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['date'], y=df['speed'], name="Speed"))
    st.plotly_chart(fig)
else:
    st.error("Data is currently unavailable for this session or environment.")
