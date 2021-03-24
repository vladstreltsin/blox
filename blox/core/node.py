""" This is my rewrite of the anytree library  """
from __future__ import annotations
from anytree.iterators import PreOrderIter
import typing as tp
from itertools import takewhile

from blox.core.events import NodePreRename, NodePostRename, \
    NodePreAttach, NodePostAttach, NodePostDetach, NodePreDetach
from blox.etc.utils import camel_to_snake
from blox.etc.errors import NameCollisionError
from collections import defaultdict, OrderedDict
from blox.etc.errors import LoopError, TreeError, BadNameError
from boltons.cacheutils import cachedproperty
from collections import deque


class TagView:

    __slots__ = ('_data',)

    def __init__(self, data):
        self._data = data

    def __contains__(self, item):
        if isinstance(item, NamedNode):
            return item.name in self._data and self._data[item.name] is item
        else:
            return False

    def contains_name(self, name):
        return name in self._data

    def __getitem__(self, item):
        return self._data[item]

    def __iter__(self):
        return iter(self._data.values())

    def keys(self):
        yield from self._data.keys()

    def values(self):
        yield from self._data.values()

    def items(self):
        yield from self._data.items()

    def __bool__(self):
        return bool(self._data)

    def __len__(self):
        return len(self._data)


class ChildrenView:

    __slots__ = ('_data',)

    def __init__(self, data):
        self._data = data

    def __contains__(self, item):
        if isinstance(item, NamedNode):
            return item.name in self._data[item.tag] and self._data[item.tag][item.name] is item
        else:
            return False

    def __iter__(self):
        for tag in self._data:
            yield self[tag]

    def __getitem__(self, tag):
        return TagView(self._data[tag])


