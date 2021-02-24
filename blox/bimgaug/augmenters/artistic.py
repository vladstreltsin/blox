from imgaug import augmenters as ia
from blox.bimgaug.augmenter import _AtomicAugmenter


class Cartoon(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Cartoon, self).__init__(augmenter=ia.artistic.Cartoon(*args, **kwargs),
                                      name=name)
