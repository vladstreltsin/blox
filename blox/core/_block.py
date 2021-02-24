from __future__ import annotations
import networkx as nx
from abc import ABC, abstractmethod
import typing as T
from collections import OrderedDict
from collections import defaultdict
from itertools import chain
import pickle
import threading
from contextlib import contextmanager
from operator import attrgetter
from functools import partial
from blox.core.namednode import NamedNodeMixin
from blox.utils import maybe_or, assert_identifier, camel_to_snake, parse_ports, first
from blox.utils import EnumeratedMemo, instance_check
from blox.core.device import DefaultDevice, BlockDevice
from blox.core.exceptions import BlockError, PortError

if T.TYPE_CHECKING:
    from blox.core.persist.base import Persister


# This is a nice trick to allow viewing inner blocks as "detached" in some contexts.
# The only thing that makes blocks "know" of the external world in through their parent attribute.
# We would like to create contexts where a block may 'think' that he is the top level block (e.g. when pickling)
# To do so, we override the parent attribute getter to look at this context variable that will be set to the
# 'orphaned' block view


class _DetachtedBlock:

    def __init__(self):
        self._block = None
        self.lock = threading.Lock()

    def acquire(self, block):
        self.lock.acquire()
        self._block = block

    def release(self):
        self._block = None
        self.lock.release()

    @property
    def block(self):
        return self._block

    @contextmanager
    def __call__(self, block):
        try:
            self.acquire(block)
            yield self
        finally:
            self.release()


_detached_block = _DetachtedBlock()


