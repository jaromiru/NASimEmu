# NASimEmu Emulation

## Installation
To use the emulation, you should install [Vagrant](https://www.vagrantup.com/downloads) and [VirtualBox](https://www.virtualbox.org/wiki/Linux_Downloads)

*Warning!* Install Vagrant from the official site: https://www.vagrantup.com/downloads (ver >= 2.2.19). Do not use obsolete packages in your distribution.

Also, install these plugins:
```
vagrant plugin install winrm  
vagrant plugin install winrm-fs  
vagrant plugin install winrm-elevated
```

## Setting vagrant up
First, Vagrant needs to be configured with the chosen scenario:
```./setup_vagrant <scenario_file.yaml>```
This command which will create `vagrant/Vagrantfile` and `vagrant/firewall.rsc` files.

Next, go the the `vagrant` folder and start Vagrant:
```
cd vagrant
vagrant status
vagrant up
```

The command will download corresponding virtual images and run the virtual network. The download is slow, but is done only once. There is a special host `attacker`, which runs Kali linux with metasploit framework and a remote interface `msfrcpd`. Also, a node `router` is the network's router and runs RouterOS (note that without license, the router stops working in 24 hours and needs to be reset).

You can login into individual hosts with `vagrant ssh attacker`, or `vagrant ssh target10` (in scenario, it is the host in subnet `1` and host id `0`). The default password for the `vagrant` user is `vagrant`.

## Resetting emulation
If you need to reset the emulation, run `vagrant destroy -f`, followed by `vagrant up`.

## Running NASimEmu
By default, the Vagrant is configured to forward the `msfrcpd` to your localhost on port `55553`, which is also configured by default in `nasimemu.msf_interface`. Then, when creating an environment, use `emulation=True`, such as:
```
env = gym.make('NASimEmu-v0', emulate=True, scenario_name='...')
```
In this case, the provided scenario will be used inform the agent about available exploits, privescs and `address_space_bounds`. The actual topology and host configuration is given by the emulation.

## Other details
### How the emulation works
When the agent issues an action to NASimEmuEnv, it is forwarded either to nasim (simulation), or `EmulatedNASimEnv` (emulation). Then it goes to `EmulatedNetwork`, then to `MsfClient`, where it is finally forwarded as a metaspoit action to the `attacker` node. The result of the action is translated back to the nasim observation format. To see the current list of exploits that can be used, see [SERVICES](/docs/SERVICES.md).

### Running emulation on a remote machine
You can run the vagrant on a remote machine. If you use localhost for performing experiments, forward the port `55553` to your localhost, like this: 
```ssh -L 55553:127.0.0.1:55553 remote-machine -N &```

### Pivoting
The attacker machine often does not see the other hosts directly. To overcome this issue, NASimEmu uses automatic pivoting and bind payloads.

### Sensitive hosts
Sensitive hosts contain a *loot*, represented as a specific file on the host with limited permissions. On linux, the file is `/home/kylo_ren/loot`, owned by the user 'kylo_ren' and permission `600`. On windows, the file is `C:/loot`, owned by the user 'kylo_ren' and other users have access denied.

If the attacker manages to read the content of the file, the loot is considered obtained.

### Networking
The network consists of `192.168.*.*/24` subnets, where subnet `0` is the attacker (internet) subnet.

There is node called router, which is a routeros instance, sitting at `192.168.*.10`. It also filters the traffic, according its firewall rules.

Network hosts use `192.168.{subnet_id}.{host_id+100}` address and are configured to route its traffic via router, if it's destined to different subnets. Traffic inside a subnet is unfiltered.

### Network debugging
You can login to the router `vagrant ssh router` and try `/tool sniffer quick interface=ether3` to see the traffic that goes through the router.

Alternatively you can also login to a specific machine and try `sudo tcpdump -i eth1`.

Currently, all the machines are on **the same interface**, which is only virtually partitioned to different IP segments by router firewall. However different protocols, such as ARP ignore this partitioning, hence the machines can see each other via ARP. This makes ARP scanning not useful in our abstraction.

### Troubleshooting
Sometimes, bringing the `router` up fails and it is necessary to remove VirtualBox's dhcpservers like this:
```
VBoxManage list dhcpservers
VBoxManage dhcpserver remove --netname HostInterfaceNetworking-vboxnet5 # substitute the correct interface
```

If you leave the network up for longer than 24 hours, the router needs to be reset (because it runs without a license). Use:
```
vagrant destroy -f router
vagrant up router
```

Sometimes, the `msfrcpd` does not respond properly. In that case, log in to the `attacker` machine and restart it.
```
vagrant ssh attacker
ps x # find the msfrcpd PID
kill <PID>
msfrpcd -P msfpassword
```