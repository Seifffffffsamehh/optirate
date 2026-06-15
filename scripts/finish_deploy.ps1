param(
    [string]$AivenHost,
    [string]$AivenPort,
    [string]$AivenUser = "avnadmin",
    [string]$AivenPassword,
    [string]$AivenDatabase = "defaultdb",
    [string]$JwtSecret,
    [ValidateSet("render", "huggingface")]
    [string]$Platform = "huggingface"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

if ($AivenHost -and $AivenPassword) {
    Write-Host "Importing local database into Aiven..."
    & "$PSScriptRoot\import_to_aiven.ps1" `
        -Host $AivenHost `
        -Port $AivenPort `
        -User $AivenUser `
        -Password $AivenPassword `
        -Database $AivenDatabase
}

if (-not $JwtSecret) {
    $JwtSecret = python -c "import secrets; print(secrets.token_hex(32))"
    Write-Host "Generated JWT_SECRET_KEY: $JwtSecret"
}

$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"

if ($Platform -eq "render") {
    if (-not $AivenHost) {
        throw "Set Aiven connection details: -AivenHost -AivenPort -AivenPassword"
    }

    Write-Host "Creating Render service..."
    render services create `
        --name optirate `
        --type web_service `
        --runtime python `
        --plan free `
        --region frankfurt `
        --repo https://github.com/Seifffffffsamehh/optirate `
        --branch main `
        --build-command "pip install -r requirements.txt" `
        --start-command 'gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 "app:create_app()"' `
        --health-check-path /api/health `
        --env-var "FLASK_ENV=production" `
        --env-var "FLASK_DEBUG=0" `
        --env-var "DB_SSL=true" `
        --env-var "DB_HOST=$AivenHost" `
        --env-var "DB_PORT=$AivenPort" `
        --env-var "DB_USER=$AivenUser" `
        --env-var "DB_PASSWORD=$AivenPassword" `
        --env-var "DB_NAME=$AivenDatabase" `
        --env-var "JWT_SECRET_KEY=$JwtSecret" `
        --env-var "PYTHON_VERSION=3.11.9" `
        --confirm -o json
}
else {
    if (-not (Get-Command hf -ErrorAction SilentlyContinue)) {
        throw "Hugging Face CLI not found. Run: pip install -U huggingface_hub"
    }

    $whoami = hf auth whoami 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in to Hugging Face. Run: hf auth login"
    }

    $space = "Seifffffffsamehh/optirate"
    Write-Host "Creating/updating Hugging Face Space: $space"
    hf repos create $space --type space --space-sdk docker --exist-ok 2>&1 | Out-Host

    $secretArgs = @()
    if ($AivenHost) { $secretArgs += "DB_HOST=$AivenHost" }
    if ($AivenPort) { $secretArgs += "DB_PORT=$AivenPort" }
    if ($AivenUser) { $secretArgs += "DB_USER=$AivenUser" }
    if ($AivenPassword) { $secretArgs += "DB_PASSWORD=$AivenPassword" }
    if ($AivenDatabase) { $secretArgs += "DB_NAME=$AivenDatabase" }
    $secretArgs += "DB_SSL=true"
    $secretArgs += "JWT_SECRET_KEY=$JwtSecret"
    $secretArgs += "FLASK_ENV=production"
    $secretArgs += "FLASK_DEBUG=0"

    if ($secretArgs.Count -gt 0) {
        $hfSecretArgs = @()
        foreach ($item in $secretArgs) {
            $hfSecretArgs += "-s"
            $hfSecretArgs += $item
        }
        & hf spaces secrets add $space @hfSecretArgs 2>&1 | Out-Host
    }

    hf spaces variables add $space -e "PORT=7860" 2>&1 | Out-Host

    Write-Host "Uploading repository to Space..."
    hf upload $space . --repo-type space --exclude ".git/*" --exclude "optirate_backup.sql" --exclude ".env" 2>&1 | Out-Host
    Write-Host "Space URL: https://huggingface.co/spaces/$space"
}
