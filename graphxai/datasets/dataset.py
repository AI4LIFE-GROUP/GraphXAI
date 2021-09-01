from graphxai.utils.explanation import EnclosingSubgraph
import torch

import pandas as pd
from graphxai.utils import Explanation#, WholeGraph

from torch_geometric.data import Dataset, Data
from torch_geometric.utils import k_hop_subgraph
from sklearn.model_selection import train_test_split

from typing import List, Optional, Callable, Union, Any, Tuple

def get_dataset(dataset, download = False):
    '''
    Base function for loading all datasets.
    Args:
        dataset (str): Name of dataset to retrieve.
        download (bool): If `True`, downloads dataset to local directory.
    '''

    if dataset == 'MUTAG':
        # Get MUTAG dataset
        return MUTAG_Dataset()
    else:
        raise NameError("Cannot find dataset '{}'.".format(dataset))

class NodeDataset:
    def __init__(self, 
        name, 
        num_hops: int,
        download: Optional[bool] = False,
        root: Optional[str] = None
        ):
        self.name = name
        self.num_hops = num_hops

        #self.graph = WholeGraph() # Set up whole_graph with all None
        self.explanations = []

    def get_graph(self, 
        use_static_split = True, 
        split_sizes = (0.7, 0.2, 0.1),
        seed = None):
        '''
        Gets graph object for training/validation/testing purposes
            - Sets masks within torch_geometric.data.Data object
        Args:
            use_static_split (bool, optional): (:default: True)
        '''

        if use_static_split:
            # Set train, test, val static masks:
            self.graph.train_mask = self.static_train_mask
            self.graph.valid_mask = self.static_valid_mask
            self.graph.test_mask  = self.static_test_mask

        else:
            assert sum(split_sizes) == 1, "split_sizes must sum to 1"
            assert len(split_sizes) == 3, "split_sizes must contain (train_size, test_size, valid_size)"
            # Create a split for user (based on seed, etc.)
            train_mask, rem_mask = train_test_split(list(range(self.n)), 
                                test_size = split_sizes[1], 
                                random_state = seed)

            valid_mask, test_mask = train_test_split(rem_mask, 
                                test_size = split_sizes[2],
                                random_state = seed)

            self.graph.train_mask = torch.tensor([i in train_mask for i in range(self.graph.num_nodes)], dtype = torch.bool)
            self.graph.valid_mask = torch.tensor([i in valid_mask for i in range(self.graph.num_nodes)], dtype = torch.bool)
            self.graph.test_mask  = torch.tensor([i in test_mask  for i in range(self.graph.num_nodes)], dtype = torch.bool)

        return self.graph

    def download(self):
        pass

    def get_enclosing_subgraph(self, node_idx: int):
        '''
        Args:
            node_idx (int): Node index for which to get subgraph around
        '''
        k_hop_tuple = k_hop_subgraph(node_idx, 
            num_hops = self.num_hops, 
            edge_index = self.graph.edge_index)
        return EnclosingSubgraph(*k_hop_tuple)

    def __len__(self) -> int:
        return 1 # There is always just one graph

    @property
    def x(self):
        return self.graph.x

    @property
    def edge_index(self):
        return self.graph.edge_index

    @property
    def y(self):
        return self.graph.y

    # @property
    # def name(self):
    #     return self.name

    def __getitem__(self, idx):
        assert idx == 0, 'Dataset has only one graph'
        return self.graph, self.explanation


class GraphDataset(Dataset):
    def __init__(self, 
        name,
        download: Optional[bool] = False,
        root: Optional[str] = None
        ):

        self.name = name

        self.graph_list = []
        self.explanation_list = []
        # explanation_list - list of explanations for each graph

    def get_train_loader(
        self, 
        use_static_split = True, 
        train_size = 0.7, 
        seed = None, 
        **kwargs):
        if self.use_static_split:
            pass
        elif seed:
            self.sampled = set()
            pass
        else:
            pass

    def get_test_loader(
        self,  
        test_size = 0.2, 
        seed = None, 
        **kwargs):
        if self.use_static_split:
            # Inherited class must have all splits stored
            pass
        elif seed:
            self.sampled = set()
            pass
        else:
            pass

    def get_val_loader(
        self, 
        use_static_split = True, 
        val_size = 0.2,
        seed = None, 
        **kwargs):
        if use_static_split:
            pass
        elif seed:
            self.sampled = set()
            pass
        else:
            pass

    def download(self):
        pass

    def __getitem__(self, idx):
        return self.graph_list[idx], self.explanation_list[idx]

class MUTAG_Dataset(GraphDataset):
    def __init__(self):

        # Processing

        super().__init__(name = 'MUTAG', x = [], y = [])

        self.graphs = None

        # Load graphs here