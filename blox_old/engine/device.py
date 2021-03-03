from __future__ import annotations
from blox_old.utils.funcs import maybe_or
from abc import abstractmethod, ABC
import typing as tp


class BlockDevice(ABC):

    def __init__(self, *args, **kwargs):
        super(BlockDevice, self).__init__(*args, **kwargs)

    def set(self, block):
        pass

    def unset(self, block):
        pass

    @abstractmethod
    def to_default(self, value: tp.Any):
        pass

    @abstractmethod
    def from_default(self, value: tp.Any):
        pass

    # The default synchronous move implementation (to and from the default device)
    def move(self, value: tp.Any, device: BlockDevice):
        return device.from_default(self.to_default(value))

    # The default synchronous move implementation (just calls the synchronous one)
    async def amove(self, value: tp.Any, device: BlockDevice):
        return await self.move(value=value, device=device)


class DefaultDevice(BlockDevice):
    """ The local CPU device. A singleton """
    _instance = None

    def __new__(cls, *args, **kwargs):
        cls._instance = maybe_or(cls._instance, super().__new__(cls, *args, **kwargs))
        return cls._instance

    def from_default(self, value: tp.Any):
        return value

    def to_default(self, value: tp.Any):
        return value

    def __repr__(self):
        return f'{self.__class__.__name__}()'


class BlockDeviceMixin:
    """ This class adds a device to the block """

    @property
    def blocks(self):
        raise NotImplementedError

    @property
    def device(self) -> BlockDevice:
        self.__lazy_init()
        return self.__device

    @device.setter
    def device(self, device: tp.Optional[BlockDevice]):
        self.__lazy_init()

        # None - means local CPU
        device = maybe_or(device, DefaultDevice())

        # Maybe make devices singletons?
        if device is not self.__device:
            self.__device.unset(self)
            self.__device = device
            self.__device.set(self)

        for child in self.blocks.descendants:
            child.device = device

    def __lazy_init(self):
        try:
            _ = self.__device
        except AttributeError:
            self.__device = DefaultDevice()
