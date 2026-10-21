# Azure CLI is an operator tool, not a Django dependency.
# Invoke uv's isolated interpreter so another application's Python cannot shadow it.
$ErrorActionPreference = 'Stop'
$ctmUvRoot = & uv tool dir
if ($LASTEXITCODE -ne 0) { throw 'Cannot locate uv tools.' }
$ctmAzurePython = Join-Path $ctmUvRoot 'azure-cli/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $ctmAzurePython)) {
    throw 'Install Azure CLI: uv tool install "azure-cli>=2.80" --python 3.13 --prerelease=allow'
}
& $ctmAzurePython -m azure.cli @args
exit $LASTEXITCODE
