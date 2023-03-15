import networkx as nx 
import plotly.graph_objects as go
import plotly.io as pio   
import numpy as np
import argparse, yaml, string, pathlib, math

def plot(graph, node_data):
    edge_x = []
    edge_y = []
    for edge in graph.edges():
        x0, y0 = node_data['x'][edge[0]], node_data['y'][edge[0]]
        x1, y1 = node_data['x'][edge[1]], node_data['y'][edge[1]]
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

    node_trace = go.Scatter(
        node_data,
        mode='markers+text',
        # hoverinfo='text',
        # marker=dict(showscale=False, size=15,),
        textposition="top center")

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0,l=0,r=0,t=0),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)),
                    )

    return fig

def make_graph(scenario):
    topology = np.array(scenario['topology'])
    graph = nx.from_numpy_array(topology)
    node_positions = nx.kamada_kawai_layout(graph)
    node_positions = np.stack([(node_positions[node]) for node in graph.nodes])

    node_data = {}
    node_data['x'] = node_positions[:, 0]
    node_data['y'] = node_positions[:, 1]

    subnet_annotation = lambda node_id: f'<b>Subnet {string.ascii_uppercase[node_id-1]} ({scenario["subnet_labels"][node_id]})</b><br>nodes=[{scenario["subnets"][node_id-1]}], sensitivity={scenario["sensitive_hosts"][node_id]}'
    node_color = lambda node_id: f'rgb({scenario["sensitive_hosts"][node_id] * 191 + 64}, 64, 64)'
    
    def node_size(node_id):
        sub = scenario["subnets"][node_id-1]
        if type(sub) is str:
            sub_size = int(scenario["subnets"][node_id-1].split('-')[-1])
        else:
            sub_size = sub

        return math.sqrt(sub_size) * 20

    node_data['text']  = ['<b>Attacker</b>' if node_id == 0 else subnet_annotation(node_id) for node_id in graph.nodes]
    node_data['marker'] = dict(opacity=1.0, size=[20 if node_id == 0 else node_size(node_id) for node_id in graph.nodes], color=['orange' if node_id == 0 else node_color(node_id) for node_id in graph.nodes])

    return graph, node_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('scenario', type=str, help='v2.yaml scenario file')
    cmd_args = parser.parse_args()

    # load yaml
    with open(cmd_args.scenario, 'r') as stream:
        scenario = yaml.safe_load(stream)

    graph, node_data = make_graph(scenario)
    fig = plot(graph, node_data)

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # fig.show()

    fig.update_xaxes(range=[-1.5, 1.5])
    fig.update_yaxes(range=[-1.5, 1.5])

    pdf_file = pathlib.Path(cmd_args.scenario).with_suffix('.pdf')
    print(f'Exporting to "{pdf_file}"')

    pio.kaleido.scope.mathjax = None
    fig.write_image(pdf_file, width=500, height=500, scale=1.0)
