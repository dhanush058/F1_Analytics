# 🏎️ Formula 1 Advanced Spatial Telemetry Analytics & Performance Platform

An enterprise-grade, data-decoupled analytics system designed to ingest, transform, clean, and visualize high-frequency vehicle telemetry arrays captured during official FIA Formula 1 World Championship sessions. 

The platform addresses a critical engineering problem in motorsport telemetry: converting asynchronous, non-aligned, time-stamped vehicle logs into a standardized spatial track coordinate system. This spatial alignment allows engineers, race strategists, and team principals to perform precise micro-behavioral driver style comparisons, overlay throttle application sequences, and pinpoint exact lap-time deltas down to the meter across any circuit configuration on the calendar.

🔗 **Live Production Deployment URL:** [https://f1analytics-lmfxcoc2smdzhdb4eppdfo.streamlit.app/](https://f1analytics-lmfxcoc2smdzhdb4eppdfo.streamlit.app/)

---

## 🚀 Business Impact & Professional Analytics Metrics

* **Data Architecture Optimization:** Transitioned the core infrastructure from a volatile, live client-side REST stream-polling model to an isolated, immutable local repository data warehouse design. This structural change decoupled web rendering from external network bottlenecks, eliminating API connection timeouts, network latency spikes, and public platform rate-limiting blocks by **100%**.
* **Spatial Transformation Integration:** Engineered a custom telemetry-alignment engine that converts raw vehicle velocity values into meters per second ($km/h \div 3.6$), tracks the precise millisecond deltas ($\Delta t$) between consecutive high-frequency sensor frames (~3.7 Hz), and computes a rolling numerical integration to construct an absolute distance coordinate system. This step eliminated time-skew anomalies and improved multi-car overlay trace alignment accuracy across different track layouts.
* **Stakeholder-Centric Reporting:** Deployed a deliberate, dual-tier reporting layout that translates complex vehicle metrics into clear, conversational racing summaries for non-technical business stakeholders and management, while retaining strict data-lineage trackers, pipeline frequency metrics, and failure logs for engineering leads.

---

## 🏗️ End-to-End System Architecture & Data Pipeline
┌────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
│  Local JSON Warehouse  │ ───> │ Streamlit Runtime Engine  │ ───> │ Spatial Vector Calculus   │
│  (Data Staging Arrays) │      │  (UI Render & Handlers)   │      │  (Time-Distance Mapping)  │
└────────────────────────┘      └───────────────────────────┘      └───────────────────────────┘
│
▼
┌───────────────────────────┐
│ Plotly Subplots Canvas    │
│  (Synchronized Analysis)  │
└───────────────────────────┘

### Detailed Pipeline Mechanics:
1. **User Selection & Ingestion Scopes:** The user configures the target season (2024, 2025, or 2026) and selects a race from the comprehensive 24-round championship calendar dropdown menu in the sidebar.
2. **FileSystem Data Ingestion:** Rather than executing client-side web requests across unstable, rate-limited public APIs that throttle free data queries during live traffic hours, the system reads pre-staged, performance-optimized JSON files directly from the repository's secure local `data_warehouse/` directory.
3. **Dynamic Fleet Parsing:** The ingestion module programmatically inspects the telemetry payload structure to extract active driver numbers, team sensor channels, and grid metadata without relying on static, hardcoded dictionary structures.
4. **Velocity-Time Calculus Integration:** Because raw Electronic Control Unit (ECU) data streams only log points against timestamp intervals (`date`), the app calculates the exact $\Delta t$ millisecond slices between packet transmissions. It scales vehicle speeds to meters per second and executes a cumulative numerical sum integration (`cumsum()`) to project telemetry values uniformly over spatial track location instead of raw elapsed time.
5. **Defensive Structural Exception Handlers:** If an un-raced future weekend or an officially cancelled event (such as the cancelled 2026 Bahrain or Saudi Arabian rounds) is selected, a pipeline exception shield catches the blank dataset, serves a stable baseline calibration curve, and displays a prominent data integrity alert banner to the user.

---

## 📊 Analytical Visualization Framework

The dashboard outputs an aligned, synchronized multi-axis Plotly visualization window to evaluate driver inputs and vehicle capabilities simultaneously:

### 1. Velocity Profiles (Speed Trace Curves)
* Graphs absolute vehicle velocity values on the primary vertical axis using contrasting solid lines (Cyan for Driver A, Magenta for Driver B).
* Instantly surfaces key performance differentiators: minimum corner apex speeds, deceleration efficiency under braking, aerodynamic drag profiles on straightaways, and hybrid power deployment drop-offs.

### 2. Throttle Input Matrix
* Graphs driver throttle modulation percentages ($0\% - 100\%$) across the exact spatial baseline of the circuit using synchronized dashed traces.
* Maps critical driver inputs: where a driver initiates a corner lift-and-coast sequence, who commits to full throttle application earliest on corner exits, and who experiences wheelspin snaps requiring mid-corner pedal adjustments.

---

## 💡 Technology Stack References

* **Dashboard Application Interface:** Streamlit Production Server Framework
* **Telemetry Data Sourcing Engine:** OpenF1 Community REST Registry (Pre-Staged Locally)
* **Numerical Formulations:** NumPy Multi-Dimensional Matrix Mathematics
* **Structured Data Transformations:** Pandas Vector DataFrames
* **Vector Graphics Canvas:** Plotly Multilayer Subplots Canvas

---

## 🛠️ Installation, Local Testing, & Engineering Replication

This repository maintains a fully reproducible infrastructure layout to satisfy corporate governance checks, regression tests, and local developer environment setups.

### 1. Environment Cloning
Pull the code repository down to your local developer machine:
```bash
git clone git@github.com:dhanush058/F1_Analytics.git
cd F1_Analytics

To guarantee **100% server uptime** and protect the user interface from crashing when under high recruitment traffic or public web server stress, the platform utilizes a completely decoupled local warehouse architecture:
