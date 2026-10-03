# Smart Campus Monitoring Using AI
## Final Project Plan, Architecture, Requirements and Implementation Details

---

## 1. Project Title

**Smart Campus Monitoring Using AI: Real-Time Network Anomaly Detection and Intelligent Monitoring System**

---

## 2. Main Objective

The project will develop a modular AI-based network monitoring system for a simulated Smart Campus network.

The main research contribution is the **improved AI engine**:

**Paper 1 → Baseline → Our Dataset → Preprocessing → Feature Selection → Model Experiments → Optimization → Improved Model → Real-Time Detection**

The monitoring system will use this engine to detect and visualize network anomalies in real time.

---

## 3. Project Goals

1. Develop an improved network anomaly detection model using the provided datasets.
2. Compare the proposed approach with the baseline methodology from Paper 1.
3. Create a Smart Campus network simulator that generates normal traffic and abnormal traffic.
4. Support both random anomaly generation and manual anomaly injection for demonstrations.
5. Build a reusable Python AI engine independent of the GUI.
6. Create two independent monitoring interfaces:
   - Streamlit prototype
   - Flask + React final application
7. Display detected anomalies directly on real-time graphs.
8. Provide risk scoring, alerts, event history and network monitoring.
9. Keep the simulator replaceable so that a real network data source can be connected later.
10. Test the complete system using dataset, ML, simulator, API and real-time tests.

---

# 4. Overall System Architecture

```text
                         SMART CAMPUS
                              |
        +---------------------+---------------------+
        |                     |                     |
   Students/Users       Faculty/Admin          IoT Devices
        |                     |                     |
        +---------------------+---------------------+
                              |
                              v
                   +---------------------+
                   |  NETWORK SIMULATOR  |
                   |                     |
                   | Normal Traffic      |
                   | Random Anomalies    |
                   | Manual Anomalies    |
                   +----------+----------+
                              |
                              v
                   +---------------------+
                   | DATA PREPROCESSOR   |
                   +----------+----------+
                              |
                              v
                   +---------------------+
                   | FEATURE PROCESSING  |
                   +----------+----------+
                              |
                              v
                   +---------------------+
                   |   IMPROVED AI MODEL |
                   |                     |
                   | Anomaly Detection   |
                   | Classification      |
                   +----------+----------+
                              |
                              v
                   +---------------------+
                   |    RISK SCORING     |
                   +----------+----------+
                              |
                 +------------+------------+
                 |                         |
                 v                         v
        +-----------------+       +-----------------+
        |    STREAMLIT    |       |   FLASK API     |
        |   PROTOTYPE     |       |                 |
        +-----------------+       +--------+--------+
                                           |
                                           v
                                  +-----------------+
                                  |     REACT       |
                                  |  FINAL WEB GUI  |
                                  +-----------------+
```

---

# 5. Research Approach

## 5.1 Paper 1 as Baseline

Paper 1 is used as the baseline/reference methodology for network anomaly detection.

The paper uses the SNMP-MIB IP group and evaluates classifiers including:

- Random Forest
- J48
- REP Tree

It also uses feature selection methods such as:

- InfoGain
- ReliefF

The paper reports very high classification accuracy for its experimental setup.

Our project will not simply reproduce the paper. Instead, the Paper 1 methodology will provide a **baseline against which our improved pipeline can be evaluated**.

---

## 5.2 Our Improvement

Our improved pipeline will investigate:

- Dataset analysis
- Data preprocessing
- Missing-value handling
- Duplicate checking
- Constant-feature removal
- Feature selection
- Multiple ML models
- Hyperparameter tuning
- Cross-validation
- Class-imbalance-aware evaluation
- Precision, Recall and F1-score
- Confusion matrix analysis

The final model will only be called "improved" if the experiments provide evidence supporting the improvement.

---

# 6. Dataset Structure

The project currently contains two main dataset groups.

## Dataset 1

`all_data (3).csv`

- Approximately 4,998 records
- 34 input features and one class column
- 8 classes
- Contains network anomaly/attack categories such as:
  - normal
  - tcp-syn
  - slowloris
  - udp-flood
  - icmp-echo
  - httpFlood
  - slowpost
  - bruteForce

This dataset closely matches the dataset structure discussed in Paper 1.

## Dataset 2

`local_A.csv` to `local_D.csv`

Combined:

- Approximately 40,262 records
- 22 input features and one class column
- 9 classes:
  - normal
  - sign_a
  - sign_b
  - sign_c
  - sign_d
  - sign_e
  - sign_f
  - sign_g

These datasets have a different feature structure from the first dataset.

### Important design decision

