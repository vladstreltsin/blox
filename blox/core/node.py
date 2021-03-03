""" This is my rewrite of the anytree library  """
from __future__ import annotations
from anytree.iterators import PreOrderIter
import typing as tp
from itertools import takewhile
from blox.etc.utils import camel_to_snake
from blox.etc.errors import NameCollisionError
from collections import defaultdict, OrderedDict
from blox.etc.errors import LoopError, TreeError, BadNameError
from boltons.cacheutils import cachedproperty


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

    def __getitem__(self, tag):
        return TagView(self._data[tag])


class NamedNode:

    separator = "/"

    def __init__(self, name=None, tag=None, tag_in_full_path=False):
        self._name = name or camel_to_snake(self.__class__.__name__)
        self._tag = tag or ''
        self._parent = None
        self._children = defaultdict(OrderedDict)
        self._tag_in_full_path = tag_in_full_path

        self._check_name(self._name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):

        if new_name != self.name:

            self._child_pre_rename_callback(new_name)
            self._check_name(new_name)

            # Check for name collision in parent
            if self.parent is not None:
                siblings = getattr(self.parent, '_children')[self.tag]
                if new_name in siblings and siblings[new_name] is not self:
                    raise NameCollisionError(f'Name "{new_name}" with tag "{self.tag}" exists in {self.parent}')

            # Rename in parent
            if self.parent is not None:
                siblings = getattr(self.parent, '_children')[self.tag]
                assert siblings.pop(self._name) is self
                siblings[new_name] = self

            # Rename self
            self._name = new_name

            self._child_post_rename_callback(new_name)

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

    def _detach(self, parent):
        self._child_pre_detach_callback(parent)
        getattr(parent, '_parent_pre_detach_callback')(self)

        siblings = getattr(parent, '_children')[self.tag]
        assert siblings.pop(self.name) is self
        self._parent = None

        self._child_post_detach_callback(parent)
        getattr(parent, '_parent_post_detach_callback')(self)

    def _attach(self, parent):
        self._child_pre_attach_callback(parent)
        getattr(parent, '_parent_pre_attach_callback')(self)

        siblings = getattr(parent, '_children')[self.tag]
        if self.name in siblings:
            raise NameCollisionError(f'Name "{self.name}" with tag "{self.tag}" exists in {parent}')

        siblings[self.name] = self
        self._parent = parent

        self._child_post_attach_callback(parent)
        getattr(parent, '_parent_post_attach_callback')(self)

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

    def descendants(self):
        yield from tuple(PreOrderIter(self))[1:]

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
        """ Returns the block's name relative to the other block """

        # The name relative to the "void" in the full name
        if other is None:
            return self.full_name

        path = list(takewhile(lambda x: other.parent is not x, self.iter_path_reverse()))

        # This means that other is not an ancestor of self
        if not path or path[-1] is not other:
            return None

        # return self.separator.join(reversed(list(map(lambda x: x.name, path))))
        return self.separator.join(reversed(list(map(lambda x: x.tagged_name, path))))

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.full_name}>"

    def _child_pre_detach_callback(self, parent):
        """Method call before detaching from `parent`."""
        pass

    def _child_post_detach_callback(self, parent):
        """Method call after detaching from `parent`."""
        pass

    def _child_pre_attach_callback(self, parent):
        """Method call before attaching to `parent`."""
        pass

    def _child_post_attach_callback(self, parent):
        """Method call after attaching to `parent`."""
        pass

    def _parent_pre_detach_callback(self, child):
        """ Method called by the parent before detaching the `child`. """
        pass

    def _parent_post_detach_callback(self, child):
        """ Method called by the parent after detaching the `child`. """
        pass

    def _parent_pre_attach_callback(self, child):
        """ Method called by the parent before attaching the `child`. """
        pass

    def _parent_post_attach_callback(self, child):
        """ Method called by the parent after attaching the `child`. """
        pass

    def _child_pre_rename_callback(self, new_name):
        pass

    def _child_post_rename_callback(self, new_name):
        pass


