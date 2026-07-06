import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="F1 Data Analytics")

# --- 1. DATA FETCHING (Strict) ---
@st.cache_data(ttl=3600)
def get_openf1(endpoint, params=None):
    try:
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# --- 2. FASTEST LAP LOGIC ---
def get_fastest_lap_data(driver_name, s_key, d_num):
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    if laps.empty: return pd.DataFrame(), None
    
    fastest = laps.loc[laps['lap_duration'].idxmin()]
    start, end = fastest['date_start'], (pd.to_datetime(fastest['date_start']) + pd.Timedelta(seconds=float(fastest['lap_duration']))).isoformat()
    
    tel = get_openf1("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": start, "date<=": end})
    if not tel.empty:
        tel['distance'] = np.linspace(0, 5000, len(tel))
    return tel, fastest['lap_duration']

# --- 3. UI & CONFIG ---
st.sidebar.title("Configuration")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = get_openf1("sessions", {"meeting_key": m_key})
selected_s = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_s]['session_key'].iloc[0]

drivers = get_openf1("drivers", {"session_key": s_key}).sort_values("full_name")
d1 = st.sidebar.selectbox("Driver A", drivers['full_name'].unique())
d2 = st.sidebar.selectbox("Ref Driver", drivers['full_name'].unique())

# --- 4. EXECUTION ---
d1_num = drivers[drivers['full_name'] == d1]['driver_number'].iloc[0]
d2_num = drivers[drivers['full_name'] == d2]['driver_number'].iloc[0]

df_a, t_a = get_fastest_lap_data(d1, s_key, d1_num)
df_b, t_b = get_fastest_lap_data(d2, s_key, d2_num)

# Fallback only if strictly required
if (df_a.empty or df_b.empty) and sim_mode:
    st.warning("API data unavailable. Using Simulation Mode.")
    dist = np.linspace(0, 5000, 1000)
    df_a = pd.DataFrame({'distance': dist, 'speed': 250 + 50*np.sin(dist/200), 'throttle': 80 + 20*np.sin(dist/500)})
    df_b = pd.DataFrame({'distance': dist, 'speed': 240 + 50*np.sin(dist/200), 'throttle': 70 + 20*np.sin(dist/500)})
    t_a, t_b = 85.0, 86.5
elif df_a.empty or df_b.empty:
    st.error("Data missing for this session. Enable Simulation Mode or check selection.")
    st.stop()

# --- 5. VISUALIZATION ---
fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Delta", "Speed", "Throttle"))
fig.add_trace(go.Scatter(x=df_a['distance'], y=np.interp(df_a['distance'], df_b['distance'], df_b['speed']) - df_a['speed'], name="Delta"), row=1, col=1)
fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1), row=2, col=1)
fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2), row=2, col=1)
fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=d1), row=3, col=1)
fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=d2), row=3, col=1)

fig.update_layout(template="plotly_dark", height=800)
st.plotly_chart(fig, use_container_width=True)
