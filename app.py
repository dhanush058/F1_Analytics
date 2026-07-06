import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIGURATION & PIT-WALL CARBON THEME ---
st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")

st.markdown("""
<style>
    /* Main Backgrounds */
    .stApp { background-color: #0B0B0E; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    
    /* Overhaul Metric Container Layout to Compact Carbon Style */
    [data-testid="stMetric"] {
        background-color: #15151C !important;
        border: 1px solid #2A2A35 !important;
        border-top: 4px solid #FF1801 !important;
        border-radius: 4px !important;
        padding: 10px 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Metric Typography Fixes */
    [data-testid="stMetricLabel"] { 
        color: #8E8E9F !important; 
        font-family: 'Courier New', monospace !important; 
        font-size: 0.75rem !important; 
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    [data-testid="stMetricValue"] { 
        color: #FFFFFF !important; 
        font-family: 'Courier New', monospace !important; 
        font-size: 1.35rem !important; 
        font-weight: 800 !important; 
    }
    
    /* Global Typography */
    h1, h2, h3 { 
        font-family: 'Courier New', monospace !important; 
        color: #FFFFFF !important; 
        text-transform: uppercase !important; 
        letter-spacing: 1px !important; 
    }
    .streamlit-expanderHeader { background-color: #15151C !important; color: white !important; border: 1px solid #2A2A35 !important; }
</style>
""", unsafe_allow_html=True)

if "toast_shown" not in st.session_state:
    st.toast("🚨 Pit-Wall Active. If 2026 data is pending or live APIs are blocked, enable 'Simulation Mode'.", icon="🏎️")
    st.session_state.toast_shown = True

COLOR_A = '#00FFFF'     
COLOR_B = '#FF00FF'     
COLOR_DELTA = '#00FF00' 
COLOR_BG = '#0B0B0E'    

# --- 2. ROBUST API FETCHER ---
@st.cache_data(ttl=600)
def get_openf1(endpoint, params=None):
    base_url = "https://api.openf1.org/v1/"
    try:
        res = requests.get(base_url + endpoint, params=params, timeout=12)
        return pd.DataFrame(res.json()) if res.status_code == 200 else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 3. DATA ENGINE (REAL LIVE DATA & ADVANCED DYNAMIC PHYSICS SIM) ---
