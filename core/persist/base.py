from blox.core._block import _Block, Port, _BlockPersisters
from blox.core.exceptions import BlockError, PersisterError
from blox.core.namednode import NamedNodeMixin
from blox.utils import maybe_error, second_or
from blox.core.engine import Session
from blox.utils import maybe_or, join_not_none
from abc import ABC, abstractmethod
from blox.core.device import DefaultDevice
import typing as T
from functools import partial
import pickle
from abc import ABC, abstractmethod


class PersisterBackend(ABC):

    @abstractmethod
    def __contains__(self, item):
        pass

    @abstractmethod
    def __getitem__(self, item):
        pass

    @abstractmethod
    def __setitem__(self, item, value):
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class Persister(ABC):
    """ The base class all persisters derive from """

    def __init__(self, name: str, block: T.Optional[_Block]=None,
                 backend: T.Optional[PersisterBackend]=None,
                 final=True, save_enabled=True, load_enabled=True):
        self.__block = block
        self._final = final
        self._save_enabled = save_enabled
        self._load_enabled = load_enabled

        self.__block.persisters.add_persister__(name=name, persister=self)

        # The backend is any object that realized the dictionary interface
        self._backend = None
        self.backend = backend

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, bk: T.Optional[PersisterBackend]):
        if bk is not None and not isinstance(bk, PersisterBackend):
            raise TypeError(f"Backend must be of type {PersisterBackend.__name__}")
        self._backend = bk

    @property
    def save_enabled(self):
        return self._save_enabled

    @property
    def load_enabled(self):
        return self._load_enabled

    @property
    def final(self):
        return self._final

    @property
    def block(self):
        return self.__block

    def get_obj_name(self, obj: NamedNodeMixin, default_name=''):
        rel_name = obj.rel_name(self.block)
        maybe_error(rel_name, BlockError(f"Cannot persist object {obj} since "
                                         f"it is not a descendant of the block {self.block}"))
        return second_or(rel_name.split(self.block.separator, maxsplit=1), default=default_name)

    @abstractmethod
    def save(self, obj, *args, **kwargs):
        pass

    @abstractmethod
    def load(self, obj, *args, **kwargs):
        pass

    # Whether or not a persister is capable of handling the specific object save request
    def can_save(self, obj, *args, **kwargs):
        return self.save_enabled

    def can_load(self, obj, *arg, **kwargs):
        return self.load_enabled

    def __enter__(self):
        if self.backend is None:
            raise PersisterError("Backend wasn't set")
        self.backend.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.backend is None:
            raise PersisterError("Backend wasn't set")
        self.backend.__exit__(exc_type, exc_val, exc_tb)
