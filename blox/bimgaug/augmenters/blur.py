from imgaug import augmenters as ia
from blox.bimgaug.augmenter import _AtomicAugmenter


class GaussianBlur(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(GaussianBlur, self).__init__(augmenter=ia.blur.GaussianBlur(*args, **kwargs),
                                           name=name)


"""
    * :class:`GaussianBlur`
    * :class:`AverageBlur`
    * :class:`MedianBlur`
    * :class:`BilateralBlur`
    * :class:`MotionBlur`
    * :class:`MeanShiftBlur`
"""