class _BlockSubBlocks:

    def __init__(self, _block: _Block):
        self._block = _block

        # This is used to quickly assign a name modifier to a new child
        self.__name_modifier_dict = defaultdict(int)

        # These dicts maps blocks children names/instances to indices in its children list (see anytree.NodeMixin)
        # self.__children_name_memo = {}
        self.__memo = EnumeratedMemo(container_fn=partial(attrgetter('children'), self.block),
                                     name_fn=attrgetter('name'),
                                     filter_fn=partial(instance_check, cls=_Block))

    def __len__(self) -> int:
        return len(list(x for x in self))

    def __bool__(self):
        return True

    @property
    def descendants(self) -> T.Iterable[_Block]:
        yield from filter(lambda x: isinstance(x, _Block), self.block.descendants)

    @property
    def block(self) -> _Block:
        return self._block

    def sort(self):
        self.block.port_graph__.toposort()

    def sorted(self) -> T.Iterable[_Block]:
        """ Returns the essential sub-blocks in topologically sorted order """
        return self.block.port_graph__.topo_blocks()

    def essential_sorted(self):
        """ Returns all sub-blocks in topologically sorted order"""
        return self.block.port_graph__.topo_blocks_essential()

    # A utility function to generate unique names for sub-blocks
    # This function should not be called by the user
    def generate_name_modifier__(self, base_name: str) -> int:

        name_modifier = self.__name_modifier_dict[base_name]
        self.__name_modifier_dict[base_name] += 1
        return name_modifier

    def __contains__(self, item: T.Union[str, _Block]) -> bool:
        if isinstance(item, str):
            return item in self.__memo

        elif isinstance(item, _Block):
            return item in self.block.children

        return False

    def __getitem__(self, item):
        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        if item in self.__memo:
            return self.__memo[item]

        raise KeyError(item)

    def __setitem__(self, item: str, block: _Block):
        """ Create set block as a sub-block under the name item """

        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        if not isinstance(block, _Block):
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

    def keys(self) -> T.Iterable[str]:
        yield from map(lambda child: child.name, self)

    def values(self) -> T.Iterable[_Block]:
        yield from self

    def items(self) -> T.Iterable[T.Tuple[str, _Block]]:
        yield from map(lambda child: (child.name, child), self)

    def __iter__(self) -> T.Iterable[_Block]:
        return iter(filter(lambda x: isinstance(x, _Block), self.block.children))

    def __getattr__(self, item: str) -> _Block:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __setattr__(self, item: str, other):

        if not item.startswith('_') and isinstance(other, _Block) and ((item in self) or (not hasattr(self, item))):
            self[item] = other
        else:
            super(_BlockSubBlocks, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(_BlockSubBlocks, self).__delattr__(item)

    def __dir__(self):
        return list(self.keys()) + list(super(_BlockSubBlocks, self).__dir__())


class _BlockPortsUpstream:

    def __init__(self, _block_ports_section: _BlockPortsSection):
        self._block_ports_section = _block_ports_section

    def clear(self):
        for _, port in self._block_ports_section.items():
            port.upstream.clear()

    def __iter__(self) -> T.Iterable[Port]:
        return iter(set(chain(port.upstream for port in self._block_ports_section.values())))


class _BlockPortsDownstream:

    def __init__(self, _block_ports_section: _BlockPortsSection):
        self.__block_ports_section = _block_ports_section

    def clear(self):
        for _, port in self.__block_ports_section.items():
            port.downstream.clear()

    def __iter__(self) -> T.Iterable[Port]:
        return iter(set(chain(port.downstream for port in self.__block_ports_section.values())))


class _BlockPortsSection:
    """ For treating input ports and output ports separately """

    def __init__(self, _block_ports: _BlockPorts, _port_class, _auxiliary: bool):
        self._block_ports = _block_ports
        self.__port_class = _port_class

        self.__names_to_instances = OrderedDict()
        self.__instances_to_names = OrderedDict()

        self.__upstream = _BlockPortsUpstream(_block_ports_section=self)
        self.__downstream = _BlockPortsDownstream(_block_ports_section=self)
        self.__auxiliary = _auxiliary

    def __bool__(self):
        return True

    @property
    def auxiliary(self):
        return self.__auxiliary

    @property
    def block(self):
        return self._block_ports.block

    @property
    def port_graph__(self):
        return self._block_ports.port_graph__

    @property
    def upstream(self):
        return self.__upstream

    @property
    def downstream(self):
        return self.__downstream

    def __call__(self, force_tuple=False) -> T.Union[None, Port, T.Tuple[Port]]:
        """ A nice way to get the ports as a tuple """

        if not force_tuple and len(self) == 0:
            return None

        elif not force_tuple and len(self) == 1:
            return next(iter(self.values()))

        else:
            return tuple(self.values())

    def __iter__(self) -> T.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(_BlockPortsSection, self).__dir__())

    def __contains__(self, item: T.Union[str, Port]):
        if isinstance(item, str):
            return item in self.__names_to_instances

        if isinstance(item, Port):
            return item in self.__instances_to_names

        return False

    def __getitem__(self, item: T.Union[str, int]) -> Port:
        """ Retrieve port instances by name """
        if isinstance(item, str):
            return self.__names_to_instances[item]

        elif isinstance(item, int):
            return list(self.values())[item]

        else:
            raise TypeError(item)

    def __setitem__(self, item: T.Union[str, int], other: T.Optional[Port]):
        """ Connect port to other port """

        port: Port = self[item]
        port.upstream.clear()

        if other is None:
            return

        # Any value that is not a port will wrapped with Const class
        # Blocks are not allowed
        if not isinstance(other, Port):
            # TODO it could be a good idea to have a block Factory instead of this
            from blox.core.block import Const
            if isinstance(other, _Block):
                raise BlockError("Cannot set ports with blocks")
            other = Const(value=other).Out()

        assert isinstance(other, Port)

        # If one of the blocks is "floating" move it under the other
        port_graph = port.upstream.port_graph__
        other_port_graph = other.downstream.port_graph__

        if port_graph is not None and other_port_graph is None:
            other.block.parent = port_graph.block

        elif other_port_graph is not None and port_graph is None:
            port.block.parent = other_port_graph.block

        # Perform the connection (has more checks inside)
        other.feed(port)

    def __delitem__(self, item: T.Union[str, int]):
        if isinstance(item, int):
            item = list(self.keys())[item]
        self.remove(item)

    def __getattr__(self, item: str) -> Port:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __setattr__(self, item, other):
        if not item.startswith('_') and (item in self):
            self[item] = other
        else:
            super(_BlockPortsSection, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(_BlockPortsSection, self).__delattr__(item)

    def __len__(self) -> int:
        return len(self.__names_to_instances)

    def keys(self) -> T.Iterable[str]:
        yield from self.__names_to_instances.keys()

    def values(self) -> T.Iterable[Port]:
        yield from self.__names_to_instances.values()

    def items(self) -> T.Iterable[T.Tuple[str, Port]]:
        yield from self.__names_to_instances.items()

    def __assert_name(self, name):
        assert_identifier(name)
        if name in self._block_ports:
            raise BlockError(f"Block {self.block} already has a port with the name {name}")

        if name in self.block.blocks:
            raise BlockError(f"Block {self.block} already has a sub block with the name {name}")

        if hasattr(self.block, name):
            raise AttributeError(f"Block {self.block} already has an attribute: {name}")

    def new(self, name) -> Port:
        """ Creates a new port with given name """
        self.__assert_name(name)

        if self.block.lock_ports:
            raise BlockError(f"Cannot add ports since {self.block} has lock_ports=True")

        # Instantiate the class
        # port = self.__port_class(_name=name, _block_ports_section=self, _auxiliary=self.auxiliary)
        port = self.__port_class(_block_ports_section=self, _auxiliary=self.auxiliary)

        # Store mappings name <-> instance
        self.__names_to_instances[name] = port
        self.__instances_to_names[port] = name

        return port

    def get_name(self, port: Port) -> str:
        return self.__instances_to_names[port]

    def rename(self, old_name, new_name):
        self.__assert_name(new_name)
        if self.block.lock_ports:
            raise BlockError(f"Cannot rename ports since {self.block} has lock_ports=True")

        port = self[old_name]

        # Store mappings name <-> instance
        self.__names_to_instances[new_name] = port
        self.__instances_to_names[port] = new_name

        del self.__names_to_instances[old_name]

        return port

    def remove(self, name):
        """ Removes a port """
        if self.block.lock_ports:
            raise BlockError(f"Cannot remove ports since {self.block} has lock_ports=True")

        port: Port = self[name]
        port.upstream.clear()
        port.downstream.clear()

        # Must use the parent class method because we disabled setting the Port parent directly
        super(Port, Port).parent.fset(port, None)

        del self.__instances_to_names[port]
        del self.__names_to_instances[name]

    def assign_all(self, others: T.Iterable):
        """ Make others feed all ports in self """
        others = list(others)

        if len(self) != len(others):
            BlockError(f"Expected {len(self)} ports, given {len(others)}")

        for port_name, other in zip(self.keys(), others):
            self[port_name] = other

    def sort(self):
        """ Sort the port instances by names """
        self.__names_to_instances = OrderedDict(sorted(self.__names_to_instances.items(), key=first))


class _BlockPorts:
    """ The place to hold all info about a block's ports """

    def __init__(self, _block: _Block):
        self.__block = _block

        # Containers to hold actual ports
        self.__in_ports = _BlockPortsSection(_block_ports=self, _port_class=_InPort, _auxiliary=False)
        self.__out_ports = _BlockPortsSection(_block_ports=self, _port_class=_OutPort, _auxiliary=False)
        self.__aux_in_ports = _BlockPortsSection(_block_ports=self, _port_class=_InPort, _auxiliary=True)
        self.__aux_out_ports = _BlockPortsSection(_block_ports=self, _port_class=_OutPort, _auxiliary=True)

    def __bool__(self):
        return True

    @property
    def In(self) -> _BlockPortsSection:
        return self.__in_ports

    @property
    def Out(self) -> _BlockPortsSection:
        return self.__out_ports

    @property
    def AuxIn(self) -> _BlockPortsSection:
        return self.__aux_in_ports

    @property
    def AuxOut(self) -> _BlockPortsSection:
        return self.__aux_out_ports

    @In.setter
    def In(self, others):
        if isinstance(others, Port):
            others = (others,)
        self.In.assign_all(others)

    @Out.setter
    def Out(self, others):
        if isinstance(others, Port):
            others = (others,)
        self.Out.assign_all(others)

    @AuxIn.setter
    def AuxIn(self, others):
        if isinstance(others, Port):
            others = (others,)
        self.AuxIn.assign_all(others)

    @AuxOut.setter
    def AuxOut(self, others):
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
    def block(self) -> _Block:
        return self.__block

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
            super(_BlockPorts, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(_BlockPorts, self).__delattr__(item)

    # To give it a Look-and-Feel of a dictionary
    def keys(self) -> T.Iterable[str]:
        yield from chain(self.__in_ports.keys(), self.__out_ports.keys(),
                         self.__aux_in_ports.keys(), self.__aux_out_ports.keys())

    def values(self) -> T.Iterable[Port]:
        yield from chain(self.__in_ports.values(), self.__out_ports.values(),
                         self.__aux_in_ports.values(), self.__aux_out_ports.values())

    def items(self) -> T.Iterable[T.Tuple[str, Port]]:
        yield from chain(self.__in_ports.items(), self.__out_ports.items(),
                         self.__aux_ports.values(), self.__aux_ports.values())

    def __len__(self) -> int:
        return len(self.__in_ports) + len(self.__out_ports) + \
               len(self.__aux_in_ports) + len(self.__aux_out_ports)

    def __iter__(self) -> T.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(_BlockPorts, self).__dir__())


class _PortGraph:

    def __init__(self, _block):
        self.__block = _block
        self.__graph = nx.DiGraph()
        self.__changed = True

        self.__essential_blocks_toposort = None
        self.__dangling_blocks_toposort = None

    @property
    def block(self):
        return self.__block

    @property
    def changed(self):
        return self.__changed

    def set_changed(self):
        self.__changed = True
        self.block.on_port_graph_change()

    def add_edge(self, *args, **kwargs):
        self.__graph.add_edge(*args, **kwargs)
        self.set_changed()

    def add_node(self, *args, **kwargs):
        self.__graph.add_node(*args, **kwargs)
        self.set_changed()

    def __contains__(self, item):
        return item in self.__graph

    def remove_edge(self, *args, **kwargs):
        self.__graph.remove_edge(*args, **kwargs)
        self.set_changed()

    def remove_node(self, *args, **kwargs):
        self.__graph.remove_node(*args, **kwargs)
        self.set_changed()

    def in_edges(self, *args, **kwargs):
        return self.__graph.in_edges(*args, **kwargs)

    def out_edges(self, *args, **kwargs):
        return self.__graph.out_edges(*args, **kwargs)

    def in_degree(self, *args, **kwargs):
        return self.__graph.in_degree(*args, **kwargs)

    def out_degree(self, *args, **kwargs):
        return self.__graph.out_degree(*args, **kwargs)

    def edges(self):
        yield from self.__graph.edges

    def toposort(self):

        if self.__changed:
            # Use the port equivalence relation p1 ~ p2 <=> p1.block == p2.block to
            # convert the port graph to block graph. The function nx.quotient_graph will
            # create a graph whose labels are frozenset object. We convert them to block objects
            block_graph = nx.quotient_graph(self.__graph, partition=lambda x, y: x.block == y.block)
            block_graph = nx.relabel_nodes(block_graph, mapping=lambda x: next(iter(x)).block)

            # Add all block's children to the graph, in case some don't have any edges
            # for child in self.block.children:
            for child in self.block.blocks:
                block_graph.add_node(child)

            self.__essential_blocks_toposort = []
            self.__dangling_blocks_toposort = []

            for ccomp in nx.weakly_connected_components(block_graph):

                # The essential component is the one in which the parent block is in
                if self.block in ccomp:
                    if len(ccomp) > 1:
                        sub_graph = nx.subgraph(block_graph, ccomp - {self.block})
                        self.__essential_blocks_toposort.extend(nx.topological_sort(sub_graph))
                else:
                    sub_graph = nx.subgraph(block_graph, ccomp)
                    self.__dangling_blocks_toposort.extend(nx.topological_sort(sub_graph))

            self.__changed = False

    def topo_blocks_essential(self) -> T.Iterable[_Block]:
        self.toposort()
        yield from self.__essential_blocks_toposort

    def topo_blocks_dangling(self) -> T.Iterable[_Block]:
        self.toposort()
        yield from self.__dangling_blocks_toposort

    def topo_blocks(self) -> T.Iterable[_Block]:
        self.toposort()
        yield from chain(self.__essential_blocks_toposort, self.__dangling_blocks_toposort)


class _BlockPersisters:
    def __init__(self, _block):
        self._block = _block
        self._persisters = OrderedDict()

    @property
    def block(self):
        return self._block

    def __contains__(self, item):
        return item in self._persisters

    def __getitem__(self, item: str) -> Persister:
        return self._persisters[item]

    def __delitem__(self, item: str):
        if item in self._persisters:
            del self._persisters[item]
        else:
            raise KeyError(item)

    def __getattr__(self, item: str) -> Persister:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(_BlockPersisters, self).__delattr__(item)

    def add_persister__(self, name, persister: Persister):
        self._persisters[name] = persister

    # To give it a Look-and-Feel of a dictionary
    def keys(self) -> T.Iterable[str]:
        return self._persisters.keys()

    def values(self) -> T.Iterable[Port]:
        return self._persisters.values()

    def items(self) -> T.Iterable[T.Tuple[str, Port]]:
        return self._persisters.items()

    def __len__(self) -> int:
        return len(self._persisters)

    def __iter__(self) -> T.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(_BlockPersisters, self).__dir__())


