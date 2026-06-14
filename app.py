import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os

# ==============================================================================
# BACKEND COMPATIBILITY ROUTINES (Hidden Scratchpad Setup)
# ==============================================================================
st.set_page_config(
    page_title="Multi-Driver F1 Telemetry Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

tmp_cache_dir = "/tmp/fastf1_cache"
if not os.path.exists(tmp_cache_dir):
    os.makedirs(tmp_cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(tmp_cache_dir)

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
        return session
    except:
        return None

def resample_telemetry_grid(telemetry_df, target_distance):
    resampled = pd.DataFrame({'Distance': target_distance})
    resampled['Speed'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Speed'])
    resampled['Throttle'] = np.interp(target_distance, telemetry_df['Distance'], telemetry_df['Throttle'])
    return resampled

# ==============================================================================
# ORIGINAL UI HEADER LAYOUT
# ==============================================================================
st.title("MULTI-DRIVER TELEMETRY PLATFORM")
st.write("Spatial Coordinate Resampling Pipeline")
st.caption("Telemetry Diagnostics Engine")

# ==============================================================================
# SIDEBAR CONTROL WORKSPACE
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Configuration Panel")
    selected_year = st.selectbox("Season Year", options=[2026, 2025, 2024], index=0)
    
    available_circuits = fetch_season_circuits(selected_year)
    selected_circuit = st.selectbox("Location / Circuit", options=available_circuits)
    
    selected_session = st.selectbox("Session Type", options=["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"])

# ==============================================================================
# RUNTIME PERFORMANCE INTERACTION LOGIC
# ==============================================================================
session_data = load_telemetry_secure(selected_year, selected_circuit, selected_session)

if session_data is None:
    st.markdown("### STATUS: ONLINE")
    st.markdown("## 🏁")
    st.error("### Operational Boundary Detected")
    st.warning("The telemetry stream logs for this session are missing or completely uncompiled on the server database. Please switch the Year dropdown selection to 2024 or choose another Grand Prix location.")
else:
    # --- DYNAMIC ROSTER DISCOVERY PASS ---
    # Extracts the full driver name registry directly from the session results database
    try:
        results_df = session_data.results
        # Build dictionary: {"Max Verstappen (VER)": "VER", ...}
        driver_mapping = {}
        for _, row in results_df.iterrows():
            display_label = f"{row['FullName']} ({row['Abbreviation']})"
            driver_mapping[display_label] = row['Abbreviation']
        
        driver_options = sorted(list(driver_mapping.keys()))
    except:
        # Emergency fallback if results metadata dictionary is delayed
        driver_mapping = {"Max Verstappen (VER)": "VER", "Lando Norris (NOR)": "NOR", "Lewis Hamilton (HAM)": "HAM"}
        driver_options = list(driver_mapping.keys())

    # Render driver dropdowns inside the sidebar workspace using full names list
    with st.sidebar:
        st.markdown("---")
        st.subheader("Drivers Matrix Alignments")
        
        d1_label = st.selectbox("Primary Driver (Baseline)", options=driver_options, index=0 if len(driver_options) > 0 else 0)
        d2_label = st.selectbox("Comparison Driver", options=driver_options, index=1 if len(driver_options) > 1 else 0)
        
        # Insert a clean option for dropping driver 3 completely from the layout pass
        d3_options = ["None / Disabled"] + driver_options
        d3_label = st.selectbox("Optional Comparison Driver 3", options=d3_options, index=0)

        st.markdown("---")
        enable_audio = st.toggle("Enable Workspace Ambiance (V8 Sound)", value=False)
        if enable_audio:
            st.components.v1.html(
                """
                <audio autoplay loop style="display:none;">
                    <source src="https://www.soundjay.com/transportation/sounds/race-car-driving-1.mp3" type="audio/mpeg">
                </audio>
                """, height=0, width=0
            )

    # Extract target 3-letter abbreviations passing parameters down onto core engines
    driver1 = driver_mapping[d1_label]
    driver2 = driver_mapping[d2_label]
    driver3 = driver_mapping[d3_label] if d3_label != "None / Disabled" else None

    try:
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
            title_text=f"Velocity Profiles & Throttle Inputs Map — {selected_circuit} ({selected_year})",
            height=750,
            template="plotly_dark",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Absolute Coordinate Baseline (Meters)", row=2, col=1)
        fig.update_yaxes(title_text="Velocity (km/h)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Throttle Input %", maxallowed=100, minallowed=0, row=1, col=1, secondary_y=True)
        fig.update_yaxes(title_text="Delta Time Performance Gap", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # ==============================================================================
        # RESTORED ORIGINAL USER GUIDE SECTION
        # ==============================================================================
        st.markdown("---")
        st.markdown("### Structural Analysis Guide")
        st.write("The secondary chart tracks the absolute performance margins down to the meter. An ascending delta trace demonstrates that the baseline driver is opening a performance gap, while a descending trend indicates the Comparison Driver is gaining time.")

    except Exception as e:
        st.markdown("### STATUS: ONLINE")
        st.markdown("## 🏁")
        st.error("### Operational Boundary Detected")
        st.write(f"Data mapping error: {str(e)}")
