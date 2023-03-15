# This is an self-executable module to create Vagrantfiles and RouterOS configuration from scenarios.

import logging
import sys
import argparse
import os.path as path
from pathlib import Path

from .env_emu import EmulatedNetwork
from .nasim.scenarios import load_scenario
from .nasim.envs import NASimEnv

class VagrantGenerator:

    def __init__(self, scenario, vagrant_file):
        self.scenario = scenario
        self.vagrant_file = vagrant_file
        self.generate_vagrant()

    def generate_vagrant(self):
        self.write_header()
        for host in self.scenario.hosts:
            self.add_host(self.scenario.hosts[host], self.scenario.hosts[host].address in self.scenario.sensitive_hosts)
        self.write_footer()

    def write_header(self):
        self.vagrant_file.write(f"""# Use:
# copy .vagrant file to ../vagrant/Vagrantfile
# copy .rsc file to ../vagrant/firewall.rsc
# cd to ../vagrant
# use vagrant to run the emulation:
# `vagrant status`
# `vagrant up`

Vagrant.configure("2") do |config|
    config.vm.provider "virtualbox" do |vb|
        vb.gui = false
        vb.memory = "1024"
        # vb.check_guest_additions = false
    end

    # see https://github.com/cheretbe/packer-routeros
    config.vm.define "router" do |router|
        router.vm.box = "cheretbe/routeros"
        router.vm.box_version = "6.48.4-0"
        router.vm.hostname = "router"

        # it needs `VBoxManage dhcpserver remove --netname HostInterfaceNetworking-vboxnet0`
        # if you receive 'A host only network interface you're attempting to configure via DHCP' error
        router.trigger.before :up do |trigger|
          trigger.warn = "removing standard dhcp host interface if existent"
          trigger.run = {{inline: "bash -c 'if [ $( VBoxManage list dhcpservers | grep -c vboxnet0 ) != \\"0\\" ]; then VBoxManage dhcpserver remove --netname HostInterfaceNetworking-vboxnet0; fi'"}}
        end

        router.ssh.username = "admin"
        router.ssh.password = "vagrant"

        router.vm.network "private_network", virtualbox__intnet: "nasim-network", auto_config: false

        router.vm.provision "routeros_file", source: "router/bootstrap.rsc", destination: "bootstrap.rsc"
        router.vm.provision "routeros_command", command: "/import bootstrap.rsc", check_script_error: true

        router.vm.provision "routeros_file", source: "firewall.rsc", destination: "firewall.rsc" # make sure you copied the .rsc file as well!
        router.vm.provision "routeros_command", command: "/import firewall.rsc", check_script_error: true

        router.vm.provision "routeros_file", source: "router/bootstrap-after-firewall.rsc", destination: "bootstrap-after-firewall.rsc"
        router.vm.provision "routeros_command", command: "/import bootstrap-after-firewall.rsc", check_script_error: true
        end

    config.vm.define "attacker" do |attacker|
        attacker.vm.box = "kalilinux/rolling"
        attacker.vm.box_version = "2022.1.0"
        attacker.vm.hostname = "attacker"
        attacker.vm.network "private_network", ip: "192.168.0.100", netmask: "255.255.255.0", virtualbox__intnet: "nasim-network"
        attacker.vm.network "forwarded_port", guest: 55553, host: 55553 # msfrpcd

        attacker.vm.synced_folder 'attacker', '/vagrant', type: 'rsync'
        attacker.vm.provision "shell", path: 'attacker/bootstrap.sh'
        attacker.vm.provision "shell", path: 'attacker/setup-network.py', args: '-subnetid 0'
    end
        """)

    def write_footer(self):
        self.vagrant_file.write("""
end
        """)

    @staticmethod
    def _get_provision_line(os, services, ip, subnet, varname, is_sensitive):
        enabled_services = [service for service in services if services[service]]
        if 'windows' in os and os['windows']:
            add_loot_line = f"{varname}.vm.provision \"shell\", path: 'target/windows-insert-loot.ps1'" if is_sensitive else ""
            return f"""
        {varname}.vm.synced_folder 'target', '/vagrant'
        {varname}.vm.provision "shell", path: 'target/windows-service-script.ps1', args: '-services {",".join(enabled_services)} -ip {ip}'
        {varname}.winrm.retry_limit = 100
        {varname}.winrm.retry_delay = 10
        {varname}.vm.provision "shell", path: 'target/windows-setup-network.ps1', args: '-subnetid {subnet}'
        {add_loot_line}
        {varname}.vm.provision :shell do |shell|
            shell.privileged = true
            shell.inline = <<-'SCRIPT'
                slmgr.vbs /rearm
                echo "Rebooting for license renewal"
            SCRIPT
            shell.reboot = true
        end
            """
        elif 'linux' in os and os['linux']:
            add_loot_line = f"{varname}.vm.provision \"shell\", path: 'target/linux-insert-loot.sh'" if is_sensitive else ""
            return f"""
        {varname}.vm.synced_folder 'target', '/vagrant', type: 'rsync'
        {varname}.vm.provision "shell", path: 'target/linux-service-script.sh', args: '{" ".join(enabled_services)}'
        {varname}.vm.provision "shell", path: 'target/bootstrap.sh'
        {varname}.vm.provision "shell", path: 'target/linux-setup-network.py', args: '-subnetid {subnet}'
        {add_loot_line}
            """

    @staticmethod
    def _get_box_from_os(os):
        if 'windows' in os and os['windows']:
            return "rapid7/metasploitable3-win2k8", "0.1.0-weekly"
        elif 'linux' in os and os['linux']:
            return "rapid7/metasploitable3-ub1404", "0.1.12-weekly"

    @staticmethod
    def _get_host_description(varname, hostname, ip, box, box_version, netmask, provision):
        return f"""
    config.vm.define "{hostname}" do |{varname}|
        {varname}.vm.box = "{box}"
        {varname}.vm.box_version = "{box_version}"
        {varname}.vm.hostname = "{hostname}"
        {varname}.vm.network "private_network", ip: "{ip}", netmask: "{netmask}", virtualbox__intnet: "nasim-network"

        {varname}.ssh.username = 'vagrant'
        {varname}.ssh.password = 'vagrant'
{provision}
    end
        """

    def add_host(self, host, is_sensitive):
        varname = 'target'
        hostname = f"target{host.address[0]}{host.address[1]}"
        ip = EmulatedNetwork._target_to_ip(host.address)
        subnet = host.address[0]
        box, box_version = self._get_box_from_os(host.os)
        netmask = "255.255.255.0" 
        provision = self._get_provision_line(host.os, host.services, ip, subnet, varname, is_sensitive)

        self.vagrant_file.write(self._get_host_description(varname, hostname, ip, box, box_version, netmask, provision))