class _Block(NamedNodeMixin):
    """ The basic component that builds systems.

     Blocks represent closed environments where computations take place. All communication
     is done via the blocks Ports. Inputs are read from the InPorts and outputs are written on
     the OutPorts. Blocks can contain children blocks (implemented using a tree).
     """

    def __init__(self,
                 name: T.Optional[str]=None,
                 In: T.Optional[T.Iterable[str]]=None,
                 Out: T.Optional[T.Iterable[str]]=None,
                 AuxIn: T.Optional[T.Iterable[str]] = None,
                 AuxOut: T.Optional[T.Iterable[str]] = None,
                 parent: T.Optional[_Block]=None):

        # The port handling class
        self.__ports = _BlockPorts(_block=self)

        # The sub blocks handling class
        self.__blocks = _BlockSubBlocks(_block=self)

        # Graph to handle port connectivity
        self.__port_graph = _PortGraph(_block=self)

        # The device to which the block is bound
        self.__device = DefaultDevice()

        # Persistence modules associated with the block
        self.__persisters = _BlockPersisters(_block=self)

        # This is a mechanism to handle naming collision in the parent
        if name is None:
            self.__base_name = camel_to_snake(self.__class__.__name__)
            # self.__auto_rename = True
        else:
            if not isinstance(name, str):
                raise TypeError(f"Illegal type for name: {type(name)}")

            self.__base_name = str(name)
            # self.__auto_rename = False

        # Allow naming flexibility in case of name collision
        self.__auto_rename = True

        # Extra attribute containers to check with  __contains__, __getitem__, __setitem__, __getattr__, __setattr__
        self.__extra_attribute_containers = [self.ports, self.blocks]

        self.__name_modifier = 0
        assert_identifier(self.__base_name)

        # Whether sub blocks can be added
        self.__atomic = False

        # Whether ports can be added or removed
        self.__lock_ports = False

        # Whether children can be added or removed
        self.__lock_children = False

        # Whether the block can be removed from its parent
        self.__lock_parent = False

        # Add inputs
        for name in parse_ports(In, default_prefix='i'):
            self.In.new(name)

        # Add outputs
        for name in parse_ports(Out, default_prefix='o'):
            self.Out.new(name)

        # Add inputs
        for name in parse_ports(AuxIn, default_prefix='xi'):
            self.AuxIn.new(name)

        # Add outputs
        for name in parse_ports(AuxOut, default_prefix='xo'):
            self.AuxOut.new(name)

        # Set parent if given
        if parent is not None:
            self.parent = parent

    def __bool__(self):
        return True

    def register_attribute_container__(self, obj):
        """ Used by subclasses that define attribute containers to be accessed from the class """
        self.__extra_attribute_containers.append(obj)

    # The following scheme will serialize the root block twice. Therefore, when
    # using an unpickled copy block, just put block = block.ports.block
    def __getstate__(self):

        odict = self.__dict__.copy()

        # This is the first block we encounter in an hierarchy
        if _detached_block.block is None:
            with _detached_block(self):
                odict['_NodeMixin__parent'] = None
                state = {'state': pickle.dumps(odict)}

            return state

        # This is when we pickle circular references to the block
        elif _detached_block.block is self:
            odict['_NodeMixin__parent'] = None
            return odict

        # This is for everything else
        else:
            if _detached_block.block in self.blocks:
                raise BlockError("Pickle Leak")

            return odict

    def __setstate__(self, state):

        # This is the first block we encounter in an hierarchy
        if _detached_block.block is None:
            with _detached_block(self):
                self.__dict__.update(pickle.loads(state['state']))

        # This is for everything else
        else:
            self.__dict__.update(state)

    def copy(self):
        return pickle.loads(pickle.dumps(self)).fix_pickle()

    # This fixes the double pickling of the root block
    def fix_pickle(self) -> _Block:
        return self.ports.block

    @property
    def persisters(self):
        return self.__persisters

    @property
    def device(self) -> BlockDevice:
        return self.__device

    @device.setter
    def device(self, device: T.Optional[BlockDevice]):

        # None - means local CPU
        device = maybe_or(device, DefaultDevice())

        # Maybe make devices singletons?
        if device is not self.__device:
            self.__device.unset(self)
            self.__device = device
            self.__device.set(self)

        for child in self.blocks.descendants:
            child.device = device

    @property
    def id(self) -> int:
        return id(self)

    @property
    def atomic(self) -> bool:
        return self.__atomic

    @atomic.setter
    def atomic(self, value: bool):
        if value and len(self.blocks):
            raise BlockError("A block with children cannot be made atomic")
        self.__atomic = value

    @property
    def lock_ports(self):
        return self.__lock_ports

    @lock_ports.setter
    def lock_ports(self, value: bool):
        self.__lock_ports = value

    @property
    def lock_children(self):
        return self.__lock_children

    @lock_children.setter
    def lock_children(self, value: bool):
        self.__lock_children = value

    @property
    def lock_parent(self):
        return self.__lock_parent

    @lock_parent.setter
    def lock_parent(self, value: bool):
        self.__lock_parent = value

    @property
    def name(self) -> str:
        if self.__name_modifier != 0:
            return f"{self.__base_name}_{self.__name_modifier}"
        return self.__base_name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str):
            raise TypeError(type(value))

        if not self.is_root and value != self.name and hasattr(self.parent, value):
            raise ValueError(f"Blocks {self} parent has an attribute {value}")

        assert_identifier(value)
        self.__name_modifier = 0
        self.__base_name = value
        self.auto_rename = False

        # Advance the counter for the current name
        if not self.is_root:
            self.parent.blocks.generate_name_modifier__(self.__base_name)

    @property
    def auto_rename(self) -> bool:
        return self.__auto_rename

    @auto_rename.setter
    def auto_rename(self, value: bool):
        self.__auto_rename = value

    @property
    def blocks(self):
        return self.__blocks

    @property
    def ports(self):
        return self.__ports

    @property
    def port_graph__(self):
        return self.__port_graph

    @property
    def In(self) -> _BlockPortsSection:
        return self.ports.In

    @In.setter
    def In(self, others):
        self.ports.In = others

    @In.deleter
    def In(self):
        del self.ports.In

    @property
    def Out(self) -> _BlockPortsSection:
        return self.ports.Out

    @Out.setter
    def Out(self, others):
        self.ports.Out = others

    @Out.deleter
    def Out(self):
        del self.ports.Out

    @property
    def AuxIn(self) -> _BlockPortsSection:
        return self.ports.AuxIn

    @AuxIn.setter
    def AuxIn(self, others):
        self.ports.AuxIn = others

    @AuxIn.deleter
    def AuxIn(self):
        del self.ports.AuxIn

    @property
    def AuxOut(self) -> _BlockPortsSection:
        return self.ports.AuxOut

    @AuxOut.setter
    def AuxOut(self, others):
        self.ports.AuxOut = others

    @AuxOut.deleter
    def AuxOut(self):
        del self.ports.AuxOut

    def _pre_detach(self, parent: _Block):
        parent.pre_detach_child_check(self)

        if parent.lock_children:
            raise BlockError(f"Block {parent} has lock_children=True")

        if self.lock_parent:
            raise BlockError(f"Block {self} has lock_parent=True")

        self.ports.In.upstream.clear()
        self.ports.Out.downstream.clear()

        # Let the parent's port graph know that one of the blocks is gone
        parent.port_graph__.set_changed()

    def _post_detach(self, parent: _Block):
        parent.post_detach_child_check(self)

        self.__name_modifier = 0  # When blocks are in the root level, they regain their original name

    def _pre_attach(self, parent: _Block):
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

    def _post_attach(self, parent: _Block):
        parent.post_attach_child_check(self)

        self.__name_modifier = parent.blocks.generate_name_modifier__(self.__base_name)

        # In case someone wants to screw things up and add a port with name such as "abc_123"
        if self.__name_modifier != 0:
            parent.blocks.generate_name_modifier__(self.name)

        # Let the parent's port graph know that there is another block around
        parent.port_graph__.set_changed()

    # Hooks to be called from the parent block
    def pre_attach_child_check(self, child: _Block):
        pass

    def post_attach_child_check(self, child: _Block):
        pass

    def pre_detach_child_check(self, child: _Block):
        pass

    def post_detach_child_check(self, child: _Block):
        pass

    # Hooks for updates on changes in the port graph of the block
    def on_port_graph_change(self):
        pass

    def __getitem__(self, item: str) -> T.Union[_Block, Port]:
        """ Provide dictionary-like syntax to access sub-blocks and ports """

        for container in self.__extra_attribute_containers:
            if item in container:
                return container[item]

        raise KeyError(item)

    def __delitem__(self, item: str):

        for container in self.__extra_attribute_containers:
            if item in container:
                del container[item]
                return

        raise KeyError(item)

    def __setitem__(self, key, value):
        """ Port connections and block addition """

        for container in self.__extra_attribute_containers:
            if key in container:
                container[key] = value
                return

        # Adding a new block
        if not isinstance(value, _Block):
            raise TypeError(value)

        self.blocks[key] = value

    def __contains__(self, item):

        if item in self.__dict__:
            return True

        # Check the extra containers (supplied by subclasses)
        if isinstance(item, str):
            for container in self.__extra_attribute_containers:
                if container.__contains__(item):
                    return True

        if isinstance(item, Port):
            return self.ports.__contains__(item)

        if isinstance(item, _Block):
            return self.blocks.__contains__(item)

        return False

    def __getattr__(self, item: str) -> T.Union[Port, _Block]:
        try:
            return super(_Block, self).__getattribute__(item)

        except AttributeError as exception:
            if not item.startswith('_') and self.__contains__(item):
                return self[item]
            else:
                raise exception

    def __setattr__(self, item: str, other):

        # Private and mangled attributes are treated the standard way
        if item.startswith('_'):
            super(_Block, self).__setattr__(item, other)

        else:
            # Adding a new block
            if not hasattr(self, item) and isinstance(other, _Block):
                self.blocks[item] = other
                return

            # For stuff inside the extra containers we call the container's __setitem__
            for container in self.__extra_attribute_containers:
                if item in container:
                    container[item] = other
                    return

            # Everything else must be handled the standard way
            else:
                super(_Block, self).__setattr__(item, other)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(_Block, self).__delattr__(item)

    def __len__(self) -> int:
        return len(self.blocks)

    def keys(self):
        # yield from chain(self.blocks.keys(), self.ports.keys())
        yield from chain.from_iterable(container.keys() for container in self.__extra_attribute_containers)

    def values(self):
        # yield from chain(self.blocks.values(), self.ports.values())
        yield from chain.from_iterable(container.values() for container in self.__extra_attribute_containers)

    def items(self):
        # yield from chain(self.blocks.items(), self.ports.items())
        yield from chain.from_iterable(container.items() for container in self.__extra_attribute_containers)

    def __call__(self, *args, **kwargs) -> T.Union[None, Port, T.Tuple[Port]]:
        """
        This method allows composing blocks over ports.
        Connects the block's inputs to the provided ports
        """

        # Handle the case when In and Out are passed without ()
        args = list(chain(*map(lambda arg: [arg] if not isinstance(arg, _BlockPortsSection) else arg, args)))

        if len(args) + len(kwargs) > len(self.In):
            raise BlockError(f"Too many inputs provided, expected at most: {len(self.In)}, "
                             f"given: {len(args) + len(kwargs)}")

        for port_name, src in chain(zip(self.In.keys(), args), kwargs.items()):
            self.In[port_name] = src

        # Return the output ports
        return self.Out()

    def __dir__(self):
        return list(self.keys()) + list(super(_Block, self).__dir__())

    def sort(self):
        """ Perform a topological sort on self and all child blocks recursively """
        self.blocks.sort()
        for child in self.blocks:
            child.sort()

        return self

    @abstractmethod
    def propagate(self, session) -> None:
        pass

    @abstractmethod
    async def pull(self, port: Port, session) -> T.Any:
        pass

    @abstractmethod
    def push(self, port: Port, session) -> None:
        pass

    @classmethod
    def wrap(cls, **kwargs):
        """ Use this method to convert function definition into block instances """

        def create_block(wrapped_fn) -> cls:

            def block_builder(fn, *, name=None, **fn_kwargs):

                # Obtain the non-keyword arguments of fn - these will serve as input port names
                num_in_ports = fn.__code__.co_argcount
                in_port_names = fn.__code__.co_varnames[0:num_in_ports]

                # Get the Out argument if it is there
                Out = kwargs.pop('Out') if 'Out' in kwargs else None

                default_name = camel_to_snake(fn.__code__.co_name)
                params = dict(name=maybe_or(name, default_name), In=in_port_names)
                params.update(kwargs)

                # Initialize the block with given input ports and the wrapped function name
                block = cls(**params)
                block.auto_rename = True

                # Get the function outputs
                out = fn(*block.In, **fn_kwargs)

                if not isinstance(out, tuple) and not isinstance(out, list) and not isinstance(out, Port):
                    raise BlockError("Wrapped function must return either a single port, a list or a tuple of ports")

                # Make sure out is iterable
                if isinstance(out, Port):
                    out = (out,)

                # Determine the output names
                if Out is None:
                    Out = parse_ports(len(out), default_prefix='o') if not isinstance(out, Port) else 1
                else:
                    Out = parse_ports(Out, default_prefix='o')
                    if len(Out) != len(out):
                        raise BlockError("The number of returned ports doesn't match the specified number of ports")

                for name, port in zip(Out, out):
                    block.Out.new(name)
                    block.Out[name] = port

                return block

            # The decorators returns a function that creates an instance of the block, like a constructor
            return partial(block_builder, wrapped_fn)

        return create_block

    @classmethod
    def pack(cls, blocks, *args, **kwargs) -> None:
        """ Pack provided blocks in a new block of the given class """

        if not blocks:
            raise BlockError("At least one block must be provided")

        # The new block will be added here
        parent = blocks[0].parent

        # All of the blocks must share the same parent
        if not all(blk.parent is parent for blk in blocks):
            raise BlockError("All of the blocks must share the same parent")

        # Store all existing connections
        connections = set()
        for port in chain.from_iterable([blk.ports for blk in blocks]):

            if port.is_in:
                connections.update((ups, port) for ups in port.upstream)
            else:
                connections.update((port, dws) for dws in port.downstream)

        # Create a new block instance and place in under the parent
        block = cls(*args, **kwargs, parent=parent)

        # Move blocks under parent block
        for blk in blocks:
            blk.parent = block

        # Restore connections
        for p1, p2 in connections:
            try:
                p1.feed(p2)

            # If connection adding has failed, it probably means that this is an external connection,
            # therefore we add an intermediate port
            except PortError:

                def add_proxy_from(p):
                    if p.is_in and not p.auxiliary:
                        return block.In.new(f'{p.block.name}_{p.name}')

                    elif p.is_in and p.auxiliary:
                        return block.AuxIn.new(f'{p.block.name}_{p.name}')

                    elif not p.is_in and not p.auxiliary:
                        return block.Out.new(f'{p.block.name}_{p.name}')

                    else:
                        return block.AuxOut.new(f'{p.block.name}_{p.name}')

                # The case when p1 is outside
                if p2.block.parent is block:
                    new_port = add_proxy_from(p2)

                # The case when p2 is outside
                else:
                    # Add new port
                    new_port = add_proxy_from(p1)

                p1.feed(new_port)
                new_port.feed(p2)

        block.ports.sort()


