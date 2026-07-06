import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & RECRUITER TOAST ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Fastest Lap")

if "toast_shown" not in st.session_state:
    st.toast("⚠️ Recruiter Note: F1 APIs often block cloud IPs or lack future data (e.g., 2026). Use 'Enable Simulation Mode' in the sidebar to evaluate the dashboard's analytics engine.", icon="🚨")
    st.session_state.toast_shown = True

COLOR_A = '#00FFFF'   # Neon Cyan
COLOR_B = '#FF00FF'   # Neon Magenta
COLOR_DELTA = '#FFFFFF' # White

# --- 2. API FETCHER (NO UGLY ERRORS) ---
@st.cache_data(ttl=600)
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=10)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. DATA ENGINE (REAL & SIMULATION) ---
def get_telemetry(driver_name, s_key, drivers_df, is_sim=False, is_ref_driver=False):
    dist_ref = np.linspace(0, 5000, 1000)
    
    if is_sim:
        # GUARANTEED VARIANCE: Driver A gets one driving style, Driver B gets another.
        # This ensures the Delta plot is highly active and realistic.
        if not is_ref_driver:
            # Driver A: Late Braking, lower apex speed
            speed = 320 - 150 * np.exp(-((dist_ref - 1100)/130)**2) \
                        - 120 * np.exp(-((dist_ref - 2300)/100)**2) \
                        - 160 * np.exp(-((dist_ref - 3400)/180)**2) \
                        - 140 * np.exp(-((dist_ref - 4400)/130)**2)
            throttle = 100 - 100 * np.exp(-((dist_ref - 1050)/150)**2) \
                           - 100 * np.exp(-((dist_ref - 2250)/110)**2) \
                           - 100 * np.exp(-((dist_ref - 3350)/190)**2) \
                           - 100 * np.exp(-((dist_ref - 4350)/140)**2)
            lap_time = 82.145
        else:
            # Driver B: Early braking, higher apex speed (carries more momentum)
            speed = 315 - 135 * np.exp(-((dist_ref - 1050)/160)**2) \
                        - 105 * np.exp(-((dist_ref - 2250)/130)**2) \
                        - 145 * np.exp(-((dist_ref - 3350)/210)**2) \
                        - 130 * np.exp(-((dist_ref - 4350)/160)**2)
            throttle = 100 - 100 * np.exp(-((dist_ref - 1000)/180)**2) \
                           - 100 * np.exp(-((dist_ref - 2200)/140)**2) \
                           - 100 * np.exp(-((dist_ref - 3300)/220)**2) \
                           - 100 * np.exp(-((dist_ref - 4300)/170)**2)
            lap_time = 82.412
            
        speed = np.clip(speed + np.random.normal(0, 1.0, 1000), 65, 340)
        throttle = np.clip(throttle + np.random.normal(0, 1.5, 1000), 0, 100)
        throttle[throttle > 95] = 100
        return pd.DataFrame({'distance': dist_ref, 'speed': speed, 'throttle': throttle}), lap_time

    # LIVE FETCHING
    d_num = drivers_df[drivers_df['full_name'] == driver_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns: return pd.DataFrame(), None
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
    
    fastest_lap = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    start_time = pd.to_datetime(fastest_lap['date_start'])
    end_time = start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']))
    
    start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
    
    tel = get_openf1("car_data", {"session_key": s_key, "driver_number": d_num, "date>=": start_str, "date<=": end_str})
    if tel.empty or 'speed' not in tel.columns: return pd.DataFrame(), fastest_lap['lap_duration']
        
    tel['speed'] = pd.to_numeric(tel['speed'], errors='coerce')
    tel['throttle'] = pd.to_numeric(tel['throttle'], errors='coerce')
    tel = tel.dropna(subset=['speed', 'throttle'])
    
    tel['distance_raw'] = np.linspace(0, 5000, len(tel))
    df_normalized = pd.DataFrame({
        'distance': dist_ref,
        'speed': np.interp(dist_ref, tel['distance_raw'], tel['speed']),
        'throttle': np.interp(dist_ref, tel['distance_raw'], tel['throttle'])
    })
    return df_normalized, fastest_lap['lap_duration']

# --- 4. SIDEBAR & ROUTING ---
st.sidebar.title("🏎️ Control Console")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
if meetings.empty:
    st.sidebar.warning(f"No API data for {year}. Please enable Simulation Mode or pick 2024.")
    st.stop()
    
meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)].sort_values("meeting_key")
selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]

