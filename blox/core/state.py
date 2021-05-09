from __future__ import annotations
from abc import ABC, abstractmethod
import typing as tp
from collections import UserDict
from scalpl import Cut
from collections import namedtuple, defaultdict
from uuid import uuid4

if tp.TYPE_CHECKING:
    from blox.core.port import Port
    from blox.core.block import Block

# ExportResult = namedtuple('ExportResult', field_names=['ports', 'meta', 'params'])
#
#
# # TODO change these
# class Exporter:
#     """ Exports State to a dictionary """
#
#     def __init__(self, root: Block, all_ports=False):
#         self.root = root
#         self.all_ports = all_ports
#
#     def __call__(self, state: State):
#
#         from blox.core.port import Port
#         from blox.core.filters import port_filter, block_filter
#
#         ports = {}
#         params = {}
#         meta = {**state.meta}
#
#         for port in self.root.descendants(lambda p: port_filter(p) and p in state):
#             assert isinstance(port, Port)
#
#             # # Skip input ports that have an upstream
#             # if not self.all_ports and port.tag == 'In' and port.upstream is not None:
#             #     continue
#
#             ports[port.rel_name(self.root)] = state[port]
#
#         for block in self.root.descendants(lambda b: block_filter(b) and b in state.params):
#             assert isinstance(block, Block)
#             params[block.rel_name(self.root)] = state.params[block]
#
#         return ExportResult(ports=ports, meta=meta, params=params)
#
#
# class Importer:
#     """ Imports State from a dictionary """
#
#     def __init__(self, root: Block):
#         self.root = root
#
#     def __call__(self,
#                  ports: tp.Dict[str, tp.Any],
#                  meta: tp.Dict[str, tp.Any],
#                  params: tp.Dict[str, tp.Dict[str, tp.Any]]) -> State:
#
#         from blox.core.port import Port
#
#         # This allows xpath-like access to blocs
#         cut = Cut({self.root.name: self.root}, sep=self.root.separator)
#
#         state = State()
#         state.meta.update(meta)
#
#         for key, value in ports.items():
#
#             try:
#                 port_name = self.root.separator.join([self.root.full_name, key])
#                 port = cut[port_name]
#             except KeyError:
#                 raise KeyError(f'No such port {port_name}')
#
#             if not isinstance(port, Port):
#                 raise TypeError(f'Path {port_name} does not correspond to a port (given: {port})')
#
#             state[port] = value
#
#         for key, value in params.items():
#
#             try:
#                 block_name = self.root.separator.join([self.root.full_name, key])
#                 block = cut[block_name]
#             except KeyError:
#                 raise KeyError(f'No such block {block_name}')
#
#             if not isinstance(block, Block):
#                 raise TypeError(f'Path {block_name} does not correspond to a block (given: {block})')
#
#             state.params[block] = value
#
#         return state


# class State(UserDict):
#     """ Stores the values of ports during computation """
#
#     def __init__(self,
#                  ports: tp.Optional[tp.Dict[Port, tp.Any]] = None,
#                  meta: tp.Optional[tp.Dict[str, tp.Any]] = None,
#                  params: tp.Optional[tp.Dict[Block, tp.Dict[str, tp.Any]]] = None):
#
#         super(State, self).__init__()
#
#         # This will contain extra global parameters
#         self.meta: tp.Dict[str, tp.Any] = dict()
#
#         # This will contain per-block parameters
#         self.params: tp.Dict[Block, tp.Dict[str, tp.Any]] = defaultdict(dict)
#
#         # Init parameters
#         for port, value in (ports or {}).items():
#             self[port] = value
#
#         for key, value in (meta or {}).items():
#             self.meta[key] = value
#
#         for block, value in (params or {}).items():
#             self.params[block] = value
#
#     def __getitem__(self, port: Port):
#         if port not in self:
#             raise KeyError(f'No value for port {port.full_name}')
#         return super(State, self).__getitem__(port)
#
#     def __call__(self, port_or_ports: tp.Union[Port, tp.Iterable[Port]]):
#         from blox.core.port import Port
#
#         if isinstance(port_or_ports, Port):
#             port = port_or_ports
#             return port.block.pull(port, self)
#
#         else:
#             return [port.block.pull(port, self) for port in port_or_ports]


class _NoDefaultClass:
    __slots__ = ()


_NoDefault = _NoDefaultClass()


class PortsDict(UserDict):

    def __setitem__(self, port: Port, value: tp.Any):
        from blox.core.port import Port

        if not isinstance(port, Port):
            raise TypeError(f'port must be of type {Port.__name__}')
        super(PortsDict, self).__setitem__(port, value)


class ParamsDict(UserDict):

    def __setitem__(self, key: str, value: tp.Any):
        if not isinstance(key, str):
            raise TypeError('parameter name must be string')
        super(ParamsDict, self).__setitem__(key, value)


class MetaDict(UserDict):

    def __init__(self, state_id=None, *args, **kwargs):
        super(MetaDict, self).__init__(*args, **kwargs)
        self._state_id = str(state_id) if state_id is not None else str(uuid4())

    @property
    def state_id(self):
        return self._state_id