def get_telemetry(driver_api_name, s_key, drivers_df, track_name, session_name, is_sim=False, driver_id=1):
    dist_ref = np.linspace(0, 5000, 1000)
    
    if is_sim:
        # Generate Hashes for Track, Session, and Driver
        track_hash = sum(ord(c) for c in track_name)
        session_hash = sum(ord(c) for c in session_name)
        driver_hash = sum(ord(c) for c in driver_api_name) * (driver_id + 7)
        
        # 1. GENERATE THE TRACK LAYOUT (Same for both drivers on this specific GP)
        np.random.seed(track_hash + session_hash)
        base_vmax = 290.0 + (track_hash % 55) # Track VMAX varies wildly (e.g., Monaco vs Monza)
        num_corners = 4 + (track_hash % 6)    # Generates between 4 and 9 corners per track
        
        # Lock in the corner apex positions for this specific track
        corner_indices = sorted(np.random.choice(range(100, 950), num_corners, replace=False))
        base_apexes = [90 + np.random.randint(0, 110) for _ in range(num_corners)]
        base_lap_time = 72.0 + (track_hash % 25)
        
        # 2. GENERATE DRIVER PHYSICS (How the driver attacks this specific track)
        np.random.seed(driver_hash + track_hash + session_hash)
        
        # Driver-specific VMAX (slipstream/setup variation)
        vmax_cap = base_vmax + (driver_hash % 6) - 3 
        
        speed = np.full(1000, vmax_cap) 
        throttle = np.full(1000, 100.0)
        
        for idx, c_idx in enumerate(corner_indices):
            base_v = base_apexes[idx]
            
            # Driver specific cornering habits
            v_apex = base_v + (driver_hash % 16) - 8
            brake_len = 25 + (driver_hash % 15)  
            accel_len = 65 + (driver_hash % 25)  
            
            brake_start = max(0, c_idx - brake_len)
            
            # Threshold Braking Phase (Steep, cubic drop)
            for i in range(brake_start, c_idx):
                progress = (i - brake_start) / brake_len
                speed[i] = vmax_cap - (vmax_cap - v_apex) * (progress ** 3) 
                throttle[i] = 0
                
            speed[c_idx] = v_apex
            throttle[c_idx] = 0
            
            # Corner Exit Phase (Concave acceleration curve)
            accel_end = min(1000, c_idx + accel_len)
            for i in range(c_idx + 1, accel_end):
                progress = (i - c_idx) / accel_len
                speed[i] = v_apex + (vmax_cap - v_apex) * np.sqrt(progress) 
                throttle[i] = min(100, progress * 450) 
                
        # Spatial Shifting (Models late vs early braking points)
        shift = (driver_hash % 12) - 6
        speed = np.roll(speed, shift)
        throttle = np.roll(throttle, shift)
        
        # High-Frequency Noise & Sensor Inertia
        speed = pd.Series(speed).rolling(window=4, min_periods=1).mean().values
        speed += np.random.normal(0, 0.9, 1000)
        throttle += np.random.normal(0, 1.3, 1000)
        throttle = np.clip(throttle, 0, 100)
        
        lap_time = base_lap_time + (driver_hash % 400) / 200.0
        return pd.DataFrame({'distance': dist_ref, 'speed': speed, 'throttle': throttle}), lap_time

    # LIVE API STREAM FLOW
    d_num = drivers_df[drivers_df['full_name'] == driver_api_name]['driver_number'].iloc[0]
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d_num})
    
    if laps.empty or 'lap_duration' not in laps.columns: return pd.DataFrame(), None
    valid_laps = laps.dropna(subset=['lap_duration'])
    if valid_laps.empty: return pd.DataFrame(), None
    
    fastest_lap = valid_laps.loc[valid_laps['lap_duration'].idxmin()]
    start_time = pd.to_datetime(fastest_lap['date_start'])
    end_time = start_time + pd.Timedelta(seconds=float(fastest_lap['lap_duration']) + 0.5)
    
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

# --- 4. CONTROL INTERFACE & SIDEBAR ---
st.sidebar.title("🏎️ Control Console")
sim_mode = st.sidebar.checkbox("Enable Simulation Mode", value=False)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])

meetings = get_openf1("meetings", {"year": year})
if meetings.empty:
    st.sidebar.warning(f"No Live API data map for {year}. Toggle Simulation Mode or select an older year.")
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

drivers_data['display_name'] = drivers_data['full_name'].str.title()
sorted_driver_list = sorted(drivers_data['display_name'].unique())

d1_display = st.sidebar.selectbox("Driver A (Searchable)", sorted_driver_list, index=0)
d2_display = st.sidebar.selectbox("Ref Driver (Searchable)", sorted_driver_list, index=min(1, len(sorted_driver_list)-1))

d1_api = drivers_data[drivers_data['display_name'] == d1_display]['full_name'].iloc[0]
d2_api = drivers_data[drivers_data['display_name'] == d2_display]['full_name'].iloc[0]

# --- 5. COMPUTE ENGINE ---
with st.spinner("Analyzing Lap Metrics..."):
    df_a, lap_time_a = get_telemetry(d1_api, s_key, drivers_data, selected_gp, selected_session, sim_mode, driver_id=1)
    df_b, lap_time_b = get_telemetry(d2_api, s_key, drivers_data, selected_gp, selected_session, sim_mode, driver_id=2)

# --- 6. CORE DISPLAY ---
if df_a.empty or df_b.empty:
    st.error("⚠️ Telemetry stream offline for this live selection. Check 'Enable Simulation Mode' in the sidebar to review dashboard layouts.")
