import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 1. Primary Page Workspace Configuration
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable automatic local data caching
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass

# 2. Cached Schedule Engine (Dynamically gathers official Grand Prix names for the drop-down)
@st.cache_data(ttl=86400)
def fetch_season_circuits(year):
    try:
        schedule = fastf1.get_event_schedule(year)
        # Filter out testing data rows
        valid_events = schedule[schedule['EventFormat'] != 'testing']
        return valid_events['EventName'].tolist()
    except Exception:
        # High-quality fallback if the remote server connection times out
        return ["Belgian Grand Prix", "Italian Grand Prix", "British Grand Prix", "Monaco Grand Prix"]

# 3. Sidebar Layout - Stage 1 Environment Drop-downs
with st.sidebar:
    st.header("Pipeline Configurations")
    selected_year = st.selectbox("Season Year", [2024, 2025, 2026], index=0)
    
    # CIRCUIT IS NOW A DYNAMIC DROP-DOWN (No text typing required)
    track_options = fetch_season_circuits(selected_year)
    selected_track = st.selectbox("Grand Prix Location / Circuit", track_options, index=0)
    selected_session = st.selectbox("Session Type", ["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"], index=0)

# Translate reader-friendly session names to FastF1 identifier tokens
session_map = {
    "Qualifying": "Q",
    "Race": "R",
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3"
}
api_session_token = session_map[selected_session]

# 4. Dynamic Driver Roster Discovery Engine
@st.cache_data(ttl=3600)
def discover_session_roster(year, location, session_type):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=False, laps=False, weather=False)
        results = session.results
        if results.empty:
            return {}
        valid_rows = results.dropna(subset=['FullName', 'Abbreviation'])
        return dict(zip(valid_rows['FullName'], valid_rows['Abbreviation']))
    except Exception:
        return {}

# Fetch active roster dictionary mapping Full Names -> Abbreviation Codes
driver_lookup_table = discover_session_roster(selected_year, selected_track, api_session_token)

# 5. Sidebar Layout - Stage 2 Multi-Driver Drop-down (Supports 2 or 3 Selections)
with st.sidebar:
    st.subheader("Driver Alignment Selection")
    if driver_lookup_table:
        full_names_list = sorted(list(driver_lookup_table.keys()))
        
        # DRIVERS SELECTION IS A MULTI-DROP-DOWN (Min 2, Max 3)
        selected_driver_names = st.multiselect(
            "Select Drivers (Min 2, Max 3)", 
            options=full_names_list,
            default=full_names_list[:2]
        )
        
        # Translate the full names back into the short codes for the data engineering pipeline
        chosen_codes = [driver_lookup_table[name] for name in selected_driver_names]
    else:
        st.error("❌ Data Registry Offline")
        st.info("The API data for this session is not available. This is normal if you selected a 2026 race that hasn't happened yet.")
        selected_driver_names, chosen_codes = [], []

# 6. Branded Dynamic Header Injection
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

# 7. Flexible Multi-Driver Telemetry Resampling Engine
@st.cache_data(ttl=3600)
def load_multi_driver_telemetry(year, location, session_type, driver_codes):
    try:
        session = fastf1.get_session(year, location, session_type)
        session.load(telemetry=True, laps=True)
        
        streams = {}
        min_max_distance = 999999
        
        # Gather data loops dynamically for all requested drivers
        for code in driver_codes:
            driver_laps = session.laps.pick_driver(code)
            if driver_laps.empty or pd.isna(driver_laps.pick_fastest().LapTime):
                return f"MISSING_LAP_{code}"
                
            tel = driver_laps.pick_fastest().get_telemetry().add_distance()
            if len(tel) == 0:
                return f"EMPTY_STREAM_{code}"
                
            streams[code] = tel
            min_max_distance = min(min_max_distance, tel['Distance'].max())
            
        # Standardized 10-meter absolute distance tracking grid
        distance_grid = np.arange(0, min_max_distance, 10)
        grid_data = {'Distance': distance_grid}
        
        # Resample traces onto the shared coordinate axis
        for code, stream in streams.items():
            grid_data[f'Speed_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Speed'])
            grid_data[f'Throttle_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Throttle'])
            grid_data[f'Time_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Time'].dt.total_seconds())
            
        df = pd.DataFrame(grid_data)
        
        # Calculate Delta performance arrays relative to the first selected driver baseline
        base_code = driver_codes[0]
        for code in driver_codes[1:]:
            df[f'Delta_vs_{code}'] = df[f'Time_{base_code}'] - df[f'Time_{code}']
            
        return df
    except Exception as e:
        return str(e)

