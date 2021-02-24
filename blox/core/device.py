from __future__ import annotations
from ..utils import maybe_or
from abc import abstractmethod, ABC
import typing as T


class BlockDevice(ABC):

    def __init__(self, *args, **kwargs):
        super(BlockDevice, self).__init__(*args, **kwargs)

    def set(self, block):
        pass

    def unset(self, block):
        pass

    @abstractmethod
    def to_default(self, value: T.Any):
        pass

    @abstractmethod
    def from_default(self, value: T.Any):
        pass

    # The default synchronous move implementation (to and from the default device)
    def move(self, value: T.Any, device: BlockDevice):
        return device.from_default(self.to_default(value))

    # The default synchronous move implementation (just calls the synchronous one)
    async def amove(self, value: T.Any, device: BlockDevice):
        return await self.move(value=value, device=device)


class DefaultDevice(BlockDevice):
    """ The local CPU device. A singleton """
    _instance = None

    def __new__(cls, *args, **kwargs):
        cls._instance = maybe_or(cls._instance, super().__new__(cls, *args, **kwargs))
        return cls._instance

    def from_default(self, value: T.Any):
        return value

    def to_default(self, value: T.Any):
        return value

    def __repr__(self):
        return f'{self.__class__.__name__}()'
