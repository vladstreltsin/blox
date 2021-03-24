from itertools import chain
from blox.etc.errors import BlockCompositionError
from more_itertools import prepend
from blox.etc.utils import remove_trailing_digits


class BlockTransformsMixin:
    """ Adds structural transformations to the Block class """

    def __call__(self, *args, **kwargs):
        """
        This method allows composing blocks over ports.
        Connects the block's inputs to the provided ports
        """

        # Handle the case when In and Out are passed without ()
        args = list(chain(*map(lambda arg: [arg], args)))

        if len(args) + len(kwargs) > len(self.In):
            raise BlockCompositionError(f"Too many inputs provided, expected at most: {len(self.In)}, "
                                        f"given: {len(args) + len(kwargs)}")

        # Figure out who is the parent block of self and all of the input ports
        # It is either the downstream block of one of the input ports
        try:
            parent = next(iter(filter(lambda x: x is not None,
                                      prepend(self.parent,
                                              map(lambda x: x.downstream_block, chain(args, kwargs.values()))))))
        except StopIteration:
            raise BlockCompositionError('Could not figure out the parent block')

        # Make self a child of the found parent (won't do anything if that is the case already)
        self._try_nesting(parent, self)

        for port_name, src in chain(zip(self.In.keys(), args), kwargs.items()):
            assert src.block is not None, "All ports must be attached to blocks"

            # This can happen only for output ports whose blocks are floating
            if src.downstream_block is None:
                self._try_nesting(parent, src.block)

            self.In[port_name] = src

        # Return the output ports
        return self.Out()

    @staticmethod
    def _try_nesting(parent, child):

        """Try attaching child to parent fixing name conflicts if arise """
        assert parent is not None
        if child.parent is not parent:
            base_name = remove_trailing_digits(child.name)
            n = 0

            # TODO - this is very slow for multiple operators in the same block
            while True:
                name = base_name if n == 0 else f'{base_name}{n}'
                if name not in parent.blocks:
                    parent.blocks[name] = child
                    break
                else:
                    n = n + 1

    @property
    def name(self):
        raise NotImplementedError

    @property
    def parent(self):
        raise NotImplementedError

    @parent.setter
    def parent(self, value):
        raise NotImplementedError

    @property
    def In(self):
        raise NotImplementedError

    @property
    def Out(self):
        raise NotImplementedError
