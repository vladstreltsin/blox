import detectron2.layers.wrappers as wrp
from blox.core.block import AtomicFunction
from blox.btorch.module import TorchModule


class Conv2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Conv2d, self).__init__(name=name, In=1, Out=1, module=wrp.Conv2d(*args, **kwargs))
        self.lock_ports = True


class Linear(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Linear, self).__init__(name=name, In=1, Out=1, module=wrp.Linear(*args, **kwargs))
        self.lock_ports = True


class ConvTranspose2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(ConvTranspose2d, self).__init__(name=name, In=1, Out=1, module=wrp.ConvTranspose2d(*args, **kwargs))
        self.lock_ports = True


class BatchNorm2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(BatchNorm2d, self).__init__(name=name, In=1, Out=1, module=wrp.BatchNorm2d(*args, **kwargs))
        self.lock_ports = True


class interpolate(AtomicFunction):

    def __init__(self, *args, name=None, **kwargs):
        super(interpolate, self).__init__(name=name, In=1, Out=1)
        self.lock_ports = True
        self._args = args
        self._kwargs = kwargs

    def fn(self, x):
        return wrp.interpolate(x, *self._args, **self._kwargs)


class cat(AtomicFunction):
    """ A wrapper around torch.cat """

    def __init__(self, dim=0, **kwargs):
        self.__dim = dim
        super(cat, self).__init__(Out=1, **kwargs)

    def fn(self, *args):
        return wrp.cat(list(args), dim=self.__dim)
