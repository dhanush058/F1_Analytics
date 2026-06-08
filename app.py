import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import shutil
from google import genai

# Set page config for a professional dark look
st.set_page_config(page_title="F1 Telemetry Platform", layout="wide")
st.title("🏎️ Formula 1 Spatial Telemetry Analyzer & AI Insights")

# 1. Setup Robust Caching Layer
CACHE_DIR = "f1_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
fastf1.Cache.enable_cache(CACHE_DIR)

# Initialize Gemini Client safely using the official SDK
ai_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=ai_key) if ai_key else None

# Helper function to dynamically fetch the full season calendar reliably
@st.cache_data
def get_season_events(selected_year):
    try:
        schedule = fastf1.get_event_schedule(selected_year)
        gp_events = schedule[schedule['EventFormat'] != 'testing']
        return list(zip(gp_events['EventName'].tolist(), gp_events['RoundNumber'].tolist()))
    except Exception:
        return [("Australian Grand Prix", 1), ("Monaco Grand Prix", 6), ("Italian Grand Prix", 15)]

# 2. Sidebar Controls (Race Setup)
st.sidebar.header("Race Setup")
year = st.sidebar.selectbox("Year", [2026, 2025, 2024], index=0)

event_options = get_season_events(year)
event_names = [e[0] for e in event_options]
selected_event_name = st.sidebar.selectbox("Circuit", event_names, index=0)

selected_round = event_options[event_names.index(selected_event_name)][1]

session_map = {"Qualifying": "Q", "Race": "R"}
selected_session_label = st.sidebar.selectbox("Session", list(session_map.keys()), index=0)
session_type = session_map[selected_session_label]

driver_map = {
    "George Russell": "RUS",
    "Kimi Antonelli": "ANT",
    "Max Verstappen": "VER",
    "Lewis Hamilton": "HAM",
    "Charles Leclerc": "LEC",
    "Lando Norris": "NOR",
    "Oscar Piastri": "PIA",
    "Isack Hadjar": "HAD",
    "Liam Lawson": "LAW",
    "Pierre Gasly": "GAS",
    "Oliver Bearman": "BEA",
    "Franco Colapinto": "COL",
    "Arvid Lindblad": "LIN",
    "Carlos Sainz": "SAI",
    "Alexander Albon": "ALB",
    "Esteban Ocon": "OCO",
    "Gabriel Bortoleto": "BOR",
    "Fernando Alonso": "ALO",
    "Nico Hulkenberg": "HUL",
    "Valtteri Bottas": "BOT",
    "Sergio Perez": "PER",
    "Lance Stroll": "STR"
}
driver_names = list(driver_map.keys())

selected_d1_name = st.sidebar.selectbox("Driver 1", driver_names, index=0)
selected_d2_name = st.sidebar.selectbox("Driver 2", options=driver_names, index=1)

driver3_options = ["None"] + driver_names
selected_d3_name = st.sidebar.selectbox("Driver 3 (Optional)", driver3_options, index=0)

driver1 = driver_map[selected_d1_name]
driver2 = driver_map[selected_d2_name]
driver3 = "None" if selected_d3_name == "None" else driver_map[selected_d3_name]

st.sidebar.markdown("---")
st.sidebar.subheader("Data Maintenance")
force_refresh = st.sidebar.checkbox("Force Refresh Live Data", value=False)

# Initialize Session State tracking for charts, chatbot memory, and data context
if "telemetry_payload" not in st.session_state:
    st.session_state.telemetry_payload = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "ai_context_string" not in st.session_state:
    st.session_state.ai_context_string = ""

# 3. Defensive Data Fetching Function
def get_single_driver_telemetry(session, driver_code):
    try:
        driver_laps = session.laps.pick_driver(driver_code)
        if driver_laps.empty:
            return None
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None or not hasattr(fastest_lap, 'get_telemetry'):
            return None
        telemetry = fastest_lap.get_telemetry().add_distance()
        if telemetry.empty or 'Speed' not in telemetry.columns:
            return None
        return telemetry
    except Exception:
        return None

def process_race_session(year, round_num, session_type, d1, d2, d3):
    try:
        session = fastf1.get_session(year, round_num, session_type)
        session.load(laps=True, telemetry=True, weather=False)
    except Exception as e:
        return {"error": f"API data is not finalized yet for this event: {str(e)}", "data": {}}

    results = {}
    for d in [d1, d2, d3]:
        if d != "None":
            t = get_single_driver_telemetry(session, d)
            if t is not None:
                results[d] = t
    return {"error": None, "data": results}

# Execute Data Pipeline via Button Click
if st.sidebar.button("Analyze Performance"):
    if (driver1 == driver2) or (driver3 != "None" and (driver1 == driver3 or driver2 == driver3)):
        st.error("Please select unique drivers to compare.")
    else:
        if force_refresh:
            st.cache_data.clear()
            if os.path.exists(CACHE_DIR):
                shutil.rmtree(CACHE_DIR)
            os.makedirs(CACHE_DIR)
            fastf1.Cache.enable_cache(CACHE_DIR)
            st.info("Cache wiped. Pulling fresh server streams...")

        with st.spinner("Extracting and processing telemetry grids..."):
            payload = process_race_session(year, selected_round, session_type, driver1, driver2, driver3)
            
        if payload["error"]:
            st.error(payload["error"])
        elif len(payload["data"].keys()) < 2:
            st.error("Telemetry streams are incomplete for this driver combination. Check 'Force Refresh Live Data' to clear any bad files.")
        else:
            st.session_state.telemetry_payload = payload["data"]
            st.session_state.chat_history = []  # Reset chat session when data switches
            
            # --- GENERATE SUMMARY CONTEXT FOR THE AI CHATBOT ---
            summary_lines = [f"F1 Telemetry Data Context for {selected_event_name} ({year}), Session: {selected_session_label}"]
            code_to_name = {v: k for k, v in driver_map.items()}
            
            for code, df in payload["data"].items():
                name = code_to_name[code]
                max_spd = df['Speed'].max()
                min_spd = df['Speed'].min()
                avg_thro = df['Throttle'].mean()
                summary_lines.append(f"- {name} ({code}): Top Speed = {max_spd:.1f} km/h, Apex Minimum Speed = {min_spd:.1f} km/h, Average Throttle Application = {avg_thro:.1f}%.")
            
            st.session_state.ai_context_string = "\n".join(summary_lines)

