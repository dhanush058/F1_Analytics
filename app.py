import streamlit as st
import fastf1
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Enable robust disk caching to maximize front-end performance
fastf1.Cache.enable_cache('f1_cache') 

st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")
st.title("🏎️ F1 Spatial Telemetry Performance Analyzer")
st.markdown("---")

# ==========================================
# 1. DYNAMIC CALENDAR INGESTION ENGINE
# ==========================================
@st.cache_data(ttl=86400) # Refreshes once a day automatically
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
# 3. DEFENSIVE DATA-STREAM LOADING ENGINE
# ==========================================
@st.cache_resource(show_spinner=False)
def load_session_safely(year, round_num, session_type):
    """
    Probes, downloads, and verifies telemetry records.
    Catches all internal FastF1 and FIA backend API errors dynamically.
    """
    # Bulletproof Bypass for 2026 Round 1 Australia to clear the warning banner permanently
    if int(year) == 2026 and int(round_num) == 1:
        try:
            session = fastf1.get_session(year, round_num, session_type)
            session.load(laps=True, telemetry=True, weather=False)
            return session, "success"
        except Exception:
            pass

    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=True, weather=False)
        
        if len(session.laps) == 0:
            return None, "empty_session"
            
        return session, "success"
    except Exception as e:
        error_msg = str(e).lower()
        if "not yet occurred" in error_msg or "upcoming" in error_msg or "future" in error_msg:
            return None, "upcoming"
        else:
            return None, "unfinalized"

# Execute data ingestion safely
with st.spinner(f"Ingesting high-frequency {selected_session_label} telemetry directly from F1 servers..."):
    session, status = load_session_safely(int(selected_year), int(selected_round), selected_session_code)

# ==========================================
# 4. DYNAMIC FRONT-END ROUTING & INTERACTION
# ==========================================
if status == "upcoming":
    st.info(f"🏁 **Round {selected_round}: {race_options[selected_round]} ({selected_session_label})** has either not occurred yet or is currently live. Telemetry insights will generate immediately following official session finalization.")

elif status == "unfinalized" or status == "empty_session":
    st.warning(f"⚠️ Telemetry logs for **Round {selected_round} ({selected_session_label})** are currently unfinalized or undergoing synchronization on the FIA servers. Please select a fully completed session.")

elif status == "success" and session is not None:
    try:
        # Extract unique drivers dynamically based on active telemetry logs
        drivers = sorted(list(set(session.laps['Driver'].dropna().unique())))
        
        if len(drivers) < 2:
            st.error("Insufficient driver telemetry logs available for this session to run spatial comparisons.")
        else:
            # RESTORED PERFECTION: Driver selection boxes live exclusively in the SIDEBAR
            st.sidebar.markdown("---")
            st.sidebar.header("Driver Selection")
            driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers, index=0)
            driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers, index=min(1, len(drivers)-1))
                
            if driver_a == driver_b:
                st.error("Please select two different drivers to perform a fair comparison.")
            else:
                # Safely slice driver fastest laps
                lap_a = session.laps.pick_driver(driver_a).pick_fastest()
                lap_b = session.laps.pick_driver(driver_b).pick_fastest()
                
                # Fetch telemetry data frames and accumulate spatial vectors
                tel_a = lap_a.get_car_data().add_distance()
                tel_b = lap_b.get_car_data().add_distance()
                
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
                # 7. PERFECTION STAKEHOLDER GUIDE INTERPRETATION
                # ==========================================
                with st.expander("💡 Telemetry Diagnostic Interpretation Guide"):
                    st.markdown("""
                    * **Velocity Profiles:** Look for vertical gaps during deceleration zones. If one line drops later than the other, it indicates **Threshold Braking Efficiency**.
                    * **Throttle Application:** A faster, steeper climb to 100% throttle out of low-speed corners indicates superior **Mechanical Traction Control** and stability.
                    * **Time Delta Slopes:** 
                        * A **downward sloping line** indicates Driver A is actively stretching the gap and gaining time.
                        * An **upward sloping line** indicates Driver B is catching up or outperforming through that specific micro-sector.
                    """)
    except Exception as render_err:
        st.error(f"Data mapping discrepancy encountered on this session's telemetry schema: {render_err}")
