from __future__ import annotations
from ..core.block import AtomicFunction, BlockError, Block
from ..utils import raise_if, maybe_or
from torch import nn
import typing as T
from itertools import chain
from functools import partial
from blox.core.namednode import NamedNodeMixin
from operator import attrgetter
from ..utils import EnumeratedMemo, instance_check, first
from more_itertools import prepend


class TorchModuleError(BlockError):
    pass


class ParameterIterator:
    """ Returns an iterator over all instances of ParameterProxy """

    def __init__(self, block: Block):
        self.__block = block

    @property
    def block(self):
        return self.__block

    def __iter__(self):
        for param in self.block.descendants:
            if isinstance(param, ParameterProxy):
                yield param


class BufferIterator:
    """ Returns an iterator over all instances of BufferProxy """

    def __init__(self, block: Block):
        self.__block = block

    @property
    def block(self):
        return self.__block

    def __iter__(self):
        for param in self.block.descendants:
            if isinstance(param, BufferIterator):
                yield param


def set_mode(block: Block, train: bool):
    for block in prepend([block], block.blocks.descendants):
        if isinstance(block, TorchModule):
            if train:
                block.train()
            else:
                block.eval()


def set_trainable(parameters: T.Iterable[ParameterProxy], train: bool):
    for param in parameters:
        raise_if(not isinstance(param, ParameterProxy),
                 TorchModuleError(f"The object {param} is not a ParameterProxy"))
        param.requires_grad = bool(train)


class TensorProxy(NamedNodeMixin):
    """ A wrapper class around torch.nn.Parameter """

    def __init__(self, _parameter_fn: T.Callable(), _parent, _name):
        self.__lock = False
        self.__parameter_fn = _parameter_fn
        self.__name = _name
        self.parent = _parent
        self.__lock = True

    @property
    def separator(self):
        return self.parent.separator

    @property
    def name(self):
        return self.__name

    @property
    def tensor(self):
        return self.__parameter_fn()

    # These implement the torch.Tensor API

    @property
    def data(self):
        return self.tensor.data

    @property
    def grad(self):
        return self.tensor.grad

    @property
    def requires_grad(self):
        return self.tensor.requires_grad

    @requires_grad.setter
    def requires_grad(self, value):
        self.tensor.requires_grad = value

    def fill_(self, *args, **kwargs):
        self.tensor.fill_(*args, **kwargs)

    def copy_(self, *args, **kwargs):
        self.tensor.copy_(*args, **kwargs)

    def normal_(self, *args, **kwargs):
        self.tensor.normal_(*args, **kwargs)

    def uniform_(self, *args, **kwargs):
        self.tensor.uniform_(*args, **kwargs)

    def zero_(self, *args, **kwargs):
        self.tensor.zero_(*args, **kwargs)

    def dim(self):
        return self.tensor.dim()

    def size(self, *args, **kwargs):
        return self.tensor.size(*args, **kwargs)

    def __getitem__(self, item):
        return self.tensor[item]

    def __setitem__(self, key, value):
        self.tensor[key] = value

    def _pre_attach(self, parent):
        raise_if(self.__lock, TorchModuleError("Parent setting is disabled"))

    def _pre_detach(self, parent):
        raise_if(self.__lock, TorchModuleError("Parent setting is disabled"))

    def _pre_attach_children(self, children):
        raise_if(self.__lock, TorchModuleError("Children setting is disabled"))

    def _pre_detach_children(self, children):
        raise_if(self.__lock, TorchModuleError("Children setting is disabled"))


class ParameterProxy(TensorProxy):
    pass


class BufferProxy(TensorProxy):
    pass


class _NNModuleChildren:
    """ A wrapper around Torch Module's children, parameters and buffers """

    def __init__(self, _module_proxy: NNModuleProxy, _attr_fn, _proxy_init_fn, _proxy_cls):
        self.__module_proxy = _module_proxy

        # A function that returns an iterator over the children proxies
        self.__attr_fn = _attr_fn

        # How the relevant proxies (parameters, buffers, submodules) are being initialized
        self.__proxy_init_fn = _proxy_init_fn

        # The class of the relevant proxies (parameters, buffers, submodules)
        self.__proxy_cls = _proxy_cls

        # Add children of the module proxy (the connection is done inside the constructor)
        for name, child in self.__attr_fn():
            self.__proxy_init_fn(name=name, module_proxy=_module_proxy, child=child)

        self.__memo = EnumeratedMemo(container_fn=partial(attrgetter('children'), self.__module_proxy),
                                     name_fn=attrgetter('name'),
                                     filter_fn=partial(instance_check, cls=self.__proxy_cls))

    @property
    def module__(self) -> nn.Module:
        return self.__module_proxy.module__

    def __contains__(self, item) -> bool:

        if isinstance(item, str):
            return item in self.__memo

        elif isinstance(item, self.__proxy_cls):
            return item in self.__module_proxy.children

        return False

    def __getitem__(self, item: str):
        """ Get a sub-block by name """

        raise_if(not isinstance(item, str), TypeError(f"Unsupported key type {type(item)}"))

        if item in self.__memo:
            return self.__memo[item]
        else:
            raise KeyError(item)

    def keys(self):
        yield from map(first, self.__attr_fn())

    def values(self):
        yield from map(partial(getattr, self.__module_proxy), self.keys())

    def items(self):
        yield from zip(self.keys(), self.values())

    def __bool__(self):
        return True

    def __getattr__(self, item: str):
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    def __dir__(self):
        return list(self.keys()) + list(super(_NNModuleChildren, self).__dir__())

    def __iter__(self):
        return iter(self.values())

    def __len__(self):
        return len(self.__attr_fn())


