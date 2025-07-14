# OpenDSS Distribution System Simulator

A Python-based simulation tool for analyzing and managing power distribution systems using OpenDSS. This tool provides a RESTful API interface for running power flow analyses, managing transformer loading, and implementing Demand Flexibility Programs (DFP) in distribution networks.

## Project Structure

```
opendss_testing2/
├── api/                     # API route handlers
│   ├── dashboard_routes.py  # Dashboard related endpoints
│   ├── user_routes.py       # User management endpoints
│   └── utility_routes.py    # Utility functions and endpoints
├── results_api/             # Simulation results and logs
│   └── critical.txt         # Critical system events and alerts
├── DEG_APIs.postman_collection  # Postman collection for API testing
├── main.py                  # Main application entry point
├── run.py                   # Application runner
└── utils.py                 # Utility functions
```

## New Features

- **Unified Node Concept**: Simplified terminology - all endpoints now use 'node' instead of 'household', 'bus', or 'node' interchangeably
- **Postman Collection**: A comprehensive Postman collection (`DEG_APIs.postman_collection`) for easy API testing and integration
- **Critical System Monitoring**: Added `critical.txt` in the `results_api` directory to track critical system events and alerts
- **Enhanced Logging**: Improved logging system for better tracking of system operations and DFP activities
- **API Documentation**: Complete API reference with request/response examples for all endpoints
- **Storage Integration**: Added support for connecting and managing storage devices in the grid

## Features

- **Power System Analysis**
  - Load and analyze IEEE test feeder models (specifically IEEE 123-Node)
  - Real-time power flow simulation
  - Power flow analysis with detailed reporting
  - Real-time monitoring of system parameters
  - Voltage profile analysis

- **Demand Flexibility Programs (DFP)**
  - Create and manage multiple DFPs
  - Subscribe/unsubscribe nodes to DFPs
  - Dynamic load management based on DFP rules
  - Real-time DFP execution and monitoring

- **Load Management**
  - Automated transformer loading management
  - Dynamic load adjustment by node
  - Individual node load control
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
   cd opendss_testing
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

### Node Management

- **GET /get_node_data**
  - Retrieves complete grid state with all node information
  - Example: `GET http://localhost:5000/get_node_data`

- **POST /get_node_details**
  - Gets detailed information about a specific node
  - Example: `POST http://localhost:5000/get_node_details`
  - Body: `{"bus_name": "1"}`

### Load Management

- **POST /modify_load_neighbourhood**
  - Adjusts load for all nodes in a neighborhood by a factor
  - Example: `POST http://localhost:5000/modify_load_neighbourhood`
  - Body: `{"neighbourhood": 1, "factor": 0.5}`

- **POST /modify_load_node**
  - Modifies load for a specific node
  - Example: `POST http://localhost:5000/modify_load_node`
  - Body: `{"bus_name": "2", "factor": 0.9}`

### Generation Control

- **POST /add_generator**
  - Adds a new generator to a node
  - Example: `POST http://localhost:5000/add_generator`
  - Body: `{"bus_name": "1", "phases": 3, "kw": 40}`

- **POST /add_device**
  - Adds a new device to a node
  - Example: `POST http://localhost:5000/add_device`
  - Body: `{"bus_name": "1", "device_name": "television", "phases": 1, "kw": 50}`

### Demand Flexibility Programs (DFP)

- **GET /get_dfp_details**
  - Retrieves information about all DFPs
  - Example: `GET http://localhost:5000/get_dfp_details`

- **POST /register_dfp**
  - Creates a new Demand Flexibility Program
  - Example: `POST http://localhost:5000/register_dfp`
  - Body: `{"name": "Peak Power", "description": "Peak shaving program", "min_power_kw": 80.0, "target_pf": 0.7}`

- **POST /subscribe_dfp**
  - Subscribes a node to a DFP
  - Example: `POST http://localhost:5000/subscribe_dfp`
  - Body: `{"bus_name": "1", "dfp_name": "Peak Power"}`

- **POST /send_dfp_to_neighbourhood**
  - Sends DFP subscription to all nodes in a neighborhood
  - Example: `POST http://localhost:5000/send_dfp_to_neighbourhood`
  - Body: `{"neighbourhood": 1, "dfp_name": "Peak Power"}`

- **POST /unsubscribe_dfp**
  - Unsubscribes a node from a DFP
  - Example: `POST http://localhost:5000/unsubscribe_dfp`
  - Body: `{"bus_name": "1", "dfp_name": "Peak Power"}`

### System Operations

- **POST /load_cache**
  - Loads system state from cache
  - Example: `POST http://localhost:5000/load_cache`

- **POST /save_cache**
  - Saves current system state to cache
  - Example: `POST http://localhost:5000/save_cache`



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

- `critical.txt` - Log of critical system events and alerts:
  - Voltage violations
  - Overloaded equipment
  - System warnings and errors
  - Emergency load shedding events
  - Timestamped critical incidents
  - System health alerts
  - Protection device operations

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
