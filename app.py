import streamlit as pd_stream
import fastf1 as f1_api
import numpy as np_math
import plotly.graph_objects as pd_plot
import os

# -----------------------------------------------------------------------------
# CONSTANTS & WORKSPACE SETUP
# -----------------------------------------------------------------------------
pd_stream.set_page_config(page_title="F1 Telemetry UX Workspace", layout="wide")

CACHE_DIR = os.path.join(os.getcwd(), "fastf1_raw_cache")
os.makedirs(CACHE_DIR, exist_ok=True)
f1_api.Cache.enable_cache(CACHE_DIR)

# 2026 F1 Full Driver Mapping 
DRIVER_MAP = {
    "VER": "Max Verstappen", "HAM": "Lewis Hamilton", "LEC": "Charles Leclerc",
    "NOR": "Lando Norris", "PIA": "Oscar Piastri", "RUS": "George Russell",
    "ANT": "Kimi Antonelli", "SAI": "Carlos Sainz", "ALB": "Alex Albon",
    "GAS": "Pierre Gasly", "OCO": "Esteban Ocon", "BEA": "Oliver Bearman",
    "LAW": "Liam Lawson", "PER": "Sergio Perez", "BOT": "Valtteri Bottas",
    "HUL": "Nico Hulkenberg", "STR": "Lance Stroll", "ALO": "Fernando Alonso",
    "COL": "Franco Colapinto", "HAD": "Isack Hadjar", "BOR": "Gabriel Bortoleto",
    "LIN": "Arvid Lindblad"
}

# Complete 24-Race 2026 Calendar 
AVAILABLE_RACES = {
    "01. Australian Grand Prix (Melbourne)": 1,
    "02. Chinese Grand Prix (Shanghai)": 2,
    "03. Japanese Grand Prix (Suzuka)": 3,
    "04. Bahrain Grand Prix (Sakhir) [Cancelled]": 4,
    "05. Saudi Arabian Grand Prix (Jeddah) [Cancelled]": 5,
    "06. Miami Grand Prix (Miami)": 6,
    "07. Canadian Grand Prix (Montreal)": 7,
    "08. Monaco Grand Prix (Monte Carlo)": 8,
    "09. Barcelona-Catalunya Grand Prix (Montmeló)": 9,
    "10. Austrian Grand Prix (Spielberg)": 10,
    "11. British Grand Prix (Silverstone)": 11,
    "12. Belgian Grand Prix (Spa-Francorchamps)": 12,
    "13. Hungarian Grand Prix (Budapest)": 13,
    "14. Dutch Grand Prix (Zandvoort)": 14,
    "15. Italian Grand Prix (Monza)": 15,
    "16. Spanish Grand Prix (Madrid)": 16,
    "17. Azerbaijan Grand Prix (Baku)": 17,
    "18. Singapore Grand Prix (Marina Bay)": 18,
    "19. United States Grand Prix (Austin)": 19,
    "20. Mexico City Grand Prix (Mexico City)": 20,
    "21. São Paulo Grand Prix (Interlagos)": 21,
    "22. Las Vegas Grand Prix (Las Vegas)": 22,
    "23. Qatar Grand Prix (Lusail)": 23,
    "24. Abu Dhabi Grand Prix (Yas Marina)": 24
}

# -----------------------------------------------------------------------------
# CORE PIPELINE ENGINE (Data Cleaning & 1D Interpolation)
# -----------------------------------------------------------------------------
def process_race_telemetry(race_name, driver_a, driver_b):
    round_num = AVAILABLE_RACES[race_name]
    
    session = f1_api.get_session(2026, round_num, 'R')
    session.load(telemetry=True, laps=True, weather=False)
    
    lap_a = session.laps.pick_driver(driver_a).pick_fastest()
    lap_b = session.laps.pick_driver(driver_b).pick_fastest()
    
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

def get_cached_telemetry(race_name, driver_a, driver_b):
    cache_key = f"{race_name}_{driver_a}_{driver_b}"
    
    if cache_key not in pd_stream.session_state["f1_paddock_cache_vault"]:
        with pd_stream.spinner("Initializing clean telemetry workspace drive... Please wait a moment."):
            try:
                processed_data = process_race_telemetry(race_name, driver_a, driver_b)
                pd_stream.session_state["f1_paddock_cache_vault"][cache_key] = processed_data
            except Exception as e:
                pd_stream.error("Data availability threshold reached for selected parameters.")
                return None
                
    return pd_stream.session_state["f1_paddock_cache_vault"][cache_key]

# -----------------------------------------------------------------------------
# USER INTERFACE & COMPOSITE LAYOUT
# -----------------------------------------------------------------------------
pd_stream.title("🏎️ Formula 1 Telemetry Analysis Workspace")

# Control Sidebar Panel
pd_stream.sidebar.header("Workspace Parameters")
selected_race = pd_stream.sidebar.selectbox("Select Grand Prix Circuit", list(AVAILABLE_RACES.keys()))

# Driver Selectboxes mapping directly to Full Names
driver_code_1 = pd_stream.sidebar.selectbox("Select Driver A", list(DRIVER_MAP.keys()), index=1) # Default HAM
driver_name_1 = DRIVER_MAP[driver_code_1]
pd_stream.sidebar.caption(f"Active Profile: **{driver_name_1}**")

driver_code_2 = pd_stream.sidebar.selectbox("Select Driver B", list(DRIVER_MAP.keys()), index=0) # Default VER
driver_name_2 = DRIVER_MAP[driver_code_2]
pd_stream.sidebar.caption(f"Active Profile: **{driver_name_2}**")

# Execution Engine
data = get_cached_telemetry(selected_race, driver_code_1, driver_code_2)

if data is not None:
    # Tier 1 Canvas: Driver Mechanical Inputs
    fig_inputs = pd_plot.Figure()
    
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_a"], name=f"{driver_name_1} Speed (km/h)", line=dict(color="#00D2BE", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_a"], name=f"{driver_name_1} Throttle %", line=dict(color="#00D2BE", dash="dash", width=1.5), yaxis="y2"))
    
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["speed_b"], name=f"{driver_name_2} Speed (km/h)", line=dict(color="#0600EF", width=2)))
    fig_inputs.add_trace(pd_plot.Scatter(x=data["grid"], y=data["throttle_b"], name=f"{driver_name_2} Throttle %", line=dict(color="#0600EF", dash="dash", width=1.5), yaxis="y2"))
    
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
    
    # Tier 2 Canvas: Downstream Structural Outcomes
    fig_outcome = pd_plot.Figure()
    fig_outcome.add_trace(pd_plot.Scatter(x=data["grid"], y=data["time_delta"], name="Pacing Gap Delta", line=dict(color="#FFFFFF", width=2.5), fill="tozeroy"))
    
    fig_outcome.update_layout(
        title=f"Tier 2 Canvas: Downstream Structural Outcomes (<0 Favors {driver_name_1} | >0 Favors {driver_name_2})",
        xaxis=dict(title="Track Baseline Distance (Meters)"),
        yaxis=dict(title="Time Differential Gap (Seconds)"),
        hovermode="x unified",
        margin=dict(l=50, r=50, t=50, b=50),
        height=250
    )
    
    pd_stream.plotly_chart(fig_inputs, use_container_width=True)
    pd_stream.plotly_chart(fig_outcome, use_container_width=True)
else:
    pd_stream.warning("Session telemetry data not found for this specific event parameter configuration.")
