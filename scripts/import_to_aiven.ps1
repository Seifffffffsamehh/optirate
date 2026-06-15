# Import optirate_backup.sql into Aiven MySQL (run after creating the Aiven service).
param(
    [Parameter(Mandatory = $true)][string]$Host,
    [Parameter(Mandatory = $true)][string]$Port,
    [Parameter(Mandatory = $true)][string]$User,
    [Parameter(Mandatory = $true)][string]$Password,
    [string]$Database = "defaultdb",
    [string]$SqlFile = "..\optirate_backup.sql"
)

$mysql = "C:\xampp\mysql\bin\mysql.exe"
if (-not (Test-Path $mysql)) {
    Write-Error "MySQL client not found at $mysql. Install MySQL Shell or use the Aiven web console."
    exit 1
}

$sqlPath = Resolve-Path $SqlFile -ErrorAction Stop
Write-Host "Importing $sqlPath into $Host`:$Port/$Database ..."

$env:MYSQL_PWD = $Password
& $mysql -h $Host -P $Port -u $User --ssl-mode=REQUIRED $Database < $sqlPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "Import failed (exit $LASTEXITCODE)."
    exit $LASTEXITCODE
}

Write-Host "Import complete. Verify with: SHOW TABLES; SELECT COUNT(*) FROM users;"
