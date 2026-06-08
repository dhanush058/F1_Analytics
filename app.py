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

# 2. Sidebar Controls (Safe Dropdowns instead of text inputs)
st.sidebar.header("Match Setup")
year = st.sidebar.selectbox("Year", [2024, 2023, 2022], index=0)

# Preset clean lists to prevent user typos causing crashes
circuit_options = ["Monza", "Silverstone", "Spa", "Monaco", "Bahrain", "Suzuka", "Austin", "Singapore"]
circuit = st.sidebar.selectbox("Circuit", circuit_options, index=0)

session_type = st.sidebar.selectbox("Session", ["Q", "R"], index=0)

# Common driver codes preset list
driver_options = ["VER", "HAM", "LEC", "NOR", "SAI", "PER", "RUS", "PIA", "ALO", "GAS"]
driver1 = st.sidebar.selectbox("Driver 1", driver_options, index=0) # Defaults to VER
driver2 = st.sidebar.selectbox("Driver 2", driver_options, index=1) # Defaults to HAM
driver3 = st.sidebar.selectbox("Driver 3", driver_options, index=2) # Defaults to LEC

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
    # Guard rail to make sure users don't compare a driver against themselves
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
            
            colors = ['#1E90FF', '#FF4500', '#00FF00'] # Blue, Orange, Neon Green
            
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
            
        else:
            st.error("Could not fetch data for this specific selection. Try a different combination of drivers or checking if that session happened.")
else:
    st.info("Select options in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
