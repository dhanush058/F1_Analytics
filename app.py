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
# 🏎️ MULTI-SEASON CONFIGURATION (ACCURATE CALENDARS)
# =========================================================
st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")

st.markdown("""
    <style>
        .f1-banner {
            background: linear-gradient(90deg, #FF0000 0%, #1E1E24 100%);
            padding: 12px;
            border-radius: 4px;
            border-left: 6px solid #FF0000;
            margin-bottom: 20px;
        }
        .f1-title {
            color: #FFFFFF !important;
            font-family: 'Titillium Web', sans-serif;
            font-weight: 800;
            letter-spacing: 1px;
            margin: 0px !important;
            font-size: 26px;
        }
        .metric-card {
            background-color: #151922;
            border: 1px solid #222933;
            border-top: 3px solid #FF0000;
            padding: 10px;
            border-radius: 4px;
            min-height: 85px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="f1-banner"><h1 class="f1-title">🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER</h1></div>', unsafe_allow_html=True)

st.sidebar.markdown("### 🛠️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle(
    "🖥️ Enable Simulated Demo Mode", 
    value=False, 
    help="Toggle this on to view full dashboard capabilities instantly if the public F1 API is throttled or offline."
)

selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=0)

# Multi-Season Master Database Calendar Configurations
seasonal_schedule = {
    2026: {
        "races": {
            1: "Australian Grand Prix", 2: "Chinese Grand Prix", 3: "Japanese Grand Prix",
            4: "Bahrain Grand Prix", 5: "Saudi Arabian Grand Prix", 6: "Miami Grand Prix",
            7: "Canadian Grand Prix", 8: "Monaco Grand Prix", 9: "Barcelona-Catalunya Grand Prix",
            10: "Austrian Grand Prix", 11: "British Grand Prix", 12: "Belgian Grand Prix",
            13: "Hungarian Grand Prix", 14: "Dutch Grand Prix", 15: "Italian Grand Prix",
            16: "Spanish Grand Prix (Madrid)", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Melbourne", 2: "Shanghai", 3: "Suzuka", 4: "Sakhir", 5: "Jeddah", 6: "Miami",
            7: "Montreal", 8: "Monaco", 9: "Barcelona", 10: "Spielberg", 11: "Silverstone", 12: "Spa",
            13: "Budapest", 14: "Zandvoort", 15: "Monza", 16: "Madrid", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        },
        "cancelled_rounds": []
    },
    2025: {
        "races": {
            1: "Australian Grand Prix", 2: "Chinese Grand Prix", 3: "Japanese Grand Prix",
            4: "Bahrain Grand Prix", 5: "Saudi Arabian Grand Prix", 6: "Miami Grand Prix",
            7: "Emilia Romagna Grand Prix", 8: "Monaco Grand Prix", 9: "Spanish Grand Prix",
            10: "Canadian Grand Prix", 11: "Austrian Grand Prix", 12: "British Grand Prix",
            13: "Belgian Grand Prix", 14: "Hungarian Grand Prix", 15: "Dutch Grand Prix",
            16: "Italian Grand Prix", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Melbourne", 2: "Shanghai", 3: "Suzuka", 4: "Sakhir", 5: "Jeddah", 6: "Miami",
            7: "Imola", 8: "Monaco", 9: "Barcelona", 10: "Montreal", 11: "Spielberg", 12: "Silverstone",
            13: "Spa", 14: "Budapest", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        },
        "cancelled_rounds": []
    },
    2024: {
        "races": {
            1: "Bahrain Grand Prix", 2: "Saudi Arabian Grand Prix", 3: "Australian Grand Prix",
            4: "Japanese Grand Prix", 5: "Chinese Grand Prix", 6: "Miami Grand Prix",
            7: "Emilia Romagna Grand Prix", 8: "Monaco Grand Prix", 9: "Canadian Grand Prix",
            10: "Spanish Grand Prix", 11: "Austrian Grand Prix", 12: "British Grand Prix",
            13: "Hungarian Grand Prix", 14: "Belgian Grand Prix", 15: "Dutch Grand Prix",
            16: "Italian Grand Prix", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Sakhir", 2: "Jeddah", 3: "Melbourne", 4: "Suzuka", 5: "Shanghai", 6: "Miami",
            7: "Imola", 8: "Monaco", 9: "Montreal", 10: "Barcelona", 11: "Spielberg", 12: "Silverstone",
            13: "Budapest", 14: "Spa", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        },
        "cancelled_rounds": []
    }
}

active_config = seasonal_schedule[selected_year]
race_options = active_config["races"]
location_map = active_config["locations"]

selected_round = st.sidebar.selectbox(
    "Select Grand Prix Track", 
    list(race_options.keys()), 
    format_func=lambda x: f"Round {x}: {race_options[x]}"
)

session_options = {
    "Race": "Race", "Qualifying": "Qualifying",
    "FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3",
    "Sprint": "Sprint", "Sprint Qualifying": "Sprint Qualifying"
}
selected_session_label = st.sidebar.selectbox("Select Session Type", list(session_options.keys()), index=0)
selected_session_api_name = session_options[selected_session_label]

target_location = location_map[selected_round]
is_cancelled_round = selected_round in active_config["cancelled_rounds"]

# =========================================================
# 🌐 OPENF1 METADATA RESOLVER
# =========================================================
session_key = None
session_start_time = None
driver_map = {}
is_simulated = True
event_name = race_options[selected_round]

if not is_cancelled_round and not demo_mode:
    session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}&session_name={selected_session_api_name}"
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
            session_start_time = matched_session.get('date_start')
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

if not is_simulated and driver_map and not demo_mode:
    drivers = sorted(list(driver_map.keys()))
else:
    drivers = ["VER", "HAM", "NOR", "LEC", "RUS", "PIA"]

driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers, index=0)
driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers, index=1 if len(drivers) > 1 else 0)

# =========================================================
# 📊 DATA-VALIDATED TELEMETRY EXTRACTION ENGINE
# =========================================================
@st.cache_data(ttl=1800, show_spinner="Querying telemetry pipeline matrix...")
def fetch_telemetry_dataframe(s_key, s_start, d_map, d_a, d_b, fallback_active):
    if fallback_active or not s_key or not d_map or d_a not in d_map or d_b not in d_map:
        return None, None, True

    try:
        num_a = d_map[d_a]
        num_b = d_map[d_b]
        date_filter = f"&date>={s_start}" if s_start else ""
        
        url_a = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_a)}{date_filter}"
        res_a = requests.get(url_a, timeout=5).json()
        
        url_b = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_b)}{date_filter}"
        res_b = requests.get(url_b, timeout=5).json()
        
        if not res_a or not res_b or len(res_a) < 20 or len(res_b) < 20:
            return
