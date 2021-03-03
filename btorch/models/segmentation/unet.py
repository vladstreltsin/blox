""" Taken from https://github.com/milesial/Pytorch-UNet/blob/master/unet """

import torch.nn.functional as F
from blox_old.btorch import nn as bnn
from blox_old.btorch.util import Concat
from blox_old.core.block.base import AtomicFunction, Function
from blox_old.utils import maybe_or


class DoubleConv(Function):
    """(convolution => [BN] => ReLU) * 2"""

    def __init__(self, in_channels, out_channels, mid_channels=None, **kwargs):
        super(DoubleConv, self).__init__(In=1, Out=1, **kwargs)
        mid_channels = maybe_or(mid_channels, out_channels)

        x = self.In()
        x = bnn.Conv2d(in_channels, mid_channels, kernel_size=3, padding=1, name='conv1')(x)
        x = bnn.BatchNorm2d(mid_channels, name='bn1')(x)
        x = bnn.ReLU(inplace=True, name='relu1')(x)
        x = bnn.Conv2d(mid_channels, out_channels, kernel_size=3, padding=1, name='conv2')(x)
        x = bnn.BatchNorm2d(out_channels, name='bn2')(x)
        x = bnn.ReLU(inplace=True, name='relu2')(x)
        self.Out = x


class Down(Function):
    """Downscaling with maxpool then double conv"""

    def __init__(self, in_channels, out_channels, **kwargs):
        super(Down, self).__init__(In=1, Out=1, **kwargs)

        x = self.In()
        x = bnn.MaxPool2d(2, name='maxpool')(x)
        x = DoubleConv(in_channels, out_channels, name='conv_dbl')(x)
        self.Out = x


class UpPad(AtomicFunction):

    def __init__(self, **kwargs):
        super(UpPad, self).__init__(In=2, Out=1, port_map=None, **kwargs)
        self.lock_ports = True

    def fn(self, x1, x2):
        # input is CHW
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]

        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2,
                        diffY // 2, diffY - diffY // 2])

        return x1


class Up(Function):
    """Upscaling then double conv"""

    def __init__(self, in_channels, out_channels, bilinear=True, **kwargs):
        super(Up, self).__init__(In=2, Out=1, **kwargs)

        # if bilinear, use the normal convolutions to reduce the number of channels
        if bilinear:
            up = bnn.Upsample(scale_factor=2, mode='bilinear', align_corners=True, name='bilinear')
            conv = DoubleConv(in_channels, out_channels, in_channels // 2, name='conv_dbl')
        else:
            up = bnn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2, name='conv_t_2d')
            conv = DoubleConv(in_channels, out_channels, name='conv_dbl')

        x1 = self.In[0]
        x2 = self.In[1]

        x1 = up(x1)
        x1 = UpPad(name='pad')(x1, x2)

        # if you have padding issues, see
        # https://github.com/HaiyongJiang/U-Net-Pytorch-Unstructured-Buggy/commit/0e854509c2cea854e247a9c615f175f76fbb2e3a
        # https://github.com/xiaopeng-liao/Pytorch-UNet/commit/8ebac70e633bac59fc22bb5195e513d5832fb3bd
        x = Concat(In=2, dim=1)(x2, x1)
        x = conv(x)
        self.Out = x


class OutConv(Function):
    def __init__(self, in_channels, out_channels, **kwargs):
        super(OutConv, self).__init__(In=1, Out=1, **kwargs)

        conv = bnn.Conv2d(in_channels, out_channels, kernel_size=1, name='conv')

        self.Out = conv(self.In())


class UNet(Function):

    def __init__(self, n_channels, n_classes, bilinear=True, **kwargs):
        super(UNet, self).__init__(In=1, Out=1, **kwargs)
        factor = 2 if bilinear else 1

        inc = DoubleConv(n_channels, 64, name='conv_in')
        down1 = Down(64, 128, name='down1')
        down2 = Down(128, 256, name='down2')
        down3 = Down(256, 512, name='down3')
        down4 = Down(512, 1024 // factor, name='down4')

        up1 = Up(1024, 512 // factor, bilinear, name='up1')
        up2 = Up(512, 256 // factor, bilinear, name='up2')
        up3 = Up(256, 128 // factor, bilinear, name='up3')
        up4 = Up(128, 64, bilinear, name='up4')
        outc = OutConv(64, n_classes, name='conv_out')

        x = self.In()
        x1 = inc(x)
        x2 = down1(x1)
        x3 = down2(x2)
        x4 = down3(x3)
        x5 = down4(x4)
        x = up1(x5, x4)
        x = up2(x, x3)
        x = up3(x, x2)
        x = up4(x, x1)
        self.Out = outc(x)

