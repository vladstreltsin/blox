from imgaug import augmenters as ia
from ..augmenter import _AtomicAugmenter, _CompositeAugmenter
from functools import partial


class Resize(_AtomicAugmenter):
    def __init__(self, size, *args, name=None, **kwargs):
        super(Resize, self).__init__(augmenter=ia.size.Resize(size=size, *args, **kwargs),
                                     name=name)


class CropAndPad(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CropAndPad, self).__init__(augmenter=ia.size.CropAndPad(*args, **kwargs),
                                         name=name)


class Crop(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Crop, self).__init__(augmenter=ia.size.Crop(*args, **kwargs),
                                   name=name)


class Pad(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Pad, self).__init__(augmenter=ia.size.Pad(*args, **kwargs),
                                  name=name)


class PadToFixedSize(_AtomicAugmenter):
    def __init__(self, width, height, *args, name=None, **kwargs):
        super(PadToFixedSize, self).__init__(augmenter=ia.size.PadToFixedSize(width=width, height=height,
                                                                              *args, **kwargs),
                                             name=name)


class CenterPadToFixedSize(_AtomicAugmenter):
    def __init__(self, width, height, *args, name=None, **kwargs):
        super(CenterPadToFixedSize, self).__init__(augmenter=ia.size.CenterPadToFixedSize(width=width, height=height,
                                                                                          *args, **kwargs),
                                                   name=name)


class CropToFixedSize(_AtomicAugmenter):
    def __init__(self, width, height, *args, name=None, **kwargs):
        super(CropToFixedSize, self).__init__(augmenter=ia.size.CropToFixedSize(width=width, height=height,
                                                                                *args, **kwargs),
                                              name=name)


class CenterCropToFixedSize(_AtomicAugmenter):
    def __init__(self, width, height, *args, name=None, **kwargs):
        super(CenterCropToFixedSize, self).__init__(augmenter=ia.size.CenterCropToFixedSize(width=width, height=height,
                                                                                            *args, **kwargs),
                                                    name=name)


class CropToMultiplesOf(_AtomicAugmenter):
    def __init__(self, width_multiple, height_multiple, *args, name=None, **kwargs):
        super(CropToMultiplesOf, self).__init__(augmenter=ia.size.CropToMultiplesOf(width_multiple=width_multiple,
                                                                                    height_multiple=height_multiple,
                                                                                    *args, **kwargs),
                                                name=name)


class CenterCropToMultiplesOf(_AtomicAugmenter):
    def __init__(self, width_multiple, height_multiple, *args, name=None, **kwargs):
        super(CenterCropToMultiplesOf, self).__init__(augmenter=ia.size.CenterCropToMultiplesOf(width_multiple=width_multiple,
                                                                                                height_multiple=height_multiple,
                                                                                                *args, **kwargs),
                                                      name=name)


class PadToMultiplesOf(_AtomicAugmenter):
    def __init__(self, width_multiple, height_multiple, *args, name=None, **kwargs):
        super(PadToMultiplesOf, self).__init__(augmenter=ia.size.PadToMultiplesOf(width_multiple=width_multiple,
                                                                                  height_multiple=height_multiple,
                                                                                  *args, **kwargs),
                                               name=name)


class CenterPadToMultiplesOf(_AtomicAugmenter):
    def __init__(self, width_multiple, height_multiple, *args, name=None, **kwargs):
        super(CenterPadToMultiplesOf, self).__init__(augmenter=ia.size.CenterPadToMultiplesOf(width_multiple=width_multiple,
                                                                                              height_multiple=height_multiple,
                                                                                              *args, **kwargs),
                                                     name=name)


class CropToPowersOf(_AtomicAugmenter):
    def __init__(self, width_base, height_base, *args, name=None, **kwargs):
        super(CropToPowersOf, self).__init__(augmenter=ia.size.CropToPowersOf(width_base=width_base,
                                                                              height_base=height_base,
                                                                              *args, **kwargs),
                                             name=name)


class CenterCropToPowersOf(_AtomicAugmenter):
    def __init__(self, width_base, height_base, *args, name=None, **kwargs):
        super(CenterCropToPowersOf, self).__init__(augmenter=ia.size.CenterCropToPowersOf(width_base=width_base,
                                                                                          height_base=height_base,
                                                                                          *args, **kwargs),
                                                   name=name)


class PadToPowersOf(_AtomicAugmenter):
    def __init__(self, width_base, height_base, *args, name=None, **kwargs):
        super(PadToPowersOf, self).__init__(augmenter=ia.size.PadToPowersOf(width_base=width_base,
                                                                            height_base=height_base,
                                                                            *args, **kwargs),
                                            name=name)


class CenterPadToPowersOf(_AtomicAugmenter):
    def __init__(self, width_base, height_base, *args, name=None, **kwargs):
        super(CenterPadToPowersOf, self).__init__(augmenter=ia.size.CenterPadToPowersOf(width_base=width_base,
                                                                                        height_base=height_base,
                                                                                        *args, **kwargs),
                                                  name=name)


class CropToAspectRatio(_AtomicAugmenter):
    def __init__(self, aspect_ratio, *args, name=None, **kwargs):
        super(CropToAspectRatio, self).__init__(augmenter=ia.size.CropToAspectRatio(aspect_ratio=aspect_ratio,
                                                                                    *args, **kwargs),
                                                name=name)


class CenterCropToAspectRatio(_AtomicAugmenter):
    def __init__(self, aspect_ratio, *args, name=None, **kwargs):
        super(CenterCropToAspectRatio, self).__init__(augmenter=ia.size.CenterCropToAspectRatio(aspect_ratio=aspect_ratio,
                                                                                                *args, **kwargs),
                                                      name=name)


class PadToAspectRatio(_AtomicAugmenter):
    def __init__(self, aspect_ratio, *args, name=None, **kwargs):
        super(PadToAspectRatio, self).__init__(augmenter=ia.size.PadToAspectRatio(aspect_ratio=aspect_ratio,
                                                                                  *args, **kwargs),
                                               name=name)


class CenterPadToAspectRatio(_AtomicAugmenter):
    def __init__(self, aspect_ratio, *args, name=None, **kwargs):
        super(CenterPadToAspectRatio, self).__init__(augmenter=ia.size.CenterPadToAspectRatio(aspect_ratio=aspect_ratio,
                                                                                              *args, **kwargs),
                                                     name=name)


class CropToSquare(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CropToSquare, self).__init__(augmenter=ia.size.CropToSquare(*args, **kwargs),
                                           name=name)


class CenterCropToSquare(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CenterCropToSquare, self).__init__(augmenter=ia.size.CenterCropToSquare(*args, **kwargs),
                                                 name=name)


class PadToSquare(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(PadToSquare, self).__init__(augmenter=ia.size.PadToSquare(*args, **kwargs),
                                          name=name)


class CenterPadToSquare(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CenterPadToSquare, self).__init__(augmenter=ia.size.CenterPadToSquare(*args, **kwargs),
                                                name=name)


class KeepSizeByResize(_CompositeAugmenter):
    def __init__(self, children=None, seed=None, name=None, **kwargs):
        super(KeepSizeByResize, self).__init__(augmenter_fn=partial(ia.size.KeepSizeByResize, seed=seed, **kwargs),
                                               name=name,
                                               children=children)
