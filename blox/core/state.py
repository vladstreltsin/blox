from __future__ import annotations
from abc import ABC, abstractmethod
import typing as tp
from collections import UserDict
from scalpl import Cut
from collections import namedtuple, defaultdict

if tp.TYPE_CHECKING:
    from blox.core.port import Port
    from blox.core.block import Block

ExportResult = namedtuple('ExportResult', field_names=['ports', 'meta', 'params'])


class Exporter:
    """ Exports State to a dictionary """

    def __init__(self, root: Block):
        self.root = root

    def __call__(self, state: State):

        from blox.core.port import Port
        from blox.core.filters import port_filter, block_filter

        ports = {}
        params = {}
        meta = {**state.meta}

        for port in self.root.descendants(lambda p: port_filter(p) and p in state):
            assert isinstance(port, Port)
            ports[port.rel_name(self.root)] = state[port]

        for block in self.root.descendants(lambda b: block_filter(b) and b in state.params):
            assert isinstance(block, Block)
            params[block.rel_name(self.root)] = state.params[block]

        return ExportResult(ports=ports, meta=meta, params=params)


class Importer:
    """ Imports State from a dictionary """

    def __init__(self, root: Block):
        self.root = root

    def __call__(self,
                 ports: tp.Dict[str, tp.Any],
                 meta: tp.Dict[str, tp.Any],
                 params: tp.Dict[str, tp.Dict[str, tp.Any]]) -> State:

        from blox.core.port import Port

        # This allows xpath-like access to blocs
        cut = Cut({self.root.name: self.root}, sep=self.root.separator)

        state = State()
        state.meta.update(meta)

        for key, value in ports.items():

            try:
                port_name = self.root.separator.join([self.root.full_name, key])
                port = cut[port_name]
            except KeyError:
                raise KeyError(f'No such port {port_name}')

            if not isinstance(port, Port):
                raise TypeError(f'Path {port_name} does not correspond to a port (given: {port})')

            state[port] = value

        for key, value in params.items():

            try:
                block_name = self.root.separator.join([self.root.full_name, key])
                block = cut[block_name]
            except KeyError:
                raise KeyError(f'No such block {block_name}')

            if not isinstance(block, Block):
                raise TypeError(f'Path {block_name} does not correspond to a block (given: {block})')

            state.params[block] = value

        return state


class State(UserDict):
    """ Stores the values of ports during computation """

    def __init__(self):
        super(State, self).__init__()

        # This will contain extra global parameters
        self.meta: tp.Dict[str, tp.Any] = dict()

        # This will contain per-block parameters
        self.params: tp.Dict[Block, tp.Dict[str, tp.Any]] = defaultdict(dict)

    def __getitem__(self, port: Port):
        if port not in self:
            raise KeyError(f'No value for port {port.full_name}')
        return super(State, self).__getitem__(port)

    def __call__(self, port: Port):
        return port.block.pull(port, self)
