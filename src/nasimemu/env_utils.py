from nasimemu.nasim.envs.host_vector import HostVector
import numpy as np

def get_possible_actions(env, s):
    # gather all possible addresses
    addresses = []
    for host_data in s[:-1]:
        host_vector = HostVector(host_data)
        addresses.append(host_vector.address)

    possible_actions = []

    for host_add in addresses:
        possible_actions.extend([(host_add, action_id) for action_id in range(len(env.action_list))]) 

    return possible_actions

def _gen_edge_index(node_index, subnets):
    def complete_graph(n):
        return [(a, b) for a in n for b in n if a != b]

    edge_index = []

    # hosts in subnets are connected together
    for subnet in subnets:
        hosts_in_subnet = np.flatnonzero( node_index[:, 0] == subnet )
        edge_index.append( complete_graph(hosts_in_subnet) )

    # all subnets together
    sub_index = np.flatnonzero( node_index[:, 1] == -1 )
    if len(sub_index) > 1:
        edge_index.append( complete_graph(sub_index) )

    # print(edge_index)
    edge_index = np.concatenate(edge_index).T
    return edge_index


def convert_to_graph(s):
    hosts_discovered = s[:-1, HostVector._discovered_idx] == 1

    host_feats = s[:-1][hosts_discovered]
    action_feats = s[-1] # TODO: discarded for now

    host_index = np.array([HostVector(x).address for x in host_feats])
    # host_index = self.host_index[hosts_discovered]

    subnets_discovered = list( {x[0] for x in host_index} )
    subnet_index = np.array( [(x, -1) for x in subnets_discovered])
    # subnet_index = self.subnet_index[subnets_discovered]
    subnet_feats = np.eye(max(subnets_discovered)+1, host_feats.shape[1])[subnets_discovered]

    # subnet 0 is internet, and will always be empty

    node_type = np.zeros( (len(host_feats) + len(subnet_feats), 1) )
    node_type[len(host_feats):] = 1     # 0 for hosts; 1 for subnets

    node_feats = np.concatenate( [host_feats, subnet_feats] )
    node_feats = np.concatenate( [node_type, node_feats], axis=1 )

    node_index = np.concatenate( [host_index, subnet_index] )

    # create edge index
    edge_index = _gen_edge_index(node_index, subnets_discovered)

    return node_feats, edge_index, node_index