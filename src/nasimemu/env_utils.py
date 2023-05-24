from nasimemu.nasim.envs.host_vector import HostVector
import numpy as np

import networkx as nx 
import plotly.graph_objects as go

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

def _gen_edge_index_v1(node_index, subnets):
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

def _gen_edge_index_v2(node_index, subnets):
    def complete_graph(n):
        return [(a, b) for a in n for b in n if a != b]

    edge_index = []

    # hosts in subnets are connected to their subnet
    for subnet in subnets:
        hosts_in_subnet = np.flatnonzero( node_index[:, 0] == subnet )
        subnet_node = np.flatnonzero( (node_index[:, 0] == subnet) * (node_index[:, 1] == -1))[0]

        edge_index.append( [(x, subnet_node) for x in hosts_in_subnet if x != subnet_node] )
        edge_index.append( [(subnet_node, x) for x in hosts_in_subnet if x != subnet_node] )
        # edge_index.append( complete_graph(hosts_in_subnet) )

    # all subnets together
    sub_index = np.flatnonzero( node_index[:, 1] == -1 )
    if len(sub_index) > 1:
        edge_index.append( complete_graph(sub_index) )

    # print(edge_index)
    edge_index = np.concatenate(edge_index).T
    return edge_index

# v1 = nodes are connected to each other; v2 = they're not
def convert_to_graph(s, version=1):
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
    if version == 1:
        edge_index = _gen_edge_index_v1(node_index, subnets_discovered)
    elif version == 2:
        edge_index = _gen_edge_index_v2(node_index, subnets_discovered)
    else:
        raise NotImplementedError()

    return node_feats, edge_index, node_index

# inspired from https://plotly.com/python/network-graphs/
def _plot(G, env):
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#444'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    node_symbols = []
    node_line_widths = []

    for node_id, node in G.nodes.items():
        x, y = node['pos']
        node_x.append(x)
        node_y.append(y)

        node_text.append(f"{node['label']}")
        node_color.append(node['color'])
        node_symbols.append(node['symbol'])
        node_line_widths.append(node['line_width'])

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        marker=dict(showscale=False, color=node_color, symbol=node_symbols, size=40, line_width=node_line_widths),
        text=node_text,
        textposition="top center",)

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            # family="Courier New, monospace",
            size=25
        )
    )

    return fig

def _make_graph(s, a):
    node_feats, edge_index, node_index = s

    G = nx.Graph() 
    G.add_edges_from(edge_index.T) 
    pos = nx.kamada_kawai_layout(G)

    def get_host_conf(host_id):
        host_vec = HostVector(node_feats[host_id][1:])

        running_services = []
        for srv_name in HostVector.service_idx_map:
            if host_vec.is_running_service(srv_name):
                running_services.append(srv_name.split('_')[-1])

        service_str = ", ".join(running_services)
        if service_str:
            service_str = "<br>" + service_str

        return service_str

    def get_host_string(i):
        node_idx = node_index[i]
        host_conf = get_host_conf(i)
        node_action = a.name if np.all(np.array(a.target) == np.array(node_idx)) else ""

        access_colors = ['black', 'orange', 'red']
        node_str = f"<span style='color:{access_colors[is_host_controlled(i)]};'>{node_idx}</span>"

        return f"{node_str} <b>{node_action}</b>{host_conf}"

    def is_host_sensitive(i):
        host_vec = HostVector(node_feats[i][1:])
        return host_vec.value > 0

    def is_host_controlled(i):
        host_vec = HostVector(node_feats[i][1:])
        return int(host_vec.access)

    def get_node_color(i):
        if node_index[i][1] == -1:
            return 'seagreen'
        else:
            return 'red' if is_host_sensitive(i) else 'skyblue'


    node_labels = {i: f"Subnet {node_index[i][0]}" if node_index[i][1] == -1 else get_host_string(i) for i in G.nodes}
    node_types = {i: 'subnet' if node_index[i][1] == -1 else 'node' for i in G.nodes}
    node_colors = {i: get_node_color(i) for i in G.nodes}
    node_symbols = {i: 'triangle-up' if node_index[i][1] == -1 else 'circle' for i in G.nodes}
    node_line_widths = {i: 4.0 if np.all(np.array(a.target) == np.array(node_index[i])) else 1.0 for i in G.nodes}

    nx.set_node_attributes(G, pos, 'pos')
    nx.set_node_attributes(G, node_labels, 'label')
    nx.set_node_attributes(G, node_types, 'type')
    nx.set_node_attributes(G, node_colors, 'color')
    nx.set_node_attributes(G, node_symbols, 'symbol')
    nx.set_node_attributes(G, node_line_widths, 'line_width')

    return G

def plot_network(env, s, last_action):
    s_graph = convert_to_graph(s, version=2)
    G = _make_graph(s_graph, last_action)
    fig = _plot(G, env)
    
    # use:
    # fig.show()

    # or:
    # pio.kaleido.scope.mathjax = None
    # fig.write_image(f"trace.pdf", width=1200, height=600, scale=1.0)

    return fig