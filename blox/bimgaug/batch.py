from ..core.block import Block, AtomicFunction, BlockError
from imgaug.augmentables import UnnormalizedBatch, Batch
import typing as T
from ..utils import maybe_or


class ImgaugError(BlockError):
    pass


AUGMENTER_COLUMNS = ('images', 'bounding_boxes', 'polygons', 'segmentation_maps', 'keypoints', 'line_strings', 'data')


class ToBatch(AtomicFunction):

    def __init__(self, *args, In=AUGMENTER_COLUMNS, **kwargs):
        super(ToBatch, self).__init__(*args, **kwargs, In=In, Out=1)

        # Check that all input ports have valid names
        for port_name in In:
            if port_name not in AUGMENTER_COLUMNS:
                raise ImgaugError(f"Illegal port name {port_name} (Must be one of {AUGMENTER_COLUMNS})")

    def fn(self, *args):
        result = UnnormalizedBatch(**{self.In[n].name: arg for n, arg in enumerate(args)}).\
            to_normalized_batch().\
            to_batch_in_augmentation()

        return result


class FromBatch(AtomicFunction):

    def __init__(self, *args, Out=AUGMENTER_COLUMNS, **kwargs):
        super(FromBatch, self).__init__(*args, **kwargs, In=1, Out=Out)

        # Check that all input ports have valid names
        for port_name in Out:
            if port_name not in AUGMENTER_COLUMNS:
                raise ImgaugError(f"Illegal port name {port_name} (Must be one of {AUGMENTER_COLUMNS})")

    def fn(self, batch):
        return [getattr(batch, f'{port.name}') for port in self.Out]


