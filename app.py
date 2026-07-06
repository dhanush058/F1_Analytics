import streamlit as st
import fastf1
import fastf1.plotting

# Setup cache (Critical for performance)
fastf1.Cache.enable_cache('./cache') 

st.title("🏎️ FastF1 2026 Telemetry")

# Selectors
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
gp = st.sidebar.text_input("GP Name (e.g. Australian)")
session_type = st.sidebar.selectbox("Session", ['R', 'Q', 'FP1', 'FP2', 'FP3'])

if st.sidebar.button("Load Data"):
    session = fastf1.get_session(year, gp, session_type)
    session.load()  # This downloads/processes everything for you
    
    # Select Drivers
    driver_list = session.results['FullName'].tolist()
    d1 = st.sidebar.selectbox("Driver A", driver_list)
    d2 = st.sidebar.selectbox("Ref Driver", driver_list)
    
    # Get Laps and Telemetry
    laps_d1 = session.laps.pick_driver(d1).pick_fastest()
    laps_d2 = session.laps.pick_driver(d2).pick_fastest()
    
    tel_d1 = laps_d1.get_telemetry()
    tel_d2 = laps_d2.get_telemetry()
    
    # Display Plot
    st.line_chart(tel_d1[['Speed', 'Throttle']])
    st.success("Telemetry loaded successfully via FastF1!")
