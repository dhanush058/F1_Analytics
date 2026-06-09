import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 1. Primary Page Workspace Configuration
st.set_page_config(page_title="F1 Telemetry Analytics", layout="wide")

# Enable performance data caching
try:
    fastf1.Cache.enable_cache('f1_cache')
except Exception:
    pass

# 2. Automated Season Calendar Fetcher
@st.cache_data(ttl=86400)
def fetch_season_circuits(year):
    try:
        schedule = fastf1.get_event_schedule(year)
        valid_events = schedule[schedule['EventFormat'] != 'testing']
        
        current_time = pd.Timestamp.now(tz='UTC')
        completed_events = valid_events[pd.to_datetime(valid_events['EventDate'], utc=True) < current_time]
        
        if completed_events.empty:
            return ["No Completed Races Available"]
            
        return completed_events['EventName'].tolist()
    except Exception:
        return ["Belgian Grand Prix", "Italian Grand Prix", "British Grand Prix", "Monaco Grand Prix", "Austrian Grand Prix"]

# 3. Sidebar Layout - Stage 1 Environment Dropdowns
with st.sidebar:
    st.header("Pipeline Configurations")
    selected_year = st.selectbox("Season Year", [2024, 2025, 2026], index=0)
    
    track_options = fetch_season_circuits(selected_year)
    selected_track = st.selectbox("Grand Prix Location / Circuit", track_options, index=0)
    
    selected_session = st.selectbox(
        "Session Type", 
        ["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"], 
        index=0
    )

session_map = {"Qualifying": "Q", "Race": "R", "Practice 1": "FP1", "Practice 2": "FP2", "Practice 3": "FP3"}
api_session_token = session_map[selected_session]

# 4. Dynamic Driver Roster Discovery Engine
@st.cache_data(ttl=3600)
def discover_session_roster(year, location, session_type):
    # HARD GUARD RAIL: Catch the uncompiled 2025 Australia API bug instantly
    if year == 2025 and "Australia" in location:
        return {}
    if location == "No Completed Races Available":
        return {}
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

# Build selection translation mapping table
driver_lookup_table = discover_session_roster(selected_year, selected_track, api_session_token)

# 5. Sidebar Layout - Stage 2 Separate Driver Dropdowns
with st.sidebar:
    st.subheader("Driver Alignment Selection")
    if driver_lookup_table:
        full_names_list = sorted(list(driver_lookup_table.keys()))
        
        driver_name_1 = st.selectbox("Primary Driver (Driver 1)", full_names_list, index=0)
        
        default_2 = min(1, len(full_names_list) - 1)
        driver_name_2 = st.selectbox("Comparison Driver (Driver 2)", full_names_list, index=default_2)
        
        driver_name_3 = st.selectbox("Optional Comparison (Driver 3)", ["None"] + full_names_list, index=0)
        
        active_names = [driver_name_1, driver_name_2]
        chosen_codes = [driver_lookup_table[driver_name_1], driver_lookup_table[driver_name_2]]
        
        if driver_name_3 != "None":
            active_names.append(driver_name_3)
            chosen_codes.append(driver_lookup_table[driver_name_3])
    else:
        st.error("❌ Telemetry File Missing on API Server")
        st.info("The configuration for this weekend is unavailable on the remote database server. **Note:** The 2025 Australian Grand Prix data streams are uncompiled by FastF1. Please switch to **2024** or select another GP on the list.")
        active_names, chosen_codes = [], []

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
        
        for code in driver_codes:
            driver_laps = session.laps.pick_driver(code)
            if driver_laps.empty or pd.isna(driver_laps.pick_fastest().LapTime):
                return f"MISSING_LAP_{code}"
                
            tel = driver_laps.pick_fastest().get_telemetry().add_distance()
            if len(tel) == 0:
                return f"EMPTY_STREAM_{code}"
                
            streams[code] = tel
            min_max_distance = min(min_max_distance, tel['Distance'].max())
            
        distance_grid = np.arange(0, min_max_distance, 10)
        grid_data = {'Distance': distance_grid}
        
        for code, stream in streams.items():
            grid_data[f'Speed_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Speed'])
            grid_data[f'Throttle_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Throttle'])
            grid_data[f'Time_{code}'] = np.interp(distance_grid, stream['Distance'], stream['Time'].dt.total_seconds())
            
        df = pd.DataFrame(grid_data)
        
        base_code = driver_codes[0]
        for code in driver_codes[1:]:
            df[f'Delta_vs_{code}'] = df[f'Time_{base_code}'] - df[f'Time_{code}']
            
        return df
    except Exception as e:
        return str(e)

# 8. Operational Execution Routine
if len(chosen_codes) >= 2:
    if len(chosen_codes) != len(set(chosen_codes)):
        st.error("🏁 Selection Conflict: Duplicate drivers chosen across separate menu slots.")
    else:
        with st.spinner("Processing telemetry arrays across spatial coordinates..."):
            df = load_multi_driver_telemetry(selected_year, selected_track, api_session_token, chosen_codes)
            
        if isinstance(df, str):
            st.error("🏁 Operational Boundary Detected")
            st.info(f"API Trace Information: {df}")
                
        elif isinstance(df, pd.DataFrame):
            # 9. Multi-Tier Subplot Construction (FIXED Spacing and margins)
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08,
                row_heights=[0.65, 0.35],
                specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
                subplot_titles=("<br>Velocity Profiles & Throttle Inputs Map", "<br>Time Delta Performance Gap Relative to Primary Driver (Seconds)")
            )
            
            color_palette = ['#00D2BE', '#FF8700', '#FF33FF']
            colors = {code: color_palette[i] for i, code in enumerate(chosen_codes)}
                
            for code in chosen_codes:
                full_name = active_names[chosen_codes.index(code)]
                
                # Velocity Line
                fig.add_trace(go.Scatter(
                    x=df['Distance'], y=df[f'Speed_{code}'], name=f"{full_name} Speed",
                    line=dict(color=colors[code], width=2), hovertemplate="Distance: %{x}m<br>Speed: %{y} km/h"
                ), row=1, col=1, secondary_y=False)
                
                # Throttle Line
                fig.add_trace(go.Scatter(
                    x=df['Distance'], y=df[f'Throttle_{code}'], name=f"{code} Throttle",
                    line=dict(color=colors[code], width=1, dash='dash'), opacity=0.45, hovertemplate="Throttle: %{y}%"
                ), row=1, col=1, secondary_y=True)
                
            # Delta Line
            for code in chosen_codes[1:]:
                fig.add_trace(go.Scatter(
                    x=df['Distance'], y=df[f'Delta_vs_{code}'], name=f"Delta: {chosen_codes[0]} vs {code}",
                    line=dict(color=colors[code], width=1.5, dash='dot'), hovertemplate="Distance: %{x}m<br>Gap: %{y}s"
                ), row=2, col=1)
                
            fig.update_layout(
                template="plotly_dark",
                height=700,
                hovermode="x unified",
                margin=dict(l=50, r=50, t=70, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="right", x=1)
            )
            
            fig.update_xaxes(title_text="Track Spatial Coordinates (Meters)", row=2, col=1)
            fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
            fig.update_yaxes(title_text="Throttle Input (%)", row=1, col=1, secondary_y=True, range=[0, 105], showgrid=False)
            fig.update_yaxes(title_text="Time Delta (s)", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)

# 10. Portfolio Documentation & Analytical User Guide
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
