import streamlit as pd_stream
import fastf1 as f1_api
import numpy as np_math
import plotly.graph_objects as pd_plot
import os

# -----------------------------------------------------------------------------
# CONFIGURATION & WORKSPACE SETUP
# -----------------------------------------------------------------------------
pd_stream.set_page_config(page_title="F1 Telemetry UX Workspace", layout="wide")

CACHE_DIR = os.path.join(os.getcwd(), "fastf1_raw_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
f1_api.Cache.enable_cache(CACHE_DIR)

# Comprehensive Master Driver Database
MASTER_DRIVER_MAP = {
    "VER": "Max Verstappen", "HAM": "Lewis Hamilton", "LEC": "Charles Leclerc",
    "NOR": "Lando Norris", "PIA": "Oscar Piastri", "RUS": "George Russell",
    "SAI": "Carlos Sainz", "ALB": "Alex Albon", "GAS": "Pierre Gasly",
    "OCO": "Esteban Ocon", "PER": "Sergio Perez", "BOT": "Valtteri Bottas",
    "HUL": "Nico Hulkenberg", "STR": "Lance Stroll", "ALO": "Fernando Alonso",
    "MAG": "Kevin Magnussen", "TSU": "Yuki Tsunoda", "RIC": "Daniel Ricciardo",
    "SAR": "Logan Sargeant", "ZHO": "Zhou Guanyu", "DEV": "Nyck de Vries",
    "LAW": "Liam Lawson", "BEA": "Oliver Bearman", "COL": "Franco Colapinto"
}

AVAILABLE_RACES = {
    "01. Bahrain Grand Prix (Sakhir)": {"year": 2023, "round": 1, "has_sprint": False},
    "02. Saudi Arabian Grand Prix (Jeddah)": {"year": 2023, "round": 2, "has_sprint": False},
    "03. Australian Grand Prix (Melbourne)": {"year": 2023, "round": 3, "has_sprint": False},
    "04. Azerbaijan Grand Prix (Baku)": {"year": 2023, "round": 4, "has_sprint": True},
    "05. Miami Grand Prix (Miami)": {"year": 2023, "round": 5, "has_sprint": True},
    "06. Monaco Grand Prix (Monte Carlo)": {"year": 2023, "round": 6, "has_sprint": False},
    "07. Spanish Grand Prix (Barcelona)": {"year": 2023, "round": 7, "has_sprint": False},
    "08. Canadian Grand Prix (Montreal)": {"year": 2023, "round": 8, "has_sprint": False},
    "09. Austrian Grand Prix (Spielberg)": {"year": 2023, "round": 9, "has_sprint": True},
    "10. British Grand Prix (Silverstone)": {"year": 2023, "round": 10, "has_sprint": False},
    "11. Hungarian Grand Prix (Budapest)": {"year": 2023, "round": 11, "has_sprint": False},
    "12. Belgian Grand Prix (Spa-Francorchamps)": {"year": 2023, "round": 12, "has_sprint": True},
    "13. Dutch Grand Prix (Zandvoort)": {"year": 2023, "round": 13, "has_sprint": False},
    "14. Italian Grand Prix (Monza)": {"year": 2023, "round": 14, "has_sprint": False},
    "15. Singapore Grand Prix (Marina Bay)": {"year": 2023, "round": 15, "has_sprint": False},
    "16. Japanese Grand Prix (Suzuka)": {"year": 2023, "round": 16, "has_sprint": False},
    "17. Qatar Grand Prix (Lusail)": {"year": 2023, "round": 17, "has_sprint": True},
    "18. United States Grand Prix (Austin)": {"year": 2023, "round": 18, "has_sprint": True},
    "19. Mexico City Grand Prix (Mexico City)": {"year": 2023, "round": 19, "has_sprint": False},
    "20. São Paulo Grand Prix (Interlagos)": {"year": 2023, "round": 20, "has_sprint": True},
    "21. Las Vegas Grand Prix (Las Vegas)": {"year": 2023, "round": 21, "has_sprint": False},
    "22. Abu Dhabi Grand Prix (Yas Marina)": {"year": 2023, "round": 22, "has_sprint": False}
}

SESSION_MAP = {
    "Grand Prix Race": "R",
    "Qualifying Session": "Q",
    "Sprint Race": "S",
    "Sprint Qualifying": "SQ",
    "Free Practice 1": "FP1",
    "Free Practice 2": "FP2",
    "Free Practice 3": "FP3"
}

# -----------------------------------------------------------------------------
# FAULT-TOLERANT SESSION LOADER & DYNAMIC FILTERING
# -----------------------------------------------------------------------------
@pd_stream.cache_resource
def load_base_session(race_name, session_code):
    """Loads the core session structure to discover active participants dynamically."""
    race_config = AVAILABLE_RACES[race_name]
    session = f1_api.get_session(race_config["year"], race_config["round"], session_code)
    session.load(telemetry=False, laps=True, weather=False)
    return session

def get_active_drivers(session):
    """Extracts and maps only drivers who actually logged valid run data."""
    active_codes = session.laps['Driver'].unique()
    active_driver_map = {}
    for code in active_codes:
        if code in MASTER_DRIVER_MAP:
            active_driver_map[MASTER_DRIVER_MAP[code]] = code
        else:
            active_driver_map[f"Guest Driver ({code})"] = code
    return dict(sorted(active_driver_map.items()))

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLLER PANEL
# -----------------------------------------------------------------------------
pd_stream.sidebar.header("Workspace Parameters")
selected_race = pd_stream.sidebar.selectbox("Select Grand Prix Circuit", list(AVAILABLE_RACES.keys()))

selected_session_label = pd_stream.sidebar.selectbox("Select Weekend Session", list(SESSION_MAP.keys()))
selected_session_code = SESSION_MAP[selected_session_label]

# Enforce scheduling validation before execution
race_meta = AVAILABLE_RACES[selected_race]
if (selected_session_code in ["S", "SQ"]) and not race_meta["has_sprint"]:
    pd_stream.sidebar.error(f"⚠️ {selected_race} did not feature a Sprint session. Resetting to Race.")
    selected_session_code = "R"

# Load the base session components to pull verified drivers
try:
    active_session = load_base_session(selected_race, selected_session_code)
    filtered_drivers = get_active_drivers(active_session)
except Exception:
    pd_stream.sidebar.warning("API connection limit hit. Using core database fallback profiles.")
    filtered_drivers = {v: k for k, v in MASTER_DRIVER_MAP.items()}

# Dynamically generate selectors based purely on participating drivers
driver_list = list(filtered_drivers.keys())
def_idx_a = min(1, len(driver_list) - 1) if len(driver_list) > 1 else 0

selected_driver_name_1 = pd_stream.sidebar.selectbox("Select Driver A", driver_list, index=def_idx_a)
selected_driver_name_2 = pd_stream.sidebar.selectbox("Select Driver B", driver_list, index=0)

driver_code_1 = filtered_drivers[selected_driver_name_1]
driver_code_2 = filtered_drivers[selected_driver_name_2]

# -----------------------------------------------------------------------------
# CORE PIPELINE ENGINE (Processing telemetry)
# -----------------------------------------------------------------------------
def process_race_telemetry(session, driver_a_code, driver_b_code):
    lap_a = session.laps.pick_driver(driver_a_code).pick_fastest()
    lap_b = session.laps.pick_driver(driver_b_code).pick_fastest()
    
    tel_a = lap_a.get_car_data().add_distance()
    tel_b = lap_b.get_car_data().add_distance()
    
    max_distance = max(tel_a['Distance'].max(), tel_b['Distance'].max())
    uniform_grid = np_math.arange(0, max_distance, 10)
    
    speed_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Speed'])
    throttle_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Throttle'])
    time_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Time'].dt.total_seconds())
    
    speed_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Speed'])
    throttle_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Throttle'])
    time_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Time'].dt.total_seconds())
    
    time_delta = time_a - time_b
    
    return {
        "grid": uniform_grid,
        "speed_a": speed_a, "throttle_a": throttle_a,
        "speed_b": speed_b, "throttle_b": throttle_b,
        "time_delta": time_delta
    }

# -----------------------------------------------------------------------------
# EXECUTION & PLOT LAYER (PLOTS FIRST)
# -----------------------------------------------------------------------------
data = None
if driver_code_1 == driver_code_2:
    pd_stream.warning("Please select two different drivers to perform a head-to-head comparison.")
else:
    with pd_stream.spinner("Syncing data arrays..."):
        try:
            # Re-verify and trigger the high-frequency telemetry stream pull safely
            active_session.load(telemetry=True, laps=True, weather=False)
            data = process_race_telemetry(active_session, driver_code_1, driver_code_2)
        except Exception as e:
            pd_stream.error("High-frequency data streams are currently restricted or incomplete for this combination. Try a different session.")

if data is not None:
    fig_inputs = pd_plot.Figure()
    
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_a"], name=f"{selected_driver_name_1} Speed", line=dict(color="#00D2BE", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_a"], name=f"{selected_driver_name_1} Throttle %", line=dict(color="#00D2BE", dash="dash", width=1.5), yaxis="y2"))
    
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_b"], name=f"{selected_driver_name_2} Speed", line=dict(color="#0600EF", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_b"], name=f"{selected_driver_name_2} Throttle %", line=dict(color="#0600EF", dash="dash", width=1.5), yaxis="y2"))
    
    fig_inputs.update_layout(
        xaxis=dict(title="Distance (Meters)"),
        yaxis=dict(title="Speed (km/h)"),
        yaxis2=dict(title="Throttle %", overlaying="y", side="right", range=[0, 105]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=30, b=30),
        height=400
    )
    
    fig_outcome = pd_plot.Figure()
    fig_outcome.add_trace(pd_plot.Scatter(x=data["grid"], y=data["time_delta"], name="Pacing Gap Delta", line=dict(color="#FFFFFF", width=2), fill="tozeroy"))
    
    fig_outcome.update_layout(
        xaxis=dict(title="Distance (Meters)"),
        yaxis=dict(title="Delta Time (Seconds)"),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=20, b=30),
        height=250
    )
    
    pd_stream.plotly_chart(fig_inputs, use_container_width=True)
    pd_stream.plotly_chart(fig_outcome, use_container_width=True)

# -----------------------------------------------------------------------------
# CONCISE & ACCESSIBLE USER GUIDE (MOVED TO BOTTOM)
# -----------------------------------------------------------------------------
pd_stream.markdown("---")
with pd_stream.expander("📖 Quick Dashboard User Guide", expanded=False):
    pd_stream.markdown("""
    This panel matches raw telemetry points from both drivers onto an exact **Distance Grid (Meters)** so you can see who won or lost time across the lap.

    *   **Chart 1 (Speed & Throttle):** 
        *   **Solid Lines (Speed):** Deep drops show braking zones. Higher valley floors mean a driver carried more corner exit speed.
        *   **Dashed Lines (Throttle):** Shows how fast a driver hammered down on the gas pedal. Any flat plateaus or sudden drops indicate tyre wheelspin or stability corrections.
    *   **Chart 2 (Time Delta Gap):** 
        *   Shows the cumulative running time gap across the entire track layout.
        *   When the graph **slopes downward**, **Driver A is gaining time**. 
        *   When the graph **slopes upward**, **Driver B is gaining time**.
    """)
