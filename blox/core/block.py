from __future__ import annotations
from blox.core.node import NamedNode
from blox.etc.loggingclass import LoggerMixin
from blox.etc.errors import TagMismatchError, PortConnectionError
from boltons.cacheutils import cachedproperty
from blox.etc.utils import parse_ports
from blox.core.transforms import BlockTransformsMixin
from blox.core.toposort import BlockToposortMixin
from blox.core.events import NodePreAttach, NodePreDetach


class Block(NamedNode, LoggerMixin, BlockTransformsMixin, BlockToposortMixin):

    def __init__(self, name=None, In=None, Out=None):
        super(Block, self).__init__(name=name, tag='blocks')
        from blox.core.port import Port

        for name in parse_ports(In, default_prefix='in'):
            self.In[name] = Port()

        for name in parse_ports(Out, default_prefix='out'):
            self.Out[name] = Port()

    @cachedproperty
    def blocks(self):
        return SubBlocksView(self, self.children['blocks'], 'blocks')

    @cachedproperty
    def In(self):
        return PortsView(self, self.children['In'], 'In')

    @cachedproperty
    def Out(self):
        return PortsView(self, self.children['Out'], 'Out')

    def links(self):
        """ Returns all port links internal to the block.

         The internal links are precisely those originating on input ports and output ports of
         the sub-blocks.
         """

        for p in self.In:
            for q in p.downstream:
                yield p, q

        for block in self.blocks:
            for p in block.Out:
                for q in p.downstream:
                    yield p, q

    def unlink(self):
        """ Clears external port links """
        self.In.clear_upstream()
        self.Out.clear_downstream()

    # This will allow using xpath-like syntax for accessing blocks
    def __getitem__(self, item):

        if isinstance(item, str) and ':' in item:
            section, item = item.split(':', maxsplit=1)
            return getattr(self, section)[item]
        else:
            return self.blocks[item]

    def __setitem__(self, key, value):
        if isinstance(key, str) and ':' in key:
            section, item = key.split(':', maxsplit=1)
            getattr(self, section)[item] = value
        else:
            self.blocks[key] = value

    def __delitem__(self, key):
        if isinstance(key, str) and ':' in key:
            section, item = key.split(':', maxsplit=1)
            del getattr(self, section)[item]
        else:
            del self.blocks[key]

    def __bool__(self):
        return True

    def handle(self, event):
        super(Block, self).handle(event)

        # Remove all external links before attaching or detaching self
        if isinstance(event, NodePreDetach) or isinstance(event, NodePreAttach):
            if event.node is self:
                self.unlink()


class SectionView:
    __slots__ = ('_block', '_data', '_tag')

    def __init__(self, block, data, tag):
        self._block = block
        self._data = data
        self._tag = tag

    def __getitem__(self, name):
        return self._data[name]

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __bool__(self):
        return bool(self._data)

    def __repr__(self):
        return str(list(self))

    def __call__(self, force_tuple=False):
        """ A way to get the ports as a tuple """

        if not force_tuple and len(self) == 0:
            return None

        elif not force_tuple and len(self) == 1:
            return next(iter(self.values()))

        else:
            return tuple(self.values())


class SubBlocksView(SectionView):
    """ A dict-like interface, for handling sub-blocks """

    def __setitem__(self, name, block):
        assert isinstance(block, Block)
        block.parent = None  # Detach the target block
        block.name = name  # Set the desired name
        block.parent = self._block  # Place the block

    def __delitem__(self, name):
        block = self[name]
        block.parent = None

    def __contains__(self, item):
        if isinstance(item, Block):
            return item in self._data
        else:
            return self._data.contains_name(item)


class PortsView(SectionView):
    """ A dict-like interface, for handling ports """

    def __setitem__(self, key, value):
        from blox.core.port import Port
        
        # Handle the wildcard for setting all ports at once
        if key == '*':
            if len(self) == 0:
                raise PortConnectionError('There are no ports in this section of the block')

            if len(self) == 1:
                self[next(iter(self.keys()))] = value

            else:
                assert len(self) == len(value)
                for name, port in zip(self.keys(), value):
                    self[name] = port

        else:
            port = value
            if not isinstance(port, Port):
                raise TypeError(f'Value must be a port (given {port})')

            # Orphaned ports become children - used for adding new ports
            if port.parent is None:
                if port.tag is not None:
                    TagMismatchError(f'Port {port} has tag {port.tag} which is incompatible with {self._tag}')

                # Override the port's tag
                setattr(port, '_tag', self._tag)
                port.name = key
                port.parent = self._block

            # Non-Orphaned ports get connected
            else:
                self[key].upstream = port

    def __delitem__(self, item):
        self[item].parent = None

    def __contains__(self, item):
        from blox.core.port import Port
        if isinstance(item, Port):
            return item in self._data
        else:
            return self._data.contains_name(item)

    def clear_upstream(self):
        for port in self:
            port.upstream = None

    def clear_downstream(self):
        for port in self:
            port.downstream.clear()



