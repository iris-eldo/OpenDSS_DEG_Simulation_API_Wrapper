# OpenDSS IEEE 123-Bus Simulation API

This project provides a stateful Python API to run and interact with an OpenDSS simulation of the IEEE 123-bus test feeder. It allows users to dynamically modify the grid's state by adding power generation or changing load consumption and receive detailed simulation results in real-time.

## Project Structure

The project is composed of two main Python files:

-   `simulation_core.py`: A library containing the `OpenDSSCircuit` class. This file handles all direct interactions with the OpenDSS engine, such as compiling the circuit, solving the power flow, and modifying circuit elements.
-   `api.py`: A lightweight web server built with Flask. It creates a persistent `OpenDSSCircuit` object and exposes API endpoints that allow users to call methods from the `simulation_core` library.

## Getting Started

### Prerequisites

-   Python 3.8+
-   `pip` (Python package installer)
-   OpenDSS is not required to be installed separately, as the `opendssdirect` library includes the engine.

### 1. Installation

First, install the necessary Python packages by running the following command in your terminal:

```sh
pip install Flask opendssdirect pandas numpy
2. Directory StructureFor the simulation to run correctly, your project folder must have the following structure. The api.py script uses a relative path to find the Master.dss file.your_project_folder/
├── api.py
├── simulation_core.py
└── Test_Systems/
    └── IEEE_123_Bus-G/
        ├── Master.dss
        └── ... (and all other required .dss files for the 123-bus system)
3. Running the API ServerNavigate to your project's root directory in your terminal and run the api.py script:python api.py
The server will initialize the circuit and start listening for requests on http://127.0.0.1:5000.API EndpointsThe API maintains a persistent state. Each modification call builds upon the previous state of the grid until the server is restarted.Add a GeneratorThis endpoint adds a new power generation source to a specified bus. If a generator already exists on that bus with the same phase configuration, this call will update its power output instead of creating a new one.Endpoint: /add_generatorMethod: POSTPayload:bus_name (string): The name of the bus (e.g., "16").phases (integer): The number of phases for the generator (1 or 3).kw (float): The target real power output in kilowatts.API Call FormatPowerShell:Invoke-WebRequest -Uri '[http://127.0.0.1:5000/add_generator](http://127.0.0.1:5000/add_generator)' -Method POST -ContentType 'application/json' -Body '{"bus_name": "16", "phases": 1, "kw": 200}'
Linux / macOS (curl):curl -X POST -H "Content-Type: application/json" -d '{"bus_name": "16", "phases": 1, "kw": 200}' [http://127.0.0.1:5000/add_generator](http://127.0.0.1:5000/add_generator)
Modify Load in a NeighbourhoodThis endpoint modifies the power consumption for all loads within a predefined neighborhood by a multiplying factor.Endpoint: /modify_load_neighbourhoodMethod: POSTPayload:neighbourhood (integer): The ID of the neighborhood (1-14).factor (float): The multiplying factor for consumption (e.g., 0.8 for 80% load, 1.5 for 150% load).API Call FormatPowerShell:Invoke-WebRequest -Uri '[http://127.0.0.1:5000/modify_load_neighbourhood](http://127.0.0.1:5000/modify_load_neighbourhood)' -Method POST -ContentType 'application/json' -Body '{"neighbourhood": 5, "factor": 0.8}'
Linux / macOS (curl):curl -X POST -H "Content-Type: application/json" -d '{"neighbourhood": 5, "factor": 0.8}' [http://127.0.0.1:5000/modify_load_neighbourhood](http://127.0.0.1:5000/modify_load_neighbourhood)
