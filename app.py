import streamlit as st
import fastf1
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# 1. Initialize High-Density Workspace Environment
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable automatic file system caching to accelerate execution
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass 

# 2. Sidebar Layout - Stage 1 Controls
with st.sidebar:
    st.header("Pipeline Configurations")
    selected_year = st.selectbox("Season Year", [2024, 2025, 2026], index=0)
    selected_track = st.selectbox("Grand Prix Location", ["Spa", "Monza", "Silverstone", "Monaco"], index=0)
    selected_session = st.selectbox("Session Type", ["Q", "R", "FP1", "FP2", "FP3"], index=0)

# 3. Dynamic Roster Extraction (Prevents mismatched inputs)
@st.cache_data(ttl=3600)
def discover_session_roster(year, location, session_type):
    try:
        # Load a minimal shell profile without pulling massive telemetry binaries yet
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=False, laps=False, weather=False)
        results = session.results
        
        if results.empty:
            return {}
        
        # Strip out practice-only backup drivers or rows missing key identifiers
        valid_rows = results.dropna(subset=['FullName', 'Abbreviation'])
        return dict(zip(valid_rows['FullName'], valid_rows['Abbreviation']))
    except Exception:
        return {}

# Run roster lookup based on Stage 1 inputs
driver_map = discover_session_roster(selected_year, selected_track, selected_session)

# 4. Sidebar Layout - Stage 2 Controls (Populated dynamically from Step 3)
with st.sidebar:
    st.subheader("Driver Alignment Selection")
    if driver_map:
        full_names_list = sorted(list(driver_map.keys()))
        
        # Establish stable safe index boundaries for default layout assignment
        default_idx1 = 0
        default_idx2 = min(1, len(full_names_list) - 1)
        
        driver_name_1 = st.selectbox("Primary Driver", full_names_list, index=default_idx1)
        driver_name_2 = st.selectbox("Comparison Driver", full_names_list, index=default_idx2)
        
        # Translate legible user-facing names back into required three-letter codes
        driver_1 = driver_map[driver_name_1]
        driver_2 = driver_map[driver_name_2]
    else:
        st.error("❌ Session Data Unavailable")
        st.info("The selected race weekend or session is not available on the remote server yet. This occurs if a weekend has not happened yet on the calendar.")
        driver_1, driver_2 = None, None

# 5. Branded Contextual Application Header 
st.markdown(
    f"""
    <div style="
        background-color: #0e1117; 
        padding: 15px 20px; 
        border-radius: 6px; 
        border-bottom: 2px solid #FF1801; 
        margin-bottom: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    ">
        <div style="display: flex; align-items: center; gap: 20px;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/3/33/Formula.1.logo.svg" 
                 style="height: 30px; width: auto; object-fit: contain;">
            <div>
                <span style="color: white; font-weight: 900; font-size: 22px; letter-spacing: 0.5px; font-family: 'Arial Black', sans-serif;">
                    MULTI-DRIVER TELEMETRY PLATFORM
                </span>
                <p style="color: #a3a8b4; margin: 3px 0 0 0; font-size: 13px; font-family: sans-serif;">
                    Spatial Coordinate Resampling Pipeline • {selected_track} {selected_year} ({selected_session})
                </p>
            </div>
        </div>
        <div style="text-align: right; font-family: sans-serif;">
            <span style="color: #ffffff; font-size: 13px; font-weight: 600; letter-spacing: 0.5px;">
                Telemetry Diagnostics Engine
            </span>
            <p style="color: #FF1801; margin: 2px 0 0 0; font-size: 11px; font-family: monospace; font-weight: bold;">
                STATUS: ONLINE
            </p>
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)

# 6. High-Fidelity Spatial Resampling Core
@st.cache_data(ttl=3600)
def process_spatial_telemetry(year, location, session_type, d1, d2):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=True, laps=True)
        
        laps_d1 = session.laps.pick_driver(d1)
        laps_d2 = session.laps.pick_driver(d2)
        
        # Verify both targets actually completed valid timed laps
        if laps_d1.empty or laps_d2.empty:
            return "MISSING_LAP_RECORD"
            
        lap_a = laps_d1.pick_fastest()
        lap_b = laps_d2.pick_fastest()
        
        if pd.isna(lap_a.LapTime) or pd.isna(lap_b.LapTime):
            return "LAP_TIME_NULL"
            
        # Isolate base telemetry streams
        tel_a = lap_a.get_telemetry().add_distance()
        tel_b = lap_b.get_telemetry().add_distance()
        
        if len(tel_a) == 0 or len(tel_b) == 0:
            return "TELEMETRY_STREAM_EMPTY"
        
        # Generate our standardized absolute 10-meter distance map grid
        max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
        distance_grid = np.arange(0, max_distance, 10)
        
        grid_df = {'Distance': distance_grid}
        for suffix, stream in [('A', tel_a), ('B', tel_b)]:
            grid_df[f'Speed_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Speed'])
            grid_df[f'Throttle_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Throttle'])
            
        return pd.DataFrame(grid_df)
    except Exception as e:
        return str(e)

# 7. Safe Execution Flow & Visualization Output
if driver_1 and driver_2:
    if driver_1 == driver_2:
        st.warning("⚠️ Identity Mirroring Detected: Please select two distinct drivers from the dropdown menus to compare tracking traces.")
    else:
        with st.spinner(f"Resampling raw log streams into aligned coordinate channels for {driver_name_1} and {driver_name_2}..."):
            result = process_spatial_telemetry(selected_year, selected_track, selected_session, driver_1, driver_2)
        
        # Handle structural issues cleanly instead of crashing the interface
        if isinstance(result, str):
            st.error("🏁 Operational Boundary Detected")
            if result in ["MISSING_LAP_RECORD", "LAP_TIME_NULL"]:
                st.info(f"The telemetry file exists, but one of the selected drivers (**{driver_name_1}** or **{driver_name_2}**) failed to record a clean lap time during this session. This is common if they retired early or crashed out. Please select another driver combination.")
            elif result == "TELEMETRY_STREAM_EMPTY":
                st.info("The API data payload returned an empty frame for this specific telemetry channel. Try checking a different practice or race session.")
            else:
                st.info(f"API Backend Response: {result}")
                
        elif isinstance(result, pd.DataFrame):
            # Generate Interactive Multi-Driver Vector Figure
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=result['Distance'], y=result['Speed_A'],
                name=driver_name_1, line=dict(color='#00D2BE', width=2),
                hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
            ))
            
            fig.add_trace(go.Scatter(
                x=result['Distance'], y=result['Speed_B'],
                name=driver_name_2, line=dict(color='#FF8700', width=2),
                hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
            ))
            
            fig.update_layout(
                template="plotly_dark",
                margin=dict(l=40, r=40, t=20, b=40),
                height=520,
                hovermode="x unified",
                xaxis=dict(title="Track Spatial Coordinates (Meters)", showgrid=True),
                yaxis=dict(title="Velocity Profile (km/h)", showgrid=True)
            )
            st.plotly_chart(fig, use_container_width=True)
