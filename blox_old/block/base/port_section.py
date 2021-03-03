from __future__ import annotations
import typing as tp
from collections import OrderedDict

from blox_old.block.base.port_base import Port
from blox_old.exceptions import BlockError
from blox_old.utils.funcs import assert_identifier, first

if tp.TYPE_CHECKING:
    from blox_old.block.base.ports_hub import PortsHub


class BlockPortsSection:
    """ For treating input ports and output ports separately """

    def __init__(self, block_ports_hub: PortsHub, port_class, auxiliary: bool):
        self._block_ports_hub = block_ports_hub
        self._port_class = port_class

        self._names_to_instances = OrderedDict()
        self._instances_to_names = OrderedDict()

        from blox_old.block.base.ports_hub import BlockPortsHubUpstream, BlockPortsHubDownstream
        self._upstream = BlockPortsHubUpstream(_block_ports_section=self)
        self._downstream = BlockPortsHubDownstream(_block_ports_section=self)

        self._auxiliary = auxiliary

    def __bool__(self):
        return True

    @property
    def auxiliary(self):
        return self._auxiliary

    @property
    def block(self):
        return self._block_ports_hub.block

    @property
    def port_graph__(self):
        return self._block_ports_hub.port_graph__

    @property
    def upstream(self):
        return self._upstream

    @property
    def downstream(self):
        return self._downstream

    def __call__(self, force_tuple=False) -> tp.Union[None, Port, tp.Tuple[Port]]:
        """ A way to get the ports as a tuple """

        if not force_tuple and len(self) == 0:
            return None

        elif not force_tuple and len(self) == 1:
            return next(iter(self.values()))

        else:
            return tuple(self.values())

    def __iter__(self) -> tp.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(BlockPortsSection, self).__dir__())

    def __contains__(self, item: tp.Union[str, Port]):
        if isinstance(item, str):
            return item in self._names_to_instances

        if isinstance(item, Port):
            return item in self._instances_to_names

        return False

    def __getitem__(self, item: tp.Union[str, int]) -> Port:
        """ Retrieve port instances by name """
        if isinstance(item, str):
            return self._names_to_instances[item]

        elif isinstance(item, int):
            return list(self.values())[item]

        else:
            raise TypeError(item)

    def __setitem__(self, item: tp.Union[str, int], other: tp.Optional[Port]):
        """ Connect port to other port """

        port: Port = self[item]
        port.upstream.clear()

        if other is None:
            return

        # Any value that is not a port will wrapped with Const class
        # Blocks are not allowed
        if not isinstance(other, Port):
            # TODO it could be a good idea to have a block Factory instead of this
            from blox_old.block.base import Const
            from blox_old.block.base.block_base import BlockBase
            if isinstance(other, BlockBase):
                raise BlockError("Cannot set ports with blocks")
            other = Const(value=other).Out()

        assert isinstance(other, Port)

        # If one of the blocks is "floating" move it under the other
        port_graph = port.upstream.port_graph__
        other_port_graph = other.downstream.port_graph__

        if port_graph is not None and other_port_graph is None:
            other.block.parent = port_graph.block

        elif other_port_graph is not None and port_graph is None:
            port.block.parent = other_port_graph.block

        # Perform the connection (has more checks inside)
        other.feed(port)

    def __delitem__(self, item: tp.Union[str, int]):
        if isinstance(item, int):
            item = list(self.keys())[item]
        self.remove(item)

    def __getattr__(self, item: str) -> Port:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __setattr__(self, item, other):
        if not item.startswith('_') and (item in self):
            self[item] = other
        else:
            super(BlockPortsSection, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(BlockPortsSection, self).__delattr__(item)

    def __len__(self) -> int:
        return len(self._names_to_instances)

    def keys(self) -> tp.Iterable[str]:
        yield from self._names_to_instances.keys()

    def values(self) -> tp.Iterable[Port]:
        yield from self._names_to_instances.values()

    def items(self) -> tp.Iterable[tp.Tuple[str, Port]]:
        yield from self._names_to_instances.items()

    def __assert_name(self, name):
        assert_identifier(name)
        if name in self._block_ports_hub:
            raise BlockError(f"Block {self.block} already has a port with the name {name}")

        if name in self.block.blocks:
            raise BlockError(f"Block {self.block} already has a sub block with the name {name}")

        if hasattr(self.block, name):
            raise AttributeError(f"Block {self.block} already has an attribute: {name}")

    def new(self, name) -> Port:
        """ Creates a new port with given name """
        self.__assert_name(name)

        if self.block.lock_ports:
            raise BlockError(f"Cannot add ports since {self.block} has lock_ports=True")

        # Instantiate the class
        # port = self.__port_class(_name=name, _block_ports_section=self, _auxiliary=self.auxiliary)
        port = self._port_class(_block_ports_section=self, _auxiliary=self.auxiliary)

        # Store mappings name <-> instance
        self._names_to_instances[name] = port
        self._instances_to_names[port] = name

        return port

    def get_name(self, port: Port) -> str:
        return self._instances_to_names[port]

    def rename(self, old_name, new_name):
        self.__assert_name(new_name)
        if self.block.lock_ports:
            raise BlockError(f"Cannot rename ports since {self.block} has lock_ports=True")

        port = self[old_name]

        # Store mappings name <-> instance
        self._names_to_instances[new_name] = port
        self._instances_to_names[port] = new_name

        del self._names_to_instances[old_name]

        return port

    def remove(self, name):
        """ Removes a port """
        if self.block.lock_ports:
            raise BlockError(f"Cannot remove ports since {self.block} has lock_ports=True")

        port: Port = self[name]
        port.upstream.clear()
        port.downstream.clear()

        # Must use the parent class method because we disabled setting the Port parent directly
        super(Port, Port).parent.fset(port, None)

        del self._instances_to_names[port]
        del self._names_to_instances[name]

    def assign_all(self, others: tp.Iterable):
        """ Make others feed all ports in self """
        others = list(others)

        if len(self) != len(others):
            BlockError(f"Expected {len(self)} ports, given {len(others)}")

        for port_name, other in zip(self.keys(), others):
            self[port_name] = other

    def sort(self):
        """ Sort the port instances by names """
        self._names_to_instances = OrderedDict(sorted(self._names_to_instances.items(), key=first))
