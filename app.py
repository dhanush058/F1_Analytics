import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 1. Primary Page Workspace Configuration
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable automatic local caching to optimize network payload speeds
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass

# 2. Sidebar Layout - Stage 1 Track Environment Filters
with st.sidebar:
    st.header("Pipeline Configurations")
    selected_year = st.selectbox("Season Year", [2024, 2025, 2026], index=0)
    selected_track = st.selectbox("Grand Prix Location", ["Spa", "Monza", "Silverstone", "Monaco"], index=0)
    selected_session = st.selectbox("Session Type", ["Q", "R", "FP1", "FP2", "FP3"], index=0)

# 3. Dynamic Roster Discovery (Builds the translation map)
@st.cache_data(ttl=3600)
def discover_session_roster(year, location, session_type):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=False, laps=False, weather=False)
        results = session.results
        
        if results.empty:
            return {}
        
        # Filter out empty rows and map Full Names to Abbreviation codes
        valid_rows = results.dropna(subset=['FullName', 'Abbreviation'])
        return dict(zip(valid_rows['FullName'], valid_rows['Abbreviation']))
    except Exception:
        return {}

# Generate active lookup dictionary based on track parameters
driver_map = discover_session_roster(selected_year, selected_track, selected_session)

# 4. Sidebar Layout - Stage 2 Driver Selection (Full Names Dropdowns)
with st.sidebar:
    st.subheader("Driver Alignment Selection")
    if driver_map:
        full_names_list = sorted(list(driver_map.keys()))
        
        # Establish stable default selection indexing
        default_idx1 = 0
        default_idx2 = min(1, len(full_names_list) - 1)
        
        driver_name_1 = st.selectbox("Primary Driver", full_names_list, index=default_idx1)
        driver_name_2 = st.selectbox("Comparison Driver", full_names_list, index=default_idx2)
        
        # Translate the full name back to the short code for backend processing
        driver_1 = driver_map[driver_name_1]
        driver_2 = driver_map[driver_name_2]
    else:
        st.error("❌ Session Data Unavailable")
        st.info("Telemetry logs for this specific weekend are not hosted on the remote server yet. Please switch your year selection to 2024 or 2025.")
        driver_1, driver_2 = None, None

# 5. Branded Dynamic Header Injection
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

# 6. Advanced Telemetry Core (Velocity + Throttle + Delta Time Arrays)
@st.cache_data(ttl=3600)
def load_advanced_telemetry(year, location, session_type, d1, d2):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=True, laps=True)
        
        laps_d1 = session.laps.pick_driver(d1)
        laps_d2 = session.laps.pick_driver(d2)
        
        if laps_d1.empty or laps_d2.empty:
            return "MISSING_DATA"
            
        lap_a = laps_d1.pick_fastest()
        lap_b = laps_d2.pick_fastest()
        
        if pd.isna(lap_a.LapTime) or pd.isna(lap_b.LapTime):
            return "NO_VALID_LAP"
            
        tel_a = lap_a.get_telemetry().add_distance()
        tel_b = lap_b.get_telemetry().add_distance()
        
        # Absolute 10-meter spatial distance tracking grid
        max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
        distance_grid = np.arange(0, max_distance, 10)
        
        grid_data = {'Distance': distance_grid}
        for suffix, stream in [('A', tel_a), ('B', tel_b)]:
            grid_data[f'Speed_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Speed'])
            grid_data[f'Throttle_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Throttle'])
            grid_data[f'Time_{suffix}'] = np.interp(distance_grid, stream['Distance'], stream['Time'].dt.total_seconds())
        
        df = pd.DataFrame(grid_data)
        # Calculate Delta-Time baseline array
        df['Delta_Time'] = df['Time_A'] - df['Time_B']
        return df
    except Exception as e:
        return str(e)

