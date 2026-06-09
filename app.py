import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 1. Page Configuration Setup
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable FastF1 caching to speed up data loading
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass

# 2. Sidebar Dropdown Selectors
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

# 4. Telemetry Processing Engine with Absolute Spatial Resampling
@st.cache_data(ttl=3600)
def load_telemetry_data(year, location, session_type, driver_a, driver_b):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=True, laps=True)
        
        # Verify drivers exist in session data
        available_drivers = session.laps['Driver'].unique()
        if driver_a not in available_drivers or driver_b not in available_drivers:
            return "DRIVER_NOT_FOUND"
        
        lap_a = session.laps.pick_driver(driver_a).pick_fastest()
        lap_b = session.laps.pick_driver(driver_b).pick_fastest()
        
        if pd.isna(lap_a.LapTime) or pd.isna(lap_b.LapTime):
            return "NO_VALID_LAP"
        
        tel_a = lap_a.get_telemetry().add_distance()
        tel_b = lap_b.get_telemetry().add_distance()
        
        max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
        distance_grid = np.arange(0, max_distance, 10)
        
        grid_data = {'Distance': distance_grid}
        for dr_id, tel in [('A', tel_a), ('B', tel_b)]:
            grid_data[f'Speed_{dr_id}'] = np.interp(distance_grid, tel['Distance'], tel['Speed'])
            grid_data[f'Throttle_{dr_id}'] = np.interp(distance_grid, tel['Distance'], tel['Throttle'])
            grid_data[f'Time_{dr_id}'] = np.interp(distance_grid, tel['Distance'], tel['Time'].dt.total_seconds())
        
        df = pd.DataFrame(grid_data)
        df['Delta_Time'] = df['Time_A'] - df['Time_B']
        return df
    except Exception as e:
        return str(e)

# 5. Core Operational Flow & Boundary Safeguards
if not driver_1 or not driver_2:
    st.warning("⚠️ Please provide driver abbreviations in the sidebar inputs (e.g., VER, NOR, HAM).")
elif driver_1 == driver_2:
    st.error("🏁 Selection Conflict: Cannot compute a spatial telemetry delta against the same driver profile.")
else:
    with st.spinner(f"Requesting data and executing resampling arrays..."):
        df = load_telemetry_data(selected_year, selected_track, selected_session, driver_1, driver_2)

    # CRITICAL FIX: Intercept errors or unreleased data streams before running Plotly layout routines
    if isinstance(df, str):
        st.error("🏁 Operational Boundary Detected")
        if "not been loaded yet" in df or "loaded yet" in df:
            st.info(f"The session **{selected_track} ({selected_year})** has not taken place yet or its data is not yet formatted on the server. Please switch the year selection to **2024** or **2025** to view archived data configurations.")
        elif df == "DRIVER_NOT_FOUND":
            st.info(f"One or both driver codes ({driver_1} / {driver_2}) did not participate in this specific event weekend.")
        elif df == "NO_VALID_LAP":
            st.info("Telemetry found, but one of the selected drivers failed to complete a valid timed lap in this session (e.g., a technical DNF or crash).")
        else:
            st.info(f"API System Response: {df}")
            
    elif isinstance(df, pd.DataFrame):
        # 6. Advanced Synchronized Multi-Tier Subplot Construction
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=("Velocity Profile & Throttle Inputs Map", "Delta Time Grid Baseline")
        )

        hover_a = f"<b>Distance:</b> %{{x}}m<br><b>{driver_1}:</b> %{{y}} km/h<br><b>Throttle:</b> %{{customdata[0]}}%"
        hover_b = f"<b>Distance:</b> %{{x}}m<br><b>{driver_2}:</b> %{{y}} km/h<br><b>Throttle:</b> %{{customdata[0]}}%"

        # Row 1: Velocity Tracks
        fig.add_trace(go.Scatter(x=df['Distance'], y=df['Speed_A'], name=driver_1, line=dict(color='#00D2BE', width=2),
                                 customdata=df[['Throttle_A']], hovertemplate=hover_a), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Distance'], y=df['Speed_B'], name=driver_2, line=dict(color='#FF8700', width=2),
                                 customdata=df[['Throttle_B']], hovertemplate=hover_b), row=1, col=1)

        # Row 2: Mathematical Delta-Time Trace
        fig.add_trace(go.Scatter(x=df['Distance'], y=df['Delta_Time'], name=f"Delta ({driver_1} vs {driver_2})", line=dict(color='#FFFFFF', width=1.5, dash='dot'),
                                 hovertemplate="<b>Distance:</b> %{x}m<br><b>Gap:</b> %{y}s"), row=2, col=1)

        # Unified UI Theming & Shared Axis Configurations
        fig.update_layout(
            template="plotly_dark",
            height=650,
            hovermode="x unified",
            margin=dict(l=50, r=50, t=30, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig.update_xaxes(title_text="Track Spatial Track Coordinates (Meters)", row=2, col=1)
        fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1)
        fig.update_yaxes(title_text="Time Gap (s)", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)
