# OpenDSS Distribution System Simulator

A Python-based simulation tool for analyzing and managing power distribution systems using OpenDSS. This tool provides a RESTful API interface for running power flow analyses, managing transformer loading, and implementing Demand Flexibility Programs (DFP) in distribution networks.

## New Features

- **Postman Collection**: A comprehensive Postman collection (`DEG_APIs.postman_collection`) is now available for easy API testing and integration.
- **Critical System Monitoring**: Added `critical.txt` in the `results_api` directory to track critical system events and alerts.
- **Enhanced Logging**: Improved logging system for better tracking of system operations and DFP activities.
- **API Documentation**: Complete API reference with request/response examples for all endpoints.

## Features

- **Power System Analysis**
  - Load and analyze IEEE test feeder models (specifically IEEE 123-Bus)
  - Real-time power flow simulation
  - Power flow analysis with detailed reporting
  - Real-time monitoring of system parameters
  - Voltage profile analysis

- **Demand Flexibility Programs (DFP)**
  - Create and manage multiple DFPs
  - Subscribe/unsubscribe buses to DFPs
  - Dynamic load management based on DFP rules
  - Real-time DFP execution and monitoring

- **Load Management**
  - Automated transformer loading management
  - Dynamic load adjustment by neighborhood
  - Individual household load control
  - Device-level load management

- **Generation Control**
  - Distributed generation integration
  - Automatic generation curtailment
  - Power factor correction

- **API & Integration**
  - RESTful API for system interaction
  - Comprehensive logging and monitoring
  - JSON-based data exchange
  - Integration with external systems

## Prerequisites

- Python 3.8 or higher
- OpenDSS (included with opendssdirect.py)
- pip (Python package manager)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd FIDE-Project-5---The-Beckn-World-Engine
   git checkout OpenDSS
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Linux/MacOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the API server:
   ```bash
   python run_simulator_data.py
   ```
   The API will be available at `http://localhost:5000`

## Usage

### Running the Simulation

1. Start the simulation server:
   ```bash
   python run_simulator_data.py
   ```

2. The server will start on `http://localhost:5000` by default.

## API Testing with Postman

We provide a Postman collection (`DEG_APIs.postman_collection`) to help you test and integrate with the API. Here's how to use it:

1. **Import the Collection**:
   - Open Postman
   - Click "Import" and select the `DEG_APIs.postman_collection` file
   - The collection will appear in your Postman workspace

2. **Using the Collection**:
   - The collection is organized by functionality (Power Flow, DFP, Load Management, etc.)
   - Each endpoint includes example requests with pre-filled values
   - Environment variables are used for common values like `base_url`

## API Documentation

### Power Flow and System Management

#### 1. Run Simulation
- **Endpoint**: `POST /run_simulation`
- **Description**: Runs a new power flow simulation with the current system state
- **Response**: Returns the latest system state
- **Example (PowerShell)**:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:5000/run_simulation" -Method Post -ContentType "application/json"
  ```

#### 2. Get System State
- **Endpoint**: `GET /get_state`
- **Description**: Retrieves the current system state
- **Response**: Returns the current system state including bus data and power flow results

#### 3. Modify Load in a Neighborhood
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

### 4. Modify Individual Household Load
- **Endpoint**: `POST /modify_load_household`
- **Description**: Adjusts the load for a specific household
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "load_name": "Load_1",
    "new_kw": 5.0,
    "new_kvar": 1.0
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      load_name = "Load_1"
      new_kw = 5.0
      new_kvar = 1.0
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/modify_load_household" -Method Post -Body $body -ContentType "application/json"
  ```

### 5. Add Generator
- **Endpoint**: `POST /add_generator`
- **Description**: Adds a new generator to a bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "kv": 0.48,
    "kw": 50.0,
    "kvar": 10.0,
    "model": 1,
    "vmin_pu": 0.9,
    "vmax_pu": 1.1
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      kv = 0.48
      kw = 50.0
      kvar = 10.0
      model = 1
      vmin_pu = 0.9
      vmax_pu = 1.1
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/add_generator" -Method Post -Body $body -ContentType "application/json"
  ```

### 6. Add Device to Bus
- **Endpoint**: `POST /add_device`
- **Description**: Adds a new device to a bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "device_name": "EV_Charger_1",
    "kw": 7.2,
    "kvar": 1.4,
    "pf": 0.98
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      device_name = "EV_Charger_1"
      kw = 7.2
      kvar = 1.4
      pf = 0.98
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/add_device" -Method Post -Body $body -ContentType "application/json"
  ```

### 7. Disconnect Device from Bus
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

## Demand Flexibility Program (DFP) Endpoints

