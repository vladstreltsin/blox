from __future__ import annotations
import typing as tp
from functools import partial
from operator import attrgetter
from collections import defaultdict
from blox2.namednode import NamedNodeMixin
from blox2.utils.memo import EnumeratedMemo
from blox2.utils.funcs import instance_check
from blox2.errors import NameCollisionError, ChildrenLockError, NameLockError, UpstreamSizeError
import networkx as nx
from abc import ABC, abstractmethod
from events import Events
from blox2.messengernode import MessengerNodeMixin
from blox2.messages import ChildRenameMessage, ChildChangeMessage, ChangeType, PortStreamDisconnect


class BlockSection:
    """
    Represents the various sections a Block can contain.
    """
    def __init__(self, block: Block):
        self._block = block

    @property
    def block(self):
        return self._block


class BlockSectionWithChildrenMemo(BlockSection):
    """
    Represents a section handling a particular type of objects stored in self.block.children
    """
    def __init__(self, block, target_class):
        super(BlockSectionWithChildrenMemo, self).__init__(block)

        if not issubclass(target_class, TreeNode):
            raise TypeError(f'target_class must be a subclass of {TreeNode.__name__}')

        self.target_class = target_class
        self._memo = {}   # This maps children names to indices self.block.children
        self._requires_init = True

    def init_memo(self):
        """ Initializes internal memo from the children list """
        if self._requires_init:
            self._memo.clear()
            for child_block in filter(lambda x: isinstance(x, self.target_class), self.block.children):
                self._memo[child_block.name] = child_block
        self._requires_init = False

    def __contains__(self, item):
        self.init_memo()
        if isinstance(item, self.target_class):
            return (item.name in self._memo) and (self._memo[item.name] is item)
        else:
            return item in self._memo

    def __getitem__(self, item):
        self.init_memo()
        return self.block.children[self._memo[item]]

    def handle_child_rename(self, child, new_name):
        if isinstance(child, self.target_class):
            if new_name in self:
                raise NameCollisionError(f'Section {self} already has the name {new_name}')

    def handle_child_change(self, child, change_type: ChangeType):
        if isinstance(child, self.target_class):

            # Before attaching, check that there is not name collision
            if change_type is ChangeType.PRE_ATTACH:
                if child.name in self:
                    raise NameCollisionError(f'Section {self} already has the name {child.name}')

            elif change_type is ChangeType.POST_ATTACH:
                self._requires_init = True

            elif change_type is ChangeType.PRE_DETACH:
                pass

            elif change_type is ChangeType.POST_DETACH:
                self._requires_init = True


class SubBlocksSection(BlockSectionWithChildrenMemo):

    def __init__(self, block):
        super(SubBlocksSection, self).__init__(block, target_class=Block)


class PortsSection(BlockSectionWithChildrenMemo):

    def __init__(self, block, target_class):
        super(PortsSection, self).__init__(block, target_class)
        if not issubclass(target_class, Port):
            raise TypeError(f'Illegal target_class {target_class.__name__} (expected {Port.__name__})')

    def new(self, name, *args, **kwargs):
        port = self.target_class(name, *args, **kwargs)
        port.parent = self.block


class InPortsSection(PortsSection):

    def __init__(self, block):
        super(InPortsSection, self).__init__(block, target_class=InPort)


class OutPortsSection(PortsSection):

    def __init__(self, block):
        super(OutPortsSection, self).__init__(block, target_class=OutPort)


class PortGraph(BlockSection):

    def __init__(self, block):
        super(PortGraph, self).__init__(block)


class TreeNode(NamedNodeMixin, MessengerNodeMixin):
    """ Represents a node in the hierarchy: for now Blocks and Ports, but may be extended to include other
    things. """

    def __init__(self, name):
        self._name = name
        self._flags = dict(lock_children=False,
                           lock_name=False)

    @property
    def flags(self) -> tp.Dict:
        return self._flags

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self.send_message(ChildRenameMessage(child=self, new_name=new_name))
        self._name = new_name

    def _pre_attach(self, parent):
        parent.recv_message(ChildChangeMessage(child=self, change_type='pre_attach'))

    def _pre_detach(self, parent):
        parent.recv_message(ChildChangeMessage(child=self, change_type='pre_detach'))

    def _post_attach(self, parent):
        parent.recv_message(ChildChangeMessage(child=self, change_type='post_attach'))

    def _post_detach(self, parent):
        parent.recv_message(ChildChangeMessage(child=self, change_type='post_detach'))

    def handle_message(self, message):
        # Disallow renaming when lock_name=True
        if isinstance(message, ChildRenameMessage):
            if self.flags['lock_name']:
                raise NameLockError(f'Attempt to change the name of {self} while lock_name=True')


