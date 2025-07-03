# OpenDSS IEEE 123-Bus Simulation API

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A stateful Python API for interacting with OpenDSS simulations of the IEEE 123-bus test feeder. This project enables dynamic modification of grid states, including load adjustments and power generation, with real-time simulation results.


## Project Structure

```
.
├── run_simulator_data.py      # Flask web server with API endpoints
├── intialize_data.py          # Core OpenDSS circuit initialization and data retrieval logic
├── modify_neighborhood_power.py # Function to modify loads in neighborhoods
├── add_generator_to_bus.py    # Function to add/update generators on buses
├── results_api/               # Directory for simulation outputs
└── README.md                  # This file
```

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages:
  - `opendssdirect`
  - `flask`
  - `pandas`
  - `numpy`
  - `requests` (for client examples, used to interact with the API)

### Installation

1.  Install the required packages:
    ```bash
    pip install opendssdirect flask pandas numpy requests
    ```

2.  Ensure your project has the following directory structure. The `Test_Systems` directory and its contents are crucial for OpenDSS to compile the circuit. You can typically find these with an OpenDSS installation.
    ```
    your_project_folder/
    ├── run_simulator_data.py
    ├── intialize_data.py
    ├── modify_neighborhood_power.py
    ├── add_generator_to_bus.py
    └── Test_Systems/
        └── IEEE_123_Bus-G/
            ├── Master.dss
            └── ... (other required .dss files for the 123-bus system)
    ```

## Usage

This project operates as a Flask API server. You will run the main API file, and then interact with it using HTTP requests (e.g., via `curl` or separate Python client scripts).

### 1. Starting the API Server

Open your terminal, navigate to your project folder, and run:

```bash
python run_simulator_data.py

```

The API server will start on `http://127.0.0.1:5000`

## API Endpoints

### `POST /modify_load_neighbourhood`
Modifies the load in a specific neighborhood by a given factor.

**Request Body:**
```json
{
  "neighbourhood": 1,
  "factor": 1.5
}
```

**Example using cURL:**
```bash
curl -X POST [http://127.0.0.1:5000/modify_load_neighbourhood](http://127.0.0.1:5000/modify_load_neighbourhood) \
     -H "Content-Type: application/json" \
     -d '{"neighbourhood": 1, "factor": 0.8}'
```

### `POST /add_generator`
Adds a generator to a specified bus.

**Request Body:**
```json
{
  "bus_name": "150",
  "phases": 3,
  "kw": 1000
}
```

**Example using cURL:**
```bash
curl -X POST [http://127.0.0.1:5000/add_generator](http://127.0.0.1:5000/add_generator) \
     -H "Content-Type: application/json" \
     -d '{"bus_name": "150", "phases": 3, "kw": 1000}'
```

## Results

Simulation results are saved in the `results_api` directory, including:
- `latest_api_results.txt`: Most recent simulation results
- Timestamped files for historical data

## Contributions
Iris Eldo and Tarun PK 

Contributions are welcome! Please feel free to submit a Pull Request.
