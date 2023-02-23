Write-Host "Starting mysql (disabling firewall rule)"

netsh advfirewall firewall delete rule name="Closed Port 3306 for MySQL"
netsh advfirewall firewall add rule name="Open Port 3306 for MySQL" dir=in action=allow protocol=TCP localport=3306