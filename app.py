import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os

# ==============================================================================
# 1. GLOBAL WORKSPACE & CACHE CONFIGURATIONS
# ==============================================================================
st.set_page_config(
    page_title="Multi-Driver F1 Telemetry Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enforce stable production scratch paths on ephemeral cloud filesystems
tmp_cache_dir = "/tmp/fastf1_cache"
if not os.path.exists(tmp_cache_dir):
    os.makedirs(tmp_cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(tmp_cache_dir)

# ==============================================================================
# 2. CORE UTILITY & DATA ENGINEERING PIPELINES
# ==============================================================================
@st.cache_data(ttl=86400)
def fetch_season_circuits(year):
    """
    Queries the central database schedule endpoint to return a clean, sorted
    list of true Grand Prix names for the selected calendar year array.
    """
    try:
        schedule = fastf1.get_event_schedule(int(year))
        # Filter out testing sessions, isolate true event profiles
        events = schedule[schedule['EventFormat'] != 'testing']
        return sorted(events['EventName'].unique().tolist())
    except:
        return ["Bahrain Grand Prix", "Saudi Arabian Grand Prix", "Australian Grand Prix", "Spanish Grand Prix"]

def load_telemetry_secure(year, grand_prix, session_type):
    """
    Secure ingestion loop that isolates memory allocation pools and forces
    full data packet compilation before feeding arrays to the analytical engines.
    """
    try:
        session = fastf1.get_session(int(year), grand_prix, session_type)
        session.load(laps=True, telemetry=True, weather=False)
        return session
    except Exception as e:
        st.sidebar.error(f"Engine Registry Alert: {str(e)}")
        return None

def resample_telemetry_grid(telemetry_df, target_distance):
    """
    Performs 1D linear array interpolation (numpy.interp) to project irregular, 
    asynchronous telemetry timestamps onto a standardized absolute distance grid.
    """
    resampled = pd.DataFrame({'Distance': target_distance})
    resampled['Speed'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Speed'])
    resampled['Throttle'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Throttle'])
    return resampled

# ==============================================================================
# 3. USER INTERFACE & SIDEBAR SELECTION CHAINS
# ==============================================================================
st.title("🏎️ Multi-Driver F1 Telemetry Analytics Platform")
st.markdown("### Spatial Coordinate Resampling Pipeline • Performance Diagnostics Engine")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ Pipeline Control Panel")
    
    # 1. Primary Scope Configurations
    selected_year = st.selectbox("Select Season Calendar", options=[2026, 2025, 2024], index=0)
    
    # Relational chain update based on chosen year variable
    available_circuits = fetch_season_circuits(selected_year)
    selected_circuit = st.selectbox("Select Location / Circuit", options=available_circuits)
    
    selected_session = st.selectbox("Select Session Profile", options=["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"])

    st.markdown("---")
    st.subheader("👥 Driver Matrix Alignments")
    driver1_input = st.text_input("Baseline Driver (3-Letter Abbreviation)", value="VER").upper()
    driver2_input = st.text_input("Comparison Driver 2 (3-Letter Abbreviation)", value="NOR").upper()
    driver3_input = st.text_input("Comparison Driver 3 (Optional / Leave Blank)", value="").upper()

    st.markdown("---")
    # Optional Professional Easter Egg Panel
    enable_audio = st.toggle("Enable Workspace Ambiance (V8 Sound)", value=False)
    if enable_audio:
        st.components.v1.html(
            """
            <audio autoplay loop style="display:none;">
                <source src="https://www.soundjay.com/transportation/sounds/race-car-driving-1.mp3" type="audio/mpeg">
            </audio>
            """, height=0, width=0
        )

# ==============================================================================
# 4. DATA PROCESSING WORKFLOW & RUNTIME EXECUTION
# ==============================================================================
if st.sidebar.button("Run Telemetry Analysis", type="primary"):
    with st.spinner("Executing spatial matrix transformations... Please wait."):
        
        session_data = load_telemetry_secure(selected_year, selected_circuit, selected_session)
        
        if session_data is None:
            st.error("### 🏁 Operational Boundary Detected")
            st.warning("The telemetry stream logs for this specific session are missing or uncompiled on the backend database. Please toggle the Year dropdown to a completed season or try another Grand Prix profile.")
        else:
            try:
                # Isolate target laps
                laps_d1 = session_data.laps.pick_driver(driver1_input)
                laps_d2 = session_data.laps.pick_driver(driver2_input)
                
                fastest_d1 = laps_d1.pick_fastest()
                fastest_d2 = laps_d2.pick_fastest()
                
                telemetry_d1 = fastest_d1.get_telemetry().add_distance()
                telemetry_d2 = fastest_d2.get_telemetry().add_distance()
                
                # Establish global 10-meter absolute distance tracking baseline array
                max_distance = min(telemetry_d1['Distance'].max(), telemetry_d2['Distance'].max())
                target_grid = np.arange(0, max_distance, 10)
                
                # Run math resampling engine
                grid_d1 = resample_telemetry_grid(telemetry_d1, target_grid)
                grid_d2 = resample_telemetry_grid(telemetry_d2, target_grid)
                
                # Optional Driver 3 Processing Block
                include_d3 = False
                if driver3_input:
                    try:
                        laps_d3 = session_data.laps.pick_driver(driver3_input)
                        fastest_d3 = laps_d3.pick_fastest()
                        telemetry_d3 = fastest_d3.get_telemetry().add_distance()
                        grid_d3 = resample_telemetry_grid(telemetry_d3, target_grid)
                        include_d3 = True
                    except:
                        st.sidebar.warning(f"Driver {driver3_input} metrics not found in logs.")
                
                # Calculate Core Performance KPI: Rolling Delta Performance Gap Time Array
                # Delta Time (approximate baseline derivation from velocity matrices)
                # t = d / v -> integrated differences
                delta_time = np.zeros(len(target_grid))
                for i in range(1, len(target_grid)):
                    v1 = max(grid_d1['Speed'].iloc[i] / 3.6, 1.0) # convert km/h to m/s, avoid zero division
                    v2 = max(grid_d2['Speed'].iloc[i] / 3.6, 1.0)
                    dt1 = 10.0 / v1
                    dt2 = 10.0 / v2
                    delta_time[i] = delta_time[i-1] + (dt1 - dt2)
                
                # ==============================================================================
                # 5. DUAL-AXIS BI-TIER VISUALIZATION FRAMEWORK (PLOTLY CORES)
                # ==============================================================================
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.1,
                    row_heights=[0.6, 0.4],
                    specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
                )
                
                # --- ROW 1: VELOCITY PROFILE & THROTTLE MAP OVERLAYS ---
                # Driver 1
                fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Speed'], name=f"{driver1_input} Velocity", line=dict(color="#00D2BE", width=2.5)), row=1, col=1, secondary_y=False)
                fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Throttle'], name=f"{driver1_input} Throttle %", line=dict(color="#00D2BE", width=1.5, dash='dash'), opacity=0.4), row=1, col=1, secondary_y=True)
                
                # Driver 2
                fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Speed'], name=f"{driver2_input} Velocity", line=dict(color="#FF8700", width=2.5)), row=1, col=1, secondary_y=False)
                fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Throttle'], name=f"{driver2_input} Throttle %", line=dict(color="#FF8700", width=1.5, dash='dash'), opacity=0.4), row=1, col=1, secondary_y=True)
                
                # Optional Driver 3 Line mapping
                if include_d3:
                    fig.add_trace(gr.Scatter(x=target_grid, y=grid_d3['Speed'], name=f"{driver3_input} Velocity", line=dict(color="#E10600", width=2.5)), row=1, col=1, secondary_y=False)
                
                # --- ROW 2: DELTA TIME PERFORMANCE GAP ---
                fig.add_trace(gr.Scatter(x=target_grid, y=delta_time, name=f"Pacing Margin (Ref: {driver1_input})", line=dict(color="#FFFFFF", width=2)), row=2, col=1)
                
                # Styling layouts
                fig.update_layout(
                    title_text=f"Telemetry Vector Analysis: {selected_circuit} ({selected_year})",
                    height=750,
                    template="plotly_dark",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                fig.update_xaxes(title_text="Absolute Track Coordinate Baseline (Meters)", row=2, col=1)
                fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
                fig.update_yaxes(title_text="Throttle Input %", maxallowed=100, minallowed=0, row=1, col=1, secondary_y=True)
                fig.update_yaxes(title_text=f"Delta Time Gap (sec Value)", row=2, col=1)
                
                # Render Graphic Asset Output
                st.plotly_chart(fig, use_container_width=True)
                
                # Analytical Insights Card
                st.info(f"💡 **Analytical Guide:** Row 2 shows the performance gap. If the white trace line drifts **upwards**, {driver2_input} is losing pace margin relative to {driver1_input}. If the trace line drops **downwards**, {driver2_input} is gaining ground.")
                
            except Exception as e:
                st.error("### 🛑 Micro-Array Conversion Error")
                st.write(f"The underlying data sequence encountered an unmapped log boundary condition. Details: {str(e)}")
else:
    st.markdown("---")
    st.subheader("📈 System Status Dashboard")
    st.success("STATUS: ONLINE • Ingestion interfaces primed. Configure parameters in the sidebar panel and execute analysis.")
