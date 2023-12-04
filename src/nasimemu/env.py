import gym, random, copy
import numpy as np
from nasimemu import nasim, env_utils

from nasimemu.nasim.envs.action import Exploit, PrivilegeEscalation, ServiceScan, OSScan, SubnetScan, ProcessScan, NoOp
import nasimemu.nasim.scenarios.benchmark as benchmark

from nasimemu.nasim.envs import NASimEnv
from nasimemu.nasim.envs.host_vector import HostVector
from nasimemu.env_emu import EmulatedNASimEnv
import traceback 

class TerminalAction():
    pass

# with deterministic exploits & privescs
class NASimScenarioGenerator(nasim.scenarios.generator.ScenarioGenerator):
    def _generate_exploits(self, num_exploits, exploit_cost, exploit_probs):
        rng = np.random.get_state()

        np.random.seed(12345)
        exploits = super()._generate_exploits(num_exploits, exploit_cost, exploit_probs)
        np.random.set_state(rng)

        return exploits

    def _generate_privescs(self, num_privesc, privesc_cost, privesc_probs):
        rng = np.random.get_state()

        np.random.seed(12346)
        privescs = super()._generate_privescs(num_privesc, privesc_cost, privesc_probs)
        np.random.set_state(rng)

        return privescs

class PartiallyObservableWrapper():
    def reset(self, s):
        self.__obs = dict()
        obs = self.__update_obs(s)
        return obs

    def step(self, s):
        obs = self.__update_obs(s)
        return obs

    def __update_obs(self, s):
        for host_data in s[:-1]:
            address = HostVector(host_data).address

            if address == (0, 0): # skip invalid entries
                continue

            if address in self.__obs:
                new_fields = host_data != 0
                self.__obs[address][new_fields] = host_data[new_fields]
            else:
                self.__obs[address] = host_data

        # construct and return new observation
        action_result = s[-1]
        obs = np.vstack([list(self.__obs.values()), action_result])

        return obs

