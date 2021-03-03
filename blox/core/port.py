from __future__ import annotations
import typing as tp
from blox.etc.loggingclass import LoggerMixin
from blox.core.node import NamedNode
from blox.etc.errors import PortConnectionError
from boltons.cacheutils import cachedproperty
from blox.core.operators import PortOperatorsMixin


class Port(NamedNode, LoggerMixin, PortOperatorsMixin):

    def __init__(self, name=None, tag=None):
        super(Port, self).__init__(name, tag=tag, tag_in_full_path=True)

        self._upstream = None
        self._downstream = dict()

    @property
    def block(self):
        return self.parent

    @property
    def upstream(self):
        return self._upstream

    @cachedproperty
    def downstream(self):
        return DownstreamView(self, self._downstream)

    @property
    def upstream_block(self):
        if self.block is None:
            return None
        if self.tag == 'In':
            return self.block.parent
        elif self.tag == 'Out':
            return self.block
        return None

    @property
    def downstream_block(self):
        if self.block is None:
            return None
        if self.tag == 'In':
            return self.block
        elif self.tag == 'Out':
            return self.block.parent
        return None

    @upstream.setter
    def upstream(self, port):

        # Remove self from upstream's downstream
        if self.upstream is not None:
            upstream = self.upstream
            self._pre_disconnect_callback(upstream)
            del getattr(self.upstream, '_downstream')[id(self)]
            self._upstream = None
            self._post_disconnect_callback(upstream)

        if port is not None:
            if not isinstance(port, Port):
                raise TypeError('Upstream must be a port')

            if self.block is None:
                raise PortConnectionError(f"Orphaned port {self} can't be connected")

            if port.block is None:
                raise PortConnectionError(f"Can't set an orphaned port as upstream")

            self._check_directions(port)

            # Set upstream
            self._pre_connect_callback(port)
            self._upstream = port
            getattr(port, '_downstream')[id(self)] = self
            self._post_connect_callback(port)

    def _check_directions(self, port):
        if (port.tag == 'In') and (self.tag == 'In'):
            if self.block.parent is not port.block:
                raise PortConnectionError(f"Can't connect {port} -> {self}")

        # This is just a tunnel through the block
        elif (port.tag == 'In') and (self.tag == 'Out'):
            if self.block is not port.block:
                raise PortConnectionError(f"Can't connect {port} -> {self}")

        elif (port.tag == 'Out') and (self.tag == 'In'):
            if port.block.parent is None:
                raise PortConnectionError(f"Can't connect {port} -> {self} (the first is floating)")

            if self.block.parent is not port.block.parent:
                raise PortConnectionError(f"Can't connect {port} -> {self}")

        elif (port.tag == 'Out') and (self.tag == 'Out'):
            if self.block is not port.block.parent:
                raise PortConnectionError(f"Can't connect {port} -> {self}")

        else:
            raise PortConnectionError(f'Invalid tag: given ({self.tag}, {port.tag})')

    def _child_pre_attach_callback(self, parent):
        super(Port, self)._child_pre_attach_callback(parent)

        from blox.core.block import Block
        if not isinstance(parent, Block):
            raise TypeError('Ports can only be attached to Blocks')
        self.unlink()

    def _child_pre_detach_callback(self, parent):
        super(Port, self)._child_pre_detach_callback(parent)
        self.unlink()

    def _pre_connect_callback(self, upstream):
        pass

    def _post_connect_callback(self, upstream):
        pass

    def _pre_disconnect_callback(self, upstream):
        pass

    def _post_disconnect_callback(self, upstream):
        pass

    def unlink(self):
        self.upstream = None
        self.downstream.clear()


class DownstreamView:
    """ A set-like view of a port's downstream """

    __slots__ = ('_data', '_port')

    def __init__(self, port, data):
        self._data = data
        self._port = port

    def __contains__(self, item):
        return id(item) in self._data

    def __iter__(self):
        return iter(self._data.values())

    def clear(self):
        for name in list(self._data.keys()):
            self._data[name].upstream = None

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return bool(self._data)

    def __call__(self, force_tuple=False):
        """ A way to get the ports as a tuple """

        if not force_tuple and len(self) == 0:
            return None

        elif not force_tuple and len(self) == 1:
            return next(iter(self))

        else:
            return tuple(self)

    def add(self, port: Port):
        if not isinstance(port, Port):
            raise TypeError('Downstream elements must be ports')
        if port not in self:
            port.upstream = self._port

    def extend(self, ports: tp.Iterable):
        for x in ports:
            self.add(x)

    def remove(self, port: Port):
        if port not in self:
            raise KeyError(f'Port {port} is not in downstream')
        port.upstream = None
