import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Set page config for a professional dark look
st.set_page_config(page_title="F1 Telemetry Analyzer", layout="wide")
st.title("🏎️ Formula 1 Spatial Telemetry Analyzer")

# 1. Setup Robust Caching Layer
CACHE_DIR = "f1_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# 2. Sidebar Controls (User Input)
st.sidebar.header("Match Setup")
year = st.sidebar.selectbox("Year", [2024, 2023, 2022], index=0)
circuit = st.sidebar.text_input("Circuit Name (e.g., Monza, Silverstone)", "Monza")
session_type = st.sidebar.selectbox("Session", ["Q", "R"], index=0) # Q = Quali, R = Race

driver1 = st.sidebar.text_input("Driver 1 Code (e.g., VER)", "VER").upper()
driver2 = st.sidebar.text_input("Driver 2 Code (e.g., HAM)", "HAM").upper()

# 3. Data Core Fetching Function (Cached by Streamlit)
@st.cache_data(show_spinner="Fetching massive telemetry streams...")
def get_telemetry_data(year, circuit, session_type, d1, d2):
    try:
        session = fastf1.get_session(year, circuit, session_type)
        session.load(laps=True, telemetry=True, weather=False)
        
        # Get fastest laps
        lap1 = session.laps.pick_driver(d1).pick_fastest()
        lap2 = session.laps.pick_driver(d2).pick_fastest()
        
        # Extract telemetry
        tel1 = lap1.get_telemetry().add_distance()
        tel2 = lap2.get_telemetry().add_distance()
        
        # Check if they are teammates to trigger visual UX rules
        is_teammate = session.results.loc[session.results['Abbreviation'] == d1, 'TeamName'].values[0] == \
                      session.results.loc[session.results['Abbreviation'] == d2, 'TeamName'].values[0]
        
        return tel1, tel2, is_teammate
    except Exception as e:
        return None, None, False

# Execute Data Pipeline
if st.sidebar.button("Analyze Performance"):
    tel1, tel2, is_teammate = get_telemetry_data(year, circuit, session_type, driver1, driver2)
    
    if tel1 is not None and tel2 is not None:
        st.success(f"Successfully synchronized data for {driver1} vs {driver2}!")
        
        # Determine visual dash rules for teammates
        d2_line_style = "dash" if is_teammate else "solid"
        
        # 4. Build Interactive Multi-Panel Plotly Charts
        # Generates a 2-row layout: Row 1 = Velocity, Row 2 = Throttle
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.1,
                            subplot_titles=("Velocity Comparison (Minimum Corner Speed)", "Throttle Application (Exit Traction)"))
        
        # --- ROW 1: VELOCITY ---
        fig.add_trace(
            go.Scatter(x=tel1['Distance'], y=tel1['Speed'], mode='lines', name=driver1,
                       line=dict(color='#1E90FF', width=2),
                       hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel2['Distance'], y=tel2['Speed'], mode='lines', name=driver2,
                       line=dict(color='#FF4500', width=2, dash=d2_line_style),
                       hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"),
            row=1, col=1
        )
        
        # --- ROW 2: THROTTLE ---
        fig.add_trace(
            go.Scatter(x=tel1['Distance'], y=tel1['Throttle'], mode='lines', name=driver1,
                       line=dict(color='#1E90FF', width=2), showlegend=False,
                       hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
            row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=tel2['Distance'], y=tel2['Throttle'], mode='lines', name=driver2,
                       line=dict(color='#FF4500', width=2, dash=d2_line_style), showlegend=False,
                       hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"),
            row=2, col=1
        )
        
        # 5. Global Layout Styling (Optimized for Mobile/Desktop Tap & Hover)
        fig.update_layout(
            height=600,
            template="plotly_dark",
            hovermode="x unified",  # Aligns data lines perfectly when user taps a specific meter point
            margin=dict(l=50, r=20, t=60, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        fig.update_xaxes(title_text="Distance along track (meters)", row=2, col=1)
        fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
        fig.update_yaxes(title_text="Throttle %", row=2, col=1)
        
        # Render Chart to Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
        # 6. Embedded Product UX: Contextual Guides for Non-Technical Users
        st.markdown("---")
        tab1, tab2 = st.tabs(["💡 How to read these graphs", "📊 Real-World Engineering Value"])
        with tab1:
            st.write("**Velocity Valleys:** Look closely at the lowest points of the curves inside corners. Whichever driver's line stays higher carried more 'minimum speed' through that corner apex.")
            st.write("**Throttle Ramps:** Look at how quickly a driver transitions from 0% back to 100%. A steeper vertical climb means the driver got back on the gas pedal much earlier, gaining time on the straights.")
        with tab2:
            st.write("In professional Formula 1 debriefs, teams use this exact spatial metric tracking format to align physical sensor positions. This eliminates timing inaccuracies caused by completely different racing lines.")
            
    else:
        st.error("Could not fetch data. Please verify the Driver codes and Circuit name are valid.")
else:
    st.info("Adjust settings in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
