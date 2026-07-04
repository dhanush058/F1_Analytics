import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# ⚙️ SECURE CACHE LAYER
# =========================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_api_json(url):
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

# =========================================================
# 🏎️ APP LAYOUT & CONFIGURATION
# =========================================================
st.set_page_config(page_title="F1 Performance Vault", layout="wide")

# Sidebar and variables
selected_year = st.sidebar.selectbox("Select Season", [2026, 2025, 2024], index=0)
# ... [Keep your TRACK_METRICS_DB, seasonal_schedule, and selection logic here] ...

# INITIALIZE session_key safely
session_key = None 

# Resolve session
session_url = f"https://api.openf1.org/v1/sessions?year={selected_year}"
sessions = fetch_api_json(session_url)
if sessions:
    # Resolve your specific session_key here
    # session_key = ... (your existing logic)

# =========================================================
# 📊 EVENT-DRIVEN DATA ENGINE (NO AUTO-REFRESH)
# =========================================================
def check_session_status(s_key):
    if s_key is None: return "no_key"
    data = fetch_api_json(f"https://api.openf1.org/v1/sessions?session_key={s_key}")
    return data[0].get('status') if data else "unknown"

# SAFE EXECUTION GUARD: Only run logic if session_key is resolved
if session_key is not None:
    status = check_session_status(session_key)
    
    if status == "finished" or demo_mode:
        # Load data only once
        telemetry_a, telemetry_b, engine_status = fetch_calibrated_telemetry(...)
        st.session_state.data_cache = (telemetry_a, telemetry_b)
    else:
        st.info(f"⏳ **Race In Progress:** Data will finalize after the session concludes. (Current Status: {status})")
        telemetry_a, telemetry_b = st.session_state.get("data_cache", (None, None))
else:
    st.error("❌ Session could not be resolved. Please check your selections.")

# =========================================================
# 📈 STATIC RENDERING (NO FRAGMENT = NO DIMMING)
# =========================================================
if telemetry_a is not None and telemetry_b is not None:
    # ... [Insert your Plotly and Metric card code here] ...
    # This will render exactly once and stay frozen.
else:
    st.write("Awaiting data finalization...")
