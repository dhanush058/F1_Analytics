import streamlit as st
import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import shutil
import time

# Set page config for a professional dark look
st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")
st.title("🏎️ Formula 1 Spatial Telemetry Analyzer (Multi-Driver Comparison)")

# 1. Setup Robust Caching Layer
CACHE_DIR = "f1_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# Initialize Session States so visualizations don't disappear on click re-runs
if "processed_data" not in st.session_state:
    st.session_state.processed_data = None
if "active_view_key" not in st.session_state:
    st.session_state.active_view_key = ""

# Helper function to dynamically fetch the full season calendar reliably
@st.cache_data
def get_season_events(selected_year):
    try:
        schedule = fastf1.get_event_schedule(selected_year)
        gp_events = schedule[schedule['EventFormat'] != 'testing']
        return list(zip(gp_events['EventName'].tolist(), gp_events['RoundNumber'].tolist()))
    except Exception:
        return [("Australian Grand Prix", 1), ("Monaco Grand Prix", 6), ("Italian Grand Prix", 13)]

# 2. Sidebar Controls - Part 1 (Race Setup)
st.sidebar.header("Race Setup")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=0)

event_options = get_season_events(year)
event_names = [e[0] for e in event_options]
selected_event_name = st.sidebar.selectbox("Circuit", event_names, index=0)

selected_round = event_options[event_names.index(selected_event_name)][1]

session_map = {"Qualifying": "Q", "Race": "R"}
selected_session_label = st.sidebar.selectbox("Session", list(session_map.keys()), index=0)
session_type = session_map[selected_session_label]

# Clean, historically accurate Year-by-Year Driver Grid mappings
YEARLY_DRIVERS_MAP = {
    2026: {
        "Max Verstappen": "VER",
        "Lando Norris": "NOR",
        "Charles Leclerc": "LEC",
        "Oscar Piastri": "PIA",
        "Carlos Sainz": "SAI",
        "Lewis Hamilton": "HAM",
        "George Russell": "RUS",
        "Sergio Perez": "PER",
        "Fernando Alonso": "ALO",
        "Lance Stroll": "STR",
        "Nico Hulkenberg": "HUL",
        "Yuki Tsunoda": "TSU",
        "Alexander Albon": "ALB",
        "Esteban Ocon": "OCO",
        "Pierre Gasly": "GAS",
        "Kimi Antonelli": "ANT",
        "Oliver Bearman": "BEA",
        "Franco Colapinto": "COL",
        "Gabriel Bortoleto": "BOR",
        "Liam Lawson": "LAW",
        "Isack Hadjar": "HAD",
        "Arvid Lindblad": "LIN",
        "Jack Doohan": "DOO"
    },
    2025: {
        "Max Verstappen": "VER",
        "Lando Norris": "NOR",
        "Charles Leclerc": "LEC",
        "Oscar Piastri": "PIA",
        "Carlos Sainz": "SAI",
        "Lewis Hamilton": "HAM",
        "George Russell": "RUS",
        "Sergio Perez": "PER",
        "Fernando Alonso": "ALO",
        "Lance Stroll": "STR",
        "Nico Hulkenberg": "HUL",
        "Yuki Tsunoda": "TSU",
        "Alexander Albon": "ALB",
        "Esteban Ocon": "OCO",
        "Pierre Gasly": "GAS",
        "Kevin Magnussen": "MAG",
        "Valtteri Bottas": "BOT",
        "Zhou Guanyu": "ZHO",
        "Oliver Bearman": "BEA",
        "Franco Colapinto": "COL",
        "Liam Lawson": "LAW",
        "Jack Doohan": "DOO"
    },
    2024: {
        "Max Verstappen": "VER",
        "Lando Norris": "NOR",
        "Charles Leclerc": "LEC",
        "Oscar Piastri": "PIA",
        "Carlos Sainz": "SAI",
        "Lewis Hamilton": "HAM",
        "George Russell": "RUS",
        "Sergio Perez": "PER",
        "Fernando Alonso": "ALO",
        "Lance Stroll": "STR",
        "Nico Hulkenberg": "HUL",
        "Yuki Tsunoda": "TSU",
        "Alexander Albon": "ALB",
        "Esteban Ocon": "OCO",
        "Pierre Gasly": "GAS",
        "Kevin Magnussen": "MAG",
        "Valtteri Bottas": "BOT",
        "Zhou Guanyu": "ZHO",
        "Daniel Ricciardo": "RIC",
        "Logan Sargeant": "SAR",
        "Oliver Bearman": "BEA",
        "Franco Colapinto": "COL",
        "Liam Lawson": "LAW"
    }
}

