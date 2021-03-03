import torch
from blox_old.btorch import nn as bnn
from blox_old.utils import maybe_or, raise_if
from ...core.block import Function, Lambda

# from .utils import load_state_dict_from_url

__all__ = ['ResNet', 'Resnet18', 'Resnet34', 'Resnet50', 'Resnet101',
           'Resnet152', 'Resnext50_32x4d', 'Resnext101_32x8d',
           'WideResnet50_2', 'WideResnet101_2']

#
# model_urls = {
#     'resnet18': 'https://download.pytorch.org/models/resnet18-5c106cde.pth',
#     'resnet34': 'https://download.pytorch.org/models/resnet34-333f7ec4.pth',
#     'resnet50': 'https://download.pytorch.org/models/resnet50-19c8e357.pth',
#     'resnet101': 'https://download.pytorch.org/models/resnet101-5d3b4d8f.pth',
#     'resnet152': 'https://download.pytorch.org/models/resnet152-b121ed2d.pth',
#     'resnext50_32x4d': 'https://download.pytorch.org/models/resnext50_32x4d-7cdf4587.pth',
#     'resnext101_32x8d': 'https://download.pytorch.org/models/resnext101_32x8d-8ba56ff5.pth',
#     'wide_resnet50_2': 'https://download.pytorch.org/models/wide_resnet50_2-95faca4d.pth',
#     'wide_resnet101_2': 'https://download.pytorch.org/models/wide_resnet101_2-32ee1156.pth',
# }


def conv3x3(in_planes, out_planes, stride=1, groups=1, dilation=1, *, name):
    """ 3x3 convolution with padding """
    return bnn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                      padding=dilation, groups=groups, bias=False, dilation=dilation, name=name)


def conv1x1(in_planes, out_planes, stride=1, *, name):
    """ 1x1 convolution """
    return bnn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False, name=name)


class BasicBlock(Function):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, **kwargs):

        super(BasicBlock, self).__init__(In=1, Out=1, **kwargs)

        norm_layer = maybe_or(norm_layer, bnn.BatchNorm2d)
        raise_if(groups != 1 or base_width != 64, ValueError('BasicBlock only supports groups=1 and base_width=64'))
        raise_if(dilation > 1, NotImplementedError("Dilation > 1 not supported in BasicBlock"))

        conv1 = conv3x3(inplanes, planes, stride, name='conv1')
        bn1 = norm_layer(planes, name='bn1')
        relu1 = bnn.ReLU(inplace=True, name='relu1')
        conv2 = conv3x3(planes, planes, name='conv2')
        bn2 = norm_layer(planes, name='bn2')
        relu2 = bnn.ReLU(inplace=True, name='relu2')

        self.downsample = downsample
        self.stride = stride

        identity = x = self.In()

        out = conv1(x)
        out = bn1(out)
        out = relu1(out)

        out = conv2(out)
        out = bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = out + identity
        out = relu2(out)

        self.Out = out


class Bottleneck(Function):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None, groups=1,
                 base_width=64, dilation=1, norm_layer=None, **kwargs):
        super(Bottleneck, self).__init__(In=1, Out=1, **kwargs)

        norm_layer = maybe_or(norm_layer, bnn.BatchNorm2d)
        width = int(planes * (base_width / 64.)) * groups

        # Both self.conv2 and self.downsample layers downsample the input when stride != 1

        conv1 = conv1x1(inplanes, width, name='conv1')
        bn1 = norm_layer(width, name='bn1')
        conv2 = conv3x3(width, width, stride, groups, dilation, name='conv2')
        bn2 = norm_layer(width, name='bn2')
        conv3 = conv1x1(width, planes * self.expansion, name='conv3')
        bn3 = norm_layer(planes * self.expansion, name='bn3')
        relu1 = bnn.ReLU(inplace=True, name='relu1')
        relu2 = bnn.ReLU(inplace=True, name='relu2')
        relu3 = bnn.ReLU(inplace=True, name='relu3')

        self.downsample = downsample
        self.stride = stride

        identity = x = self.In()

        out = conv1(x)
        out = bn1(out)
        out = relu1(out)

        out = conv2(out)
        out = bn2(out)
        out = relu2(out)

        out = conv3(out)
        out = bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out = out + identity
        out = relu3(out)

        self.Out = out


