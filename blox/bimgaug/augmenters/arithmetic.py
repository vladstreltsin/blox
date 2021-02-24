from imgaug.augmenters import arithmetic
from blox.bimgaug.augmenter import _AtomicAugmenter


class Add(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Add, self).__init__(augmenter=arithmetic.Add(*args, **kwargs),
                                  name=name)


class AddElementwise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(AddElementwise, self).__init__(augmenter=arithmetic.AddElementwise(*args, **kwargs),
                                             name=name)


class AdditiveGaussianNoise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(AdditiveGaussianNoise, self).__init__(augmenter=arithmetic.AdditiveGaussianNoise(*args, **kwargs),
                                                    name=name)


class AdditiveLaplaceNoise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(AdditiveLaplaceNoise, self).__init__(augmenter=arithmetic.AdditiveLaplaceNoise(*args, **kwargs),
                                                   name=name)


class Multiply(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Multiply, self).__init__(augmenter=arithmetic.Multiply(*args, **kwargs),
                                       name=name)


class MultiplyElementwise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(MultiplyElementwise, self).__init__(augmenter=arithmetic.MultiplyElementwise(*args, **kwargs),
                                                  name=name)


class Cutout(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Cutout, self).__init__(augmenter=arithmetic.Cutout(*args, **kwargs),
                                     name=name)


class Dropout(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Dropout, self).__init__(augmenter=arithmetic.Dropout(*args, **kwargs),
                                      name=name)


class CoarseDropout(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CoarseDropout, self).__init__(augmenter=arithmetic.CoarseDropout(*args, **kwargs),
                                            name=name)


class Dropout2d(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Dropout2d, self).__init__(augmenter=arithmetic.Dropout2d(*args, **kwargs),
                                        name=name)


class TotalDropout(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(TotalDropout, self).__init__(augmenter=arithmetic.TotalDropout(*args, **kwargs),
                                           name=name)


class ReplaceElementwise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ReplaceElementwise, self).__init__(augmenter=arithmetic.ReplaceElementwise(*args, **kwargs),
                                                 name=name)


class ImpulseNoise(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ImpulseNoise, self).__init__(augmenter=arithmetic.ImpulseNoise(*args, **kwargs),
                                           name=name)


class SaltAndPepper(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(SaltAndPepper, self).__init__(augmenter=arithmetic.SaltAndPepper(*args, **kwargs),
                                            name=name)


class CoarseSaltAndPepper(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CoarseSaltAndPepper, self).__init__(augmenter=arithmetic.CoarseSaltAndPepper(*args, **kwargs),
                                                  name=name)


class Salt(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Salt, self).__init__(augmenter=arithmetic.Salt(*args, **kwargs),
                                   name=name)


class CoarseSalt(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CoarseSalt, self).__init__(augmenter=arithmetic.CoarseSalt(*args, **kwargs),
                                         name=name)


class Pepper(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Pepper, self).__init__(augmenter=arithmetic.Pepper(*args, **kwargs),
                                     name=name)


class CoarsePepper(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(CoarsePepper, self).__init__(augmenter=arithmetic.CoarsePepper(*args, **kwargs),
                                           name=name)


class Invert(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Invert, self).__init__(augmenter=arithmetic.Invert(*args, **kwargs),
                                     name=name)


class Solarize(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Solarize, self).__init__(augmenter=arithmetic.Solarize(*args, **kwargs),
                                       name=name)


class ContrastNormalization(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ContrastNormalization, self).__init__(augmenter=arithmetic.ContrastNormalization(*args, **kwargs),
                                                    name=name)


class JpegCompression(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(JpegCompression, self).__init__(augmenter=arithmetic.JpegCompression(*args, **kwargs),
                                              name=name)