class _PortOperatorMixin:

    def __add__(self, other: T.Any) -> Port:
        from blox.core.block import Add
        return Add(In=2, Out=1)(self, other)

    def __radd__(self, other) -> Port:
        from blox.core.block import Add
        return Add(In=2, Out=1)(other, self)

    def __sub__(self, other: T.Any) -> Port:
        from blox.core.block import Sub
        return Sub(In=2, Out=1)(self, other)

    def __rsub__(self, other) -> Port:
        from blox.core.block import Sub
        return Sub(In=2, Out=1)(other, self)

    def __mul__(self, other: T.Any) -> Port:
        from blox.core.block import Mul
        return Mul(In=2, Out=1)(self, other)

    def __rmul__(self, other) -> Port:
        from blox.core.block import Mul
        return Mul(In=2, Out=1)(other, self)

    def __truediv__(self, other) -> Port:
        from blox.core.block import TrueDiv
        return TrueDiv(In=2, Out=1)(self, other)

    def __rtruediv__(self, other) -> Port:
        from blox.core.block import TrueDiv
        return TrueDiv(In=2, Out=1)(other, self)

    def __floordiv__(self, other) -> Port:
        from blox.core.block import FloorDiv
        return FloorDiv(In=2, Out=1)(self, other)

    def __rfloordiv__(self, other) -> Port:
        from blox.core.block import FloorDiv
        return FloorDiv(In=2, Out=1)(other, self)

    def __matmul__(self, other) -> Port:
        from blox.core.block import MatMul
        return MatMul(In=2, Out=1)(self, other)

    def __rmatmul__(self, other) -> Port:
        from blox.core.block import MatMul
        return MatMul(In=2, Out=1)(other, self)


