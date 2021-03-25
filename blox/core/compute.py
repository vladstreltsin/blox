from __future__ import annotations
from blox.etc.errors import ComputeError
from blox.core.block import Block
from blox.core.events import LinkPostConnect, LinkPreDisconnect, NodePostRename
import networkx as nx
import typing as tp
from collections import deque

if tp.TYPE_CHECKING:
    from blox.core.state import State
    from blox.core.port import Port


class PullResult:
    pass


class Done(PullResult):
    __slots__ = ('value', )

    def __init__(self, value):
        self.value = value


class Next(PullResult):
    __slots__ = ('port', )

    def __init__(self, port):
        self.port = port


class TopoSort:
    """ Topological sort of children blocks """

    def __init__(self, block: Block):
        self._block = block
        self._changed = True
        self._essential_blocks_toposort = []
        self._dangling_blocks_toposort = []

    def reset(self):
        self._changed = True

    def _sort(self):

        # Create link graph
        graph = nx.DiGraph()
        for p1, p2 in self._block.links():
            graph.add_edge(p1, p2)

        # Use the port equivalence relation p1 ~ p2 <=> p1.block == p2.block to
        # convert the port graph to block graph. The function nx.quotient_graph will
        # create a graph whose labels are frozenset object. We convert them to block objects
        block_graph = nx.quotient_graph(graph, partition=lambda x, y: x.block == y.block)
        block_graph = nx.relabel_nodes(block_graph, mapping=lambda x: next(iter(x)).block)

        # Add all block's children to the graph, in case some don't have any edges
        # for child in self.block.children:
        for child in self._block.blocks:
            block_graph.add_node(child)

        self._essential_blocks_toposort = []
        self._dangling_blocks_toposort = []

        for ccomp in nx.weakly_connected_components(block_graph):

            # The essential component is the one in which the parent block is in
            if self._block in ccomp:
                if len(ccomp) > 1:
                    sub_graph = nx.subgraph(block_graph, ccomp - {self._block})
                    self._essential_blocks_toposort.extend(nx.topological_sort(sub_graph))
            else:
                sub_graph = nx.subgraph(block_graph, ccomp)
                self._dangling_blocks_toposort.extend(nx.topological_sort(sub_graph))

        self._changed = False

    def __iter__(self):
        if self._changed:
            self._sort()
        return iter(self._essential_blocks_toposort)


class Computable(Block):
    """ Base class for all computable blocks implementing the pull, push, propagate methods """

    def __init__(self, *args, **kwargs):
        super(Computable, self).__init__(*args, **kwargs)
        self._toposort = TopoSort(self)

    def pull(self, port, state):
        """
        Compute a port's value using the pull protocol.
        """
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        stack = deque()
        arrow = Next(port)

        while True:
            # We always enter the loop with an arrow
            if isinstance(arrow, Done):

                if len(stack) == 0:
                    return arrow.value

                else:
                    arrow = stack[-1].send(arrow.value)
                    if isinstance(arrow, Done):
                        stack.pop()

            elif isinstance(arrow, Next):

                port = arrow.port
                gen = port.block.pull_generator(port, state)

                arrow = next(gen)
                if isinstance(arrow, Next):
                    stack.append(gen)

            else:
                raise ComputeError(f'Got unknown type for pull result {type(arrow)}')

    def pull_generator(self, port: Port, state: State):
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        if port in state:
            yield Done(state[port])

        if port.upstream is None:
            raise ComputeError(f'Trying to pull on port {port} without an upstream')

        value = yield Next(port.upstream)
        state[port] = value

        yield Done(value)

    def push(self, port: Port, state: State):
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        if port not in state:
            raise ComputeError(f'Trying to push the port {port} that has no value')

        for p in port.downstream:
            state[p] = state[port]

        if port.meta.get('propagate_cleanup'):
            del state[port]

    def propagate(self, state: State):
        # Push all inputs
        for port in self.In:
            port.block.push(port, state)

        # Propagate essential children (in topological order)
        for child in self._toposort:
            child.propagate(state)

            for port in child.Out:
                port.block.push(port, state)

    def handle(self, event):
        super(Computable, self).handle(event)

        # Detect a link change (while the the links still exist)
        # Links are those port connections where
        #   * upstream is an In port of self
        #   * upstream is an Out port of a child of self
        # In such case, the toposort must be reset
        if isinstance(event, LinkPreDisconnect) or isinstance(event, LinkPostConnect):
            port1 = event.port1
            if port1 in self.In or (port1.block in self.blocks and port1 in port1.block.Out):
                self._toposort.reset()


class Function(Computable):

    def pull_generator(self, port: Port, state: State):
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        if port in state:
            yield Done(state[port])

        # Input ports are simply pulled
        if port in self.In:
            gen = super(Function, self).pull_generator(port, state)

            # The following code does the following:
            # a. Gets the first command from the generator (should be Next(...))
            # b. Until it gets a Done(...) it yields the command back to the calling method
            #    (that effectively serves as an 'event loop'). Then, it passes the received
            #    result back to the generator to get a new command.
            pull_result = next(gen)
            while not isinstance(pull_result, Done):
                pull_result = gen.send((yield pull_result))

        # For output ports we first pull the inputs and then propagate
        else:
            for p in self.In:
                gen = super(Function, self).pull_generator(p, state)

                pull_result = next(gen)
                while not isinstance(pull_result, Done):
                    pull_result = gen.send((yield pull_result))

            self.propagate(state)

        assert port in state
        yield Done(state[port])


class AtomicFunction(Function):

    def __init__(self, *args, **kwargs):
        super(AtomicFunction, self).__init__(*args, **kwargs)

    def callback(self,
                 ports: tp.Dict[str, tp.Any],
                 meta: tp.Dict[str, tp.Any],
                 params: tp.Dict[str, tp.Any]):
        raise NotImplementedError

    def propagate(self, state: State):

        # Get inputs
        ports = {port.name: state[port] for port in self.In}
        meta = state.meta

        # Collect parameters for the current block
        params = state.params[self] if self in state.params else {}

        # Compute the function
        result = self.callback(ports=ports, meta=meta, params=params)

        # TODO this parameter should be overridable by params or meta
        # Memory maintenance
        for port in self.In:
            if port.meta.get('propagate_cleanup'):
                del state[port]

        # Set outputs
        if len(self.Out) == 1:
            state[self.Out()] = result
        else:
            if len(self.Out) != len(result):
                raise ComputeError(f"In Function {self}: expected {len(self.Out)} outputs, got {len(result)}")

            for out_port, value in zip(self.Out, result):
                state[out_port] = value


