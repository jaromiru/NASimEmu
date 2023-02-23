Write-Host "Starting wamp"

$wampConfig = "C:\wamp\bin\apache\Apache2.2.21\conf\httpd.conf"

(Get-Content $wampConfig) -Replace 'Listen 8585', 'Listen 80' | Set-Content $wampConfig
(Get-Content $wampConfig) -Replace 'ServerName localhost:8585', 'ServerName localhost:80' | Set-Content $wampConfig

Set-Service -Name wampmysqld -StartupType Automatic
Start-Service -Name wampmysqld

Set-Service -Name wampapache -StartupType Automatic
Start-Service -Name wampapache