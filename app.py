import streamlit as st
import fastf1
import pandas as pd
import numpy as np
import plotly.graph_objects as gr
from plotly.subplots import make_subplots
import os

# ==============================================================================
# BACKEND STORAGE FIXED ROUTINES (Hidden Environment Compatibility)
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
# ORIGINAL UI HEADER LAYOUT (RESTORED)
# ==============================================================================
st.title("MULTI-DRIVER TELEMETRY PLATFORM")
st.write(f"Spatial Coordinate Resampling Pipeline")
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

    st.markdown("---")
    st.subheader("Drivers")
    driver1_input = st.text_input("Primary Driver", value="VER").upper()
    driver2_input = st.text_input("Comparison Driver", value="NOR").upper()
    driver3_input = st.text_input("Optional Comparison (Leave blank to disable)", value="").upper()

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

# ==============================================================================
# RUNTIME PERFORMANCE INTERACTION LOGIC
# ==============================================================================
session_data = load_telemetry_secure(selected_year, selected_circuit, selected_session)

if session_data is None:
    # ORIGINAL DEFENSIVE NOTICE LAYOUT (RESTORED)
    st.markdown("### STATUS: ONLINE")
    st.markdown("## 🏁")
    st.error("### Operational Boundary Detected")
    st.warning("The telemetry stream logs for this session are missing or completely uncompiled on the server database. Please switch the Year dropdown selection to 2024 or choose another Grand Prix location.")
else:
    try:
        laps_d1 = session_data.laps.pick_driver(driver1_input)
        laps_d2 = session_data.laps.pick_driver(driver2_input)
        
        fastest_d1 = laps_d1.pick_fastest()
        fastest_d2 = laps_d2.pick_fastest()
        
        telemetry_d1 = fastest_d1.get_telemetry().add_distance()
        telemetry_d2 = fastest_d2.get_telemetry().add_distance()
        
        max_distance = min(telemetry_d1['Distance'].max(), telemetry_d2['Distance'].max())
        target_grid = np.arange(0, max_distance, 10)
        
        grid_d1 = resample_telemetry_grid(telemetry_d1, target_grid)
        grid_d2 = resample_telemetry_grid(telemetry_d2, target_grid)
        
        include_d3 = False
        if driver3_input:
            try:
                laps_d3 = session_data.laps.pick_driver(driver3_input)
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
        
        # ORIGINAL BI-TIER PLOTLY INTERACTIVE ENVIRONMENT
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.08,
            row_heights=[0.6, 0.4],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]]
        )
        
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Speed'], name=f"{driver1_input} Velocity", line=dict(color="#00D2BE", width=2.5)), row=1, col=1, secondary_y=False)
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d1['Throttle'], name=f"{driver1_input} Throttle %", line=dict(color="#00D2BE", width=1.5, dash='dash'), opacity=0.3), row=1, col=1, secondary_y=True)
        
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Speed'], name=f"{driver2_input} Velocity", line=dict(color="#FF8700", width=2.5)), row=1, col=1, secondary_y=False)
        fig.add_trace(gr.Scatter(x=target_grid, y=grid_d2['Throttle'], name=f"{driver2_input} Throttle %", line=dict(color="#FF8700", width=1.5, dash='dash'), opacity=0.3), row=1, col=1, secondary_y=True)
        
        if include_d3:
            fig.add_trace(gr.Scatter(x=target_grid, y=grid_d3['Speed'], name=f"{driver3_input} Velocity", line=dict(color="#E10600", width=2.5)), row=1, col=1, secondary_y=False)
        
        fig.add_trace(gr.Scatter(x=target_grid, y=delta_time, name=f"Pacing Margin (Ref: {driver1_input})", line=dict(color="#FFFFFF", width=2)), row=2, col=1)
        
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
        
        st.markdown("---")
        st.markdown("### Structural Analysis Guide")
        st.write("The secondary chart tracks the absolute performance margins down to the meter. An ascending delta trace demonstrates that the baseline driver is opening a performance gap, while a descending trend indicates the Comparison Driver is gaining time.")

    except Exception as e:
        # Fallback to the original status look even if processing errors happen
        st.markdown("### STATUS: ONLINE")
        st.markdown("## 🏁")
        st.error("### Operational Boundary Detected")
        st.write(f"Data mapping error: {str(e)}")
