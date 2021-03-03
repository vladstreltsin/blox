from __future__ import annotations
import typing as tp
from itertools import chain

if tp.TYPE_CHECKING:
    from blox_old.block.base.block_base import BlockBase
    from blox_old.block.base.port_section import BlockPortsSection
    from blox_old.block.base.port_base import Port


class PortsHub:
    """ This class holds the various ports sections a block can have """

    def __init__(self, block: BlockBase):
        self._block = block

        # Containers to hold actual ports
        from blox_old.block.base.port_base import InPort, OutPort
        from blox_old.block.base.port_section import BlockPortsSection
        self._in_ports = BlockPortsSection(block_ports_hub=self, port_class=InPort, auxiliary=False)
        self._out_ports = BlockPortsSection(block_ports_hub=self, port_class=OutPort, auxiliary=False)
        self._aux_in_ports = BlockPortsSection(block_ports_hub=self, port_class=InPort, auxiliary=True)
        self._aux_out_ports = BlockPortsSection(block_ports_hub=self, port_class=OutPort, auxiliary=True)

    def __bool__(self):
        return True

    @property
    def In(self) -> BlockPortsSection:
        return self._in_ports

    @property
    def Out(self) -> BlockPortsSection:
        return self._out_ports

    @property
    def AuxIn(self) -> BlockPortsSection:
        return self._aux_in_ports

    @property
    def AuxOut(self) -> BlockPortsSection:
        return self._aux_out_ports

    @In.setter
    def In(self, others):
        from blox_old.block.base.port_base import Port
        if isinstance(others, Port):
            others = (others,)
        self.In.assign_all(others)

    @Out.setter
    def Out(self, others):
        from blox_old.block.base.port_base import Port
        if isinstance(others, Port):
            others = (others,)
        self.Out.assign_all(others)

    @AuxIn.setter
    def AuxIn(self, others):
        from blox_old.block.base.port_base import Port
        if isinstance(others, Port):
            others = (others,)
        self.AuxIn.assign_all(others)

    @AuxOut.setter
    def AuxOut(self, others):
        from blox_old.block.base.port_base import Port
        if isinstance(others, Port):
            others = (others,)
        self.AuxOut.assign_all(others)

    @In.deleter
    def In(self):
        for name in list(self.In.keys()):
            del self[name]

    @Out.deleter
    def Out(self):
        for name in list(self.Out.keys()):
            del self[name]

    @AuxIn.deleter
    def AuxIn(self):
        for name in list(self.AuxIn.keys()):
            del self[name]

    @AuxOut.deleter
    def AuxOut(self):
        for name in list(self.AuxOut.keys()):
            del self[name]

    @property
    def block(self) -> BlockBase:
        return self._block

    @property
    def port_graph__(self):
        return self.block.port_graph__

    def sort(self):
        self.In.sort()
        self.Out.sort()
        self.AuxIn.sort()
        self.AuxOut.sort()

    def __contains__(self, item) -> bool:
        return self.In.__contains__(item) or \
               self.Out.__contains__(item) or \
               self.AuxIn.__contains__(item) or \
               self.AuxOut.__contains__(item)

    def __getitem__(self, item: str) -> Port:
        """ Retrieve port instances by name """
        if item in self.In:
            return self.In[item]

        if item in self.Out:
            return self.Out[item]

        if item in self.AuxIn:
            return self.AuxIn[item]

        if item in self.AuxOut:
            return self.AuxOut[item]

        raise KeyError(item)

    def __setitem__(self, item: str, port):
        """ Connect port to other port """
        if item in self.In:
            self.In[item] = port

        elif item in self.Out:
            self.Out[item] = port

        elif item in self.AuxIn:
            self.AuxIn[item] = port

        elif item in self.AuxOut:
            self.AuxOut[item] = port

        else:
            raise KeyError(item)

    def __delitem__(self, item: str):
        if item in self.In:
            del self.In[item]

        elif item in self.Out:
            del self.Out[item]

        elif item in self.AuxIn:
            del self.AuxIn[item]

        elif item in self.AuxOut:
            del self.AuxOut[item]

        else:
            raise KeyError(item)

    def __getattr__(self, item: str) -> Port:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __setattr__(self, item, other):
        if not item.startswith('_') and item in self:
            self[item] = other

        else:
            super(PortsHub, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(PortsHub, self).__delattr__(item)

    # To give it a Look-and-Feel of a dictionary
    def keys(self) -> tp.Iterable[str]:
        yield from chain(self._in_ports.keys(), self._out_ports.keys(),
                         self._aux_in_ports.keys(), self._aux_out_ports.keys())

    def values(self) -> tp.Iterable[Port]:
        yield from chain(self._in_ports.values(), self._out_ports.values(),
                         self._aux_in_ports.values(), self._aux_out_ports.values())

    def items(self) -> tp.Iterable[tp.Tuple[str, Port]]:
        yield from chain(self._in_ports.items(), self._out_ports.items(),
                         self.__aux_ports.values(), self.__aux_ports.values())

    def __len__(self) -> int:
        return len(self._in_ports) + len(self._out_ports) + \
               len(self._aux_in_ports) + len(self._aux_out_ports)

    def __iter__(self) -> tp.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(PortsHub, self).__dir__())


class BlockPortsHubUpstream:

    def __init__(self, _block_ports_section: BlockPortsSection):
        self._block_ports_section = _block_ports_section

    def clear(self):
        for _, port in self._block_ports_section.items():
            port.upstream.clear()

    def __iter__(self) -> tp.Iterable[Port]:
        return iter(set(chain(port.upstream for port in self._block_ports_section.values())))


class BlockPortsHubDownstream:

    def __init__(self, _block_ports_section: BlockPortsSection):
        self.__block_ports_section = _block_ports_section

    def clear(self):
        for _, port in self.__block_ports_section.items():
            port.downstream.clear()

    def __iter__(self) -> tp.Iterable[Port]:
        return iter(set(chain(port.downstream for port in self.__block_ports_section.values())))
