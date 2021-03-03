from __future__ import annotations
from blox_old.core.block.base import Port, _Block
from collections import OrderedDict
import typing as T
from itertools import chain
import operator

PORT_SIDES = {"EAST", "WEST", "NORTH", "SOUTH"}
SIDE_ALIGNMENTS = {"CENTER", "BEGIN", "END", "DISTRIBUTED", "JUSTIFIED"}


class VisualizationError(Exception):
    pass


class _Label:

    def __init__(self, text: str, height: T.Optional[int] = None, width: T.Optional[int] = None):
        self.text = text
        self.height = height or 5               # TODO: This is temporary!!
        self.width = width or 6*len(self.text)  # TODO: This is temporary!!

    def to_dict(self):
        return {"text": self.text,
                "height": self.height,
                "width": self.width}


class _LabelsSection:

    def __init__(self, owner: T.Union[Port, _Block]):
        self.__labels = dict()
        self.__priorities = dict()
        self.__owner = owner

    @property
    def owner(self):
        return self.__owner

    @property
    def name_label(self):
        return _Label(text=self.owner.name)

    def __iter__(self):

        return iter(chain([self.name_label],
                          [self.__labels[label_name] for label_name, _ in
                           sorted(self.__priorities.items(), key=operator.itemgetter(1))]))

    def add(self, name, priority: int = 0, **kwargs):
        if name in self.__labels:
            raise VisualizationError(f"Port label {name} exists for port {self.owner}")

        self.__labels[name] = _Label(**kwargs)
        self.__priorities[name] = priority

    def remove(self, name: str):
        if name in self.__labels:
            del self.__labels[name]
            del self.__priorities[name]


class _PortVis:

    def __init__(self, _port: Port, _diagram: ElkDiagram):
        self.__port = _port
        self.__diagram = _diagram
        self.__labels = _LabelsSection(owner=self.port)
        self.side = self.__default_side(_port)
        self.height = 5
        self.width = 5

    @property
    def diagram(self):
        return self.__diagram

    def __default_side(self, port):
        if port.is_in and not self.port.auxiliary:
            side = 'WEST'
        elif not port.is_in and not port.auxiliary:
            side = 'EAST'
        elif port.is_in and port.auxiliary:
            side = 'NORTH'
        else:
            side = 'SOUTH'
        return side

    @property
    def port(self):
        return self.__port

    @property
    def labels(self):
        return self.__labels

    @property
    def index(self):
        # return self.port.block.vis.get_port_index(port=self)
        return self.diagram[self.port.block].get_port_index(port=self.port)

    @property
    def side(self):
        # return self.port.block.vis.get_port_side(port=self)
        return self.diagram[self.port.block].get_port_side(port=self.port)

    @side.setter
    def side(self, value):
        # self.port.block.vis.set_port_side(port=self, side=value)
        self.diagram[self.port.block].set_port_side(port=self.port, side=value)

    def to_dict(self):
        return {
                "height": self.height,
                "width": self.width,
                "id": str(self.port.id),
                "labels": [label.to_dict() for label in self.labels],
                "layoutOptions": {
                    "port.side": f"{self.side}",
                    "port.index": self.index
                    },
                }

    def cleanup__(self):
        # self.port.block.vis.remove_port__(port=self)
        self.diagram[self.port.block].remove_port__(port=self.port)


class _BlockSide:
    def __init__(self, block):
        self.__block = block


class _PortSurroundings:
    def __init__(self):
        self.__top = 10.
        self.__left = 10.
        self.__bottom = 10.
        self.__right = 10.
    
    @property
    def top(self):
        return self.__top
    
    @top.setter
    def top(self, value):
        self.__top = value

    @property
    def bottom(self):
        return self.__bottom

    @bottom.setter
    def bottom(self, value):
        self.__bottom = value

    @property
    def left(self):
        return self.__left

    @left.setter
    def left(self, value):
        self.__left = value
        
    @property
    def right(self):
        return self.__right

    @right.setter
    def right(self, value):
        self.__right = value
        
    def to_dict(self):
        return {"spacing.portsSurrounding": f"[top={self.top},"
                                            f"left={self.left},"
                                            f"bottom={self.bottom},"
                                            f"right={self.right}]"}


