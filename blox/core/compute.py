from blox.etc.errors import ComputeError
from blox.core.block import Block


class PullResult:
    pass


class Done(PullResult):
    __slots__ = ('value', )

    def __init__(self, value):
        self.value = value


class Next(PullResult):
    __slots__ = ('port', )

    def __init__(self, port):
        self.port = port


class TopoSort:

    def __init__(self, block):
        self._block = block

    def reset(self):
        pass

    def __iter__(self):
        pass


class Computable(Block):
    """ Base class for all computable blocks implementing the pull, push, propagate methods """

    def __init__(self, push_cleanup=True, *args, **kwargs):
        super(Computable, self).__init__(*args, **kwargs)
        self.push_cleanup = push_cleanup
        self.toposort = TopoSort(self)

    def pull_generator(self, port, state) -> PullResult:
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        if port in state:
            yield Done(state[port])

        if port.upstream is None:
            raise ComputeError(f'Trying to pull on port {port} without an upstream')

        value = yield Next(port.upstream)
        state[port] = value

        yield Done(value)

    def push(self, port, state):
        assert port in self.In or port in self.Out, f"Port {port} doesn't belong to block {self}"

        if port not in state:
            raise ComputeError(f'Trying to push the port {port} that has no value')

        for p in port.downstream:
            state[p] = state[port]

        if self.push_cleanup:
            del state[port]

    def propagate(self, state):
        # Push all inputs
        for port in self.In:
            port.push(state)

        # Propagate essential children (in topological order)
        for child in self.toposort:
            child.propagate(state)

            for port in child.Out:
                port.push(state)

    def _parent_post_attach_callback(self, child):
        self.toposort.reset()

    def _parent_post_detach_callback(self, child):
        self.toposort.reset()
