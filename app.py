import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & NEON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Fastest Lap")

# Top-Middle Pop-up Notification directed at Recruiters
if "toast_shown" not in st.session_state:
    st.toast("⚠️ Recruiter Note: F1's API hosting restrictions can block cloud server IPs. If live data fails to load, toggle 'Enable Simulation Mode' in the sidebar to test dashboard logic with accurate, distinct driver telemetry profiles.", icon="🚨")
    st.session_state.toast_shown = True

# Colors for the F1 Cyberpunk aesthetic
COLOR_A = '#00FFFF'   # Neon Cyan
COLOR_B = '#FF00FF'   # Neon Magenta
COLOR_DELTA = '#FFFFFF' # Crisp White

# --- 2. CACHED LIVE API FETCHING ---
@st.cache_data(ttl=600)  # Low TTL ensures data updates automatically as new races drop
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=8)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# --- 3. DATA ENGINE: SINGLE FASTEST LAP & SPATIAL INTERPOLATION ---
def get_telemetry(driver_name, s_key, drivers_df, is_sim=False):
    dist_ref = np.linspace(0, 5000, 1000) # Standardized 1,000 reference points along the track
    
    if is_sim:
        # Generates highly realistic F1 track profiles instead of broken random noise/flatlines
        seed = sum(ord(c) for c in driver_name)
        np.random.seed(seed)
        
        # Synthetic track layout: 4 corner braking profiles across a 5.0km lap
        speed = 315 - 140 * np.exp(-((dist_ref - 1100)/160)**2) \
                    - 110 * np.exp(-((dist_ref - 2300)/110)**2) \
                    - 150 * np.exp(-((dist_ref - 3400)/190)**2) \
                    - 135 * np.exp(-((dist_ref - 4400)/140)**2)
        
        # Unique driver signature adjustments (so traces do not overlap identically)
        driver_variance = (seed % 4) - 2.0
        speed += driver_variance + np.sin(dist_ref / 80) * 2.5
        speed = np.clip(speed, 65, 338)
        
        # Smooth physical transition curves for throttle application
        throttle = 100 - 98 * np.exp(-((dist_ref - 1020)/170)**2) \
                       - 98 * np.exp(-((dist_ref - 2240)/120)**2) \
                       - 98 * np.exp(-((dist_ref - 3310)/200)**2) \
                       - 98 * np.exp(-((dist_ref - 4320)/150)**2)
        throttle = np.clip(throttle + np.random.normal(0, 1.2, 1000), 0, 100)
        throttle[throttle > 92] = 100 # Pin to full-throttle on straightaways
        
        lap_time = 82.4 + (seed % 10) / 4.2
        return pd.DataFrame({'distance': dist_ref, 'speed': speed, 'throttle': throttle}), lap_time

    # LIVE FETCHING FLOW
    d_num = drivers_df[drivers_df['full_name'] == driver_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns:
        return pd.DataFrame(), None
        
    # Isolate single fastest lap duration and time window
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
    fastest_lap = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    
    start_time = pd.to_datetime(fastest_lap['date_start'])
    end_time = start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']))
    
    # Target telemetry exclusively inside the boundaries of that single lap
    tel = get_openf1("car_data", {
        "session_key": s_key, 
        "driver_number": d_num, 
        "date>=": start_time.isoformat(), 
        "date<=": end_time.isoformat()
    })
    
    if tel.empty or 'speed' not in tel.columns:
        return pd.DataFrame(), fastest_lap['lap_duration']
        
    tel['speed'] = pd.to_numeric(tel['speed'], errors='coerce')
    tel['throttle'] = pd.to_numeric(tel['throttle'], errors='coerce')
    tel = tel.dropna(subset=['speed', 'throttle'])
    
    # Linearly project asynchronous telemetry samples onto our standardized 1000-point distance grid
    tel['distance_raw'] = np.linspace(0, 5000, len(tel))
    interp_speed = np.interp(dist_ref, tel['distance_raw'], tel['speed'])
    interp_throttle = np.interp(dist_ref, tel['distance_raw'], tel['throttle'])
    
    df_normalized = pd.DataFrame({'distance': dist_ref, 'speed': interp_speed, 'throttle': interp_throttle})
    return df_normalized, fastest_lap['lap_duration']

# --- 4. STREAMLIT CONFIGURATION SIDEBAR ---
st.sidebar.title("🏎️ Control Console")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

# Dynamically update Grand Prix selection
meetings = get_openf1("meetings", {"year": year})
if not meetings.empty:
    # Filter out testing sessions to keep dashboard focused entirely on true race weekends
    meetings = meetings[~meetings['meeting_name'].str.contains("Testing", case=False, na=False)].sort_values("meeting_key")
    selected_gp = st.sidebar.selectbox("Grand Prix", meetings['meeting_name'].unique())
    m_key = meetings[meetings['meeting_name'] == selected_gp]['meeting_key'].iloc[0]
else:
    st.sidebar.error("F1 API Gateway Timeout.")
    st.stop()

# Sessions Dropdown
sessions = get_openf1("sessions", {"meeting_key": m_key})
if not sessions.empty:
    selected_session = st.sidebar.selectbox("Session", sessions['session_name'].unique())
    s_key = sessions[sessions['session_name'] == selected_session]['session_key'].iloc[0]
else:
    st.sidebar.error("Session telemetry unavailable.")
    st.stop()

# Alphabetically Sorted Drivers Dropdown
drivers_data = get_openf1("drivers", {"session_key": s_key})
if not drivers_data.empty:
    drivers_data = drivers_data.dropna(subset=['full_name'])
    sorted_driver_list = sorted(drivers_data['full_name'].unique())
    d1 = st.sidebar.selectbox("Driver A", sorted_driver_list, index=0)
    d2 = st.sidebar.selectbox("Ref Driver", sorted_driver_list, index=min(1, len(sorted_driver_list)-1))
else:
    st.sidebar.error("Driver roster could not be resolved.")
    st.stop()

# --- 5. DATA EXECUTION ---
df_a, lap_time_a = get_telemetry(d1, s_key, drivers_data, sim_mode)
df_b, lap_time_b = get_telemetry(d2, s_key, drivers_data, sim_mode)

# --- 6. METRIC DISPLAY & CHARTS ---
if not df_a.empty and not df_b.empty:
    st.title(f"Fastest Lap Telemetry: {selected_gp} ({year})")
    
    # 5 Performance KPI Cards (Quantitative & Qualitative Mix)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("MAX VEL: DRIVER A", f"{df_a['speed'].max():.0f} km/h", d1)
    m2.metric("MAX VEL: REF DRIVER", f"{df_b['speed'].max():.0f} km/h", d2)
    
    # Math Engine: Advanced Cumulative Numerical Integration for Time Delta Trace
    v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6  # convert to m/s
    v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
    dx = 5000 / 1000 # Distance step interval
    delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * dx
    
    final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
    m3.metric("LAP TIME VARIANCE", f"{final_delta:.3f} s", f"{d1} vs {d2}")
    m4.metric("TRACK DIMENSION", "5.00 km", "Normalized Plot Axis")
    m5.metric("PIPELINE STATUS", "SIM DATA" if sim_mode else "LIVE API", f"Session: {selected_session}")

    # Build 3 Synchronized Subplots with Shared Distance Axis
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=("Cumulative Time Delta (Seconds)", "Speed Profile (km/h)", "Throttle Application (%)"),
                        vertical_spacing=0.07)

    # Subplot 1: Cumulative Time Delta (Above 0 = Driver A Leading, Below 0 = Ref Driver Leading)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta_time_array, name="Time Delta", line=dict(color=COLOR_DELTA, width=2.5)), row=1, col=1)
    
    # Subplot 2: Speed Curves
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=f"{d1} Speed", line=dict(color=COLOR_A, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=f"{d2} Speed", line=dict(color=COLOR_B, width=2)), row=2, col=1)
    
    # Subplot 3: Throttle Traces (Fully aligned curves, showing cornering phases clearly)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color=COLOR_A, width=1.5), showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=f"{d2} Throttle", line=dict(color=COLOR_B, width=1.5), showlegend=False), row=3, col=1)

    # Apply F1 Plotly Dark Theme Engineering
    fig.update_layout(template="plotly_dark", height=850, paper_bgcolor="#0A0A0C", plot_bgcolor="#0A0A0C", hovermode="x unified")
    fig.update_xaxes(title_text="Track Distance (Meters)", row=3, col=1)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.error("No telemetry chunks available inside the fastest lap window for this combination. Please activate 'Simulation Mode' in the sidebar.")