class BlockState:
    """ This class represents the state of a single block: its port values, its parameters etc """

    def __init__(self):
        self._params = ParamsDict()
        self._ports = PortsDict()

    @property
    def params(self):
        return self._params

    @property
    def ports(self):
        return self._ports


class State:
    """ This class represents the computation state of the entire system. """

    def __init__(self, state_id: tp.Optional[str]=None):
        self._block_states: tp.Dict[Block, BlockState] = defaultdict(BlockState)
        self._meta = MetaDict(state_id=state_id)

    def __getitem__(self, item: tp.Union[str, Port, Block]):
        """ Gets a value depending on the type """
        from blox.core.port import Port
        from blox.core.block import Block

        # For block it returns the block state
        if isinstance(item, Block):
            return self._block_states[item]

        # For ports its returns the port value (if any)
        elif isinstance(item, Port):
            return self._block_states[item.block].ports[item]

        # For strings (item should be string) it returns the value of the global parameter
        else:
            if not isinstance(item, str):
                raise TypeError('Global parameter names must be strings')
            return self._meta[item]

    def __setitem__(self, item: tp.Union[str, Port], value):
        from blox.core.port import Port

        # When a port is given set its value
        if isinstance(item, Port):
            self._block_states[item.block].ports[item] = value

        # When a string is given set the global parameter value
        else:
            if not isinstance(item, str):
                raise TypeError('Meta parameter names must be strings')
            return self._meta[item]

    def __contains__(self, item: tp.Union[str, Port]):
        from blox.core.port import Port

        if isinstance(item, Port):
            return item in self._block_states[item.block].ports

        else:
            return item in self._meta

    def __delitem__(self, item: tp.Union[str, Port]):
        from blox.core.port import Port

        if isinstance(item, Port):
            del self._block_states[item.block].ports[item]
        else:
            del self._meta[item]

    def __call__(self, port_or_ports: tp.Union[Port, tp.Iterable[Port]]):
        from blox.core.port import Port

        # The case when a single port is given
        if isinstance(port_or_ports, Port):
            port = port_or_ports
            return port.block.pull(port, self)

        # The case when multiple ports are given
        else:
            for port in port_or_ports:
                if not isinstance(port, Port):
                    raise TypeError(f'port must be an instance of {Port.__name__}')

            return [port.block.pull(port, self) for port in port_or_ports]

    @property
    def state_id(self):
        return self.meta.state_id
    
    @property
    def meta(self):
        return self._meta

    def to_xpath_state(self, root_block: Block) -> XPathState:
        from blox.core.block import Block
        from blox.core.filters import block_filter

        if not isinstance(root_block, Block):
            raise TypeError(f'root_block must be of type {Block.__name__}')

        xpath_state = XPathState(state_id=self.state_id)

        # Store the globals
        for key, value in self.meta.items():
            xpath_key = root_block.separator.join([xpath_state.meta_prefix, key])
            xpath_state[xpath_key] = value

        # Store root level parameters
        for key, value in self[root_block].params.items():
            xpath_state[key] = value

        # Store root level ports
        for port, value in self[root_block].ports.items():
            xpath_state[port.rel_name(root_block)] = value

        # Store nested parameters and ports
        for block in root_block.descendants(lambda b: block_filter(b)):
            assert isinstance(block, Block)
            for name, value in self[block].params.items():
                key = root_block.separator.join([block.rel_name(root_block), name])
                xpath_state[key] = value

            for port, value in self[block].ports.items():
                key = port.rel_name(root_block)
                xpath_state[key] = value

        return xpath_state

    # A generator of all ports contained in the state
    def ports(self):
        for block_state in self._block_states.values():
            for port in block_state.ports.keys():
                yield port


class XPathState(UserDict):
    """ This in this class the state's values are encoded using blocks paths """

    def __init__(self, state_id=None, *args, **kwargs):
        super(XPathState, self).__init__(*args, **kwargs)
        self.meta_prefix = '@meta'
        self._state_id = str(state_id) if state_id is not None else str(uuid4())

    @property
    def state_id(self):
        return self._state_id

    def to_state(self, root_block: Block) -> State:
        from blox.core.port import Port

        state = State(state_id=self.state_id)

        for key, value in self.items():

            path = key.split(root_block.separator)

            # Handle global parameters
            if path[0] == self.meta_prefix:
                state.meta[root_block.separator.join(path[1:])] = value

            # Handle everything else (ports and block parameters)
            else:
                path, leaf_element = path[:-1], path[-1]

                # Get the deepest block and the associated leaf
                block = root_block
                for element in path:
                    block = block.blocks[element]

                # Check whether the leaf element is a port:
                if leaf_element in block:
                    port = block[leaf_element]
                    if not isinstance(port, Port):
                        raise TypeError(f'{leaf_element} must be an instance of {Port.__name__}')

                    # Set the port value in the state
                    state[port] = value

                # If it is not a port then it must be a parameter
                else:
                    state[block].params[leaf_element] = value

        return state

