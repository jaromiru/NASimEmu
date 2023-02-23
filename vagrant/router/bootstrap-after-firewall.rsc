/ip firewall filter add chain=forward action=drop log=yes log-prefix=denied

# /ip firewall filter add chain=forward action=accept protocol=icmp src-address=192.168.0.0/16 dst-address=192.168.0.0/16
# /ip firewall filter add chain=forward action=drop connection-state=invalid log=yes log-prefix=invalid

:put "Firewall configuration:"
/ip firewall filter print