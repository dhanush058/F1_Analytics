import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os
import time

# ==============================================================================
# PERMANENT LIVE STORAGE ARCHITECTURE (Unrestricted Live Mode)
# ==============================================================================
st.set_page_config(
    page_title="F1 Team Telemetry Hub",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fix: Create a standard cache folder inside your app folder so permissions never fail
persistent_cache_dir = os.path.join(os.getcwd(), "f1_paddock_cache_vault")
if not os.path.exists(persistent_cache_dir):
    os.makedirs(persistent_cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(persistent_cache_dir)

@st.cache_data(ttl=86400)
def fetch_season_circuits(year):
    try:
        schedule = fastf1.get_event_schedule(int(year))
        events = schedule[schedule['EventFormat'] != 'testing']
        return sorted(events['EventName'].unique().tolist())
    except:
        return ["Bahrain Grand Prix", "Saudi Arabian Grand Prix", "Australian Grand Prix", "Spanish Grand Prix"]

def load_telemetry_secure(year, grand_prix, session_type):
    try:
        session = fastf1.get_session(int(year), grand_prix, session_type)
        session.load(laps=True, telemetry=True, weather=False)
        
        # MEMORY GUARD: Prevent race conditions by giving cloud threads time to unpack data structures cleanly
        retry_count = 0
        while (not hasattr(session, 'laps') or session.laps is None or len(session.laps) == 0) and retry_count < 5:
            time.sleep(0.5)
            retry_count += 1
            
        return session
    except:
        return None

def resample_telemetry_grid(telemetry_df, target_distance):
    resampled = pd.DataFrame({'Distance': target_distance})
    resampled['Speed'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Speed'])
    resampled['Throttle'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Throttle'])
    return resampled

# ==============================================================================
# FORMULA 1 HIGH-PERFORMANCE BRANDING THEME
# ==============================================================================
st.markdown(
    """
    <style>
    .reportview-container { background: #111217; }
    h1 { color: #FF1801 !important; font-family: 'Titillium Web', sans-serif; font-weight: 900; letter-spacing: -1px; }
    .stSelectbox label { color: #E1E1E6 !important; font-weight: bold; }
    div[data-testid="stNotification"] { border-left: 5px solid #FF1801; background-color: #1F2026; }
    </style>
    """, 
    unsafe_allow_html=True
)

st.title("官方 F1 MULTI-DRIVER TELEMETRY PLATFORM")
st.write("🛰️ **Spatial Coordinate Resampling Pipeline** | Real-Time Telemetry Analytics Layer")
st.caption("⚙️ Pit Wall Diagnostics Engine v2.6")

# ==============================================================================
# SIDEBAR CONTROL WORKSPACE
# ==============================================================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f2/Formula2_logo.svg", width=80, output_format="PNG")
    st.header("🔧 Telemetry Control Unit")
    selected_year = st.selectbox("Season Year", options=[2026, 2025, 2024], index=0)
    
    available_circuits = fetch_season_circuits(selected_year)
    selected_circuit = st.selectbox("Location / Circuit", options=available_circuits)
    
    selected_session = st.selectbox("Session Type", options=["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"])

# ==============================================================================
# RUNTIME PERFORMANCE INTERACTION LOGIC
# ==============================================================================
session_data = load_telemetry_secure(selected_year, selected_circuit, selected_session)

if session_data is None or not hasattr(session_data, 'laps') or session_data.laps is None or len(session_data.laps) == 0:
    st.markdown("### 🔴 PIT WALL TELEMETRY STATUS: OFFLINE")
    st.markdown("## 🛑")
    st.error("### Operational Boundary Detected")
    st.warning("The telemetry stream logs for this session are missing or completely uncompiled on the server database. Please switch the Year dropdown selection to 2024 or choose another Grand Prix location.")
else:
    # --- DYNAMIC ROSTER DISCOVERY PASS ---
    try:
        unique_drivers = sorted(session_data.laps['Driver'].dropna().unique().tolist())
        driver_options = [f"🏎️ {d}" for d in unique_drivers]
        driver_mapping = {f"🏎️ {d}": d for d in unique_drivers}
    except:
        driver_mapping = {"🏎️ VER": "VER", "🏎️ NOR": "NOR", "🏎️ HAM": "HAM", "🏎️ LEC": "LEC"}
        driver_options = list(driver_mapping.keys())

    with st.sidebar:
        st.markdown("---")
        st.subheader("📊 Driver Selections")
        
        ui_key = f"drivers_{selected_year}_{selected_circuit.replace(' ', '_')}"
        
        d1_label = st.selectbox("Primary Driver (Baseline)", options=driver_options, index=0, key=f"{ui_key}_d1")
        d2_label = st.selectbox("Comparison Driver 2", options=driver_options, index=1 if len(driver_options) > 1 else 0, key=f"{ui_key}_d2")
        
        d3_options = ["None / Disabled"] + driver_options
        d3_label = st.selectbox("Optional Comparison Driver 3", options=d3_options, index=0, key=f"{ui_key}_d3")

        st.markdown("---")
        enable_audio = st.toggle("🔊 Active Engine Telemetry Audio (V8)", value=False)
        if enable_audio:
            st.components.v1.html(
                """
                <audio autoplay loop style="display:none;">
                    <source src="https://www.soundjay.com/transportation/sounds/race-car-driving-1.mp3" type="audio/mpeg">
                </audio>
                """, height=0, width=0
            )

    try:
        driver1 = driver_mapping.get(d1_label, unique_drivers[0])
        driver2 = driver_mapping.get(d2_label, unique_drivers[1] if len(unique_drivers) > 1 else unique_drivers[0])
        driver3 = driver_mapping.get(d3_label, None) if d3_label != "None / Disabled" else None

        laps_d1 = session_data.laps.pick_driver(driver1)
        laps_d2 = session_data.laps.pick_driver(driver2)
        
        fastest_d1 = laps_d1.pick_fastest()
        fastest_d2 = laps_d2.pick_fastest()
        
        telemetry_d1 = fastest_d1.get_telemetry().add_distance()
        telemetry_d2 = fastest_d2.get_telemetry().add_distance()
        
        max_distance = min(telemetry_d1['Distance'].max(), telemetry_d2['Distance'].max())
        target_grid = np.arange(0, max_distance, 10)
        
        grid_d1 = resample_telemetry_grid(telemetry_d1, target_grid)
        grid_d2 = resample_telemetry_grid(telemetry_d2, target_grid)
        
        include_d3 = False
        if driver3:
            try:
                laps_d3 = session_data.laps.pick_driver(driver3)
                fastest_d3 = laps_d3.pick_fastest()
                telemetry_d3 = fastest_d3.get_telemetry().add_distance()
                grid_d3 = resample_telemetry_grid(telemetry_d3, target_grid)
                include_d3 = True
            except:
                pass
        
        delta_time = np.zeros(len(target_grid))
        for i in range(1, len(target_grid)):
            v1 = max(grid_d1['Speed'].iloc[i] / 3.6, 1.0)
            v2 = max(grid_d2['Speed'].iloc[i] / 3.6, 1.0)
            delta_time[i] = delta_time[i-1] + ((10.0 / v1) - (10.0 / v2))
        
        # ==============================================================================
        # PLOTLY INTERACTIVE BI-TIER WORKSPACE RENDER
        # ==============================================================================
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08,
            row_heights=[0.6, 0.4],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
        )
        
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Speed'], name=f"{driver1} Velocity", line=dict(color="#00D2BE", width=2.5)), row=1, col=1, secondary_y=False)
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Throttle'], name=f"{driver1} Throttle %", line=dict(color="#00D2BE", width=1.5, dash='dash'), opacity=0.3), row=1, col=1, secondary_y=True)
        
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Speed'], name=f"{driver2} Velocity", line=dict(color="#FF8700", width=2.5)), row=1, col=1, secondary_y=False)
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Throttle'], name=f"{driver2} Throttle %", line=dict(color="#FF8700", width=1.5, dash='dash'), opacity=0.3), row=1, col=1, secondary_y=True)
        
        if include_d3:
            fig.add_trace(gr.Scatter(x=target_grid, y=grid_d3['Speed'], name=f"{driver3} Velocity", line=dict(color="#E10600", width=2.5)), row=1, col=1, secondary_y=False)
        
        fig.add_trace(gr.Scatter(x=target_grid, y=delta_time, name=f"Pacing Margin (Ref: {driver1})", line=dict(color="#FFFFFF", width=2)), row=2, col=1)
        
        fig.update_layout(
            title_text=f"📊 LAP PROFILE STREAM: {selected_circuit} ({selected_year})",
            height=750,
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Absolute Track Coordinate Baseline (Meters)", row=2, col=1)
        fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Throttle Input %", maxallowed=100, minallowed=0, row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Delta Time Performance Gap", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ==============================================================================
        # SIMPLIFIED, PROFESSIONAL EXECUTIVE GUIDE SECTION
        # ==============================================================================
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📖 Quick-Start User Manual")
            st.markdown(
                """
                1. **Select Context:** Set the desired **Season Year**, **Circuit**, and **Session Type** in the left panel.
                2. **Choose Drivers:** Map driver profiles to isolate matchups. The **Primary Driver** acts as your flat statistical `0.00` baseline.
                3. **Analyze:** * Click and drag to zoom into specific corner sectors.
                   * Double-click anywhere on the canvas to reset your layout view.
                """
            )
            
        with col2:
            st.markdown("### 🛠️ Core Engineering & Mathematics Documentation")
            st.markdown(
                """
                * **1D Linear Array Interpolation (`numpy.interp`):** Standardizes asynchronous telemetry data intervals onto an absolute uniform grid measured down to every **10 meters** to allow clear data comparisons.
                * **The Pacing Margin Trace (Row 2 Chart):**
                  * **Trending Upwards (↗️):** Comparison Driver is **losing pace** relative to the baseline.
                  * **Trending Downwards (↘️):** Comparison Driver is **gaining ground** on the baseline.
                * **Throttle Curve Map:** The dashed line traces driver throttle profiles. Use this to identify who picks up throttle quicker on corner exits.
                """
            )
            
    except Exception as e:
        st.markdown("### 🔴 SYSTEM INTEGRITY WARNING")
        st.markdown("## 🛑")
        st.error("### Operational Boundary Detected")
        st.write(f"Data mapping error: {str(e)}")
