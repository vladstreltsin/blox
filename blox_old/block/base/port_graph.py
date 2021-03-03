from __future__ import annotations
import typing as tp
from itertools import chain
import networkx as nx

if tp.TYPE_CHECKING:
    from blox_old.block.base.block_base import BlockBase


class PortGraph:

    def __init__(self, block):
        self._block = block
        self._graph = nx.DiGraph()
        self._changed = True

        self._essential_blocks_toposort = None
        self._dangling_blocks_toposort = None

    @property
    def block(self):
        return self._block

    @property
    def changed(self):
        return self._changed

    def set_changed(self):
        self._changed = True
        self.block.on_port_graph_change()

    def add_edge(self, *args, **kwargs):
        self._graph.add_edge(*args, **kwargs)
        self.set_changed()

    def add_node(self, *args, **kwargs):
        self._graph.add_node(*args, **kwargs)
        self.set_changed()

    def __contains__(self, item):
        return item in self._graph

    def remove_edge(self, *args, **kwargs):
        self._graph.remove_edge(*args, **kwargs)
        self.set_changed()

    def remove_node(self, *args, **kwargs):
        self._graph.remove_node(*args, **kwargs)
        self.set_changed()

    def in_edges(self, *args, **kwargs):
        return self._graph.in_edges(*args, **kwargs)

    def out_edges(self, *args, **kwargs):
        return self._graph.out_edges(*args, **kwargs)

    def in_degree(self, *args, **kwargs):
        return self._graph.in_degree(*args, **kwargs)

    def out_degree(self, *args, **kwargs):
        return self._graph.out_degree(*args, **kwargs)

    def edges(self):
        yield from self._graph.edges

    def toposort(self):

        if self._changed:
            # Use the port equivalence relation p1 ~ p2 <=> p1.block == p2.block to
            # convert the port graph to block graph. The function nx.quotient_graph will
            # create a graph whose labels are frozenset object. We convert them to block objects
            block_graph = nx.quotient_graph(self._graph, partition=lambda x, y: x.block == y.block)
            block_graph = nx.relabel_nodes(block_graph, mapping=lambda x: next(iter(x)).block)

            # Add all block's children to the graph, in case some don't have any edges
            # for child in self.block.children:
            for child in self.block.blocks:
                block_graph.add_node(child)

            self._essential_blocks_toposort = []
            self._dangling_blocks_toposort = []

            for ccomp in nx.weakly_connected_components(block_graph):

                # The essential component is the one in which the parent block is in
                if self.block in ccomp:
                    if len(ccomp) > 1:
                        sub_graph = nx.subgraph(block_graph, ccomp - {self.block})
                        self._essential_blocks_toposort.extend(nx.topological_sort(sub_graph))
                else:
                    sub_graph = nx.subgraph(block_graph, ccomp)
                    self._dangling_blocks_toposort.extend(nx.topological_sort(sub_graph))

            self._changed = False

    def topo_blocks_essential(self) -> tp.Iterable[BlockBase]:
        self.toposort()
        yield from self._essential_blocks_toposort

    def topo_blocks_dangling(self) -> tp.Iterable[BlockBase]:
        self.toposort()
        yield from self._dangling_blocks_toposort

    def topo_blocks(self) -> tp.Iterable[BlockBase]:
        self.toposort()
        yield from chain(self._essential_blocks_toposort, self._dangling_blocks_toposort)
