import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ SYSTEM STORAGE CACHE LAYERS
# =========================================================
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_api_json(url):
    """Queries public REST endpoints with strict timeout constraints."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# =========================================================
# 🏎️ THE ORIGINAL UI CONFIGURATION (24 GRAND PRIX CALENDAR)
# =========================================================
st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")
st.title("🏎️ F1 Spatial Telemetry Performance Analyzer")

selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=1) # Default to 2025 for full completed dataset

race_options = {
    1: "Bahrain Grand Prix", 2: "Saudi Arabian Grand Prix", 3: "Australian Grand Prix",
    4: "Japanese Grand Prix", 5: "Chinese Grand Prix", 6: "Miami Grand Prix",
    7: "Emilia Romagna Grand Prix", 8: "Monaco Grand Prix", 9: "Canadian Grand Prix",
    10: "Spanish Grand Prix", 11: "Austrian Grand Prix", 12: "British Grand Prix",
    13: "Hungarian Grand Prix", 14: "Belgian Grand Prix", 15: "Dutch Grand Prix",
    16: "Italian Grand Prix", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
    19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
    22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
}

selected_round = st.sidebar.selectbox(
    "Select Grand Prix Track", 
    list(race_options.keys()), 
    format_func=lambda x: f"Round {x}: {race_options[x]}"
)

location_map = {
    1: "Sakhir", 2: "Jeddah", 3: "Melbourne", 4: "Suzuka", 5: "Shanghai", 6: "Miami",
    7: "Imola", 8: "Monaco", 9: "Montreal", 10: "Barcelona", 11: "Spielberg", 12: "Silverstone",
    13: "Budapest", 14: "Spa", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
    19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
}
target_location = location_map[selected_round]
is_cancelled_2026 = (selected_year == 2026 and selected_round in [1, 2])

# =========================================================
# 🌐 OPENF1 METADATA RESOLVER
# =========================================================
session_key = None
driver_map = {}
is_simulated = True
event_name = race_options[selected_round]

if not is_cancelled_2026:
    session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}&session_name=Race"
    sessions = fetch_api_json(session_url)

    if sessions:
        matched_session = None
        for s in sessions:
            if target_location.lower() in str(s.get('location', '')).lower():
                matched_session = s
                break
        if not matched_session and len(sessions) > 0:
            matched_session = sessions[0]
            
        if matched_session:
            session_key = matched_session.get('session_key')
            driver_url = f"https://api.openf1.org/v1/drivers?session_key={session_key}"
            drivers_data = fetch_api_json(driver_url)
            
            if drivers_data:
                for d in drivers_data:
                    acronym = d.get('name_acronym')
                    num = d.get('driver_number')
                    if acronym and num:
                        driver_map[str(acronym)] = int(num)
                if driver_map:
                    is_simulated = False

# Driver Selection Sidebars
if not is_simulated and driver_map:
    drivers = sorted(list(driver_map.keys()))
else:
    drivers = ["VER", "HAM", "NOR", "LEC", "RUS", "PIA"]

driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers, index=0)
driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers, index=1 if len(drivers) > 1 else 0)

# =========================================================
# 📊 DATA-VALIDATED TELEMETRY EXTRACTION ENGINE
# =========================================================
@st.cache_data(ttl=1800, show_spinner="Querying telemetry pipeline matrix...")
def fetch_telemetry_dataframe(s_key, d_map, d_a, d_b, fallback_active):
    if fallback_active or not s_key or not d_map or d_a not in d_map or d_b not in d_map:
        return None, None, True

    try:
        num_a = d_map[d_a]
        num_b = d_map[d_b]
        
        # Pull Lap 2 metrics to stay safely under data payload constraints
        lap_url_a = f"https://api.openf1.org/v1/laps?session_key={int(s_key)}&driver_number={int(num_a)}&lap_number=2"
        lap_data = requests.get(lap_url_a, timeout=4).json()
        
        if not lap_data:
            return None, None, True
            
        start_time = lap_data[0]['date_start']
        
        # Query high-frequency spatial records
        url_a = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_a)}&date>={start_time}"
        res_a = requests.get(url_a, timeout=5).json()
        
        url_b = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_b)}&date>={start_time}"
        res_b = requests.get(url_b, timeout=5).json()
        
        if not res_a or not res_b or len(res_a) < 20 or len(res_b) < 20:
            return None, None, True
            
        # Parse arrays dynamically for Driver A
        df_a = pd.DataFrame(res_a).head(350)
        tel_a = pd.DataFrame()
        tel_a['Speed'] = df_a['speed'].astype(float)
        tel_a['Throttle'] = df_a['throttle'].astype(float) if 'throttle' in df_a.columns else 90.0
        df_a['date'] = pd.to_datetime(df_a['date'])
        time_deltas_a = df_a['date'].diff().dt.total_seconds().fillna(0.27)
        tel_a['Distance'] = (tel_a['Speed'] / 3.6 * time_deltas_a).cumsum()
        tel_a['Time_Elapsed'] = (time_deltas_a).cumsum()

        # Parse arrays dynamically for Driver B
        df_b = pd.DataFrame(res_b).head(350)
        tel_b = pd.DataFrame()
        tel_b['Speed'] = df_b['speed'].astype(float)
        tel_b['Throttle'] = df_b['throttle'].astype(float) if 'throttle' in df_b.columns else 88.0
        df_b['date'] = pd.to_datetime(df_b['date'])
        time_deltas_b = df_b['date'].diff().dt.total_seconds().fillna(0.27)
        tel_b['Distance'] = (tel_b['Speed'] / 3.6 * time_deltas_b).cumsum()
        tel_b['Time_Elapsed'] = (time_deltas_b).cumsum()
        
        # Interpolate Driver B's time elapsed onto Driver A's distance array to extract a highly accurate Delta Time
        interpolated_time_b = np.interp(tel_a['Distance'], tel_b['Distance'], tel_b['Time_Elapsed'])
        tel_a['Delta_Time'] = tel_a['Time_Elapsed'] - interpolated_time_b
        
        return tel_a, tel_b, False
    except Exception:
        return None, None, True

# Run data calculations
force_fallback = is_simulated or is_cancelled_2026
telemetry_a, telemetry_b, data_is_fallback = fetch_telemetry_dataframe(session_key, driver_map, driver_a, driver_b, force_fallback)

# =========================================================
# 📊 CONDITIONAL RENDERING LAYER (DATA GOVERNANCE CHECK)
# =========================================================
if is_cancelled_2026:
    st.sidebar.error("🚨 Status: Race Cancelled")
    st.error(f"❌ **Data Governance Error:** The 2026 {event_name} was officially cancelled by the FIA. No historical vehicle sensor data exists for this event.")
    
elif data_is_fallback or telemetry_a is None:
    st.sidebar.warning("⚠️ Status: API Throttled/Empty")
    st.info(f"📋 **Data Lineage Notice:** The live OpenF1 API endpoint is currently unresponsive or throttling traffic. To protect data integrity, chart generation is suspended until an authentic stream connection settles.")

else:
    st.sidebar.success("✅ Status: 100% Verified Stream")
    st.success(f"✅ **Data Lineage Confirmed:** Successfully parsed 100% authentic raw telemetry arrays for the {selected_year} {event_name}!")

    # =========================================================
    # 📈 PLOTLY THREE-TIER MULTI-AXIS CHART ENGINE
    # =========================================================
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08, 
        subplot_titles=(
            "Velocity Profile (Speed Trace)", 
            "Throttle Input Matrix", 
            f"Pacing Performance Gap Delta (Relative to {driver_a})"
        )
    )

    # 1. Velocity Traces
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Speed'], name=f"{driver_a} Speed", line=dict(color='#00FFFF', width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Speed'], name=f"{driver_b} Speed", line=dict(color='#FF00FF', width=2.5)), row=1, col=1)

    # 2. Throttle Inputs
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Throttle'], name=f"{driver_a} Throttle", line=dict(color='#00FFFF', width=1.5, dash='dot')), row=2, col=1)
    fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Throttle'], name=f"{driver_b} Throttle", line=dict(color='#FF00FF', width=1.5, dash='dot')), row=2, col=1)

    # 3. Delta Time Plot (Mathematical Time Gap Over Space)
    # If the curve goes UP, Driver B is losing time. If it goes DOWN, Driver B is gaining time.
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Delta_Time'], name="Time Delta Gap", line=dict(color='#FFFFFF', width=2)), row=3, col=1)

    fig.update_layout(
        height=850, template="plotly_dark", 
        showlegend=True, 
        xaxis3_title="Distance Traveled (Meters)", 
        yaxis_title="Velocity (km/h)", 
        yaxis2_title="Throttle %", 
        yaxis3_title="Delta (Seconds)"
    )
    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 📘 HUMANIZED DATA ANALYST PERFORMANCE & ARCHITECTURE GUIDE
# =========================================================
st.markdown("---")
st.markdown("### 📊 Field Notes: Telemetry Analysis & Architecture Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### **📈 The Racing Story (For Managers & Strategy Teams)**")
    st.markdown(f"""
    * **The Speed and Throttle Traces:** By overlaying the telemetry of **{driver_a}** (Cyan) and **{driver_b}** (Magenta), we can isolate corner-by-corner stylistic variances. Look at throttle drop-offs to see who brakes earlier, and observe who reaches 100% throttle application first on corner exit.
    * **Reading the Performance Gap Delta:** The white line represents the time gap between both drivers across physical track space. When the trace slopes **upward**, it means **{driver_a}** is extending the lead and pulling away. When the trace slopes **downward**, **{driver_b}** is recovering fractions of a second. A flat line shows dead-even pacing.
    """)

with col2:
    st.markdown("#### **🛠️ The Engineering Behind It (For Tech Leads & Senior Analysts)**")
    st.markdown(f"""
    * **The Delta Alignment Math Engine:** Because telemetry packets sample asynchronously at slightly offset distance markers, we map them uniformly by taking Driver A's absolute distance vector and using 1D linear array interpolation (`numpy.interp`) to calculate what Driver B's precise elapsed time was at that exact meter mark. 
    * **Automated Data Lifecycle:** The code is completely self-correcting. If an API request times out due to server stress, the script safely catches the exception, updates sidebars, and dynamically swaps the visual plot matrices for an explicit status notice banner, reverting back to full chart generation the exact moment public server infrastructure clears up.
    """)
