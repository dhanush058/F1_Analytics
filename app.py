import os
import streamlit as st
import matplotlib.pyplot as plt
import fastf1
import fastf1.plotting

# ==============================================================================
# 🛠️ GLOBAL ENVIRONMENT & STREAMLIT SETUP
# ==============================================================================
st.set_page_config(
    page_title="Multi-Driver F1 Telemetry Analyzer", 
    page_icon="🏎️", 
    layout="wide"
)

# Apply FastF1's official color mapping styles for Matplotlib
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# Enable disk caching. This prevents downloading massive telemetry files 
# multiple times, optimizing server performance.
if not os.path.exists('f1_cache'):
    os.makedirs('f1_cache')
fastf1.Cache.enable_cache('f1_cache')

# ==============================================================================
# 🎨 SIDEBAR INTERFACE CONTROL PANEL
# ==============================================================================
st.sidebar.header("🏁 Race Settings")

# Form inputs for session targeting
year = st.sidebar.number_input("📅 Season Year", min_value=2018, max_value=2026, value=2025, step=1)
gp_name = st.sidebar.text_input("📍 Grand Prix Location", value="Monza")
session_type = st.sidebar.selectbox(
    "⏱️ Session Type", 
    options=["Q", "R", "FP1", "FP2", "FP3"], 
    index=0,
    help="Q = Qualifying, R = Race, FP = Free Practice"
)

st.sidebar.markdown("---")
st.sidebar.subheader("🏎️ Driver Comparison Group")
# Input multiple drivers split by commas (e.g., VER, HAM, LEC, NOR)
drivers_input = st.sidebar.text_input("Enter Driver Codes (Comma Separated)", value="VER, HAM, LEC")

analyze_btn = st.sidebar.button("⚡ Run Multi-Analysis", use_container_width=True)

# ==============================================================================
# 📊 MAIN CONTENT DATA VISUALIZATION ENGINE
# ==============================================================================
st.title("🏎️ Formula 1 Multi-Driver Performance Dashboard")
st.markdown("Analyze telemetry logs synchronized meter-by-meter along the physical layout of the circuit perimeter.")

if analyze_btn:
    # Split input text into a clean list of capitalized strings
    driver_list = [d.strip().upper() for d in drivers_input.split(",") if d.strip()]
    
    if len(driver_list) < 2:
        st.error("❌ Please input at least two driver codes to generate a comparative analysis.")
        st.stop()

    with st.spinner("📥 Extracting telemetry matrices from API stream..."):
        try:
            # Fetch and load telemetry data
            session = fastf1.get_session(year, gp_name, session_type)
            session.load()
            
            fastest_laps = {}
            telemetry_data = {}
            team_colors = {}
            
            # Loop through driver inputs, skip with a warning if a driver has no data
            for driver in driver_list:
                try:
                    lap = session.laps.pick_driver(driver).pick_fastest()
                    fastest_laps[driver] = lap
                    telemetry_data[driver] = lap.get_car_data().add_distance()
                    team_colors[driver] = fastf1.plotting.get_driver_color(driver, session=session)
                except Exception:
                    st.warning(f"⚠️ Telemetry log or lap data missing for driver: {driver}. Skipping.")
            
            valid_drivers = list(fastest_laps.keys())
            if len(valid_drivers) < 2:
                st.error("❌ Not enough valid telemetry found to construct comparison charts.")
                st.stop()
                
            # Set the baseline reference driver (the absolute fastest time among inputs)
            baseline_driver = min(valid_drivers, key=lambda d: fastest_laps[d]['LapTime'])
            
        except Exception as e:
            st.error(f"❌ Core Data Extraction Failure. Verify year or circuit location spelling.")
            st.info(f"Technical Log: {e}")
            st.stop()

    # SECTION 1: Performance Summary Metric Cards
    st.markdown(f"### ⏱️ Lap Leaderboard (Baseline Tracking Target: **{baseline_driver}**)")
    cols = st.columns(len(valid_drivers))
    
    for i, driver in enumerate(sorted(valid_drivers, key=lambda d: fastest_laps[d]['LapTime'])):
        with cols[i]:
            is_baseline = "⭐ " if driver == baseline_driver else ""
            st.metric(
                label=f"{is_baseline}{driver}", 
                value=str(fastest_laps[driver]['LapTime'])[:-3]
            )

    # SECTION 2: Matplotlib Overlaid Graphs
    st.markdown("### 📊 Synchronized Telemetry Traces")
    
    fig, ax = plt.subplots(3, 1, figsize=(14, 11), sharex=True, 
                           gridspec_kw={'height_ratios': [1.5, 2, 1]})

    # Dynamic trace building loop
    for driver in valid_drivers:
        color = team_colors[driver]
        tel = telemetry_data[driver]
        
        # 1. Speed Profile Panel
        ax[1].plot(tel['Distance'], tel['Speed'], label=driver, color=color, linewidth=1.5, alpha=0.85)
        
        # 2. Throttle Application Panel
        ax[2].plot(tel['Distance'], tel['Throttle'], color=color, linewidth=1.2, alpha=0.7)
        
        # 3. Time Delta Vector Panel (Relative to the chosen session baseline)
        if driver != baseline_driver:
            delta_time, ref_tel, _ = fastf1.utils.delta_time(fastest_laps[baseline_driver], fastest_laps[driver])
            ax[0].plot(ref_tel['Distance'], delta_time, label=f"{driver} vs {baseline_driver}", color=color, linewidth=1.5)

    # Apply layout cleanups and axes boundaries
    ax[0].axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax[0].set_ylabel('Delta Time (Seconds)\n[ Climbing = Losing Time ]')
    ax[0].legend(loc='upper left')
    ax[0].set_title(f"{session.event['EventName']} - {session.name} Session Overlays", fontsize=12)

    ax[1].set_ylabel('Velocity (km/h)')
    ax[1].legend(loc='lower left')
    ax[1].grid(True, linestyle=':', alpha=0.3)

    ax[2].set_ylabel('Throttle %')
    ax[2].set_xlabel('Physical Distance Along Track (Meters)')
    ax[2].grid(True, linestyle=':', alpha=0.3)

    plt.tight_layout()
    
    # Render the chart on the webpage
    st.pyplot(fig)
    
else:
    # Default app welcoming state
    st.info("👈 Set your race inputs in the sidebar and click 'Run Multi-Analysis' to compile telemetry.")