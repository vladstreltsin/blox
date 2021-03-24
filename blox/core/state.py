from __future__ import annotations
from abc import ABC, abstractmethod
import typing as tp
from collections import UserDict
from scalpl import Cut
from collections import namedtuple

if tp.TYPE_CHECKING:
    from blox.core.port import Port
    from blox.core.block import Block

ExportResult = namedtuple('ExportResult', field_names=['ports', 'meta'])


class Exporter:
    """ Exports State to a dictionary """

    def __init__(self, root: Block):
        self.root = root

    def __call__(self, state: State):

        from blox.core.port import Port
        from blox.core.filters import port_filter

        ports = {}
        meta = {**state.meta}

        for port in self.root.descendants(lambda p: port_filter(p) and p in state):
            assert isinstance(port, Port)
            ports[port.rel_name(self.root)] = state[port]

        return ExportResult(ports=ports, meta=meta)


class Importer:
    """ Imports State from a dictionary """

    def __init__(self, root: Block):
        self.root = root

    def __call__(self, ports: tp.Dict[str, tp.Any], meta: tp.Dict[str, str]) -> State:

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

        return state


class State(UserDict):
    """ Stores the values of ports during computation """

    def __init__(self):
        super(State, self).__init__()
        self.meta = dict()      # This will contain extra information about the state

    def __getitem__(self, port: Port):
        if port not in self:
            raise KeyError(f'No value for port {port.full_name}')
        return super(State, self).__getitem__(port)

    def __call__(self, port: Port):
        return port.block.pull(port, self)

