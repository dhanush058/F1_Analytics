import streamlit as st
import fastf1
import fastf1.plotting
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. Force Cache Refresh & Setup
fastf1.Cache.enable_cache('f1_cache')
st.set_page_config(layout="wide")

# 2. Select GP by Round Number (More Reliable for 2026)
year = st.sidebar.selectbox("Year", [2026, 2025, 2024])
schedule = fastf1.get_event_schedule(year)
selected_gp = st.sidebar.selectbox("Select GP", schedule['EventName'].tolist())
event = schedule[schedule['EventName'] == selected_gp].iloc[0]
round_num = int(event['RoundNumber'])

# 3. Robust Session Loading
try:
    session = fastf1.get_session(year, round_num, 'Q')
    with st.spinner("Loading session..."):
        session.load(telemetry=True, laps=True)
    
    if session.results.empty:
        st.error("Session data empty. Try a different GP.")
        st.stop()

    drivers = session.results['FullName'].dropna().tolist()
    d1 = st.sidebar.selectbox("Driver A", drivers)
    d2 = st.sidebar.selectbox("Ref Driver", drivers)

    # 4. Telemetry Extraction
    def get_tel(name):
        code = session.results[session.results['FullName'] == name]['Abbreviation'].iloc[0]
        # Ensure we pick the fastest lap and retrieve telemetry
        return session.laps.pick_driver(code).pick_fastest().get_telemetry()

    tel_a, tel_b = get_tel(d1), get_tel(d2)

    # 5. Dashboard (Simplified for stability)
    st.title(f"🚀 {selected_gp} Telemetry")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Speed'], name=d1), row=1, col=1)
    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Speed'], name=d2), row=2, col=1)
    st.plotly_chart(fig)

except Exception as e:
    st.error(f"Failed to load: {e}. If this persists, the data for this session is not yet public.")
