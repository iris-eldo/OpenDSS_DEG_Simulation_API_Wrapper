# OpenDSS Distribution System Simulator

A Python-based simulation tool for analyzing and managing power distribution systems using OpenDSS. This tool provides a simplified interface for running power flow analyses and managing transformer loading in distribution networks.

## Features

- Load and analyze IEEE test feeder models (specifically IEEE 123-Bus)
- Automated transformer loading management
- Power flow analysis with detailed reporting
- REST API interface for integration with other systems
- Real-time monitoring of system parameters

## Prerequisites

- Python 3.8 or higher
- OpenDSS (included with opendssdirect.py)

## Installation

1. Clone this repository
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Simulation

1. Start the simulation server:
   ```bash
   python run_simulator_data.py
   ```

2. The server will start on `http://localhost:5000` by default.

## API Endpoints

### 1. Modify Load in a Neighborhood
- **Endpoint**: `POST /modify_load_neighbourhood`
- **Description**: Adjusts the load factor for all loads in a specific neighborhood
- **Request Body**:
  ```json
  {
    "neighbourhood": 1,
    "factor": 0.8
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      neighbourhood = 1
      factor = 0.8
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/modify_load_neighbourhood" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"neighbourhood": 1, "factor": 0.8}' \
       http://localhost:5000/modify_load_neighbourhood
  ```

### 2. Modify Load for a Specific Household
- **Endpoint**: `POST /modify_load_household`
- **Description**: Adjusts the load factor for a specific household/bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "factor": 0.9
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      factor = 0.9
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/modify_load_household" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "factor": 0.9}' \
       http://localhost:5000/modify_load_household
  ```

### 3. Add Generator to a Bus
- **Endpoint**: `POST /add_generator`
- **Description**: Adds a generator to a specified bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "kw": 100,
    "phases": 3
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      kw = 100
      phases = 3
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/add_generator" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "kw": 100, "phases": 3}' \
       http://localhost:5000/add_generator
  ```

### 4. Add Device to a Bus
- **Endpoint**: `POST /add_device`
- **Description**: Adds a load device to a specified bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "device_name": "EV_Charger_1",
    "kw": 7.5,
    "phases": 1
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      device_name = "EV_Charger_1"
      kw = 7.5
      phases = 1
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/add_device" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "device_name": "EV_Charger_1", "kw": 7.5, "phases": 1}' \
       http://localhost:5000/add_device
  ```

### 5. Disconnect Device from Bus
- **Endpoint**: `POST /disconnect_device`
- **Description**: Removes a device from a bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "device_name": "EV_Charger_1"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      device_name = "EV_Charger_1"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/disconnect_device" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "device_name": "EV_Charger_1"}' \
       http://localhost:5000/disconnect_device
  ```

## Project Structure

```
opendss_testing/
│
├── main.py                    # Core OpenDSS circuit management and simulation logic
├── run_simulator_data.py      # Flask API server and simulation controller
├── IEEE_123_Bus_G_neighbourhoods.py  # Configuration for IEEE 123-Bus test feeder
├── requirements.txt           # Python dependencies
├── README.md                  # This documentation file
│
├── Test_Systems/              # OpenDSS model files
│   └── IEEE_123_Bus-G/
│       ├── Master.dss         # Main OpenDSS circuit definition
│       ├── BusCoords.dat      # Bus coordinate data
│       ├── IEEE123_BusXY.csv  # Bus location data
│       ├── IEEE123_EnergyMeters.dss  # Energy meter definitions
│       ├── IEEE123_LineCodes.dss     # Line code definitions
│       ├── IEEE123_Lines.dss         # Line segment definitions
│       ├── IEEE123_LoadShapes.dss    # Load shape definitions
│       ├── IEEE123_Loads.dss         # Load definitions
│       ├── IEEE123_Regulators.dss    # Voltage regulator definitions
│       ├── IEEE123_Sections.dss      # Section definitions
│       ├── IEEE123_SwtControl.dss    # Switch control definitions
│       └── IEEE123_YardCables.dss    # Cable definitions
│
└── results_api/               # Directory for storing simulation results
    └── latest_api_results.txt  # Latest simulation results in text format
```

