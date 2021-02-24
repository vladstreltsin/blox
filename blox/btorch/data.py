import torch.utils.data as torch_util_data
from blox.core.block import AtomicFunction
from blox.core.generator import Generator
import typing as T
from blox.utils import maybe_or


class AtomicDataLoader(AtomicFunction):
    """A block wrapper around the torch DataLoader class """

    def __init__(self,
                 dataset,
                 batch_size=1,
                 shuffle=False,
                 sampler=None,
                 num_workers=0,
                 collate_fn=None,
                 pin_memory=False,
                 drop_last=False, worker_init_fn=None,  name=None, Out=None):
        super(AtomicDataLoader, self).__init__(name=name, In=(), Out=Out)
        self.__data_loader = torch_util_data.DataLoader(dataset=dataset, batch_size=batch_size,
                                                        shuffle=shuffle, sampler=sampler,
                                                        num_workers=num_workers, collate_fn=collate_fn,
                                                        pin_memory=pin_memory,
                                                        drop_last=drop_last, worker_init_fn=worker_init_fn)

        self.lock_ports = True

        def gen():
            while True:
                yield from self.__data_loader

        self.__gen = gen()

    def fn(self):
        return next(self.__gen)


class DataLoader(Generator):

    def __init__(self,
                 keys: T.Union[T.Iterable, int],
                 batch_size=1, shuffle=False, sampler=None,
                 collate_fn=None, drop_last=False,
                 pin_memory=False,                  # Unused for now
                 queue_size=1, keep_sessions=True, task_delay=0., **kwargs):

        if isinstance(keys, int):
            keys = list(range(keys))

        # We'll use a torch DataLoader to emulate the batch sampler required by the generator
        batch_sampler = torch_util_data.DataLoader(dataset=list(keys),
                                                   sampler=sampler, shuffle=shuffle,
                                                   drop_last=drop_last, batch_size=batch_size)

        # The collate_fn is either provided or we'll just use the default one
        collate_fn = maybe_or(collate_fn, batch_sampler.collate_fn)
        batch_sampler.collate_fn = list

        super(DataLoader, self).__init__(queue_size=queue_size,
                                         keep_sessions=keep_sessions,
                                         collate_fn=collate_fn,
                                         batch_sampler=batch_sampler,
                                         task_delay=task_delay,
                                         **kwargs)