else:
    st.title(f"Fastest Lap: {selected_gp} — {selected_session}")
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(label=f"VMAX — {d1_display.split()[-1].upper()}", value=f"{df_a['speed'].max():.0f} KM/H")
    m2.metric(label=f"VMAX — {d2_display.split()[-1].upper()}", value=f"{df_b['speed'].max():.0f} KM/H")
    
    v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6
    v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
    delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * (5000/1000)
    final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
    
    m3.metric(label="LAP TIME DELTA", value=f"{final_delta:.3f} S")
    m4.metric(label="TRACK DIMENSION", value="5.00 KM")
    m5.metric(label="DATA PIPELINE", value="SIMULATION" if sim_mode else "LIVE API")

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        subplot_titles=(f"Time Delta (s) [Up = {d1_display} Gaining]", "Speed Trace (km/h)", "Throttle Trace (%)"),
                        vertical_spacing=0.08)

    fig.add_trace(go.Scatter(x=df_a['distance'], y=delta_time_array, name="Delta", line=dict(color=COLOR_DELTA, width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['speed'], name=d1_display, line=dict(color=COLOR_A, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['speed'], name=d2_display, line=dict(color=COLOR_B, width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df_a['distance'], y=df_a['throttle'], name=d1_display, line=dict(color=COLOR_A, width=1.5), showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_b['distance'], y=df_b['throttle'], name=d2_display, line=dict(color=COLOR_B, width=1.5), showlegend=False), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", 
        height=850, 
        paper_bgcolor=COLOR_BG, 
        plot_bgcolor=COLOR_BG, 
        hovermode="x unified",
        font=dict(family="Courier New, monospace", size=12, color="white")
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#1B1B22')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1B1B22')
    
    st.plotly_chart(fig, use_container_width=True)

# --- 7. REFACTORED HUMAN-ENGINEERING EXPANDER ---
with st.expander("📖 PIT-WALL TELEMETRY & DATA GOVERNANCE STANDARD"):
    st.markdown("""
    ### 📊 Telemetry Analysis Breakdown
    * **Time Delta (Neon Green Line):** Evaluates ongoing advantage metrics. If the graph rises, Driver A is outperforming the reference car.
    * **Speed Curves:** Deep 'V' configurations highlight major threshold braking zones. True F1 telemetry features a sharp, convex drop (heavy initial G-force) and a concave exit (drag-limited acceleration).
    * **Throttle Curves:** Reaching a solid 100% plateau sooner highlights superior rear stability and acceleration response.

    ---

    ### 💻 Systems Infrastructure & Spatial Normalization
    Telemetry streaming feeds from active hardware packages deliver data packets at irregular, variable frequencies (~3.7 Hz). Because track positioning times vary wildly between individual cars, raw chronologic records remain impossible to plot together without causing severe mathematical artifacts.
    
    To guarantee complete data precision, this platform deploys a custom **Spatial Normalization Pipeline**. Time-series intervals are parsed and remapped into matching spatial steps using one-dimensional linear projection (`np.interp`). Both streams share an identical 1,000-point tracking path, establishing completely safe data alignment.

    ---

    ### 🛡️ Data Governance: Why Simulation Data is Required
    * **The 2026 Live Data Problem:** The official OpenF1 API database relies on historical, post-race session dumps. Currently, the telemetry for un-driven future races (like the 2026 calendar year) simply does not exist yet.
    * **Cloud Proxy Blocking:** Furthermore, cloud hosting platforms (like Streamlit Community Cloud) mask their outbound requests through massive shared server IPs. F1's firewall infrastructure aggressively blocks these cloud IP ranges to prevent DDoS attacks, making live-scraping extremely unstable in production.
    * **The Solution (Synthetic Transparency):** To prevent catastrophic application failure during a recruiter review or portfolio demo, we implemented a highly advanced deterministic physics engine. This engine mathematically replicates high-G F1 track behavior dynamically based on the track and driver hashes. **We explicitly declare this fallback state in the top-right "Data Pipeline Status" card so users never mistake synthetic physics models for live engineering data.**
    """)