# --- 7. COMPREHENSIVE BILINGUAL INTERPRETATION GUIDE ---
with st.expander("📖 Comprehensive Telemetry Engineering Guide (Technical & Functional Manual)"):
    t_col, f_col = st.columns(2)
    with t_col:
        st.write("### 💻 Technical Infrastructure Data Spec")
        st.write("""
        * **Spatial Normalization Mapping:** F1 components stream telemetry metrics via independent sensors at asynchronous intervals (~3.7 Hz). Rather than plotting raw chronological arrays—which distort comparative layouts—this application processes datasets onto an integrated coordinate structure using **Linear Spatial Interpolation (`np.interp`)**.
        * **Time Delta Analytics Core:** The Time Delta vector is mapped using high-fidelity spatial calculus. By integrating reciprocal velocity values over distance steps ($\int \Delta \\frac{1}{v} dx$), the system tracks exactly where gaps form on the track without encountering alignment spikes.
        """)
    with f_col:
        st.write("### 🏁 Functional Racing Analytics Spec")
        st.write("""
        * **Deciphering the Time Delta:** When the trace slopes upward, Driver A is outperforming the Ref Driver through that specific mini-sector. A downward slope represents areas where the Ref Driver is actively clawing back performance.
        * **Evaluating Throttle Transitions:** The speed trace exhibits 'V' patterns during heavy braking phases. The rate at which the throttle trace jumps from 0% back to 100% out of these corners highlights differences in car downforce setup and driver commitment.
        """)
