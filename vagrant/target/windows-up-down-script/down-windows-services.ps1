Write-Host "Stopping unwanted services"

Set-Service -Name w3svc -StartupType Disabled
Stop-Service -Name w3svc

Set-Service -Name ftpsvc -StartupType Disabled
Stop-Service -Name ftpsvc