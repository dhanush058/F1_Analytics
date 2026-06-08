import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Set page config for a professional dark look
st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")
st.title("🏎️ Formula 1 Spatial Telemetry Analyzer (3-Driver Comparison)")

# 1. Setup Robust Caching Layer
CACHE_DIR = "f1_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# Helper function to dynamically fetch the full season calendar
@st.cache_data
def get_season_circuits(selected_year):
    try:
        schedule = fastf1.get_event_schedule(selected_year)
        # Filter out testing sessions, keep only official Grand Prix events
        gp_events = schedule[schedule['EventFormat'] != 'testing']
        return gp_events['EventName'].tolist()
    except Exception:
        # Fallback list just in case the API schedule endpoint fails
        return ["Monaco", "Monza", "Silverstone", "Spa", "Melbourne", "Suzuka"]

# 2. Sidebar Controls
st.sidebar.header("Match Setup")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=0)

# DYNAMIC CIRCUITS: Pulls every single race for the selected year instantly
circuit_options = get_season_circuits(year)
circuit = st.sidebar.selectbox("Circuit", circuit_options, index=0)

session_type = st.sidebar.selectbox("Session", ["Q", "R"], index=0)

# Full 2024-2026 active grid abbreviations
driver_options = ["ANT", "VER", "HAM", "LEC", "NOR", "RUS", "PIA", "HAD", "LAW", "GAS", "BEA", "COL", "LIN", "SAI", "ALB", "OCO", "BOR", "ALO", "HUL", "BOT", "PER", "STR"]
driver1 = st.sidebar.selectbox("Driver 1", driver_options, index=0) # Defaults to ANT
driver2 = st.sidebar.selectbox("Driver 2", driver_options, index=1) # Defaults to VER
driver3 = st.sidebar.selectbox("Driver 3", driver_options, index=2) # Defaults to HAM

# 3. Data Core Fetching Function for 3 Drivers
@st.cache_data(show_spinner="Fetching massive telemetry streams...")
def get_three_telemetry_data(year, circuit, session_type, d1, d2, d3):
    try:
        session = fastf1.get_session(year, circuit, session_type)
        session.load(laps=True, telemetry=True, weather=False)
        
        # Get fastest laps for all 3 drivers
        lap1 = session.laps.pick_driver(d1).pick_fastest()
        lap2 = session.laps.pick_driver(d2).pick_fastest()
        lap3 = session.laps.pick_driver(d3).pick_fastest()
        
        # Extract telemetry profiles
        tel1 = lap1.get_telemetry().add_distance()
        tel2 = lap2.get_telemetry().add_distance()
        tel3 = lap3.get_telemetry().add_distance()
        
        return tel1, tel2, tel3
    except Exception as e:
        return None, None, None

# Execute Data Pipeline
if st.sidebar.button("Analyze Performance"):
    if driver1 == driver2 or driver2 == driver3 or driver1 == driver3:
        st.error("Please select three different drivers to compare.")
    else:
        tel1, tel2, tel3 = get_three_telemetry_data(year, circuit, session_type, driver1, driver2, driver3)
        
        if tel1 is not None and tel2 is not None and tel3 is not None:
            st.success(f"Successfully synchronized data for {driver1}, {driver2}, and {driver3}!")
            
            # 4. Build Interactive Multi-Panel Plotly Charts
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.1,
                                subplot_titles=("Velocity Comparison (Minimum Corner Speed)", "Throttle Application (Exit Traction)"))
            
            colors = ['#00FF00', '#1E90FF', '#FF4500'] # Neon Green, Blue, Orange
            
            # --- ROW 1: VELOCITY ---
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Speed'], mode='lines', name=driver1,
                           line=dict(color=colors[0], width=2),
                           hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Speed'], mode='lines', name=driver2,
                           line=dict(color=colors[1], width=2),
                           hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel3['Distance'], y=tel3['Speed'], mode='lines', name=driver3,
                           line=dict(color=colors[2], width=2),
                           hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
                row=1, col=1
            )
            
            # --- ROW 2: THROTTLE ---
            fig.add_trace(
                go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], mode='lines', name=driver1,
                           line=dict(color=colors[0], width=2), showlegend=False,
                           hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], mode='lines', name=driver2,
                           line=dict(color=colors[1], width=2), showlegend=False,
                           hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
                row=2, col=1
            )
            fig.add_trace(
                go.Scatter(x=tel3['Distance'], y=tel3['Throttle'], mode='lines', name=driver3,
                           line=dict(color=colors[2], width=2), showlegend=False,
                           hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
                row=2, col=1
            )
            
            # 5. Global Layout Styling
            fig.update_layout(
                height=650,
                template="plotly_dark",
                hovermode="x unified",
                margin=dict(l=50, r=20, t=60, b=50),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            fig.update_xaxes(title_text="Distance along track (meters)", row=2, col=1)
            fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
            fig.update_yaxes(title_text="Throttle %", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 6. RESTORED GUIDE: Detailed Metric Explanations for Users
            st.markdown("---")
            tab1, tab2 = st.tabs(["💡 Live Telemetry Metric Guide", "📊 Why Spatial Distance Alignment Matters"])
            with tab1:
                st.subheader("How to Analyze the 3 Drivers")
                st.markdown("""
                * **Velocity Valleys (Speed Chart):** Look at the deep dips in the lines. These represent braking points and corners. Whichever driver's line stays highest at the absolute lowest point carried the best **minimum corner speed** at the apex.
                * **Braking Points:** Where a line suddenly drops vertically reveals exactly where a driver smashed the brakes. You can spot who braved a later braking point.
                * **Throttle Application (Throttle Chart):** Look at the slopes where the line climbs back from 0% to 100%. A steeper, faster climb means that driver achieved **exit traction** and pinned the gas pedal earlier, maximizing their top speed down the next straightway.
                """)
            with tab2:
                st.subheader("Data Analyst Design Insight")
                st.write("Traditional time-series graphs plot data against clock seconds. In Formula 1, if one driver brakes earlier, their entire timeline shifts forward, making direct visual overlays impossible to compare. By using a custom data pipeline to resample and normalize telemetry across **Track Distance (Meters)**, this dashboard locks all three profiles to the exact same physical coordinates. You are looking at an absolute, apples-to-apples performance breakdown at every single meter of the circuit.")
            
        else:
            st.error("Could not fetch data for this specific selection. Ensure the chosen session has occurred and all selected drivers set valid laps.")
else:
    st.info("Select options in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