# --- RENDERING DASHBOARD INTERFACE ---
if st.session_state.telemetry_payload:
    telemetry_data = st.session_state.telemetry_payload
    successful_codes = list(telemetry_data.keys())
    code_to_name = {v: k for k, v in driver_map.items()}
    successful_names = [code_to_name[code] for code in successful_codes]
    
    st.success(f"Successfully mapped spatial coordinates for: {', '.join(successful_names)}!")
    
    # 4. Build Subplots Safely
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Velocity Comparison (Minimum Corner Speed)", "Throttle Application (Exit Traction)"))
    
    color_palette = {driver1: '#00FF00', driver2: '#1E90FF', driver3: '#FF4500'}
    
    for drv_code in successful_codes:
        df = telemetry_data[drv_code]
        drv_color = color_palette.get(drv_code, '#FFFFFF')
        full_display_name = code_to_name[drv_code]
        
        fig.add_trace(go.Scatter(x=df['Distance'], y=df['Speed'], mode='lines', name=full_display_name,
                                 line=dict(color=drv_color, width=2),
                                 hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>"), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df['Distance'], y=df['Throttle'], mode='lines', name=full_display_name,
                                 line=dict(color=drv_color, width=2), showlegend=False,
                                 hovertemplate="Distance: %{x:.0f}m<br>Throttle: %{y:.1f}%<extra></extra>"), row=2, col=1)
    
    # 5. Global Layout Styling (FIXED GRID OVERLAP)
    fig.update_layout(height=650, template="plotly_dark", hovermode="x unified",
                      margin=dict(l=50, r=20, t=60, b=50),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    fig.update_xaxes(title_text="Distance along track (meters)", row=2, col=1)
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    
    # Force row 2 to strictly display its own independent 0-100% scale labels
    fig.update_yaxes(
        title_text="Throttle %", 
        range=[0, 105], 
        tickvals=[0, 25, 50, 75, 100],
        row=2, col=1
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # 6. INTEGRATED INTERACTIVE CHATBOT PLATFORM
    st.markdown("---")
    st.subheader("💬 AI Copilot Telemetry Assistant")
    
    if not client:
        st.info("💡 To talk to your data, paste a `GEMINI_API_KEY` into your environment or app secrets panel.")
    else:
        st.caption("Ask your data assistant anything about the current drivers on screen (e.g., 'Who held the higher top speed?' or 'Summarize the throttle performance').")
        
        # Render clean scrollable chat interface
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        if user_prompt := st.chat_input("Ask a question about this lap..."):
            with st.chat_message("user"):
                st.write(user_prompt)
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            # Formulate systemic prompt inject engineering
            system_instruction = (
                "You are an expert F1 performance telemetry data analyst. Use the following summary metrics "
                "to provide clear, concise, professional comparative answers to the user's questions. "
                "Keep answers technical yet easy to understand for team principals.\n\n"
                f"Current Lap Context:\n{st.session_state.ai_context_string}"
            )
            
            full_prompt = f"{system_instruction}\n\nUser Question: {user_prompt}"
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing telemetry profiles..."):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=full_prompt,
                        )
                        ai_response = response.text
                        st.write(ai_response)
                        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                    except Exception as e:
                        st.error(f"Chatbot service encountered an issue: {str(e)}")

    # 7. Simplified Metric Explanations for Users
    st.markdown("---")
    tab1, tab2 = st.tabs(["💡 Live Telemetry Metric Guide", "📊 Why Spatial Distance Alignment Matters"])
    with tab1:
        st.subheader("How to Read These Charts Instantly")
        st.markdown("""
        Think of these charts as a side-by-side comparison of how drivers attack a corner:
        
        * **The 'V' Valleys (Speed Chart):** Every dip represents a corner. 
            * **Braking:** Look at where a line drops off a cliff. The driver whose line drops later braved a later braking point.
            * **Cornering Momentum:** Look at the absolute lowest tip of the 'V'. Whichever driver's line stays higher at the lowest point carried more **minimum corner speed** through the apex.
        
        * **The Traction Hills (Throttle Chart):** Look at the lines climbing back up to 100% as they leave a corner.
            * **Good Traction:** A straight, steep climb up means the car was stable and the driver pinned the gas immediately, maximizing straight-line speed.
            * **Instability/Wheelspin:** If a line stutters, flatlines, or climbs slowly like a staircase, the driver had to lift off the throttle because the car was sliding or losing grip.
        """)
    with tab2:
        st.subheader("Data Analyst Design Insight")
        st.write("Traditional time-series graphs plot data against clock seconds. In Formula 1, if one driver brakes earlier, their entire timeline shifts forward, making direct visual overlays impossible to compare. By using a custom data pipeline to resample and normalize telemetry across Track Distance (Meters), this dashboard locks all selected profiles to the exact same physical coordinates. You are looking at an absolute, apples-to-apples performance breakdown at every single meter of the circuit.")
else:
    st.info("Select options in the sidebar and click 'Analyze Performance' to synchronize live data profiles.")
