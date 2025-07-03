# OpenDSS IEEE 123-Bus Simulation API

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A stateful Python API for interacting with OpenDSS simulations of the IEEE 123-bus test feeder. This project enables dynamic modification of grid states, including load adjustments and power generation, with real-time simulation results.

## 📂 Project Structure

```
.
├── api.py                 # Flask web server with API endpoints
├── simulation_core.py     # Core OpenDSS interaction logic
├── results_api/           # Directory for simulation outputs
└── README.md              # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Required Python packages:
  - opendssdirect
  - flask
  - pandas
  - numpy

### Installation

1. Install the required packages:
   ```bash
   pip install opendssdirect flask pandas numpy
   ```

2. Ensure your project has the following directory structure:
   ```
   your_project_folder/
   ├── api.py
   ├── simulation_core.py
   └── Test_Systems/
       └── IEEE_123_Bus-G/
           ├── Master.dss
           └── ... (other required .dss files)
   ```

## 🚀 Usage

### Starting the API Server

```bash
python api.py
```

The API server will start on `http://127.0.0.1:5000`

## 📚 API Endpoints

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
curl -X POST http://127.0.0.1:5000/modify_load_neighbourhood \
     -H "Content-Type: application/json" \
     -d '{"neighbourhood": 1, "factor": 1.5}'
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
curl -X POST http://127.0.0.1:5000/add_generator \
     -H "Content-Type: application/json" \
     -d '{"bus_name": "150", "phases": 3, "kw": 1000}'
```

## 📁 Results

Simulation results are saved in the `results_api` directory, including:
- `latest_api_results.txt`: Most recent simulation results
- Timestamped files for historical data

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