# observation_format in ['matrix', 'graph']
class NASimEmuEnv(gym.Env):
    def __init__(self, scenario_name, emulate=False, step_limit=None, random_init=False, observation_format='matrix', fully_obs=False, verbose=False):
        # different processes need different seeds
        random.seed()
        np.random.seed()

        self.emulate = emulate
        self.step_limit = step_limit
        self.verbose = verbose
        self.fully_obs = fully_obs
        self.observation_format = observation_format

        self.scenario_name = scenario_name
        self.random_init = random_init

    def _generate_env(self):
        if ':' in self.scenario_name: # there are multiple possible scenarios
            scenarios = self.scenario_name.split(':')
            scenario = random.choice(scenarios)
        else:
            scenario = self.scenario_name

        if scenario.endswith(".yaml"):        # static scenario
            scenario = nasim.load_scenario(scenario)

        else:   # generated scenario
            scenario_params = benchmark.AVAIL_GEN_BENCHMARKS[scenario]
            scenario_params['step_limit'] = None

            generator = NASimScenarioGenerator()
            scenario = generator.generate(randomize_subnet_sizes=True, **scenario_params)

        if self.emulate:
            self.env = EmulatedNASimEnv(scenario=scenario)
        else:
            self.env = NASimEnv(scenario, fully_obs=self.fully_obs, flat_actions=False, flat_obs=False)

        if not self.fully_obs:
            self.env_po_wrapper = PartiallyObservableWrapper()

        # self.edge_index = self._gen_edge_index()
        self.exploit_list, self.privesc_list, self.action_list = self._create_action_lists()
        self.action_cls = [x[0] for x  in self.action_list]

        host_num_map = self.env.scenario.host_num_map
        self.host_index = np.array( sorted(host_num_map, key=host_num_map.get) )# fixed order node index
        self.subnet_index = np.array( [(x, -1) for x in range(len(self.env.scenario.subnets))] )

        self.discovered_subnets = set()
        self.subnet_graph = set() # (from, to)

    def _create_action_lists(self):
        exploit_list = sorted(self.env.scenario.exploits.items())
        privesc_list = sorted(self.env.scenario.privescs.items())

        action_list = [
                (ServiceScan, {'cost': self.env.scenario.service_scan_cost}),
                (OSScan, {'cost': self.env.scenario.os_scan_cost}),
                (SubnetScan, {'cost': self.env.scenario.subnet_scan_cost}),
                (ProcessScan, {'cost': self.env.scenario.process_scan_cost}),
        ]

        for exploit_name, exploit_params in exploit_list:
            action_list.append( (Exploit, {'name': exploit_name, **exploit_params}))

        for privesc_name, privesc_params in privesc_list:
            action_list.append( (PrivilegeEscalation, {'name': privesc_name, **privesc_params}))

        return exploit_list, privesc_list, action_list

    def _translate_action(self, action):
        target, action_id = action

        if action_id == -1: # terminal action
            return TerminalAction()

        a_class, a_params = self.action_list[action_id]
        # print(a_class, a_params, target, action_id)
        a = a_class(target=tuple(target), **a_params)

        if not self.emulate: # in emulation, we don't know the exact scenario configuration; hence the actions can be different
            assert a in self.env.action_space.actions, "Failed to execute " + str(a)

        return a

    def _get_subnets(self, s):
        return {HostVector(x).address[0] for x in s[:-1]}

    # action = ((subnet, host), action_id)
    def step(self, action):
        if type(action) in [np.ndarray, list, tuple]:
            a = self._translate_action(action)
        else:
            a = action

        if isinstance(a, TerminalAction):
            s, r, d, i = self.env.step(NoOp())
            r = 0.
            d = True

        else:
            s, r, d, i = self.env.step(a)
            d = False # ignore done flag from the environment, the agent has to choose to terminate

        r /= 10. # reward scaling
        if not self.fully_obs:
            s = self.env_po_wrapper.step(s)

        # track newly discovered subnets and remember the origin
        if isinstance(a, SubnetScan):
            s_subnets = self._get_subnets(s)
            new_subnets = s_subnets - self.discovered_subnets
            origin_subnet = a.target[0]

            for new_subnet in new_subnets:
                self.subnet_graph.add( (origin_subnet, new_subnet) )

            self.discovered_subnets = s_subnets

        self.step_idx += 1

        if self.verbose:
            print("===========================================")
            print(f"Step: {self.step_idx}")
            # print(f"Raw state: \n {s}")
            print(f"Action: {a}")
            print(f"R: {r} D: {d}")
            print(f"Info: {i}")

            self.env.render(obs=s)
            # self.env.render() # show observation

        i['s_raw'] = s
        i['a_raw'] = a

        if self.observation_format == 'graph':
            s = env_utils.convert_to_graph(s, self.subnet_graph)

        i['s_true'] = s
        i['d_true'] = d
        i['step_idx'] = self.step_idx
        i['subnet_graph'] = self.subnet_graph

        if (self.step_limit is not None) and (self.step_idx >= self.step_limit):
            d = True

        if d:
            s = self.reset()

        i['done'] = d
        i['d_true'] = d # fix: this will disable the difference between true termination and step_limit exceedance - both are treated the same

        return s, r, d, i

    def reset(self):
        self.step_idx = 0
        self._generate_env() # generate new env

        s = self.env.reset()

        if not self.fully_obs:
            s = self.env_po_wrapper.reset(s)

        self.discovered_subnets = self._get_subnets(s)
        self.subnet_graph = set()

        if self.observation_format == 'graph':
            s = env_utils.convert_to_graph(s, self.subnet_graph)

        # break the tie with random offset
        if self.random_init:
            self.step_idx = np.random.randint(self.step_limit)
            self.random_init = False

        if self.verbose:
            print()
            print("-------")
            print("reset()")
            print("-------")
            self.env.render_state()
            self.env.render(obs=s)

        return s

    def render(self, s):
        self.env.render(obs=s)

    def render_state(self):
        self.env.render_state()