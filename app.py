import streamlit as st
import fastf1
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

# Complete Master Driver Dictionary across 2024, 2025, and 2026 grids
MASTER_DRIVER_MAP = {
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
    # Rookies, Mid-Season Replacements, and New Grid Debuts (2024-2026)
    "Kimi Antonelli": "ANT",
    "Oliver Bearman": "BEA",
    "Franco Colapinto": "COL",
    "Gabriel Bortoleto": "BOR",
    "Liam Lawson": "LAW",
    "Isack Hadjar": "HAD",
    "Arvid Lindblad": "LIN",
    "Jack Doohan": "DOO"
}

# Inverse map to safely turn abbreviation codes -> Full Names
CODE_TO_NAME = {v: k for k, v in MASTER_DRIVER_MAP.items()}

# 3. Dynamic Driver Filter (Matches session availability against our Master Full Name list)
@st.cache_data(show_spinner=False)
def get_active_session_drivers(year, round_num, session_type):
    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=False, weather=False)
        active_codes = session.laps['Driver'].unique().tolist()
        
        # Build list of available full names based on who actually drove during this specific session
        display_names = []
        for code in active_codes:
            if code in CODE_TO_NAME:
                display_names.append(CODE_TO_NAME[code])
            else:
                display_names.append(code) # Fallback to raw code if an unmapped wild-card entry appears
        return sorted(display_names)
    except Exception:
        # Emergency complete full fallback if API list retrieval times out
        return sorted(list(MASTER_DRIVER_MAP.keys()))

# Get the clean list of Full Names available for this specific weekend
available_full_names = get_active_session_drivers(year, selected_round, session_type)

st.sidebar.markdown("---")
st.sidebar.header("Driver Selection")

d1_name = st.sidebar.selectbox("Driver 1", available_full_names, index=0)
d2_name = st.sidebar.selectbox("Driver 2", available_full_names, index=min(1, len(available_full_names)-1))

driver3_options = ["None"] + available_full_names
d3_name = st.sidebar.selectbox("Driver 3 (Optional)", driver3_options, index=0)

# Map selected full names back to raw codes for the FastF1 backend engine processing
driver1 = MASTER_DRIVER_MAP.get(d1_name, d1_name)
driver2 = MASTER_DRIVER_MAP.get(d2_name, d2_name)
driver3 = "None" if d3_name == "None" else MASTER_DRIVER_MAP.get(d3_name, d3_name)

# Clear Cache Option to fix corrupted file downloads instantly
st.sidebar.markdown("---")
st.sidebar.subheader("Data Maintenance")
force_refresh = st.sidebar.checkbox("Force Refresh Live Data", value=False)

# 4. Defensive Data Fetching Function
def get_single_driver_telemetry(session, driver_code):
    try:
        driver_laps = session.laps.pick_driver(driver_code)
        if driver_laps.empty:
            return None
        
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None or not hasattr(fastest_lap, 'get_telemetry'):
            return None
            
        telemetry = fastest_lap.get_telemetry().add_distance()
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
    
    t2 = get_single_driver_
