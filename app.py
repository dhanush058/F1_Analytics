import streamlit as st
import fastf1
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# 1. Page Configuration Setup
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable FastF1 caching to speed up data loading
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass

# 2. Sidebar Control Configuration
with st.sidebar:
    st.header("Pipeline Configurations")
    selected_year = st.selectbox("Season Year", [2024, 2025, 2026], index=0)
    selected_track = st.selectbox("Grand Prix Location", ["Spa", "Monza", "Silverstone", "Monaco"], index=0)
    selected_session = st.selectbox("Session Type", ["Q", "R", "FP1", "FP2", "FP3"], index=0)
    
    st.subheader("Driver Selectors")
    driver_1 = st.text_input("Primary Driver Code", value="VER").upper().strip()
    driver_2 = st.text_input("Comparison Driver Code", value="NOR").upper().strip()

# 3. Branded Dynamic Header Injection
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

# 4. Core Analytical Telemetry Engine
@st.cache_data(ttl=3600)
def process_spatial_telemetry(year, location, session_type, d1, d2):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=True, laps=True)
        
        # Verify drivers exist in data
        available_drivers = session.laps['Driver'].unique()
        if d1 not in available_drivers or d2 not in available_drivers:
            return "DRIVER_NOT_FOUND"
            
        lap_a = session.laps.pick_driver(d1).pick_fastest()
        lap_b = session.laps.pick_driver(d2).pick_fastest()
        
        if pd.isna(lap_a.LapTime) or pd.isna(lap_b.LapTime):
            return "NO_LAP_TIME"
            
        tel_a = lap_a.get_telemetry().add_distance()
        tel_b = lap_b.get_telemetry().add_distance()
        
        # Absolute 10-meter spatial distance grid
        max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
        distance_grid = np.arange(0, max_distance, 10)
        
        grid_data = {'Distance': distance_grid}
        for suffix, stream in [('A', tel_a), ('B', tel_b)]:
            grid_data[f'Speed_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Speed'])
            
        return pd.DataFrame(grid_data)
    except Exception as e:
        return str(e)

# 5. Operational Execution Routine
if not driver_1 or not driver_2:
    st.warning("⚠️ Please provide driver abbreviations in the sidebar inputs (e.g., VER, NOR).")
elif driver_1 == driver_2:
    st.error("🏁 Selection Conflict: Cannot compare a driver against themselves.")
else:
    with st.spinner(f"Resampling spatial matrices for {driver_1} vs {driver_2}..."):
        df = process_spatial_telemetry(selected_year, selected_track, selected_session, driver_1, driver_2)

    # THE FIX: Stop errors or unreleased 2026 data loops from hitting Plotly and creating blank screens
    if isinstance(df, str):
        st.error("🏁 Operational Boundary Detected")
        if "not been loaded yet" in df or "loaded yet" in df:
            st.info(f"The session data for **{selected_track} ({selected_year})** is not published on the server yet. Please switch the year selection to **2024** or **2025** to test this track configuration.")
        elif df == "DRIVER_NOT_FOUND":
            st.info(f"One or both driver codes ({driver_1} / {driver_2}) did not participate in this specific race weekend.")
        elif df == "NO_LAP_TIME":
            st.info("One of the chosen drivers failed to record a valid timed lap in this session (e.g., a crash or DNF).")
        else:
            st.info(f"API Trace: {df}")
            
    elif isinstance(df, pd.DataFrame):
        # 6. Original Plotly Trace Generation
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['Distance'], y=df['Speed_A'],
            name=driver_1, line=dict(color='#00D2BE', width=2),
            hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
        ))
        
        fig.add_trace(go.Scatter(
            x=df['Distance'], y=df['Speed_B'],
            name=driver_2, line=dict(color='#FF8700', width=2),
            hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
        ))
        
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=40, r=40, t=20, b=40),
            height=500,
            hovermode="x unified",
            xaxis=dict(title="Track Spatial Coordinates (Meters)", showgrid=True),
            yaxis=dict(title="Velocity Profile (km/h)", showgrid=True)
        )
        st.plotly_chart(fig, use_container_width=True)
