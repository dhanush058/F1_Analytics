import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ LIGHTWEIGHT API DATA WAREHOUSE LAYER
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_api_json(url):
    try:
        response = requests.get(url, timeout=12)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# =========================================================
# 🏎️ THE ORIGINAL UI CONFIGURATION (EXPANDED TO ALL 24 GPs)
# =========================================================
st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")
st.title("🏎️ F1 Spatial Telemetry Performance Analyzer")

selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=0)

# Full 24 Grand Prix Championship Configuration
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

# Structural location name translator map for OpenF1 query parameters
location_map = {
    1: "Sakhir", 2: "Jeddah", 3: "Melbourne", 4: "Suzuka", 5: "Shanghai", 6: "Miami",
    7: "Imola", 8: "Monaco", 9: "Montreal", 10: "Barcelona", 11: "Spielberg", 12: "Silverstone",
    13: "Budapest", 14: "Spa-Francorchamps", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
    19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
}
target_location = location_map[selected_round]

# Explicitly flag cancelled historical events in 2026 to ensure accurate reporting
is_cancelled_2026 = (selected_year == 2026 and selected_round in [1, 2])

# =========================================================
# 🌐 OPENF1 METADATA RESOLVER
# =========================================================
session_key = None
driver_map = {}
is_simulated = True
event_name = race_options[selected_round]

if not is_cancelled_2026:
    session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}"
    sessions = fetch_api_json(session_url)

    if sessions:
        matched_session = None
        for s in sessions:
            loc_str = str(s.get('location', '')).lower()
            meet_str = str(s.get('meeting_name', '')).lower()
            name_str = str(s.get('session_name', '')).lower()
            
            # Check for the correct track location match
            if target_location.lower() in loc_str or target_location.lower() in meet_str:
                # OpenF1 labels competitive Sunday tracks as 'Race' or 'Grand Prix'
                if "race" in name_str or "grand prix" in name_str:
                    matched_session = s
                    break
                    
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

# =========================================================
# ORIGINAL DRIVER MENUS & SIDEBAR
# =========================================================
if not is_simulated and driver_map:
    st.sidebar.success("✅ **Data Lineage:** Authenticated API Stream Match")
    drivers = sorted(list(driver_map.keys()))
else:
    st.sidebar.info("ℹ️ **Data Lineage:** Simulation Fail-Safe Engaged")
    drivers = ["VER", "HAM", "NOR", "LEC", "RUS", "PIA"]

driver_a = st.sidebar.selectbox("Select Driver A", drivers, index=0)
driver_b = st.sidebar.selectbox("Select Driver B", drivers, index=1 if len(drivers) > 1 else 0)

# =========================================================
# 📊 TIME-BOUND SPATIAL TELEMETRY PIPELINE EXTRACTION
# =========================================================
@st.cache_data(ttl=3600, show_spinner="Extracting high-frequency telemetry grid...")
def fetch_telemetry_dataframe(s_key, d_map, d_a, d_b, fallback_active):
    """
    Retrieves real telemetry data arrays. If data is missing, un-raced, or marked as fallback,
    generates isolated sine profiles labeled explicitly as simulated.
    """
    angles = np.linspace(0, 4 * np.pi, 600)
    mock_a = pd.DataFrame({
        'Speed': 210 + np.sin(angles) * 65 + np.random.normal(0, 1.5, 600),
        'Throttle': 55 + np.sin(angles) * 40,
        'Distance': np.linspace(0, 5300, 600)
    })
    mock_b = pd.DataFrame({
        'Speed': 205 + np.sin(angles + 0.08) * 68 + np.random.normal(0, 1.5, 600),
        'Throttle': 52 + np.sin(angles + 0.08) * 42,
        'Distance': np.linspace(0, 5300, 600)
    })

    if fallback_active or not s_key or not d_map or d_a not in d_map or d_b not in d_map:
        return mock_a, mock_b, True

    try:
        num_a = d_map[d_a]
        num_b = d_map[d_b]
        
        url_a = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_a)}"
        res_a = requests.get(url_a, timeout=12).json()
        
        url_b = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_b)}"
        res_b = requests.get(url_b, timeout=12).json()
        
        # Check if the arrays exist and contain telemetry entries
        if not res_a or not res_b or len(res_a) < 50 or len(res_b) < 50:
            return mock_a, mock_b, True
            
        # Parse and process Driver A
        df_a = pd.DataFrame(res_a).head(600)
        tel_a = pd.DataFrame()
        tel_a['Speed'] = df_a['speed'].astype(float)
        tel_a['Throttle'] = df_a['throttle'].astype(float) if 'throttle' in df_a.columns else 90.0
        df_a['date'] = pd.to_datetime(df_a['date'])
        time_deltas_a = df_a['date'].diff().dt.total_seconds().fillna(0.27)
        tel_a['Distance'] = (tel_a['Speed'] / 3.6 * time_deltas_a).cumsum()

        # Parse and process Driver B
        df_b = pd.DataFrame(res_b).head(600)
        tel_b = pd.DataFrame()
        tel_b['Speed'] = df_b['speed'].astype(float)
        tel_b['Throttle'] = df_b['throttle'].astype(float) if 'throttle' in df_b.columns else 88.0
        df_b['date'] = pd.to_datetime(df_b['date'])
        time_deltas_b = df_b['date'].diff().dt.total_seconds().fillna(0.27)
        tel_b['Distance'] = (tel_b['Speed'] / 3.6 * time_deltas_b).cumsum()
        
        return tel_a, tel_b, False
    except Exception:
        return mock_a, mock_b, True

