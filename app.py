# --- 6. CORE DISPLAY ---
    if df_a.empty or df_b.empty:
        st.error("⚠️ Telemetry stream offline for this live selection. Check 'Enable Simulation Mode' in the sidebar to review dashboard layouts.")
    else:
        st.markdown(f"""
            <h2 style='text-transform: uppercase; font-weight: 900; margin-bottom: 0px;'>F1 TELEMETRY ANALYSIS</h2>
            <h4 style='color: #FF1801; font-weight: 600; margin-top: 0px; margin-bottom: 25px;'>{selected_gp} — {selected_session}</h4>
        """, unsafe_allow_html=True)
        
        m1, m2, m3, m4, m5 = st.columns(5)
        
        # Delta Math Processing
        master_track_len = max(len_a, len_b)
        v_a_ms = np.where(df_a['speed'] < 10, 10, df_a['speed']) / 3.6
        v_b_ms = np.where(df_b['speed'] < 10, 10, df_b['speed']) / 3.6
        dx_step = master_track_len / 1000.0
        
        delta_time_array = np.cumsum((1 / v_b_ms) - (1 / v_a_ms)) * dx_step
        final_delta = lap_time_a - lap_time_b if (lap_time_a and lap_time_b) else delta_time_array[-1]
        
        max_gap_idx = np.argmax(np.abs(delta_time_array))
        max_gap = delta_time_array[max_gap_idx]
        
        vmax_a = df_a['speed'].max()
        vmax_b = df_b['speed'].max()
        vmax_diff = vmax_a - vmax_b

        # Standardized Cards (Removing driver names to prevent cramping)
        m1.metric(label=f"VMAX — {d1_display.split()[-1].upper()}", value=f"{vmax_a:.0f} KM/H", delta=f"{vmax_diff:.0f} KM/H")
        m2.metric(label=f"VMAX — {d2_display.split()[-1].upper()}", value=f"{vmax_b:.0f} KM/H", delta=f"{-vmax_diff:.0f} KM/H")
        
        # Standardized Lap and Gap Cards
        m3.metric(label="LAP TIME DELTA", value=f"{abs(final_delta):.3f} S", delta=f"{-final_delta:.3f} S", delta_color="normal")
        m4.metric(label="MAX SPATIAL GAP", value=f"{abs(max_gap):.3f} S", delta=f"{max_gap:.3f} S", delta_color="normal")
        m5.metric(label="DATA PIPELINE", value="SIMULATION" if sim_mode else "LIVE API")
