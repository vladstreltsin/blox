from __future__ import annotations
import typing as tp
from itertools import takewhile
from anytree import NodeMixin
import logging


logger = logging.getLogger(__name__)


class NamedNodeMixin(NodeMixin):
    """
    Extension class of anytree.NodeMixin to include a fully qualified name for each node.
    """

    # This must be implemented by the inheriting class
    @property
    def name(self):
        raise NotImplementedError

    @property
    def full_name(self) -> str:
        """ Return the block's name relative to the root """
        return self.separator.join(map(lambda x: x.name, self.path))

    def rel_name(self, other: NamedNodeMixin) -> tp.Optional[str]:
        """ Returns the block's name relative to the other block """

        # The name relative to the "void" in the full name
        if other is None:
            return self.full_name

        path = list(takewhile(lambda x: other.parent is not x, self.iter_path_reverse()))

        # This means that other is not an ancestor of self
        if not path or path[-1] is not other:
            return None

        return self.separator.join(reversed(list(map(lambda x: x.name, path))))

    def __str__(self):
        return self.full_name

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.full_name}>"
