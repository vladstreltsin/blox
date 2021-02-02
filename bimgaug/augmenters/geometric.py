from imgaug.augmenters import geometric
from ..augmenter import _AtomicAugmenter, _CompositeAugmenter
from functools import partial


class Affine(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Affine, self).__init__(augmenter=geometric.Affine(*args, **kwargs),
                                     name=name)


class ScaleX(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ScaleX, self).__init__(augmenter=geometric.ScaleX(*args, **kwargs),
                                     name=name)


class ScaleY(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ScaleY, self).__init__(augmenter=geometric.ScaleY(*args, **kwargs),
                                     name=name)


class TranslateX(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(TranslateX, self).__init__(augmenter=geometric.TranslateX(*args, **kwargs),
                                         name=name)


class TranslateY(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(TranslateY, self).__init__(augmenter=geometric.TranslateY(*args, **kwargs),
                                         name=name)


class Rotate(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Rotate, self).__init__(augmenter=geometric.Rotate(*args, **kwargs),
                                     name=name)


class ShearX(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ShearX, self).__init__(augmenter=geometric.ShearX(*args, **kwargs),
                                     name=name)


class ShearY(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ShearY, self).__init__(augmenter=geometric.ShearY(*args, **kwargs),
                                     name=name)


class AffineCv2(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(AffineCv2, self).__init__(augmenter=geometric.AffineCv2(*args, **kwargs),
                                        name=name)


class PiecewiseAffine(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(PiecewiseAffine, self).__init__(augmenter=geometric.PiecewiseAffine(*args, **kwargs),
                                              name=name)


class PerspectiveTransform(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(PerspectiveTransform, self).__init__(augmenter=geometric.PerspectiveTransform(*args, **kwargs),
                                                   name=name)


class ElasticTransformation(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(ElasticTransformation, self).__init__(augmenter=geometric.ElasticTransformation(*args, **kwargs),
                                                    name=name)


class Rot90(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Rot90, self).__init__(augmenter=geometric.Rot90(*args, **kwargs),
                                    name=name)


class Jigsaw(_AtomicAugmenter):
    def __init__(self, *args, name=None, **kwargs):
        super(Jigsaw, self).__init__(augmenter=geometric.Jigsaw(*args, **kwargs),
                                     name=name)


class WithPolarWarping(_CompositeAugmenter):
    def __init__(self, children=None, seed=None, name=None):
        super(WithPolarWarping, self).__init__(augmenter_fn=partial(geometric.WithPolarWarping, seed=seed),
                                               name=name,
                                               children=children)