class _Spacing:

    def __init__(self):
        self.__port_port = 10.
        self.__label_port = 2.
        self.__label_label = 10.
        self.__label_node = 10.
        self.__node_node = 10.
        self.__edge_edge = 5.
        self.__edge_label = 5.
        self.__edge_node = 5.
        self.__node_self_loop = 10.
        self.__port_surroundings = _PortSurroundings()

    @property
    def port_surroundings(self):
        return self.__port_surroundings

    @property
    def node_self_loop(self):
        return self.__node_self_loop

    @node_self_loop.setter
    def node_self_loop(self, value):
        self.__node_self_loop = value

    @property
    def edge_node(self):
        return self.__edge_node

    @edge_node.setter
    def edge_node(self, value):
        self.__edge_node = value
        
    @property
    def edge_label(self):
        return self.__edge_label

    @edge_label.setter
    def edge_label(self, value):
        self.__edge_label = value

    @property
    def edge_edge(self):
        return self.__edge_edge

    @edge_edge.setter
    def edge_edge(self, value):
        self.__edge_edge = value
        
    @property
    def node_node(self):
        return self.__node_node

    @node_node.setter
    def node_node(self, value):
        self.__node_node = value

    @property
    def label_node(self):
        return self.__label_node
    
    @label_node.setter
    def label_node(self, value):
        self.__label_node = value
        
    @property
    def label_label(self):
        return self.__label_label
    
    @label_label.setter
    def label_label(self, value):
        self.__label_label = value
        
    @property
    def label_port(self):
        return self.__label_port
    
    @label_port.setter
    def label_port(self, value):
        self.__label_port = value
    
    @property
    def port_port(self):
        return self.__port_port
    
    @port_port.setter
    def port_port(self, value):
        self.__port_port = value

    def to_dict(self):
        
        return {
            "spacing.portPort": str(self.port_port),
            "spacing.labelLabel": str(self.label_label),
            "spacing.labelPort": str(self.label_port),
            "spacing.labelNode": str(self.label_node),
            "spacing.nodeNode": str(self.node_node),
            "spacing.edgeEdge": str(self.edge_edge),
            "spacing.edgeLabel": str(self.edge_label),
            "spacing.edgeNode": str(self.edge_node),
            "spacing.nodeSelfLoop": str(self.node_self_loop),
            **self.port_surroundings.to_dict()
        }
    

class _PortAlignment:
    
    def __init__(self):
        self.__north = "DISTRIBUTED"
        self.__south = "DISTRIBUTED"
        self.__east = "DISTRIBUTED"
        self.__west = "DISTRIBUTED"
    
    @property
    def north(self):
        return self.__north
    
    @north.setter
    def north(self, value):
        assert value in SIDE_ALIGNMENTS
        self.__north = value

    @property
    def south(self):
        return self.__south

    @south.setter
    def south(self, value):
        assert value in SIDE_ALIGNMENTS
        self.__south = value

    @property
    def east(self):
        return self.__east

    @east.setter
    def east(self, value):
        assert value in SIDE_ALIGNMENTS
        self.__east = value

    @property
    def west(self):
        return self.__west

    @west.setter
    def west(self, value):
        assert value in SIDE_ALIGNMENTS
        self.__west = value

    def to_dict(self):
        return {
            "portAlignment.north": self.north,
            "portAlignment.south": self.south,
            "portAlignment.east": self.east,
            "portAlignment.west": self.west,
        }


class _NodeSize:

    def __init__(self, block):
        self._block = block
        # self.__minimum = (self.minimal_width + 20., 40.)
        self.__minimum = (self.minimal_width, self.minimal_height)
        self.__constraints = ["NODE_LABELS", "MINIMUM_SIZE"]

    @property
    def minimal_width(self):
        return max(6.*len(self.block.name), 20. * max(len(self.block.AuxIn), len(self.block.AuxOut))) + 20.

    @property
    def minimal_height(self):
        return max(20. * max(len(self.block.In), len(self.block.Out)), 20.)

    @property
    def block(self):
        return self._block

    @property
    def minimum(self):
        return self.__minimum

    @minimum.setter
    def minimum(self, value: T.Tuple[float, float]):
        value = tuple(value)
        assert len(value) == 2
        x = float(value[0])
        y = float(value[1])
        self.__minimum = (x, y)

    @property
    def constraints(self):
        return self.__constraints

    def to_dict(self):
        return {
            "nodeSize.minimum": f"({self.minimum[0]}, {self.minimum[1]})",
            "nodeSize.constraints": f"[{', '.join(self.constraints)}]",
        }


