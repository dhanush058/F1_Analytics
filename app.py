import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ EVENT-DRIVEN DATA ENGINE (NO REFRESH FLICKER)
# =========================================================
@st.cache_data(ttl=600, show_spinner=False)
def check_session_status(s_key):
    # Only checks if the session is finalized
    data = fetch_api_json(f"https://api.openf1.org/v1/sessions?session_key={s_key}")
    return data[0].get('status') if data else "unknown"

# This function fetches only when manually triggered or when season/track changes
def get_clean_telemetry(s_key, d_map, d_a, d_b, target_length):
    # ... [Keep your fetch_calibrated_telemetry logic here] ...
    # This logic now runs only once per load or manual refresh
    pass

# =========================================================
# 🏎️ APP LAYOUT
# =========================================================
# Use a standard static layout. No fragment, no run_every.
# The user will simply refresh the page manually to pull the updated 'finalized' data.

# Fetch logic...
# [Keep your existing sidebar and metadata resolution]

# NEW: State Management
if "data_cache" not in st.session_state:
    st.session_state.data_cache = None

# Logic to only pull if session status is 'finished' or we are in 'demo_mode'
status = check_session_status(session_key)
if status == "finished" or demo_mode:
    telemetry_a, telemetry_b, engine_status = fetch_calibrated_telemetry(...)
    st.session_state.data_cache = (telemetry_a, telemetry_b)
else:
    st.info(f"⏳ **Race In Progress:** Data will auto-update upon session finalization. (Current Status: {status})")
    # Show last cached data if available
    telemetry_a, telemetry_b = st.session_state.data_cache if st.session_state.data_cache else (None, None)

# [Plotting remains static - it will not re-render unless you manually refresh]
