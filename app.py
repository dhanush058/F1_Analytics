import streamlit as st
import fastf1
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Setup
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide")

# 2. Year & Event Selection
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
selected_gp = st.sidebar.selectbox("Select GP", schedule['EventName'].tolist())

# 3. Session Loading
try:
    event = schedule[schedule['EventName'] == selected_gp].iloc[0]
    session = fastf1.get_session(year, event['RoundNumber'], 'Q')
    
    # Force load with progress bar
    with st.spinner("Loading session data..."):
        session.load(telemetry=True, laps=True)
    
    if session.results.empty:
        st.error("Session data is empty for this event.")
        st.stop()

    drivers = session.results['FullName'].dropna().tolist()
    d1 = st.sidebar.selectbox("Driver A", drivers)
    d2 = st.sidebar.selectbox("Ref Driver", drivers)

    # 4. Telemetry Engine
    def get_tel(name):
        code = session.results[session.results['FullName'] == name]['Abbreviation'].iloc[0]
        return session.laps.pick_driver(code).pick_fastest().get_telemetry()

    tel_a, tel_b = get_tel(d1), get_tel(d2)

    # 5. Dashboard
    st.title(f"🚀 {selected_gp} Telemetry")
    # ... (Plotly code here)
    st.success("Data loaded successfully.")

except fastf1.exceptions.DataNotLoadedError:
    st.error("FastF1 failed to load the session data. This often happens if the session is not yet indexed or blocked by IP.")
except Exception as e:
    st.error(f"Unexpected error: {e}")
