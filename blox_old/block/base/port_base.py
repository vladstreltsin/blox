from __future__ import annotations
import typing as tp
from abc import abstractmethod, ABC
import networkx as nx
from blox_old.exceptions import PortError
from blox_old.tree.namednode import NamedNodeMixin
from blox_old.block.base.port_mixins.port_operators import PortOperatorMixin

if tp.TYPE_CHECKING:
    from blox_old.block.base.block_base import BlockBase
    from blox_old.block.base.port_section import BlockPortsSection


class Port(NamedNodeMixin):
    """ The gateways to and from Blocks. Always instantiated using _BlockPortsSection.new() """

    def __init__(self, _block_ports_section: BlockPortsSection, _auxiliary: bool):

        self.__block_ports_section = _block_ports_section
        self.__auxiliary = _auxiliary
        self.__lock_name = False

        # Set the parent once and for all
        super(Port, self.__class__).parent.fset(self, self.block)

    @property
    def device(self):
        return self.block.device

    @property
    def parent(self):
        return self.block

    @parent.setter
    def parent(self, value):
        raise PortError("Cannot set the attribute parent")

    @property
    def children(self):
        return tuple()

    @children.setter
    def children(self, value):
        raise PortError("Cannot set the attribute children")

    @property
    def separator(self):
        return self.parent.separator

    @property
    def id(self) -> int:
        return id(self)

    @property
    def auxiliary(self):
        return self.__auxiliary

    @property
    def lock_name(self):
        return self.__lock_name

    @lock_name.setter
    def lock_name(self, value: bool):
        self.__lock_name = value

    @property
    def block(self) -> BlockBase:
        return self.__block_ports_section.block

    @property
    def name(self) -> str:
        return self.__block_ports_section.get_name(self)

    @name.setter
    def name(self, new_name: str):
        if self.lock_name:
            raise PortError(f"Port {self} has lock_name=True")

        self.__block_ports_section.rename(old_name=self.name, new_name=new_name)

    @property
    @abstractmethod
    def upstream(self) -> PortUpstream:
        pass

    @property
    @abstractmethod
    def downstream(self) -> PortDownstream:
        pass

    @property
    @abstractmethod
    def is_in(self) -> bool:
        pass

    @property
    def is_out(self) -> bool:
        return not self.is_in

    @property
    def section(self) -> BlockPortsSection:

        if self.is_in and not self.auxiliary:
            return self.block.In

        elif self.is_in and self.auxiliary:
            return self.block.AuxIn

        elif not self.is_in and not self.auxiliary:
            return self.block.Out

        else:
            return self.block.AuxOut

    def __assert_can_feed(self, other: Port):
        if self.downstream.port_graph__ is None:
            raise PortError(f"Port {self} has no downstream port graph (probably because it belongs to a root block)")

        if other.upstream.port_graph__ is None:
            raise PortError(f"Port {other} has no upstream port graph (probably because it belongs to a root block)")

        if self.downstream.port_graph__ is not other.upstream.port_graph__:
            raise PortError(f"Port's {self} downstream and port's {other} upstream do not share the same port graph")

        if len(other.upstream) > 0:
            raise PortError(f"Port {other} is already driven by some port")

    def feed(self, other: Port):
        self.__assert_can_feed(other)
        self.downstream.port_graph__.add_edge(self, other)

    async def pull(self, session):
        result = await self.block.pull(self, session)
        return result

    def push(self, session):
        self.block.push(self, session)

    def _assert_session(self, x):
        from blox_old.engine.engine import Session
        if not isinstance(x, Session):
            raise TypeError(x)

    def __getitem__(self, session):
        self._assert_session(session)
        return session[self]

    def __setitem__(self, session, value):
        self._assert_session(session)
        session[self] = value

    def __contains__(self, session):
        self._assert_session(session)
        return self in session

    def __delitem__(self, session):
        self._assert_session(session)
        del session[self]

    def __call__(self, session, timeout=None):
        self._assert_session(session)
        return session(port=self, timeout=timeout)
    

class PortUpstream(ABC):

    def __init__(self, _port: Port):
        self.__port = _port

    @property
    def port(self) -> Port:
        return self.__port

    @property
    @abstractmethod
    def port_graph__(self):
        pass

    def __len__(self) -> int:
        if self.port_graph__ is not None and self.port in self.port_graph__:
            return self.port_graph__.in_degree(self.port)
        return 0

    def __iter__(self) -> tp.Iterable[Port]:
        if not len(self):
            return iter(())
        return iter(map(lambda pair: pair[0],
                        self.port_graph__.in_edges(self.port)))

    def __call__(self) -> tp.Optional[Port]:
        if len(self) == 0:
            return None

        elif len(self) == 1:
            return next(iter(self))

        else:
            raise PortError("Upstream size > 1")

    def clear(self):
        """ Clear connections on the upstream """
        if self.port_graph__ is not None and self.port in self.port_graph__:
            self.port_graph__.remove_node(self.port)


class PortDownstream(ABC):

    def __init__(self, _port):
        self.__port = _port

    @property
    def port(self) -> Port:
        return self.__port

    @property
    @abstractmethod
    def port_graph__(self):
        pass

    def __len__(self) -> int:
        if self.port_graph__ is not None and self.port in self.port_graph__:
            return self.port_graph__.out_degree(self.port)
        return 0

    def __iter__(self) -> tp.Iterable[Port]:
        if not len(self):
            return iter(())

        return iter(map(lambda pair: pair[1], self.port_graph__.out_edges(self.port)))

    def __call__(self) -> tp.Tuple[Port]:
        return tuple(self)

    def clear(self):
        """ Clear connections on the downstream """
        if self.port_graph__ is not None and self.port in self.port_graph__:
            self.port_graph__.remove_node(self.port)


class InPortUpstream(PortUpstream):
    @property
    def port_graph__(self) -> tp.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph__


class OutPortUpstream(PortUpstream):
    @property
    def port_graph__(self):
        return self.port.block.ports.port_graph__


class InPortDownstream(PortDownstream):
    @property
    def port_graph__(self):
        return self.port.block.ports.port_graph__


class OutPortDownstream(PortDownstream):
    @property
    def port_graph__(self) -> tp.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph__


class InPort(Port):

    def __init__(self, *args, **kwargs):
        super(InPort, self).__init__(*args, **kwargs)
        self.__upstream = InPortUpstream(_port=self)
        self.__downstream = InPortDownstream(_port=self)

    @property
    def upstream(self):
        return self.__upstream

    @property
    def downstream(self):
        return self.__downstream

    @property
    def is_in(self):
        return True


class OutPort(Port):

    def __init__(self, *args, **kwargs):
        super(OutPort, self).__init__(*args, **kwargs)
        self.__upstream = OutPortUpstream(_port=self)
        self.__downstream = OutPortDownstream(_port=self)

    @property
    def upstream(self):
        return self.__upstream

    @property
    def downstream(self):
        return self.__downstream

    @property
    def is_in(self) -> bool:
        return False