sessions = get_openf1("sessions", {"meeting_key": m_key})
if sessions.empty: st.stop()
selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]

drivers_data = get_openf1("drivers", {"session_key": s_key})
if drivers_data.empty: st.stop()
drivers_data = drivers_data.dropna(subset=['full_name'])
sorted_driver_list = sorted(drivers_data['full_name'].unique())
d1 = st.sidebar.selectbox("Driver A", sorted_driver_list, index=0)
d2 = st.sidebar.selectbox("Ref Driver", sorted_driver_list, index=min(1, len(sorted_driver_list)-1))

# --- 5. EXECUTION & VISUALIZATION ---
with st.spinner("Processing Telemetry Data..."):
    # Note: Passing `is_ref_driver=True` to the second driver guarantees distinct simulated curves
    df_a, lap_time_a = get_telemetry(d1, s_key, drivers_data, sim_mode, is_ref_driver=False)
    df_b, lap_time_b = get_telemetry(d2, s_key, drivers_data, sim_mode, is_ref_driver=True)

if df_a.empty or df_b.empty:
    st.warning("⚠️ Real telemetry is unavailable for this specific session (API returned 404). Please check 'Enable Simulation Mode' in the sidebar to view the analytics dashboard.")
else:
    st.title(f"Fastest Lap Telemetry: {selected_gp}")
    
    # Metrics (5 Cards)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("MAX VEL: DRIVER A", f"{df_a['speed'].max():.0f} km/h", d1)
    m2.metric("MAX VEL: REF DRIVER", f"{df_b['speed'].max():.0f} km/h", d2)
    
    # Delta Math
    v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6
    v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
    delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * (5000/1000)
    final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
    
    m3.metric("LAP TIME VARIANCE", f"{final_delta:.3f} s")
    m4.metric("TRACK DIMENSION", "5.00 km")
    m5.metric("DATA SOURCE", "SIMULATION" if sim_mode else "LIVE API")

    # Neon F1 Plots
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Cumulative Time Delta (s) [Up = A Faster]", "Speed Profile (km/h)", "Throttle Application (%)"),
                        vertical_spacing=0.07)

    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta_time_array, name="Time Delta", line=dict(color=COLOR_DELTA, width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=f"{d1} Speed", line=dict(color=COLOR_A, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=f"{d2} Speed", line=dict(color=COLOR_B, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color=COLOR_A, width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=f"{d2} Throttle", line=dict(color=COLOR_B, width=1.5)), row=3, col=1)

    fig.update_layout(template="plotly_dark", height=850, paper_bgcolor="#0A0A0C", plot_bgcolor="#0A0A0C", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# --- 6. GUIDE ---
with st.expander("📖 Comprehensive Telemetry Engineering Guide (Technical & Functional Manual)"):
    t_col, f_col = st.columns(2)
    with t_col:
        st.write("### 💻 Technical Infrastructure")
        st.write("F1 components stream telemetry metrics at asynchronous intervals (~3.7 Hz). Rather than plotting chronological arrays, this application maps datasets onto an integrated track coordinate structure using **Linear Spatial Interpolation (`np.interp`)**.")
    with f_col:
        st.write("### 🏁 Functional Analytics")
        st.write("* **Time Delta:** Upward slope = Driver A is faster. Downward = Ref Driver is faster.")
        st.write("* **Speed & Throttle:** Deep 'V' speed traces indicate heavy braking. Faster throttle application (earlier return to 100%) out of these zones highlights differences in car downforce and driver commitment.")
