def get_single_driver_telemetry(session, driver_code):
    try:
        # Pick driver laps safely
        driver_laps = session.laps.pick_driver(driver_code)
        if driver_laps.empty:
            return None
        
        fastest_lap = driver_laps.pick_fastest()
        if fastest_lap is None:
            return None
            
        # Verify the telemetry method exists safely
        if not hasattr(fastest_lap, 'get_telemetry'):
            return None
            
        telemetry = fastest_lap.get_telemetry().add_distance()
        if telemetry.empty or 'Speed' not in telemetry.columns:
            return None
            
        return telemetry
    except Exception:
        return None