# Blocks


class Block(TreeNode):
    """
    A base class for all Blocks.

    [This is basically a node in a tree that has containers and a PortGraph]

    """
    def __init__(self,
                 name: str,
                 parent: tp.Optional[Block]=None,
                 In: tp.Optional[tp.Iterable[str]]=None,
                 Out: tp.Optional[tp.Iterable[str]]=None):

        super(Block, self).__init__(name)
        self.parent = parent

        self.blocks = SubBlocksSection(block=self)
        self.In = InPortsSection(block=self)
        self.Out = OutPortsSection(block=self)
        self.port_graph = PortGraph(block=self)

        for name in (In or []):
            self.In.new(name)

        for name in (Out or []):
            self.Out.new(name)

    def handle_message(self, message):
        super(Block, self).handle_message(message)

        if isinstance(message, ChildRenameMessage):
            self.handle_child_rename_message(message.child, message.new_name)

        elif isinstance(message, ChildChangeMessage):
            self.handle_child_change_message(message.child, message.change_type)

    def handle_child_rename_message(self, child, new_name):
        """ Child renaming messages are handled in the various block sections """

        if isinstance(child, Block):
            self.blocks.handle_child_rename(child, new_name)

        elif isinstance(child, InPort):
            self.In.handle_child_rename(child, new_name)

        elif isinstance(child, OutPort):
            self.Out.handle_child_rename(child, new_name)

    def handle_child_change_message(self, child, change_type):
        """ Child attach/detach messages are handled in the various block sections """

        if isinstance(child, Block):
            self.blocks.handle_child_change(child, change_type)

        elif isinstance(child, InPort):
            self.In.handle_child_change(child, change_type)

        elif isinstance(child, OutPort):
            self.Out.handle_child_change(child, change_type)


# Ports

class Port(TreeNode):

    def __init__(self, name, *args, **kwargs):
        super(Port, self).__init__(name)

    @property
    def upstream(self):
        raise NotImplementedError

    @property
    def downstream(self):
        raise NotImplementedError

    def handle_message(self, message):
        super(Port, self).handle_message(message)


class InPort(Port):

    def __init__(self, *args, **kwargs):
        super(InPort, self).__init__(*args, **kwargs)
        self._upstream = InPortUpstream(self)
        self._downstream = InPortDownstream(self)

    def upstream(self):
        return self._upstream

    def downstream(self):
        return self._downstream


class OutPort(Port):

    def __init__(self, *args, **kwargs):
        super(OutPort, self).__init__(*args, **kwargs)
        self._upstream = OutPortUpstream(self)
        self._downstream = OutPortDownstream(self)

    def upstream(self):
        return self._upstream

    def downstream(self):
        return self._downstream


# Port Upstreams/downstreams

class PortStream:

    def __init__(self, port: Port):
        self._port = port

    @property
    def port(self):
        return self.port

    @property
    def port_graph(self):
        return None

    def clear(self):
        if self.port_graph is not None and self.port in self.port_graph:
            self.port_graph.remove_node(self.port)


class PortUpstream(PortStream):

    def __len__(self) -> int:
        if self.port_graph is not None and self.port in self.port_graph:
            return self.port_graph.in_degree(self.port)
        return 0

    def __iter__(self) -> tp.Iterable[Port]:
        if len(self) == 0:
            return iter(())
        return iter(map(lambda pair: pair[0],
                        self.port_graph.in_edges(self.port)))

    def __call__(self) -> tp.Optional[Port]:
        if len(self) == 0:
            return None

        elif len(self) == 1:
            return next(iter(self))

        else:
            raise UpstreamSizeError(f"Upstream size = {len(self)} > 1")


class PortDownstream(PortStream):

    def __len__(self) -> int:
        if self.port_graph is not None and self.port in self.port_graph:
            return self.port_graph.out_degree(self.port)
        return 0

    def __iter__(self) -> tp.Iterable[Port]:
        if not len(self):
            return iter(())

        return iter(map(lambda pair: pair[1], self.port_graph.out_edges(self.port)))

    def __call__(self) -> tp.Tuple[Port]:
        return tuple(self)


class InPortUpstream(PortUpstream):
    @property
    def port_graph(self) -> tp.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph


class OutPortUpstream(PortUpstream):
    @property
    def port_graph(self):
        return self.port.block.ports.port_graph


class InPortDownstream(PortDownstream):
    @property
    def port_graph(self):
        return self.port.block.ports.port_graph


class OutPortDownstream(PortDownstream):
    @property
    def port_graph(self) -> tp.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph




