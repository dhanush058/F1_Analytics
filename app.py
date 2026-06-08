import subprocess
import sys
import os

# ==============================================================================
# 📦 DYNAMIC DEPENDENCY INJECTION LAYER (CRASH PROTECTION)
# ==============================================================================
try:
    import matplotlib.pyplot as plt
    import fastf1
    import fastf1.plotting
except ModuleNotFoundError:
    # If Streamlit Cloud misses requirements.txt, force-install dependencies manually on startup
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", 
        "matplotlib", "fastf1", "pandas", "numpy", "streamlit"
    ])
    import matplotlib.pyplot as plt
    import fastf1
    import fastf1.plotting

import streamlit as st
import pandas as pd

# ==============================================================================
# 🛠️ GLOBAL ENVIRONMENT & STREAMLIT SETUP
# ==============================================================================
st.set_page_config(
    page_title="Dynamic F1 Telemetry Analyzer", 
    page_icon="🏎️", 
    layout="wide"
)

# Apply FastF1's official color mapping styles for Matplotlib
fastf1.plotting.setup_mpl(misc_mpl_mods=False)

# Force system to read the repository cache folder first
cache_dir = 'f1_cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
fastf1.Cache.enable_cache(cache_dir)

# ==============================================================================
# 🎨 SIDEBAR INTERFACE CONTROL PANEL
# ==============================================================================
st.sidebar.header("🏁 Race Settings")

year = st.sidebar.number_input("📅 Season Year", min_value=2018, max_value=2026, value=2026, step=1)
gp_name = st.sidebar.text_input("📍 Grand Prix Location", value="Monaco")
session_type = st.sidebar.selectbox("⏱️ Session Type", options=["Q", "R", "FP1", "FP2", "FP3"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🏎️ Driver Comparison Group")

driver_list = []
with st.sidebar.spinner("⏳ Syncing entry list from cache/API..."):
    try:
        # Load lightweight metadata to populate the dropdown menu dynamically
        meta_session = fastf1.get_session(year, gp_name, session_type)
        meta_session.load(laps=True, telemetry=False, weather=False)
        clean_laps = meta_session.laps.dropna(subset=['Driver'])
        available_drivers = sorted(list(clean_laps['Driver'].unique()))
        
        driver_list = st.sidebar.multiselect(
            "Select Drivers to Compare", 
            options=available_drivers, 
            default=available_drivers[:2] if len(available_drivers) >= 2 else None
        )
    except Exception:
        st.sidebar.caption("⚠️ Live lookup offline. Enter driver codes manually:")
        drivers_input = st.sidebar.text_input("Enter Driver Codes (Comma Separated)", value="VER, HAM")
        driver_list = [d.strip().upper() for d in drivers_input.split(",") if d.strip()]

analyze_btn = st.sidebar.button("⚡ Run Multi-Analysis", use_container_width=True)

# ==============================================================================
# 📊 MAIN CONTENT DATA VISUALIZATION ENGINE
# ==============================================================================
st.title("🏎️ Formula 1 Multi-Driver Performance Dashboard")
st.markdown("Analyze telemetry logs synchronized meter-by-meter along the physical circuit perimeter.")

if analyze_btn:
    if not driver_list or len(driver_list) < 2:
        st.error("❌ Please select or input at least two driver codes to generate a comparative analysis.")
        st.stop()

    fastest_laps = {}
    telemetry_data = {}
    team_colors = {}

    with st.spinner("📥 Extracting telemetry matrices from data stream..."):
        try:
            session = fastf1.get_session(year, gp_name, session_type)
            session.load()
            
            for driver in driver_list:
                try:
                    lap = session.laps.pick_driver(driver).pick_fastest()
                    if lap is not None and pd.notna(lap['LapTime']):
                        fastest_laps[driver] = lap
                        telemetry_data[driver] = lap.get_car_data().add_distance()
                        team_colors[driver] = fastf1.plotting.get_driver_color(driver, session=session)
                except Exception:
                    st.warning(f"⚠️ Telemetry log missing for driver: {driver}. Skipping.")
            
            valid_drivers = list(fastest_laps.keys())
            if len(valid_drivers) < 2:
                raise ValueError("Incomplete data profiles generated.")
                
            baseline_driver = min(valid_drivers, key=lambda d: fastest_laps[d]['LapTime'])

        except Exception as e:
            st.error("❌ Core Data Extraction Failure. The live connection is blocked by the API firewall.")
            st.info("💡 TO FIX THIS: Run this race configuration once on your local computer via VS Code, then push the generated files to GitHub to cache them permanently!")
            st.stop()

    # SECTION 1: Performance Summary Metric Cards
    st.markdown(f"### ⏱️ Lap Leaderboard (Baseline Tracking Target: **{baseline_driver}**)")
    cols = st.columns(len(valid_drivers))
    for i, driver in enumerate(sorted(valid_drivers, key=lambda d: fastest_laps[d]['LapTime'])):
        with cols[i]:
            is_baseline = "⭐ " if driver == baseline_driver else ""
            st.metric(label=f"{is_baseline}{driver}", value=str(fastest_laps[driver]['LapTime'])[:-3])

    # SECTION 2: Matplotlib Overlaid Graphs
    st.markdown("### 📊 Synchronized Telemetry Traces")
    fig, ax = plt.subplots(3, 1, figsize=(14, 11), sharex=True, gridspec_kw={'height_ratios': [1.5, 2, 1]})

    # Dynamic trace building loop with teammate styling protection
    for i, driver in enumerate(valid_drivers):
        color = team_colors[driver]
        tel = telemetry_data[driver]
        
        # 💡 TEAMMATE VISUAL PROTECTION LAYER: 
        # If comparing teammates, use a solid line for the first driver and a dashed line for subsequent ones!
        if i > 0 and team_colors[driver] == team_colors[valid_drivers[0]]:
            line_style = '--'   # Dashed line for teammate
            display_label = f"{driver} (Teammate Track)"
        else:
            line_style = '-'    # Solid line for primary driver
            display_label = driver

        # 1. Speed Profile Panel (Applies the new line_style)
        ax[1].plot(tel['Distance'], tel['Speed'], label=display_label, color=color, linestyle=line_style, linewidth=1.8, alpha=0.9)
        
        # 2. Throttle Application Panel
        ax[2].plot(tel['Distance'], tel['Throttle'], color=color, linestyle=line_style, linewidth=1.2, alpha=0.7)
        
        # 3. Time Delta Vector Panel (Relative to baseline)
        if driver != baseline_driver:
            try:
                delta_time, ref_tel, _ = fastf1.utils.delta_time(fastest_laps[baseline_driver], fastest_laps[driver])
                ax[0].plot(ref_tel['Distance'], delta_time, label=f"{driver} vs {baseline_driver}", color=color, linestyle=line_style, linewidth=1.5)
            except Exception:
                pass

    ax[0].axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax[0].set_ylabel('Delta Time (Seconds)\n[ Climbing = Losing Time ]')
    ax[0].legend(loc='upper left')
    ax[0].set_title(f"{session.event['EventName']} ({year}) - {session.name} Session Overlays", fontsize=12)

    ax[1].set_ylabel('Velocity (km/h)')
    ax[1].legend(loc='lower left')
    ax[1].grid(True, linestyle=':', alpha=0.3)

    ax[2].set_ylabel('Throttle %')
    ax[2].set_xlabel('Physical Distance Along Track (Meters)')
    ax[2].grid(True, linestyle=':', alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)
    
else:
    st.info("👈 Set your race inputs in the sidebar. Click 'Run Multi-Analysis' to compile telemetry charts dynamically.")