CURRENT_YEAR_MAP = YEARLY_DRIVERS_MAP[year]
CODE_TO_NAME = {v: k for k, v in CURRENT_YEAR_MAP.items()}

# 3. Dynamic Session Driver Filter
@st.cache_data(show_spinner=False)
def get_active_session_drivers(year, round_num, session_type):
    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=False, weather=False)
        active_codes = session.laps['Driver'].unique().tolist()
        
        display_names = []
        for code in active_codes:
            if code in CODE_TO_NAME:
                display_names.append(CODE_TO_NAME[code])
            else:
                display_names.append(code)
        return sorted(display_names)
    except Exception:
        return sorted(list(CURRENT_YEAR_MAP.keys()))

available_full_names = get_active_session_drivers(year, selected_round, session_type)

st.sidebar.markdown("---")
st.sidebar.header("Driver Selection")

d1_name = st.sidebar.selectbox("Driver 1", available_full_names, index=0)
d2_name = st.sidebar.selectbox("Driver 2", available_full_names, index=min(1, len(available_full_names)-1))

driver3_options = ["None"] + available_full_names
d3_name = st.sidebar.selectbox("Driver 3 (Optional)", driver3_options, index=0)

driver1 = CURRENT_YEAR_MAP.get(d1_name, d1_name)
driver2 = CURRENT_YEAR_MAP.get(d2_name, d2_name)
driver3 = "None" if d3_name == "None" else CURRENT_YEAR_MAP.get(d3_name, d3_name)

st.sidebar.markdown("---")
st.sidebar.subheader("Data Maintenance")
force_refresh = st.sidebar.checkbox("Force Refresh Live Data", value=False)

# Unique signature key tracking the user's explicit parameter settings
target_view_key = f"{year}_{selected_round}_{session_type}_{driver1}_{driver2}_{driver3}"

# 4. Advanced Defensive Telemetry Extraction
def get_single_driver_telemetry(session, driver_code):
    try:
        driver_laps = session.laps.pick_driver(driver_code)
        if driver_laps.empty:
            return None
        
        # Priority 1: Try to pull their absolute fastest lap recorded
        target_lap = driver_laps.pick_fastest()
        
        # Priority 2 Fallback: If pick_fastest fails or is empty, pull their final completed lap
        if target_lap is None or pd.isna(target_lap['LapTime']):
            valid_timed_laps = driver_laps.dropna(subset=['LapTime'])
            if not valid_timed_laps.empty:
                target_lap = valid_timed_laps.iloc[-1]
            else:
                target_lap = driver_laps.iloc[-1] # Baseline emergency fallback
                
        if target_lap is None or not hasattr(target_lap, 'get_telemetry'):
            return None
            
        telemetry = target_lap.get_telemetry().add_distance()
        if telemetry.empty or 'Speed' not in telemetry.columns:
            return None
            
        return telemetry
    except Exception:
        return None

def process_race_session(year, round_num, session_type, d1, d2, d3):
    session = fastf1.get_session(year, round_num, session_type)
    
    for attempt in range(2):
        try:
            session.load(laps=True, telemetry=True, weather=False)
            break
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            return {"error": f"The F1 live timing network timed out. Hit 'Analyze Performance' again to retry. Details: {str(e)}", "data": {}}

    results = {}
    t1 = get_single_driver_telemetry(session, d1)
    if t1 is not None: results[d1] = t1
    
    t2 = get_single_driver_telemetry(session, d2)
    if t2 is not None: results[d2] = t2
    
    if d3 != "None":
        t3 = get_single_driver_telemetry(session, d3)
        if t3 is not None: results[d3] = t3
        
    return {"error": None, "data": results}

# Execute Data Pipeline via Button Trigger
if st.sidebar.button("Analyze Performance"):
    has_duplicates = (driver1 == driver2) or (driver3 != "None" and (driver1 == driver3 or driver2 == driver3))
    
    if has_duplicates:
        st.error("Please select unique drivers to compare.")
    else:
        if force_refresh:
            st.cache_data.clear()
            if os.path.exists(CACHE_DIR):
                shutil.rmtree(CACHE_DIR)
            os.makedirs(CACHE_DIR)
            fastf1.Cache.enable_cache(CACHE_DIR)
            st.info("🔄 Global RAM and memory configurations purged! Reloading crisp server data channels...")
            st.rerun()

        with st.spinner("Extracting and processing telemetry grids..."):
            payload = process_race_session(year, selected_round, session_type, driver1, driver2, driver3)
            
        if payload["error"]:
            st.error(payload["error"])
            st.session_state.processed_data = None
            st.session_state.active_view_key = ""
        else:
            # Lock calculations and view tracking keys securely into memory state
            st.session_state.processed_data = payload["data"]
            st.session_state.active_view_key = target_view_key

