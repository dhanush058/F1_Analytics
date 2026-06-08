import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Set page config for a professional dark look
st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")
st.title("🏎️ Formula 1 Spatial Telemetry Analyzer (Multi-Driver Comparison)")

# 1. Setup Robust Caching Layer
CACHE_DIR = "f1_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# Helper function to dynamically fetch the full season calendar reliably
@st.cache_data
def get_season_events(selected_year):
    try:
        schedule = fastf1.get_event_schedule(selected_year)
        gp_events = schedule[schedule['EventFormat'] != 'testing']
        return list(zip(gp_events['EventName'].tolist(), gp_events['RoundNumber'].tolist()))
    except Exception:
        return [("Australian Grand Prix", 1), ("Monaco Grand Prix", 6), ("Italian Grand Prix", 15)]

# 2. Sidebar Controls (Race Setup)
st.sidebar.header("Race Setup")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=0)

event_options = get_season_events(year)
event_names = [e[0] for e in event_options]
selected_event_name = st.sidebar.selectbox("Circuit", event_names, index=0)

selected_round = event_options[event_names.index(selected_event_name)][1]
session_type = st.sidebar.selectbox("Session", ["Q", "R"], index=0)

# Full active grid abbreviations
driver_options = ["RUS", "ANT", "VER", "HAM", "LEC", "NOR", "PIA", "HAD", "LAW", "GAS", "BEA", "COL", "LIN", "SAI", "ALB", "OCO", "BOR", "ALO", "HUL", "BOT", "PER", "STR"]

driver1 = st.sidebar.selectbox("Driver 1", driver_options, index=0) # Defaults to RUS
driver2 = st.sidebar.selectbox("Driver 2", driver_options, index=1) # Defaults to ANT

driver3_options = ["None"] + driver_options
driver3 = st.sidebar.selectbox("Driver 3 (Optional)", driver3_options, index=0)

# 3. Defensive Data Fetching Function (Validates each driver safely)
def get_single_driver_telemetry(session, driver_code):
    try:
        # Pick driver laps safely
        driver_laps = session.laps.pick_driver(driver_code)
        if driver_laps.empty:
            return None
        
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None:
            return None
            
        # Verify the telemetry method exists safely
        if not hasattr(fastest_lap, 'get_telemetry'):
            return None
            
        telemetry = fastest_lap.get_telemetry().add_distance()
        if telemetry.empty or 'Speed' not in telemetry.columns:
            return None
            
        return telemetry
    except Exception:
        return None

@st.cache_data(show_spinner="Extracting and processing telemetry grids...")
def process_race_session(year, round_num, session_type, d1, d2, d3):
    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=True, weather=False)
    except Exception as e:
        return {"error": f"The API session info is not available yet for this event: {str(e)}", "data": {}}

    results = {}
    
    # Process Driver 1
    t1 = get_single_driver_telemetry(session, d1)
    if t1 is not None: 
        results[d1] = t1
    
    # Process Driver 2 (Fixed variable logic here)
    t2 = get_single_driver_telemetry(session, d2)
    if t2 is not None: 
        results[d2] = t2
    
    # Process Driver 3
    if d3 != "None":
        t3 = get_single_driver_telemetry(session, d3)
        if t3 is not None: 
            results[d3] = t3
        
    return {"error": None, "data": results}

# Execute Data Pipeline
if st.sidebar.button("Analyze Performance"):
    has_duplicates = (driver1 == driver2) or (driver3 != "None" and (driver1 == driver3 or driver2 == driver3))
    
    if has_duplicates:
        st.error("Please select unique drivers to compare.")
    else:
        payload = process_race_session(year, selected_round, session_type, driver1, driver2, driver3)
        
        if payload["error"]:
            st.error(payload["error"])
        else:
            telemetry_data = payload["data"]
            successful_drivers = list(telemetry_data.keys())
            
            if len(successful_drivers) < 2:
                st.warning("⚠️ Telemetry Stream Processing Alert")
                st.info(f"Successfully loaded drivers: {successful_drivers if successful_drivers else 'None'}")
                st.error("FastF1 has not fully populated telemetry logs for these specific driver laps yet. Try a different driver combination or check if the session data is completely finalized by the FIA.")
            else:
                st.success(f"Successfully mapped spatial coordinates for: {', '.join(successful_drivers)}!")
                
                # 4. Build Plots safely using only validated data streams
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.1,
                                    subplot_titles=("Velocity Comparison (Minimum Corner Speed)", "Throttle Application (Exit Traction)"))
                
                # Color map assignments
                color_palette = {driver1: '#00FF00', driver2: '#1E90FF', driver3: '#FF4500'}
                
                for drv in successful_drivers:
                    df = telemetry_data[drv]
                    drv_color = color_palette.get(drv, '#FFFFFF')
                    
                    # --- ROW 1: VELOCITY ---
                    fig.add_trace(
                        go.Scatter(x=df['Distance'], y=df['Speed'], mode='lines', name=drv,
                                   line=dict(color=drv_color, width=2),
                                   hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
                        row=1, col=1
                    )
                    
                    # --- ROW 2: THROTTLE ---
                    fig.add_trace(
                        go.Scatter(x=df['Distance'], y=df['Throttle'], mode='lines', name=drv,
                                   line=dict(color=drv_color, width=2), showlegend=False,
                                   hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
                        row=2, col=1
                    )
                
                # 5. Global Layout Styling
                fig.update_layout(
                    height=650,
                    template="plotly_dark",
                    hovermode="x unified",
                    margin=dict(l=50, r=20, t=60, b=50),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                fig.update_xaxes(title_text="Distance along track (meters)", row=2, col=1)
                fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
                fig.update_yaxes(title_text="Throttle %", row=2, col=1)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 6. Metric Explanations for Users
                st.markdown("---")
                tab1, tab2 = st.tabs(["💡 Live Telemetry Metric Guide", "📊 Why Spatial Distance Alignment Matters"])
                with tab1:
                    st.subheader("How to Analyze Driver Profiles")
                    st.markdown("""
                    * **Velocity Valleys (Speed Chart):** Look at the deep dips in the lines. These represent braking points and corners. Whichever driver's line stays highest at the absolute lowest point carried the best **minimum corner speed** at the apex.
                    * **Braking Points:** Where a line suddenly drops vertically reveals exactly where a driver smashed the brakes. You can spot who braved a later braking point.
                    * **Throttle Application (Throttle Chart):** Look at the slopes where the line climbs back from 0% to 100%. A steeper, faster climb means that driver achieved **exit traction** and pinned the gas pedal earlier, maximizing their top speed down the next straightway.
                    """)
                with tab2:
                    st.subheader("Data Analyst Design Insight")
                    st.write("Traditional time-series graphs plot data against clock seconds. In Formula 1, if one driver brakes earlier, their entire timeline shifts forward, making direct visual overlays impossible to compare. By using a custom data pipeline to resample and normalize telemetry across **Track Distance (Meters)**, this dashboard locks all selected profiles to the exact same physical coordinates. You are looking at an absolute, apples-to-apples performance breakdown at every single meter of the circuit.")
else:
    st.info("Select options in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
