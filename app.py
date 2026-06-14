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
        # Force full synchronous loading of both laps and channels before returning object
        session.load(laps=True, telemetry=True, weather=False)
        return session
    except Exception as e:
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
# SIDEBAR CONTROL WORKSPACE (FORM PROTECTED)
# ==============================================================================
with st.sidebar:
    # Encapsulate all configurations inside a form block to handle browser states cleanly
    with st.form(key="pipeline_configuration_form"):
        st.header("⚙️ Configuration Panel")
        selected_year = st.selectbox("Season Year", options=[2026, 2025, 2024], index=0)
        
        available_circuits = fetch_season_circuits(selected_year)
        selected_circuit = st.selectbox("Location / Circuit", options=available_circuits)
        
        selected_session = st.selectbox("Session Type", options=["Qualifying", "Race", "Practice 1", "Practice 2", "Practice 3"])

        st.markdown("---")
        st.subheader("Drivers Matrix Alignments")
        
        # Hardcoded clean fallback names for the initial form setup pass to guarantee stability
        driver_options = [
            "Max Verstappen (VER)", "Lando Norris (NOR)", "Charles Leclerc (LEC)", 
            "Lewis Hamilton (HAM)", "Oscar Piastri (PIA)", "George Russell (RUS)",
            "Carlos Sainz (SAI)", "Fernando Alonso (ALO)", "Alexander Albon (ALB)"
        ]
        
        d1_label = st.selectbox("Primary Driver (Baseline)", options=driver_options, index=0)
        d2_label = st.selectbox("Comparison Driver", options=driver_options, index=1)
        
        d3_options = ["None / Disabled"] + driver_options
        d3_label = st.selectbox("Optional Comparison Driver 3", options=d3_options, index=0)

        st.markdown("---")
        enable_audio = st.toggle("Enable Workspace Ambiance (V8 Sound)", value=False)
        
        # Form Submission Point
        submit_button = st.form_submit_button(label="⚡ Run Telemetry Analysis", type="primary")

    if enable_audio:
        st.components.v1.html(
            """
            <audio autoplay loop style="display:none;">
                <source src="https://www.soundjay.com/transportation/sounds/race-car-driving-1.mp3" type="audio/mpeg">
            </audio>
            """, height=0, width=0
        )

# Map human-readable labels to their standard 3-letter timing abbreviations
driver_mapping = {label: label.split("(")[-1].replace(")", "") for label in driver_options}
driver1 = driver_mapping.get(d1_label, "VER")
driver2 = driver_mapping.get(d2_label, "NOR")
driver3 = driver_mapping.get(d3_label, None) if d3_label != "None / Disabled" else None

# ==============================================================================
# RUNTIME DATA PROCESSING & VISUALIZATION LOOP
# ==============================================================================
if submit_button:
    with st.spinner("Synchronizing tracking telemetry arrays... Please wait."):
        session_data = load_telemetry_secure(selected_year, selected_circuit, selected_session)
        
        if session_data is None:
            st.markdown("### STATUS: ONLINE")
            st.markdown("## 🏁")
            st.error("### Operational Boundary Detected")
            st.warning("The telemetry stream logs for this session are missing or completely uncompiled on the server database. Please switch the Year dropdown selection to 2024 or choose another Grand Prix location.")
        else:
            try:
                # Isolate specific telemetry vectors
                laps_d1 = session_data.laps.pick_driver(driver1)
                laps_d2 = session_data.laps.pick_driver(driver2)
                
                fastest_d1 = laps_d1.pick_fastest()
                fastest_d2 = laps_d2.pick_fastest()
                
                telemetry_d1 = fastest_d1.get_telemetry().add_distance()
                telemetry_d2 = fastest_d2.get_telemetry().add_distance()
                
                # Establish uniform 10-meter absolute spacing grid bounds
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
                
                # Derive relative delta performance progression map
                delta_time = np.zeros(len(target_grid))
                for i in range(1, len(target_grid)):
                    v1 = max(grid_d1['Speed'].iloc[i] / 3.6, 1.0)
                    v2 = max(grid_d2['Speed'].iloc[i] / 3.6, 1.0)
                    delta_time[i] = delta_time[i-1] + ((10.0 / v1) - (10.0 / v2))
                
                # Construct Plotly Visualization Canvas
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
                
                st.markdown("---")
                st.markdown("### Structural Analysis Guide")
                st.write("The secondary chart tracks the absolute performance margins down to the meter. An ascending delta trace demonstrates that the baseline driver is opening a performance gap, while a descending trend indicates the Comparison Driver is gaining time.")

            except Exception as e:
                st.markdown("### STATUS: ONLINE")
                st.markdown("## 🏁")
                st.error("### Operational Boundary Detected")
                st.write(f"Data mapping error: {str(e)}")
else:
    # Standard baseline landing interface when app finishes cold booting
    st.markdown("### STATUS: ONLINE")
    st.markdown("## 🏁")
    st.info("💡 **Welcome to the Telemetry Engine Workspace.** Adjust your tracking options in the sidebar configuration container and click **Run Telemetry Analysis** to construct live time-series interpolation curves.")
