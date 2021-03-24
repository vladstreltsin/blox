from __future__ import annotations
from blox.core.compute import Computable
from blox.core.state import State
from blox.core.port import Port
import typing as tp


class BloxMap:
    """ Converts a Blox system to a function """

    def __init__(self, world: Computable):
        self.world = world

    def __call__(self, *args):
        state = State()

        for port, arg in zip(self.world.In, args):
            state[port] = arg

        result = [state(port) for port in self.world.Out]

        if len(self.world.Out) == 0:
            return None

        elif len(self.world.Out) == 1:
            return result[0]

        return result

