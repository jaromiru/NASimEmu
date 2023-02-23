Write-Host "Stopping elasticsearch"
Set-Service -Name elasticsearch-service-x64 -StartupType Disabled
Stop-Service -Name elasticsearch-service-x64