class ResNet(Function):

    def __init__(self, block, layers, num_classes=1000, zero_init_residual=False,
                 groups=1, width_per_group=64, replace_stride_with_dilation=None,
                 norm_layer=None, **kwargs):

        super(ResNet, self).__init__(In=1, Out=1, **kwargs)

        self.__norm_layer = maybe_or(norm_layer, bnn.BatchNorm2d)
        self.inplanes = 64
        self.dilation = 1

        # each element in the tuple indicates if we should replace
        # the 2x2 stride with a dilated convolution instead
        replace_stride_with_dilation = maybe_or(replace_stride_with_dilation, [False, False, False])
        raise_if(len(replace_stride_with_dilation) != 3,
                 ValueError("replace_stride_with_dilation should be None or a 3-element tuple, "
                            "got {}".format(replace_stride_with_dilation)))

        self.groups = groups
        self.base_width = width_per_group

        conv1 = bnn.Conv2d(3, self.inplanes, kernel_size=7, stride=2, padding=3, bias=False, name='conv1')
        bn1 = self.__norm_layer(self.inplanes, name='bn1')
        relu1 = bnn.ReLU(inplace=True, name='relu1')
        maxpool = bnn.MaxPool2d(kernel_size=3, stride=2, padding=1, name='maxpool')
        layer1 = self.__make_layer(block, 64, layers[0], name='layer1')
        layer2 = self.__make_layer(block, 128, layers[1], stride=2,
                                   dilate=replace_stride_with_dilation[0], name='layer2')
        layer3 = self.__make_layer(block, 256, layers[2], stride=2,
                                   dilate=replace_stride_with_dilation[1], name='layer3')
        layer4 = self.__make_layer(block, 512, layers[3], stride=2,
                                   dilate=replace_stride_with_dilation[2], name='layer4')
        avgpool = bnn.AdaptiveAvgPool2d((1, 1), name='avgpool')
        fc = bnn.Linear(512 * block.expansion, num_classes, name='fc')

        x = self.In()
        x = conv1(x)
        x = bn1(x)
        x = relu1(x)
        x = maxpool(x)

        x = layer1(x)
        x = layer2(x)
        x = layer3(x)
        x = layer4(x)

        x = avgpool(x)
        x = Lambda(lambda u: torch.flatten(u, 1), name='flatten')(x)
        x = fc(x)
        self.Out = x

        self.__init_weights(zero_init_residual)

    def __init_weights(self, zero_init_residual):

        # Handle Weight initialization
        for child in self.descendants:
            if isinstance(child, bnn.Conv2d):
                torch.nn.init.kaiming_normal_(child.weight, mode='fan_out', nonlinearity='relu')

            elif isinstance(child, (bnn.BatchNorm2d, bnn.GroupNorm)):
                torch.nn.init.constant_(child.weight, 1)
                torch.nn.init.constant_(child.bias, 0)

        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for child in self.descendants:
                if isinstance(child, Bottleneck):
                    torch.nn.init.constant_(child.bn3.weight, 0)
                elif isinstance(child, BasicBlock):
                    torch.nn.init.constant_(child.bn2.weight, 0)

    def __make_layer(self, block, planes, blocks, stride=1, dilate=False, *, name):
        norm_layer = self.__norm_layer
        downsample = None

        previous_dilation = self.dilation
        if dilate:
            self.dilation *= stride
            stride = 1
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = bnn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride, name='conv1x1_d'),
                norm_layer(planes * block.expansion, name='bn_d'),
                name='downsample')

        layers = [block(self.inplanes, planes, stride, downsample, self.groups,
                        self.base_width, previous_dilation, norm_layer, name='blk0')]

        self.inplanes = planes * block.expansion

        for k in range(1, blocks):
            layers.append(block(self.inplanes, planes, groups=self.groups,
                                base_width=self.base_width, dilation=self.dilation,
                                norm_layer=norm_layer, name=f'blk{k}'))

        return bnn.Sequential(*layers, name=name)


class Resnet18(ResNet):
    def __init__(self, **kwargs):
        super(Resnet18, self).__init__(block=BasicBlock, layers=[2, 2, 2, 2], **kwargs)


class Resnet34(ResNet):
    def __init__(self, **kwargs):
        super(Resnet34, self).__init__(block=BasicBlock, layers=[3, 4, 6, 3], **kwargs)


class Resnet50(ResNet):
    def __init__(self, **kwargs):
        super(Resnet50, self).__init__(block=Bottleneck, layers=[3, 4, 6, 3], **kwargs)


class Resnet101(ResNet):
    def __init__(self, **kwargs):
        super(Resnet101, self).__init__(block=Bottleneck, layers=[3, 4, 23, 3], **kwargs)


class Resnet152(ResNet):
    def __init__(self, **kwargs):
        super(Resnet152, self).__init__(block=Bottleneck, layers=[3, 8, 36, 3], **kwargs)


class Resnext50_32x4d(ResNet):
    def __init__(self, **kwargs):
        super(Resnext50_32x4d, self).__init__(block=Bottleneck, layers=[3, 4, 6, 3],
                                              groups=32, width_per_group=4, **kwargs)


class Resnext101_32x8d(ResNet):
    def __init__(self, **kwargs):
        super(Resnext101_32x8d, self).__init__(block=Bottleneck, layers=[3, 4, 23, 3],
                                               groups=32, width_per_group=8, **kwargs)


class WideResnet50_2(ResNet):
    def __init__(self, **kwargs):
        super(WideResnet50_2, self).__init__(block=Bottleneck, layers=[3, 4, 6, 3],
                                             width_per_group=64 * 2, **kwargs)


class WideResnet101_2(ResNet):
    def __init__(self, **kwargs):
        super(WideResnet101_2, self).__init__(block=Bottleneck, layers=[3, 4, 23, 3],
                                              width_per_group=64 * 2, **kwargs)