# 7. Core Operational Runtime Execution Loop
if driver_1 and driver_2:
    if driver_1 == driver_2:
        st.warning("⚠️ Mirroring Conflict: Please select two distinct drivers to compute comparative deltas.")
    else:
        with st.spinner(f"Resampling raw sensor matrices for {driver_name_1} vs {driver_name_2}..."):
            df = load_advanced_telemetry(selected_year, selected_track, selected_session, driver_1, driver_2)

        if isinstance(df, str):
            st.error("🏁 Operational Boundary Detected")
            if "not been loaded yet" in df or "loaded yet" in df:
                st.info("The calendar session picked has not occurred yet or data is unreleased. Switch Year back to **2024** or **2025** to run telemetry arrays.")
            elif df == "MISSING_DATA" or df == "NO_VALID_LAP":
                st.info(f"Telemetry exists, but either **{driver_name_1}** or **{driver_name_2}** failed to log a fast timed lap in this session (e.g., a technical DNF). Try another combination.")
            else:
                st.info(f"API Response Trace: {df}")
                
        elif isinstance(df, pd.DataFrame):
            # 8. Multi-Tier Subplot Construction with Secondary Y-Axis for Throttle
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.06,
                row_heights=[0.68, 0.32],
                specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
                subplot_titles=("Velocity Profiles & Throttle Inputs Map", "Delta Time Performance Gap (Seconds)")
            )

            # Custom Interactive Hover Templates
            hover_speed_a = f"<b>Distance:</b> %{{x}}m<br><b>{driver_1} Speed:</b> %{{y}} km/h"
            hover_speed_b = f"<b>Distance:</b> %{{x}}m<br><b>{driver_2} Speed:</b> %{{y}} km/h"
            hover_throt_a = f"<b>{driver_1} Throttle:</b> %{{y}}%"
            hover_throt_b = f"<b>{driver_2} Throttle:</b> %{{y}}%"

            # --- ROW 1: VELOCITY TRACES (Primary Y-Axis) ---
            fig.add_trace(go.Scatter(x=df['Distance'], y=df['Speed_A'], name=f"{driver_name_1} Speed", 
                                     line=dict(color='#00D2BE', width=2), hovertemplate=hover_speed_a), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(x=df['Distance'], y=df['Speed_B'], name=f"{driver_name_2} Speed", 
                                     line=dict(color='#FF8700', width=2), hovertemplate=hover_speed_b), row=1, col=1, secondary_y=False)

            # --- ROW 1: RESTORED THROTTLE TRACES (Secondary Y-Axis) ---
            fig.add_trace(go.Scatter(x=df['Distance'], y=df['Throttle_A'], name=f"{driver_1} Throttle", 
                                     line=dict(color='#00D2BE', width=1, dash='dash'), opacity=0.55, hovertemplate=hover_throt_a), row=1, col=1, secondary_y=True)
            fig.add_trace(go.Scatter(x=df['Distance'], y=df['Throttle_B'], name=f"{driver_2} Throttle", 
                                     line=dict(color='#FF8700', width=1, dash='dash'), opacity=0.55, hovertemplate=hover_throt_b), row=1, col=1, secondary_y=True)

            # --- ROW 2: DELTA-TIME GAP TRACE ---
            fig.add_trace(go.Scatter(x=df['Distance'], y=df['Delta_Time'], name=f"Delta Gap (A vs B)", 
                                     line=dict(color='#FFFFFF', width=1.5, dash='dot'), hovertemplate="<b>Distance:</b> %{x}m<br><b>Gap:</b> %{y}s"), row=2, col=1)

            # High-Density Dashboard Theme Styling
            fig.update_layout(
                template="plotly_dark",
                height=680,
                hovermode="x unified",
                margin=dict(l=50, r=50, t=30, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            # Configure Layout Titles and Limits
            fig.update_xaxes(title_text="Track Spatial Coordinates (Meters)", row=2, col=1)
            fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Throttle Input (%)", row=1, col=1, secondary_y=True, range=[0, 105], showgrid=False)
            fig.update_yaxes(title_text="Time Delta (s)", row=2, col=1)

            st.plotly_chart(fig, use_container_width=True)

# 9. Portfolio Documentation & Analytical User Guide
st.markdown("---")
st.subheader("💡 Analytical Operations & System Documentation")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    ### 🏗️ Architectural Pipeline Logic
    * **Asynchronous Resampling:** F1 telemetry sensors log speed and throttle variables over fluctuating timestamps. This pipeline discards time entirely and projects telemetry onto a standardized, absolute **10-meter spatial distance map grid** using 1D linear array interpolation (`numpy.interp`).
    * **Dynamic Roster Mapping:** To eliminate selection mismatch crashes, the app executes a pre-flight metadata pass (`discover_session_roster`), mining the session registry to match human-readable driver names to telemetry stream tokens.
    """)

with col2:
    st.markdown("""
    ### 📊 Metric Evaluation Guide
    * **Throttle vs. Velocity Correlation:** By overlaying Throttle inputs (dashed lines) directly against Velocity (solid lines), you can instantly isolate driver micro-behaviors—such as who jumps back onto 100% full throttle earlier on a corner exit.
    * **Reading the Delta Time Graph:** The secondary plot tracks cumulative pacing differences down to the meter. An ascending delta line means the Primary Driver is actively pulling away; a descending trend indicates the Comparison Driver is gaining time.
    """)
