from __future__ import annotations
from blox.core.compute import Computable
from blox.core.state import State, Importer, Exporter, ExportResult
from blox.core.port import Port
import typing as tp
from collections import namedtuple
from dataclasses import dataclass
import traceback
import sys

@dataclass
class Target:
    """ This is used as a marker for ports that need to be computed """
    target: str


class BloxServer:
    """ Converts a Blox system to a server """

    def __init__(self, world: Computable):
        self.world = world

    def __call__(self,
                 targets: tp.Iterable[str],
                 ports: tp.Dict[str, tp.Any],
                 meta: tp.Dict[str, tp.Any],
                 params: tp.Dict[str, tp.Dict[str, tp.Any]]) -> ExportResult:

        targets = list(targets)
        ports = ports.copy()
        params = params.copy()

        # Fill in the targets to compute. This is done because we want to convert
        # them targets to Ports.
        for target in targets:
            ports[target] = Target(target)

        # Construct the initial state
        state: State = Importer(self.world)(ports, meta, params)

        # Pop out all ports that need to be computed
        target_ports = {}
        for port in list(state.keys()):
            if isinstance(state[port], Target):
                target = state.pop(port).target
                target_ports[target] = port

        # Compute ports. If an error occurs, export the state and return an error
        for target, port in target_ports.items():
            try:
                state(port)

            except Exception as e:
                traceback.print_exc(file=sys.stdout)
                state.meta['exception'] = str(e)
                state.meta['failed_target'] = target
                break

        return Exporter(self.world)(state)