class Port(NamedNodeMixin, _PortOperatorMixin):
    """ The gateways to and from Blocks. Always instantiated using _BlockPortsSection.new() """

    def __init__(self, _block_ports_section: _BlockPortsSection, _auxiliary: bool):

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
    def block(self) -> _Block:
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
    def upstream(self) -> _PortUpstream:
        pass

    @property
    @abstractmethod
    def downstream(self) -> _PortDownstream:
        pass

    @property
    @abstractmethod
    def is_in(self) -> bool:
        pass

    @property
    def is_out(self) -> bool:
        return not self.is_in

    @property
    def section(self) -> _BlockPortsSection:

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

    def __assert_session(self, x):
        from blox.core.engine import Session
        if not isinstance(x, Session):
            raise TypeError(x)

    def __getitem__(self, session):
        self.__assert_session(session)
        return session[self]

    def __setitem__(self, session, value):
        self.__assert_session(session)
        session[self] = value

    def __contains__(self, session):
        self.__assert_session(session)
        return self in session

    def __delitem__(self, session):
        self.__assert_session(session)
        del session[self]

    def __call__(self, session, timeout=None):
        self.__assert_session(session)
        return session(port=self, timeout=timeout)


class _PortUpstream(ABC):

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

    def __iter__(self) -> T.Iterable[Port]:
        if not len(self):
            return iter(())
        return iter(map(lambda pair: pair[0],
                        self.port_graph__.in_edges(self.port)))

    def __call__(self) -> T.Optional[Port]:
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


