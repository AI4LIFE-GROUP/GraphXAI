import sys, time, os, pickle
import torch
import networkx as nx
import matplotlib.pyplot as plt

from graphxai.datasets.shape_graph import ShapeGraph
from graphxai.datasets import load_ShapeGraph


start_time = time.time()

SG = ShapeGraph(
    model_layers = 3,
    make_explanations=True,
    num_subgraphs = 1200,
    prob_connection = 0.0075,
    subgraph_size = 12,
    class_sep = 0.5,
    n_informative = 6,
    verify = True
)

SG.dump('large_graph.pickle')
print('Time to make:', time.time() - start_time)

# tmp_loc = root_data = os.path.join('/Users/owenqueen/Desktop/data', 'ShapeGraph')
# SG = load_ShapeGraph(number=2, root = tmp_loc)

data = SG.get_graph()
G = SG.G

print('\t Size:', SG.num_nodes)
print('\t Class 0:', torch.sum(data.y == 0))
print('\t Class 1:', torch.sum(data.y == 1))

# Get degree distribution of G:
degrees = sorted([d for n, d in G.degree()])

variant_code = 'PA'

plt.hist(degrees, color = 'green')
plt.title('Degree Distribution - {}'.format(variant_code))
plt.xlabel('Degree')
plt.ylabel('Frequency')
plt.show()