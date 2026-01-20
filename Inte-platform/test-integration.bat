@echo off
echo ========================================
echo Salesforce to SAP Integration Test
echo ========================================
echo.

echo Running PowerShell test script...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0test-integration.ps1"

echo.
pause