class _NNModuleParameters(_NNModuleChildren):
    def __init__(self, _module_proxy: NNModuleProxy):

        # The kwargs is needed to match the expected signature
        def _proxy_init_fn(name, module_proxy, **kwargs):
            ParameterProxy(_parameter_fn=partial(attrgetter(name), module_proxy.module__),
                           _parent=module_proxy, _name=name)

        super(_NNModuleParameters, self).__init__(_module_proxy=_module_proxy,
                                                  _attr_fn=partial(getattr(_module_proxy.module__, 'named_parameters'),
                                                                   recurse=False),
                                                  _proxy_init_fn=_proxy_init_fn, _proxy_cls=ParameterProxy)


class _NNModuleBuffers(_NNModuleChildren):
    def __init__(self, _module_proxy: NNModuleProxy):

        # The kwargs is needed to match the expected signature
        def _proxy_init_fn(name, module_proxy, **kwargs):
            BufferProxy(_parameter_fn=partial(attrgetter(name), module_proxy.module__),
                        _parent=module_proxy, _name=name)

        super(_NNModuleBuffers, self).__init__(_module_proxy=_module_proxy,
                                               _attr_fn=partial(getattr(_module_proxy.module__, 'named_buffers'),
                                                                recurse=False),
                                               _proxy_init_fn=_proxy_init_fn, _proxy_cls=BufferProxy)


class _NNModuleSubmodules(_NNModuleChildren):
    def __init__(self, _module_proxy: NNModuleProxy):

        def _proxy_init_fn(name, module_proxy, child):
            NNModuleProxy(module=child, name=name, parent=module_proxy)

        super(_NNModuleSubmodules, self).__init__(_module_proxy=_module_proxy,
                                                  _attr_fn=partial(getattr(_module_proxy.module__, 'named_children')),
                                                  _proxy_init_fn=_proxy_init_fn, _proxy_cls=NNModuleProxy)


class NNModuleProxy(NamedNodeMixin):
    """ Allows easy access to torch module's children """

    def __init__(self, module: nn.Module, name: T.Optional = None, parent: T.Optional = None):
        self.__lock = False
        self.__module = module
        self.__name = name

        # Set the parent if provided
        self.parent = parent

        # Add module parameters
        self.__buffers = _NNModuleBuffers(_module_proxy=self)
        self.__parameters = _NNModuleParameters(_module_proxy=self)
        self.__submodules = _NNModuleSubmodules(_module_proxy=self)

        self.__lock = True

    @property
    def parameters(self):
        return self.__parameters

    @property
    def buffers(self):
        return self.__buffers

    @property
    def submodules(self):
        return self.__submodules

    @property
    def name(self):
        return self.__name

    @property
    def module__(self) -> nn.Module:
        return self.__module

    def _pre_attach(self, parent):
        raise_if(self.__lock, TorchModuleError("Parent setting is disabled"))

    def _pre_detach(self, parent):
        raise_if(self.__lock, TorchModuleError("Parent setting is disabled"))

    def _pre_attach_children(self, children):
        raise_if(self.__lock, TorchModuleError("Children setting is disabled"))

    def _pre_detach_children(self, children):
        raise_if(self.__lock, TorchModuleError("Children setting is disabled"))

    def __contains__(self, item):
        return item in self.parameters or \
               item in self.buffers or \
               item in self.submodules

    def __getitem__(self, item):
        if item in self.parameters:
            return self.parameters[item]

        if item in self.buffers:
            return self.buffers[item]

        if item in self.submodules:
            return self.submodules[item]

        raise KeyError(item)

    def __getattr__(self, item: str):
        if not item.startswith('_') and item in self:
            return self[item]
        else:
            raise AttributeError(item)

    # To give it a Look-and-Feel of a dictionary
    def keys(self) -> T.Iterable[str]:
        yield from chain(self.parameters.keys(), self.buffers.keys(), self.submodules.keys())

    def values(self):
        yield from chain(self.parameters.values(), self.buffers.values(), self.submodules.values())

    def items(self):
        yield from chain(self.parameters.items(), self.buffers.items(), self.submodules.items())

    def __len__(self) -> int:
        return len(self.parameters) + len(self.buffers) + len(self.submodules)

    def __iter__(self):
        return iter(self.values())

    def __dir__(self):
        return list(self.keys()) + list(super(NNModuleProxy, self).__dir__())

    def to(self, device):
        self.module__.to(device)

    def forward(self, *args, **kwargs):
        return self.module__.forward(*args, **kwargs)

    def train(self):
        self.module__.train()

    def eval(self):
        self.module__.eval()

    def state_dict(self):
        return self.module__.state_dict()

    def load_state_dict(self, state_dict):
        self.module__.load_state_dict(state_dict=state_dict, strict=True)


class TorchModule(AtomicFunction, NNModuleProxy):

    def __init__(self, module: nn.Module, *args, **kwargs):
        AtomicFunction.__init__(self, port_map=None, *args, **kwargs)
        NNModuleProxy.__init__(self, module=module)

        self.register_attribute_container__(self.parameters)
        self.register_attribute_container__(self.submodules)
        self.register_attribute_container__(self.buffers)

        # TODO: I am not totally sure if there could be a collision with the ports names here

    def fn(self, *args, **kwargs):
        return self.forward(*args, **kwargs)

    @classmethod
    def wrap(cls, **kwargs):
        raise NotImplementedError

