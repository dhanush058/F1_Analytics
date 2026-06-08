# 🏎️ Formula 1 Spatial Telemetry Analyzer (3-Driver Comparison)

[![Streamlit App](https://static.streamlit.io/badge_streamlit.svg)](https://f1analytics-lmfxcoc2smdzhdb4eppdfo.streamlit.app/)

An advanced, interactive data analytics dashboard designed to ingest, normalize, and visualize millisecond-level car telemetry streams from official FIA Formula 1 race weekends. The application supports the **2024 to 2026** grids, allowing users to benchmark up to three drivers simultaneously across deep performance layers.

---

## 💡 The Core Problem & Engineering Strategy

### 1. Spatial Distance Normalization vs. Time Series
Traditional telemetry charts plot performance metrics against clock seconds. In professional motorsports, this format fails during head-to-head comparisons: if one driver brakes earlier into a corner, their entire timeline shifts forward, destroying the ability to visually cross-examine data overlays.

**The Fix:** This dashboard implements a custom data pipeline that resamples and transforms temporal data streams into **Track Distance (Meters)**. By locking all telemetry profiles to identical physical coordinates, it establishes an absolute, apples-to-apples spatial baseline. You can instantly pinpoint exactly which driver carried more speed or applied throttle earlier at any single meter of the circuit.

### 2. Signal Processing & Data Cleaning
Car sensors sample parameters like velocity, engine RPM, and throttle positions at varying high-frequency intervals. When merging datasets for three separate vehicles, this leaves empty intervals and misaligned rows. 
* **Linear Interpolation:** Applied across continuous physical streams (Speed) to mathematically construct smooth, highly precise spatial comparisons.
* **Forward-Filling:** Implemented on discrete step-based streams to handle data dropouts without creating artificial sensor artifacts.

### 3. High-Performance Caching Layer
Querying raw telemetry streams directly from remote cloud APIs involves transferring massive datasets, leading to user wait times of up to 15 seconds. 
* To eliminate this bottleneck, the dashboard deploys a localized caching mechanism (`f1_cache`). 
* After the initial retrieval, data is stored locally, dropping subsequent page load times from **15+ seconds to under 1 second** while completely insulating the application from cloud API rate-limiting crashes.

### 4. Dynamic Season Calendar Pipeline
Instead of relying on rigid, hardcoded track dropdowns, the application dynamically queries the official calendar schedule API based on the user's selected season year. The UI instantly updates to showcase the exact 24-round calendar layout specific to that active F1 season.

---

## 🛠️ Performance Architecture: The 2 Core Telemetry Panels

To optimize mobile and desktop screen real estate while eliminating redundant, low-signal charts (such as binary on/off brake tracking), the analysis is concentrated into two deeply revealing interactive panels:

### Panel 1: Velocity Comparison (Minimum Corner Speed)
Deep V-shaped valleys map the precise breaking zones and corner apexes. 
* **Micro-Analysis:** Easily observe the vertical gradient of the line to evaluate braking deceleration rates. Whichever driver's trace holds the highest position at the absolute nadir of the valley carried the optimal **minimum corner speed** directly through the apex.

### Panel 2: Throttle Application (Exit Traction)
Tracks the exact percentage of pedal input as the car exits a corner.
* **Micro-Analysis:** The steepness of the recovery slope returning to 100% serves as a visual proxy for chassis balance and exit traction. A sharper, more immediate climb indicates a driver who stabilized the platform early and pinned the gas pedal first, maximizing top-end speed down the ensuing straightaway.

---

## 🚀 Local Installation & Deployment

To clone and run this production-ready dashboard locally on your machine, execute the following workflow:

1. Clone the repository down to your local directory:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/YOUR_F1_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_F1_REPO_NAME.git)
   cd YOUR_F1_REPO_NAME
