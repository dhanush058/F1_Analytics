import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# 🏎️ MASTER GLOBAL TRACK SPECIFICATION DATABASE
# =========================================================
TRACK_METRICS_DB = {
    "melbourne": {"length": 5278, "corners": 14},
    "shanghai": {"length": 5451, "corners": 16},
    "suzuka": {"length": 5807, "corners": 18},
    "sakhir": {"length": 5412, "corners": 15},
    "jeddah": {"length": 6174, "corners": 27},
    "miami": {"length": 5412, "corners": 19},
    "imola": {"length": 4909, "corners": 19},
    "monaco": {"length": 3337, "corners": 19},
    "montreal": {"length": 4361, "corners": 14},
    "barcelona": {"length": 4657, "corners": 14},
    "spielberg": {"length": 4318, "corners": 10},
    "silverstone": {"length": 5891, "corners": 18},
    "budapest": {"length": 4381, "corners": 14},
    "spa": {"length": 7004, "corners": 19},
    "zandvoort": {"length": 4259, "corners": 14},
    "monza": {"length": 5793, "corners": 11},
    "madrid": {"length": 5474, "corners": 20},
    "baku": {"length": 6003, "corners": 20},
    "marina bay": {"length": 4940, "corners": 19},
    "austin": {"length": 5513, "corners": 20},
    "mexico city": {"length": 4304, "corners": 17},
    "são paulo": {"length": 4309, "corners": 15},
    "las vegas": {"length": 6201, "corners": 17},
    "lusail": {"length": 5419, "corners": 16},
    "yas marina": {"length": 5281, "corners": 16}
}

seasonal_schedule = {
    2026: {
        "races": {
            1: "Australian Grand Prix", 2: "Chinese Grand Prix", 3: "Japanese Grand Prix",
            4: "Bahrain Grand Prix", 5: "Saudi Arabian Grand Prix", 6: "Miami Grand Prix",
            7: "Canadian Grand Prix", 8: "Monaco Grand Prix", 9: "Barcelona-Catalunya Grand Prix",
            10: "Austrian Grand Prix", 11: "British Grand Prix", 12: "Belgian Grand Prix",
            13: "Hungarian Grand Prix", 14: "Dutch Grand Prix", 15: "Italian Grand Prix",
            16: "Spanish Grand Prix (Madrid)", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Melbourne", 2: "Shanghai", 3: "Suzuka", 4: "Sakhir", 5: "Jeddah", 6: "Miami",
            7: "Montreal", 8: "Monaco", 9: "Barcelona", 10: "Spielberg", 11: "Silverstone", 12: "Spa",
            13: "Budapest", 14: "Zandvoort", 15: "Monza", 16: "Madrid", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        }
    },
    2025: {
        "races": {
            1: "Australian Grand Prix", 2: "Chinese Grand Prix", 3: "Japanese Grand Prix",
            4: "Bahrain Grand Prix", 5: "Saudi Arabian Grand Prix", 6: "Miami Grand Prix",
            7: "Emilia Romagna Grand Prix", 8: "Monaco Grand Prix", 9: "Spanish Grand Prix",
            10: "Canadian Grand Prix", 11: "Austrian Grand Prix", 12: "British Grand Prix",
            13: "Belgian Grand Prix", 14: "Hungarian Grand Prix", 15: "Dutch Grand Prix",
            16: "Italian Grand Prix", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Melbourne", 2: "Shanghai", 3: "Suzuka", 4: "Sakhir", 5: "Jeddah", 6: "Miami",
            7: "Imola", 8: "Monaco", 9: "Barcelona", 10: "Montreal", 11: "Spielberg", 12: "Silverstone",
            13: "Spa", 14: "Budapest", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        }
    },
    2024: {
        "races": {
            1: "Bahrain Grand Prix", 2: "Saudi Arabian Grand Prix", 3: "Australian Grand Prix",
            4: "Japanese Grand Prix", 5: "Chinese Grand Prix", 6: "Miami Grand Prix",
            7: "Emilia Romagna Grand Prix", 8: "Monaco Grand Prix", 9: "Canadian Grand Prix",
            10: "Spanish Grand Prix", 11: "Austrian Grand Prix", 12: "British Grand Prix",
            13: "Hungarian Grand Prix", 14: "Belgian Grand Prix", 15: "Dutch Grand Prix",
            16: "Italian Grand Prix", 17: "Azerbaijan Grand Prix", 18: "Singapore Grand Prix",
            19: "United States Grand Prix", 20: "Mexico City Grand Prix", 21: "São Paulo Grand Prix",
            22: "Las Vegas Grand Prix", 23: "Qatar Grand Prix", 24: "Abu Dhabi Grand Prix"
        },
        "locations": {
            1: "Sakhir", 2: "Jeddah", 3: "Melbourne", 4: "Suzuka", 5: "Shanghai", 6: "Miami",
            7: "Imola", 8: "Monaco", 9: "Montreal", 10: "Barcelona", 11: "Spielberg", 12: "Silverstone",
            13: "Budapest", 14: "Spa", 15: "Zandvoort", 16: "Monza", 17: "Baku", 18: "Marina Bay",
            19: "Austin", 20: "Mexico City", 21: "São Paulo", 22: "Las Vegas", 23: "Lusail", 24: "Yas Marina"
        }
    }
}

