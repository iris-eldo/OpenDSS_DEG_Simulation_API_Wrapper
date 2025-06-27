# Setup script for Windows

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires Administrator privileges. Please run as Administrator." -ForegroundColor Red
    exit 1
}

# Check if Python is installed
$pythonVersion = python --version 2>&1
if (-not $?) {
    Write-Host "Python is not installed. Please install Python 3.8 or later and add it to PATH." -ForegroundColor Red
    exit 1
}

Write-Host "Detected $pythonVersion" -ForegroundColor Green

# Create and activate virtual environment
$venvPath = ".\venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $venvPath
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

# Install PyTorch with CUDA support
Write-Host "Installing PyTorch with CUDA support..." -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other requirements
Write-Host "Installing other requirements..." -ForegroundColor Cyan
pip install -r requirements.txt

# Check CUDA availability
Write-Host "`nChecking CUDA availability..." -ForegroundColor Cyan
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else "N/A"}'); print(f'Current device: {torch.cuda.current_device() if torch.cuda.is_available() else "CPU"}')"

Write-Host "`nSetup completed successfully!" -ForegroundColor Green
Write-Host "To activate the virtual environment in the future, run:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "`nTo run the simulation, use:" -ForegroundColor Yellow
Write-Host "  python main.py" -ForegroundColor White
