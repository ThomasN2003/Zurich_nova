$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host ""
Write-Host "Checking trained model files..."

$requiredFiles = @(
    "treatment_contribution_model.pkl",
    "annual_expense_model.pkl",
    "model_metrics.pkl",
    "pricing_reference.csv"
)

$missingFiles = @()

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host ""
    Write-Host "Model files are missing."
    Write-Host "Running training.py..."

    python .\training.py

    if ($LASTEXITCODE -ne 0) {
        throw "Model training failed."
    }
}

Write-Host ""
Write-Host "Starting ML API on port 8000..."

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$PSScriptRoot'; python -m uvicorn ml_api:app --reload --port 8000"
)

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting Streamlit on port 8501..."

python -m streamlit run .\app.py