The datasets should **not be blindly merged** because their feature sets are different.

They will first be analyzed independently and used appropriately in the experimental pipeline.

---

# 7. Engine Architecture

The engine is the most important technical part of the project.

```text
engine/
|
|-- data_preprocessor.py
|-- feature_extraction.py
|-- feature_selection.py
|-- model_training.py
|-- model_evaluation.py
|-- visualize_model_accuracy.py
|-- model_loader.py
|-- anomaly_detector.py
|-- risk_scoring.py
`-- pipeline.py
```

---

# 8. Engine File Responsibilities

## 8.1 data_preprocessor.py

Responsible only for preparing the raw datasets.

Workflow:

```text
Raw Dataset
     |
     v
Load Data
     |
     v
Validate Columns
     |
     v
Check Missing Values
     |
     v
Check Duplicates
     |
     v
Handle Invalid Values
     |
     v
Remove Constant Features
     |
     v
Encode Required Data
     |
     v
Clean Dataset
```

The purpose is to keep dataset preparation separate from model training.

---

## 8.2 feature_extraction.py

Responsible for generating or deriving useful network features when required.

Possible features include:

- Packet rate
- Byte rate
- Connection rate
- Traffic ratios
- Protocol-related features
- Other features derived from the available dataset

Only features supported by the available data will be used.

---

## 8.3 feature_selection.py

Responsible for selecting useful features.

Potential methods:

- InfoGain
- ReliefF
- Mutual Information
- Model-based feature importance

The methods will be tested experimentally rather than assuming one method is automatically better.

---

## 8.4 model_training.py

Responsible for training candidate models.

Potential models include:

- Random Forest
- Extra Trees
- Decision Tree
- Gradient Boosting
- Other suitable models identified during experimentation

The Paper 1 models will provide the baseline.

---

## 8.5 model_evaluation.py

Responsible for evaluating models.

Metrics:

- Accuracy
- Precision
- Recall
- F1-score
- Macro F1
- Weighted F1
- Confusion Matrix

Because the local datasets are highly imbalanced, accuracy will not be used as the only performance measure.

---

## 8.6 visualize_model_accuracy.py

This is a **standalone experimental utility**.

It is not part of the running application pipeline.

Purpose:

- Read model-result data
- Generate accuracy comparison graphs
- Generate Precision/Recall/F1 comparison graphs
- Generate confusion-matrix visualizations where applicable

Workflow:

```text
Model Results
     |
     v
visualize_model_accuracy.py
     |
     +--> Accuracy Graph
     +--> Precision Graph
     +--> Recall Graph
     +--> F1 Graph
     `--> Confusion Matrix
```

It can be run independently whenever experimental results need to be visualized.

It does NOT participate in:

```text
Simulator -> AI Engine -> GUI
```

---

## 8.7 model_loader.py

Loads the final trained model from the `models/` directory.

Example:

```text
models/
`-- anomaly_model.pkl
```

The deployed system loads the trained model instead of retraining it every time.

---

## 8.8 anomaly_detector.py

Responsible for real-time prediction.

Workflow:

```text
Network Record
      |
      v
Preprocessing
      |
      v
Feature Transformation
      |
      v
Trained Model
      |
      v
Prediction
```

Example output:

```json
{
  "prediction": "tcp-syn",
  "is_anomaly": true,
  "confidence": 0.97
}
```

Actual values will be produced by the trained model.

---

## 8.9 risk_scoring.py

Converts detection results into practical monitoring levels.

Possible levels:

```text
NORMAL
LOW
MEDIUM
HIGH
CRITICAL
```

Risk can consider:

- Model confidence
- Traffic intensity
- Attack/anomaly class
- Number of affected connections
- Duration
- Repeated detections

The exact scoring formula will be finalized after model and simulator testing.

---

## 8.10 pipeline.py

Connects the engine components.

```text
Input
  |
  v
Preprocessor
  |
  v
Feature Processing
  |
  v
Feature Selection
  |
  v
Model
  |
  v
Anomaly Detector
  |
  v
Risk Scoring
  |
  v
Standard Output
```

The output format will be standardized so that both Streamlit and Flask can use the same engine.

---

# 9. Network Simulator

The simulator will create a virtual Smart Campus network.

Recommended structure:

```text
simulator/
|
|-- network_simulator.py
|-- campus_entities.py
|-- traffic_generator.py
|-- anomaly_generator.py
`-- simulation_config.py
```

---

# 10. Smart Campus Network Model

The simulator represents:

### Student Network

- Student computers
- Mobile devices
- Student Wi-Fi
- Student web/LMS activity

### Faculty Network

