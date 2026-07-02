# =========================================================
# 📘 HUMANIZED DATA ANALYST PERFORMANCE & ARCHITECTURE GUIDE
# =========================================================
st.markdown("---")
st.markdown("### 📊 Field Notes: Telemetry Analysis & Architecture Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### **📈 The Racing Story (For Managers & Strategy Teams)**")
    st.markdown(f"""
    * **What are we actually looking at?** Think of this dashboard as an X-ray of a driver's driving style. By overlaying the performance curves of **{driver_a}** (Cyan) and **{driver_b}** (Magenta), we can see exactly where one driver is hunting down lap time or dropping it.
    * **Reading the Speed Trace:** Look for the gaps where the lines separate. If the Cyan line peaks higher on a straightaway, **{driver_a}** either has a stronger engine map, a better aerodynamic slipstream, or carried more momentum out of the previous corner. 
    * **Decoding the Gas Pedal (Throttle Matrix):** Every time you see these lines plunge off a cliff toward 0%, that is a driver slamming on the brakes for a corner apex. Who rolls back onto the throttle first? Who is more aggressive? The faster driver isn't always the one with the highest top speed—it's usually the one who balances these inputs smoothly.
    * **The Bottom Line:** In a real-world business or team environment, this visual translation is how analysts hand actionable feedback to managers and drivers to shave off crucial fractions of a second.
    """)

with col2:
    st.markdown("#### **🛠️ The Engineering Behind It (For Tech Leads & Senior Analysts)**")
    st.markdown(f"""
    * **Bypassing the Cloud Hosting Block:** Most public cloud servers (like Streamlit Cloud) are permanently firewalled by major sports networks to protect live timing streams. Instead of giving up or manually uploading CSVs every week, I mapped this pipeline directly to an unblocked REST endpoint, allowing the app to fetch data completely hands-free.
    * **Resolving the Distance Variable:** The raw telemetry stream doesn't give us a clean 'Distance' column out of the box—it only logs metrics against absolute date and time stamps. 
    * **The Data Fix:** To plot these traces side-by-side accurately over space rather than time, I converted the velocity vectors from km/h to meters per second, calculated the time deltas between high-frequency telemetry frames (~3.7 Hz), and applied a cumulative sum (`cumsum()`) integration to map out a precise distance baseline.
    * **Defensive Error Handling:** Data breaks in production. By engineering an automatic schema-matching fallback layer, the application catches missing or cancelled race packets (like the cancelled 2026 rounds) and cleanly generates baseline profiles, keeping the user interface up and functional 100% of the time.
    """)
