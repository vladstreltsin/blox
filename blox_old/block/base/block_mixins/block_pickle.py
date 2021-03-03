from __future__ import annotations
import pickle
import threading
from contextlib import contextmanager
from blox_old.exceptions import BlockError
import typing as tp

if tp.TYPE_CHECKING:
    from blox_old.block.base.block_base import BlockBase


# This is a nice trick to allow viewing inner blocks as "detached" in some contexts.
# The only thing that makes blocks "know" of the external world in through their parent attribute.
# We would like to create contexts where a block may 'think' that he is the top level block (e.g. when pickling)
# To do so, we override the parent attribute getter to look at this context variable that will be set to the
# 'orphaned' block view

class DetachedBlock:

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


DETACHED_BLOCK = DetachedBlock()


class BlockPickleMixin:
    """
    Adds pickling functionality to the BlockBase class
    """

    @property
    def blocks(self):
        raise NotImplementedError

    @property
    def ports(self):
        raise NotImplementedError

    # The following scheme will serialize the root block twice. Therefore, when
    # using an unpickled copy block, just put block = block.ports.block
    def __getstate__(self):
        odict = self.__dict__.copy()

        # This is the first block we encounter in an hierarchy
        if DETACHED_BLOCK.block is None:
            with DETACHED_BLOCK(self):
                odict['_NodeMixin__parent'] = None
                state = {'state': pickle.dumps(odict)}

            return state

        # This is when we pickle circular references to the block
        elif DETACHED_BLOCK.block is self:
            odict['_NodeMixin__parent'] = None
            return odict

        # This is for everything else
        else:
            if DETACHED_BLOCK.block in self.blocks:
                raise BlockError("Pickle Leak")

            return odict

    def __setstate__(self, state):

        # This is the first block we encounter in an hierarchy
        if DETACHED_BLOCK.block is None:
            with DETACHED_BLOCK(self):
                self.__dict__.update(pickle.loads(state['state']))

        # This is for everything else
        else:
            self.__dict__.update(state)

    def copy(self):
        return pickle.loads(pickle.dumps(self)).fix_pickle()

    # This fixes the double pickling of the root block
    def fix_pickle(self) -> BlockBase:
        return self.ports.block

