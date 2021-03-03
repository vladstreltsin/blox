from __future__ import annotations
import typing as tp
from itertools import chain

from blox_old.tree.namednode import NamedNodeMixin
from blox_old.utils.funcs import assert_identifier, camel_to_snake, parse_ports
from blox_old.exceptions import BlockError
from blox_old.block.base.block_mixins.block_pickle import BlockPickleMixin
from blox_old.block.base.block_mixins.block_transforms import BlockTransformsMixin
from blox_old.block.base.block_mixins.block_summary import BlockSummaryMixin

if tp.TYPE_CHECKING:
    from blox_old.block.base.port_base import Port
    from blox_old.block.base.port_section import BlockPortsSection

IN_PORT_DEFAULT_PREFIX = 'i'
OUT_PORT_DEFAULT_PREFIX = 'o'
AUX_IN_PORT_DEFAULT_PREFIX = 'xi'
AUX_OUT_PORT_DEFAULT_PREFIX = 'xo'


class BlockBase(NamedNodeMixin, BlockPickleMixin, BlockTransformsMixin, BlockSummaryMixin):
    """
    A class that realizes the block structure.

    Think of block diagrams. When designing them on the blackboard we draw rectangles and various
    arrows that connect them. Some rectangles may be disjoint while others can be contained within other rectangles.
    The goal of this class is to translate this type of modeling into code, hopefully in a "pythonic way".

    A Block is a rectangle that contains other rectangles and has little "holes" in it called 'ports'. It has
    a name, it resides on some 'device' (more on that later) and has other 'tools' hanging on its walls. To be a little
    more precise we can try describing the above with a diagram:

        +-------------+-----------------(*)--(*)--+---------------------+
        | b1          |  AUX IN PORTS   xi1   xi2 |                     |
        |             +---------------------------+                     |
        +-----------+                                       +-----------+
        | IN PORTS  |      +----------------+               | OUT PORTS |
        (*) i1      |      | b2             |               |      o1 (*)
        (*) i2  ---------->(*) i1      o1 (*)--------------------> o2 (*)
        |           |      |                |               |           |
        +-----------+      |                |               +-----------+
        |                  +----------------+                           |
        |                                                               |
        |                                                               |
        |             +---------------------------+                     |
        |             | AUX OUT PORTS  xo1  xo2   |                     |
        +-------------+----------------(*)--(*)---+---------------------+

    Lets digest it, explaining the class structure on the way.

    1. Naming
        Everything has names: blocks, ports, sections, persisters, etc. The name of a block
        is given by its name attribute.

    There are many things going on here. We see a block b1 that has 8 ports:
    *   2 port of type IN:
            This type of ports corresponds to the inputs the block must process
    *   2 ports of type OUT
            This type of ports corresponds to the outputs that result after processing the inputs
    *   2 port of type AUX IN
            This type of ports corresponds to special input values such as parameters that are set once
            (more on that later)
    *   2 port of type AUX OUT
            This type of ports corresponds to by-product outputs (more on that later)


    Attributes
    ----------
    name
        The name of the block

    # TODO Write all of that.... there's a lot to cover here...
    """

    def __init__(self,
                 name: tp.Optional[str]=None,
                 In: tp.Optional[tp.Iterable[str]]=None,
                 Out: tp.Optional[tp.Iterable[str]]=None,
                 AuxIn: tp.Optional[tp.Iterable[str]] = None,
                 AuxOut: tp.Optional[tp.Iterable[str]] = None,
                 parent: tp.Optional[BlockBase]=None):
        """

        Parameters
        ----------
        name
            The name of the block.
            Defaults to the class name converted to camel case. Some number may be added to avoid collision.

        In
            An iterable of input port names

        Out
            An iterable of output port names

        AuxIn
            An iterable of auxiliary input port names

        AuxOut
            An iterable of auxiliary output port names

        parent
            The parent block. If left none the block is created 'floating'
        """

        # This handles all that has to do with ports. See BlockPortsHub docs.
        from blox_old.block.base.block_ports_hub import PortsHub
        self._ports = PortsHub(block=self)

        # This handles all that has to do with children blocks. See SubBlocksHub docs.
        from blox_old.block.base.block_subblocks_hub import SubBlocksHub
        self._blocks = SubBlocksHub(block=self)

        # This provides a mechanism to manage port connections
        from blox_old.block.base.port_graph import PortGraph
        self._port_graph = PortGraph(block=self)

        # This is a mechanism to handle naming collision in the parent.
        # The provided name serves as a base to which a counter (called name modifier) is appended
        # In case of a name collision.
        self._base_name = camel_to_snake(self.__class__.__name__) if name is None else str(name)
        self._name_modifier = 0
        assert_identifier(self._base_name)

        # Extra attribute containers to check with  __contains__, __getitem__, __setitem__, __getattr__, __setattr__
        self._extra_attribute_containers = []
        self.register_attribute_container__(self.ports)
        self.register_attribute_container__(self.blocks)

        # Configuration parameters (can be modified later)
        self.auto_rename = True  # Allow naming flexibility in case of name collision
        self._atomic = False     # Whether sub blocks can be added (see the public attribute)
        self.lock_ports = False  # Whether ports can be added or removed
        self.lock_children = False  # Whether children can be added or removed
        self.lock_parent = False  # Whether the block can be removed from its parent

        # Add given ports
        self.__add_ports(In, Out, AuxIn, AuxOut)

        # Set parent if given
        if parent is not None:
            self.parent = parent

    def __add_ports(self, In, Out, AuxIn, AuxOut):
        # Add inputs
        for name in parse_ports(In, default_prefix=IN_PORT_DEFAULT_PREFIX):
            self.In.new(name)

        # Add outputs
        for name in parse_ports(Out, default_prefix=OUT_PORT_DEFAULT_PREFIX):
            self.Out.new(name)

        # Add inputs
        for name in parse_ports(AuxIn, default_prefix=AUX_IN_PORT_DEFAULT_PREFIX):
            self.AuxIn.new(name)

        # Add outputs
        for name in parse_ports(AuxOut, default_prefix=AUX_OUT_PORT_DEFAULT_PREFIX):
            self.AuxOut.new(name)

    def __bool__(self):
        return True

    def register_attribute_container__(self, obj):
        """ Used by subclasses that define attribute containers to be accessed from the class """
        self._extra_attribute_containers.append(obj)

    @property
    def id(self) -> int:
        return id(self)

    @property
    def atomic(self) -> bool:
        return self._atomic

    @atomic.setter
    def atomic(self, value: bool):
        if value and len(self.blocks):
            raise BlockError("A block with children cannot be made atomic")
        self._atomic = value

    @property
    def name(self) -> str:
        if self._name_modifier != 0:
            return f"{self.__base_name}_{self.__name_modifier}"
        return self._base_name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str):
            raise TypeError(type(value))

        if not self.is_root and value != self.name and hasattr(self.parent, value):
            raise ValueError(f"Blocks {self} parent has an attribute {value}")

        assert_identifier(value)
        self._name_modifier = 0
        self._base_name = value
        self.auto_rename = False

        # Advance the counter for the current name
        if not self.is_root:
            self.parent.blocks.generate_name_modifier__(self._base_name)

    def _pre_detach(self, parent: BlockBase):
        parent.pre_detach_child_check(self)

        if parent.lock_children:
            raise BlockError(f"Block {parent} has lock_children=True")

        if self.lock_parent:
            raise BlockError(f"Block {self} has lock_parent=True")

        self.ports.In.upstream.clear()
        self.ports.Out.downstream.clear()

        # Let the parent's port graph know that one of the blocks is gone
        parent.port_graph__.set_changed()

    def _post_detach(self, parent: BlockBase):
        parent.post_detach_child_check(self)

        self._name_modifier = 0  # When blocks are in the root level, they regain their original name

    def _pre_attach(self, parent: BlockBase):
        parent.pre_attach_child_check(self)

        if parent.lock_children:
            raise BlockError(f"Block {parent} has lock_children=True")

        if self.lock_parent:
            raise BlockError(f"Block {self} has lock_parent=True")

        if parent.atomic:
            raise BlockError(f"Block {parent} is atomic")

        if self.name in parent.ports:
            raise BlockError(f"Parent already has a port with the name {self.name}")

        if self.auto_rename:
            if self.name not in parent.blocks and hasattr(parent, self.name):
                raise BlockError(f"Parent already has an attribute with the name {self.name}")
        else:
            if hasattr(parent, self.name):
                raise BlockError(f"Parent already has an attribute with the name {self.name} "
                                 f"(try setting auto_rename=True)")

        self.ports.In.upstream.clear()
        self.ports.Out.downstream.clear()

    def _post_attach(self, parent: BlockBase):
        parent.post_attach_child_check(self)

        self._name_modifier = parent.blocks.generate_name_modifier__(self._base_name)

        # In case someone wants to screw things up and add a port with name such as "abc_123"
        if self._name_modifier != 0:
            parent.blocks.generate_name_modifier__(self.name)

        # Let the parent's port graph know that there is another block around
        parent.port_graph__.set_changed()

    # Hooks to be called from the parent block
    def pre_attach_child_check(self, child: BlockBase):
        pass

    def post_attach_child_check(self, child: BlockBase):
        pass

    def pre_detach_child_check(self, child: BlockBase):
        pass

    def post_detach_child_check(self, child: BlockBase):
        pass

    # Hooks for updates on changes in the port graph of the block
    def on_port_graph_change(self):
        pass

    def __getitem__(self, item: str) -> tp.Union[BlockBase, Port]:
        """ Provide dictionary-like syntax to access sub-blocks and ports """

        for container in self._extra_attribute_containers:
            if item in container:
                return container[item]

        raise KeyError(item)

    def __delitem__(self, item: str):

        for container in self._extra_attribute_containers:
            if item in container:
                del container[item]
                return

        raise KeyError(item)

    def __setitem__(self, key, value):
        """ Port connections and block addition """

        for container in self._extra_attribute_containers:
            if key in container:
                container[key] = value
                return

        # Adding a new block
        if not isinstance(value, BlockBase):
            raise TypeError(value)

        self.blocks[key] = value

    def __contains__(self, item):
        from blox_old.block.base.port_base import Port

        if item in self.__dict__:
            return True

        # Check the extra containers (supplied by subclasses)
        if isinstance(item, str):
            for container in self._extra_attribute_containers:
                if container.__contains__(item):
                    return True

        if isinstance(item, Port):
            return self.ports.__contains__(item)

        if isinstance(item, BlockBase):
            return self.blocks.__contains__(item)

        return False

    def __getattr__(self, item: str) -> tp.Union[Port, BlockBase]:
        try:
            return super(BlockBase, self).__getattribute__(item)

        except AttributeError as exception:
            if not item.startswith('_') and self.__contains__(item):
                return self[item]
            else:
                raise exception

    def __setattr__(self, item: str, other):

        # Private and mangled attributes are treated the standard way
        if item.startswith('_'):
            super(BlockBase, self).__setattr__(item, other)

        else:
            # Adding a new block
            if not hasattr(self, item) and isinstance(other, BlockBase):
                self.blocks[item] = other
                return

            # For stuff inside the extra containers we call the container's __setitem__
            for container in self._extra_attribute_containers:
                if item in container:
                    container[item] = other
                    return

            # Everything else must be handled the standard way
            else:
                super(BlockBase, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(BlockBase, self).__delattr__(item)

    def __len__(self) -> int:
        return len(self.blocks)

    def keys(self):
        yield from chain.from_iterable(container.keys() for container in self._extra_attribute_containers)

    def values(self):
        yield from chain.from_iterable(container.values() for container in self._extra_attribute_containers)

    def items(self):
        yield from chain.from_iterable(container.items() for container in self._extra_attribute_containers)

    def __dir__(self):
        return list(self.keys()) + list(super(BlockBase, self).__dir__())

    def sort(self):
        """ Perform a topological sort on self and all child blocks recursively """

        self.blocks.sort()
        for child in self.blocks:
            child.sort()

        return self

    # Public access to containers
    @property
    def blocks(self):
        return self._blocks

    @property
    def ports(self):
        return self._ports

    @property
    def port_graph__(self):
        return self._port_graph

    # Lots of boilerplate crap
    @property
    def In(self) -> BlockPortsSection:
        return self.ports.In

    @In.setter
    def In(self, others):
        self.ports.In = others

    @In.deleter
    def In(self):
        del self.ports.In

    @property
    def Out(self) -> BlockPortsSection:
        return self.ports.Out

    @Out.setter
    def Out(self, others):
        self.ports.Out = others

    @Out.deleter
    def Out(self):
        del self.ports.Out

    @property
    def AuxIn(self) -> BlockPortsSection:
        return self.ports.AuxIn

    @AuxIn.setter
    def AuxIn(self, others):
        self.ports.AuxIn = others

    @AuxIn.deleter
    def AuxIn(self):
        del self.ports.AuxIn

    @property
    def AuxOut(self) -> BlockPortsSection:
        return self.ports.AuxOut

    @AuxOut.setter
    def AuxOut(self, others):
        self.ports.AuxOut = others

    @AuxOut.deleter
    def AuxOut(self):
        del self.ports.AuxOut
