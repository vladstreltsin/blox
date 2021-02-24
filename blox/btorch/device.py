from __future__ import annotations
from blox.core.device import BlockDevice
from blox.btorch.module import TorchModule, TorchModuleError
import torch
from blox.utils import raise_if, maybe_or
from blox.core.block import Port, Block
import typing as T


class TorchCudaError(TorchModuleError):
    pass


def if_instance_map(x, t, fn):
    return fn(x) if isinstance(x, t) else x


class TorchCuda(BlockDevice):

    _instances = {}

    # The idea is to create a unique instance for each torch device
    def __new__(cls, index=0, *args, **kwargs):

        instance = super(TorchCuda, cls).__new__(cls)
        if index not in cls._instances:
            cls._instances[index] = instance

        return cls._instances[index]

    def __init__(self, index=0, *args, **kwargs):

        super(TorchCuda, self).__init__(*args, **kwargs)
        raise_if(not torch.cuda.is_available(), TorchCudaError("Cuda is unavailable"))
        raise_if(index >= torch.cuda.device_count(), TorchCudaError(f"Given index ({index}) exceeds the number "
                                                                    f"of cuda devices ({torch.cuda.device_count()})"))

        self.__device = torch.device(index)

    @property
    def device(self) -> torch.device:
        return self.__device

    # Moves all TorchModules to the torch.device
    def set(self, block: Block):
        if_instance_map(block, TorchModule, lambda blk: blk.to(self.__device))

    # Moves all TorchModule to the cpu
    def unset(self, block: Block):
        if_instance_map(block, TorchModule, lambda blk: blk.to('cpu'))

    def from_default(self, value: T.Any):
        return if_instance_map(value, torch.Tensor, lambda x: x.to(self.__device))

    def to_default(self, value: T.Any):
        return if_instance_map(value, torch.Tensor, lambda x: x.to('cpu'))