class NamedNode:
    __slots__ = ('_name', '_tag', '_parent', '_children', '_tag_in_full_path', 'meta')

    separator = "/"

    def __init__(self, name=None, tag=None, tag_in_full_path=False):
        self._name = name or camel_to_snake(self.__class__.__name__)
        self._tag = tag or ''
        self._parent = None
        self._children = defaultdict(OrderedDict)
        self._tag_in_full_path = tag_in_full_path

        self._check_name(self._name)

        self.meta = dict()  # To handle any extra data associated with the node

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):

        if new_name != self.name:
            self.bubble(NodePreRename(node=self, parent=self.parent, new_name=new_name), start_nodes=[self])
            self._name, old_name = new_name, self._name
            self.bubble(NodePostRename(node=self, parent=self.parent, old_name=old_name), start_nodes=[self])

    @property
    def tag(self):
        return self._tag

    @cachedproperty
    def children(self):
        return ChildrenView(self._children)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):

        parent = self.parent

        if parent is not None:
            self._detach(parent)

        if value is not None:
            self._check_node(value)
            self._check_loop(value)
            self._attach(value)

    def detach(self):
        self.parent = None
        return self

    @staticmethod
    def _check_name(name):
        if ':' in name:
            raise BadNameError('Names cannot contain ":"')
        if '*' in name:
            raise BadNameError('Names cannot contain "*"')

    @staticmethod
    def _check_node(node):
        if not isinstance(node, NamedNode):
            raise TreeError(f'Node {node} is not of type {NamedNode.__name__}')

    def _check_loop(self, node):
        if node is self:
            raise LoopError(f"Cannot set parent. {self} cannot be parent of itself.")

        if any(child is self for child in node.iter_path_reverse()):
            raise LoopError(f"Cannot set parent. {self} is parent of {node}")

    def _detach(self, parent: NamedNode):

        self.bubble(NodePreDetach(node=self, parent=parent), start_nodes=[self, parent])
        self._parent = None
        self.bubble(NodePostDetach(node=self, parent=parent), start_nodes=[self, parent])

    def _attach(self, parent: NamedNode):

        # There is no link yet between parent and self
        self.bubble(NodePreAttach(node=self, parent=parent), start_nodes=[self, parent])
        self._parent = parent
        self.bubble(NodePostAttach(node=self, parent=parent), start_nodes=[self, parent])

    def path(self):
        yield from reversed(list(self.iter_path_reverse()))

    def iter_path_reverse(self):
        node = self
        while node is not None:
            yield node
            node = node.parent

    def ancestors(self):
        if self.parent is not None:
            yield from self.parent.path()

    def descendants(self,
                    filter_fn: tp.Optional[tp.Callable[[NamedNode], bool]]=None) \
            -> tp.Generator[NamedNode, None, None]:
        """
        A generator to return descendant nodes (children, children-of-children, etc).

        Parameters
        ----------
        filter_fn
            A callable accepting an instance of NamedNode and returning a boolean used as a filter.

        Yields
        -------
            Instances of NamedNode
        """
        queue = deque()
        queue.append(self)

        while True:
            if not queue:
                break

            node = queue.popleft()

            if node is not self and (not filter_fn or filter_fn(node)):
                yield node

            for tag_view in node.children:
                queue.extend(tag_view)

    def root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    @property
    def is_root(self):
        return self.parent is None

    def depth(self):
        return len(list(self.iter_path_reverse()))

    @property
    def tagged_name(self):
        if self._tag_in_full_path:
            return f'{self.tag}:{self.name}'
        else:
            return self.name

    @property
    def full_name(self) -> str:
        """ Return the block's name relative to the root """
        # return self.separator.join(map(lambda x: x.name, self.path()))
        return self.separator.join(map(lambda x: x.tagged_name, self.path()))

    def rel_name(self, other: NamedNode) -> tp.Optional[str]:
        """ Returns the node's name relative to the other node """

        # The name relative to the "void" in the full name
        if other is None:
            return self.full_name

        path = list(takewhile(lambda x: other is not x, self.iter_path_reverse()))

        # This means that other is not an ancestor of self
        if not path or path[-1].parent is not other:
            return None

        # return self.separator.join(reversed(list(map(lambda x: x.name, path))))
        return self.separator.join(reversed(list(map(lambda x: x.tagged_name, path))))

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.full_name}>"

    @staticmethod
    def bubble(event, start_nodes: tp.Iterable[NamedNode]):
        seen_nodes = set()
        for start_node in start_nodes:
            for node in start_node.iter_path_reverse():
                if id(node) in seen_nodes:
                    break
                node.handle(event)
                seen_nodes.add(id(node))

    def handle(self, event):

        # Handle name collisions when renaming a child
        if isinstance(event, NodePreRename):
            parent, child, new_name = event.parent, event.node, event.new_name

            if parent is self:
                siblings = self._children[child.tag]
                if new_name in siblings and siblings[new_name] is not child:
                    raise NameCollisionError(f'Name "{new_name}" with tag "{child.tag}" '
                                             f'exists in {parent}')

            elif child is self:
                self._check_name(new_name)

        # Update new child name in children
        elif isinstance(event, NodePostRename):
            parent, child, old_name = event.parent, event.node, event.old_name

            if parent is self:
                siblings = self._children[child.tag]
                assert siblings.pop(old_name) is child
                siblings[child.name] = child

        # Make sure there is no name collision before attaching
        elif isinstance(event, NodePreAttach):
            parent, child = event.parent, event.node
            if parent is self:
                siblings = self._children[child.tag]
                if child.name in siblings:
                    raise NameCollisionError(f'Name "{child.name}" with tag "{child.tag}" exists in {parent}')

        # Update child addition in parent
        elif isinstance(event, NodePostAttach):
            parent, child = event.parent, event.node
            if parent is self:
                siblings = self._children[child.tag]
                assert child.name not in siblings
                siblings[child.name] = child

        # Update child remove in parent
        elif isinstance(event, NodePostDetach):

            parent, child = event.parent, event.node
            if parent is self:
                siblings = self._children[child.tag]
                assert siblings.pop(child.name) is child

