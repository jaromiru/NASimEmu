Write-Host "Stopping wamp"

Set-Service -Name wampapache -StartupType Disabled
Stop-Service -Name wampapache
Set-Service -Name wampmysqld -StartupType Disabled
Stop-Service -Name wampmysqld