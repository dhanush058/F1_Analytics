import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics Pro")
st.markdown("""
<style>
    .metric-card { background-color: #0E1117; border: 2px solid #00FFFF; padding: 15px; border-radius: 10px; text-align: center; }
    h3 { color: #00FFFF; margin: 0; font-size: 24px; }
    [data-testid="stAppViewContainer"] { background-color: #050505; color: white; }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
BASE_URL = "https://api.openf1.org/v1"

@st.cache_data(ttl=3600)
def fetch_api(endpoint, params=None):
    try:
        res = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- 3. UI LAYOUT ---
st.title("🏎️ F1 Telemetry Analysis")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
meetings = fetch_api("meetings", {"year": year})
sel_gp = st.sidebar.selectbox("Grand Prix", [m['meeting_name'] for m in meetings])
m_key = next(m['meeting_key'] for m in meetings if m['meeting_name'] == sel_gp)

sess = fetch_api("sessions", {"meeting_key": m_key})
sel_sess = st.sidebar.selectbox("Session", [s['session_name'] for s in sess])
s_key = next(s['session_key'] for s in sess if s['session_name'] == sel_sess)

drivers = fetch_api("drivers", {"session_key": s_key})
d1 = st.sidebar.selectbox("Driver A", [d['full_name'] for d in drivers])
d2 = st.sidebar.selectbox("Ref Driver", [d['full_name'] for d in drivers])

# --- 4. DATA PROCESSING ---
def get_fastest_lap_tel(d_name, s_key):
    d_num = next(d['driver_number'] for d in drivers if d['full_name'] == d_name)
    laps = fetch_api("laps", {"session_key": s_key, "driver_number": d_num})
    fastest = min([l for l in laps if l['lap_duration']], key=lambda x: x['lap_duration'])
    
    # Get telemetry for the exact lap window
    tel = fetch_api("car_data", {
        "session_key": s_key, "driver_number": d_num,
        "date>": fastest['date_start'], "date<": fastest['date_end']
    })
    return pd.DataFrame(tel)

# --- 5. DASHBOARD ---
if st.button("Generate Analysis"):
    df_a = get_fastest_lap_tel(d1, s_key)
    df_b = get_fastest_lap_tel(d2, s_key)

    if not df_a.empty and not df_b.empty:
        # Metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(f'<div class="metric-card"><small>MAX VEL (A)</small><h3>{df_a["speed"].max()}</h3></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><small>AVG THR (A)</small><h3>{df_a["throttle"].mean():.1f}%</h3></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><small>MAX GAP</small><h3>{abs(df_a["speed"].max()-df_b["speed"].max()):.1f}</h3></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><small>GEAR (A)</small><h3>{df_a["n_gear"].mode()[0]}</h3></div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="metric-card"><small>RPM (A)</small><h3>{df_a["rpm"].mean():.0f}</h3></div>', unsafe_allow_html=True)

        # 3 Plots
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(y=df_a['speed'], name=f"{d1} Speed"), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name="Throttle"), row=2, col=1)
        fig.add_trace(go.Scatter(y=df_a['speed']-df_b['speed'], name="Speed Delta"), row=3, col=1)
        fig.update_layout(template="plotly_dark", height=800)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📖 Comprehensive Guide"):
            st.write("**Non-Tech:** This compares the fastest laps of two drivers. If the delta is positive, Driver A is faster.")
            st.write("**Tech:** Telemetry is filtered via UTC timestamps provided by the OpenF1 API to ensure single-lap isolation.")
