from imgaug import augmenters as ia
from blox_old.bimgaug.augmenter import _CompositeAugmenter
from functools import partial


class Sequential(_CompositeAugmenter):

    def __init__(self, children=None, seed=None, random_order=False, name=None):
        super(Sequential, self).__init__(augmenter_fn=partial(ia.meta.Sequential,
                                                              seed=seed,
                                                              random_order=random_order),
                                         name=name,
                                         children=children)


class SomeOf(_CompositeAugmenter):

    def __init__(self, n=None, children=None, seed=None, random_order=False, name=None):
        super(SomeOf, self).__init__(augmenter_fn=partial(ia.meta.SomeOf,
                                                          n=n, random_order=random_order,
                                                          seed=seed),
                                     name=name,
                                     children=children)


class OneOf(_CompositeAugmenter):

    def __init__(self, children=None, seed=None, name=None):
        super(OneOf, self).__init__(augmenter_fn=partial(ia.meta.OneOf, seed=seed),
                                    name=name,
                                    children=children)

