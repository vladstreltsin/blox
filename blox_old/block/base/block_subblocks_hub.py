from __future__ import annotations
import typing as tp
from collections import defaultdict
from functools import partial
from operator import attrgetter
from blox_old.exceptions import BlockError
from blox_old.utils.memo import EnumeratedMemo
from blox_old.utils.funcs import instance_check

if tp.TYPE_CHECKING:
    from blox_old.block.base.block_base import BlockBase


class SubBlocksHub:
    """
    This class holds all of the sub-blocks of a given block
    """

    def __init__(self, block: BlockBase):
        from blox_old.block.base.block_base import BlockBase

        self._block = block

        # This is used to quickly assign a name modifier to a new child
        self._name_modifier_dict = defaultdict(int)

        # These dicts maps blocks children names/instances to indices in its children list (see anytree.NodeMixin)
        self._memo = EnumeratedMemo(container_fn=partial(attrgetter('children'), self.block),
                                    name_fn=attrgetter('name'),
                                    filter_fn=partial(instance_check, cls=BlockBase))

    def __len__(self) -> int:
        return len(list(x for x in self))

    def __bool__(self):
        return True

    @property
    def descendants(self) -> tp.Iterable[BlockBase]:
        from blox_old.block.base.block_base import BlockBase
        yield from filter(lambda x: isinstance(x, BlockBase), self.block.descendants)

    @property
    def block(self) -> BlockBase:
        return self._block

    def sort(self):
        self.block.port_graph__.toposort()

    def sorted(self) -> tp.Iterable[BlockBase]:
        """ Returns the essential sub-blocks in topologically sorted order """
        return self.block.port_graph__.topo_blocks()

    def essential_sorted(self):
        """ Returns all sub-blocks in topologically sorted order"""
        return self.block.port_graph__.topo_blocks_essential()

    # A utility function to generate unique names for sub-blocks
    # This function should not be called by the user
    def generate_name_modifier__(self, base_name: str) -> int:

        name_modifier = self._name_modifier_dict[base_name]
        self._name_modifier_dict[base_name] += 1
        return name_modifier

    def __contains__(self, item: tp.Union[str, BlockBase]) -> bool:
        from blox_old.block.base.block_base import BlockBase

        if isinstance(item, str):
            return item in self._memo

        elif isinstance(item, BlockBase):
            return item in self.block.children

        return False

    def __getitem__(self, item):
        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        if item in self._memo:
            return self._memo[item]

        raise KeyError(item)

    def __setitem__(self, item: str, block: BlockBase):
        """ Create set block as a sub-block under the name item """
        from blox_old.block.base.block_base import BlockBase

        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        if not isinstance(block, BlockBase):
            raise TypeError(f"Unsupported block type {type(block)}")

        if item in self:
            raise BlockError(f'Block {self.block} already has a child with the name {item}')

        block.auto_rename = True    # So that we don't have problems attaching it with its current name
        block.parent = self.block
        block.name = item

    def __delitem__(self, item):
        """ Remove a sub-block """
        child = self[item]
        child.parent = None     # Throw the child away

    def keys(self) -> tp.Iterable[str]:
        yield from map(lambda child: child.name, self)

    def values(self) -> tp.Iterable[BlockBase]:
        yield from self

    def items(self) -> tp.Iterable[tp.Tuple[str, BlockBase]]:
        yield from map(lambda child: (child.name, child), self)

    def __iter__(self) -> tp.Iterable[BlockBase]:
        from blox_old.block.base.block_base import BlockBase
        return iter(filter(lambda x: isinstance(x, BlockBase), self.block.children))

    def __getattr__(self, item: str) -> BlockBase:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __setattr__(self, item: str, other):
        from blox_old.block.base.block_base import BlockBase

        if not item.startswith('_') and isinstance(other, BlockBase) and ((item in self) or (not hasattr(self, item))):
            self[item] = other
        else:
            super(SubBlocksHub, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(SubBlocksHub, self).__delattr__(item)

    def __dir__(self):
        return list(self.keys()) + list(super(SubBlocksHub, self).__dir__())