# 8. Operational Execution Routine & Validation Check
if len(chosen_codes) < 2 or len(chosen_codes) > 3:
    st.warning("⚠️ Alignment Boundary: Please choose either 2 or 3 drivers from the drop-down menu to display the plots.")
else:
    with st.spinner("Processing telemetry arrays across spatial coordinates..."):
        df = load_multi_driver_telemetry(selected_year, selected_track, api_session_token, chosen_codes)
        
    if isinstance(df, str):
        st.error("🏁 Operational Boundary Detected")
        if "loaded yet" in df or "not been loaded" in df:
            st.info("The session data has not been uploaded to the server yet. Please change your Year selection to **2024** or **2025** to load this track layout.")
        elif "MISSING_LAP" in df:
            st.info(f"Driver **{df.split('_')[-1]}** did not record a valid timed lap during this session. Please update your selection.")
        else:
            st.info(f"API Backend Response: {df}")
            
    elif isinstance(df, pd.DataFrame):
        # 9. Multi-Tier Subplot Construction (Restoring ALL 3 metrics: Velocity, Throttle, and Delta)
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.06,
            row_heights=[0.68, 0.32],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
            subplot_titles=("Velocity Profiles & Throttle Inputs Map", f"Time Delta Performance Gap Relative to {chosen_codes[0]} (Seconds)")
        )
        
        # Color hex codes map for up to 3 traces
        colors = {chosen_codes[0]: '#00D2BE', chosen_codes[1]: '#FF8700'}
        if len(chosen_codes) == 3:
            colors[chosen_codes[2]] = '#FF33FF'
            
        # Plot Velocity (Solid lines) and Throttle (Dashed lines) for all active selections
        for code in chosen_codes:
            full_name = selected_driver_names[chosen_codes.index(code)]
            
            # Speed Trace (Primary Axis)
            fig.add_trace(go.Scatter(
                x=df['Distance'], y=df[f'Speed_{code}'], name=f"{full_name} Speed",
                line=dict(color=colors[code], width=2), hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
            ), row=1, col=1, secondary_y=False)
            
            # Throttle Trace (Secondary Axis - RESTORED)
            fig.add_trace(go.Scatter(
                x=df['Distance'], y=df[f'Throttle_{code}'], name=f"{code} Throttle Input",
                line=dict(color=colors[code], width=1, dash='dash'), opacity=0.5, hovertemplate="Throttle: %{y}%"
            ), row=1, col=1, secondary_y=True)
            
        # Plot time delta variations for additional drivers relative to baseline
        for code in chosen_codes[1:]:
            fig.add_trace(go.Scatter(
                x=df['Distance'], y=df[f'Delta_vs_{code}'], name=f"Delta: {chosen_codes[0]} vs {code}",
                line=dict(color=colors[code], width=1.5, dash='dot'), hovertemplate="Distance: %{x}m<br>Gap: %{y}s"
            ), row=2, col=1)
            
        # High-Density Dashboard Theme Styling
        fig.update_layout(
            template="plotly_dark",
            height=680,
            hovermode="x unified",
            margin=dict(l=50, r=50, t=30, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Track Spatial Coordinates (Meters)", row=2, col=1)
        fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Throttle Input (%)", row=1, col=1, secondary_y=True, range=[0, 105], showgrid=False)
        fig.update_yaxes(title_text="Time Delta (s)", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)

# 10. Portfolio Documentation & Analytical User Guide (RESTORED GUIDE)
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
