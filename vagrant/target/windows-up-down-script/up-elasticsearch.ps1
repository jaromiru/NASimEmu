Write-Host "Starting elasticsearch"

Set-Service -Name elasticsearch-service-x64 -StartupType Automatic
Start-Service -Name elasticsearch-service-x64