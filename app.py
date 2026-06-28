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

DRIVER_MAP = {
    "Max Verstappen": "VER",
    "Lewis Hamilton": "HAM",
    "Charles Leclerc": "LEC",
    "Lando Norris": "NOR",
    "Oscar Piastri": "PIA",
    "George Russell": "RUS",
    "Carlos Sainz": "SAI",
    "Alex Albon": "ALB",
    "Pierre Gasly": "GAS",
    "Esteban Ocon": "OCO",
    "Sergio Perez": "PER",
    "Valtteri Bottas": "BOT",
    "Nico Hulkenberg": "HUL",
    "Lance Stroll": "STR",
    "Fernando Alonso": "ALO"
}

AVAILABLE_RACES = {
    "Australian Grand Prix (Melbourne)": {"year": 2023, "round": 3, "has_sprint": False},
    "Miami Grand Prix (Miami)": {"year": 2023, "round": 5, "has_sprint": True},
    "Monaco Grand Prix (Monte Carlo)": {"year": 2023, "round": 6, "has_sprint": False},
    "Spanish Grand Prix (Barcelona)": {"year": 2023, "round": 7, "has_sprint": False},
    "Canadian Grand Prix (Montreal)": {"year": 2023, "round": 8, "has_sprint": False},
    "Austrian Grand Prix (Spielberg)": {"year": 2023, "round": 9, "has_sprint": True},
    "British Grand Prix (Silverstone)": {"year": 2023, "round": 10, "has_sprint": False}
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
# CORE PIPELINE ENGINE
# -----------------------------------------------------------------------------
def process_race_telemetry(race_name, session_code, driver_a_code, driver_b_code):
    race_config = AVAILABLE_RACES[race_name]
    
    session = f1_api.get_session(race_config["year"], race_config["round"], session_code)
    session.load(telemetry=True, laps=True, weather=False)
    
    laps_a = session.laps.pick_driver(driver_a_code)
    laps_b = session.laps.pick_driver(driver_b_code)
    
    if laps_a.empty or laps_b.empty:
        raise ValueError("Selected driver did not log valid run segments during this session.")
        
    lap_a = laps_a.pick_fastest()
    lap_b = laps_b.pick_fastest()
    
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
# FAULT-TOLERANT MEMORY LAYER (f1_paddock_cache_vault)
# -----------------------------------------------------------------------------
if "f1_paddock_cache_vault" not in pd_stream.session_state:
    pd_stream.session_state["f1_paddock_cache_vault"] = {}

def get_cached_telemetry(race_name, session_code, driver_a_code, driver_b_code):
    cache_key = f"{race_name}_{session_code}_{driver_a_code}_{driver_b_code}"
    
    if cache_key not in pd_stream.session_state["f1_paddock_cache_vault"]:
        with pd_stream.spinner("Initializing clean telemetry workspace drive..."):
            try:
                processed_data = process_race_telemetry(race_name, session_code, driver_a_code, driver_b_code)
                pd_stream.session_state["f1_paddock_cache_vault"][cache_key] = processed_data
            except Exception as e:
                return None
                
    return pd_stream.session_state["f1_paddock_cache_vault"][cache_key]

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLLER PANEL
# -----------------------------------------------------------------------------
pd_stream.sidebar.header("Workspace Parameters")
selected_race = pd_stream.sidebar.selectbox("Select Grand Prix Circuit", list(AVAILABLE_RACES.keys()))

selected_session_label = pd_stream.sidebar.selectbox("Select Weekend Session", list(SESSION_MAP.keys()))
selected_session_code = SESSION_MAP[selected_session_label]

race_meta = AVAILABLE_RACES[selected_race]
if (selected_session_code in ["S", "SQ"]) and not race_meta["has_sprint"]:
    pd_stream.sidebar.error(f"⚠️ {selected_race} is not a Sprint Weekend. Resetting to Grand Prix Race.")
    selected_session_code = "R"

selected_driver_name_1 = pd_stream.sidebar.selectbox("Select Driver A", list(DRIVER_MAP.keys()), index=1)
selected_driver_name_2 = pd_stream.sidebar.selectbox("Select Driver B", list(DRIVER_MAP.keys()), index=0)

driver_code_1 = DRIVER_MAP[selected_driver_name_1]
driver_code_2 = DRIVER_MAP[selected_driver_name_2]

data = get_cached_telemetry(selected_race, selected_session_code, driver_code_1, driver_code_2)

# -----------------------------------------------------------------------------
# GRAPH RENDERING LAYER (PLOTS UP FIRST)
# -----------------------------------------------------------------------------
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
else:
    pd_stream.warning("Telemetry traces for this specific parameter combination are missing from the server logs. Please choose an alternate driver configuration or a competitive session (Qualifying/Race).")

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
