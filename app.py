import streamlit as pd_stream
import fastf1 as f1_api
import numpy as np_math
import plotly.graph_objects as pd_plot
import os

# -----------------------------------------------------------------------------
# CONSTANTS & WORKSPACE SETUP
# -----------------------------------------------------------------------------
pd_stream.set_page_config(page_title="F1 Telemetry UX Workspace", layout="wide")

# Set a local, writable directory for FastF1's raw data cache
CACHE_DIR = os.path.join(os.getcwd(), "fastf1_raw_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
f1_api.Cache.enable_cache(CACHE_DIR)

# Define the 3 completed 2026 races currently targetable in our scope
AVAILABLE_RACES = {
    "Monaco Grand Prix": 8,
    "Canadian Grand Prix": 9,
    "Spanish Grand Prix": 10
}

# -----------------------------------------------------------------------------
# CORE PIPELINE ENGINE (Data Cleaning & 1D Interpolation)
# -----------------------------------------------------------------------------
def process_race_telemetry(race_name, driver_a, driver_b):
    """
    Ingests live telemetry streams, filters out noise, and applies 1D linear
    interpolation to force asynchronous streams onto a uniform 10-meter grid baseline.
    """
    round_num = AVAILABLE_RACES[race_name]
    
    # Ingest session
    session = f1_api.get_session(2026, round_num, 'R')
    session.load(telemetry=True, laps=True, weather=False)
    
    # Data Cleaning: Filter out non-race event noise and isolate fastest valid laps
    lap_a = session.laps.pick_driver(driver_a).pick_fastest()
    lap_b = session.laps.pick_driver(driver_b).pick_fastest()
    
    # Stream Ingestion
    tel_a = lap_a.get_telemetry()
    tel_b = lap_b.get_telemetry()
    
    # Mathematical Alignment: Define a uniform 10-meter spatial track grid baseline
    max_distance = max(tel_a['Distance'].max(), tel_b['Distance'].max())
    uniform_grid = np_math.arange(0, max_distance, 10)
    
    # 1D Linear Interpolation Engine
    speed_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Speed'])
    throttle_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Throttle'])
    time_a = np_math.interp(uniform_grid, tel_a['Distance'], tel_a['Time'].dt.total_seconds())
    
    speed_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Speed'])
    throttle_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Throttle'])
    time_b = np_math.interp(uniform_grid, tel_b['Distance'], tel_b['Time'].dt.total_seconds())
    
    # Calculate Systemic Outcome: Pacing Delta Margin
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

def get_cached_telemetry(race_name, driver_a, driver_b):
    """
    Retrieves telemetry from the local cache vault. If a server sleep state wiped 
    the workspace, it triggers a safe self-healing initialization loop.
    """
    cache_key = f"{race_name}_{driver_a}_{driver_b}"
    
    # 🛡️ SELF-HEALING LOOP: If cache is missing due to inactivity, reload automatically
    if cache_key not in pd_stream.session_state["f1_paddock_cache_vault"]:
        with pd_stream.spinner("Initializing clean telemetry workspace drive... Please wait a moment."):
            try:
                processed_data = process_race_telemetry(race_name, driver_a, driver_b)
                pd_stream.session_state["f1_paddock_cache_vault"][cache_key] = processed_data
            except Exception as e:
                pd_stream.error("Operational Boundary Defect bypassed. Forcing hard telemetry pipeline reset...")
                # Immediate fallback parameters to prevent dashboard crash
                return None
                
    return pd_stream.session_state["f1_paddock_cache_vault"][cache_key]

# -----------------------------------------------------------------------------
# USER INTERFACE & COMPOSITE LAYOUT (Enterprise UX Framework)
# -----------------------------------------------------------------------------
pd_stream.title("🏎️ Formula 1 Telemetry Analysis Workspace")
pd_stream.markdown("### High-Density Enterprise Performance UI")

# Control Sidebar Panel
pd_stream.sidebar.header("Workspace Parameters")
selected_race = pd_stream.sidebar.selectbox("Select 2026 Grand Prix", list(AVAILABLE_RACES.keys()))

col_input1, col_input2 = pd_stream.sidebar.columns(2)
with col_input1:
    driver_1 = pd_stream.text_input("Driver A", "HAM").upper()
with col_input2:
    driver_2 = pd_stream.text_input("Driver B", "VER").upper()

# Core Data Execution Loop
data = get_cached_telemetry(selected_race, driver_1, driver_2)

if data is not None:
    # 🎨 COMPOSITE VISUAL HIERARCHY: Bi-Tier Canvas Architecture
    # Tier 1 Canvas: Driver Inputs (Speed and Throttle Overlay)
    fig_inputs = pd_plot.Figure()
    
    # Driver A Inputs
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_a"], name=f"{driver_1} Speed (km/h)", line=dict(color="#00D2BE", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_a"], name=f"{driver_1} Throttle %", line=dict(color="#00D2BE", dash="dash", width=1.5), yaxis="y2"))
    
    # Driver B Inputs
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_b"], name=f"{driver_2} Speed (km/h)", line=dict(color="#0600EF", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_b"], name=f"{driver_2} Throttle %", line=dict(color="#0600EF", dash="dash", width=1.5), yaxis="y2"))
    
    fig_inputs.update_layout(
        title="Tier 1 Canvas: Driver Mechanical Ingestion Inputs",
        xaxis=dict(title="Track Baseline Distance (Meters)"),
        yaxis=dict(title="Velocity Speed (km/h)"),
        yaxis2=dict(title="Throttle Engagement %", overlaying="y", side="right", range=[0, 105]),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50),
        height=400
    )
    
    # Tier 2 Canvas: Downstream Systemic Outcomes (Pacing Delta Time Margin)
    fig_outcome = pd_plot.Figure()
    fig_outcome.add_trace(pd_plot.Scatter(x=data["grid"], y=data["time_delta"], name="Pacing Gap Delta", line=dict(color="#FFFFFF", width=2.5), fill="tozeroy"))
    
    fig_outcome.update_layout(
        title=f"Tier 2 Canvas: Downstream Structural Outcomes (<0 Favors {driver_1} | >0 Favors {driver_2})",
        xaxis=dict(title="Track Baseline Distance (Meters)"),
        yaxis=dict(title="Time Differential Gap (Seconds)"),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50),
        height=250
    )
    
    # Synchronized Dashboard Layout Deployment
    pd_stream.plotly_chart(fig_inputs, use_container_width=True)
    pd_stream.plotly_chart(fig_outcome, use_container_width=True)

else:
    pd_stream.warning("Workspace Engine encountered data acquisition boundaries. Adjust Driver abbreviations and re-run.")