class _PortDownstream(ABC):

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

    def __iter__(self) -> T.Iterable[Port]:
        if not len(self):
            return iter(())

        return iter(map(lambda pair: pair[1], self.port_graph__.out_edges(self.port)))

    def __call__(self) -> T.Tuple[Port]:
        return tuple(self)

    def clear(self):
        """ Clear connections on the downstream """
        if self.port_graph__ is not None and self.port in self.port_graph__:
            self.port_graph__.remove_node(self.port)


class _InPortUpstream(_PortUpstream):
    @property
    def port_graph__(self) -> T.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph__


class _OutPortUpstream(_PortUpstream):
    @property
    def port_graph__(self):
        return self.port.block.ports.port_graph__


class _InPortDownstream(_PortDownstream):
    @property
    def port_graph__(self):
        return self.port.block.ports.port_graph__


class _OutPortDownstream(_PortDownstream):
    @property
    def port_graph__(self) -> T.Optional[nx.DiGraph]:
        if self.port.block.is_root:
            return None
        else:
            return self.port.block.parent.ports.port_graph__


class _InPort(Port):

    def __init__(self, *args, **kwargs):
        super(_InPort, self).__init__(*args, **kwargs)
        self.__upstream = _InPortUpstream(_port=self)
        self.__downstream = _InPortDownstream(_port=self)

    @property
    def upstream(self):
        return self.__upstream

    @property
    def downstream(self):
        return self.__downstream

    @property
    def is_in(self):
        return True


class _OutPort(Port):

    def __init__(self, *args, **kwargs):
        super(_OutPort, self).__init__(*args, **kwargs)
        self.__upstream = _OutPortUpstream(_port=self)
        self.__downstream = _OutPortDownstream(_port=self)

    @property
    def upstream(self):
        return self.__upstream

    @property
    def downstream(self):
        return self.__downstream

    @property
    def is_in(self) -> bool:
        return False

