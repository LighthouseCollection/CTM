# Keep the loopback OAuth review server alive while the user completes MFA.
# Provider secrets pass directly from SSH into Python stdin, never argv or disk.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.tmp/venv313/Scripts/python.exe'
ssh -o BatchMode=yes ctm 'sudo -n cat /opt/ctm/secrets/microsoft.env' |
    & $pythonPath scripts/local_microsoft.py
exit $LASTEXITCODE