class RouteOsGenerator:
    def __init__(self, scenario, out=sys.stdout):
        self.out = out
        self.firewall = scenario.firewall
        self.topology = scenario.topology
        self.generate_firewall()

    def generate_firewall(self):
        """for link in self.firewall:
            for service_allowed in self.firewall[link]:
                print(service_allowed, self.firewall[link][service_allowed])"""
        text_output = ""
        for address_in in range(len(self.topology)):
            for address_out in range(len(self.topology[address_in])):
                if address_in != address_out and self.topology[address_in][address_out] == 1:
                    text_output += f"/ip firewall filter add chain=forward action=accept src-address=192.168.{address_in}.0/24 dst-address=192.168.{address_out}.0/24 proto=icmp\n"
                    text_output += f"/ip firewall filter add chain=forward action=accept src-address=192.168.{address_in}.0/24 dst-address=192.168.{address_out}.0/24 proto=tcp\n"
        self.out.write(text_output)

class VagrantClient:
    def __init__(self, scenario, dst_file, routeos_file):
        self.scenario = scenario

        self.dst_file = dst_file
        self.routeos_file = routeos_file
        
        self.logger = logging.getLogger("VagrantInterface")

        self.generate_routeos_file()
        self.generate_vagrant_file()
        # self.launch_vagrant()

    def generate_routeos_file(self):
        self.logger.info("Generating routeos firewall file.")
        with open(self.routeos_file, "w") as file:
            RouteOsGenerator(self.scenario, out=file)


    def generate_vagrant_file(self):
        self.logger.info("Generating Vagrantfile.")
        with open(self.dst_file, "w") as file:
            VagrantGenerator(self.scenario, file)

    # def launch_vagrant(self):
    #     self.logger.info("Vagrant file generated, you can now launch the virtual machines with vagrant.")
    #     # input()
        # subprocess.run(["vagrant", "up", "--provision", "--parallel", "--no-tty"], cwd="nasim_emulation/vagrant")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=str, help="Path to the scenario file")
    parser.add_argument('--dst', type=str, help="Path to the vagrant file")
    parser.add_argument('--routeros', type=str, help="Path to the routeros file")

    args = parser.parse_args()

    if args.dst is None:
        args.dst = str(Path(args.file).with_suffix('.vagrant'))

    if args.routeros is None:
        args.routeros = str(Path(args.file).with_suffix('.rsc'))

    print(f"Vagrantfile: {args.dst}, routeros file: {args.routeros}")

    scenario = load_scenario(args.file)

    print("\nGenerated scenario:")
    env = NASimEnv(scenario)
    env.reset()
    env.render_state()
    print("")

    VagrantClient(scenario, args.dst, args.routeros)
