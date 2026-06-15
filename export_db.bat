@echo off
echo ===================================================
echo     OptiRate Database Exporter (for XAMPP)
echo ===================================================
echo.
echo Make sure your XAMPP MySQL server is running before continuing!
pause

echo.
echo Exporting 'optirate_db' to 'optirate_backup.sql'...
"C:\xampp\mysql\bin\mysqldump.exe" -u root optirate_db > optirate_backup.sql

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Export failed. Ensure XAMPP is installed in C:\xampp\ and MySQL is running.
) else (
    echo.
    echo [SUCCESS] Database exported to optirate_backup.sql!
)
echo.
pause