- Faculty computers
- Faculty Wi-Fi
- LMS
- Email
- Web services

### Administration

- Administrative computers
- Database systems
- Management systems

### Computer Labs

- Lab PCs
- Lab servers
- Shared services

### IoT Network

- CCTV
- Temperature sensors
- Smart classroom devices
- Access control
- Smart lighting
- RFID devices

### Campus Services

- DNS server
- Web server
- Database server
- LMS
- Authentication server

---

# 11. Normal Traffic Generation

The simulator should generate behavior-based traffic rather than completely random numbers.

### Student example

```text
Student
   |
   v
DNS Request
   |
   v
Web Request
   |
   v
LMS
   |
   v
Response
```

### Faculty example

```text
Faculty
   |
   v
Authentication
   |
   v
LMS
   |
   v
Email
   |
   v
Web Services
```

### IoT example

```text
Sensor
   |
   v
Periodic Data
   |
   v
IoT Gateway
   |
   v
Campus Server
```

### Lab example

```text
Lab PCs
   |
   v
DNS
   |
   v
Web
   |
   v
Internal Server
```

These activities generate the network features expected by the AI engine.

---

# 12. Network Traffic Records

The simulator can generate records containing fields such as:

```text
timestamp
source
destination
protocol
packet_rate
bytes
connections
duration
port
device_type
network_zone
```

The simulator must produce data in the feature schema required by the trained model.

This makes the simulator replaceable by a future real-world network data collector.

---

# 13. Random Anomaly Generation

The simulator will continuously generate normal traffic and can randomly inject anomalies.

Possible anomaly types include:

### TCP-SYN

Unusually high numbers of connection attempts.

### UDP Flood

Very high UDP packet traffic.

### ICMP Anomaly

Excessive ICMP requests.

### HTTP Flood

High numbers of HTTP requests.

### Slowloris

Many long-running HTTP connections.

### SlowPOST

Slow POST-style traffic.

### Brute Force

Repeated authentication attempts.

The supported anomaly types will be matched to the trained model and available dataset labels.

---

# 14. Manual Anomaly Generation

A manual anomaly mechanism will be included specifically for demonstrations and testing.

Example controls:

```text
+----------------------------------+
|      MANUAL ANOMALY CONTROL      |
+----------------------------------+
|                                  |
| Attack Type:                     |
| [ TCP-SYN              v ]       |
|                                  |
| Intensity:                       |
| [ ========---- ]                |
|                                  |
| Duration:                        |
| [ 10 seconds ]                  |
|                                  |
|       [ START ANOMALY ]          |
|                                  |
+----------------------------------+
```

The user can select:

- Attack type
- Intensity
- Duration

Then click:

**START ANOMALY**

The simulator immediately injects the selected traffic pattern.

---

# 15. Random and Manual Anomalies

```text
                    SIMULATOR
                       |
             +---------+---------+
             |                   |
             v                   v
      Random Generator    Manual Generator
             |                   |
             +---------+---------+
                       |
                       v
                 Traffic Stream
                       |
                       v
                    AI Engine
```

### Random mode

Used for continuous realistic testing.

### Manual mode

Used for:

- PBL demonstration
- Testing specific attacks
- Debugging
- Testing graphs
- Testing alerts
- Demonstrating detection to the evaluator

---

# 16. Real-Time Monitoring

The system will continuously perform:

```text
Traffic
  |
  v
Feature Processing
  |
  v
AI Prediction
  |
  v
Risk Score
  |
  v
Graph
  |
  v
Alert
  |
  v
Event Log
```

Anomalies must appear directly on the real-time graph at their detection timestamp.

Example:

```text
Packet Rate
|
|                              * HIGH
|                             /|\
|                            / | \
|              normal       /  |
|       _______             /   |
|______/       \____________/    \____
|
+--------------------------------------> Time
                       ^
                  AI Detection
```

---

# 17. Streamlit Prototype

Streamlit will be the rapid prototype and testing interface.

## Style

The visual design will be inspired by the provided dashboard reference image.

Style characteristics:

- Dark navy background
- Blue/purple gradient accents
- Rounded cards
- Dark glass-like panels
- Left sidebar
- KPI cards
- Modern charts
- Soft shadows
- Blue/cyan primary accents
- Red/orange/yellow alert colors
- Clean typography
- Futuristic network-monitoring appearance

---

# 18. Streamlit Layout

