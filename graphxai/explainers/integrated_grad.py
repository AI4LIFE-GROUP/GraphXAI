import torch
from torch_geometric.utils import k_hop_subgraph
from torch_geometric.data import Data

from graphxai.explainers._base import _BaseExplainer
from graphxai.utils import Explanation

device = "cuda" if torch.cuda.is_available() else "cpu"


class IntegratedGradExplainer(_BaseExplainer):
    """
    Integrated Gradient Explanation for GNNs
    """
    def __init__(self, model, criterion):
        """
        Args:
            model (torch.nn.Module): model on which to make predictions
            criterion (torch.nn.Module): loss function
        """
        super().__init__(model)
        self.criterion = criterion

    def get_explanation_node(self, node_idx: int, x: torch.Tensor,
                             edge_index: torch.Tensor, 
                             label: torch.Tensor = None,
                             y = None,
                             num_hops: int = None, **_):
        """
        Explain a node prediction.

        Args:
            node_idx (int): index of the node to be explained
            edge_index (torch.Tensor, [2 x m]): edge index of the graph
            x (torch.Tensor, [n x d]): node features
            label (torch.Tensor, [n x ...]): labels to explain
            num_hops (int): number of hops to consider

        Returns:
            exp (dict):
                exp['feature_imp'] (torch.Tensor, [d]): feature mask explanation
                exp['edge_imp'] (torch.Tensor, [m]): k-hop edge importance
                exp['node_imp'] (torch.Tensor, [m]): k-hop node importance
            khop_info (4-tuple of torch.Tensor):
                0. the nodes involved in the subgraph
                1. the filtered `edge_index`
                2. the mapping from node indices in `node_idx` to their new location
                3. the `edge_index` mask indicating which edges were preserved
        """
        exp = dict()

        if (label is None) and (y is None):
            raise ValueError('Either label or y should be provided for Integrated Gradients')

        label = y[node_idx] if label is None else label 

        num_hops = num_hops if num_hops is not None else self.L
        khop_info = subset, sub_edge_index, mapping, _ = \
            k_hop_subgraph(node_idx, num_hops, edge_index,
                           relabel_nodes=True, num_nodes=x.shape[0])
        sub_x = x[subset]

        steps = 40

        self.model.eval()
        grads = torch.zeros(steps+1, x.shape[1]).to(device)
        for i in range(steps+1):
            with torch.no_grad():
                baseline = torch.zeros_like(sub_x).to(device)  # TODO: baseline all 0s, all 1s, ...?
                temp_x = baseline + (float(i)/steps) * (sub_x.clone()-baseline)
            temp_x.requires_grad = True
            output = self.model(temp_x, sub_edge_index)
            loss = self.criterion(output[mapping], label)
            loss.backward()
            grad = temp_x.grad[torch.where(subset==node_idx)[0].item()]
            grads[i] = grad

        grads = (grads[:-1] + grads[1:]) / 2.0
        avg_grads = torch.mean(grads, axis=0)

        # Integrated gradients for only node_idx:
        # baseline[0] just gets a single-value 0-tensor
        integrated_gradients = ((x[torch.where(subset == node_idx)[0].item()]
                                 - baseline[0]) * avg_grads)

        # Integrated gradients across the enclosing subgraph:
        all_node_ig = ((x[subset] - baseline) * avg_grads)

        exp = Explanation(
            feature_imp = integrated_gradients,
            node_imp = torch.sum(all_node_ig, dim=1),
            node_idx = node_idx
        )
        exp.set_enclosing_subgraph(khop_info)

        return exp

    def get_explanation_graph(self, edge_index: torch.Tensor,
                              x: torch.Tensor, 
                              y: torch.Tensor = None,
                              label: torch.Tensor = None,
                              forward_kwargs={}):
        """
        Explain a whole-graph prediction.

        Args:
            edge_index (torch.Tensor, [2 x m]): edge index of the graph
            x (torch.Tensor, [n x d]): node features
            label (torch.Tensor, [n x ...]): labels to explain
            forward_args (tuple, optional): additional arguments to model.forward
                beyond x and edge_index

        Returns:
            exp (dict):
                exp['feature_imp'] (torch.Tensor, [d]): feature mask explanation
                exp['edge_imp'] (torch.Tensor, [m]): k-hop edge importance
                exp['node_imp'] (torch.Tensor, [m]): k-hop node importance
        """
        exp = dict()

        steps = 40

        if (label is None) and (y is None):
            raise ValueError('Either label or y should be provided for Integrated Gradients')

        label = y if label is None else label 

        self.model.eval()
        grads = torch.zeros(steps+1, *x.shape)
        baseline = torch.zeros_like(x)  # TODO: baseline all 0s, all 1s, ...?
        for i in range(steps+1):
            with torch.no_grad():
                temp_x = baseline + (float(i)/steps) * (x.clone()-baseline)
            temp_x.requires_grad = True
            if forward_kwargs is None:
                output = self.model(temp_x, edge_index)
            else:
                output = self.model(temp_x, edge_index, **forward_kwargs)
            loss = self.criterion(output, label)
            loss.backward()
            grad = temp_x.grad
            grads[i] = grad

        grads = (grads[:-1] + grads[1:]) / 2.0
        avg_grads = torch.mean(grads, axis=0)
        integrated_gradients = (x - baseline) * avg_grads
        #exp['feature_imp'] = integrated_gradients

        exp = Explanation(
            node_imp = integrated_gradients,
        )

        exp.set_whole_graph(Data(x=x, edge_index=edge_index))

        return exp

    def get_explanation_link(self):
        """
        Explain a link prediction.
        """
        raise NotImplementedError()
