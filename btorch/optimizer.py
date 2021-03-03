from __future__ import annotations
# from torch.optim import SGD, Adam, Adagrad, Adadelta, AdamW, SparseAdam, \
#     Adamax, ASGD, LBFGS, RMSprop, Rprop

import torch.optim as torch_opt
from blox_old.core.block.base import Sink
import typing as T
from blox_old.utils import maybe_or, maybe_error, const
from collections import deque
from blox_old.btorch.module import TorchModule, ParameterIterator
from functools import partial
from blox_old.core.engine import SessionError
from blox_old.btorch.scheduler import TorchScheduler, LambdaLR


class TorchOptimizerError(SessionError):
    pass


class TorchOptimizer(Sink):

    def __init__(self, *args, optimizer_fn, scheduler: T.Optional[TorchScheduler]=None, **kwargs):
        super(TorchOptimizer, self).__init__(*args, **kwargs)

        self.__optimizer_fn = optimizer_fn
        self.__optimizer = None
        self.__scheduler = maybe_or(scheduler, LambdaLR(lr_lambda=const(1.), last_epoch=-1))

    def init(self):
        """ Searches for all torch parameters that might influence the input """

        seen_ports = set()
        next_ports = deque([self.In()])
        parameters = set()

        while next_ports:

            # Get the next port and update seen ports
            port = next_ports.popleft()
            if port in seen_ports:
                continue
            seen_ports.add(port)

            # Figure out the next port to check
            block = port.block

            # If the port has upstream then it is the port we check
            # Otherwise, In case the block is atomic, we pass to its inputs
            if port.upstream:
                next_ports.extend(port.upstream)
            elif block.atomic:
                next_ports.extend(block.In)

            # Add parameters if the block has them
            if isinstance(block, TorchModule):
                parameters.update(map(lambda x: x.tensor, ParameterIterator(block)))

        # Sets the optimizer and initializes the LR scheduler
        self.__optimizer = self.__optimizer_fn(parameters)
        self.__scheduler.init(self.__optimizer)

    def step(self, session):
        maybe_error(self.__optimizer, TorchOptimizerError("The optimizer was not initialized"))
        self.__optimizer.zero_grad()
        loss = self.get(session)
        loss.backward()

        self.__optimizer.step()
        self.__scheduler.step()


class Adagrad(TorchOptimizer):

    def __init__(self, lr=0.01, lr_decay=0, weight_decay=0, initial_accumulator_value=0, eps=1e-10, *args, **kwargs):
        super(Adagrad, self).__init__(*args, **kwargs,
                                      optimizer_fn=partial(torch_opt.Adagrad,
                                                           lr=lr, lr_decay=lr_decay, weight_decay=weight_decay,
                                                           initial_accumulator_value=initial_accumulator_value,
                                                           eps=eps))


class Adadelta(TorchOptimizer):

    def __init__(self, lr=1.0, rho=0.9, eps=1e-06, weight_decay=0, *args, **kwargs):
        super(Adadelta, self).__init__(*args, **kwargs,
                                       optimizer_fn=partial(torch_opt.Adadelta,
                                                            lr=lr, rho=rho, eps=eps, weight_decay=weight_decay))


class Adam(TorchOptimizer):

    def __init__(self, lr=0.001, betas=(0.9, 0.999), eps=1e-08, weight_decay=0, amsgrad=False, *args, **kwargs):
        super(Adam, self).__init__(*args, **kwargs,
                                   optimizer_fn=partial(torch_opt.Adam,
                                                        lr=lr, betas=betas, eps=eps, weight_decay=weight_decay,
                                                        amsgrad=amsgrad))


class AdamW(TorchOptimizer):

    def __init__(self, lr=0.001, betas=(0.9, 0.999), eps=1e-08, weight_decay=0.01, amsgrad=False, *args, **kwargs):
        super(AdamW, self).__init__(*args, **kwargs,
                                    optimizer_fn=partial(torch_opt.AdamW,
                                                         lr=lr, betas=betas, eps=eps, weight_decay=weight_decay,
                                                         amsgrad=amsgrad))

# TODO add all others