### 8. Register New DFP
- **Endpoint**: `POST /register_dfp`
- **Description**: Registers a new Demand Flexibility Program
- **Request Body**:
  ```json
  {
    "name": "peak_shaving",
    "min_power_kw": 100.0,
    "target_pf": 0.95
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
      min_power_kw = 100.0
      target_pf = 0.95
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/register_dfp" -Method Post -Body $body -ContentType "application/json"
  ```

### 9. Update DFP Parameters
- **Endpoint**: `PUT /update_dfp`
- **Description**: Updates an existing DFP's parameters
- **Request Body**:
  ```json
  {
    "name": "peak_shaving",
    "min_power_kw": 120.0,
    "target_pf": 0.98
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
      min_power_kw = 120.0
      target_pf = 0.98
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/update_dfp" -Method Put -Body $body -ContentType "application/json"
  ```

### 10. Delete DFP
- **Endpoint**: `DELETE /delete_dfp`
- **Description**: Removes a DFP and cleans up subscriptions
- **Request Body**:
  ```json
  {
    "name": "peak_shaving"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/delete_dfp" -Method Delete -Body $body -ContentType "application/json"
  ```

### 11. Subscribe Bus to DFP
- **Endpoint**: `POST /subscribe_dfp`
- **Description**: Subscribes a bus to a DFP
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "dfp_name": "peak_shaving"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      dfp_name = "peak_shaving"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/subscribe_dfp" -Method Post -Body $body -ContentType "application/json"
  ```

### 12. Unsubscribe Bus from DFP
- **Endpoint**: `POST /unsubscribe_dfp`
- **Description**: Removes a bus from a DFP
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "dfp_name": "peak_shaving"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      dfp_name = "peak_shaving"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/unsubscribe_dfp" -Method Post -Body $body -ContentType "application/json"
  ```

