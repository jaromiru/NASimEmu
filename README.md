# NASimEmu: Network Attack Simulator & Emulator

<div align=center>
    <img src="docs/nasimemu_trace.svg" alt="NASimEmu observation" width="75%" height="75%">
</div>

## Introduction
This project is based on [Network Attack Simulator](https://github.com/Jjschwartz/NetworkAttackSimulator), a framework for simulating offensive reinforcement-learning based agents in a computer network, using the [OpenAI Gym](https://github.com/openai/gym) interface. NaSimEmu extends this framework in two ways. First, it bring changes that allows much more realistic settings. Second, it provides an **emulation with virtual machines**, which share the same interface with simulation. Moreover, the same scenario can be easily run in simulation and emulation. Hence, an agent trained in simulation can be deployed in emulation without change.

## Instalation
Make sure you use latest `pip`:
```
pip install --upgrade pip
```

Clone the repository and install it locally (`-e` for development mode):
```
git clone https://github.com/jaromiru/NASimEmu.git
cd NASimEmu; pip install -e .
```

To use emulation, you have to install [Vagrant](https://developer.hashicorp.com/vagrant/downloads) yourself; see [EMULATION](docs/EMULATION.md).

## Usage
```python
import gym, random, logging
import nasimemu, nasimemu.env_utils as env_utils

# In this example, a scenario instance is randomly generated from either 'entry_dmz_one_subnet' or 'entry_dmz_two_subnets' on every new episode. Make sure the path to scenarios is correct.
# To use emulation, setup Vagrant and change emulate=True.
env = gym.make('NASimEmu-v0', emulate=False, scenario_name='scenarios/entry_dmz_one_subnet.v2.yaml:scenarios/entry_dmz_two_subnets.v2.yaml')
s = env.reset()

# To see the emulation logs, uncomment the following:
# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('urllib3').setLevel(logging.INFO)

# To see the whole network, use (only in simulation):
# env.render_state()

for _ in range(3):
    actions = env_utils.get_possible_actions(env, s)
    env.render(s)

    # you can convert the observation into a graph format (e.g., for Pytorch Geometric) as:
    # s_graph = env_utils.convert_to_graph(s)

    action = random.choice(actions)
    s, r, done, info = env.step(action)

    print(f"Possible actions: {actions}")

    (action_subnet, action_host), action_id = action
    print(f"Taken action: {action}; subnet_id={action_subnet}, host_id={action_host}, action={env.action_list[action_id]}")
    print(f"reward: {r}, done: {done}\n")
    input()
```

## Gym integration
NASimEmu currently doesn't support many of the default agents made for gym, because it uses custom environment spaces (the size of the environment is unknown to the attacker at the beginning) and an action space that changes at each step when a new host is discovered.

## Implemented Deep RL Agents
See the separate repository [NASimEmu-agents](https://github.com/jaromiru/NASimEmu-agents) for implemented agents.

## Simulation
The simulation is based on Network Attack Simulator and you can read its docs here: https://networkattacksimulator.readthedocs.io

These are the changes in NaSimEmu:

- Support for new [v2 scenarios](docs/SCENARIOS.md), which define classes of problems from which random instances are generated. The v2 scenarios define a topology, sensitive subnets, services, processes and exploits. However, the generated instances vary in number of hosts in subnets and hosts' configuration. For example, you can define scenarios representing "bank", "university" or "enterprise" domains.
- Agent can be trained or deployed in multiple scerarios at once. This is useful to test generalization and transfer learning of the agent. E.g., how does it perform in the "enterprise" scenario when trained only in "bank" and "university"?
- The interface has been changed to true partial observability. That is, the agent cannot infer the number of hosts or subnets in the current scenario instance and all other unknown information is masked. To aleviate memorization of acquired information, the observation at each step records all the information gathered so far. Further, host and subnet ids are scrambled to avoid their memorization.

## Emulation
The emulation is made with [Vagrant](https://www.vagrantup.com/) and [VirtualBox](https://www.virtualbox.org/). You will need to install these on your system first. A scenario is converted into a Vagrantfile and deployed. The vagrant spawns a virtual machine for each host in the scenario (currently, Ubuntu and Windows machines are available) and configures them properly. Additionally, it deploys one [RouterOS](https://wiki.mikrotik.com/wiki/Manual:RouterOS_FAQ) based router that segments the network into subnets and one attacker machine that runs [Kali Linux](https://www.kali.org/) and uses [Metasploit](https://www.metasploit.com/) with pre-configured exploits to run.

For more information about emulation, see [EMULATION](docs/EMULATION.md).

## Limitations / Properties
Please, be aware of the following:

- exploits are assumed to always work (in emulation, this is not true)
- the services have a single version and are always exploitable, if the exploit is defined
- currently, the maximum number of subnets and hosts in subnets have to be defined, so that the host vector size is always the same
- if there are multiple paths from the attacker to a target (some of which are filtered by firewalls), the simulator assumes that the host is exploitable if any of the paths allow it; in emulation, this is not implemented (the first discovered path will be used); avoid doing this
- we assume that a firewall either block or allows **all** traffic between subnets
- in emulation, all hosts are on the same interface, which is only virtually segmented by the router; avoid using protocols that bypass the router (such as ARP)
- if defined in the scenario, sensitive services always run on all sensitive nodes; sensitive services also run on 10% of non-sensitive nodes
- emulation do not provide any rewards

## Acknowledgements

[@bastien-buil](https://www.github.com/bastien-buil) - windows emulation, bugfixes and part of documentation