# Force simulation behavior instantly if the race was cancelled or hasn't occurred yet
force_fallback = is_simulated or is_cancelled_2026
telemetry_a, telemetry_b, data_is_fallback = fetch_telemetry_dataframe(session_key, driver_map, driver_a, driver_b, force_fallback)

# =========================================================
# 📈 TRANSPARENT DATA ANNOUNCEMENT BANNERS
# =========================================================
if is_cancelled_2026:
    st.warning(f"⚠️ **Data Integrity Notice:** The 2026 {event_name} was officially called off/cancelled by the FIA. The charts below display synthetic baseline traces for software verification.")
elif data_is_fallback:
    st.info(f"📊 **Data Integrity Notice:** Telemetry streams for the {selected_year} {event_name} are either uncompleted or processing. Displaying baseline calibration traces until live session data settles.")
else:
    st.success(f"✅ **Data Lineage Confirmed:** Successfully parsed 100% authentic raw telemetry arrays for the {selected_year} {event_name}!")

# =========================================================
# 📈 PLOTLY RENDERING LAYER
# =========================================================
label_prefix = "[SIMULATED] " if data_is_fallback else ""

fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.15, 
    subplot_titles=(f"{label_prefix}Velocity Profile (Speed Trace)", f"{label_prefix}Throttle Input Matrix")
)

# Row 1: Speed Performance Curves
fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Speed'], name=f"{label_prefix}{driver_a} Speed", line=dict(color='#00FFFF', width=2.5)), row=1, col=1)
fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Speed'], name=f"{label_prefix}{driver_b} Speed", line=dict(color='#FF00FF', width=2.5)), row=1, col=1)

# Row 2: Throttle Inputs Matrix
fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Throttle'], name=f"{label_prefix}{driver_a} Throttle", line=dict(color='#00FFFF', width=1.5, dash='dot')), row=2, col=1)
fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Throttle'], name=f"{label_prefix}{driver_b} Throttle", line=dict(color='#FF00FF', width=1.5, dash='dot')), row=2, col=1)

fig.update_layout(
    height=650, 
    template="plotly_dark", 
    title_text=f"{label_prefix}Telemetry Comparison Profile: {event_name} ({selected_year})", 
    showlegend=True,
    xaxis2_title="Distance Traveled (Meters)",
    yaxis_title="Velocity (km/h)",
    yaxis2_title="Throttle Application %"
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
    * **What are we actually looking at?** Think of this dashboard as an X-ray of a driver's driving style. By overlaying the performance curves of **{driver_a}** (Cyan) and **{driver_b}** (Magenta), we can see exactly where one driver is hunting down lap time or dropping it.
    * **Reading the Speed Trace:** Look for the gaps where the lines separate. If the Cyan line peaks higher on a straightaway, **{driver_a}** either has a stronger engine map, a better aerodynamic slipstream, or carried more momentum out of the previous corner. 
    * **Decoding the Gas Pedal (Throttle Matrix):** Every time you see these lines plunge off a cliff toward 0%, that is a driver slamming on the brakes for a corner apex. Who rolls back onto the throttle first? Who is more aggressive? The faster driver isn't always the one with the highest top speed—it's usually the one who balances these inputs smoothly.
    * **The Business Takeaway:** In a real-world business or team environment, this visual translation is how analysts hand actionable feedback to managers and drivers to shave off crucial fractions of a second.
    """)

with col2:
    st.markdown("#### **🛠️ The Engineering Behind It (For Tech Leads & Senior Analysts)**")
    st.markdown(f"""
    * **Bypassing the Cloud Hosting Block:** Most public cloud servers (like Streamlit Cloud) are permanently firewalled by major sports networks to protect live timing streams. Instead of giving up or manually uploading CSVs every week, I mapped this pipeline directly to an unblocked REST endpoint, allowing the app to fetch data completely hands-free.
    * **Resolving the Distance Variable:** The raw telemetry stream doesn't give us a clean 'Distance' column out of the box—it only logs metrics against absolute date and time stamps. 
    * **The Data Fix:** To plot these traces side-by-side accurately over space rather than time, I converted the velocity vectors from km/h to meters per second, calculated the time deltas between high-frequency telemetry frames (~3.7 Hz), and applied a cumulative sum (`cumsum()`) integration to map out a precise distance baseline.
    * **Defensive Error Handling:** Data breaks in production. By engineering an automatic schema-matching fallback layer, the application catches missing or cancelled race packets (like the cancelled 2026 rounds) and cleanly generates baseline profiles, keeping the user interface up and functional 100% of the time.
    """)
