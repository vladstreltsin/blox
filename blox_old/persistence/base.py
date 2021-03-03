from __future__ import annotations
from blox_old.core.exceptions import BlockError, PersisterError
from blox_old.core.tree.namednode import NamedNodeMixin
from blox_old.utils.funcs import maybe_error, second_or
import typing as tp
from abc import ABC, abstractmethod
from collections import OrderedDict

if tp.TYPE_CHECKING:
    from blox_old.core.block.base.ports.port import Port


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

    def __init__(self, name: str, block: tp.Optional[_Block]=None,
                 backend: tp.Optional[PersisterBackend]=None,
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
    def backend(self, bk: tp.Optional[PersisterBackend]):
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


class BlockPersisters:
    def __init__(self, _block):
        self._block = _block
        self._persisters = OrderedDict()

    @property
    def block(self):
        return self._block

    def __contains__(self, item):
        return item in self._persisters

    def __getitem__(self, item: str) -> Persister:
        return self._persisters[item]

    def __delitem__(self, item: str):
        if item in self._persisters:
            del self._persisters[item]
        else:
            raise KeyError(item)

    def __getattr__(self, item: str) -> Persister:
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __delattr__(self, item):
        if item in self:
            del self[item]
        else:
            super(BlockPersisters, self).__delattr__(item)

    def add_persister__(self, name, persister: Persister):
        self._persisters[name] = persister

    # To give it a Look-and-Feel of a dictionary
    def keys(self) -> tp.Iterable[str]:
        return self._persisters.keys()

    def values(self) -> tp.Iterable[Port]:
        return self._persisters.values()

    def items(self) -> tp.Iterable[tp.Tuple[str, Port]]:
        return self._persisters.items()

    def __len__(self) -> int:
        return len(self._persisters)

    def __iter__(self) -> tp.Iterable[Port]:
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(BlockPersisters, self).__dir__())


class BlockPersistersMixin:

    def __lazy_init(self):
        try:
            _ = self.__persisters
        except AttributeError:
            self.__persisters = BlockPersisters(_block=self)

    @property
    def persisters(self):
        self.__lazy_init()
        return self.__persisters
