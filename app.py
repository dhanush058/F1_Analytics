import streamlit as st
import fastf1
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Force explicit directory initialization to bypass hosting permissions
os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache') 

st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")
st.title("🏎️ F1 Spatial Telemetry Performance Analyzer")

# ==========================================
# CACHE PURGE BUTTON (THE RESET SWITCH)
# ==========================================
if st.button("🔄 Clear System Cache & Force API Reload"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.success("System memory purged! Recalculating with a fresh live server request...")

st.markdown("---")

# ==========================================
# 1. DYNAMIC CALENDAR INGESTION ENGINE
# ==========================================
@st.cache_data(ttl=86400)
def fetch_bulletproof_schedule(year):
    """
    Dynamically pulls the official schedule from FastF1 servers to
    ensure calendar updates never require manual code edits.
    """
    try:
        schedule = fastf1.get_event_schedule(year)
        official_races = schedule[schedule['RoundNumber'] > 0]
        
        race_map = {}
        for _, row in official_races.iterrows():
            race_map[int(row['RoundNumber'])] = f"{row['EventName']} ({row['Location']})"
        return race_map
    except Exception:
        return {
            1: "Australia (Melbourne)", 2: "China (Shanghai)", 3: "Japan (Suzuka)",
            4: "Bahrain (Sakhir)", 5: "Saudi Arabia (Jeddah)", 6: "Miami (Miami)",
            7: "Emilia Romagna (Imola)", 8: "Monaco (Monaco)", 9: "Spain (Barcelona)",
            10: "Canada (Montreal)", 11: "Austria (Spielberg)", 12: "Great Britain (Silverstone)"
        }

# ==========================================
# 2. SIDEBAR NAVIGATION & CONFIGURATION
# ==========================================
st.sidebar.header("Race Selection Configuration")

selected_year = st.sidebar.selectbox("Select Season Year", [2026, 2025, 2024])

# Dynamically pull the correct calendar options
race_options = fetch_bulletproof_schedule(selected_year)

selected_round = st.sidebar.selectbox(
    "Select Grand Prix Round", 
    options=list(race_options.keys()), 
    format_func=lambda x: f"Round {x}: {race_options[x]}"
)

# All F1 session variants mapped perfectly to API hooks
session_mapping = {
    "Race": "R",
    "Qualifying": "Q",
    "Sprint": "S",
    "Sprint Qualifying": "SQ",
    "FP3": "FP3",
    "FP2": "FP2",
    "FP1": "FP1"
}
selected_session_label = st.sidebar.selectbox("Select Session Type", list(session_mapping.keys()))
selected_session_code = session_mapping[selected_session_label]

# ==========================================
# 3. DIAGNOSTIC DATA-STREAM LOADING ENGINE
# ==========================================
@st.cache_resource(show_spinner=False)
def load_session_safely(year, round_num, session_type, race_options_dict):
    """
    Probes, downloads, and verifies telemetry records.
    Exposes the raw exception string to identify global system blocks.
    """
    try:
        full_string = race_options_dict.get(int(round_num), "")
        event_keyword = full_string.split(" (")[0].strip() if " (" in full_string else full_string
    except Exception:
        event_keyword = ""

    last_error_observed = "Unknown connection anomaly."

    if event_keyword:
        try:
            session = fastf1.get_session(int(year), event_keyword, session_type)
            session.load(laps=True, telemetry=True, weather=False)
            if len(session.laps) > 0:
                return session, "success"
        except Exception as e:
            last_error_observed = str(e)

    try:
        session = fastf1.get_session(int(year), int(round_num), session_type)
        session.load(laps=True, telemetry=True, weather=False)
        
        if len(session.laps) == 0:
            return None, "empty_session"
            
        return session, "success"
    except Exception as e:
        error_msg = str(e).lower()
        if "not yet occurred" in error_msg or "upcoming" in error_msg or "future" in error_msg:
            return None, "upcoming"
        else:
            return None, f"SYSTEM_ERROR: {str(e)} | Keyword Error: {last_error_observed}"

# Execute data ingestion safely with updated string-mapping arguments
with st.spinner(f"Ingesting high-frequency {selected_session_label} telemetry directly from F1 servers..."):
    session, status = load_session_safely(selected_year, selected_round, selected_session_code, race_options)

# ==========================================
# 4. DYNAMIC FRONT-END ROUTING & INTERACTION
# ==========================================
if status == "upcoming":
    st.info(f"🏁 **Round {selected_round}: {race_options[selected_round]} ({selected_session_label})** has either not occurred yet or is currently live. Telemetry insights will generate immediately following official session finalization.")

elif status == "unfinalized" or status == "empty_session" or "SYSTEM_ERROR" in str(status):
    st.warning(f"⚠️ Telemetry logs for **Round {selected_round} ({selected_session_label})** could not be loaded.")
    st.code(f"Raw Diagnostic Output: {status}", language="text")
    st.info("💡 Copy the raw diagnostic text above so we can identify exactly what is blocking your local environment setup.")

elif status == "success" and session is not None:
    try:
        # PROTECTED: Extract unique drivers safely inside a validation check
        try:
            drivers = sorted(list(set(session.laps['Driver'].dropna().unique())))
        except Exception:
            st.warning(f"⚠️ Telemetry logs for **Round {selected_round} ({selected_session_label})** are currently unfinalized or undergoing synchronization on the FIA servers. Please select a fully completed session.")
            st.stop()
        
        if len(drivers) < 2:
            st.error("Insufficient driver telemetry logs available for this session to run spatial comparisons.")
        else:
            # Driver selection boxes live exclusively in the SIDEBAR
            st.sidebar.markdown("---")
            st.sidebar.header("Driver Selection")
            driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers, index=0)
            driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers, index=min(1, len(drivers)-1))
                
            if driver_a == driver_b:
                st.error("Please select two different drivers to perform a fair comparison.")
            else:
                # ==========================================
                # DEFENSIVE SENSOR VALIDATION OVERRIDE
                # ==========================================
                try:
                    # Safely slice driver fastest laps
                    lap_a = session.laps.pick_driver(driver_a).pick_fastest()
                    lap_b = session.laps.pick_driver(driver_b).pick_fastest()
                    
                    # Fetch telemetry data frames and accumulate spatial vectors
                    tel_a = lap_a.get_car_data().add_distance()
                    tel_b = lap_b.get_car_data().add_distance()
                    
                    if len(tel_a) == 0 or len(tel_b) == 0:
                        raise ValueError("Telemetry data streams are currently empty.")
                        
                except Exception as telemetry_load_error:
                    st.warning(f"⚠️ High-frequency sensor arrays for {driver_a} or {driver_b} are currently unfinalized or missing for this specific session type. Try switching session types (e.g., from Practice to Race/Qualifying).")
                    st.stop()
                
                # ==========================================
                # 5. SPATIAL GRID NORMALIZATION (THE CORE MATH)
                # ==========================================
                max_distance = min(tel_a['Distance'].max(), tel_b['Distance'].max())
                
                # Construct perfectly uniform 10-meter spatial coordinates
                uniform_grid = np.arange(0, max_distance, 10)
                
                # Execute 1D Linear Interpolation to bypass time-asynchronous sensor drift
                speed_a_norm = np.interp(uniform_grid, tel_a['Distance'], tel_a['Speed'])
                speed_b_norm = np.interp(uniform_grid, tel_b['Distance'], tel_b['Speed'])
                
                throttle_a_norm = np.interp(uniform_grid, tel_a['Distance'], tel_a['Throttle'])
                throttle_b_norm = np.interp(uniform_grid, tel_b['Distance'], tel_b['Throttle'])
                
                time_a_norm = np.interp(uniform_grid, tel_a['Distance'], tel_a['Time'].dt.total_seconds())
                time_b_norm = np.interp(uniform_grid, tel_b['Distance'], tel_b['Time'].dt.total_seconds())
                
                # Accumulate the true, localized Pacing Time Delta relative to Driver B
                time_delta = time_a_norm - time_b_norm

                # Calculate dynamic summary metrics from normalization calculations
                final_lap_time_diff = time_a_norm[-1] - time_b_norm[-1]
                max_speed_a = int(np.max(speed_a_norm))
                max_speed_b = int(np.max(speed_b_norm))
                avg_throttle_a = int(np.mean(throttle_a_norm))
                avg_throttle_b = int(np.mean(throttle_b_norm))
                
                st.subheader(f"📊 Session Summary Profile: {race_options[selected_round]} ({selected_year})")
                
                sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
                with sum_col1:
                    st.metric(
                        label="Lap Time Variant Baseline",
                        value=f"{driver_a} vs {driver_b}",
                        delta=f"{final_lap_time_diff:+.3f}s",
                        delta_color="inverse"
                    )
                with sum_col2:
                    st.metric(
                        label=f"{driver_a} V-Max (Top Speed)",
                        value=f"{max_speed_a} km/h",
                        delta=f"{max_speed_a - max_speed_b:+} km/h vs {driver_b}"
                    )
                with sum_col3:
                    st.metric(
                        label=f"{driver_b} V-Max (Top Speed)",
                        value=f"{max_speed_b} km/h",
                        delta=f"{max_speed_b - max_speed_a:+} km/h vs {driver_a}"
                    )
                with sum_col4:
                    st.metric(
                        label="Mean Throttle Duty Cycle",
                        value=f"{avg_throttle_a}% / {avg_throttle_b}%",
                        delta=f"{avg_throttle_a - avg_throttle_b:+} % Gap"
                    )
                st.markdown("---")
                
                # ==========================================
                # 6. DIAGNOSTIC UI CHART CONFIGURATION
                # ==========================================
                fig = make_subplots(
                    rows=3, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.05,
                    subplot_titles=(
                        f"Velocity Comparison Profile (km/h)", 
                        "Throttle Application Variance (%)", 
                        f"Cumulative Time Delta (Seconds) - Negative means {driver_a} is faster"
                    )
                )
                
                # Subplot 1: Speed Profiles
                fig.add_trace(go.Scatter(x=uniform_grid, y=speed_a_norm, name=f"{driver_a} Speed", line=dict(color='#1f77b4', width=2)), row=1, col=1)
                fig.add_trace(go.Scatter(x=uniform_grid, y=speed_b_norm, name=f"{driver_b} Speed", line=dict(color='#ff7f0e', width=2, dash='dash')), row=1, col=1)
                
                # Subplot 2: Throttle Inputs
                fig.add_trace(go.Scatter(x=uniform_grid, y=throttle_a_norm, name=f"{driver_a} Throttle", line=dict(color='#1f77b4', width=1.5), showlegend=False), row=2, col=1)
                fig.add_trace(go.Scatter(x=uniform_grid, y=throttle_b_norm, name=f"{driver_b} Throttle", line=dict(color='#ff7f0e', width=1.5, dash='dash'), showlegend=False), row=2, col=1)
                
                # Subplot 3: Cumulative Time Delta Outcome
                fig.add_trace(go.Scatter(x=uniform_grid, y=time_delta, name="Pacing Delta", line=dict(color='#2ca02c', width=2.5)), row=3, col=1)
                
                # Polish Layout Architecture
                fig.update_layout(height=850, title_text=f"Lap Analysis: {driver_a} vs {driver_b} ({session.event['EventName']} - {selected_session_label} {selected_year})", hovermode="x unified")
                fig.update_xaxes(title_text="Track Position (Meters)", row=3, col=1)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # ==========================================
                # 7. COMPREHENSIVE & HUMANIZED GUIDE
                # ==========================================
                with st.expander("💡 Telemetry Diagnostic Interpretation Guide"):
                    st.markdown(f"""
                    This guide breaks down exactly how to read the visual charts above—translating raw lines into actual driving performance stories while providing the engineering pipeline mechanics behind them.

                    ### 🎛️ The Core Pipeline Math (Spatial Grid Normalization)
                    * **The Technical Challenge:** Raw telemetry data streamed directly from F1 servers is **time-asynchronous** and sampled at variable frequencies (up to 100Hz). If Driver A drives faster through a sector than Driver B, their data points naturally drift out of alignment on a standard timeline. Comparing raw timelines results in an inaccurate overlay.
                    * **The Engineering Solution:** To establish a statistically fair baseline, this application implements **1D Linear Interpolation (`numpy.interp`)**. The script dynamically identifies the maximum overlapping lap distance, constructs a uniform **10-meter fixed spatial grid**, and maps the asynchronous sensor data onto this spatial framework. This allows true, apples-to-apples spatial comparisons at every physical point on the circuit.

                    ### 🏎️ 1. Velocity Profile (The Speed Chart)
                    * **Technical Metric:** 1D Interpolated Speed Array ($km/h$) mapped across localized spatial coordinates.
                    * **What to look for:** Look closely at the vertical spaces between lines right before deep corners (deceleration zones).
                    * **The Story:** If one driver's line stays high and drops down later than the other, they are maximizing **threshold braking efficiency** (braking deeper and later into the corner). If their line dips lower at the absolute bottom of the curve, they are sacrificing minimum apex roll-speed to prioritize a sharper, quicker car rotation.

                    ### ⚙️ 2. Throttle Application Variance (The Driver Inputs)
                    * **Technical Metric:** Normalized Percentage Vector ($0-100\%$) representing raw engine butterfly valve positioning.
                    * **What to look for:** Look at the steepness of the lines as they climb out of the low-speed corners back up to 100%.
                    * **The Story:** A line that shoots straight up smoothly shows superior **mechanical traction control** and driver confidence. If you see jagged steps, drop-offs, or a delayed lift off the bottom, it means the chassis is experiencing wheel-spin or rear-end instability, forcing the driver to feather the pedal to catch the car.

                    ### ⏱️ 3. Cumulative Time Delta (The Bottom Line)
                    * **Technical Metric:** Localized step-integration ($\Delta t = t_A - t_B$) accumulated across the uniform spatial grid.
                    * **What to look for:** Look at the overall slope direction of the green line across the track.
                    * **The Story:** This chart tracks who is actively winning the battle at every single meter of the lap.
                        * **Downward Slope (📉):** Means **{driver_a}** is actively expanding the gap and gaining lap time in that micro-sector.
                        * **Upward Slope (📈):** Means **{driver_b}** is outperforming the baseline and clawing time back.
                        * **Flat Line (➖):** Both drivers are executing identical pacing through that specific stretch of tarmac.
                    """)
    except Exception as render_err:
        if "StopException" in type(render_err).__name__:
            pass
        else:
            st.error(f"Unexpected operational discrepancy encountered: {render_err}")