# =========================================================
# ⚙️ HIGH SPEED CACHE INFRASTRUCTURE
# =========================================================
@st.cache_data(ttl=5, show_spinner=False)
def fetch_api_json(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# =========================================================
# 🏎️ VIEWPORT RENDER INITIALIZATION
# =========================================================
st.sidebar.markdown("### 🛠️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle(
    "🖥️ Enable Simulated Demo Mode", 
    value=False, 
    help="Force simulated data validation frames to test multi-axis layouts immediately."
)

selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=0)

active_config = seasonal_schedule[int(selected_year)]
race_options = active_config["races"]
location_map = active_config["locations"]

selected_round = st.sidebar.selectbox(
    "Select Grand Prix Track", 
    list(race_options.keys()), 
    format_func=lambda x: f"Round {x}: {race_options[x]}"
)

selected_session_label = st.sidebar.selectbox("Select Session Type", ["Race", "Qualifying", "FP1", "FP2", "FP3"], index=0)

target_location = location_map[selected_round]
event_name = race_options[selected_round]
true_circuit_length = TRACK_METRICS_DB.get(target_location.lower(), {"length": 5000})["length"]

# =========================================================
# 🌐 OPENF1 METADATA RESOLVER
# =========================================================
session_key = None
session_start_time = None
driver_map = {}
is_simulated = True

if not demo_mode:
    session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}&session_name={selected_session_label}"
    sessions = fetch_api_json(session_url)

    if sessions:
        matched_session = None
        for s in sessions:
            if target_location.lower() in str(s.get('location', '')).lower():
                matched_session = s
                break
        if not matched_session and len(sessions) > 0:
            matched_session = sessions[0]
            
        if matched_session:
            session_key = matched_session.get('session_key')
            session_start_time = matched_session.get('date_start')
            driver_url = f"https://api.openf1.org/v1/drivers?session_key={session_key}"
            drivers_data = fetch_api_json(driver_url)
            
            if drivers_data:
                for d in drivers_data:
                    acronym = d.get('name_acronym')
                    num = d.get('driver_number')
                    if acronym and num:
                        driver_map[str(acronym)] = int(num)
                if driver_map:
                    is_simulated = False

if not is_simulated and driver_map and not demo_mode:
    drivers = sorted(list(driver_map.keys()))
else:
    drivers = ["VER", "HAM", "NOR", "LEC", "RUS", "PIA", "ALO", "ALB"]

driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers, index=0)
driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers, index=1 if len(drivers) > 1 else 0)

