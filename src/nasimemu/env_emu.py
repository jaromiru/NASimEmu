# This is a high-level wrapper around NASimEnv that translates nasim actions into actions in msf_interface and the module result into nasim result.

from nasimemu.nasim.envs import NASimEnv
from nasimemu.nasim.envs.host_vector import HostVector
from nasimemu.nasim.scenarios.host import Host

import logging, random
import numpy as np, time, ipaddress

from nasimemu.msf_interface import MsfClient

WHOLE_NETWORK = '192.168.1-5.100-110'

class EmulatedNetwork():
    def __init__(self, host_dim, scenario):
        self.msfclient = MsfClient('msfpassword', '192.168.0.100')
        self.host_dim = host_dim
        self.scenario = scenario

        self.logger = logging.getLogger("EmulatedNetwork")
        # start fresh - kill all sessions
        # for session in self.msfclient.get_sessions():
                # session.stop()

        self.observed_hosts = set()

    @staticmethod
    def _ip_to_target(host):
        _, _, t_subnet, t_id = host.split('.')
        return int(t_subnet), int(t_id)-100

    @staticmethod
    def _target_to_ip(target):
        return f'192.168.{target[0]}.{100+target[1]}'

    def _is_session_root(self, session_id, os):
        if os == 'windows':
            groups = self.msfclient.run_shell_command(session_id, 'whoami /groups', os)
            return "BUILTIN\\Administrators" in groups
        else:
            username = self.msfclient.run_shell_command(session_id, 'whoami', os)
            return 'root' in username

    def _contains_loot(self, session_id, os):
        if os == 'linux':
            loot_file = '/home/kylo_ren/loot'
            res = self.msfclient.run_shell_command(session_id, f'test -f {loot_file}; echo NO_LOOT=$?')
            return "NO_LOOT=0" in res
        elif os == 'windows':
            loot_file = "C:\\loot"
            res = self.msfclient.run_shell_command(session_id, f'IF EXIST {loot_file} ECHO file exists', os='windows')
            return "file exists" in res
        else:
            return None

    def _recover_loot(self, session_id, os):
        if os == 'linux':
            loot_file = '/home/kylo_ren/loot'
            res = self.msfclient.run_shell_command(session_id, f'cat {loot_file}')

            if "LOOT=" in res:
                return res
            else:
                return None
        elif os == 'windows':
            loot_file = 'C:\\loot'
            res = self.msfclient.run_shell_command(session_id, f'type {loot_file}', os='windows')

            loot = [line for line in res.split('\n') if "LOOT=" in line]
            if len(loot) > 0:
                return loot[0]
            else:
                return None
        else:
            return None

    def _get_action_result(self):
        a_res =  np.zeros(self.host_dim)        # TODO: auxiliary action result - see observation.py from_action_result()
        return a_res


    def initial_scan(self):
        result = self.msfclient.scan_portscan(WHOLE_NETWORK, ports='22')
        hosts = set([x.split(':')[0] for x in result])

        self.observed_hosts.update(hosts)

        # translate IPs to (subnet, host_id)
        targets = [self._ip_to_target(x) for x in hosts]
        # targets = [x for x in targets if x[0] != 0]   # filter internet

        # create hosts & vectorize
        host_vecs = []
        for target in targets:
            host = Host(target, os=dict(), services=dict(), processes=dict(), firewall=None, value=0., discovery_value=0.,
                            compromised=False, reachable=True, discovered=True, access=0)
            host_vec = HostVector.vectorize(host, None).numpy()
            host_vecs.append(host_vec)

        host_vecs.append( self._get_action_result() )   # TODO: auxiliary action result - see observation.py from_action_result()
        host_vecs = np.vstack(host_vecs)

        return host_vecs

    def _get_meterpreter(self, ip):
        sessions = self.msfclient.get_sessions_filtered(ip=ip, session_type='meterpreter')

        if len(sessions) == 0:  # upgrade one of the sessions to meterpreter
            sessions = self.msfclient.get_sessions_filtered(ip=ip)
            session_shell = int(random.choice(list(sessions)))
            session_meterpreter = self.msfclient.post_shell_to_meterpreter(session_shell)

            if session_meterpreter is None:
                self.logger.warning(f'Upgrading a shell {session_shell} ({ip}) to meterpreter failed!')

        else:
            session_meterpreter = int(random.choice(list(sessions)))

        return session_meterpreter

    def _update_routes(self, source_ip, target_ips):
        self.logger.info(f'Found new hosts {target_ips}, creating a route from {source_ip}.')
        session_meterpreter = self._get_meterpreter(source_ip)

        if session_meterpreter is None:
            self.logger.warning(f'Creating new routes failed.')
            return

        target_subnets = set(ipaddress.ip_network(f'{ip}/24', strict=False) for ip in target_ips)

        for subnet in target_subnets:
            self.msfclient.run_msf_command(f'route add {subnet} {session_meterpreter}')

        self.msfclient.run_msf_command(f'route')

    def subnet_scan(self, a):
        target_ip = self._target_to_ip(a.target)
        sessions = self.msfclient.get_sessions_filtered(ip=target_ip)
        info = {'success': False}

        if len(sessions) == 0:
            self.logger.warning(f'No available session for action {a}')
            host_vecs = np.array([[np.zeros(self.host_dim)]])
            return host_vecs, info

        session_id = int(random.choice(list(sessions)))
        hosts = self.msfclient.scan_ping_sweep(WHOLE_NETWORK, session_id)

        # if we discovered new hosts, we need to create a route to them
        new_hosts = set(hosts) - self.observed_hosts
        if len(new_hosts) > 0:
            self._update_routes(target_ip, new_hosts)
            self.observed_hosts.update(new_hosts)

        targets = [self._ip_to_target(x) for x in hosts]

        # create hosts & vectorize
        host_vecs = []
        for target in targets:
            host = Host(target, os=dict(), services=dict(), processes=dict(), firewall=None, value=0., discovery_value=0.,
                            compromised=False, reachable=True, discovered=True, access=0)
            host_vec = HostVector.vectorize(host, None).numpy()
            host_vecs.append(host_vec)

        host_vecs.append( self._get_action_result() )                   # TODO: auxiliary action result - see observation.py from_action_result()
        host_vecs = np.vstack(host_vecs)

        info['success'] = True
        return host_vecs, info

    def _post_exploitation(self, session_id, os, host_address):
        if os is None:  # some actions may have blank os, so try to detect it here (should not happen in the standard scenarios)
            os = self.msfclient.get_os_by_cmd(session_id)

        osdict = {os: False for os in self.scenario.os}
        osdict[os] = True

        # recover true services
        servicesdict = {service: False for service in self.scenario.services}
        services = self.msfclient.get_services_by_cmd(session_id, os)
        for srv in services:
            servicesdict[srv] = True

        # check for loot
        if self._contains_loot(session_id, os):
            value = 100
            loot = self._recover_loot(session_id, os)

            if loot:
                self.logger.info(f"----------------------")
                self.logger.info(f"Loot recovered: {loot}")
                self.logger.info(f"----------------------")

        else:
            value = 0

        # check access
        access = 2 if self._is_session_root(session_id, os) else 1

        # create host vector
        host = Host(host_address, os=osdict, services=servicesdict, processes=dict(), firewall=None, value=value, discovery_value=0.,
                                                compromised=True, reachable=True, discovered=True, access=access)
        host_vec = HostVector.vectorize(host, None).numpy()

        return host_vec

    def exploit(self, a):
        rhost = self._target_to_ip(a.target)
        info = {'success': False}

        if a.name == 'e_drupal':
            session_id = self.msfclient.exploit_drupal_coder_exec(rhost)
        elif a.name == 'e_proftpd':
            session_id = self.msfclient.exploit_proftpd_modcopy_exec(rhost)
        elif a.name == 'e_wp_ninja':
            session_id = self.msfclient.exploit_wp_ninja_forms_unauthenticated_file_upload(rhost)   # TODO: uses reverse payload
        elif a.name == 'e_phpwiki':
            session_id = self.msfclient.exploit_phpwiki_ploticus_exec(rhost)
        elif a.name == 'e_elasticsearch':
            session_id = self.msfclient.exploit_elasticsearch_script_mvel_rce(rhost)
        else:
            raise NotImplementedError(a)

        if session_id is None:
            self.logger.warning(f'Failed exploit: {a}')
            host_vecs = np.array([[self._get_action_result()]])
            return host_vecs, info

        else:
            host_vec = self._post_exploitation(session_id, a.os, a.target)
            host_vecs = np.vstack([host_vec, self._get_action_result()])
            info['success'] = True
            return host_vecs, info

    def privesc(self, a):
        rhost = self._target_to_ip(a.target)
        sessions = self.msfclient.get_sessions_filtered(ip=rhost)
        info = {'success': False}

        if len(sessions) == 0:
            self.logger.warning(f'No available session for action {a}')
            host_vecs = np.array([[self._get_action_result()]])
            return host_vecs, info

        session_id_user = int(random.choice(list(sessions)))

        if a.name == 'pe_kernel':
            session_id = self.msfclient.privesc_overlayfs_priv_esc(rhost, session_id_user)
        else:
            raise NotImplementedError(a)

        if session_id is None:
            self.logger.warning(f'Privesc {a} failed')
            host_vecs = np.array([[self._get_action_result()]])
            return host_vecs, info

        else:

            host_vec = self._post_exploitation(session_id, a.os, a.target)
            host_vecs = np.vstack([host_vec, self._get_action_result()])
            info['success'] = True

            return host_vecs, info

    def os_scan(self, a):
        info = {'success': False}

        rhost = self._target_to_ip(a.target)
        os = self.msfclient.scan_os_smb(rhost)
        #os = self.msfclient.scan_os_nmap(rhost)

        if len(os) != 0 and os[0] is not None:
            info['success'] = True

            osdict = {os: False for os in self.scenario.os}
            osdict[os[0]] = True

            host = Host(a.target, os=osdict, services=dict(), processes=dict(), firewall=None, value=0,
                    discovery_value=0, compromised=False, reachable=False, discovered=False, access=0)
        else:
            self.logger.warning(f"Failure: OS not detected.")
            host = Host(a.target, os=dict(), services=dict(), processes=dict(), firewall=None, value=0, discovery_value=0.,
                    compromised=False, reachable=False, discovered=False, access=0)

        host_vec = HostVector.vectorize(host, None).numpy()
        host_vecs = np.vstack([host_vec, self._get_action_result()])
        return host_vecs, info

    def service_scan(self, a):
        info = {'success': False}

        rhost = self._target_to_ip(a.target)
        res = self.msfclient.scan_portscan(rhost, '21,80,3306,9200')
        open_ports = [x.split(':')[1] for x  in res]

        exploitable_services = {service: False for service in self.scenario.services}

        if '9200' in open_ports:
            exploitable_services['9200_windows_elasticsearch'] = True

        if '80' in open_ports:
            http_dirs = self.msfclient.scan_dir_scanner(rhost, '80')

            if '21' in open_ports and 'uploads' in http_dirs:
                exploitable_services['21_linux_proftpd'] = True
            if 'drupal' in http_dirs:
                exploitable_services['80_linux_drupal'] = True
            if 'phpwiki' in http_dirs:
                exploitable_services['80_linux_phpwiki'] = True
            if 'wordpress' in http_dirs:
                exploitable_services['80_windows_wp_ninja'] = True

        if '3306' in open_ports:
            exploitable_services['3306_any_mysql'] = True

        self.logger.info(f'Found these services: {exploitable_services} ({rhost}).')

        host = Host(a.target, os=dict(), services=exploitable_services, processes=dict(), firewall=None, value=0, discovery_value=0.,
                        compromised=False, reachable=False, discovered=False, access=0)
        host_vec = HostVector.vectorize(host, None).numpy()

        host_vecs = np.vstack([host_vec, self._get_action_result()])
        info['success'] = True
        return host_vecs, info

    def process_scan(self, a):      # TODO, currently - no processes
        info = {'success': False}

        host = Host(a.target, os=dict(), services=dict(), processes=dict(), firewall=None, value=0, discovery_value=0.,
                        compromised=False, reachable=False, discovered=False, access=0)
        host_vec = HostVector.vectorize(host, None).numpy()

        host_vecs = np.vstack([host_vec, self._get_action_result()])
        info['success'] = True
        return host_vecs, info

    def translate_action(self, a):
        if a.is_exploit():
            return self.exploit(a)

        if a.is_privilege_escalation():
            return self.privesc(a)

        if a.is_service_scan():
            return self.service_scan(a)

        if a.is_os_scan():
            return self.os_scan(a)

        if a.is_subnet_scan():
            return self.subnet_scan(a)

        if a.is_process_scan():
            return self.process_scan(a)

        raise NotImplementedError(a)

