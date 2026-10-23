# Keep the loopback OAuth review server alive while the user completes MFA.
# Provider secrets pass directly from SSH into Python stdin, never argv or disk.
param([string]$ReviewDirectory)
$ErrorActionPreference = 'Stop'
if ($ReviewDirectory) { $env:CTM_LOCAL_REVIEW_DIR = $ReviewDirectory }
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
ssh -o BatchMode=yes ctm 'sudo -n cat /opt/ctm/secrets/microsoft.env' |
    & $pythonPath scripts/local_microsoft.py
exit $LASTEXITCODE
