import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & THEME ---
CITY_MAP = {
    "Australian Grand Prix": "Melbourne", "Chinese Grand Prix": "Shanghai",
    "Japanese Grand Prix": "Suzuka", "Bahrain Grand Prix": "Sakhir",
    "Saudi Arabian Grand Prix": "Jeddah", "Miami Grand Prix": "Miami",
    "Canadian Grand Prix": "Montreal", "Monaco Grand Prix": "Monte-Carlo",
    "Spanish Grand Prix": "Barcelona", "Austrian Grand Prix": "Spielberg",
    "British Grand Prix": "Silverstone", "Belgian Grand Prix": "Spa-Francorchamps",
    "Hungarian Grand Prix": "Budapest", "Dutch Grand Prix": "Zandvoort",
    "Italian Grand Prix": "Monza", "Azerbaijan Grand Prix": "Baku",
    "Singapore Grand Prix": "Singapore", "United States Grand Prix": "Austin",
    "Mexican Grand Prix": "Mexico City", "Sao Paulo Grand Prix": "São Paulo",
    "Las Vegas Grand Prix": "Las Vegas", "Qatar Grand Prix": "Lusail",
    "Abu Dhabi Grand Prix": "Yas Island"
}

st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")
st.markdown("""
<style>
    .stApp { background-color: #0B0B0E; color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    [data-testid="stMetric"] { background-color: #15151C !important; border-top: 4px solid #FF1801 !important; padding: 15px; }
    [data-testid="stMetricLabel"] { color: #FF1801 !important; font-weight: 500; }
    .main-title { text-align: center; font-size: 2rem; color: #FFFFFF; margin-bottom: 10px; font-weight: 500; }
    .subtitle-text { text-align: center; font-size: 1.1rem; color: #FF1801 !important; margin-bottom: 25px; font-weight: 500; }
    h2, h3 { color: #FF1801 !important; font-weight: 500; font-size: 1.1rem; }
    .warning-box { background-color: #2A1111; border-left: 4px solid #FF1801; padding: 15px; border-radius: 4px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT DATA ENGINE ---
def check_api_health():
    try: return requests.get("https://api.openf1.org/v1/meetings?year=2024", timeout=5).status_code == 200
    except: return False

def get_openf1(endpoint, params=None):
    try:
        headers = {'User-Agent': 'F1-PitWall-Analytics/2.0'}
        res = requests.get(f"https://api.openf1.org/v1/{endpoint}", params=params, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and "detail" in data:
                return pd.DataFrame()
            return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
        return pd.DataFrame()
    except: return pd.DataFrame()

def get_telemetry(d1_n, d2_n, s_key, sim, d_id, offset=0):
    if sim:
        seed = zlib.crc32(f"{s_key}_{d1_n}_{d2_n}_{d_id}".encode())
        np.random.seed(seed + offset)
        dist = np.linspace(0, 4000.0, 1000)
        speed = 280 + 40 * np.sin(dist/400 + offset) + 20 * np.sin(dist/150)
        throttle = np.clip(50 + 50 * np.sin(dist/300 + offset), 0, 100)
        return pd.DataFrame({'distance': dist, 'speed': speed, 'throttle': throttle}), 85.0, 4000.0
    
    laps = get_openf1("laps", {"session_key": s_key, "driver_number": d1_n})
    if laps.empty or 'lap_duration' not in laps.columns: return pd.DataFrame(), 0, 0
    
    laps['lap_duration'] = pd.to_numeric(laps['lap_duration'], errors='coerce')
    laps = laps.dropna(subset=['lap_duration', 'date_start'])
    if laps.empty: return pd.DataFrame(), 0, 0
    
    laps = laps.sort_values('lap_duration')
    
    for _, f_lap in laps.iterrows():
        duration = float(f_lap['lap_duration'])
        
        try:
            start = pd.to_datetime(f_lap['date_start'])
            if start.tzinfo is not None:
                start = start.tz_convert('UTC').tz_localize(None)
        except Exception:
            continue
            
        end = start + pd.Timedelta(seconds=duration)
        tel = get_openf1(f"car_data?session_key={s_key}&driver_number={d1_n}&date>={start.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}&date<={end.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}")
        
        if not tel.empty and 'date' in tel.columns and len(tel) > 100:
            try:
                tel['date'] = pd.to_datetime(tel['date'])
                tel = tel.sort_values('date')
                tel['dt'] = tel['date'].diff().dt.total_seconds().fillna(0)
                tel['dist'] = ((tel['speed']/3.6) * tel['dt']).cumsum()
                
                if tel['dist'].max() < 2000.0:
                    continue
                    
                ref = np.linspace(0, tel['dist'].max(), 1000)
                return pd.DataFrame({
                    'distance': ref, 
                    'speed': np.interp(ref, tel['dist'], tel['speed']), 
                    'throttle': np.interp(ref, tel['dist'], tel['throttle'])
                }), duration, tel['dist'].max()
            except Exception:
                continue

    return pd.DataFrame(), 0, 0

# --- 3. UI & CONTROL ---
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=2)
api_healthy = check_api_health()
meetings = get_openf1("meetings", {"year": year})

if meetings.empty or 'meeting_name' not in meetings.columns:
    meetings = pd.DataFrame({
        'meeting_name': ['Australian Grand Prix', 'Bahrain Grand Prix', 'Saudi Arabian Grand Prix', 'Monaco Grand Prix', 'British Grand Prix'],
        'meeting_key': [1231, 1232, 1233, 1234, 1235]
    })
    api_healthy = False

st.markdown("<div class='main-title'>Formula 1 Telemetry Analysis</div>", unsafe_allow_html=True)

if not meetings.empty:
    gp_raw = st.sidebar.selectbox("GP", meetings['meeting_name'].unique())
    
    matched_meeting = meetings[meetings['meeting_name'] == gp_raw]
    meeting_key = matched_meeting['meeting_key'].iloc[0] if not matched_meeting.empty else 1231
    s_data = get_openf1("sessions", {"meeting_key": meeting_key})
    
    # ---> CUSTOM ERROR: FUTURE GP / NO SESSIONS YET (or empty date_start) <---
    is_future_gp = False
    if s_data.empty or 'session_name' not in s_data.columns:
        is_future_gp = True
    else:
        # Check if sessions have valid past start dates or are missing date info
        if 'date_start' in s_data.columns:
            try:
                s_data['date_start'] = pd.to_datetime(s_data['date_start'], errors='coerce')
                if s_data['date_start'].dropna().empty or (s_data['date_start'].dropna() > pd.Timestamp.now()).all():
                    is_future_gp = True
            except:
                pass
        else:
            is_future_gp = True

    if is_future_gp:
        st.markdown(f"""
        <div class='warning-box'>
            <b>⚠️ Grand Prix not yet happened</b><br>
            No session records or telemetry pipelines are initialized for the <b>{year} {gp_raw}</b>. 
            Please select a completed past event or enable Simulation Mode.
        </div>
        """, unsafe_allow_html=True)
        st.stop()
        
    s_name = st.sidebar.selectbox("Session", s_data['session_name'].unique())
    s_key = s_data[s_data['session_name'] == s_name]['session_key'].iloc[0]
    
    drivers = get_openf1("drivers", {"session_key": s_key})
    
    if drivers.empty or 'full_name' not in drivers.columns:
        st.sidebar.warning("⚠️ Live driver list timed out. Loaded offline roster for Simulation.")
        drivers = pd.DataFrame({
            'full_name': ['Max Verstappen', 'Lewis Hamilton', 'Charles Leclerc', 'Lando Norris', 'Oscar Piastri', 'George Russell', 'Carlos Sainz', 'Fernando Alonso'],
            'driver_number': [1, 44, 16, 4, 81, 63, 55, 14]
        })
        api_healthy = False

    if not drivers.empty:
        d1_name = st.sidebar.selectbox("Driver A", sorted(drivers['full_name'].str.title().unique()))
        d2_name = st.sidebar.selectbox("Ref Driver", sorted(drivers['full_name'].str.title().unique()), index=1)
        sim = st.sidebar.checkbox("Simulation Mode")
        
        if not api_healthy and not sim:
            st.error("⚠️ PIPELINE OFFLINE: Unable to reach OpenF1 servers. Enable 'Simulation Mode' to continue.")
            st.stop()
        
        city = CITY_MAP.get(gp_raw, "Global Circuit")
        st.markdown(f"<div class='subtitle-text'>{gp_raw.upper()}, {city.upper()}, {year}, {s_name.upper()}</div>", unsafe_allow_html=True)
        
        d1_n = drivers[drivers['full_name'].str.title() == d1_name]['driver_number'].iloc[0]
        d2_n = drivers[drivers['full_name'].str.title() == d2_name]['driver_number'].iloc[0]
        
        with st.spinner("Extracting & Normalizing Telemetry..."):
            df1, lap1, len1 = get_telemetry(d1_n, d2_n, s_key, sim, 1, 0)
            df2, lap2, len2 = get_telemetry(d2_n, d1_n, s_key, sim, 2, 5)

        if not df1.empty and not df2.empty:
            common = min(len(df1), len(df2))
            delta = np.cumsum((1 / np.maximum(df2['speed'].values[:common]/3.6, 1)) - (1 / np.maximum(df1['speed'].values[:common]/3.6, 1))) * (max(len1, len2)/common)
            peak_gap = delta[np.argmax(np.abs(delta))]
            
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric(d1_name.split()[-1].upper(), f"{df1['speed'].max():.0f} KM/H", f"{df1['speed'].max()-df2['speed'].max():+.0f}")
            m2.metric(d2_name.split()[-1].upper(), f"{df2['speed'].max():.0f} KM/H", f"{df2['speed'].max()-df1['speed'].max():+.0f}")
            m3.metric("LAP DELTA", f"{lap1-lap2:+.3f} S", delta=f"{lap1-lap2:+.3f}", delta_color="inverse")
            m4.metric("PEAK GAP", f"{peak_gap:+.3f} S", delta=f"{peak_gap:+.3f}", delta_color="inverse")
            m5.metric("PIPELINE", "SIM" if sim else "LIVE")

            lap_diff = lap1 - lap2
            top_diff = df1['speed'].max() - df2['speed'].max()
            avg_speed_diff = df1['speed'].mean() - df2['speed'].mean()
            avg_throttle_diff = df1['throttle'].mean() - df2['throttle'].mean()
            peak_dist = df1['distance'].values[:common][np.argmax(np.abs(delta))]
            peak_direction = "gained" if peak_gap < 0 else "lost"

            if abs(lap_diff) < 0.005:
                pace_clause = f"<b>{d1_name}</b> and <b>{d2_name}</b> are virtually matched on single-lap pace ({lap_diff:+.3f} s)"
                if abs(avg_speed_diff) >= 0.5:
                    spd_leader = d1_name if avg_speed_diff > 0 else d2_name
                    spd_other = d2_name if avg_speed_diff > 0 else d1_name
                    factor_clause = f"balancing a {abs(avg_speed_diff):.2f} km/h higher average speed for {spd_leader} against {spd_other}'s speed in other sections"
                elif abs(avg_throttle_diff) >= 0.5:
                    thr_leader = d1_name if avg_throttle_diff > 0 else d2_name
                    factor_clause = f"with {thr_leader} holding a {abs(avg_throttle_diff):.2f}% higher average throttle"
                elif abs(top_diff) >= 1.0:
                    top_leader = d1_name if top_diff > 0 else d2_name
                    factor_clause = f"with a {abs(top_diff):.0f} km/h peak speed edge for {top_leader}"
                else:
                    factor_clause = "with closely matched speed and throttle profiles across the lap"
                takeaway_text = "shows closely balanced single-lap pace where small section trade-offs cancel out over the lap."
            else:
                faster_driver = d1_name if lap_diff < 0 else d2_name
                slower_driver = d2_name if lap_diff < 0 else d1_name
                faster_avg_spd = avg_speed_diff if lap_diff < 0 else -avg_speed_diff
                faster_avg_thr = avg_throttle_diff if lap_diff < 0 else -avg_throttle_diff
                faster_top_spd = top_diff if lap_diff < 0 else -top_diff

                pace_clause = f"<b>{faster_driver}</b> is faster on single-lap pace by <b>{abs(lap_diff):.3f} s</b> vs. <b>{slower_driver}</b>"

                if faster_avg_spd >= 0.5:
                    factor_clause = f"driven mainly by a {faster_avg_spd:.2f} km/h higher average speed for {faster_driver}"
                elif faster_avg_thr >= 0.5:
                    factor_clause = f"driven mainly by a {faster_avg_thr:.2f}% higher average throttle for {faster_driver}"
                elif faster_top_spd >= 1.0:
                    factor_clause = f"driven mainly by a {faster_top_spd:.0f} km/h top speed edge for {faster_driver}"
                elif faster_avg_spd <= -0.5:
                    factor_clause = f"despite {slower_driver} holding a {abs(faster_avg_spd):.2f} km/h higher average speed"
                elif faster_avg_thr <= -0.5:
                    factor_clause = f"despite {slower_driver} holding a {abs(faster_avg_thr):.2f}% higher average throttle"
                elif faster_top_spd <= -1.0:
                    factor_clause = f"despite {slower_driver} holding a {abs(faster_top_spd):.0f} km/h top speed edge"
                else:
                    factor_clause = "with closely matched speed and throttle averages across the lap"

                if faster_avg_spd <= -0.5 and faster_avg_thr >= 0.5:
                    takeaway_text = f"shows {faster_driver} offsetting straight/average speed deficits through stronger throttle and corner-exit power ({faster_avg_thr:+.2f}% avg throttle vs. {slower_driver})."
                elif faster_avg_spd <= -0.5:
                    takeaway_text = f"shows {faster_driver} gaining time in braking zones or cornering sections to overcome {slower_driver}'s higher average speed."
                elif faster_avg_thr >= 0.5:
                    takeaway_text = f"shows traction and corner-exit power delivery ({faster_driver} +{faster_avg_thr:.2f}% avg throttle vs. {slower_driver}) as a key differentiator."
                elif faster_avg_spd >= 0.5 and faster_avg_thr < -0.5:
                    takeaway_text = f"shows {faster_driver} carrying higher overall speed despite {slower_driver}'s +{abs(faster_avg_thr):.2f}% higher average throttle."
                else:
                    takeaway_text = f"shows cumulative section pace and peak speed ({top_diff:+.0f} km/h {d1_name} vs. {d2_name}) shaping the final gap."

            if "race" in s_name.lower() or "sprint" in s_name.lower():
                scope_note = (
                    f"<br><strong style='color:#FF1801;'>Note:</strong> this compares each driver's fastest clean lap rather than full-{s_name.lower()} classification, "
                    f"where pit strategy, tire wear, traffic, and grid position determine final finishing order."
                )
            else:
                scope_note = (
                    f"<br><strong style='color:#FF1801;'>Note:</strong> this compares each driver's fastest clean telemetry lap in {s_name}, "
                    f"which may differ from final session classification depending on track evolution, traffic, or lap deletions."
                )

            mode_label = "Simulation" if sim else "Live"
            st.markdown(
                f"<div style='color:#CCCCCC; font-size:0.95rem; margin: 10px 0 18px 0;'>"
                f"<strong style='color:#FF1801;'>Quick Summary ({year} {gp_raw} — {s_name}, {mode_label}):</strong> "
                f"{pace_clause}, {factor_clause}, "
                f"with a peak gap swing of <b>{peak_gap:+.2f} s</b> ({peak_direction} by {d1_name}) near <b>{peak_dist:,.0f} m</b>; "
                f"overall this {takeaway_text}{scope_note}"
                f"</div>",
                unsafe_allow_html=True
            )

            titles = ["Spatial Gap Analysis", "Speed Comparison", "Throttle Application"]
            y_labels = ["Delta (s)", "Speed (km/h)", "Throttle (%)"]
            hover_formats = ["+.2f", ".2f", ".2f"]
            hover_units = ["s", "km/h", "%"]
            hover_names = ["Delta", "Speed", "Throttle"]
            for i, title in enumerate(titles):
                fig = go.Figure()
                driver_label = f"{d1_name} vs. {d2_name}" if i == 0 else d1_name
                fig.add_trace(go.Scatter(
                    x=df1['distance'][:common],
                    y=delta if i==0 else df1.iloc[:, i],
                    name=d1_name,
                    line=dict(color='#00FFFF'),
                    hovertemplate=(
                        f"<b>Driver: {driver_label}</b><br>"
                        "Distance: %{x:,.1f} m<br>"
                        f"{hover_names[i]}: %{{y:{hover_formats[i]}}} {hover_units[i]}"
                        "<extra></extra>"
                    )
                ))
                if i > 0:
                    fig.add_trace(go.Scatter(
                        x=df2['distance'],
                        y=df2.iloc[:, i],
                        name=d2_name,
                        line=dict(color='#FF00FF'),
                        hovertemplate=(
                            f"<b>Driver: {d2_name}</b><br>"
                            "Distance: %{x:,.1f} m<br>"
                            f"{hover_names[i]}: %{{y:{hover_formats[i]}}} {hover_units[i]}"
                            "<extra></extra>"
                        )
                    ))
                fig.update_layout(title=dict(text=title, x=0.05, font=dict(color='#FF1801', size=14, family="Segoe UI")), xaxis=dict(title="Distance (m)"), yaxis=dict(title=y_labels[i]), template="plotly_dark", height=300, margin=dict(l=50, r=20, t=50, b=40))
                st.plotly_chart(fig, use_container_width=True)
        else:
            # ---> CUSTOM ERROR: DRIVER DATA UNAVAILABLE <---
            st.markdown(f"""
            <div class='warning-box'>
                <b>⚠️ Driver data for this session not available</b><br>
                The selected driver combination (<b>{d1_name}</b> vs <b>{d2_name}</b>) has incomplete or missing telemetry records for this specific session.<br><br>
                <i>Please choose a different driver pair or switch to <b>Simulation Mode</b>.</i>
            </div>
            """, unsafe_allow_html=True)

with st.expander("📖 PIT-WALL ANALYTICS: COMPREHENSIVE GUIDE"):
    st.markdown("""
    ### How to Read These Plots:
- <strong style='color:#FF1801;'>Spatial Gap Analysis:</strong> Tracks the cumulative time gap across track distance—a negative value (Green) means your primary driver is pulling away, while a positive value (Red) means they are losing time. Upward/downward shifts show where time is gained or lost along the lap.
- <strong style='color:#FF1801;'>Speed Comparison:</strong> Compares top-end straight speed and corner entry/exit velocity side by side across the lap so you can spot traction or drag differences.
- <strong style='color:#FF1801;'>Throttle Application:</strong> Shows how early and smoothly each driver gets back on full power after braking zones or corners.
- <strong style='color:#FF1801;'>Telemetry:</strong> These plots are synced to distance, not time. This is how engineers find exactly where a driver is braking too early or missing the exit power.

    ### Metric Breakdown:
- <strong style='color:#FF1801;'>Driver Top Speed Cards:</strong> Show peak recorded speed (`KM/H`) for each driver alongside the relative speed difference (`+/-`) against the other driver.
- <strong style='color:#FF1801;'>Lap Delta:</strong> The bottom line—how many seconds faster or slower the driver is compared to the benchmark.
- <strong style='color:#FF1801;'>Peak Gap:</strong> Your diagnostic tool for maximum swing—shows the largest time advantage or deficit reached along the lap, helping pinpoint where the biggest gain or loss happened.
- <strong style='color:#FF1801;'>Pipeline Indicator:</strong> Shows whether the dashboard is currently running on `LIVE` telemetry or fallback `SIM` mode.

    ### Technical Architecture:
- <strong style='color:#FF1801;'>The Pipeline:</strong> Built to be "pit-wall proof." If the live API heartbeat stops, the app automatically pivots to a high-fidelity simulation, keeping the dashboard alive.
- <strong style='color:#FF1801;'>Normalization:</strong> We use `numpy.interp` to map messy F1 sensor data onto a uniform distance grid across the lap (around ~5km on typical circuits with minor ~0.2–0.3km variance, or 4km in simulation mode) for a clean comparison.
- <strong style='color:#FF1801;'>Lap Selection:</strong> Queries session lap records, filters out incomplete or missing timing/telemetry runs, and evaluates the fastest clean laps for comparison.

    ### Practical Applications:
- <strong style='color:#FF1801;'>Qualifying & Race Prep:</strong> Helps compare two drivers' fastest laps to isolate whether pace differences come from high-speed straights, braking zones, or corner exits.
- <strong style='color:#FF1801;'>Setup & Driving Diagnostics:</strong> Pinpoints where a driver loses time repeatedly on a circuit—such as late throttle pickup or lower minimum corner speed—to guide setup or driving adjustments.
- <strong style='color:#FF1801;'>Broadcast & Post-Session Review:</strong> Turns raw telemetry feeds into clear, distance-aligned visuals for rapid post-session debriefs and storytelling.

    ### Data Governance:
- <strong style='color:#FF1801;'>Fail-Safe Logic:</strong> Every request has a strict timeout, so a slow server never hangs your UI.
- <strong style='color:#FF1801;'>Deterministic Simulation:</strong> We hash `session_key` and `driver_id` with `zlib.crc32` to generate a unique, repeatable "telemetry fingerprint."
    """, unsafe_allow_html=True)
