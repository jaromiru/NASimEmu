

param (
    [string]$subnetid = '0'
)


for($remote_subnet = 0; $remote_subnet -lt 10; $remote_subnet++) {
    if($remote_subnet -ne $subnetid){
        route -p ADD "192.168.$remote_subnet.0" MASK "255.255.255.0" "192.168.$subnetid.10"
    }
}

# allow 4444 port (for bind payloads), ping & enable firewall
Write-Host "Enabling firewall"
netsh advfirewall firewall add rule name="Open Port 4444" dir=in action=allow protocol=TCP localport=4444
netsh advfirewall firewall add rule name="ICMP Allow incoming V4 echo request" protocol=icmpv4:8,any dir=in action=allow
netsh advfirewall set allprofiles state on
