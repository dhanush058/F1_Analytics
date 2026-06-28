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

# Full Driver Mapping: Keys are what the user sees, values are what the API needs
DRIVER_MAP = {
    "Max Verstappen": "VER",
    "Lewis Hamilton": "HAM",
    "Charles Leclerc": "LEC",
    "Lando Norris": "NOR",
    "Oscar Piastri": "PIA",
    "George Russell": "RUS",
    "Kimi Antonelli": "ANT",
    "Carlos Sainz": "SAI",
    "Alex Albon": "ALB",
    "Pierre Gasly": "GAS",
    "Esteban Ocon": "OCO",
    "Oliver Bearman": "BEA",
    "Liam Lawson": "LAW",
    "Sergio Perez": "PER",
    "Valtteri Bottas": "BOT",
    "Nico Hulkenberg": "HUL",
    "Lance Stroll": "STR",
    "Fernando Alonso": "ALO",
    "Franco Colapinto": "COL",
    "Isack Hadjar": "HAD",
    "Gabriel Bortoleto": "BOR",
    "Arvid Lindblad": "LIN"
}

# Complete 2026 Season Calendar Up To Current Date
AVAILABLE_RACES = {
    "Australian Grand Prix (Melbourne)": 1,
    "Chinese Grand Prix (Shanghai)": 2,
    "Japanese Grand Prix (Suzuka)": 3,
    "Miami Grand Prix (Miami)": 6,
    "Canadian Grand Prix (Montreal)": 7,
    "Monaco Grand Prix (Monte Carlo)": 8,
    "Barcelona-Catalunya Grand Prix (Montmeló)": 9,
    "Austrian Grand Prix (Spielberg)": 10
}

# -----------------------------------------------------------------------------
# WORKSPACE APPLICATION USER GUIDE
# -----------------------------------------------------------------------------
with pd_stream.expander("📖 Workspace User Guide & System Overview", expanded=False):
    pd_stream.markdown("""
    #### Welcome to the F1 Telemetry Analysis Workspace
    This interactive enterprise interface translates raw, high-frequency vehicle telemetry streams into a synchronized visual head-to-head format.
    
    * **How to Use:** 
      1. Open the sidebar controller panel on the left.
      2. Choose an event from the **Grand Prix Circuit** dropdown list.
      3. Select **Driver A** and **Driver B** using their full names. 
      
    * **Core Pipeline Transformations:**
      * **Automated Noise Removal:** Filters out pit lanes, practice sessions, and slow warm-up laps to focus strictly on pure racing limits.
      * **1D Linear Interpolation:** Normalizes mismatched sensor arrays down to a standard 10-meter spatial tracking baseline, aligning both drivers onto the exact same grid timeline.
      * **0.1-Second Memory Cache:** Stores calculated metrics dynamically to guarantee lag-free interactions.
    """)

# -----------------------------------------------------------------------------
# CORE PIPELINE ENGINE (Data Ingestion & 1D Interpolation)
# -----------------------------------------------------------------------------
def process_race_telemetry(race_name, driver_a_code, driver_b_code):
    round_num = AVAILABLE_RACES[race_name]
    
    session = f1_api.get_session(2026, round_num, 'R')
    session.load(telemetry=True, laps=True, weather=False)
    
    lap_a = session.laps.pick_driver(driver_a_code).pick_fastest()
    lap_b = session.laps.pick_driver(driver_b_code).pick_fastest()
    
    tel_a = lap_a.get_telemetry()
    tel_b = lap_b.get_telemetry()
    
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

def get_cached_telemetry(race_name, driver_a_code, driver_b_code):
    cache_key = f"{race_name}_{driver_a_code}_{driver_b_code}"
    
    if cache_key not in pd_stream.session_state["f1_paddock_cache_vault"]:
        with pd_stream.spinner("Initializing clean telemetry workspace drive..."):
            try:
                processed_data = process_race_telemetry(race_name, driver_a_code, driver_b_code)
                pd_stream.session_state["f1_paddock_cache_vault"][cache_key] = processed_data
            except Exception as e:
                pd_stream.error("Data tracking boundaries reached for these parameters.")
                return None
                
    return pd_stream.session_state["f1_paddock_cache_vault"][cache_key]

# -----------------------------------------------------------------------------
# SIDEBAR CONTROLLER PANEL
# -----------------------------------------------------------------------------
pd_stream.sidebar.header("Workspace Parameters")
selected_race = pd_stream.sidebar.selectbox("Select Grand Prix Circuit", list(AVAILABLE_RACES.keys()))

# Stacking Driver 1 directly over Driver 2 using full names
selected_driver_name_1 = pd_stream.sidebar.selectbox("Select Driver A", list(DRIVER_MAP.keys()), index=1)
selected_driver_name_2 = pd_stream.sidebar.selectbox("Select Driver B", list(DRIVER_MAP.keys()), index=0)

driver_code_1 = DRIVER_MAP[selected_driver_name_1]
driver_code_2 = DRIVER_MAP[selected_driver_name_2]

# Execution Loop
data = get_cached_telemetry(selected_race, driver_code_1, driver_code_2)

# -----------------------------------------------------------------------------
# CLEAN GRAPH ARCHITECTURE
# -----------------------------------------------------------------------------
if data is not None:
    # Speed and Throttle Overlays
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
    
    # Delta Comparison Chart
    fig_outcome = pd_plot.Figure()
    fig_outcome.add_trace(pd_plot.Scatter(x=data["grid"], y=data["time_delta"], name="Pacing Gap Delta", line=dict(color="#FFFFFF", width=2), fill="tozeroy"))
    
    fig_outcome.update_layout(
        xaxis=dict(title="Distance (Meters)"),
        yaxis=dict(title="Delta Time (Seconds)"),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=20, b=30),
        height=250
    )
    
    # Clean Rendering Display
    pd_stream.plotly_chart(fig_inputs, use_container_width=True)
    pd_stream.plotly_chart(fig_outcome, use_container_width=True)
else:
    pd_stream.warning("Telemetry arrays unavailable for this choice. Check selected drivers.")