# =========================================================
# 📊 PRECISION CALIBRATED TELEMETRY PIPELINE ENGINE
# =========================================================
def fetch_calibrated_telemetry(s_key, d_map, d_a, d_b, target_length, fallback_active):
    if fallback_active or not s_key or not d_map or d_a not in d_map or d_b not in d_map:
        return None, None, "MISSING_DATA"

    try:
        num_a = d_map[d_a]
        num_b = d_map[d_b]
        
        laps_url = f"https://api.openf1.org/v1/laps?session_key={int(s_key)}&driver_number={int(num_a)}"
        lap_data = fetch_api_json(laps_url)
        
        if not lap_data or len(lap_data) == 0:
            return None, None, "EMPTY_LAP_RECORD"
            
        df_laps = pd.DataFrame(lap_data).dropna(subset=['lap_duration'])
        if df_laps.empty:
            return None, None, "EMPTY_LAP_RECORD"
            
        fastest_lap_row = df_laps.loc[df_laps['lap_duration'].idxmin()]
        start_time_str = fastest_lap_row['date_start']
        duration = fastest_lap_row['lap_duration']
        
        start_dt = pd.to_datetime(start_time_str)
        end_dt = start_dt + pd.Timedelta(seconds=float(duration))
        time_filter = f"&date>={start_dt.strftime('%Y-%m-%dT%H:%M:%S')}&date<={end_dt.strftime('%Y-%m-%dT%H:%M:%S')}"
        
        url_a = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_a)}{time_filter}"
        res_a = requests.get(url_a, timeout=12).json()
        url_b = f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_b)}{time_filter}"
        res_b = requests.get(url_b, timeout=12).json()
        
        if not res_a or not res_b or len(res_a) < 10 or len(res_b) < 10:
            return None, None, "EMPTY_SENSOR_STREAM"
            
        df_a = pd.DataFrame(res_a).sort_values('date')
        df_b = pd.DataFrame(res_b).sort_values('date')
        
        df_a['date'] = pd.to_datetime(df_a['date'])
        df_b['date'] = pd.to_datetime(df_b['date'])
        
        # FIXED: Synchronous Timeline Slicing Layer isolates common boundaries.
        # This completely drops dead packet trailing arrays and stops the 70s delta leakage.
        last_common_date = min(df_a['date'].max(), df_b['date'].max())
        first_common_date = max(df_a['date'].min(), df_b['date'].min())
        
        df_a = df_a[(df_a['date'] >= first_common_date) & (df_a['date'] <= last_common_date)]
        df_b = df_b[(df_b['date'] >= first_common_date) & (df_b['date'] <= last_common_date)]
        
        if df_a.empty or df_b.empty:
            return None, None, "ASYNC_STREAM_GAP"
            
        df_merged = pd.merge_asof(df_a, df_b, on='date', suffixes=('_a', '_b'), direction='nearest')
        df_merged = df_merged.dropna(subset=['speed_a', 'speed_b'])
        
        time_deltas = df_merged['date'].diff().dt.total_seconds().fillna(0.24)
        time_deltas = np.where((time_deltas < 0.005) | (time_deltas > 5.0), 0.24, time_deltas)
        
        raw_dist_a = (df_merged['speed_a'].astype(float) / 3.6 * time_deltas).cumsum()
        raw_dist_b = (df_merged['speed_b'].astype(float) / 3.6 * time_deltas).cumsum()
        
        distance_grid = np.linspace(0, target_length, 350)
        
        speed_a_aligned = np.interp(distance_grid, (raw_dist_a / raw_dist_a.max()) * target_length, df_merged['speed_a'].astype(float))
        throttle_a_aligned = np.interp(distance_grid, (raw_dist_a / raw_dist_a.max()) * target_length, df_merged['throttle_a'].astype(float) if 'throttle_a' in df_merged.columns else 95.0)
        
        speed_b_aligned = np.interp(distance_grid, (raw_dist_b / raw_dist_b.max()) * target_length, df_merged['speed_b'].astype(float))
        throttle_b_aligned = np.interp(distance_grid, (raw_dist_b / raw_dist_b.max()) * target_length, df_merged['throttle_b'].astype(float) if 'throttle_b' in df_merged.columns else 92.0)
        
        time_a_aligned = np.cumsum(1 / (np.maximum(speed_a_aligned, 15) / 3.6))
        time_b_aligned = np.cumsum(1 / (np.maximum(speed_b_aligned, 15) / 3.6))
        delta_time = time_a_aligned - time_b_aligned
        
        # Validation gate drops asymmetric calculations if data drift yields an incorrect metric
        if np.abs(delta_time).max() > 18.0:
            return None, None, "CORRUPTED_STREAM_GAP"
            
        tel_a = pd.DataFrame({'Distance': distance_grid, 'Speed': speed_a_aligned, 'Throttle': throttle_a_aligned, 'Delta_Time': delta_time})
        tel_b = pd.DataFrame({'Distance': distance_grid, 'Speed': speed_b_aligned, 'Throttle': throttle_b_aligned})
        
        return tel_a, tel_b, "SUCCESS"
    except Exception as e:
        return None, None, str(e)

force_fallback = is_simulated or demo_mode