```text
+---------------------------------------------------------+
| SMART CAMPUS AI MONITOR                    ● LIVE       |
+-------+-------------------------------------------------+
|       |                                                 |
|  HOME | Network Status    Anomalies     Risk           |
|       | +---------+       +-------+    +---------+     |
|  VIEW | | ONLINE  |       |   04  |    |  HIGH   |     |
|       | +---------+       +-------+    +---------+     |
| CHART |                                                 |
|       | REAL-TIME PACKET RATE                           |
| ALERT | +---------------------------------------------+ |
|       | |                         *                   | |
| DEV   | |       /-------\         /|\                 | |
|       | |------/         \-------/ | \------          | |
| SET   | +---------------------------------------------+ |
|       |                                                 |
|       | Network Zones      Recent Anomalies             |
+-------+-------------------------------------------------+
```

The Streamlit application will have its own monitoring logic and UI.

---

# 19. Streamlit Simulation Control

A Simulation page can provide:

```text
SIMULATION CONTROL

Simulation:       [ ON ]

Traffic Mode:     [ Normal + Random ]

Random Anomaly:   [ ON ]

Manual Injection:

Attack:
[ TCP-SYN v ]

Intensity:
[ =======--- ]

Duration:
[ 10 sec ]

[ START ANOMALY ]
```

This makes demonstrations simple and controllable.

---

# 20. Flask + React Final GUI

The final application will use:

```text
React
   |
   v
Flask REST API
   |
   v
Python AI Engine
```

The React interface will be a separate professional monitoring application.

It will share the AI engine and standardized data/API format but will have its own monitoring UI.

---

# 21. React GUI Style

The final GUI will use the same overall visual language as the provided reference:

**Modern Dark Smart-Network Operations Dashboard**

Characteristics:

- Dark navy background
- Purple/blue gradient accents
- Rounded cards
- Left vertical sidebar
- Top status bar
- KPI cards
- Interactive graphs
- Network topology
- Anomaly timeline
- Alert panel
- Campus/network-zone visualization
- Responsive design

---

# 22. React Pages

### Dashboard

Real-time monitoring.

### Network

Campus network overview.

### Anomalies

Anomaly history and details.

### Devices

Campus devices and IoT devices.

### Simulation

Simulator controls and manual anomaly injection.

### Analytics

Historical model and network statistics.

### Settings

System configuration.

---

# 23. Technology Stack

## AI and Data

- Python
- Pandas
- NumPy
- Scikit-learn
- Joblib
- SciPy if required

## Prototype

- Streamlit
- Plotly

## Backend

- Flask
- Flask-CORS
- REST API

## Frontend

- React
- JavaScript
- HTML
- CSS
- Tailwind CSS
- Charting library

## Simulator

- Python
- NumPy
- Pandas
- Controlled random/probability mechanisms

## Testing

- Pytest
- Scikit-learn metrics

## Development

- VS Code
- Git
- GitHub
- Python virtual environment
- Node.js
- npm

---

# 24. Dependencies

Initial `requirements.txt`:

```text
pandas
numpy
scikit-learn
scipy
joblib
flask
flask-cors
streamlit
plotly
pytest
```

Frontend dependencies will include:

```text
react
react-dom
axios
react-router-dom
tailwindcss
```

Exact versions should be fixed after successful installation and testing.

---

# 25. Hardware Requirements

No special hardware is required.

Recommended:

```text
CPU:      Modern 4-core processor
RAM:      16 GB recommended
          8 GB minimum
Storage:  5–10 GB free
OS:       Windows / Linux
Browser:  Chrome / Edge
Python:   3.11+ recommended
```

The project is designed to run on a normal student laptop.

---

# 26. Software Requirements

Required:

- Python
- VS Code
- Node.js
- npm
- Git
- Modern web browser

Optional:

- Cisco Packet Tracer

Cisco Packet Tracer is not required for the core implementation because the Python simulator provides the traffic source.

---

# 27. Cybersecurity Mechanisms

The prototype will include:

### AI anomaly detection

Detect abnormal traffic patterns.

### Attack classification

Identify supported attack/anomaly classes.

### Risk scoring

Convert detection output into practical severity levels.

### Real-time alerts

Display suspicious events immediately.

### Event logging

Store anomaly history.

### Input validation

Reject malformed network records.

### API validation

Validate Flask API requests before passing data to the engine.

### Component separation

Keep the simulator, AI engine, backend and frontend separated.

---

# 28. Testing Strategy

## Dataset Testing

- Missing values
- Duplicate values
- Constant features
- Class distribution
- Invalid values

## ML Testing

- Paper 1 baseline
- Improved models
- Cross-validation
- Hyperparameter tuning
- Multiple evaluation metrics

## Simulator Testing

- Normal traffic
- Random anomalies
- Manual anomalies
- Different campus zones
- Different anomaly types

## Real-Time Testing

