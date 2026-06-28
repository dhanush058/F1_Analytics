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
    "SAR": "Logan Sargeant", "ZHO": "Zhou Guanyu", "BEA": "Oliver Bearman",
    "COL": "Franco Colapinto", "ANT": "Kimi Antonelli", 
    "LAW": "Liam Lawson", "HAD": "Isack Hadjar", "BOR": "Gabriel Bortoleto"
}

# Simplified clear strings for cross-year database lookup integration
AVAILABLE_RACES = [
    "Australia", "Bahrain", "Saudi Arabia", "Japan", "China", "Miami", 
    "Imola", "Monaco", "Canada", "Spain", "Austria", "Great Britain", 
    "Hungary", "Belgium", "Netherlands", "Monza", "Azerbaijan", 
    "Singapore", "Austin", "Mexico", "Brazil", "Las Vegas", "Qatar", "Abu Dhabi"
]

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
def load_base_session(selected_year, gp_name, session_code):
    """Loads the core session structure using native fuzzy string matching."""
    session = f1_api.get_session(selected_year, gp_name, session_code)
    session.load(telemetry=False, laps=True, weather=False)
    return session

def get_active_drivers(session):
    """Extracts and maps only drivers who actually logged valid run data."""
    if session.laps.empty:
        return {}
    active_codes = session.laps['Driver'].unique()
    active_driver_map = {}
    for code in active_codes:
        if code in MASTER_DRIVER_MAP:
            active_driver_map[MASTER_DRIVER_MAP[code]] = code
        else:
            active_driver_map[f"Driver ({code})"] = code
    return dict(sorted(active_driver_map.items()))

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLLER PANEL
# -----------------------------------------------------------------------------
pd_stream.sidebar.header("Workspace Parameters")

# Year Selector Component
selected_year = pd_stream.sidebar.selectbox("Select Season Year", [2024, 2025, 2026], index=0)

selected_race_name = pd_stream.sidebar.selectbox("Select Grand Prix Circuit", AVAILABLE_RACES)

selected_session_label = pd_stream.sidebar.selectbox("Select Weekend Session", list(SESSION_MAP.keys()))
selected_session_code = SESSION_MAP[selected_session_label]

# Load the base session components dynamically using native string queries
session_load_success = True
try:
    active_session = load_base_session(selected_year, selected_race_name, selected_session_code)
    filtered_drivers = get_active_drivers(active_session)
    if not filtered_drivers:
        session_load_success = False
except Exception:
    session_load_success = False
    filtered_drivers = {}

# Dynamically generate selectors based purely on participating drivers
if session_load_success and filtered_drivers:
    driver_list = list(filtered_drivers.keys())
    def_idx_a = min(1, len(driver_list) - 1) if len(driver_list) > 1 else 0

    selected_driver_name_1 = pd_stream.sidebar.selectbox("Select Driver A", driver_list, index=def_idx_a)
    selected_driver_name_2 = pd_stream.sidebar.selectbox("Select Driver B", driver_list, index=0)

    driver_code_1 = filtered_drivers[selected_driver_name_1]
    driver_code_2 = filtered_drivers[selected_driver_name_2]
else:
    driver_code_1 = driver_code_2 = None

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
if not session_load_success:
    pd_stream.warning(f"🏁 The telemetry data for {selected_year} {selected_race_name} ({selected_session_label}) is either an upcoming event or has not been finalized on the FIA data logs yet. Please switch to a completed session.")
elif driver_code_1 == driver_code_2:
    pd_stream.warning("Please select two different drivers to perform a head-to-head comparison.")
else:
    with pd_stream.spinner("Syncing data arrays..."):
        try:
            active_session.load(telemetry=True, laps=True, weather=False)
            data = process_race_telemetry(active_session, driver_code_1, driver_code_2)
        except Exception:
            pd_stream.error("High-frequency traces are currently locked out or missing from server logs for this specific session choice.")

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
# PREMIUM & COMPREHENSIVE PERFORMANCE RADAR GUIDE
# -----------------------------------------------------------------------------
pd_stream.markdown("---")
with pd_stream.expander("📖 Telemetry Performance Analytics & Interpretation Guide", expanded=False):
    pd_stream.markdown("""
    This advanced dashboard synchronizes raw, high-frequency vehicle telemetry channels onto a single **Normalized Spatial Grid (X-Axis in Meters)**. By eliminating time-mismatch artifacts, you can directly compare driver micro-inputs against structural lap time outcomes.

    ### 📈 Chart 1: Driver Ingestion Inputs (Speed & Throttle Overlay)
    This chart visualizes exactly what the drivers are doing with their physical inputs at every meter of the track.
    
    *   **Solid Traces (Car Speed in km/h):** Look for the steep downward valleys—these are major deceleration zones. 
        *   *The Deep Analysis:* A narrower valley indicates superior, stable threshold braking. A higher valley floor means the driver carried more "roll-speed" through the geometric center (apex) of the turn.
    *   **Dashed Traces (Throttle Pedal Engagement %):** Tracks how cleanly a driver applies power when exiting a corner.
        *   *The Deep Analysis:* Look for a straight, immediate vertical line climbing back to 100%. If you spot staircase-like plateaus, jagged dips, or hesitations, it reveals traction instability, snap-oversteer, or active driver lifting to stabilize the chassis.

    ### 📉 Chart 2: Structural Performance Outcomes (Pacing Time Delta)
    This chart calculates the running, cumulative time difference between the two laps across the entire lap profile.
    
    *   **The 0.00s Baseline:** The horizontal zero-line is the reference benchmark. 
    *   **Downward Slopes (Negative Trend):** The line dips down when **Driver A is pulling away** and actively pocketing lap time.
    *   **Upward Slopes (Positive Trend):** The line climbs when **Driver B is gaining a performance advantage** and outperforming Driver A.
    *   *The Pro Trick:* Look directly vertically at both charts at the exact same meter mark. You can deduce whether Driver A won a micro-sector because they brake later on corner entry (Speed trace drops later) or because Driver B had wheelspin on exit (Throttle trace stutters).
    
    ### 🛠️ Behind the Scenes Architectural Highlights
    *   **1D Linear Interpolation Engine:** Telemetry sensors fire at different frequencies (e.g., speed vs. pedal positions). This app resamples and normalizes mismatched data arrays onto a strict 10-meter spatial interval baseline using `numpy.interp` to ensure a mathematically true comparison.
    *   **Pure ECU Extraction:** Uses dedicated car computer channels (`get_car_data()`) to bypass unstable satellite telemetry loops, ensuring complete data consistency across both competitive sessions and free practice environments.
    """)
