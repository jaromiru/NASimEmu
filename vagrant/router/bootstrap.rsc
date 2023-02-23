:put "Bootstrapping router"

# find the correct eth3 interface
# -------------------------------
#/import vagrant_provision_mac_addr.rsc
:global vmNICMACs
# vmNICMACs array is zero-based
:local eth3MACaddr [:pick $vmNICMACs 2]
:local eth3name [/interface ethernet get [find mac-address="$eth3MACaddr"] name]

# initialize the networks
# -------------------------------
/ip address add address=192.168.0.10/24 interface=$eth3name
/ip address add address=192.168.1.10/24 interface=$eth3name
/ip address add address=192.168.2.10/24 interface=$eth3name
/ip address add address=192.168.3.10/24 interface=$eth3name
/ip address add address=192.168.4.10/24 interface=$eth3name
/ip address add address=192.168.5.10/24 interface=$eth3name
/ip address add address=192.168.6.10/24 interface=$eth3name
/ip address add address=192.168.7.10/24 interface=$eth3name
/ip address add address=192.168.8.10/24 interface=$eth3name
/ip address add address=192.168.9.10/24 interface=$eth3name
/ip address add address=192.168.10.10/24 interface=$eth3name

:put "This is the new configuration:"
/ip address print


# initialize firewall
# -------------------------------

# no ICMP from the router itself
/ip firewall filter add chain=output action=drop protocol=icmp

# allow established connections
/ip firewall filter add chain=forward action=fasttrack-connection connection-state=established,related
/ip firewall filter add chain=forward action=accept connection-state=established,related
