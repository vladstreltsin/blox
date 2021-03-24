from __future__ import annotations
import typing as tp

if tp.TYPE_CHECKING:
    from blox.core.node import NamedNode


def in_port_filter(node: NamedNode) -> bool:
    from blox.core.port import Port
    return isinstance(node, Port) and node.tag == 'In'


def out_port_filter(node: NamedNode) -> bool:
    from blox.core.port import Port
    return isinstance(node, Port) and node.tag == 'Out'


def block_filter(node: NamedNode) -> bool:
    from blox.core.block import Block
    return isinstance(node, Block)


def port_filter(node: NamedNode) -> bool:
    from blox.core.port import Port
    return isinstance(node, Port)
