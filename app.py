# --- 4. PLOT ENGINE (Data Normalization Layer) ---
if d1 != "No Data" and d2 != "No Data":
    data_a = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d1))
    data_b = pipeline.get_driver_telemetry(s_map.get(selected_session), d_map.get(d2))
    
    if data_a and data_b:
        # Normalize: ensure it's a flat structure
        df_a = pd.json_normalize(data_a)
        df_b = pd.json_normalize(data_b)
        
        # Validation: Check if columns exist and replace 0s if data is actually missing
        for col in ['speed', 'throttle']:
            if col not in df_a.columns: df_a[col] = 0
            if col not in df_b.columns: df_b[col] = 0
        
        # Slice for UI performance
        df_a, df_b = df_a.iloc[:500], df_b.iloc[:500]
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Speed (km/h)", "Throttle (%)", "Delta (s)"))
        
        fig.add_trace(go.Scatter(y=df_a['speed'], name=d1, line=dict(color='#00FFFF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_b['speed'], name=d2, line=dict(color='#FF00FF')), row=1, col=1)
        fig.add_trace(go.Scatter(y=df_a['throttle'], name=f"{d1} Throttle", line=dict(color='#00FF00')), row=2, col=1)
        
        # Calculate safe delta (handle length mismatch)
        min_len = min(len(df_a), len(df_b))
        delta = df_a['speed'].values[:min_len] - df_b['speed'].values[:min_len]
        fig.add_trace(go.Scatter(y=delta, name="Delta", line=dict(color='#FFFF00')), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, plot_bgcolor='#0E1117')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Data returned from API is empty or malformed.")
        # Debugging: Show raw API sample if empty
        if data_a: st.write("Sample of Data A:", data_a[0])
