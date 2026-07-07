# 🏎️ Formula 1 Advanced Spatial Telemetry Analytics & Performance Platform

An enterprise-grade, data-decoupled analytics system designed to ingest, transform, clean, and visualize high-frequency vehicle telemetry captured during official FIA Formula 1 World Championship sessions.

The platform addresses a critical engineering problem in motorsport telemetry: converting asynchronous, non-aligned, time-stamped vehicle logs into a standardized spatial track coordinate system. This spatial alignment allows engineers, race strategists, and team principals to perform precise driver style comparisons, overlay throttle application sequences, and pinpoint exact lap-time deltas down to the meter.

🔗 **Live Production Deployment URL:** https://f1analytics-lmfxcoc2smdzhdb4eppdfo.streamlit.app/

---

## 🚀 Business Impact & Professional Analytics Metrics

* **Data Architecture Optimization:** Transitioned the infrastructure from a volatile, live stream-polling model to an isolated, local warehouse design. This decoupled web rendering from external network bottlenecks, eliminating API timeouts, latency spikes, and rate-limiting blocks.
  
* **Spatial Transformation Integration:** Engineered a custom telemetry-alignment engine that converts raw vehicle velocity values into meters per second, tracks the precise millisecond deltas between sensor frames, and computes rolling numerical integration to construct an absolute distance coordinate system. This eliminates time-skew anomalies and improves multi-car trace alignment.
  
* **Stakeholder-Centric Reporting:** Deployed a deliberate, dual-tier reporting layout that translates complex vehicle metrics into clear, conversational racing summaries for non-technical business stakeholders and management, while retaining strict data-lineage trackers, pipeline frequency metrics, and failure logs for engineering leads.

---

## 🏗️ End-to-End System Architecture & Data Pipeline
Pipeline Mechanics: 
1. **FileSystem Data Ingestion**: Rather than executing client-side web requests across unstable public APIs, the system reads performance-optimized JSON files staged directly from the local repository directory.
   
2. **Dynamic Fleet Parsing**: The ingestion module inspects the telemetry payload structure to extract active driver numbers and sensor channels programmatically without relying on hardcoded structures.

3. **Velocity-Time Calculus**: Because ECU data streams log points against timestamps, the app calculates the exact millisecond slices between packet transmissions. It scales vehicle speeds to meters per second and executes a cumulative sum integration (cumsum) to project telemetry over spatial track location instead of raw elapsed time.

4. **Defensive Exception Handlers**: If a future or cancelled event is selected, a pipeline exception shield catches the blank dataset, serves a stable baseline calibration curve, and displays a data integrity alert.

## 📊 Analytical Visualization FrameworkThe dashboard outputs an aligned, synchronized multi-axis Plotly visualization window to evaluate driver inputs and vehicle capabilities simultaneously:

The dashboard outputs a synchronized, multi-axis visualization window to evaluate driver inputs and vehicle capabilities simultaneously:

- Time Delta & Spatial Gap: Graphs the cumulative time advantage of the primary driver against the reference. Negative values (Green) highlight where the driver is gaining time, while the slope of the curve identifies specific track sections where the primary driver outperforms or underperforms the benchmark.

- Velocity Profiles: Graphs absolute vehicle velocity values on the primary vertical axis. This surfaces key performance differentiators including minimum corner apex speeds, deceleration efficiency under braking, and aerodynamic drag profiles on straights.

- Throttle Input Matrix: Graphs throttle modulation percentages across the exact spatial baseline of the circuit. This maps critical driver inputs: where a driver initiates a lift-and-coast sequence, commits to full throttle on exit, and performs mid-corner pedal adjustments.


## 💡 Technology Stack References: 

- Dashboard Application Interface: Streamlit Production Server Framework

- Telemetry Data Sourcing Engine: OpenF1 Community REST Registry (Pre-Staged Locally)

- Numerical Formulations: NumPy Multi-Dimensional Matrix Mathematics

- Structured Data Transformations: Pandas Vector DataFrames

- Vector Graphics Canvas: Plotly Multilayer Subplots Canvas

## 🛠️ Installation, Local Testing, & Engineering Replication
This repository maintains a fully reproducible infrastructure layout to satisfy corporate governance checks, regression tests, and local developer environment setups.

1. Environment Setup
   
```bash
git clone git@github.com:dhanush058/F1_Analytics.git
cd F1_Analytics
pip install -r requirements.txt
```
2. Local Execution
```bash
streamlit run app.py
```
