from collections import deque
from blox.core.compute import Done, Next
from blox.etc.errors import ComputeError


class State:

    def __init__(self):
        self._data = {}

    def __contains__(self, port):
        return id(port) in self._data

    def __getitem__(self, port):
        if id(port) not in self._data:
            raise KeyError(port)
        return self._data[id(port)]

    def __setitem__(self, port, value):
        self._data[id(port)] = value

    def __delitem__(self, port):
        del self._data[id(port)]

    def compute(self, port):
        """
        Compute a port's value using the pull protocol.
        """
        stack = deque()
        arrow = Next(port)

        while True:
            # We always enter the loop with an arrow
            if isinstance(arrow, Done):

                if len(stack) == 0:
                    return arrow.value

                else:
                    arrow = stack[-1].send(arrow.value)
                    if isinstance(arrow, Done):
                        stack.pop()

            elif isinstance(arrow, Next):

                port = arrow.port
                gen = port.block.pull_generator(port, self)

                arrow = next(gen)
                if isinstance(arrow, Next):
                    stack.append(gen)

            else:
                raise ComputeError(f'Got unknown type for pull result {type(arrow)}')
