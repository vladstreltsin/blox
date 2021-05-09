from __future__ import annotations
from blox.core.compute import Computable
from blox.core.state import State, XPathState
from blox.core.port import Port
import typing as tp
from collections import namedtuple
from dataclasses import dataclass
import traceback
import sys
from dataclasses import field
from collections import OrderedDict


@dataclass
class Target:
    """ This is used as a marker for ports that need to be computed """
    target_name: str


class XPathServer:

    def __init__(self, root_block: Computable):
        self.root_block = root_block

    def __call__(self, xpstate: XPathState, target_or_targets: tp.Union[str, tp.Iterable[str]]) -> XPathState:

        # Make a copy because we are going to change some entries in it
        xpstate = xpstate.copy()

        if isinstance(target_or_targets, str):
            target_or_targets = [target_or_targets]
        else:
            target_or_targets = list(target_or_targets)

        # Place sentinels on the target ports
        for target_name in target_or_targets:
            xpstate[target_name] = Target(target_name=target_name)

        # Convert xpath-state to a normal state
        state = xpstate.to_state(self.root_block)

        # Extract all ports whose value is an instance of Target
        target_ports = dict()
        for port in list(state.ports()):
            if isinstance(state[port], Target):
                target_name = state[port.block].ports.pop(port).target_name
                target_ports[target_name] = port

        # Compute ports. If an error is raised an exception will be thrown here
        for target_name, port in target_ports.items():
            state(port)

        return state.to_xpath_state(self.root_block)

# class JSONServer:
#
#     def __init__(self, root_block: Computable):