- Traffic to graph
- Anomaly to graph marker
- Anomaly to alert
- Anomaly to log

## API Testing

```text
React -> Flask
Flask -> Engine
Engine -> Flask
Flask -> React
```

---

# 29. Expected PBL Demonstration

### Step 1

Open the dashboard.

```text
SYSTEM: ONLINE
Traffic: NORMAL
Anomalies: 0
```

### Step 2

Start the simulator.

Normal campus traffic appears.

### Step 3

Select:

**TCP-SYN**

and click:

**START ANOMALY**

### Step 4

Traffic increases on the live graph.

### Step 5

The AI engine detects the abnormal pattern.

### Step 6

The graph displays an anomaly marker.

### Step 7

The dashboard displays:

```text
Attack: TCP-SYN
Risk: HIGH
Time: current detection time
```

### Step 8

Stop the anomaly.

Traffic returns toward normal.

This demonstrates the complete:

**Simulation → AI Detection → Risk → Visualization → Alert**

workflow.

---

# 30. Complete Project Folder Structure

```text
smart-campus-monitor/
|
|-- engine/
|   |
|   |-- data_preprocessor.py
|   |-- feature_extraction.py
|   |-- feature_selection.py
|   |-- model_training.py
|   |-- model_evaluation.py
|   |-- visualize_model_accuracy.py   # standalone utility
|   |-- model_loader.py
|   |-- anomaly_detector.py
|   |-- risk_scoring.py
|   `-- pipeline.py
|
|-- simulator/
|   |
|   |-- network_simulator.py
|   |-- campus_entities.py
|   |-- traffic_generator.py
|   |-- anomaly_generator.py
|   `-- simulation_config.py
|
|-- models/
|   `-- anomaly_model.pkl
|
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- results/
|
|-- streamlit/
|   `-- app.py
|
|-- backend/
|   |-- app.py
|   |-- routes/
|   `-- services/
|
|-- frontend/
|   |-- src/
|   |-- public/
|   |-- package.json
|   `-- ...
|
|-- tests/
|   |-- test_preprocessor.py
|   |-- test_engine.py
|   |-- test_simulator.py
|   `-- test_api.py
|
|-- requirements.txt
|-- README.md
`-- .gitignore
```

---

# 31. Activity 3 Requirement Mapping

| Activity 3 Requirement | Our Project Implementation |
|---|---|
| Problem Identification | Difficulty of real-time anomaly detection in complex Smart Campus networks |
| Requirement Analysis | Real-time traffic, AI detection, alerts, risk scoring and visualization |
| Network Architecture | Student, Faculty, Admin, Labs, Wi-Fi, IoT and Campus Services |
| AI Integration | Improved ML-based anomaly detection engine |
| IoT Architecture | Simulated IoT devices and traffic |
| Cybersecurity Mechanisms | Anomaly detection, classification, risk scoring, alerts, logging and validation |
| Prototype Implementation | Python + Simulator + Streamlit + Flask + React |
| System Workflow | Traffic → Preprocessing → Features → AI → Risk → Dashboard |
| Testing | Dataset, ML, simulator, API and real-time testing |
| Expected Outcomes | Improved detection and real-time Smart Campus monitoring |

---

# 32. Final Research and System Concept

```text
                         OUR RESEARCH
                              |
                 +------------+------------+
                 |                         |
             PAPER 1                   OUR DATA
             Baseline                     |
                 |                         |
                 +------------+------------+
                              |
                              v
                    IMPROVED AI ENGINE
                              |
                              v
                       SAVED ML MODEL
                              |
                +-------------+-------------+
                |                           |
                v                           v
         SMART CAMPUS                 RANDOM / MANUAL
           SIMULATOR                   ANOMALIES
                |                           |
                +-------------+-------------+
                              |
                              v
                       REAL-TIME ENGINE
                              |
                 +------------+------------+
                 |                         |
                 v                         v
            STREAMLIT                FLASK + REACT
            PROTOTYPE                FINAL SYSTEM
                 |                         |
                 v                         v
          Prototype UI              Professional UI
                 |                         |
                 +------------+------------+
                              |
                              v
                     SMART CAMPUS
                     AI MONITORING
```

---

# 33. Core Project Statement

The project can be summarized as:

> **A modular Smart Campus network monitoring system that uses an improved machine-learning-based anomaly detection engine, a configurable campus network simulator, real-time risk assessment, and modern monitoring dashboards. The system supports both automatically generated and manually injected anomalies and is designed so that the simulator can later be replaced by a real network data source.**

The **AI engine is the main research component**, while the simulator, Streamlit application, and Flask + React application provide the experimental, demonstration, and deployment layers.
