import imgaug.augmenters as ia
from blox.core.block import AtomicFunction, Block, Function
from blox.core.exceptions import BlockError
from blox.core.engine import Session
from blox.utils import maybe_or
from imgaug import HooksImages
from abc import abstractmethod
from functools import partial
import typing as T
from blox.bimgaug.batch import ToBatch, FromBatch, AUGMENTER_COLUMNS


class AugmenterError(BlockError):
    pass


class _AugmenterBlock(Function):

    def __init__(self, name=None):
        super(_AugmenterBlock, self).__init__(name=name, In=1, Out=1)
        self.lock_ports = True

    @property
    @abstractmethod
    def augmenter(self):
        pass

    def propagate(self, session: Session):
        # Call the internal augmenter to compute the output port
        session[self.Out()] = self.augmenter.augment_batch_(session[self.In()].value)


class _AtomicAugmenter(_AugmenterBlock):
    """ A base class for a block wrapping a single augmenter """
    def __init__(self, augmenter: ia.meta.Augmenter, name=None):
        super(_AtomicAugmenter, self).__init__(name=name)
        self.__augmenter = augmenter
        self.atomic = True

    @property
    def augmenter(self):
        return self.__augmenter


class _CompositeAugmenter(_AugmenterBlock):
    """ A base class for a block wrapping a sequence of augmenters """

    def __init__(self, augmenter_fn: T.Callable,
                 children: T.Union[None, _AugmenterBlock, T.Iterable[_AugmenterBlock]]=None, name=None):
        super(_CompositeAugmenter, self).__init__(name=name)

        self.__augmenter = None
        self.__augmenter_fn = augmenter_fn

        # Connect the children in series from the input to the output
        if children is not None:

            # The case when only a single child is given
            if isinstance(children, _AugmenterBlock):
                children = [children]

            x = self.In()
            for child in children:
                x = child(x)
            self.Out = x

    def pre_attach_child_check(self, child):
        if not isinstance(child, _AugmenterBlock):
            raise AugmenterError(f"Only instances of {_AtomicAugmenter.__name__} "
                                 f"and {_CompositeAugmenter.__name__} can be sub-blocks "
                                 f"of {_CompositeAugmenter.__name__}")

    def on_port_graph_change(self):
        self.__augmenter = None
        if isinstance(self.parent, _AugmenterBlock):
            self.parent.on_port_graph_change()

    @property
    def augmenter(self):
        if self.__augmenter is None:

            # This utility function make sure that a port has only one downstream port and returns that port
            def _port_downstream(p):
                if len(p.downstream) != 1:
                    raise AugmenterError(f"Expected downstream size of 1 for port {p}, got {len(p.downstream)}")
                return next(iter(p.downstream))

            # Check that the sub-block are connected in a sequence from the input port to the output
            port = _port_downstream(self.In())
            for block in self.port_graph__.topo_blocks():

                if port is not block.In():
                    raise AugmenterError(f"Expected {port} to match with {block.In()}")
                port = _port_downstream(block.Out())

            if port is not self.Out():
                raise AugmenterError(f"Expected {port} to match with {self.Out()}")

            # Builds the composite augmenter in a recursive way
            self.__augmenter = self.__augmenter_fn(children=[block.augmenter
                                                             for block in self.port_graph__.topo_blocks()])

        return self.__augmenter


class Augmenter(Function):

    def __init__(self, columns=AUGMENTER_COLUMNS, children=None, name=None):

        def to_in(s):
            return f'in_{s}'

        def to_out(s):
            return f'out_{s}'

        super(Augmenter, self).__init__(name=name, In=map(to_in, columns), Out=map(to_out, columns))

        # Convert input to batch
        x = ToBatch(In=columns)(self.In)

        # Apply augmenters sequence
        for child in maybe_or(children, []):
            x = child(x)

        # Convert batch to outputs
        self.Out = FromBatch(Out=columns)(x)

