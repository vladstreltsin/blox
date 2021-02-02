from functools import partial
from torch.optim import lr_scheduler as lrs
import typing as T
from ..utils import maybe_error

from ..core.engine import SessionError


class TorchSchedulerError(SessionError):
    pass


class TorchScheduler:

    def __init__(self, scheduler_fn):
        self.__scheduler_fn = scheduler_fn
        self.__scheduler: T.Optional[lrs._LRScheduler] = None

    def init(self, optimizer):
        self.__scheduler = self.__scheduler_fn(optimizer)

    def step(self):
        maybe_error(self.__scheduler, TorchSchedulerError("The scheduler was not initialized"))
        self.__scheduler.step(epoch=None)


class LambdaLR(TorchScheduler):
    def __init__(self, lr_lambda, last_epoch=-1):
        super(LambdaLR, self).__init__(scheduler_fn=partial(lrs.LambdaLR, lr_lambda=lr_lambda, last_epoch=last_epoch))


class StepLR(TorchScheduler):
    def __init__(self, step_size, gamma=0.1, last_epoch=-1):
        super(StepLR, self).__init__(scheduler_fn=partial(lrs.StepLR,
                                                          step_size=step_size, gamma=gamma, last_epoch=last_epoch))


class MultiStepLR(TorchScheduler):
    def __init__(self, milestones, gamma=0.1, last_epoch=-1):
        super(MultiStepLR, self).__init__(scheduler_fn=partial(lrs.MultiStepLR,
                                                               milestones=milestones,
                                                               gamma=gamma, last_epoch=last_epoch))


class ExponentialLR(TorchScheduler):
    def __init__(self, gamma, last_epoch=-1):
        super(ExponentialLR, self).__init__(scheduler_fn=partial(lrs.ExponentialLR,
                                                                 gamma=gamma, last_epoch=last_epoch))


class CosineAnnealingLR(TorchScheduler):
    def __init__(self, T_max, eta_min=0, last_epoch=-1):
        super(CosineAnnealingLR, self).__init__(scheduler_fn=partial(lrs.CosineAnnealingLR,
                                                                     T_max=T_max, eta_min=eta_min,
                                                                     last_epoch=last_epoch))


class ReduceLROnPlateau(TorchScheduler):
    def __init__(self, mode='min', factor=0.1, patience=10,
                 verbose=False, threshold=1e-4, threshold_mode='rel',
                 cooldown=0, min_lr=0, eps=1e-8):
        super(ReduceLROnPlateau, self).__init__(scheduler_fn=partial(lrs.ReduceLROnPlateau,
                                                                     mode=mode, factor=factor, patience=patience,
                                                                     verbose=verbose, threshold=threshold,
                                                                     threshold_mode=threshold_mode,
                                                                     cooldown=cooldown, min_lr=min_lr,
                                                                     eps=eps))


class CyclicLR(TorchScheduler):
    def __init__(self, base_lr,
                 max_lr,
                 step_size_up=2000,
                 step_size_down=None,
                 mode='triangular',
                 gamma=1.,
                 scale_fn=None,
                 scale_mode='cycle',
                 cycle_momentum=True,
                 base_momentum=0.8,
                 max_momentum=0.9,
                 last_epoch=-1):
        super(CyclicLR, self).__init__(scheduler_fn=partial(lrs.CyclicLR,
                                                            base_lr=base_lr,
                                                            max_lr=max_lr,
                                                            step_size_up=step_size_up,
                                                            step_size_down=step_size_down,
                                                            mode=mode,
                                                            gamma=gamma,
                                                            scale_fn=scale_fn,
                                                            scale_mode=scale_mode,
                                                            cycle_momentum=cycle_momentum,
                                                            base_momentum=base_momentum,
                                                            max_momentum=max_momentum,
                                                            last_epoch=last_epoch))


class CosineAnnealingWarmRestarts(TorchScheduler):
    def __init__(self, T_0, T_mult=1, eta_min=0, last_epoch=-1):
        super(CosineAnnealingWarmRestarts, self).__init__(scheduler_fn=partial(lrs.CosineAnnealingWarmRestarts,
                                                                               T_0=T_0,
                                                                               T_mult=T_mult,
                                                                               eta_min=eta_min,
                                                                               last_epoch=last_epoch))