class EmulatedNASimEnv(NASimEnv):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.emulated_network = EmulatedNetwork(self.current_state.tensor.shape[1], self.scenario)
        self.logger = logging.getLogger("EmulatedNASimEnv")

    def reset(self):
        super().reset()

        self.logger.info("reset()")
        s = self.emulated_network.initial_scan()
        return s

    def step(self, a):
        time.sleep(1)

        self.logger.info(f"step() with {a}")
        s, i = self.emulated_network.translate_action(a)

        return s, 0., False, i  # s, r, d, i

if __name__ == '__main__':
    # useful for testing
    # ------------------

    from nasimemu import nasim

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.INFO)

    scenario = nasim.load_scenario("scenarios/test_scenario.yaml")
    env = EmulatedNASimEnv(scenario=scenario)

    # a = nasim.envs.action.SubnetScan(target=(1,0), cost=1.0)
    # a = nasim.envs.action.OSScan(target=(1,0), cost=1.0)
    # a = nasim.envs.action.Exploit(name='e_proftpd', service='proftpd', target=(1,0), cost=1.0)
    # a = nasim.envs.action.Exploit(name='e_drupal', service='drupal', target=(1,0), cost=1.0)
    # a = nasim.envs.action.PrivilegeEscalation(name='pe_kernel', process=None, access=1, target=(1,0), cost=1.0)
    a = nasim.envs.action.ServiceScan(target=(1,0), cost=1.0)

    s, r, d, i = env.step(a)
    print(s, r, d, i)
