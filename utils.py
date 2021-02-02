from __future__ import annotations

import re
import typing as T
from typing import Callable, TypeVar, Optional


def raise_if(cond, exception: Exception):
    if cond:
        raise exception


class const:
    """ A constant value as a function """
    def __init__(self, value):
        self.value = value

    def __call__(self, *args, **kwargs):
        return self.value


def identity(x):
    return x


# Here *args and **kwargs are used as a garbage can
def instance_check(item, cls):
    return isinstance(item, cls)


def first(pair):
    return pair[0]


def second(pair):
    return pair[1]


class EnumeratedMemo:
    """ Implemets a memo for lookup in a list of items each having a name """

    def __init__(self, container_fn: T.callable, name_fn: T.Callable, filter_fn: T.Optional[T.Callable]):
        self.__container_fn = container_fn
        self.__memo = {}
        self.__filter_fn = filter_fn
        self.__name_fn = name_fn

    def __contains__(self, item) -> bool:
        """ Check whether self.block contains item as one of its children, where item can be
        either a string or an instance of Block.
        """

        # Get the container instance
        container = self.__container_fn()

        def contains(idx, itm):
            return idx < len(container) and self.__filter_fn(container[idx]) and self.__name_fn(container[idx]) == itm

        # This is the case when we refer to sub-blocks by their names
        # We'll use a memo here since this kind of check will be used often
        if isinstance(item, str):

            child_idx = self.__memo.get(item, None)

            # This is the case that the memo finds something
            if child_idx is not None and contains(child_idx, item):
                return True

            # Otherwise, look-up the child one by one and update the memo
            for child_idx, child in enumerate(container):
                if contains(child_idx, item):
                    self.__memo[item] = child_idx
                    return True

            return False

        return False

    def __getitem__(self, item):
        """ Get a sub-block by name """

        if not isinstance(item, str):
            raise TypeError(f"Unsupported key type {type(item)}")

        # Get the container instance
        container = self.__container_fn()

        if item in self:
            # This line IS a bit hacky. We trust the __contains__ method to update self.__children_name_memo
            # in case item is actually one of block's children
            return container[self.__memo[item]]

        else:
            raise KeyError(item)

# Monad utils to handle None-s


T = TypeVar('T')
S = TypeVar('S')


def maybe_fmap(f: Callable[T, S]) -> Callable[Optional[T], Optional[S]]:
    return lambda x: f(x) if x is not None else None


def maybe_bind(x: Optional[T], f: Callable[T, Optional[S]]):
    return f(x) if x is not None else None


def maybe_error(x: Optional[T], exception: Exception) -> T:
    if x is not None:
        return x
    raise exception


def maybe_raise(exception: Optional[Exception]) -> None:
    if exception is not None:
        raise exception


def maybe_or(x: Optional[T], other: T.Any) -> T.Any:
    if x is not None:
        return x
    else:
        return other


# Taken from https://github.com/Kemaweyan/singleton_decorator/blob/master/singleton_decorator
class _SingletonWrapper:
    """
    A singleton wrapper class. Its instances would be created
    for each decorated class.
    """

    def __init__(self, cls):
        self.__wrapped__ = cls
        self._instance = None

    def __call__(self, *args, **kwargs):
        """Returns a single instance of decorated class"""
        if self._instance is None:
            self._instance = self.__wrapped__(*args, **kwargs)
        return self._instance


def singleton(cls):
    """
    A singleton decorator. Returns a wrapper objects. A call on that object
    returns a single instance object of decorated class. Use the __wrapped__
    attribute to access decorated class directly in unit tests
    """
    return _SingletonWrapper(cls)


RE_LEGAL_NAME = re.compile('[0-9a-zA-Z_]+')
RE_PORT_RANGE_LETTERS = re.compile('(?P<start>[a-zA-Z])-(?P<end>[a-zA-Z])')
RE_PORT_RANGE_INDICES = re.compile('(?P<prefix>[a-zA-Z]+)(?P<start>[0-9]+)-(?P<end>[0-9]+)')


def assert_identifier(name):
    # Provided name must be a legal python identifier
    if not RE_LEGAL_NAME.match(name) or name.startswith('_') or name.endswith('_'):
        raise ValueError(f"Illegal name {name}")


# Copied from: https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def to_tuple(obj) -> T.Tuple:
    if obj is None:
        return ()
    if isinstance(obj, str):
        return obj,
    else:
        return tuple(obj)


def parse_ports(obj, default_prefix):

    if isinstance(obj, int):
        prefix = default_prefix
        return tuple(f"{prefix}{n}" for n in range(1, obj+1))

    elif isinstance(obj, str):
        match = RE_PORT_RANGE_LETTERS.match(obj)
        if match:
            start = match['start']
            end = match['end']

            if ord(end) < ord(start):
                raise ValueError(f"The specified range {obj} is empty")
            return tuple(f"{chr(c)}" for c in range(ord(start), ord(end)+1))

        match = RE_PORT_RANGE_INDICES.match(obj)
        if match:
            prefix = match['prefix']
            start = int(match['start'])
            end = int(match['end'])

            if end < start:
                raise ValueError(f"The specified range {obj} is empty")
            return tuple(f"{prefix}{n}" for n in range(start, end + 1))

        return to_tuple(obj)

    return to_tuple(obj)


# Taken from https://stackoverflow.com/questions/2020014/get-fully-qualified-class-name-of-an-object-in-python
def fullname(o):
    """
    o.__module__ + "." + o.__class__.__qualname__ is an example in
    this context of H.L. Mencken's "neat, plausible, and wrong."
    Python makes no guarantees as to whether the __module__ special
    attribute is defined, so we take a more circumspect approach.
    Alas, the module name is explicitly excluded from __qualname__
    in Python 3.
    """

    builtins_module = str.__class__.__module__
    if o.__class__.__name__ == 'function':
        module = o.__module__
        name = o.__name__
    else:
        module = o.__class__.__module__
        name = o.__class__.__name__

    # Avoid reporting __builtin__
    if module is None or module == builtins_module:
        return name
    else:
        return f'{module}.{name}'


def compose(*fns):
    """ Functional composition of inputs """

    if len(fns) == 0:
        raise ValueError("At least one function must be provided")

    def composite(*args):
        x = fns[-1](*args)
        for fn in reversed(fns[0:-1]):
            x = fn(x)
        return x

    return composite


def second_or(lst, default):
    if len(lst) > 1:
        return lst[1]
    else:
        return default


def join_not_none(sep: str, iterable):
    return sep.join(filter(None, iterable))


def filter_compose(*fns: T.Callable[[T.Any], bool]):
    """ Composition of filter functions """
    def composite(x):
        for f in fns:
            if not f(x):
                return False
        return True

    return composite


def signature_check(dummy, *args, **kwargs):
    """Checks whether the arguments match the signature of a dummy function by catching a TypeError"""
    try:
        dummy(*args, **kwargs)
        return True

    except TypeError:
        return False