class _BlockVis:

    def __init__(self, _block: _Block, _diagram: ElkDiagram):
        self.__block = _block
        self.__diagram = _diagram
        self.__ports_to_sides = OrderedDict()
        self.__sides_to_ports = {side: OrderedDict() for side in PORT_SIDES}    # This is a dict of ordered sets
        self.__labels = _LabelsSection(owner=self.block)
        self.__show = True
        self.__algorithm = "layered"
        self.__spacing = _Spacing()
        self.__alignment = _PortAlignment()
        self.__node_size = _NodeSize(block=self.block)

    @property
    def diagram(self):
        return self.__diagram

    @property
    def node_size(self):
        return self.__node_size

    @property
    def alignment(self):
        return self.__alignment

    @property
    def spacing(self):
        return self.__spacing

    @property
    def algorithm(self):
        return self.__algorithm

    @algorithm.setter
    def algorithm(self, value):
        # TODO check validity
        self.__algorithm = value

    @property
    def block(self):
        return self.__block

    @property
    def show(self):
        return self.__show

    @show.setter
    def show(self, value: bool):
        if value:
            self.labels.remove(name='_hidden')
        else:
            self.labels.add(name='_hidden', text='#')

        self.__show = value

    @property
    def labels(self):
        return self.__labels

    def remove_port__(self, port: Port):
        if port in self.__ports_to_sides:
            side = self.__ports_to_sides[port]
            del self.__ports_to_sides[port]
            del self.__sides_to_ports[side][port]

    def set_port_side(self, port: Port, side: str):
        if side not in PORT_SIDES:
            raise VisualizationError(f"Illegal port size {side}")

        # If port already has a side
        if port in self.__ports_to_sides:
            old_side = self.__ports_to_sides[port]
            del self.__sides_to_ports[old_side][port]

        self.__ports_to_sides[port] = side
        self.__sides_to_ports[side][port] = None    # The OrderedDict here works as an "ordered set"

    def get_port_side(self, port: Port):
        return self.__ports_to_sides.get(port, None)

    def get_port_index(self, port: Port):
        side = self.get_port_side(port)
        if side is None:
            raise VisualizationError(f"No side for port {port}")

        dct = self.__sides_to_ports[side]
        idx = list(dct.keys()).index(port)

        # if side == 'EAST' or side == 'SOUTH':
        if side == 'EAST' or side == 'NORTH':
            return idx + 1

        else:
            return len(dct) - idx

    def to_dict(self):

        return {"id": str(self.block.id),
                "children": [self.diagram[child].to_dict() for child in self.block.blocks] if self.show else [],
                "labels": [label.to_dict() for label in self.labels],
                "ports": [self.diagram[port].to_dict() for port in self.block.ports],
                "edges": [{"id": f"{p1.id}_{p2.id}", "sources": [f"{p1.id}"], "targets": [f"{p2.id}"]}
                          for p1, p2 in self.block.port_graph__.edges()] if self.show else [],
                "layoutOptions": {
                    "algorithm": self.algorithm,
                    "nodeLabels.placement": "[H_CENTER, V_TOP, INSIDE]",
                    "portLabels.placement": "[OUTSIDE]",
                    "portConstraints": "FIXED_ORDER",
                    # "elk.direction": "DOWN",
                    **self.spacing.to_dict(),
                    **self.alignment.to_dict(),
                    **self.node_size.to_dict()
                    },
                }


class ElkDiagram:

    def __init__(self, block: _Block):

        self.__block_vis_dict = {}
        self.__port_vis_dict = {}
        self.__block = block

        # Build visualization classes for the hierarchy
        def _rec_export(blk):
            self.__block_vis_dict[blk] = _BlockVis(_block=blk, _diagram=self)
            for port in blk.ports:
                self.__port_vis_dict[port] = _PortVis(_port=port, _diagram=self)

            for child in blk.blocks:
                _rec_export(child)

        _rec_export(block)

    def __getitem__(self, item: T.Union[_Block, Port]):

        if isinstance(item, _Block):
            return self.__block_vis_dict[item]

        elif isinstance(item, Port):
            return self.__port_vis_dict[item]

        raise TypeError(type(item))

    @property
    def block(self):
        return self.__block

    def to_dict(self):
        return {"id": str('root'),
                "children": [self[self.block].to_dict()]
                }


# A utility function
def to_dict(block: _Block):
    return ElkDiagram(block).to_dict()