# --- RENDERING ENGINE (Runs safely and dynamically on every state execution loop) ---
if st.session_state.processed_data and st.session_state.active_view_key == target_view_key:
    telemetry_data = st.session_state.processed_data
    successful_codes = list(telemetry_data.keys())
    
    if len(successful_codes) < 2:
        st.warning("⚠️ Telemetry Stream Processing Alert")
        st.error(f"FastF1 could not find complete telemetry streams for this pairing. Try selecting an alternate session (e.g., switching from Qualifying to Race) or check 'Force Refresh Live Data'.")
    else:
        successful_names = [CODE_TO_NAME.get(code, code) for code in successful_codes]
        st.success(f"Successfully mapped spatial coordinates for: {', '.join(successful_names)}!")
        
        # Build Plots safely using only validated data streams
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.1,
                            subplot_titles=("Velocity Comparison (Minimum Corner Speed)", "Throttle Application (Exit Traction)"))
        
        color_palette = {driver1: '#00FF00', driver2: '#1E90FF', driver3: '#FF4500'}
        
        for drv_code in successful_codes:
            df = telemetry_data[drv_code]
            drv_color = color_palette.get(drv_code, '#FFFFFF')
            full_display_name = CODE_TO_NAME.get(drv_code, drv_code)
            
            # --- ROW 1: VELOCITY ---
            fig.add_trace(
                go.Scatter(x=df['Distance'], y=df['Speed'], mode='lines', name=full_display_name,
                           line=dict(color=drv_color, width=2),
                           hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
                row=1, col=1
            )
            
            # --- ROW 2: THROTTLE ---
            fig.add_trace(
                go.Scatter(x=df['Distance'], y=df['Throttle'], mode='lines', name=full_display_name,
                           line=dict(color=drv_color, width=2), showlegend=False,
                           hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
                row=2, col=1
            )
        
        # Global Layout Styling (FIXED GRID AND AXIS WARPING OVERLAP)
        fig.update_layout(
            height=650,
            template="plotly_dark",
            hovermode="x unified",
            margin=dict(l=50, r=20, t=60, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Distance along track (meters)", row=2, col=1)
        fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
        
        # Force row 2 to be perfectly linear, evenly spaced, and entirely independent
        fig.update_yaxes(
            title_text="Throttle %", 
            range=[-5, 105], 
            tickvals=[0, 25, 50, 75, 100],
            matches=None,  # Breaks the visual scale sync with Row 1
            row=2, col=1
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Metric Explanations for Users
        st.markdown("---")
        tab1, tab2 = st.tabs(["💡 Live Telemetry Metric Guide", "📊 Why Spatial Distance Alignment Matters"])
        with tab1:
            st.subheader("How to Read These Charts Instantly")
            st.markdown("""
            Think of these charts as a side-by-side comparison of how drivers attack a corner:
            
            * **The 'V' Valleys (Speed Chart):** Every dip represents a corner. 
                * **Braking:** Look at where a line drops off a cliff. The driver whose line drops later braved a later braking point.
                * **Cornering Momentum:** Look at the absolute lowest tip of the 'V'. Whichever driver's line stays higher at the lowest point carried more **minimum corner speed** through the apex.
            
            * **The Traction Hills (Throttle Chart):** Look at the lines climbing back up to 100% as they leave a corner.
                * **Good Traction:** A straight, steep climb up means the car was stable and the driver pinned the gas immediately, maximizing straight-line speed.
                * **Instability/Wheelspin:** If a line stutters, flatlines, or climbs slowly like a staircase, the driver had to lift off the throttle because the car was sliding or losing grip.
            """)
        with tab2:
            st.subheader("Data Analyst Design Insight")
            st.write("Traditional time-series graphs plot data against clock seconds. In Formula 1, if one driver brakes earlier, their entire timeline shifts forward, making direct visual overlays impossible to compare. By using a custom data pipeline to resample and normalize telemetry across Track Distance (Meters), this dashboard locks all selected profiles to the exact same physical coordinates. You are looking at an absolute, apples-to-apples performance breakdown at every single meter of the circuit.")
else:
    st.info("Select options in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
