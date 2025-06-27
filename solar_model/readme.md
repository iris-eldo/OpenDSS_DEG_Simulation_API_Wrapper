# Solar Energy Adoption Simulation

An agent-based simulation model for studying the adoption of solar energy in residential communities, with both CPU and GPU-accelerated implementations.

## Overview

This project simulates the adoption of residential solar panels and their impact on the electrical grid. It models households, communities, and grid stations as agents that interact over time. The simulation includes:

- Solar energy generation based on location and weather patterns
- Energy consumption patterns for households
- Market mechanisms for buying/selling excess energy
- Social influence on solar adoption decisions
- Financial calculations including ROI and payback periods

## Project Structure

```
solar_model/
├── config/
│   ├── solar.yaml          # Main configuration file
│   └── data/               # Input data files
│       ├── energy_data.csv
│       ├── price_data.csv
│       ├── solar_pv_prices.csv
│       └── household/
│           └── demand_profile.csv
├── source/
│   ├── substeps/          # Simulation substeps
│   │   ├── __init__.py
│   │   ├── solar_generation.py
│   │   ├── market_clearing.py
│   │   ├── grid_interaction.py
│   │   ├── solar_adoption.py
│   │   └── financial_update.py
│   └── utilities/          # Helper functions
│       ├── __init__.py
│       ├── config_loader.py
│       ├── data_loader.py
│       └── metrics.py
├── main.py                 # Main simulation script
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Prerequisites

- Python 3.8 or higher
- NVIDIA GPU with CUDA support (for GPU acceleration)
- CUDA Toolkit 11.8 or compatible version
- cuDNN (for GPU acceleration)

## Installation

### Windows Setup

1. **Clone the repository**:
   ```powershell
   git clone <repository-url>
   cd solar_model
   ```

2. **Run the setup script (as Administrator)**:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\setup_venv.ps1
   ```

   This will:
   - Create a Python virtual environment
   - Install PyTorch with CUDA support
   - Install all required dependencies
   - Verify CUDA availability

3. **Activate the virtual environment** (if not already activated):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

### Linux/macOS Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd solar_model
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install PyTorch with CUDA** (visit [pytorch.org](https://pytorch.org/get-started/locally/) for the correct command for your system):
   ```bash
   pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

4. **Install other requirements**:
   ```bash
   pip install -r requirements.txt
   ```

## GPU Acceleration

The simulation includes a GPU-accelerated version that can significantly improve performance for large-scale simulations:

- **CPU Version**: Uses standard NumPy operations
  ```bash
  python main.py
  ```

- **GPU Version**: Uses PyTorch with CUDA for acceleration
  ```bash
  python gpu_simulation.py
  ```

### Verifying GPU Support

To verify that GPU acceleration is working, run:

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device count: {torch.cuda.device_count()}")
print(f"Current device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
```

## Configuration

The simulation is configured using the `config/solar.yaml` file. Key parameters include:

- Simulation settings (number of steps, random seed)
- Environment parameters (grid prices, solar costs)
- Agent properties (households, communities, grid stations)
- Substeps configuration

## Running the Simulation

To run the simulation with default settings:

```bash
python main.py
```

This will run the simulation for the number of steps specified in the configuration and save the results to `results.csv`.

## Output

The simulation generates the following outputs:

- **Console Output**: Progress updates and key metrics for each time step
- **results.csv**: Detailed metrics for each time step, including:
  - Solar adoption rate
  - Energy generation and consumption
  - Financial metrics (savings, ROI)
  - Grid load and pricing

## Key Features

### 1. Solar Generation
- Models solar panel output based on location and time of year
- Accounts for panel degradation and efficiency
- Tracks energy production and consumption

### 2. Market Clearing
- Balances energy supply and demand within communities
- Calculates dynamic pricing based on local conditions
- Manages energy trading between households and the grid

### 3. Grid Interaction
- Models grid stability and capacity constraints
- Implements dynamic pricing based on load
- Tracks grid revenue and performance metrics

### 4. Solar Adoption
- Simulates household decision-making for solar adoption
- Incorporates financial, social, and environmental factors
- Models peer influence and information diffusion

### 5. Financial Analysis
- Calculates ROI and payback periods
- Tracks savings and costs over time
- Models incentives and subsidies

## Customization

You can customize the simulation by modifying:

1. **Configuration File**: Adjust parameters in `config/solar.yaml`
2. **Input Data**: Replace CSV files in `config/data/` with your own data
3. **Substeps**: Modify the Python files in `source/substeps/` to change agent behaviors

## Dependencies

### Core Dependencies
- Python 3.8+
- NumPy
- Pandas
- PyYAML
- Matplotlib (for visualization)
- SciPy (for statistical functions)
- tqdm (for progress bars)

### GPU Acceleration
- PyTorch with CUDA support
- CUDA Toolkit (11.8 recommended)
- cuDNN
- Numba (for additional GPU acceleration)
- CuPy (optional, for GPU-accelerated NumPy operations)

## Performance Tips

1. **Batch Processing**: For large numbers of agents, use batch processing to fully utilize GPU parallelism.
2. **Mixed Precision**: Consider using `torch.cuda.amp` for mixed-precision training to speed up computation.
3. **Data Loading**: Use `torch.utils.data.DataLoader` for efficient data loading and preprocessing.
4. **Memory Management**: Monitor GPU memory usage with `nvidia-smi` and adjust batch sizes accordingly.

## Troubleshooting

### Common Issues

1. **CUDA Out of Memory**:
   - Reduce batch size
   - Use gradient checkpointing
   - Clear cache: `torch.cuda.empty_cache()`

2. **CUDA Version Mismatch**:
   - Ensure your CUDA version matches the PyTorch build
   - Reinstall PyTorch with the correct CUDA version

3. **Slow Performance**:
   - Ensure you're using the GPU version of PyTorch
   - Check for CPU-GPU data transfers that could be bottlenecks
   - Profile your code with `torch.profiler`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on agent-based modeling principles
- Inspired by real-world energy markets and policies
- Built using open-source Python libraries