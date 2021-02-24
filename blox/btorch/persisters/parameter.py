from blox.core.persist.base import Persister
from blox.core.exceptions import PersisterError
from blox.utils import join_not_none, raise_if

from blox.btorch.module import NNModuleProxy, TensorProxy


class ParameterPersister(Persister):

    def can_save(self, obj, *args, **kwargs):
        return super(ParameterPersister, self).can_save(obj, *args, **kwargs) and \
               (isinstance(obj, NNModuleProxy) or isinstance(obj, TensorProxy))

    def can_load(self, obj, *args, **kwargs):
        return super(ParameterPersister, self).can_load(obj, *args, **kwargs) and \
               (isinstance(obj, NNModuleProxy) or isinstance(obj, TensorProxy))

    def save(self, obj, tag=None, *args, **kwargs):

        if isinstance(obj, NNModuleProxy):
            return self._save_module_proxy(obj, tag)

        elif isinstance(obj, TensorProxy):
            return self._save_tensor_proxy(obj, tag)

        else:
            raise PersisterError(f"Unsupported type {type(obj)} of object {obj} passed to {self.__class__.__name__}")

    def load(self, obj, tag=None, *args, **kwargs):

        if isinstance(obj, NNModuleProxy):
            return self._load_module_proxy(obj, tag)

        elif isinstance(obj, TensorProxy):
            return self._load_tensor_proxy(obj, tag)

        else:
            raise PersisterError(f"Unsupported type {type(obj)} of object {obj} passed to {self.__class__.__name__}")

    def _save_module_proxy(self, module_proxy, tag):
        # We'll handle module proxies using Torch's state dict interface
        state_dict = module_proxy.state_dict()

        for key, tensor in state_dict.items():
            key = join_not_none(self.block.separator, [self.get_obj_name(module_proxy), *key.split('.'), tag])

            # Store the tensors as if they were on the cpu
            self.backend[key] = tensor.detach().cpu()

    def _load_module_proxy(self, module_proxy, tag):

        # We'll use the state_dict() method to figure out what keys are needed
        state_dict = {}
        for key, orig_tensor in module_proxy.state_dict().items():

            # Get the keys
            backend_key = join_not_none(self.block.separator, [self.get_obj_name(module_proxy), *key.split('.'), tag])

            raise_if(backend_key not in self.backend,
                     PersisterError(f"Key {backend_key} is not contained in the backend"))

            # Restore the tensors on the current target device
            state_dict[key] = self.backend[backend_key].to(orig_tensor.device)

        module_proxy.load_state_dict(state_dict=state_dict)

    def _save_tensor_proxy(self, tensor_proxy, tag):

        key = join_not_none(self.block.separator, [self.get_obj_name(tensor_proxy), tag])

        # Store the tensors as if they were on the cpu
        self.backend[key] = tensor_proxy.tensor.detach().cpu()

    def _load_tensor_proxy(self, tensor_proxy, tag):

        key = join_not_none(self.block.separator, [self.get_obj_name(tensor_proxy), tag])
        raise_if(key not in self.backend,
                 PersisterError(f"Key {key} is not contained in the backend"))

        tensor = self.backend[key]

        # See torch.nn.Module._load_from_state_dict
        # Backward compatibility: loading 1-dim tensor from 0.3.* to version 0.4+
        if len(tensor_proxy.tensor.shape) == 0 and len(tensor.shape) == 1:
            tensor = tensor[0]

        raise_if(tensor.shape != tensor_proxy.tensor.shape,
                 PersisterError(f"Tensor shape mishmatch for {key}: given {tensor.shape} "
                                f"expected {tensor_proxy.tensor.shape}"))

        # TODO - Why doesn't torch complain when loading a module?
        # Allow in-place copying
        tensor_proxy.requires_grad, requires_grad = False, tensor_proxy.requires_grad

        # Move tensor to target device and set the tensor proxy
        tensor = tensor.to(tensor_proxy.tensor.device)
        tensor_proxy.tensor.copy_(tensor)

        tensor_proxy.requires_grad = requires_grad
