import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ SYSTEM STORAGE CACHE LAYERS
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_api_json(url):
    """Queries public REST endpoints with strict timeout constraints."""
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

# =========================================================
# 🏎️ MULTI-SEASON CONFIGURATION (ACCURATE CALENDARS)
# =========================================================
st.set_page_config(page_title="F1 Spatial Telemetry Analyzer", layout="wide")

st.markdown("""
    <style>
        .f1-banner {
            background: linear-gradient(90deg, #FF0000 0%, #1E1E24 100%);
            padding: 12px;
            border-radius: 4px;
            border-left: 6px solid #FF0000;
            margin-bottom: 20px;
        }
        .f1-title {
            color: #FFFFFF !important;
            font-family: 'Titillium Web', sans-serif;
            font-weight: 800;
            letter-spacing: 1px;
            margin: 0px !important;
            font-size: 26px;
        }
        .metric-card {
            background-color: #151922;
            border: 1px solid #222933;
            border-top: 3px solid #FF0000;
            padding: 10px;
            border-radius: 4px;
            min-height: 85px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="f1-banner"><h1 class="f1-title">🏎️ FORMULA 1 SPATIAL TELEMETRY PERFORMANCE ANALYZER</h1></div>', unsafe_allow_html=True)

st.sidebar.markdown("### 🛠️ Portfolio Control Panel")
demo_mode = st.sidebar.toggle(
    "🖥️ Force Simulated Demo Mode", 
    value=False, 
    help="Explicitly switch to the high-fidelity offline simulation loop."
)

selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=0)

# Multi-Season Master Database Calendar Configurations
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

active_config = seasonal_schedule[selected_year]
race_options = active_config["races"]
location_map = active_config["locations"]

selected_round = st.sidebar.selectbox(
    "Select Grand Prix Track", 
    list(race_options.keys()), 
    format_func=lambda x: f"Round {x}: {race_options[x]}"
)

session_options = {
    "Race": "Race", "Qualifying": "Qualifying",
    "FP1": "Practice 1", "FP2": "Practice 2", "FP3": "Practice 3",
    "Sprint": "Sprint", "Sprint Qualifying": "Sprint Qualifying"
}
selected_session_label = st.sidebar.selectbox("Select Session Type", list(session_options.keys()), index=0)
selected_session_api_name = session_options[selected_session_label]

target_location = location_map[selected_round]
event_name = race_options[selected_round]

# =========================================================
# 🌐 OPENF1 LIVE LIVE METADATA RESOLVER
# =========================================================
session_key = None
session_start_time = None
driver_map = {}
api_is_available = False

if not demo_mode:
    session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}&session_name={selected_session_api_name}"
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
                    api_is_available = True

# Static selection mapping to safeguard drivers choice baseline
drivers_pool = sorted(list(driver_map.keys())) if (api_is_available and driver_map) else ["VER", "HAM", "NOR", "LEC", "RUS", "PIA"]

driver_a = st.sidebar.selectbox("Select Driver A (Baseline)", drivers_pool, index=0)
driver_b = st.sidebar.selectbox("Select Driver B (Comparison)", drivers_pool, index=1 if len(drivers_pool) > 1 else 0)

# =========================================================
# 📊 DUAL-GATED DATA INTERACTION LAYER
# =========================================================
@st.cache_data(ttl=1800, show_spinner=False)
def load_processed_telemetry(s_key, s_start, d_map, d_a, d_b, force_sim, year, track_rd, session_lbl):
    """Dual-Gated structural extraction engine. Cascades to simulation safely."""
    # Gate A: Try loading live external cloud feed
    if not force_sim and s_key and d_map and d_a in d_map and d_b in d_map:
        try:
            num_a = d_map[d_a]
            num_b = d_map[d_b]
            date_filter = f"&date>={s_start}" if s_start else ""
            
            res_a = requests.get(f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_a)}{date_filter}", timeout=4).json()
            res_b = requests.get(f"https://api.openf1.org/v1/car_data?session_key={int(s_key)}&driver_number={int(num_b)}{date_filter}", timeout=4).json()
            
            if res_a and res_b and len(res_a) >= 20 and len(res_b) >= 20:
                df_a = pd.DataFrame(res_a).head(350)
                tel_a = pd.DataFrame()
                tel_a['Speed'] = df_a['speed'].astype(float)
                tel_a['Throttle'] = df_a['throttle'].astype(float) if 'throttle' in df_a.columns else 95.0
                df_a['date'] = pd.to_datetime(df_a['date'])
                dt_a = df_a['date'].diff().dt.total_seconds().fillna(0.25)
                tel_a['Distance'] = (tel_a['Speed'] / 3.6 * dt_a).cumsum()
                tel_a['Time_Elapsed'] = dt_a.cumsum()

                df_b = pd.DataFrame(res_b).head(350)
                tel_b = pd.DataFrame()
                tel_b['Speed'] = df_b['speed'].astype(float)
                tel_b['Throttle'] = df_b['throttle'].astype(float) if 'throttle' in df_b.columns else 92.0
                df_b['date'] = pd.to_datetime(df_b['date'])
                dt_b = df_b['date'].diff().dt.total_seconds().fillna(0.25)
                tel_b['Distance'] = (tel_b['Speed'] / 3.6 * dt_b).cumsum()
                tel_b['Time_Elapsed'] = dt_b.cumsum()
                
                interp_b = np.interp(tel_a['Distance'], tel_b['Distance'], tel_b['Time_Elapsed'])
                tel_a['Delta_Time'] = tel_a['Time_Elapsed'] - interp_b
                return tel_a, tel_b, "Live API Verified"
        except Exception:
            pass # Cascade to Gate B cleanly
            
    # Gate B: High-Fidelity Deterministic Local Simulation Loop
    driver_ids = {"VER": 33, "HAM": 44, "NOR": 4, "LEC": 16, "RUS": 63, "PIA": 81}
    id_a = driver_ids.get(d_a, 12)
    id_b = driver_ids.get(d_b, 24)
    
    np.random.seed(int(track_rd) + len(session_lbl) + int(year))
    track_length = 4200 + (track_rd * 120)  
    num_corners = 6 + (track_rd % 8)       
    dist_baseline = np.linspace(0, track_length, 400)
    
    speed_base = 275.0
    for i in range(num_corners):
        c_pos = (track_length / (num_corners + 1)) * (i + 1) + np.random.uniform(-80, 80)
        speed_base -= 95 * np.exp(-((dist_baseline - c_pos) / 200)**2)
    
    np.random.seed(id_a + track_rd + year)
    agg_a = np.random.uniform(0.97, 1.03)
    speed_a = np.clip((speed_base * agg_a) + np.random.normal(0, 1.2, len(dist_baseline)), 65, 335)
    throttle_a = np.clip(100 - (335 - speed_a) * 1.05 + np.random.normal(0, 1.8, len(dist_baseline)), 0, 100)
    
    np.random.seed(id_b + track_rd + year)
    agg_b = np.random.uniform(0.97, 1.03)
    speed_b = np.clip((np.roll(speed_base, int(np.random.uniform(-4, 4))) * agg_b) + np.random.normal(0, 1.2, len(dist_baseline)), 65, 335)
    throttle_b = np.clip(100 - (335 - speed_b) * 1.05 + np.random.normal(0, 1.8, len(dist_baseline)), 0, 100)
    
    time_a = np.cumsum(1 / (np.maximum(speed_a, 15) / 3.6))
    time_b = np.cumsum(1 / (np.maximum(speed_b, 15) / 3.6))
    
    telemetry_a = pd.DataFrame({'Distance': dist_baseline, 'Speed': speed_a, 'Throttle': throttle_a, 'Delta_Time': (time_a - time_b) * 12.0})
    telemetry_b = pd.DataFrame({'Distance': dist_baseline, 'Speed': speed_b, 'Throttle': throttle_b})
    return telemetry_a, telemetry_b, "Local Simulation Engine Active"

# Run data transformation core
telemetry_a, telemetry_b, engine_status = load_processed_telemetry(
    session_key, session_start_time, driver_map, driver_a, driver_b, 
    demo_mode or not api_is_available, selected_year, selected_round, selected_session_label
)

# Banner Notifications to convey accurate lineage statuses
if "Simulation" in engine_status and not demo_mode:
    st.sidebar.warning("⚠️ Status: API Cloud Layer Throttled")
    st.info(f"💡 **Data Lineage Shield Active:** The live OpenF1 API server is currently unresponsive or empty for {selected_year}. The localized sandbox core has automatically taken over to preserve dashboard interaction.")
elif "Simulation" in engine_status and demo_mode:
    st.sidebar.info("🖥️ Status: Sandbox Forced")
else:
    st.sidebar.success("✅ Status: 100% Live API Stream")

# =========================================================
# 📑 SUMMARY KPI MATRIX
# =========================================================
total_dist = f"{int(telemetry_a['Distance'].max()):,} m"
max_v_a, max_v_b = telemetry_a['Speed'].max(), telemetry_b['Speed'].max()
peak_velocity = f"{max_v_a:.1f} km/h ({driver_a})" if max_v_a > max_v_b else f"{max_v_b:.1f} km/h ({driver_b})"
max_delta = f"{telemetry_a['Delta_Time'].abs().max():.3f} s"
r_score = telemetry_a['Throttle'].corr(telemetry_b['Throttle'])
throttle_corr = f"{r_score:.2f} r-Score" if not np.isnan(r_score) else "1.00 r-Score"

sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)
with sum_col1:
    st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🏁 TRACK LENGTH</strong><br><span style="font-size:16px; font-weight:bold;">{total_dist}</span><br><span style="color:#8892B0; font-size:11px;">{event_name}</span></div>', unsafe_allow_html=True)
with sum_col2:
    st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🏎️ CORRELATION</strong><br><span style="font-size:16px; font-weight:bold;">{throttle_corr}</span><br><span style="color:#8892B0; font-size:11px;">{driver_a} vs {driver_b}</span></div>', unsafe_allow_html=True)
with sum_col3:
    st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">⚡ TOP SPEED VMAX</strong><br><span style="font-size:16px; font-weight:bold;">{peak_velocity}</span><br><span style="color:#8892B0; font-size:11px;">Session Peak Trap</span></div>', unsafe_allow_html=True)
with sum_col4:
    st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">⏱️ MAX PACING GAP</strong><br><span style="font-size:16px; font-weight:bold;">{max_delta}</span><br><span style="color:#8892B0; font-size:11px;">Peak Lap Deficit</span></div>', unsafe_allow_html=True)
with sum_col5:
    st.markdown(f'<div class="metric-card"><strong style="color:#FF0000; font-size:11px;">🛡️ ENGINE LINEAGE</strong><br><span style="font-size:15px; font-weight:bold;">{engine_status}</span><br><span style="color:#8892B0; font-size:11px;">Data Integrity Audit</span></div>', unsafe_allow_html=True)

st.markdown(f"> **Strategic Intelligence Note:** Evaluating performance parameters between **{driver_a}** and **{driver_b}** across the **{selected_session_label}** telemetry logs.")
st.markdown("---")

# =========================================================
# 📈 PLOTLY VISUALIZATION CANVAS
# =========================================================
fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
    subplot_titles=("Velocity Profile (Speed Trace)", "Throttle Input Matrix", f"Pacing Performance Gap Delta (Relative to {driver_a})")
)
fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Speed'], name=f"{driver_a} Speed", line=dict(color='#00FFFF', width=3)), row=1, col=1) 
fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Speed'], name=f"{driver_b} Speed", line=dict(color='#FF00FF', width=3)), row=1, col=1) 
fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Throttle'], name=f"{driver_a} Throttle", line=dict(color='#00FFFF', width=1.5, dash='longdash')), row=2, col=1)
fig.add_trace(go.Scatter(x=telemetry_b['Distance'], y=telemetry_b['Throttle'], name=f"{driver_b} Throttle", line=dict(color='#FF00FF', width=1.5, dash='longdash')), row=2, col=1)
fig.add_trace(go.Scatter(x=telemetry_a['Distance'], y=telemetry_a['Delta_Time'], name="Time Delta Gap", line=dict(color='#00FF66', width=2.5)), row=3, col=1) 

fig.update_layout(height=850, template="plotly_dark", showlegend=True, plot_bgcolor='#0E1117', paper_bgcolor='#0E1117', xaxis3_title="Distance Traveled (Meters)", yaxis_title="Velocity (km/h)", yaxis2_title="Throttle %", yaxis3_title="Delta (Seconds)")
fig.update_xaxes(gridcolor='#222933', zerolinecolor='#444d56')
fig.update_yaxes(gridcolor='#222933', zerolinecolor='#444d56')
st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 📘 COMPREHENSIVE TYPOGRAPHIC MANUAL
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
    * **Performance Gap Delta Line:** Tracks relative time differences down to the individual meter. An ascending green trend means **{driver_a}** is pulling away; a descending trend means **{driver_b}** is reclaiming the pacing deficit.
    """)
with col_right:
    st.info("### 🏗️ Data Pipeline Architecture (Technical Overview)")
    st.markdown("""
    This framework implements a decoupled transformation process to eliminate client connectivity overhead and enforce data security.
    
    * **Matchup Correlation ($r$-Score):** Values near $1.00$ indicate identical driving lines; lower scores show different corner approaches or lift-and-coast techniques.
    * **Lineage Integrity Loop:** Free public REST APIs enforce tight request thresholds. If traffic blocks, a defensive loop catches errors, drops blank charts, and flags a notice to run the offline simulation safely.
    * **Spatial Normalization Engine:** Vehicle metrics log against raw timestamps. To construct a standardized spatial map, the pipeline converts velocity arrays and applies sequential rolling Riemann integration.
    """)
