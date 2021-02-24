from blox.btorch.module import TorchModule
from blox.core.block import Block
from torch import nn


class Sequential(Block):

    def __init__(self, *blocks: TorchModule, name=None, **kwargs):
        super(Sequential, self).__init__(In=1, Out=1, name=name, **kwargs)
        self.lock_ports = True

        # Apply blocks in sequence
        p = self.In()

        for block in blocks:
            block.parent = self
            block.In = p
            p = block.Out()

        self.Out = p


class Conv2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Conv2d, self).__init__(name=name, module=nn.Conv2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Linear(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Linear, self).__init__(name=name, module=nn.Linear(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Softmax(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Softmax, self).__init__(name=name, module=nn.Softmax(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class MaxPool2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(MaxPool2d, self).__init__(name=name, module=nn.MaxPool2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class AdaptiveAvgPool2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(AdaptiveAvgPool2d, self).__init__(name=name, module=nn.AdaptiveAvgPool2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class ReLU(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(ReLU, self).__init__(name=name, module=nn.ReLU(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class BatchNorm1d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(BatchNorm1d, self).__init__(name=name, module=nn.BatchNorm1d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class BatchNorm2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(BatchNorm2d, self).__init__(name=name, module=nn.BatchNorm2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class BatchNorm3d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(BatchNorm3d, self).__init__(name=name, module=nn.BatchNorm3d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class GroupNorm(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(GroupNorm, self).__init__(name=name, module=nn.GroupNorm(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Upsample(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Upsample, self).__init__(name=name, module=nn.Upsample(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class ConvTranspose1d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(ConvTranspose1d, self).__init__(name=name, module=nn.ConvTranspose1d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class ConvTranspose2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(ConvTranspose2d, self).__init__(name=name, module=nn.ConvTranspose2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class ConvTranspose3d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(ConvTranspose3d, self).__init__(name=name, module=nn.ConvTranspose3d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Dropout(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Dropout, self).__init__(name=name, module=nn.Dropout(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Dropout2d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Dropout2d, self).__init__(name=name, module=nn.Dropout2d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True


class Dropout3d(TorchModule):

    def __init__(self, *args, name=None, **kwargs):
        super(Dropout3d, self).__init__(name=name, module=nn.Dropout3d(*args, **kwargs), In=1, Out=1)
        self.lock_ports = True
