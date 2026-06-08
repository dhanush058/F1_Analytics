# 🏎️ Formula 1 Multi-Driver Telemetry & Performance Dashboard

An interactive, production-ready telemetry analytics platform built using **Streamlit**, **FastF1**, and **Matplotlib**. This application allows users to overlay and compare synchronized car sensor streams (Time Deltas, Velocity, and Throttle Application) between F1 drivers for any session from 2018 through the current 2026 season.

👉 **[Launch Live Streamlit Dashboard Application](https://f1analytics-lmfxcoc2smdzhdb4eppdfo.streamlit.app/)**

---

## 🚀 Core Engineering & Software Architecture Features

### 1. Dynamic Spatial Synchronization (Meter-by-Meter Alignment)
Traditional telemetry mapping over raw time arrays creates misalignment due to drivers taking different racing lines or starting laps at separate times. This pipeline uses **Pandas** and **FastF1** mathematical utilities to resample and transform time-series telemetry logs into spatial vectors, aligning data streams point-by-point based on **Physical Distance Along the Track Perimeter (Meters)**.

### 2. Built-in Network Resilience Layer (Hybrid Local Caching)
To bypass Ergast API rate-limits and cloud container network firewalls, the backend is engineered with a localized caching matrix (`f1_cache/`). When a race configuration is run, the engine serializes the data profiles into compressed binary cache files (`.ff1pkl`). If the live API handshake fails or hits a firewall on Streamlit Cloud, the application cleanly drops back to the cache layer, maintaining 100% application uptime.

### 3. Teammate Visual Protection Layer
To prevent visual confusion when analyzing drivers from the same construction team (who share the exact same official brand HEX color), the drawing engine intercepts the team assignment variables. It preserves the official color identity but automatically updates the line-style matrix—assigning a **Solid Line (`-`)** to the primary driver and an alternating **Dashed Line (`--`)** to the teammate.

### 4. Guided Analytics User Experience (UX)
Designed for both data scientists and casual racing fans, the frontend includes interactive breakdown tabs built below the charts. This turns abstract technical sensor data into actionable insights by breaking down how to interpret the shapes, peaks, and valleys of telemetry traces.

---

## 📊 Telemetry Panels Broken Down

1. **Lap Leaderboard:** Computes dynamic metric cards ranking the selected drivers relative to the fastest session baseline tracking target ($Ref_{tel}$).
2. **Time Delta Vector Panel ($ax[0]$):** Traces continuous performance differentials in seconds. The faster driver is anchored as a flat gray baseline ($0.0\text{s}$), and the climbing/dipping colored vectors map exactly where a trailing driver is losing or gaining time.
3. **Velocity Profile Panel ($ax[1]$):** Maps absolute wheel speeds ($\text{km/h}$). Steep drops highlight corner braking entries, "V-shapes" pinpoint braking intensity, and the bottoms of the valleys show corner apex minimum speeds.
4. **Throttle Application Panel ($ax[2]$):** Monitors the exact percentage of foot pressure on the gas pedal ($0\%\text{ to }100\%$). Plateaus indicate full-throttle straightline acceleration, floors show heavy braking zones, and exit ramps expose driver tire traction handling.

---

## 🛠️ Technology Stack

* **Frontend Framework:** Streamlit (UI Engine, Multiselect Component Framework, Async Spinners)
* **Data Ingestion & Calculations:** FastF1 API (Timing sheets, telemetry log streams, GPS coordinates)
* **Visualization Layer:** Matplotlib (Shared multi-panel subplots utilizing a unified X-axis tracking distance)
* **Data Management:** Pandas, NumPy, Protocol Buffer/Pickle Caching

---

## 💻 Local Setup & Developer Execution

To clone, set up dependencies, and host this system on your local machine:

```bash
# 1. Clone the repository
git clone [https://github.com/dhanush058/F1_Analytics.git](https://github.com/dhanush058/F1_Analytics.git)
cd F1_Analytics

# 2. Install pinned dependencies
pip install -r requirements.txt

# 3. Launch the local Streamlit development server
streamlit run app.py
