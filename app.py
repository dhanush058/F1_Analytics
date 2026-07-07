import streamlit as st
import requests
import pandas as pd
import numpy as np
import zlib
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. CONFIG & THEME ---
CITY_MAP = {"Australian Grand Prix": "Melbourne", "British Grand Prix": "Silverstone"} # Add all as needed

st.set_page_config(layout="wide", page_title="F1 Analytics: Pit-Wall")
st.markdown("""
<style>
    .stApp { background-color: #0B0B0E; color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
    [data-testid="stSidebar"] { background-color: #111116; border-right: 2px solid #FF1801; }
    [data-testid="stMetric"] { background-color: #15151C !important; border-top: 4px solid #FF1801 !important; padding: 15px; }
</style>
""", unsafe_allow_html=True)

# --- 2. RESILIENT DATA ENGINE ---
def check_api_health():
    """Diagnostic check to see if OpenF1 API is responsive."""
    try:
        res = requests.get("https://api.openf1.org/v1/meetings?year=2024", timeout=5)
        return res.status_code == 200
    except: return False

def get_telemetry(d1_n, d2_n, s_key, sim, d_id, offset=0):
    if sim:
        seed = zlib.crc32(f"{s_key}_{d1_n}_{d2_n}_{d_id}".encode())
        np.random.seed(seed + offset)
        dist = np.linspace(0, 4000.0, 1000)
        speed = 280 + 40 * np.sin(dist/400 + offset) + 20 * np.sin(dist/150)
        throttle = np.clip(50 + 50 * np.sin(dist/300 + offset), 0, 100)
        return pd.DataFrame({'distance': dist, 'speed': speed, 'throttle': throttle}), 85.0, 4000.0
    
    # Live Data Logic (omitted for brevity, keep your existing logic here)
    return pd.DataFrame(), 0, 0

# --- 3. UI & CONTROL ---
st.sidebar.title("Data Pipeline Control")
sim = st.sidebar.checkbox("Force Simulation Mode")

# PIPELINE DIAGNOSTIC
api_healthy = check_api_health()

if not api_healthy and not sim:
    st.error("⚠️ DATA PIPELINE INTERRUPTION")
    st.markdown("""
    **Diagnostics:** The OpenF1 Live API is currently unreachable. 
    **Recommendation:** System is defaulting to Simulation Mode to maintain analytical continuity.
    """)
    if st.button("Activate Simulation Environment"):
        sim = True
        st.rerun()
    st.stop() # Stops execution if data is missing, providing a clean professional fallback.

# ... Rest of your UI and Plotly Logic ...