### 13. Modify High-Wattage Devices in Bus
- **Endpoint**: `POST /modify_devices_in_bus`
- **Description**: Reduces load for high-wattage devices on a specific bus
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "power_threshold_kw": 5.0,
    "reduction_factor": 0.7
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      power_threshold_kw = 5.0
      reduction_factor = 0.7
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/modify_devices_in_bus" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "power_threshold_kw": 5.0, "reduction_factor": 0.7}' \
       http://localhost:5000/modify_devices_in_bus
  ```

### 14. Execute DFP Rules
- **Endpoint**: `POST /execute_dfp`
- **Description**: Executes DFP rules on all subscribed buses
- **Request Body**:
  ```json
  {
    "dfp_name": "peak_shaving"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      dfp_name = "peak_shaving"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/execute_dfp" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"dfp_name": "peak_shaving"}' \
       http://localhost:5000/execute_dfp
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

### 6. DFP Management

#### 6.1 Register a New DFP
- **Endpoint**: `POST /register_dfp`
- **Description**: Registers a new Demand Flexibility Program
- **Request Body**:
  ```json
  {
    "name": "peak_shaving",
    "min_power_kw": 100.0,
    "target_pf": 0.95
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
      min_power_kw = 100.0
      target_pf = 0.95
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/register_dfp" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"name": "peak_shaving", "min_power_kw": 100.0, "target_pf": 0.95}' \
       http://localhost:5000/register_dfp
  ```

#### 6.2 Update DFP Parameters
- **Endpoint**: `PUT /update_dfp`
- **Description**: Updates an existing DFP's parameters
- **Request Body**:
  ```json
  {
    "name": "peak_shaving",
    "min_power_kw": 120.0,
    "target_pf": 0.98
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
      min_power_kw = 120.0
      target_pf = 0.98
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/update_dfp" -Method Put -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X PUT -H "Content-Type: application/json" \
       -d '{"name": "peak_shaving", "min_power_kw": 120.0, "target_pf": 0.98}' \
       http://localhost:5000/update_dfp
  ```

#### 6.3 Delete a DFP
- **Endpoint**: `DELETE /delete_dfp`
- **Description**: Removes a DFP and cleans up subscriptions
- **Request Body**:
  ```json
  {
    "name": "peak_shaving"
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      name = "peak_shaving"
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/delete_dfp" -Method Delete -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X DELETE -H "Content-Type: application/json" \
       -d '{"name": "peak_shaving"}' \
       http://localhost:5000/delete_dfp
  ```

#### 6.4 Subscribe Bus to DFP
- **Endpoint**: `POST /subscribe_dfp`
- **Description**: Subscribes a bus to a DFP
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "dfp_number": 1
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      dfp_number = 1
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/subscribe_dfp" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "dfp_number": 1}' \
       http://localhost:5000/subscribe_dfp
  ```

#### 6.5 Unsubscribe Bus from DFP
- **Endpoint**: `POST /unsubscribe_dfp`
- **Description**: Removes a bus from a DFP
- **Request Body**:
  ```json
  {
    "bus_name": "1",
    "dfp_number": 1
  }
  ```
- **Example (PowerShell)**:
  ```powershell
  $body = @{
      bus_name = "1"
      dfp_number = 1
  } | ConvertTo-Json
  Invoke-RestMethod -Uri "http://localhost:5000/unsubscribe_dfp" -Method Post -Body $body -ContentType "application/json"
  ```
- **Example (Linux)**:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
       -d '{"bus_name": "1", "dfp_number": 1}' \
       http://localhost:5000/unsubscribe_dfp
  ```

## Output Files

The following files are generated in the `results_api` directory:

- `latest_api_results.txt` - Detailed results from the most recent simulation run, including:
  - Power flow convergence status
  - Total circuit power (kW)
  - Total losses (kW)
  - Voltage profile statistics
  - Detailed bus information

- `management_log.txt` - Comprehensive log of all system management activities:
  - Load modifications
  - Generator operations
  - Device connections/disconnections
  - System state changes
  - Timestamped actions

- `dfp_registry.txt` - Current registry of all Demand Flexibility Programs:
  - DFP names and indices
  - Minimum power requirements (kW)
  - Target power factors
  - Registration timestamps
  - Active subscriptions

- `dfps_logs.txt` - Historical log of all DFP-related activities:
  - DFP creation and updates
  - Bus subscriptions/unsubscriptions
  - Rule executions
  - System responses to DFP actions

## Model Configuration

### IEEE 123-Bus Model

The system is pre-configured with the IEEE 123-Bus test feeder model. The file `IEEE_123_Bus_G_neighbourhoods.py` contains the specific configuration for this model, including:

1. **Neighborhood Definitions**:
   - Each neighborhood is defined by a pincode (numeric identifier)
   - Format: `pincode: [list_of_buses]`
   - Example:
     ```python
     NEIGHBORHOOD_DATA = {
         1: ["1", "3", "4", "6"],
         2: ["24", "25", "26", "27"],
         # ... more neighborhoods
     }
     ```

2. **Transformer Mappings**:
   - Maps pincodes to their respective transformer buses
   - Format: `pincode: "transformer_bus_name"`
   - Example:
     ```python
     TRANSFORMER_DATA = {
         1: "1",
         2: "24",
         # ... more transformers
     }
     ```

### Using Other Models

To use this system with a different OpenDSS model, you'll need to:

1. Update the `NEIGHBORHOOD_DATA` dictionary with your area's pincode-to-bus mappings
2. Update the `TRANSFORMER_DATA` dictionary to map pincodes to their respective transformer buses
3. Ensure your OpenDSS model files are properly configured in the `Test_Systems` directory
4. Update the main circuit file path in your code if different from the default

## Project Structure

```
opendss_testing/
│
├── main.py                    # Core OpenDSS circuit management and simulation logic
│   ├── OpenDSSCircuit class   # Main class handling circuit operations
│   ├── Load management        # Functions for load control and adjustment
│   ├── Generator control      # Distributed generation management
│   └── DFP implementation    # Demand Flexibility Program logic
│
├── run_simulator_data.py      # Flask API server and simulation controller
│   ├── API endpoints         # All REST API route handlers
│   ├── Request validation    # Input validation for API calls
│   └── Response formatting   # Standardized API responses
│
├── Test_Systems/              # Contains test feeder models
│   └── IEEE_123_Bus-G/        # IEEE 123-Bus test feeder (sample model)
│       ├── Master.DSS         # Master OpenDSS file
│       ├── BusCoords.dss      # Bus coordinates
│       ├── BusVoltageBases.DSS # Voltage base definitions
│       ├── EnergyMeter.DSS    # Energy meter configurations
│       ├── Line.DSS           # Line definitions
│       ├── LineCode.DSS       # Line code definitions
│       ├── LoadShape.DSS      # Load shape definitions
│       ├── RegControl.DSS     # Regulator control settings
│       ├── Spectrum.DSS       # Harmonic spectrum data
│       ├── TCC_Curve.DSS      # Time-current characteristic curves
│       ├── Transformer.DSS    # Transformer definitions
│       ├── Vsource.dss        # Voltage source definitions
│       └── feeder/            # Additional feeder components
│           ├── Branches.dss   # Branch definitions
│           ├── Capacitors.dss # Capacitor banks
│           ├── Loads.dss      # Load definitions
│           └── Transformers.dss # Transformer configurations
│
└── results_api/               # Directory for simulation results and logs
    ├── latest_api_results.txt  # Latest simulation results in text format
    ├── management_log.txt      # Log of all management actions and decisions
    ├── dfp_registry.txt       # Current DFP configurations and parameters
    ├── dfps_logs.txt          # Historical log of all DFP-related activities
    └── critical.txt           # Tracks critical system events and alerts
