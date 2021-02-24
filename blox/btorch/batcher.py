from blox._crap.sampler import Batcher
from torch.utils.data import DataLoader
from ..utils import maybe_or


class TorchBatcher(Batcher):
    """ Same as a simple batcher but uses the default torch DataLoader's collate_fn as a default """

    def __init__(self, collate_fn=None, *args, **kwargs):
        super(TorchBatcher, self).__init__(*args, **kwargs,
                                           collate_fn=maybe_or(collate_fn, DataLoader([]).collate_fn))


