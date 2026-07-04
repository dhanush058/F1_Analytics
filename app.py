import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- 1. PREMIUM DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_live_data(year, round_num):
    # Fetch session metadata to get valid session_key
    url = f"https://api.openf1.org/v1/sessions?year={year}&round_number={round_num}"
    response = requests.get(url)
    
    if response.status_code != 200 or not response.json():
        return None, "No session data found for this round."

    sessions = response.json()
    # Filter for Qualifying
    qualifying = [s for s in sessions if s.get('session_name') == 'Qualifying']
    
    if not qualifying:
        return None, "Qualifying session not found."

    session_key = qualifying[0]['session_key']
    
    # Fetch car data
    tel_url = f"https://api.openf1.org/v1/car_data?session_key={session_key}"
    tel_data = requests.get(tel_url).json()
    
    if not tel_data:
        return None, "Telemetry data not available."
        
    return pd.DataFrame(tel_data), None

# --- 2. CLEAN UI ---
st.set_page_config(page_title="F1 Analytics Pro", layout="wide")
st.title("🏎️ Premium F1 Live Analytics")

year = st.sidebar.selectbox("Year", [2026])
round_num = st.sidebar.number_input("Round Number", 1, 24, 1)

df, error = get_live_data(year, round_num)

if error:
    st.warning(f"Status: {error}")
else:
    st.success("Data ingested successfully.")
    
    # Professional Plot
    fig = go.Figure()
    # Assuming standard columns for OpenF1 car_data
    fig.add_trace(go.Scatter(x=df['date'], y=df['speed'], name="Speed"))
    fig.update_layout(template="plotly_dark", title="Speed Telemetry")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📖 Professional Guide"):
        st.write("This dashboard leverages the OpenF1 API for cloud-native, real-time data ingestion, bypassing traditional IP-based restrictions.")