# =========================================================
# 💎 NON-DIMMING FRAGMENT CANVAS WRAPPER (ERROR FIXED)
# =========================================================
@st.fragment(run_every=10)
def execute_live_viewport_render():
    telemetry_a, telemetry_b, engine_status = fetch_calibrated_telemetry(
        session_key, driver_map, driver_a, driver_b, true_circuit_length, force_fallback
    )
    
    # DYNAMIC TRACK HARMONIZED SIMULATOR BACKUP
    if engine_status != "SUCCESS" or telemetry_a is None:
        is_simulated_active = True
        driver_ids = {"VER": 33, "HAM": 44, "NOR": 4, "LEC": 16, "RUS": 63, "PIA": 81, "ALO": 14, "ALB": 23}
        id_a, id_b = driver_ids.get(driver_a, 10), driver_ids.get(driver_b, 20)
        
        track_seed = int(selected_round) + int(selected_year)
        np.random.seed(track_seed)
        
        dist_baseline = np.linspace(0, true_circuit_length, 350)
        speed_base = 280.0
        for i in range(12):
            corner_pos = (true_circuit_length / 13) * (i + 1) + np.random.uniform(-100, 100)
            speed_base -= 95 * np.exp(-((dist_baseline - corner_pos) / 190)**2)
            
        np.random.seed(id_a + track_seed)
        speed_a = np.clip((speed_base * np.random.uniform(0.97, 1.03)) + np.random.normal(0, 1.2, 350), 60, 340)
        throttle_a = np.clip(100 - (310 - speed_a) * 1.1 + np.random.normal(0, 1.5, 350), 0, 100)
        
        np.random.seed(id_b + track_seed)
        speed_b = np.clip((np.roll(speed_base, int(np.random.uniform(-4, 4))) * np.random.uniform(0.97, 1.03)) + np.random.normal(0, 1.2, 350), 60, 340)
        throttle_b = np.clip(100 - (310 - speed_b) * 1.1 + np.random.normal(0, 1.5, 350), 0, 100)
        
        delta_time = np.cumsum(1 / (np.maximum(speed_a, 15) / 3.6)) - np.cumsum(1 / (np.maximum(speed_b, 15) / 3.6))
        
        telemetry_a = pd.DataFrame({'Distance': dist_baseline, 'Speed': speed_a, 'Throttle': throttle_a, 'Delta_Time': delta_time * 1.5})
        telemetry_b = pd.DataFrame({'Distance': dist_baseline, 'Speed': speed_b, 'Throttle': throttle_b})
        lineage_integrity = "100% Emulated Core"
    else:
        is_simulated_active = False
        lineage_integrity = "100% Authentic API"

    # FIXED: Placed status block elements inside the fragment container function block to prevent layout exceptions
    if is_simulated_active:
        st.info("🖥️ **Dashboard Framework Mode:** Sandbox Simulator Interface Active")
    else:
        st.success("✅ **Dashboard Framework Mode:** Live Ingestion Stream Fully Operational")

    # KPI Summary Cards Formulation
    total_dist = f"{int(telemetry_a['Distance'].max()):,} m"
    max_v_a = telemetry_a['Speed'].max()
    max_v_b = telemetry_b['Speed'].max()

    peak_velocity = f"{max_v_a:.1f} km/h ({driver_a})" if max_v_a > max_v_b else f"{max_v_b:.1f} km/h ({driver_b})"
    max_delta = f"{telemetry_a['Delta_Time'].abs().max():.3f} s"
    r_corr = telemetry_a['Throttle'].corr(telemetry_b['Throttle'])
    throttle_corr = f"{r_corr:.2f}" if not np.isnan(r_corr) else "1.00"
    
    st.markdown("### 📋 Executive Summary Insights Panel")
    sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)
    with sum_col1:
        st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🏁 CIRCUIT FOOTPRINT</strong><br><span style="font-size:16px; font-weight:bold;">{total_dist}</span><br><span style="color:#8892B0; font-size:11px;">Track: {event_name}</span></div>', unsafe_allow_html=True)
    with sum_col2:
        st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🏎️ MATCHUP CORRELATION</strong><br><span style="font-size:16px; font-weight:bold;">{throttle_corr} r-Score</span><br><span style="color:#8892B0; font-size:11px;">Style: {driver_a} vs. {driver_b}</span></div>', unsafe_allow_html=True)
    with sum_col3:
        st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">⚡ TOP SPEED VMAX</strong><br><span style="font-size:16px; font-weight:bold;">{peak_velocity}</span><br><span style="color:#8892B0; font-size:11px;">Peak Envelope Velocity</span></div>', unsafe_allow_html=True)
    with sum_col4:
        st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">⏱️ MAX PERFORMANCE GAP</strong><br><span style="font-size:16px; font-weight:bold;">{max_delta}</span><br><span style="color:#8892B0; font-size:11px;">Maximum Spatial Deficit</span></div>', unsafe_allow_html=True)
    with sum_col5:
        st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🛡️ LINEAGE INTEGRITY</strong><br><span style="font-size:16px; font-weight:bold;">{lineage_integrity}</span><br><span style="color:#8892B0; font-size:11px;">Data Stream Governance</span></div>', unsafe_allow_html=True)

    # RESTORED: Alert banner prompts portfolio reviewers seamlessly if open API packet sizes drop
    if is_simulated_active and not demo_mode:
        st.warning(f"📋 **Data Gapping Notification Indicator ({engine_status}):** The open REST endpoints returned incomplete tracking packages for {selected_year} {event_name}.")
        st.info("💡 **Recruiter Portfolio Evaluation Tip:** To review flawless aligned multi-axis graphics instantly without packet drops, toggle **'Enable Simulated Demo Mode'** inside the left control panel.")

    st.markdown("---")

    # Render High-Density Subplots
    label_suffix = f" ({selected_session_label})"
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
                        subplot_titles=(f"Velocity Profile (Speed Trace){label_suffix}", f"Throttle Input Matrix{label_suffix}", f"Pacing Performance Gap Delta (Relative to {driver_a}){label_suffix}"))
    
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Speed'], name=f"{driver_a} Speed", line=dict(color='#00FFFF', width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Speed'], name=f"{driver_b} Speed", line=dict(color='#FF00FF', width=3)), row=1, col=1)
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Throttle'], name=f"{driver_a} Throttle", line=dict(color='#00FFFF', width=1.5, dash='longdash')), row=2, col=1)
    fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Throttle'], name=f"{driver_b} Throttle", line=dict(color='#FF00FF', width=1.5, dash='longdash')), row=2, col=1)
    fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Delta_Time'], name="Time Delta Gap", line=dict(color='#00FF66', width=2.5)), row=3, col=1)
    
    fig.update_layout(height=850, template="plotly_dark", plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', xaxis3_title="Distance Traveled (Meters)", yaxis_title="Velocity (km/h)", yaxis2_title="Throttle %", yaxis3_title="Delta (Seconds)")
    fig.update_xaxes(gridcolor='#222933', zerolinecolor='#444d56')
    fig.update_yaxes(gridcolor='#222933', zerolinecolor='#444d56')
    st.plotly_chart(fig, use_container_width=True)

# Run localized viewport canvas
execute_live_viewport_render()

# =========================================================
# 📘 COMPREHENSIVE TYPOGRAPHIC FIELD MANUAL GUIDE
# =========================================================
st.markdown("---")
st.markdown("## 📊 Telemetry Engineering Field Manual")

col_left, col_right = st.columns(2)
with col_left:
    st.success("### 📈 Tactical Racing Analysis (How to Read the Plots)")
    st.markdown(f"""
    This matrix aligns time-series variables over absolute spatial distance to track driving habits and vehicle margins between **{driver_a}** and **{driver_b}**.
    
    * **Velocity Profile Chart:** Look at the straightaways; parallel lines show clean aerodynamic efficiency and engine limits. Diverging slopes entering corners uncover variances in braking threshold aggression.
    * **Throttle Input Matrix:** Look for stepped steps to spot aerodynamic stabilization or fuel management. Sharp vertical rises profile excellent exit traction control on the apex lines.
    * **Performance Gap Delta Line:** Tracks relative time differences down to the individual meter. An ascending green trend means pulls away; a descending trend means reclaiming the pacing deficit.
    """)

with col_right:
    st.info("### 🏗️ Data Pipeline Architecture (Technical Overview)")
    st.markdown("""
    This framework implements a decoupled transformation process to eliminate client connectivity overhead and enforce data security.
    
    * **Matchup Correlation ($r$-Score):** Values near $1.00$ indicate identical driving lines; lower scores show different corner approaches or lift-and-coast techniques.
    * **Lineage Integrity Loop:** Free public REST APIs enforce tight request thresholds. If traffic blocks, a defensive loop catches errors, drops blank charts, and flags a notice to run the offline simulation safely.
    * **Spatial Normalization Engine:** Vehicle metrics log against raw timestamps. To construct a standardized spatial map, the pipeline converts velocity arrays and applies sequential rolling Riemann integration.
    """)
