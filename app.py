def get_fastest_lap(name):
    # Check if results exist and if the driver is in the results
    driver_data = session.results[session.results['FullName'] == name]
    if driver_data.empty:
        return None
    
    code = driver_data['Abbreviation'].iloc[0]
    laps = session.laps.pick_driver(code)
    
    # Check if the driver actually completed any laps
    if laps.empty:
        return None
        
    return laps.pick_fastest()

# --- Updated Loading Logic ---
try:
    session = fastf1.get_session(year, selected_gp, 'Q')
    session.load(telemetry=True, laps=True)
    
    # Ensure results are available
    if not session.results.empty:
        driver_list = session.results['FullName'].dropna().tolist()
        d1 = st.sidebar.selectbox("Driver A", driver_list)
        d2 = st.sidebar.selectbox("Ref Driver", driver_list)
    else:
        st.error("Results are not yet available for this session.")
        st.stop()
except Exception as e:
    st.error(f"Could not load session data: {e}")
    st.stop()
