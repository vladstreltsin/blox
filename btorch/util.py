import torch
from blox_old.core.block.base import AtomicFunction


class Concat(AtomicFunction):
    """ A wrapper around torch.cat """

    def __init__(self, dim=0, **kwargs):
        self.__dim = dim
        super(Concat, self).__init__(Out=1, **kwargs)

    def fn(self, *args):
        return torch.cat(args, dim=self.__dim)


